import numpy as np
from fastapi import HTTPException
from sklearn.tree import DecisionTreeRegressor, _tree
from sqlalchemy.orm import Session

from app.fingerprinting.comparator import compare_fingerprints
from app.fingerprinting.metrics import compute_fingerprint_metrics
from app.models.fingerprint import Fingerprint
from app.models.ml_model import MLModel
from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession
from app.schemas.fingerprint import ComparisonResult


def create_fingerprint(db: Session, session_id: str) -> Fingerprint:
    """
    Compute and store a fingerprint for a completed probe session.

    Raises:
        404: If session_id doesn't exist
        422: If the probe session is not yet complete
        400: If a fingerprint already exists for this session
    """

    # ── Fetch the probe session ───────────────────────────────────────────────
    session = db.query(ProbeSession).filter(ProbeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Probe session not found")

    if session.status != "done":
        raise HTTPException(
            status_code=422,
            detail=f"Probe session status is '{session.status}', must be 'done'"
        )

    # ── Check for existing fingerprint ────────────────────────────────────────
    existing = (
        db.query(Fingerprint)
        .filter(Fingerprint.session_id == session_id)
        .first()
    )
    if existing:
        return existing   # idempotent: return existing fingerprint

    # ── Compute metrics ───────────────────────────────────────────────────────
    try:
        metrics = compute_fingerprint_metrics(db, session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fingerprint computation failed: {e}")

    # ── Store fingerprint ─────────────────────────────────────────────────────
    fingerprint = Fingerprint(
        session_id=session_id,
        model_id=session.model_id,
        **metrics,
    )
    db.add(fingerprint)
    db.commit()
    db.refresh(fingerprint)
    return fingerprint


def get_fingerprint(db: Session, fingerprint_id: str) -> Fingerprint:
    """Retrieve a fingerprint by ID."""
    fp = db.query(Fingerprint).filter(Fingerprint.id == fingerprint_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    return fp


def get_fingerprints_for_model(db: Session, model_id: str) -> list[Fingerprint]:
    """List all fingerprints for a model, newest first."""
    return (
        db.query(Fingerprint)
        .filter(Fingerprint.model_id == model_id)
        .order_by(Fingerprint.created_at.desc())
        .all()
    )


def compare(db: Session, fp_a_id: str, fp_b_id: str) -> dict:
    """
    Compare two fingerprints and return similarity metrics.

    Raises:
        404: If either fingerprint doesn't exist
        400: If comparing a fingerprint with itself
    """
    if fp_a_id == fp_b_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a fingerprint with itself"
        )

    fp_a = get_fingerprint(db, fp_a_id)
    fp_b = get_fingerprint(db, fp_b_id)
    return compare_fingerprints(fp_a, fp_b)


# In-memory cache for uncertainty regions
_uncertainty_regions_cache = {}

def get_uncertainty_regions(db: Session, fingerprint_id: str) -> list[dict]:
    """
    Detect uncertainty regions represented as feature-space bounding boxes.
    Uses a DecisionTreeRegressor and caches results in-memory.
    """
    if fingerprint_id in _uncertainty_regions_cache:
        return _uncertainty_regions_cache[fingerprint_id]

    fp = get_fingerprint(db, fingerprint_id)
    
    probe_results = (
        db.query(ProbeResult)
        .filter(ProbeResult.session_id == fp.session_id)
        .all()
    )
    if not probe_results:
        return []

    model = db.query(MLModel).filter(MLModel.id == fp.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    features = model.input_schema.get("features", [])
    if not features:
        return []

    # Prepare features and target
    X = np.array([r.input_vector for r in probe_results])
    y = np.array([r.confidence for r in probe_results])

    # Fit a decision tree to identify low confidence partitions
    reg = DecisionTreeRegressor(max_leaf_nodes=8, random_state=42)
    reg.fit(X, y)

    # Traverse tree leaves to extract bounding boxes
    tree_ = reg.tree_
    feature_names = [features[i]["name"] if i != _tree.TREE_UNDEFINED else None for i in tree_.feature]

    bounds_default = {}
    for f in features:
        name = f["name"]
        feat_min = f.get("min", float("-inf"))
        feat_max = f.get("max", float("inf"))
        if feat_min is None: feat_min = float("-inf")
        if feat_max is None: feat_max = float("inf")
        bounds_default[name] = [feat_min, feat_max]

    regions = []

    def traverse(node, current_bounds):
        if tree_.feature[node] != _tree.TREE_UNDEFINED:
            feat_name = feature_names[node]
            threshold = tree_.threshold[node]

            # Left child (feature <= threshold)
            left_bounds = {k: list(v) for k, v in current_bounds.items()}
            left_bounds[feat_name][1] = min(left_bounds[feat_name][1], float(threshold))
            traverse(tree_.children_left[node], left_bounds)

            # Right child (feature > threshold)
            right_bounds = {k: list(v) for k, v in current_bounds.items()}
            right_bounds[feat_name][0] = max(right_bounds[feat_name][0], float(threshold))
            traverse(tree_.children_right[node], right_bounds)
        else:
            regions.append((node, current_bounds))

    traverse(0, bounds_default)

    # Calculate statistics per leaf
    leaf_ids = reg.apply(X)
    evaluated_regions = []

    for node_id, bounds in regions:
        indices = np.where(leaf_ids == node_id)[0]
        if len(indices) == 0:
            continue
        mean_conf = float(np.mean(y[indices]))
        variance = float(np.var(y[indices]))
        density = float(len(indices) / len(X))

        cleaned_bounds = {}
        for k, v in bounds.items():
            lower = v[0] if v[0] != float("-inf") else None
            upper = v[1] if v[1] != float("inf") else None
            cleaned_bounds[k] = [lower, upper]

        evaluated_regions.append({
            "feature_bounds": cleaned_bounds,
            "mean_confidence": mean_conf,
            "sample_density": density,
            "variance": variance
        })

    # Rule: Mean Confidence < 0.65 AND Variance >= 75th percentile
    if evaluated_regions:
        variances = [r["variance"] for r in evaluated_regions]
        p75_var = np.percentile(variances, 75)
        
        matched_regions = [
            r for r in evaluated_regions
            if r["mean_confidence"] < 0.65 and r["variance"] >= p75_var
        ]
        
        if not matched_regions:
            # Fallback to the top 2 regions with lowest confidence
            sorted_by_conf = sorted(evaluated_regions, key=lambda x: x["mean_confidence"])
            matched_regions = sorted_by_conf[:2]
    else:
        matched_regions = []

    _uncertainty_regions_cache[fingerprint_id] = matched_regions
    return matched_regions

