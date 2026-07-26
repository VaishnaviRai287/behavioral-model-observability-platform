import numpy as np
from sqlalchemy.orm import Session

from app.models.faiss_index import FAISSIndex
from app.monitoring.faiss_indexer import query_knn


def score_novelty(db: Session, model_id: str, activation: np.ndarray) -> tuple[float | None, bool]:
    """Score how far a query activation sits from the model's baseline FAISS index, flagging it as novel past mean + 3*std."""
    index_record = db.query(FAISSIndex).filter(FAISSIndex.model_id == model_id).first()
    if not index_record:
        return None, False

    try:
        distances = query_knn(index_record.index_file_path, activation, k=5)
        mean_distance = float(np.mean(distances))

        threshold = index_record.baseline_mean_distance + 3 * index_record.baseline_std_distance
        novelty_flag = mean_distance > threshold

        return mean_distance, novelty_flag
    except Exception:
        # Novelty scoring is best-effort — an indexing/query failure shouldn't
        # fail the prediction request itself.
        return None, False
