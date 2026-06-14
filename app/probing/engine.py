import numpy as np
from sqlalchemy.orm import Session

from app.ml.loader import load_model
from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession
from app.probing.sampler import generate_probe_inputs


def run_probe_session(db: Session, session: ProbeSession, file_path: str, schema: dict) -> None:
    """
    Execute a complete probing run and store all results.

    This function:
    1. Loads the model via the unified wrapper
    2. Generates synthetic inputs via LHS
    3. Runs predict() on each input
    4. Stores individual ProbeResult rows
    5. Computes summary statistics
    6. Updates the ProbeSession with final stats

    Args:
        db:        Active database session
        session:   The ProbeSession ORM record (already created, status="running")
        file_path: Path to the model file on disk
        schema:    The model's input_schema dict
    """

    # ── Step 1: Load the model ────────────────────────────────────────────────
    wrapper = load_model(file_path)

    # ── Step 2: Generate probe inputs ─────────────────────────────────────────
    probe_inputs = generate_probe_inputs(schema, session.n_probes)

    # ── Step 3: Run predictions ───────────────────────────────────────────────
    results = []
    confidences = []
    class_counts: dict[int, int] = {}

    for input_vector in probe_inputs:
        input_array = np.array([input_vector])   # shape (1, n_features)
        prediction = wrapper.predict(input_array)

        # Record individual result
        probe_result = ProbeResult(
            session_id=session.id,
            input_vector=input_vector,
            predicted_class=prediction.predicted_class,
            confidence=prediction.confidence,
            raw_output=prediction.raw_output,
        )
        results.append(probe_result)

        # Accumulate stats
        confidences.append(prediction.confidence)
        class_counts[prediction.predicted_class] = (
            class_counts.get(prediction.predicted_class, 0) + 1
        )

    # ── Step 4: Bulk insert probe results ────────────────────────────────────
    db.bulk_save_objects(results)

    # ── Step 5: Compute summary statistics ───────────────────────────────────
    confidence_array = np.array(confidences)
    mean_conf = float(np.mean(confidence_array))
    std_conf = float(np.std(confidence_array))
    dominant_class = max(class_counts, key=class_counts.get)

    # Convert int keys to str for JSON storage
    class_distribution = {str(k): v for k, v in class_counts.items()}

    # ── Step 6: Update session record ────────────────────────────────────────
    session.status = "done"
    session.mean_confidence = mean_conf
    session.confidence_std = std_conf
    session.dominant_class = dominant_class
    session.class_distribution = class_distribution

    db.commit()
