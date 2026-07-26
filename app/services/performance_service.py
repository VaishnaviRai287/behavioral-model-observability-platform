import numpy as np
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog

def analyze_performance_profile(db: Session, model_id: str) -> dict:
    """Compute latency, throughput, memory, and CPU stats from recent prediction logs."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(1000)
        .all()
    )

    if not logs:
        return {
            "latency": {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0},
            "throughput": {"rps_1m": 0.0, "rps_5m": 0.0, "rps_overall": 0.0},
            "memory": {"mean_mb": 0.0, "peak_mb": 0.0},
            "cpu": {"mean_pct": 0.0, "peak_pct": 0.0},
            "total_predictions": 0
        }

    total_predictions = len(logs)

    latencies = [log.latency_ms for log in logs]
    lat_mean = float(np.mean(latencies))
    lat_min = float(np.min(latencies))
    lat_max = float(np.max(latencies))
    lat_p50 = float(np.percentile(latencies, 50))
    lat_p95 = float(np.percentile(latencies, 95))
    lat_p99 = float(np.percentile(latencies, 99))

    cpu_utils = [log.cpu_utilization for log in logs if log.cpu_utilization is not None]
    mem_usages = [log.memory_mb for log in logs if log.memory_mb is not None]

    cpu_mean = float(np.mean(cpu_utils)) if cpu_utils else 0.0
    cpu_peak = float(np.max(cpu_utils)) if cpu_utils else 0.0

    mem_mean = float(np.mean(mem_usages)) if mem_usages else 0.0
    mem_peak = float(np.max(mem_usages)) if mem_usages else 0.0

    now = datetime.now(timezone.utc)

    one_min_ago = now - timedelta(minutes=1)
    logs_1m = db.query(PredictionLog).filter(
        PredictionLog.model_id == model_id,
        PredictionLog.created_at >= one_min_ago
    ).count()
    rps_1m = logs_1m / 60.0

    # 5-minute window
    five_min_ago = now - timedelta(minutes=5)
    logs_5m = db.query(PredictionLog).filter(
        PredictionLog.model_id == model_id,
        PredictionLog.created_at >= five_min_ago
    ).count()
    rps_5m = logs_5m / 300.0

    # Overall window (time delta between first and last log)
    sorted_logs = sorted(logs, key=lambda x: x.created_at)
    time_diff = (sorted_logs[-1].created_at - sorted_logs[0].created_at).total_seconds()
    if time_diff > 1:
        rps_overall = len(logs) / time_diff
    else:
        rps_overall = rps_1m

    return {
        "latency": {
            "mean": round(lat_mean, 3),
            "p50": round(lat_p50, 3),
            "p95": round(lat_p95, 3),
            "p99": round(lat_p99, 3),
            "min": round(lat_min, 3),
            "max": round(lat_max, 3)
        },
        "throughput": {
            "rps_1m": round(rps_1m, 3),
            "rps_5m": round(rps_5m, 3),
            "rps_overall": round(rps_overall, 3)
        },
        "memory": {
            "mean_mb": round(mem_mean, 2),
            "peak_mb": round(mem_peak, 2)
        },
        "cpu": {
            "mean_pct": round(cpu_mean, 2),
            "peak_pct": round(cpu_peak, 2)
        },
        "total_predictions": total_predictions
    }
