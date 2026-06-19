"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  useModelDetail,
  useModelHealth,
  useModelAlerts,
  useModelPredictions,
  useModelFingerprints,
} from "@/hooks/useModelHealth";
import { api } from "@/lib/api";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  ArrowLeft,
  Activity,
  AlertOctagon,
  Percent,
  Compass,
  CheckCircle,
  Clock,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  Play,
  BarChart2,
  Heart,
  Cpu,
  Database,
} from "lucide-react";

export default function ModelDashboard() {
  const params = useParams();
  const router = useRouter();
  const modelId = params.id as string;

  // Polling Hooks
  const { data: model, loading: modelLoading, error: modelError } = useModelDetail(modelId);
  const { data: health, loading: healthLoading, error: healthError, refetch: refetchHealth } = useModelHealth(modelId);
  const { data: alerts, setData: setAlerts, error: alertsError, refetch: refetchAlerts } = useModelAlerts(modelId);
  const { data: predictions, loading: predLoading, error: predError, refetch: refetchPredictions } = useModelPredictions(modelId);
  const { data: fingerprints } = useModelFingerprints(modelId);

  const [resolvingId, setResolvingId] = useState<string | null>(null);

  // Observability Enhancement States
  const [activeTab, setActiveTab] = useState<"monitoring" | "graph" | "health" | "performance" | "drift_analysis">("monitoring");
  const [datasetHealth, setDatasetHealth] = useState<any>(null);
  const [datasetHealthLoading, setDatasetHealthLoading] = useState(false);
  const [performanceProfile, setPerformanceProfile] = useState<any>(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [driftAnalysis, setDriftAnalysis] = useState<any>(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [selectedLayer, setSelectedLayer] = useState<any>(null);
  const [selectedDriftFeature, setSelectedDriftFeature] = useState<string>("");

  // Lazy loading API data based on active tab
  React.useEffect(() => {
    if (activeTab === "health" && !datasetHealth) {
      setDatasetHealthLoading(true);
      api.getDatasetHealth(modelId)
        .then(setDatasetHealth)
        .catch(console.error)
        .finally(() => setDatasetHealthLoading(false));
    }
    if (activeTab === "performance" && !performanceProfile) {
      setPerformanceLoading(true);
      api.getPerformanceProfile(modelId)
        .then(setPerformanceProfile)
        .catch(console.error)
        .finally(() => setPerformanceLoading(false));
    }
    if (activeTab === "drift_analysis" && !driftAnalysis) {
      setDriftLoading(true);
      api.getDriftAnalysis(modelId)
        .then(setDriftAnalysis)
        .catch(console.error)
        .finally(() => setDriftLoading(false));
    }
  }, [activeTab, modelId, datasetHealth, performanceProfile, driftAnalysis]);

  // Simulation States
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulatedCount, setSimulatedCount] = useState(0);
  const [simTotal, setSimTotal] = useState(75);
  const [simStatus, setSimStatus] = useState("");

  const handleSimulateTraffic = async () => {
    if (isSimulating || !model) return;
    setIsSimulating(true);
    setSimulatedCount(0);
    setSimTotal(75);
    setSimStatus("Starting traffic...");

    const featuresSpec = model.input_schema?.features || [];
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    try {
      // Step 1: Normal predictions (30 count)
      for (let i = 0; i < 30; i++) {
        setSimStatus(`Streaming Normal Traffic (${i + 1}/30)`);
        
        const payloadFeatures: Record<string, number> = {};
        featuresSpec.forEach((f: any) => {
          const minVal = f.min !== undefined && f.min !== null ? f.min : 0.0;
          const maxVal = f.max !== undefined && f.max !== null ? f.max : 1.0;
          // Normal is bottom 30% of range
          payloadFeatures[f.name] = Number((minVal + Math.random() * (maxVal - minVal) * 0.3).toFixed(3));
        });

        await fetch(`/api/models/${modelId}/predict`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ features: payloadFeatures }),
        });

        setSimulatedCount(i + 1);
        refetchPredictions();
        refetchHealth();
        refetchAlerts();
        
        await delay(120);
      }

      // Step 2: Drifted predictions (45 count)
      for (let i = 0; i < 45; i++) {
        setSimStatus(`Injecting Drift Traffic (${i + 1}/45)`);

        const payloadFeatures: Record<string, number> = {};
        featuresSpec.forEach((f: any) => {
          const minVal = f.min !== undefined && f.min !== null ? f.min : 0.0;
          const maxVal = f.max !== undefined && f.max !== null ? f.max : 1.0;
          // Drifted is top 30% of range (0.7 - 0.98)
          payloadFeatures[f.name] = Number((minVal + (0.7 + Math.random() * 0.28) * (maxVal - minVal)).toFixed(3));
        });

        await fetch(`/api/models/${modelId}/predict`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ features: payloadFeatures }),
        });

        setSimulatedCount(30 + i + 1);
        refetchPredictions();
        refetchHealth();
        refetchAlerts();

        await delay(120);
      }

      setSimStatus("Simulation complete!");
    } catch (err: any) {
      setSimStatus(`Error: ${err.message || "Failed to stream"}`);
    } finally {
      setIsSimulating(false);
      refetchPredictions();
      refetchHealth();
      refetchAlerts();
    }
  };

  // Compute Novelty Thresholds
  const baselineMean = model?.baseline_mean ?? 0.0;
  const baselineStd = model?.baseline_std ?? 0.0;
  const threshold = baselineMean + 3 * baselineStd;

  const handleResolveAlert = async (alertId: string) => {
    setResolvingId(alertId);
    try {
      await api.resolveAlert(modelId, alertId);
      // Remove resolved alert from local state
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (err: any) {
      alert(`Failed to resolve alert: ${err.message}`);
    } finally {
      setResolvingId(null);
    }
  };

  if (modelLoading || healthLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-slate-800 rounded" />
        <div className="h-10 w-64 bg-slate-800 rounded" />
        <div className="h-24 bg-darkCard border border-darkBorder rounded-2xl" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 bg-darkCard border border-darkBorder rounded-2xl" />
          <div className="h-80 bg-darkCard border border-darkBorder rounded-2xl" />
        </div>
      </div>
    );
  }

  if (modelError || !model) {
    return (
      <div className="glass-panel max-w-lg mx-auto p-8 text-center rounded-2xl border-rose-500/20 mt-12">
        <div className="p-3 w-fit mx-auto rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-4">
          <AlertTriangle className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Model Not Found</h2>
        <p className="text-slate-400 text-sm mb-6">
          The model ID "{modelId}" does not exist or has been deleted.
        </p>
        <button
          onClick={() => router.push("/")}
          className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-medium transition-colors text-sm"
        >
          Back to Registry
        </button>
      </div>
    );
  }

  // format prediction events for novelty chart
  const timelineData = [...predictions]
    .reverse() // Display oldest to newest left-to-right
    .map((p) => ({
      created_at: new Date(p.created_at).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      faiss_distance: p.faiss_distance ?? 0.0,
      novelty_flag: p.novelty_flag ?? false,
    }));

  // format feature drift events for bar chart
  const featureDriftData = health
    ? Object.entries(health.drift_scores).map(([name, score]) => ({
        name,
        score,
      }))
    : [];

  const totalPredictionsCount = predictions.length;
  const activeAlertsCount = alerts.filter((a) => !a.resolved_at).length;
  const noveltyRatePercent = health ? (health.novelty_rate * 100).toFixed(1) : "0.0";

  // Custom Dot component for Novelty Timeline
  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (cx === undefined || cy === undefined) return null;
    const isNovel = payload.novelty_flag || (payload.faiss_distance > threshold && threshold > 0);
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isNovel ? 4.5 : 3}
        fill={isNovel ? "#F43F5E" : "#0D9488"}
        stroke={isNovel ? "#F43F5E" : "#0D9488"}
        className={isNovel ? "pulse-glow-rose" : ""}
      />
    );
  };

  // ── Sub-renders for Observability Tabs ─────────────────────────────────────
  const renderArchitectureGraph = () => {
    const layers = model.architecture?.layers || [];
    if (layers.length === 0) {
      return (
        <div className="py-12 text-center max-w-sm mx-auto">
          <div className="p-3 w-fit mx-auto rounded-full bg-slate-800 text-slate-500 mb-3 border border-darkBorder">
            <Compass className="h-5.5 w-5.5" />
          </div>
          <h4 className="text-sm font-semibold text-white mb-0.5">No Architecture Graph Available</h4>
          <p className="text-xs text-slate-400">
            Ensure the model was uploaded in a supported framework (PyTorch or Keras) to compile the graph.
          </p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SVG Canvas */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl flex flex-col items-center max-h-[600px] overflow-y-auto min-h-[400px]">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-6 self-start">Model Topology Graph</h4>
          <div className="relative flex flex-col items-center w-full py-4 select-none">
            {layers.map((layer: any, idx: number) => {
              const isSelected = selectedLayer?.name === layer.name;
              return (
                <React.Fragment key={idx}>
                  {/* Layer Node */}
                  <div
                    onClick={() => setSelectedLayer(layer)}
                    className={`w-64 p-3.5 rounded-xl border cursor-pointer transition-all duration-200 text-center flex flex-col justify-center items-center relative group
                      ${isSelected 
                        ? "bg-teal-500/15 border-teal-500 shadow-lg shadow-teal-500/15 scale-[1.03]" 
                        : "bg-slate-900 border-darkBorder hover:border-teal-500/50 hover:bg-slate-850 hover:scale-[1.01]"
                      }`}
                  >
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider font-mono">
                      Layer {idx}
                    </span>
                    <span className="text-xs font-bold text-white mt-1 break-all truncate max-w-full">
                      {layer.name || `layer_${idx}`}
                    </span>
                    <span className="text-[10px] mt-1.5 px-2 py-0.5 rounded bg-slate-950 text-teal-400 font-mono font-semibold border border-darkBorder/40">
                      {layer.type}
                    </span>
                  </div>

                  {/* Flow Arrow */}
                  {idx < layers.length - 1 && (
                    <div className="flex flex-col items-center my-3.5">
                      <div className="w-0.5 h-6 bg-gradient-to-b from-teal-500/40 to-teal-500/10" />
                      <div className="w-1.5 h-1.5 rounded-full bg-teal-500/40 -mt-1.5 animate-pulse" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Inspector Sidebar */}
        <div className="glass-panel p-5 rounded-2xl space-y-4 h-fit">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">Layer Inspector</h4>
          {selectedLayer ? (
            <div className="space-y-4">
              <div className="space-y-1">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Name</span>
                <p className="text-sm font-bold text-white break-all">{selectedLayer.name}</p>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Class Type</span>
                <div>
                  <span className="inline-block text-xs bg-teal-500/10 border border-teal-500/30 px-2.5 py-0.5 rounded text-teal-400 font-mono font-bold">
                    {selectedLayer.type}
                  </span>
                </div>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Configuration details</span>
                <pre className="text-[11px] text-slate-300 font-mono bg-slate-950 p-3 rounded border border-darkBorder overflow-x-auto whitespace-pre-wrap break-all">
                  {selectedLayer.details || "No parameter details extracted."}
                </pre>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">
              Click on a layer in the graph to inspect its parameters.
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderDatasetHealth = () => {
    if (datasetHealthLoading) {
      return (
        <div className="h-64 flex items-center justify-center text-teal-400 animate-pulse font-semibold">
          Analyzing dataset health...
        </div>
      );
    }
    if (!datasetHealth) return null;

    const classChartData = Object.entries(datasetHealth.class_imbalance.counts).map(([name, count]) => ({
      name: `Class ${name}`,
      count,
      percentage: datasetHealth.class_imbalance.percentages[name] || 0
    }));

    const outliersChartData = Object.entries(datasetHealth.outliers.by_feature).map(([name, count]) => ({
      name,
      count
    }));

    return (
      <div className="space-y-6">
        {/* Health Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Missing Values</span>
            <p className="text-2xl font-bold text-white mt-1.5">{datasetHealth.missing_values.percentage}%</p>
            <p className="text-[10px] text-slate-500 mt-1">{datasetHealth.missing_values.total_missing} null values found</p>
          </div>
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Duplicate Inputs</span>
            <p className="text-2xl font-bold text-white mt-1.5">{datasetHealth.duplicates.percentage}%</p>
            <p className="text-[10px] text-slate-500 mt-1">{datasetHealth.duplicates.duplicate_count} duplicates found</p>
          </div>
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Outliers Rate</span>
            <p className="text-2xl font-bold text-white mt-1.5">{datasetHealth.outliers.percentage}%</p>
            <p className="text-[10px] text-slate-500 mt-1">{datasetHealth.outliers.total_outliers} outliers detected</p>
          </div>
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Class Entropy</span>
            <p className="text-2xl font-bold text-white mt-1.5">{datasetHealth.class_imbalance.entropy}</p>
            <p className="text-[10px] text-slate-500 mt-1">Shannon scale (higher = balanced)</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Class Imbalance Chart */}
          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Class Balance Distribution</h3>
              <p className="text-[11px] text-slate-400">Proportions of classes predicted in production logs</p>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={classChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" vertical={false} />
                  <XAxis dataKey="name" stroke="#475569" fontSize={10} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={10} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#161B2E", borderColor: "#1F293D" }} />
                  <Bar dataKey="count" fill="#0D9488" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Outliers By Feature */}
          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Outliers Count per Feature</h3>
              <p className="text-[11px] text-slate-400">Total values falling outside standard 1.5 * IQR bounds</p>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={outliersChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" horizontal={false} />
                  <XAxis type="number" stroke="#475569" fontSize={10} tickLine={false} />
                  <YAxis type="category" dataKey="name" stroke="#475569" fontSize={10} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#161B2E", borderColor: "#1F293D" }} />
                  <Bar dataKey="count" fill="#F43F5E" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderPerformanceProfile = () => {
    if (performanceLoading) {
      return (
        <div className="h-64 flex items-center justify-center text-teal-400 animate-pulse font-semibold">
          Loading performance metrics...
        </div>
      );
    }
    if (!performanceProfile) return null;

    const latData = [
      { name: "Min", val: performanceProfile.latency.min },
      { name: "P50", val: performanceProfile.latency.p50 },
      { name: "Mean", val: performanceProfile.latency.mean },
      { name: "P95", val: performanceProfile.latency.p95 },
      { name: "P99", val: performanceProfile.latency.p99 },
      { name: "Max", val: performanceProfile.latency.max }
    ];

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Avg Throughput</span>
            <p className="text-2xl font-bold text-teal-400 mt-1.5">{performanceProfile.throughput.rps_1m} RPS</p>
            <p className="text-[10px] text-slate-500 mt-1">Last 1 minute average</p>
          </div>
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">P95 Latency</span>
            <p className="text-2xl font-bold text-white mt-1.5">{performanceProfile.latency.p95} ms</p>
            <p className="text-[10px] text-slate-500 mt-1">95% of queries execute faster</p>
          </div>
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Mean CPU Util</span>
            <p className="text-2xl font-bold text-white mt-1.5">{performanceProfile.cpu.mean_pct}%</p>
            <p className="text-[10px] text-slate-500 mt-1">Peak: {performanceProfile.cpu.peak_pct}%</p>
          </div>
          <div className="glass-panel p-4.5 rounded-2xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Memory RSS</span>
            <p className="text-2xl font-bold text-white mt-1.5">{performanceProfile.memory.mean_mb} MB</p>
            <p className="text-[10px] text-slate-500 mt-1">Peak: {performanceProfile.memory.peak_mb} MB</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Latency Percentiles */}
          <div className="lg:col-span-2 glass-panel p-5 rounded-2xl space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Latency Percentiles & Boundaries</h3>
              <p className="text-[11px] text-slate-400">Execution time profile computed across recent production requests</p>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" vertical={false} />
                  <XAxis dataKey="name" stroke="#475569" fontSize={10} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={10} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#161B2E", borderColor: "#1F293D" }} />
                  <Bar dataKey="val" fill="#0D9488" radius={[4, 4, 0, 0]}>
                    {latData.map((entry, index) => {
                      let fill = "#0D9488";
                      if (entry.name === "P95") fill = "#F59E0B";
                      if (entry.name === "P99" || entry.name === "Max") fill = "#F43F5E";
                      return <Cell key={`cell-${index}`} fill={fill} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* CPU & Memory Health */}
          <div className="glass-panel p-5 rounded-2xl space-y-6 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Inference Server Resources</h3>
              <p className="text-[11px] text-slate-400">Live compute constraints recorded during execution</p>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-400">CPU Load</span>
                  <span className="text-white">{performanceProfile.cpu.mean_pct}%</span>
                </div>
                <div className="h-2 bg-slate-900 rounded-full overflow-hidden border border-darkBorder/40">
                  <div 
                    className="bg-teal-500 h-full transition-all duration-300" 
                    style={{ width: `${Math.min(performanceProfile.cpu.mean_pct, 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-500">Max limit: 100% of single core allocation</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-400">Memory Allocation</span>
                  <span className="text-white">{performanceProfile.memory.mean_mb} MB</span>
                </div>
                <div className="h-2 bg-slate-900 rounded-full overflow-hidden border border-darkBorder/40">
                  <div 
                    className="bg-cyan-500 h-full transition-all duration-300" 
                    style={{ width: `${Math.min((performanceProfile.memory.mean_mb / 512) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-500">Peak consumption: {performanceProfile.memory.peak_mb} MB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderDriftAnalysis = () => {
    if (driftLoading) {
      return (
        <div className="h-64 flex items-center justify-center text-teal-400 animate-pulse font-semibold">
          Loading drift analysis...
        </div>
      );
    }
    if (!driftAnalysis) return null;

    if (!selectedDriftFeature && driftAnalysis.feature_drift.length > 0) {
      setSelectedDriftFeature(driftAnalysis.feature_drift[0].name);
    }

    const currentFeatureDrift = driftAnalysis.feature_drift.find((fd: any) => fd.name === selectedDriftFeature);
    
    const featureDistChartData = currentFeatureDrift?.distribution.labels.map((label: string, idx: number) => ({
      name: label,
      baseline: (currentFeatureDrift.distribution.baseline[idx] * 100).toFixed(1),
      production: (currentFeatureDrift.distribution.production[idx] * 100).toFixed(1)
    })) || [];

    const confDistChartData = driftAnalysis.target_drift.confidence_drift.distribution.labels.map((label: string, idx: number) => ({
      name: label,
      baseline: (driftAnalysis.target_drift.confidence_drift.distribution.baseline[idx] * 100).toFixed(1),
      production: (driftAnalysis.target_drift.confidence_drift.distribution.production[idx] * 100).toFixed(1)
    }));

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 font-bold uppercase">Target Classification Drift</span>
              <h4 className="text-base font-bold text-white">Predictions Output Distribution (Target Drift)</h4>
            </div>
            <div className="flex items-baseline justify-between mt-4">
              <div>
                <span className="text-[10px] text-slate-400 block">Population Stability Index (PSI)</span>
                <span className="text-2xl font-bold text-white">{driftAnalysis.target_drift.class_drift.psi_score}</span>
              </div>
              <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase border
                ${driftAnalysis.target_drift.class_drift.verdict === "critical" 
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-400" 
                  : driftAnalysis.target_drift.class_drift.verdict === "warning"
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                    : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                }`}>
                {driftAnalysis.target_drift.class_drift.verdict}
              </span>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 font-bold uppercase">Confidence Score Drift</span>
              <h4 className="text-base font-bold text-white">Confidence Score Distribution Drift</h4>
            </div>
            <div className="flex items-baseline justify-between mt-4">
              <div className="flex gap-6">
                <div>
                  <span className="text-[10px] text-slate-400 block">KS Statistic</span>
                  <span className="text-2xl font-bold text-white">{driftAnalysis.target_drift.confidence_drift.ks_statistic}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">PSI Score</span>
                  <span className="text-2xl font-bold text-white">{driftAnalysis.target_drift.confidence_drift.psi_score}</span>
                </div>
              </div>
              <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase border
                ${driftAnalysis.target_drift.confidence_drift.verdict === "critical" 
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-400" 
                  : driftAnalysis.target_drift.confidence_drift.verdict === "warning"
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                    : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                }`}>
                {driftAnalysis.target_drift.confidence_drift.verdict}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Feature Distribution Shift</h3>
                <p className="text-[11px] text-slate-400">Baseline (Probing) vs Production (Live logs) histograms</p>
              </div>
              
              <select
                value={selectedDriftFeature}
                onChange={(e) => setSelectedDriftFeature(e.target.value)}
                className="bg-slate-900 border border-darkBorder rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-teal-500/50"
              >
                {driftAnalysis.feature_drift.map((fd: any) => (
                  <option key={fd.name} value={fd.name}>{fd.name}</option>
                ))}
              </select>
            </div>

            {currentFeatureDrift && (
              <div className="flex gap-6 bg-slate-950/40 border border-darkBorder/40 p-3 rounded-xl text-xs">
                <div>
                  <span className="text-[10px] text-slate-500">KS Statistic:</span>
                  <strong className="text-white ml-1.5">{currentFeatureDrift.ks_statistic}</strong>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">PSI Score:</span>
                  <strong className="text-white ml-1.5">{currentFeatureDrift.psi_score}</strong>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Verdict:</span>
                  <strong className={`ml-1.5 uppercase ${currentFeatureDrift.verdict === 'critical' ? 'text-rose-400' : currentFeatureDrift.verdict === 'warning' ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {currentFeatureDrift.verdict}
                  </strong>
                </div>
              </div>
            )}

            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={featureDistChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" vertical={false} />
                  <XAxis dataKey="name" stroke="#475569" fontSize={9} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={9} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#161B2E", borderColor: "#1F293D" }} />
                  <Line type="monotone" dataKey="baseline" name="Training (LHS Baseline)" stroke="#0D9488" strokeWidth={1.5} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="production" name="Production (Live Traffic)" stroke="#F43F5E" strokeWidth={1.5} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Confidence Distribution Shift</h3>
              <p className="text-[11px] text-slate-400">Baseline (Probing) vs Production (Live logs) histograms</p>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={confDistChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" vertical={false} />
                  <XAxis dataKey="name" stroke="#475569" fontSize={9} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={9} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#161B2E", borderColor: "#1F293D" }} />
                  <Line type="monotone" dataKey="baseline" name="Training (LHS Baseline)" stroke="#0D9488" strokeWidth={1.5} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="production" name="Production (Live Traffic)" stroke="#F43F5E" strokeWidth={1.5} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Back button & title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors w-fit"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Registry
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-extrabold tracking-tight text-gradient">
              {model.name}
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-darkBorder uppercase">
              {model.framework}
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono select-all">
            ID: {model.id}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Simulation Controls */}
          {isSimulating ? (
            <div className="flex items-center gap-3 px-4.5 py-2.5 bg-slate-900 border border-darkBorder rounded-xl text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              </span>
              <span className="text-slate-300 font-semibold font-mono">{simStatus}</span>
              <div className="w-20 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="bg-teal-500 h-1.5 transition-all duration-150" 
                  style={{ width: `${(simulatedCount / simTotal) * 100}%` }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={handleSimulateTraffic}
              className="flex items-center gap-2 px-4.5 py-2.5 bg-rose-500 hover:bg-rose-600 text-white rounded-xl text-sm font-semibold transition-all hover:scale-[1.02] shadow-lg shadow-rose-500/15"
            >
              <Play className="h-4 w-4 fill-current text-white" />
              <span>Simulate Drift Traffic</span>
            </button>
          )}

          {/* Link to Fingerprint Page */}
          {fingerprints && fingerprints.length > 0 && (
            <Link
              href={`/models/${model.id}/fingerprint`}
              className="flex items-center gap-1.5 px-4.5 py-2.5 bg-teal-500/10 border border-teal-500/30 text-teal-400 hover:bg-teal-500/20 hover:border-teal-500/50 rounded-xl text-sm font-medium transition-all"
            >
              <span>View Behavioral Fingerprint</span>
              <ChevronRight className="h-4 w-4" />
            </Link>
          )}
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Mean Confidence */}
        <div className="glass-panel p-4.5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold tracking-wider uppercase">
              Mean Confidence
            </span>
            <Compass className="h-4.5 w-4.5 text-teal-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-1.5">
            {predictions.length > 0
              ? (predictions.reduce((acc, curr) => acc + curr.confidence, 0) / predictions.length).toFixed(3)
              : "N/A"}
          </p>
        </div>

        {/* Novelty Rate % */}
        <div className="glass-panel p-4.5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold tracking-wider uppercase">
              Novelty Rate
            </span>
            <Percent className="h-4.5 w-4.5 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-1.5">
            {noveltyRatePercent}%
          </p>
        </div>

        {/* Active Alerts count */}
        <div className="glass-panel p-4.5 rounded-2xl border-rose-500/15">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold tracking-wider uppercase">
              Active Alerts
            </span>
            <AlertOctagon className="h-4.5 w-4.5 text-rose-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-1.5">
            {activeAlertsCount}
          </p>
        </div>

        {/* Total Predictions */}
        <div className="glass-panel p-4.5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold tracking-wider uppercase">
              Total Predictions
            </span>
            <Activity className="h-4.5 w-4.5 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-1.5">
            {totalPredictionsCount}
          </p>
        </div>
      </div>

      {/* Tabs Switcher Bar */}
      <div className="flex border-b border-darkBorder/60 gap-1 overflow-x-auto pb-px">
        {[
          { id: "monitoring", label: "Monitoring Dashboard", icon: Activity },
          { id: "graph", label: "Architecture Graph", icon: Compass },
          { id: "health", label: "Dataset Health", icon: Database },
          { id: "performance", label: "Inference Performance", icon: Cpu },
          { id: "drift_analysis", label: "Drift Analysis", icon: AlertTriangle },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-5 py-3 border-b-2 font-semibold text-sm transition-all duration-200 whitespace-nowrap -mb-px
                ${isActive
                  ? "border-teal-500 text-teal-400 bg-teal-500/5"
                  : "border-transparent text-slate-400 hover:text-white hover:bg-slate-800/30"
                }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? "text-teal-400" : "text-slate-400"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Conditionally Render Tab Contents */}
      {activeTab === "monitoring" && (
        <div className="space-y-6">
          {/* Observability Charts Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Panel 1: Novelty Score Timeline */}
            <div className="glass-panel p-5 rounded-2xl space-y-4">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Novelty Score Timeline
                </h3>
                <p className="text-[11px] text-slate-400">
                  Penultimate layer FAISS activation distance (last 100 inferences)
                </p>
              </div>

              <div className="h-64 w-full">
                {timelineData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" vertical={false} />
                      <XAxis
                        dataKey="created_at"
                        stroke="#475569"
                        fontSize={9}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis stroke="#475569" fontSize={9} tickLine={false} axisLine={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#161B2E",
                          borderColor: "#1F293D",
                          borderRadius: "8px",
                          fontSize: "11px",
                          color: "#f1f5f9",
                        }}
                      />
                      {/* Baseline distance reference line */}
                      <ReferenceLine
                        y={baselineMean}
                        stroke="#64748B"
                        strokeWidth={1}
                        label={{
                          value: "baseline mean",
                          fill: "#94A3B8",
                          fontSize: 9,
                          position: "insideBottomRight",
                        }}
                      />
                      {/* 3-sigma novelty threshold reference line */}
                      <ReferenceLine
                        y={threshold}
                        stroke="#F43F5E"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        label={{
                          value: "novelty limit (mean+3σ)",
                          fill: "#F43F5E",
                          fontSize: 9,
                          position: "insideTopRight",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="faiss_distance"
                        stroke="#0D9488"
                        strokeWidth={1.5}
                        dot={<CustomDot />}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center p-6 bg-slate-900/30 rounded-xl border border-darkBorder/40">
                    <Clock className="h-8 w-8 text-slate-600 mb-2" />
                    <span className="text-xs text-slate-400 font-medium">No inference events yet</span>
                    <span className="text-[10px] text-slate-500 mt-1 max-w-[240px]">
                      Send live predictions via the API to plot the novelty distance timeline.
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Panel 2: Drift Scores per Feature */}
            <div className="glass-panel p-5 rounded-2xl space-y-4">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Feature Drift (KS Statistic)
                </h3>
                <p className="text-[11px] text-slate-400">
                  Kolmogorov-Smirnov distance on inference distributions against baseline
                </p>
              </div>

              <div className="h-64 w-full">
                {featureDriftData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      layout="vertical"
                      data={featureDriftData}
                      margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" horizontal={false} />
                      <XAxis
                        type="number"
                        domain={[0, 1.0]}
                        stroke="#475569"
                        fontSize={9}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        stroke="#475569"
                        fontSize={9}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#161B2E",
                          borderColor: "#1F293D",
                          borderRadius: "8px",
                          fontSize: "11px",
                          color: "#f1f5f9",
                        }}
                      />
                      <ReferenceLine
                        x={0.1}
                        stroke="#F59E0B"
                        strokeDasharray="3 3"
                        label={{
                          value: "Warning (0.1)",
                          fill: "#F59E0B",
                          fontSize: 8,
                          position: "insideTopRight",
                        }}
                      />
                      <ReferenceLine
                        x={0.2}
                        stroke="#F43F5E"
                        strokeDasharray="3 3"
                        label={{
                          value: "Critical (0.2)",
                          fill: "#F43F5E",
                          fontSize: 8,
                          position: "insideTopRight",
                        }}
                      />
                      <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                        {featureDriftData.map((entry, index) => {
                          let fill = "#0D9488"; // normal
                          if (entry.score >= 0.2) {
                            fill = "#F43F5E"; // critical
                          } else if (entry.score >= 0.1) {
                            fill = "#F59E0B"; // warning
                          }
                          return <Cell key={`cell-${index}`} fill={fill} />;
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center p-6 bg-slate-900/30 rounded-xl border border-darkBorder/40">
                    <Compass className="h-8 w-8 text-slate-600 mb-2" />
                    <span className="text-xs text-slate-400 font-medium">No drift evaluations recorded</span>
                    <span className="text-[10px] text-slate-500 mt-1 max-w-[240px]">
                      Drift is evaluated automatically every 50 predictions.
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Active Alerts Panel */}
          <div className="glass-panel rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-darkBorder">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Active Observability Alerts
              </h3>
              <p className="text-[11px] text-slate-400">
                Current active breaches of statistical drift or novelty thresholds
              </p>
            </div>

            {alerts.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-darkBorder">
                  <thead className="bg-slate-900/40">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Alert Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Severity
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Trigger Details
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Timestamp
                      </th>
                      <th className="relative px-6 py-3">
                        <span className="sr-only">Resolve</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-darkBorder">
                    {alerts.map((alert) => (
                      <tr key={alert.id} className="hover:bg-darkHover/20">
                        <td className="px-6 py-4.5 whitespace-nowrap">
                          <span className="font-mono text-xs font-semibold text-white bg-slate-900 border border-darkBorder px-2.5 py-1 rounded">
                            {alert.alert_type}
                          </span>
                        </td>
                        <td className="px-6 py-4.5 whitespace-nowrap">
                          {alert.severity === "critical" ? (
                            <span className="inline-flex items-center gap-1.5 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded font-semibold">
                              <AlertOctagon className="h-3 w-3" />
                              Critical
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded font-semibold">
                              <AlertTriangle className="h-3 w-3" />
                              Warning
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4.5 text-xs text-slate-300">
                          {alert.alert_type === "LATENT_NOVELTY" ? (
                            <span>
                              Penultimate layer distance exceeded threshold: distance{" "}
                              <strong className="text-rose-400">
                                {alert.metadata.distance !== undefined && alert.metadata.distance !== null 
                                  ? Number(alert.metadata.distance).toFixed(4) 
                                  : "N/A"}
                              </strong>
                            </span>
                          ) : (
                            <div className="space-y-1">
                              {alert.metadata.drifted_features && alert.metadata.drifted_features.length > 0 ? (
                                alert.metadata.drifted_features.map((df: any, idx: number) => (
                                  <div key={idx} className="flex flex-wrap items-center gap-1">
                                    <span>Feature</span>
                                    <strong className="text-amber-400">{df.feature_name}</strong>
                                    <span>drifted:</span>
                                    <span>KS =</span>
                                    <strong className="text-rose-400 font-mono">
                                      {df.ks_statistic !== undefined && df.ks_statistic !== null 
                                        ? Number(df.ks_statistic).toFixed(4) 
                                        : "N/A"}
                                    </strong>
                                    <span className="text-slate-500 text-[10px]">(threshold: {df.severity === 'critical' ? '0.30' : '0.15'})</span>
                                    <span className="text-slate-500 mx-0.5">|</span>
                                    <span>PSI =</span>
                                    <strong className="text-rose-400 font-mono">
                                      {df.psi_score !== undefined && df.psi_score !== null 
                                        ? Number(df.psi_score).toFixed(4) 
                                        : "N/A"}
                                    </strong>
                                    <span className="text-slate-500 text-[10px]">(threshold: {df.severity === 'critical' ? '0.25' : '0.10'})</span>
                                  </div>
                                ))
                              ) : (
                                <span>Feature exceeded drift threshold</span>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4.5 whitespace-nowrap text-xs text-slate-400">
                          {new Date(alert.created_at).toLocaleTimeString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </td>
                        <td className="px-6 py-4.5 whitespace-nowrap text-right text-xs font-medium">
                          <button
                            onClick={() => handleResolveAlert(alert.id)}
                            disabled={resolvingId === alert.id}
                            className="px-3.5 py-1.5 bg-teal-500/10 border border-teal-500/30 text-teal-400 hover:bg-teal-500/20 hover:border-teal-500/50 rounded-lg transition-colors font-medium disabled:opacity-50"
                          >
                            {resolvingId === alert.id ? "Resolving..." : "Resolve"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center max-w-sm mx-auto">
                <div className="p-3 w-fit mx-auto rounded-full bg-emerald-500/10 text-emerald-400 mb-3 border border-emerald-500/20">
                  <ShieldCheck className="h-5.5 w-5.5" />
                </div>
                <h4 className="text-sm font-semibold text-white mb-0.5">No Active Alerts</h4>
                <p className="text-xs text-slate-400">
                  Model parameters are stable and within acceptable bounds.
                </p>
              </div>
            )}
          </div>

          {/* Model Architecture Section */}
          <div className="glass-panel rounded-2xl overflow-hidden mt-6">
            <div className="px-6 py-4 border-b border-darkBorder flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Extracted Model Architecture
                </h3>
                <p className="text-[11px] text-slate-400">
                  Automatically analyzed internal layers and structural topology of the model
                </p>
              </div>
              {model.architecture?.layers && (
                <span className="text-[10px] bg-teal-500/10 border border-teal-500/30 text-teal-400 font-mono px-2 py-0.5 rounded font-semibold">
                  {model.architecture.layers.length} Layers Found
                </span>
              )}
            </div>
            
            {model.architecture?.layers && model.architecture.layers.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-darkBorder">
                  <thead className="bg-slate-900/40">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Layer Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Type / Class
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Configuration Details
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-darkBorder">
                    {model.architecture.layers.map((layer: any, idx: number) => (
                      <tr key={idx} className="hover:bg-darkHover/10">
                        <td className="px-6 py-4.5 whitespace-nowrap text-xs font-mono text-white">
                          {layer.name || `layer_${idx}`}
                        </td>
                        <td className="px-6 py-4.5 whitespace-nowrap">
                          <span className="text-xs bg-slate-950 border border-darkBorder px-2.5 py-1 rounded font-semibold text-teal-400">
                            {layer.type}
                          </span>
                        </td>
                        <td className="px-6 py-4.5 text-xs text-slate-300 font-mono">
                          {layer.details || "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : model.architecture?.error ? (
              <div className="py-8 px-6 text-center max-w-md mx-auto">
                <div className="p-2 w-fit mx-auto rounded-full bg-rose-500/10 text-rose-400 mb-2 border border-rose-500/20">
                  <AlertTriangle className="h-4.5 w-4.5" />
                </div>
                <h4 className="text-xs font-semibold text-white mb-0.5">Architecture Analysis Failed</h4>
                <p className="text-[11px] text-slate-400 font-mono text-left bg-slate-950/40 p-2.5 rounded border border-darkBorder max-h-32 overflow-y-auto">
                  {model.architecture.error}
                </p>
              </div>
            ) : (
              <div className="py-10 text-center max-w-sm mx-auto">
                <div className="p-3 w-fit mx-auto rounded-full bg-slate-800 text-slate-500 mb-3 border border-darkBorder">
                  <Compass className="h-5.5 w-5.5" />
                </div>
                <h4 className="text-sm font-semibold text-white mb-0.5">No Architecture Extracted</h4>
                <p className="text-xs text-slate-400">
                  Model architecture extraction is supported for PyTorch and TensorFlow/Keras frameworks.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "graph" && renderArchitectureGraph()}
      {activeTab === "health" && renderDatasetHealth()}
      {activeTab === "performance" && renderPerformanceProfile()}
      {activeTab === "drift_analysis" && renderDriftAnalysis()}
    </div>
  );
}
