import { useState, useEffect } from "react";
import {
  api,
  ModelListItem,
  ModelDetail,
  ModelHealth,
  Alert,
  PredictionLog,
  Fingerprint,
  UncertaintyRegion,
} from "../lib/api";

// 1. Models List Polling (Slower: 10s)
export function useModels() {
  const [data, setData] = useState<ModelListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.listModels();
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load models");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 10000); // 10s

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return { data, loading, error };
}

// 2. Model Detail Polling (Slower: 10s)
export function useModelDetail(modelId: string) {
  const [data, setData] = useState<ModelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!modelId) return;
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.getModelDetail(modelId);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load model details");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 10000); // 10s

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [modelId]);

  return { data, loading, error };
}

// 3. Model Health Polling (Fast-changing: 5s)
export function useModelHealth(modelId: string) {
  const [data, setData] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refetch = () => setRefreshTrigger((prev) => prev + 1);

  useEffect(() => {
    if (!modelId) return;
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.getModelHealth(modelId);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load model health stats");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 5000); // 5s

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [modelId, refreshTrigger]);

  return { data, loading, error, refetch };
}

// 4. Model Alerts Polling (Fast-changing: 5s)
export function useModelAlerts(modelId: string) {
  const [data, setData] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refetch = () => setRefreshTrigger((prev) => prev + 1);

  useEffect(() => {
    if (!modelId) return;
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.listAlerts(modelId);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load active alerts");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 5000); // 5s

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [modelId, refreshTrigger]);

  return { data, setData, loading, error, refetch };
}

// 5. Prediction Logs Polling (Fast-changing: 5s, last 100 predictions)
export function useModelPredictions(modelId: string) {
  const [data, setData] = useState<PredictionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refetch = () => setRefreshTrigger((prev) => prev + 1);

  useEffect(() => {
    if (!modelId) return;
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.listPredictions(modelId, 100);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load prediction events");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 5000); // 5s

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [modelId, refreshTrigger]);

  return { data, loading, error, refetch };
}

// 6. Fingerprints (Static after probing: load once)
export function useModelFingerprints(modelId: string) {
  const [data, setData] = useState<Fingerprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!modelId) return;
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.listFingerprints(modelId);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load fingerprints");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
  }, [modelId]);

  return { data, loading, error };
}

// 7. Uncertainty Regions (Static after fingerprint: load once)
export function useUncertaintyRegions(fingerprintId: string | undefined) {
  const [data, setData] = useState<UncertaintyRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fingerprintId) return;
    let active = true;
    const fetch = async () => {
      try {
        const res = await api.getUncertaintyRegions(fingerprintId);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to load uncertainty regions");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
  }, [fingerprintId]);

  return { data, loading, error };
}
