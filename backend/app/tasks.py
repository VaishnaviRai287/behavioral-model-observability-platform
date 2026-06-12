import asyncio
from celery import Celery
from uuid import UUID
from typing import Tuple, Any
import numpy as np
import scipy.stats as stats
import faiss
from sqlalchemy.future import select

from app.core.database import SessionLocal
from app.crud.fingerprint import fingerprint_crud
from app.crud.observability import observability_crud
from app.models.observability import InferenceLog

import os

# Configure Celery
broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
celery_app = Celery("tasks", broker=broker_url, backend=backend_url)

# Support running Celery tasks synchronously (eager mode) for testing/local setups without Redis
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true":
    celery_app.conf.task_always_eager = True

def compute_ks_drift(expected_matrix: np.ndarray, actual_matrix: np.ndarray) -> Tuple[float, float]:
    """
    Computes KS values across 2D matrices.
    """
    max_stat = 0.0
    min_p_val = 1.0
    for col in range(expected_matrix.shape[1]):
        stat, p_val = stats.ks_2samp(expected_matrix[:, col], actual_matrix[:, col])
        max_stat = max(max_stat, stat)
        min_p_val = min(min_p_val, p_val)
    return max_stat, min_p_val

def compute_psi(expected_vector: np.ndarray, actual_vector: np.ndarray, num_bins: int = 10) -> float:
    """
    Calculates Population Stability Index.
    """
    percentiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(expected_vector, percentiles)
    bins = np.unique(bins)
    
    expected_counts, _ = np.histogram(expected_vector, bins=bins)
    actual_counts, _ = np.histogram(actual_vector, bins=bins)
    
    # Avoid zero counts
    expected_pcts = (expected_counts + 1e-5) / (np.sum(expected_counts) + 1e-5 * len(expected_counts))
    actual_pcts = (actual_counts + 1e-5) / (np.sum(actual_counts) + 1e-5 * len(actual_counts))
    
    return float(np.sum((actual_pcts - expected_pcts) * np.log(actual_pcts / expected_pcts)))

async def run_drift_checks(db, model_id: UUID, fingerprint: Any, logs: list):
    # 1. Rebuild expectations from fingerprint metadata
    features = fingerprint.high_uncertainty_regions.get("regions", [])
    if not features:
        return
        
    num_features = len(features)
    
    # Construct expected samples matrix representing reference space boundaries
    expected_samples = np.random.uniform(0.0, 1.0, size=(100, num_features))
    for j, feat in enumerate(features):
        expected_samples[:, j] = expected_samples[:, j] * (feat["max"] - feat["min"]) + feat["min"]
        
    # Extract actual records binnings
    actual_records = []
    for log in logs:
        row = []
        for feat in features:
            row.append(log.features.get(feat["feature"], 0.0))
        actual_records.append(row)
    actual_samples = np.array(actual_records)
    
    # Compute KS checks
    max_ks, min_pval = compute_ks_drift(expected_samples, actual_samples)
    if min_pval < 0.05:
        await observability_crud.create_alert(
            db=db,
            model_id=model_id,
            alert_type="FEATURE_DRIFT",
            severity="warning",
            message=f"Statistically significant feature drift detected (KS p-value={min_pval:.4f}).",
            metric_value=float(max_ks)
        )
        
    # 2. Check Latent Space Novelty if PyTorch model embeddings are logged
    actual_embeddings = [log.latent_embedding["vector"] for log in logs if log.latent_embedding is not None]
    if len(actual_embeddings) > 0 and len(fingerprint.boundary_samples.get("samples", [])) > 0:
        # Construct reference vector space from bndry samples
        ref_samples = []
        for s in fingerprint.boundary_samples["samples"]:
            # Mock baseline representations
            ref_samples.append([0.5] * len(actual_embeddings[0]))
        ref_space = np.array(ref_samples, dtype='float32')
        
        # Build FAISS index
        dimension = ref_space.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(ref_space)
        
        # Compute threshold limit (95th percentile distance)
        distances, _ = index.search(ref_space, 1)
        threshold = max(0.1, float(np.percentile(distances, 95)))
        
        # Check current inputs distances
        query_vectors = np.array(actual_embeddings, dtype='float32')
        live_distances, _ = index.search(query_vectors, 1)
        mean_live_dist = float(np.mean(live_distances))
        
        if mean_live_dist > threshold * 2:
            await observability_crud.create_alert(
                db=db,
                model_id=model_id,
                alert_type="LATENT_NOVELTY",
                severity="critical",
                message=f"Extreme latent space novelty anomaly detected (mean distance={mean_live_dist:.3f}, threshold={threshold:.3f}).",
                metric_value=mean_live_dist
            )

@celery_app.task
def process_observability_check(model_id_str: str):
    model_id = UUID(model_id_str)
    
    # Helper running async loop inside celery worker thread
    loop = asyncio.get_event_loop()
    
    async def run():
        async with SessionLocal() as db:
            fingerprint = await fingerprint_crud.get_latest_by_model(db, model_id)
            if not fingerprint:
                return
                
            logs = await observability_crud.get_recent_logs(db, model_id, limit=50)
            if len(logs) < 10:
                return # Wait for minimum baseline statistics
                
            await run_drift_checks(db, model_id, fingerprint, logs)
            
    loop.run_until_complete(run())
