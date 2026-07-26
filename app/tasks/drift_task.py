from app.database import SessionLocal
from app.monitoring.alert_engine import process_feature_drift
from app.monitoring.drift_detector import detect_drift
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.drift_task.run_drift_check")
def run_drift_check(model_id: str) -> None:
    """
    Runs the KS/PSI drift sweep for a model and raises alerts on breach.

    Executed off the request path (in a Celery worker) so a prediction's
    response is never blocked by drift computation. Opens its own DB session
    since the FastAPI request session that triggered this is already closed
    by the time the worker picks up the task.
    """
    db = SessionLocal()
    try:
        drift_events = detect_drift(db, model_id, n_recent=100)
        process_feature_drift(db, model_id, drift_events)
    finally:
        db.close()
