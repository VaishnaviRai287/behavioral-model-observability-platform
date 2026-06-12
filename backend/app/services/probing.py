import numpy as np
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from scipy.stats import qmc

from app.crud.model_registry import model_registry_crud
from app.crud.fingerprint import fingerprint_crud
from app.services.prediction import prediction_service
from app.models.fingerprint import BehavioralFingerprint

class ProbingEngine:
    async def run_probing_and_fingerprint(
        self, db: AsyncSession, model_id: UUID, num_samples: int = 1000
    ) -> BehavioralFingerprint:
        # 1. Fetch Model from DB registry
        model = await model_registry_crud.get(db, model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID '{model_id}' is not registered."
            )

        features = model.input_schema.get("features", [])
        if not features:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model input schema must contain features to run probing."
            )

        # 2. Generate Latin Hypercube Samples in [0, 1]^D
        input_dim = len(features)
        sampler = qmc.LatinHypercube(d=input_dim)
        raw_samples = sampler.random(n=num_samples)

        # Scale LHS raw samples to defined features bounds
        probes = []
        for i in range(num_samples):
            record = {}
            for j, feature in enumerate(features):
                name = feature["name"]
                f_type = feature.get("type", "float")
                min_val = feature.get("min", 0.0)
                max_val = feature.get("max", 1.0)

                scaled = min_val + raw_samples[i, j] * (max_val - min_val)
                if f_type == "int":
                    scaled = int(round(scaled))
                record[name] = scaled
            probes.append(record)

        # 3. Execute inferences in batch
        prediction_out = await prediction_service.predict(db=db, model_id=model_id, raw_inputs=probes)
        predictions = prediction_out["predictions"]
        probabilities = prediction_out["probabilities"]

        # 4. Compute distributions and metrics
        # Class distribution
        unique_classes, counts = np.unique(predictions, return_counts=True)
        class_dist = {}
        for c, count in zip(unique_classes, counts):
            class_dist[str(c)] = {
                "count": int(count),
                "ratio": float(count) / num_samples
            }

        # Confidence distribution
        confidences = []
        if probabilities is not None:
            confidences = [max(prob) for prob in probabilities]
        else:
            confidences = [1.0] * num_samples # Default confidence if no probabilities available

        confidences_np = np.array(confidences)
        conf_dist = {
            "mean": float(np.mean(confidences_np)),
            "std": float(np.std(confidences_np)),
            "p10": float(np.percentile(confidences_np, 10)),
            "p25": float(np.percentile(confidences_np, 25)),
            "p50": float(np.percentile(confidences_np, 50)),
            "p75": float(np.percentile(confidences_np, 75)),
            "p90": float(np.percentile(confidences_np, 90)),
        }

        # Shannon Entropy for uncertainty profiling
        entropy = []
        if probabilities is not None:
            for prob in probabilities:
                prob_np = np.array(prob) + 1e-9 # avoid log(0)
                prob_np = prob_np / np.sum(prob_np)
                ent = -np.sum(prob_np * np.log2(prob_np))
                entropy.append(ent)
        else:
            entropy = [0.0] * num_samples

        entropy_np = np.array(entropy)

        # High uncertainty regions (top 10% highest entropy samples)
        high_unc_regions = []
        threshold = np.percentile(entropy_np, 90)
        high_unc_indices = np.where(entropy_np >= threshold)[0]
        if len(high_unc_indices) > 0:
            for j, feature in enumerate(features):
                name = feature["name"]
                feat_vals = [probes[idx][name] for idx in high_unc_indices]
                high_unc_regions.append({
                    "feature": name,
                    "min": float(np.min(feat_vals)),
                    "max": float(np.max(feat_vals)),
                    "mean": float(np.mean(feat_vals))
                })

        # Boundary samples (5 samples closest to classification boundary threshold)
        boundary_indices = np.argsort(confidences_np)[:5]
        boundary_samples = []
        for idx in boundary_indices:
            boundary_samples.append({
                "inputs": probes[idx],
                "prediction": int(predictions[idx]),
                "confidence": float(confidences_np[idx])
            })

        # 5. Save and return fingerprint baseline
        return await fingerprint_crud.create(
            db=db,
            model_id=model_id,
            num_samples=num_samples,
            class_distribution=class_dist,
            confidence_distribution=conf_dist,
            high_uncertainty_regions={"regions": high_unc_regions},
            boundary_samples={"samples": boundary_samples}
        )

probing_engine = ProbingEngine()
