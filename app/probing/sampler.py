import numpy as np
from scipy.stats.qmc import LatinHypercube, scale


def generate_probe_inputs(schema: dict, n_probes: int) -> list[list[float]]:
    """Generate n_probes synthetic input vectors via Latin Hypercube Sampling over the schema's feature bounds."""
    features = schema["features"]
    n_features = len(features)

    lower_bounds = []
    upper_bounds = []

    for feature in features:
        feat_min = feature.get("min")
        feat_max = feature.get("max")

        # Features without declared bounds get a sensible default range.
        if feat_min is None:
            feat_min = -3.0
        if feat_max is None:
            feat_max = 3.0

        lower_bounds.append(float(feat_min))
        upper_bounds.append(float(feat_max))

    sampler = LatinHypercube(d=n_features, seed=42)
    unit_samples = sampler.random(n=n_probes)
    scaled_samples = scale(unit_samples, l_bounds=lower_bounds, u_bounds=upper_bounds)

    return scaled_samples.tolist()
