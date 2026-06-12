import pytest
import asyncio
import pytest_asyncio
import os
import joblib
import numpy as np
import torch
import torch.nn as nn
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.api.deps import get_db
from app.main import app
from httpx import AsyncClient, ASGITransport

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class StandardTabularClassifier(nn.Module):
    def __init__(self, input_dim: int = 2, hidden_dim: int = 4, output_dim: int = 2):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
    def forward(self, x):
        return self.network(x)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="session", autouse=True)
def generate_test_model_artifacts():
    """
    Creates temporary model binary artifacts for prediction tests.
    """
    temp_dir = os.path.abspath("test_artifacts")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 1. Sklearn
    X = np.array([[10, 50.0], [5, 20.0]])
    y = np.array([1, 0])
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression()
    clf.fit(X, y)
    joblib.dump(clf, os.path.join(temp_dir, "test_sklearn.joblib"))
    
    # 2. PyTorch
    torch_model = StandardTabularClassifier(input_dim=2)
    torch.save(torch_model.state_dict(), os.path.join(temp_dir, "test_pytorch.pt"))
    
    yield
    
    # Clean up test artifacts
    if os.path.exists(os.path.join(temp_dir, "test_sklearn.joblib")):
        os.remove(os.path.join(temp_dir, "test_sklearn.joblib"))
    if os.path.exists(os.path.join(temp_dir, "test_pytorch.pt")):
        os.remove(os.path.join(temp_dir, "test_pytorch.pt"))
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)