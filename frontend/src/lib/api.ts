export interface FeatureSpec {
  name: string;
  type: string;
  min?: number;
  max?: number;
  categories?: string[];
}

export interface InputSchema {
  features: FeatureSpec[];
}

export interface ModelListItem {
  id: string;
  name: string;
  framework: string;
  status: string;
  created_at: string;
}

export interface ModelDetail {
  id: string;
  name: string;
  framework: string;
  file_path: string;
  input_schema: InputSchema;
  status: string;
  created_at: string;
  baseline_mean?: number | null;
  baseline_std?: number | null;
  signature?: string | null;
  architecture?: {
    layers?: Array<{
      name?: string;
      type: string;
      details?: string;
    }>;
    error?: string;
  } | null;
}

export interface ModelHealth {
  novelty_rate: number;
  drift_scores: Record<string, number>;
  active_alerts: number;
}

export interface Alert {
  id: string;
  model_id: string;
  alert_type: string;
  severity: 'warning' | 'critical';
  metadata: Record<string, any>;
  resolved_at: string | null;
  created_at: string;
}

export interface PredictionLog {
  id: string;
  model_id: string;
  input_features: Record<string, any>;
  predicted_class: number;
  output_class: number;
  confidence: number;
  raw_output: number[];
  latency_ms: number;
  faiss_distance: number | null;
  novelty_flag: boolean | null;
  created_at: string;
}

export interface Fingerprint {
  id: string;
  session_id: string;
  model_id: string;
  confidence_histogram: number[];
  entropy: number;
  uncertainty_rate: number;
  class_bias: number;
  mean_confidence: number;
  confidence_std: number;
  created_at: string;
}

export interface UncertaintyRegion {
  feature_bounds: Record<string, [number | null, number | null]>;
  mean_confidence: number;
  sample_density: number;
  variance: number;
}

export interface GlobalExplainability {
  model_id: string;
  feature_importance: Array<{
    feature: string;
    importance: number;
  }>;
}

export interface PredictionBreakdown {
  feature: string;
  value: any;
  contribution: number;
}

export interface PredictionExplanation {
  prediction_id: string;
  predicted_class: number;
  base_value: number;
  prediction_value: number;
  breakdown: PredictionBreakdown[];
}

// Global API Helper client using fetch
class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let message = `API Error: ${res.status}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          message = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch (_) {}
      throw new Error(message);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return res.json() as Promise<T>;
  }

  // Models
  listModels(): Promise<ModelListItem[]> {
    return this.request<ModelListItem[]>('/api/models');
  }

  getModelDetail(id: string): Promise<ModelDetail> {
    return this.request<ModelDetail>(`/api/models/${id}`);
  }

  deleteModel(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/models/${id}`, { method: 'DELETE' });
  }

  uploadModel(name: string, schema: string, file: File): Promise<ModelListItem> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('schema', schema);
    formData.append('file', file);

    return fetch('/api/models', {
      method: 'POST',
      body: formData,
    }).then(async res => {
      if (!res.ok) {
        let errText = "Upload failed";
        try {
          const errData = await res.json();
          if (errData.detail) errText = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
        } catch (_) {}
        throw new Error(errText);
      }
      return res.json();
    });
  }

  // Probing & Fingerprinting
  probeModel(modelId: string, nProbes: number = 100): Promise<{ id: string }> {
    return this.request<{ id: string }>(`/api/models/${modelId}/probe`, {
      method: 'POST',
      body: JSON.stringify({ n_probes: nProbes }),
    });
  }

  generateFingerprint(sessionId: string): Promise<{ id: string }> {
    return this.request<{ id: string }>(`/api/probes/${sessionId}/fingerprint`, {
      method: 'POST',
    });
  }


  // Health & Monitoring
  getModelHealth(id: string): Promise<ModelHealth> {
    return this.request<ModelHealth>(`/api/models/${id}/health`);
  }

  listAlerts(id: string): Promise<Alert[]> {
    return this.request<Alert[]>(`/api/models/${id}/alerts`);
  }

  resolveAlert(modelId: string, alertId: string): Promise<Alert> {
    return this.request<Alert>(`/api/models/${modelId}/alerts/${alertId}/resolve`, {
      method: 'POST',
    });
  }

  // Predictions Logs (Limit 100 for dashboard timeline)
  listPredictions(id: string, limit: number = 100): Promise<PredictionLog[]> {
    return this.request<PredictionLog[]>(`/api/models/${id}/predictions?limit=${limit}`);
  }

  // Fingerprinting
  listFingerprints(id: string): Promise<Fingerprint[]> {
    return this.request<Fingerprint[]>(`/api/models/${id}/fingerprints`);
  }

  getUncertaintyRegions(fingerprintId: string): Promise<UncertaintyRegion[]> {
    return this.request<UncertaintyRegion[]>(`/api/fingerprints/${fingerprintId}/uncertainty-regions`);
  }

  // Observability Additions
  getDatasetHealth(modelId: string): Promise<any> {
    return this.request<any>(`/api/models/${modelId}/dataset-health`);
  }

  getPerformanceProfile(modelId: string): Promise<any> {
    return this.request<any>(`/api/models/${modelId}/performance`);
  }

  getDriftAnalysis(modelId: string, nRecent: number = 100): Promise<any> {
    return this.request<any>(`/api/models/${modelId}/drift-analysis?n_recent=${nRecent}`);
  }

  getGlobalExplainability(modelId: string): Promise<GlobalExplainability> {
    return this.request<GlobalExplainability>(`/api/models/${modelId}/explainability/global`);
  }

  getPredictionExplanation(modelId: string, predictionId: string): Promise<PredictionExplanation> {
    return this.request<PredictionExplanation>(`/api/models/${modelId}/predictions/${predictionId}/explain`);
  }
}

export const api = new ApiClient();
