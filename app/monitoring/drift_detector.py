import numpy as np
from scipy.stats import ks_2samp
from sqlalchemy.orm import Session

from app.models.drift_event import DriftEvent
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog
from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession


def compute_psi(expected: np.ndarray, actual: np.ndarray, num_bins: int = 10) -> float:
    """
    Calculate the Population Stability Index (PSI) between expected and actual distributions.
    """
    percentiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(expected, percentiles)
    bin_edges = np.unique(bin_edges)

    # If the range of values is zero, binning cannot be performed (zero variance)
    if len(bin_edges) < 2:
        return 0.0

    # Slightly adjust outer boundaries to capture edge values
    bin_edges[0] -= 1e-5
    bin_edges[-1] += 1e-5

    # Compute frequency counts in each bin
    expected_counts, _ = np.histogram(expected, bins=bin_edges)
    actual_counts, _ = np.histogram(actual, bins=bin_edges)

    expected_props = expected_counts / len(expected)
    actual_props = actual_counts / len(actual)

    # Apply Laplace smoothing to avoid division by zero or infinite logarithm values
    eps = 1e-4
    expected_props = np.where(expected_props == 0, eps, expected_props)
    actual_props = np.where(actual_props == 0, eps, actual_props)

    # Normalize proportions to sum to 1.0
    expected_props /= expected_props.sum()
    actual_props /= actual_props.sum()

    # Calculate final PSI
    psi = np.sum((actual_props - expected_props) * np.log(actual_props / expected_props))
    return float(psi)


def detect_drift(db: Session, model_id: str, n_recent: int = 100) -> list[DriftEvent]:
    """
    Analyze recent predictions for a model against baseline distributions and log drift events.
    """
    # 1. Fetch latest successful probe session (baseline)
    session = (
        db.query(ProbeSession)
        .filter(ProbeSession.model_id == model_id, ProbeSession.status == "done")
        .order_by(ProbeSession.created_at.desc())
        .first()
    )
    if not session:
        return []

    # 2. Get baseline input vectors
    probe_results = db.query(ProbeResult).filter(ProbeResult.session_id == session.id).all()
    if not probe_results:
        return []
    baseline_vectors = np.array([pr.input_vector for pr in probe_results])

    # 3. Get recent prediction logs
    prediction_logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(n_recent)
        .all()
    )
    if not prediction_logs:
        return []

    # Oldest and newest timestamps in the sample represent window bounds
    sorted_logs = sorted(prediction_logs, key=lambda x: x.created_at)
    window_start = sorted_logs[0].created_at
    window_end = sorted_logs[-1].created_at

    live_vectors = np.array([log.input_vector for log in prediction_logs])

    # 4. Fetch feature definitions from model schema
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        return []
    features = model.input_schema.get("features", [])

    drift_events = []

    # Statistical Thresholds
    PSI_WARNING = 0.1
    PSI_CRITICAL = 0.25
    KS_WARNING = 0.15
    KS_CRITICAL = 0.30

    for i, feature in enumerate(features):
        feature_name = feature["name"]
        expected_feat = baseline_vectors[:, i]
        actual_feat = live_vectors[:, i]

        # Calculate Kolmogorov-Smirnov statistic
        ks_res = ks_2samp(expected_feat, actual_feat)
        ks_stat = float(ks_res.statistic)

        # Calculate Population Stability Index
        psi_score = compute_psi(expected_feat, actual_feat)



        # Determine severity level
        severity = "none"
        if ks_stat >= KS_CRITICAL or psi_score >= PSI_CRITICAL:
            severity = "critical"
        elif ks_stat >= KS_WARNING or psi_score >= PSI_WARNING:
            severity = "warning"

        event = DriftEvent(
            model_id=model_id,
            feature_name=feature_name,
            ks_statistic=ks_stat,
            psi_score=psi_score,
            severity=severity,
            window_start=window_start,
            window_end=window_end,
        )
        db.add(event)
        drift_events.append(event)

    db.commit()
    return drift_events
