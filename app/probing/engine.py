import numpy as np
from sqlalchemy.orm import Session

from app.ml.loader import load_model
from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession
from app.probing.sampler import generate_probe_inputs


def run_probe_session(db: Session, session: ProbeSession, file_path: str, schema: dict) -> None:
    """Run an LHS probe sweep against a model, store the results, and mark the session done."""
    wrapper = load_model(file_path)
    probe_inputs = generate_probe_inputs(schema, session.n_probes)

    results = []
    confidences = []
    class_counts: dict[int, int] = {}
    activations = []

    for input_vector in probe_inputs:
        input_array = np.array([input_vector])
        prediction, activation = wrapper.predict_with_activations(input_array)
        activations.append(activation[0])

        results.append(ProbeResult(
            session_id=session.id,
            input_vector=input_vector,
            predicted_class=prediction.predicted_class,
            confidence=prediction.confidence,
            raw_output=prediction.raw_output,
        ))

        confidences.append(prediction.confidence)
        class_counts[prediction.predicted_class] = (
            class_counts.get(prediction.predicted_class, 0) + 1
        )

    db.bulk_save_objects(results)

    if activations:
        from app.monitoring.faiss_indexer import build_and_save_index
        activation_matrix = np.vstack(activations)
        build_and_save_index(db, session.model_id, activation_matrix)

    confidence_array = np.array(confidences)
    mean_conf = float(np.mean(confidence_array))
    std_conf = float(np.std(confidence_array))
    dominant_class = max(class_counts, key=class_counts.get)
    class_distribution = {str(k): v for k, v in class_counts.items()}

    session.status = "done"
    session.mean_confidence = mean_conf
    session.confidence_std = std_conf
    session.dominant_class = dominant_class
    session.class_distribution = class_distribution

    db.commit()
