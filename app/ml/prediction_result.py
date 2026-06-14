from dataclasses import dataclass


@dataclass
class PredictionResult:
    """
    The unified output of any model prediction, regardless of framework.

    All ModelWrapper implementations must return this type.
    """
    predicted_class: int        # The winning class index (0, 1, 2, ...)
    confidence: float           # Probability of the predicted class (0.0 to 1.0)
    raw_output: list[float]     # Full probability distribution across all classes
