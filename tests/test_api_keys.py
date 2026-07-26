import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.ml import model_cache
from app.models.api_key import ApiKey

# Test database configuration — mirrors tests/test_drift_alerting.py

SQLALCHEMY_TEST_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")

if SQLALCHEMY_TEST_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_TEST_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    model_cache.clear_all()

    # This file specifically tests the auth gate itself, so — unlike every other
    # test file — it flips disable_auth back off for the duration of each test.
    original_disable_auth = settings.disable_auth
    settings.disable_auth = False

    yield

    settings.disable_auth = original_disable_auth
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
    model_cache.clear_all()


@pytest.fixture
def client():
    return TestClient(app)


# Bootstrap and enforcement

def test_bootstrap_creates_first_key_without_auth(client):
    """A fresh instance (zero keys) can mint its first key with no Authorization header."""
    resp = client.post("/api/v1/api-keys", json={"name": "bootstrap"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"].startswith("mmk_")
    assert body["key_prefix"] == body["key"][:12]
    assert body["name"] == "bootstrap"


def test_protected_endpoint_rejects_missing_key(client):
    client.post("/api/v1/api-keys", json={"name": "bootstrap"})
    resp = client.get("/api/v1/models")
    assert resp.status_code == 401


def test_protected_endpoint_accepts_valid_key(client):
    created = client.post("/api/v1/api-keys", json={"name": "bootstrap"}).json()
    resp = client.get("/api/v1/models", headers={"Authorization": f"Bearer {created['key']}"})
    assert resp.status_code == 200


def test_protected_endpoint_rejects_garbage_key(client):
    client.post("/api/v1/api-keys", json={"name": "bootstrap"})
    resp = client.get("/api/v1/models", headers={"Authorization": "Bearer not-a-real-key"})
    assert resp.status_code == 401


def test_second_bootstrap_requires_existing_key(client):
    """Once an active key exists, minting another one requires auth."""
    first = client.post("/api/v1/api-keys", json={"name": "first"}).json()

    unauthenticated = client.post("/api/v1/api-keys", json={"name": "second"})
    assert unauthenticated.status_code == 401

    authenticated = client.post(
        "/api/v1/api-keys",
        json={"name": "second"},
        headers={"Authorization": f"Bearer {first['key']}"},
    )
    assert authenticated.status_code == 201


def test_revoked_key_is_rejected(client):
    created = client.post("/api/v1/api-keys", json={"name": "bootstrap"}).json()
    headers = {"Authorization": f"Bearer {created['key']}"}

    revoke_resp = client.delete(f"/api/v1/api-keys/{created['id']}", headers=headers)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked_at"] is not None

    resp = client.get("/api/v1/models", headers=headers)
    assert resp.status_code == 401


def test_list_api_keys_never_exposes_plaintext_or_hash(client):
    created = client.post("/api/v1/api-keys", json={"name": "bootstrap"}).json()
    headers = {"Authorization": f"Bearer {created['key']}"}

    resp = client.get("/api/v1/api-keys", headers=headers)
    assert resp.status_code == 200
    listed = resp.json()
    assert len(listed) == 1
    assert "key" not in listed[0]
    assert "key_hash" not in listed[0]
    assert listed[0]["key_prefix"] == created["key_prefix"]


def test_key_hash_never_stores_plaintext(client):
    created = client.post("/api/v1/api-keys", json={"name": "bootstrap"}).json()

    db = TestingSessionLocal()
    row = db.query(ApiKey).filter(ApiKey.id == created["id"]).first()
    assert row.key_hash != created["key"]
    db.close()
