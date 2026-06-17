import os
import faiss
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models.faiss_index import FAISSIndex


def build_and_save_index(db: Session, model_id: str, vectors: np.ndarray) -> FAISSIndex:
    """
    Build a FAISS L2 index over activation vectors, calculate baseline mean/std,
    save the index to disk, and register it in the database.
    """
    # 1. Prepare vectors as float32
    vectors = vectors.astype(np.float32)
    n_samples, dim = vectors.shape

    if n_samples == 0:
        raise ValueError("Cannot build FAISS index with 0 vectors.")

    # 2. Build FAISS IndexFlatL2
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    # 3. Persist index file to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    index_file_name = f"faiss_{model_id}.index"
    index_file_path = os.path.join(settings.upload_dir, index_file_name)
    faiss.write_index(index, index_file_path)

    # 4. Perform self-query to compute baseline statistics
    # Query for the 5 nearest neighbors
    k = min(5, n_samples)
    distances, _ = index.search(vectors, k)

    # Compute mean distance per sample across k-NN
    mean_distances = np.mean(distances, axis=1)

    baseline_mean = float(np.mean(mean_distances))
    baseline_std = float(np.std(mean_distances))

    # 5. Clear any existing records for this model to maintain 1-to-1 relationships
    existing = db.query(FAISSIndex).filter(FAISSIndex.model_id == model_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    # 6. Save new index record
    db_record = FAISSIndex(
        model_id=model_id,
        index_file_path=index_file_path,
        vector_dim=dim,
        vector_count=n_samples,
        baseline_mean_distance=baseline_mean,
        baseline_std_distance=baseline_std,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return db_record


def query_knn(index_file_path: str, vector: np.ndarray, k: int = 5) -> np.ndarray:
    """
    Load index from disk and query for nearest neighbor distances.
    """
    if not os.path.exists(index_file_path):
        raise FileNotFoundError(f"FAISS index file not found at: {index_file_path}")

    index = faiss.read_index(index_file_path)

    # Ensure vector is 2D float32
    vector = vector.astype(np.float32)
    if len(vector.shape) == 1:
        vector = vector.reshape(1, -1)

    k = min(k, index.ntotal)
    distances, _ = index.search(vector, k)
    return distances
