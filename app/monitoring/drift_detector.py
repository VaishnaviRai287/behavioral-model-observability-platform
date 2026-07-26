import numpy as np
from collections import Counter
from scipy.stats import ks_2samp
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.drift_event import DriftEvent
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog
from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession

PSI_WARNING = 0.1
PSI_CRITICAL = 0.25
KS_WARNING = 0.15
KS_CRITICAL = 0.30


def compute_psi(expected: np.ndarray, actual: np.ndarray, num_bins: int = 10) -> float:
    """Compute the Population Stability Index between an expected and actual distribution."""
    percentiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(expected, percentiles)
    bin_edges = np.unique(bin_edges)

    if len(bin_edges) < 2:
        # Zero variance in the expected distribution — binning is meaningless.
        return 0.0

    bin_edges[0] -= 1e-5
    bin_edges[-1] += 1e-5

    expected_counts, _ = np.histogram(expected, bins=bin_edges)
    actual_counts, _ = np.histogram(actual, bins=bin_edges)

    expected_props = expected_counts / len(expected)
    actual_props = actual_counts / len(actual)

    # Laplace smoothing so empty bins don't produce log(0) or divide-by-zero.
    eps = 1e-4
    expected_props = np.where(expected_props == 0, eps, expected_props)
    actual_props = np.where(actual_props == 0, eps, actual_props)
    expected_props /= expected_props.sum()
    actual_props /= actual_props.sum()

    psi = np.sum((actual_props - expected_props) * np.log(actual_props / expected_props))
    return float(psi)


def _severity(ks_stat: float, psi_score: float) -> str:
    if ks_stat >= KS_CRITICAL or psi_score >= PSI_CRITICAL:
        return "critical"
    if ks_stat >= KS_WARNING or psi_score >= PSI_WARNING:
        return "warning"
    return "none"


def detect_drift(db: Session, model_id: str, n_recent: int = 100) -> list[DriftEvent]:
    """Compare recent predictions against the baseline probe session and log a DriftEvent per feature."""
    session = (
        db.query(ProbeSession)
        .filter(ProbeSession.model_id == model_id, ProbeSession.status == "done")
        .order_by(ProbeSession.created_at.desc())
        .first()
    )
    if not session:
        return []

    probe_results = db.query(ProbeResult).filter(ProbeResult.session_id == session.id).all()
    if not probe_results:
        return []
    baseline_vectors = np.array([pr.input_vector for pr in probe_results])

    prediction_logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(n_recent)
        .all()
    )
    if not prediction_logs:
        return []

    sorted_logs = sorted(prediction_logs, key=lambda x: x.created_at)
    window_start = sorted_logs[0].created_at
    window_end = sorted_logs[-1].created_at

    live_vectors = np.array([log.input_vector for log in prediction_logs])

    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        return []
    features = model.input_schema.get("features", [])

    drift_events = []

    for i, feature in enumerate(features):
        feature_name = feature["name"]
        expected_feat = baseline_vectors[:, i]
        actual_feat = live_vectors[:, i]

        ks_stat = float(ks_2samp(expected_feat, actual_feat).statistic)
        psi_score = compute_psi(expected_feat, actual_feat)

        event = DriftEvent(
            model_id=model_id,
            feature_name=feature_name,
            ks_statistic=ks_stat,
            psi_score=psi_score,
            severity=_severity(ks_stat, psi_score),
            window_start=window_start,
            window_end=window_end,
        )
        db.add(event)
        drift_events.append(event)

    db.commit()
    return drift_events


def _empty_drift_analysis() -> dict:
    return {
        "feature_drift": [],
        "target_drift": {
            "class_drift": {"psi_score": 0.0, "verdict": "stable", "baseline": {}, "production": {}},
            "confidence_drift": {"ks_statistic": 0.0, "psi_score": 0.0, "verdict": "stable", "baseline": [], "production": []}
        }
    }


