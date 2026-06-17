import numpy as np
from sqlalchemy.orm import Session

from app.models.faiss_index import FAISSIndex
from app.monitoring.faiss_indexer import query_knn


def score_novelty(db: Session, model_id: str, activation: np.ndarray) -> tuple[float | None, bool]:
    """
    Calculate the FAISS distance for a query activation vector and classify
    whether it represents an out-of-distribution (OOD) novelty.
    """
    # 1. Fetch index record from database
    index_record = db.query(FAISSIndex).filter(FAISSIndex.model_id == model_id).first()
    if not index_record:
        # If no FAISS index exists for this model, fallback to null/False
        return None, False

    try:
        # 2. Query nearest neighbor distances (K=5)
        distances = query_knn(index_record.index_file_path, activation, k=5)
        
        # 3. Compute mean distance for this sample
        mean_distance = float(np.mean(distances))

        # 4. Check against baseline threshold (mean + 3 * std)
        threshold = index_record.baseline_mean_distance + 3 * index_record.baseline_std_distance
        novelty_flag = mean_distance > threshold

        return mean_distance, novelty_flag
    except Exception:
        # In case of any indexing or query issues, return default safe values
        return None, False
