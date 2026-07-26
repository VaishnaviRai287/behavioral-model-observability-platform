from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.drift_event import DriftEvent


def process_latent_novelty(db: Session, model_id: str, distance: float, metadata: dict) -> None:
    """
    Handle latent space novelty detection. Creates a new alert if no active novelty alert exists.
    """
    active_alert = (
        db.query(Alert)
        .filter(
            Alert.model_id == model_id,
            Alert.alert_type == "LATENT_NOVELTY",
            Alert.resolved_at.is_(None),
        )
        .first()
    )
    if active_alert:
        return

    alert = Alert(
        model_id=model_id,
        alert_type="LATENT_NOVELTY",
        severity="critical",
        alert_metadata={"distance": distance, **metadata},
    )
    db.add(alert)
    db.commit()


def process_feature_drift(db: Session, model_id: str, drift_events: list[DriftEvent]) -> None:
    """
    Handle feature statistical drift breaches. Creates or updates alerts based on severity bounds.
    """
    # Filter for features that breached warning or critical bounds
    breached_events = [e for e in drift_events if e.severity in ("warning", "critical")]
    if not breached_events:
        return

    # Determine maximum severity among breached features
    max_severity = "warning"
    if any(e.severity == "critical" for e in breached_events):
        max_severity = "critical"

    drift_details = [
        {
            "feature_name": e.feature_name,
            "ks_statistic": e.ks_statistic,
            "psi_score": e.psi_score,
            "severity": e.severity,
        }
        for e in breached_events
    ]

    active_alert = (
        db.query(Alert)
        .filter(
            Alert.model_id == model_id,
            Alert.alert_type == "FEATURE_DRIFT",
            Alert.resolved_at.is_(None),
        )
        .first()
    )

    if active_alert:
        # Update metadata details and propagate severity upwards if it escalated
        meta = dict(active_alert.alert_metadata)
        meta["drifted_features"] = drift_details
        active_alert.alert_metadata = meta
        active_alert.severity = max_severity
        db.commit()
        return

    alert = Alert(
        model_id=model_id,
        alert_type="FEATURE_DRIFT",
        severity=max_severity,
        alert_metadata={"drifted_features": drift_details},
    )
    db.add(alert)
    db.commit()
