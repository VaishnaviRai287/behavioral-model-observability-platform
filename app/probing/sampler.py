import numpy as np
from scipy.stats.qmc import LatinHypercube, scale


def generate_probe_inputs(schema: dict, n_probes: int) -> list[list[float]]:
    """
    Generate n_probes synthetic input vectors using Latin Hypercube Sampling.

    Args:
        schema: The model's input_schema dict from the database.
                Expected format:
                {
                    "features": [
                        {"name": "x1", "type": "float", "min": 0, "max": 1},
                        {"name": "x2", "type": "float", "min": -5, "max": 5},
                    ]
                }
        n_probes: Number of synthetic input vectors to generate.

    Returns:
        List of n_probes input vectors, each a list of floats.
        Shape: (n_probes, n_features)
    """
    features = schema["features"]
    n_features = len(features)

    # Determine bounds for each feature
    lower_bounds = []
    upper_bounds = []

    for feature in features:
        feat_min = feature.get("min")
        feat_max = feature.get("max")

        # If no bounds declared, use sensible defaults
        if feat_min is None:
            feat_min = -3.0
        if feat_max is None:
            feat_max = 3.0

        lower_bounds.append(float(feat_min))
        upper_bounds.append(float(feat_max))

    # Create LHS sampler for n_features dimensions
    sampler = LatinHypercube(d=n_features, seed=42)

    # Generate n_probes samples in [0, 1]^n_features
    unit_samples = sampler.random(n=n_probes)

    # Scale from [0, 1] to [feature_min, feature_max]
    scaled_samples = scale(unit_samples, l_bounds=lower_bounds, u_bounds=upper_bounds)

    # Convert to plain Python lists (not numpy arrays) for JSON storage
    return scaled_samples.tolist()