def analyze_drift_and_distributions(db: Session, model_id: str, n_recent: int = 100) -> dict:
    """Compute per-feature and target drift, including baseline-vs-production histograms for the dashboard."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    features = model.input_schema.get("features", [])

    session = (
        db.query(ProbeSession)
        .filter(ProbeSession.model_id == model_id, ProbeSession.status == "done")
        .order_by(ProbeSession.created_at.desc())
        .first()
    )

    prediction_logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(n_recent)
        .all()
    )

    if not session or not prediction_logs:
        return _empty_drift_analysis()

    probe_results = db.query(ProbeResult).filter(ProbeResult.session_id == session.id).all()
    if not probe_results:
        return _empty_drift_analysis()

    baseline_vectors = np.array([pr.input_vector for pr in probe_results])
    live_vectors = np.array([log.input_vector for log in prediction_logs if log.input_vector])

    if len(live_vectors) == 0:
        return _empty_drift_analysis()

    feature_drifts = []
    for idx, feature in enumerate(features):
        name = feature["name"]
        expected = baseline_vectors[:, idx]
        actual = live_vectors[:, idx]

        ks_stat = float(ks_2samp(expected, actual).statistic)
        psi = compute_psi(expected, actual)

        percentiles = np.linspace(0, 100, 11)
        bin_edges = np.percentile(expected, percentiles)
        bin_edges = np.unique(bin_edges)

        if len(bin_edges) >= 2:
            bin_edges[0] -= 1e-5
            bin_edges[-1] += 1e-5

            exp_counts, _ = np.histogram(expected, bins=bin_edges)
            act_counts, _ = np.histogram(actual, bins=bin_edges)

            exp_props = (exp_counts / len(expected)).tolist()
            act_props = (act_counts / len(actual)).tolist()
            bin_labels = [f"{float(bin_edges[i]):.2f} - {float(bin_edges[i+1]):.2f}" for i in range(len(bin_edges)-1)]
        else:
            exp_props = []
            act_props = []
            bin_labels = []

        verdict = _severity(ks_stat, psi)
        feature_drifts.append({
            "name": name,
            "ks_statistic": round(ks_stat, 4),
            "psi_score": round(psi, 4),
            "verdict": "stable" if verdict == "none" else verdict,
            "distribution": {
                "labels": bin_labels,
                "baseline": exp_props,
                "production": act_props
            }
        })

    expected_conf = np.array([pr.confidence for pr in probe_results])
    actual_conf = np.array([log.confidence for log in prediction_logs])

    conf_ks = float(ks_2samp(expected_conf, actual_conf).statistic)
    conf_psi = compute_psi(expected_conf, actual_conf)
    conf_verdict = _severity(conf_ks, conf_psi)
    conf_verdict = "stable" if conf_verdict == "none" else conf_verdict

    conf_bins = np.linspace(0.0, 1.0, 11)
    exp_conf_counts, _ = np.histogram(expected_conf, bins=conf_bins)
    act_conf_counts, _ = np.histogram(actual_conf, bins=conf_bins)
    exp_conf_props = (exp_conf_counts / len(expected_conf)).tolist()
    act_conf_props = (act_conf_counts / len(actual_conf)).tolist()
    conf_labels = [f"{conf_bins[i]:.1f} - {conf_bins[i+1]:.1f}" for i in range(len(conf_bins)-1)]

    expected_classes = [pr.predicted_class for pr in probe_results]
    actual_classes = [log.predicted_class for log in prediction_logs]
    unique_classes = sorted(list(set(expected_classes + actual_classes)))

    exp_class_counts = Counter(expected_classes)
    act_class_counts = Counter(actual_classes)

    exp_class_props = {str(c): (exp_class_counts[c] / len(expected_classes)) for c in unique_classes}
    act_class_props = {str(c): (act_class_counts[c] / len(actual_classes)) for c in unique_classes}

    # PSI on class proportions, same smoothing approach as compute_psi.
    exp_classes_arr = np.array([exp_class_counts[c] for c in unique_classes])
    act_classes_arr = np.array([act_class_counts[c] for c in unique_classes])
    exp_class_props_arr = exp_classes_arr / len(expected_classes)
    act_class_props_arr = act_classes_arr / len(actual_classes)
    eps = 1e-4
    exp_class_props_arr = np.where(exp_class_props_arr == 0, eps, exp_class_props_arr)
    act_class_props_arr = np.where(act_class_props_arr == 0, eps, act_class_props_arr)
    exp_class_props_arr /= exp_class_props_arr.sum()
    act_class_props_arr /= act_class_props_arr.sum()
    class_psi = float(np.sum((act_class_props_arr - exp_class_props_arr) * np.log(act_class_props_arr / exp_class_props_arr)))

    class_verdict = "stable"
    if class_psi >= PSI_CRITICAL:
        class_verdict = "critical"
    elif class_psi >= PSI_WARNING:
        class_verdict = "warning"

    return {
        "feature_drift": feature_drifts,
        "target_drift": {
            "class_drift": {
                "psi_score": round(class_psi, 4),
                "verdict": class_verdict,
                "baseline": {str(k): round(v, 4) for k, v in exp_class_props.items()},
                "production": {str(k): round(v, 4) for k, v in act_class_props.items()}
            },
            "confidence_drift": {
                "ks_statistic": round(conf_ks, 4),
                "psi_score": round(conf_psi, 4),
                "verdict": conf_verdict,
                "distribution": {
                    "labels": conf_labels,
                    "baseline": exp_conf_props,
                    "production": act_conf_props
                }
            }
        }
    }
