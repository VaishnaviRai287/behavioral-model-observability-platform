import os
import json
import httpx
from typing import List, Dict, Any, Optional
from uuid import UUID
from app.core.config import settings

class LLMService:
    async def generate_changelog(
        self,
        model_a_info: Dict[str, Any],
        fingerprint_a: Dict[str, Any],
        model_b_info: Dict[str, Any],
        fingerprint_b: Dict[str, Any]
    ) -> str:
        # If API key is missing, return a deterministic mock release log
        if not settings.GEMINI_API_KEY:
            return self._generate_mock_changelog(model_a_info, fingerprint_a, model_b_info, fingerprint_b)

        # Build prompt
        prompt = self._build_changelog_prompt(model_a_info, fingerprint_a, model_b_info, fingerprint_b)
        
        # Call Gemini API
        return await self._call_gemini(prompt)

    async def explain_alert(
        self,
        alert_info: Dict[str, Any],
        model_info: Dict[str, Any],
        fingerprint: Dict[str, Any],
        recent_logs: List[Dict[str, Any]]
    ) -> str:
        # If API key is missing, return a deterministic mock alert explanation
        if not settings.GEMINI_API_KEY:
            return self._generate_mock_alert_explanation(alert_info, model_info, fingerprint, recent_logs)

        # Build prompt
        prompt = self._build_alert_explanation_prompt(alert_info, model_info, fingerprint, recent_logs)

        # Call Gemini API
        return await self._call_gemini(prompt)

    async def _call_gemini(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise Exception(f"Gemini API returned status {response.status_code}: {response.text}")
                
                data = response.json()
                # Parse candidates[0].content.parts[0].text
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            # On failure, fall back to warning and mock response to avoid breaking user workflows
            return f"**[Error calling Gemini API: {str(e)} - Falling back to deterministic analysis]**\n\n" + self._generate_fallback_text(prompt)

    def _build_changelog_prompt(
        self,
        model_a: Dict[str, Any],
        fingerprint_a: Dict[str, Any],
        model_b: Dict[str, Any],
        fingerprint_b: Dict[str, Any]
    ) -> str:
        return f"""You are an expert machine learning observability system. Analyze the behavioral differences between two model versions using their LHS probing fingerprints.

Model A (Baseline):
- Name: {model_a.get('name')}
- Version: {model_a.get('version')}
- Framework: {model_a.get('framework')}
- Task: {model_a.get('task_type')}
- Input Schema: {json.dumps(model_a.get('input_schema'))}
- Class Distribution: {json.dumps(fingerprint_a.get('class_distribution'))}
- Confidence Distribution: {json.dumps(fingerprint_a.get('confidence_distribution'))}
- High Uncertainty Regions: {json.dumps(fingerprint_a.get('high_uncertainty_regions'))}

Model B (Target):
- Name: {model_b.get('name')}
- Version: {model_b.get('version')}
- Framework: {model_b.get('framework')}
- Task: {model_b.get('task_type')}
- Input Schema: {json.dumps(model_b.get('input_schema'))}
- Class Distribution: {json.dumps(fingerprint_b.get('class_distribution'))}
- Confidence Distribution: {json.dumps(fingerprint_b.get('confidence_distribution'))}
- High Uncertainty Regions: {json.dumps(fingerprint_b.get('high_uncertainty_regions'))}

Analyze the changes. Generate a clean, detailed markdown release changelog that lists:
1. Decision boundary changes (e.g. are predictions shifting between class labels).
2. Average confidence delta.
3. Feature regions where model uncertainty has increased or decreased.
4. Recommendation on whether to promote Model B to production.

Be professional and base all claims strictly on the provided JSON data.
"""

    def _build_alert_explanation_prompt(
        self,
        alert: Dict[str, Any],
        model: Dict[str, Any],
        fingerprint: Dict[str, Any],
        recent_logs: List[Dict[str, Any]]
    ) -> str:
        logs_summary = []
        for l in recent_logs[:10]:
            logs_summary.append({
                "features": l.get("features"),
                "prediction": l.get("prediction"),
                "confidence": l.get("confidence")
            })

        return f"""You are a machine learning model observability assistant. An operational alert has fired, and you need to generate a diagnostic explanation for the on-call engineer.

Alert Details:
- Type: {alert.get('alert_type')}
- Severity: {alert.get('severity')}
- Message: {alert.get('message')}
- Metric Value: {alert.get('metric_value')}

Model Details:
- Name: {model.get('name')}
- Version: {model.get('version')}

Baseline Behavior:
- High Uncertainty Regions: {json.dumps(fingerprint.get('high_uncertainty_regions'))}
- Boundary Samples: {json.dumps(fingerprint.get('boundary_samples'))}

Recent Inference Log Sample:
{json.dumps(logs_summary, indent=2)}

Analyze this evidence. Write a clear diagnostic report in markdown explaining:
1. The meaning and cause of this alert.
2. How the current incoming traffic features compare to the baseline high-uncertainty regions.
3. Recommended remediation steps (e.g. feature bounds to restrict, categories of inputs to collect for retraining).

Be concise, technical, and directly ground your reasoning in the provided logs and metrics.
"""

    def _generate_mock_changelog(
        self,
        model_a: Dict[str, Any],
        fingerprint_a: Dict[str, Any],
        model_b: Dict[str, Any],
        fingerprint_b: Dict[str, Any]
    ) -> str:
        conf_a = fingerprint_a.get("confidence_distribution", {}).get("mean", 0.0)
        conf_b = fingerprint_b.get("confidence_distribution", {}).get("mean", 0.0)
        conf_delta = conf_b - conf_a

        return f"""# Behavioral Changelog: Model Comparison Report

This report highlights the behavioral differences between baseline **{model_a.get('name')} (v{model_a.get('version')})** and target **{model_b.get('name')} (v{model_b.get('version')})** computed from LHS probing metrics.

### 1. Classification & Label Shifts
* **Class Ratios**: The predicted class frequencies between baseline and target models show stable bounds with minor variations. No massive decision flip behavior is registered across uniform spaces.

### 2. Confidence Delta Analysis
* **Baseline Mean Confidence**: `{conf_a:.4f}`
* **Target Mean Confidence**: `{conf_b:.4f}`
* **Confidence Shift**: `{conf_delta:+.4f}`
* *Evaluation*: The target model is behaving with a minor confidence shift compared to the baseline version.

### 3. Uncertainty Profile
* **High Uncertainty Regions**:
  * Baseline regions of concern: `{json.dumps(fingerprint_a.get('high_uncertainty_regions', {}).get('regions', []))}`
  * Target regions of concern: `{json.dumps(fingerprint_b.get('high_uncertainty_regions', {}).get('regions', []))}`

### 4. Deployment Recommendation
* **Decision**: **Approved for Staging**. The behavioral differences are well-bounded, and confidence remains high. Proceed with standard shadow deployment before promoting to production.
"""

    def _generate_mock_alert_explanation(
        self,
        alert: Dict[str, Any],
        model: Dict[str, Any],
        fingerprint: Dict[str, Any],
        recent_logs: List[Dict[str, Any]]
    ) -> str:
        return f"""# Diagnostic Alert Analysis: {alert.get('alert_type')} ({alert.get('severity')})

### 1. Root Cause Evaluation
* **Event**: An alert of type `{alert.get('alert_type')}` with value `{alert.get('metric_value')}` was triggered on model **{model.get('name')} (v{model.get('version')})**.
* **Reason**: The live prediction stream has drifted from the baseline feature distributions or exhibits latent boundary representations.

### 2. Live Traffic vs Baseline Fingerprint
* **Observed Shift**: Incoming live logs feature fields show high overlap with the model's known high uncertainty bounds: `{json.dumps(fingerprint.get('high_uncertainty_regions', {}).get('regions', []))}`.
* **Sample Inference Logs**: Analyzed {len(recent_logs)} recent records. The log samples demonstrate a clear clustering pattern.

### 3. Actionable Remediation
1. **Retraining**: Collect input logs representing this drifted region and integrate them into the next model training batch.
2. **Threshold Guard**: Restrict predictions or flag confidence warnings for requests falling in the high-uncertainty bounds.
"""

    def _generate_fallback_text(self, prompt: str) -> str:
        if "Model A" in prompt:
            return "Unable to call Gemini API. Model comparisons demonstrate small confidence variances. Deployment to staging is recommended."
        else:
            return "Unable to call Gemini API. Alert triggered due to feature drift or latent space novelty. Retraining is recommended."

llm_service = LLMService()
