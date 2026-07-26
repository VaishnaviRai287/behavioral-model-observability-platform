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
import { api, authHeaders } from "@/lib/api";
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
  Clock,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  Play,
  Cpu,
  Database,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Fingerprint as FingerprintIcon,
  Layers,
  Terminal,
} from "lucide-react";

// Recharts styling constants
const GRID_STROKE = "#E8D3D9";
const AXIS_STROKE = "#8A6A70";
const TOOLTIP_STYLE = {
  backgroundColor: "#FFFFFF",
  borderColor: "#211C19",
  borderRadius: 0,
  fontSize: "11px",
  color: "#1A1613",
  boxShadow: "3px 3px 0px #211C19",
};
const PAPER = "#1A1613";
const MUTE = "#8A6A70";
const ROSE = "#E11D48";
const AMBER = "#D97706";
const EMERALD = "#059669";

// Context framing header for charts: Title, Description, What am I looking at?, Why does it matter?
function ChartFrameHeader({
  title,
  what,
  why,
  badgeText = "RESEARCH_WINDOW",
}: {
  title: string;
  what: string;
  why: string;
  badgeText?: string;
}) {
  return (
    <div className="border-b-2 border-line pb-3 mb-4 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-serif font-bold text-xl text-paper">{title}</h3>
        <span className="badge-research">{badgeText}</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 font-mono text-[11px]">
        <div className="bg-panel/30 border border-line p-2.5">
          <span className="label-mono block text-accent font-bold mb-0.5">WHAT AM I LOOKING AT?</span>
          <p className="text-paper/90 leading-relaxed">{what}</p>
        </div>
        <div className="bg-ink border border-line p-2.5">
          <span className="label-mono block text-paper font-bold mb-0.5">WHY DOES IT MATTER?</span>
          <p className="explainer leading-relaxed">{why}</p>
        </div>
      </div>
    </div>
  );
}

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

  // Accordion Section States
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    monitoring: true,
    health: false,
    performance: false,
    drift_analysis: false,
    explainability: false,
  });

  const toggleSection = (sectionKey: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionKey]: !prev[sectionKey],
    }));
  };

  // Observability Data States
  const [datasetHealth, setDatasetHealth] = useState<any>(null);
  const [datasetHealthLoading, setDatasetHealthLoading] = useState(false);
  const [performanceProfile, setPerformanceProfile] = useState<any>(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [driftAnalysis, setDriftAnalysis] = useState<any>(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [selectedDriftFeature, setSelectedDriftFeature] = useState<string>("");

  // Explainability States
  const [globalExplain, setGlobalExplain] = useState<any>(null);
  const [globalLoading, setGlobalLoading] = useState(false);
  const [selectedPredId, setSelectedPredId] = useState<string | null>(null);
  const [predExplanation, setPredExplanation] = useState<any>(null);
  const [explanationLoading, setExplanationLoading] = useState(false);

  // Copy hash feedback state
  const [copiedHash, setCopiedHash] = useState(false);
  const [showRawParams, setShowRawParams] = useState(false);

  // Lazy loading API data when an accordion section is expanded
  React.useEffect(() => {
    if (expandedSections.health && !datasetHealth) {
      setDatasetHealthLoading(true);
      api.getDatasetHealth(modelId)
        .then(setDatasetHealth)
        .catch(console.error)
        .finally(() => setDatasetHealthLoading(false));
    }
    if (expandedSections.performance && !performanceProfile) {
      setPerformanceLoading(true);
      api.getPerformanceProfile(modelId)
        .then(setPerformanceProfile)
        .catch(console.error)
        .finally(() => setPerformanceLoading(false));
    }
    if (expandedSections.drift_analysis && !driftAnalysis) {
      setDriftLoading(true);
      api.getDriftAnalysis(modelId)
        .then(setDriftAnalysis)
        .catch(console.error)
        .finally(() => setDriftLoading(false));
    }
    if (expandedSections.explainability) {
      if (!globalExplain) {
        setGlobalLoading(true);
        api.getGlobalExplainability(modelId)
          .then(setGlobalExplain)
          .catch(console.error)
          .finally(() => setGlobalLoading(false));
      }
      if (predictions && predictions.length > 0 && !selectedPredId) {
        setSelectedPredId(predictions[0].id);
      }
    }
  }, [expandedSections, modelId, datasetHealth, performanceProfile, driftAnalysis, globalExplain, predictions, selectedPredId]);

  // Fetch local prediction explanation when selection changes
  React.useEffect(() => {
    if (selectedPredId) {
      setExplanationLoading(true);
      api.getPredictionExplanation(modelId, selectedPredId)
        .then(setPredExplanation)
        .catch(console.error)
        .finally(() => setExplanationLoading(false));
    }
  }, [selectedPredId, modelId]);

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
          payloadFeatures[f.name] = Number((minVal + Math.random() * (maxVal - minVal) * 0.3).toFixed(3));
        });

        await fetch(`/api/models/${modelId}/predict`, {
          method: "POST",
          headers: authHeaders({ "Content-Type": "application/json" }),
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
          payloadFeatures[f.name] = Number((minVal + (0.7 + Math.random() * 0.28) * (maxVal - minVal)).toFixed(3));
        });

        await fetch(`/api/models/${modelId}/predict`, {
          method: "POST",
          headers: authHeaders({ "Content-Type": "application/json" }),
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

  const baselineMean = model?.baseline_mean ?? 0.0;
  const baselineStd = model?.baseline_std ?? 0.0;
  const threshold = baselineMean + 3 * baselineStd;

  const handleResolveAlert = async (alertId: string) => {
    setResolvingId(alertId);
    try {
      await api.resolveAlert(modelId, alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (err: any) {
      alert(`Failed to resolve alert: ${err.message}`);
    } finally {
      setResolvingId(null);
    }
  };

  const handleCopySignature = () => {
    if (model?.signature) {
      navigator.clipboard.writeText(model.signature);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  if (modelLoading || healthLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-panel" />
        <div className="h-10 w-64 bg-panel" />
        <div className="h-28 editorial-section" />
        <div className="h-96 research-window" />
      </div>
    );
  }

  if (modelError || !model) {
    return (
      <div className="utility-panel-rose max-w-lg mx-auto p-8 text-center mt-12 border-2 border-rose-400">
        <div className="p-3 w-fit mx-auto border-2 border-rose-400 bg-ink text-rose-600 mb-4">
          <AlertTriangle className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-serif text-paper font-bold mb-2">Model Artifact Not Found</h2>
        <p className="explainer mb-6">
          The model ID &quot;{modelId}&quot; does not exist or has been deleted from storage.
        </p>
        <button
          onClick={() => router.push("/registry")}
          className="btn-physical-accent mx-auto"
        >
          Back to Registry
        </button>
      </div>
    );
  }

  // Format prediction events for novelty timeline
  const timelineData = [...predictions]
    .reverse()
    .map((p) => ({
      created_at: new Date(p.created_at).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      faiss_distance: p.faiss_distance ?? 0.0,
      novelty_flag: p.novelty_flag ?? false,
    }));

  const featureDriftData = health
    ? Object.entries(health.drift_scores).map(([name, score]) => ({
        name,
        score,
      }))
    : [];

  const totalPredictionsCount = predictions.length;
  const activeAlertsCount = alerts.filter((a) => !a.resolved_at).length;
  const noveltyRatePercent = health ? (health.novelty_rate * 100).toFixed(1) : "0.0";

  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (cx === undefined || cy === undefined) return null;
    const isNovel = payload.novelty_flag || (payload.faiss_distance > threshold && threshold > 0);
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isNovel ? 5 : 3}
        fill={isNovel ? ROSE : PAPER}
        stroke={isNovel ? ROSE : PAPER}
      />
    );
  };

  const scrollToSection = (sectionKey: string) => {
    setExpandedSections((prev) => ({ ...prev, [sectionKey]: true }));
    const element = document.getElementById(`section-${sectionKey}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="space-y-10">
      {/* 1. IDENTITY & HEADER (Level 2 Editorial Section) */}
      <div className="border-b-2 border-line pb-6 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <Link
              href="/registry"
              className="badge-research hover:border-accent hover:text-accent cursor-pointer transition-colors w-fit"
            >
              ← MODEL REGISTRY
            </Link>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="font-serif font-extrabold text-4xl sm:text-5xl text-paper tracking-tight">
                {model.name}
              </h1>
              <span className="badge-research-finding">
                {model.framework.toUpperCase()}
              </span>
              <span className="badge-research-baseline">
                STATUS: {model.status.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs text-mute">
              <span>MODEL_ID:</span>
              <code className="text-paper font-bold">{model.id}</code>
            </div>
          </div>

          {/* Traffic Simulation Control (Level 4 Utility Component) */}
          {isSimulating ? (
            <div className="utility-panel-amber p-3 space-y-2 shrink-0 max-w-xs">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-rose-600 animate-pulse" />
                <span className="font-mono text-xs font-bold text-paper">{simStatus}</span>
              </div>
              <div className="w-full bg-ink border border-line h-2 overflow-hidden">
                <div
                  className="bg-accent h-full transition-all duration-150"
                  style={{ width: `${(simulatedCount / simTotal) * 100}%` }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={handleSimulateTraffic}
              className="btn-physical-accent shrink-0"
            >
              <Play className="h-4 w-4 fill-current" />
              <span>Simulate Drift Traffic</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. BEHAVIORAL FINGERPRINT BANNER (Unboxed Editorial Overview) */}
      <div className="bg-panel/40 border-2 border-line p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 border-2 border-line bg-ink shrink-0">
              <FingerprintIcon className="h-6 w-6 text-paper" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="badge-research-finding">BEHAVIORAL FINGERPRINT</span>
                <span className="badge-research">1,000 PROBES SWEEP</span>
                <span className="badge-research-baseline">FAISS INDEX ACTIVE</span>
              </div>
              <p className="font-serif font-bold text-2xl text-paper mt-1 tracking-tight">
                {model.signature ? `${model.signature.substring(0, 16)}...` : "Extracting Signature..."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopySignature}
              className="btn-physical text-xs py-1 px-3"
            >
              {copiedHash ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {copiedHash ? "Copied" : "Copy Signature"}
            </button>
            <Link
              href={`/models/${model.id}/fingerprint`}
              className="btn-physical-accent text-xs py-1 px-3"
            >
              Full Analysis →
            </Link>
          </div>
        </div>

        <p className="explainer max-w-3xl">
          Decision-boundary baseline compiled from 1,000 synthetic Latin Hypercube probe vectors. Live predictions compare against this FAISS activation index.
        </p>

        {/* Collapsible raw details */}
        <div className="pt-2 border-t border-line">
          <button
            onClick={() => setShowRawParams(!showRawParams)}
            className="label-mono hover:text-accent flex items-center gap-1 cursor-pointer"
          >
            {showRawParams ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {showRawParams ? "Hide Advanced Parameters" : "View Advanced Signature & Parameter Hashes"}
          </button>
          {showRawParams && (
            <div className="mt-3 bg-ink border-2 border-line p-3 font-mono text-xs space-y-1 overflow-x-auto text-paper">
              <p><strong className="text-accent">FULL_SHA256_SIGNATURE:</strong> {model.signature || "N/A"}</p>
              <p><strong className="text-mute">BASELINE_MEAN_DISTANCE:</strong> {baselineMean.toFixed(4)}</p>
              <p><strong className="text-mute">BASELINE_STD_DISTANCE:</strong> {baselineStd.toFixed(4)}</p>
              <p><strong className="text-mute">NOVELTY_THRESHOLD_3SIGMA:</strong> {threshold.toFixed(4)}</p>
            </div>
          )}
        </div>
      </div>

      {/* 3. LEVEL 3 — UNBOXED INLINE METRIC STRIP */}
      <div className="space-y-2">
        <span className="badge-research">LIVE OBSERVABILITY READOUT</span>
        <div className="metric-strip">
          <div className="inline-metric">
            <span className="label-mono block text-mute">CERTAINTY</span>
            <p className="font-display text-3xl text-paper">
              {predictions.length > 0
                ? (predictions.reduce((acc, curr) => acc + curr.confidence, 0) / predictions.length).toFixed(3)
                : "N/A"}
            </p>
            <p className="explainer">Mean Confidence</p>
          </div>

          <div className="inline-metric">
            <span className="label-mono block text-accent font-bold">NOVELTY RATE</span>
            <p className="font-display text-3xl text-paper">{noveltyRatePercent}%</p>
            <p className="explainer">Out-of-distribution</p>
          </div>

          <div className="inline-metric">
            <span className={activeAlertsCount > 0 ? "label-mono block text-rose-600 font-bold" : "label-mono block text-mute"}>
              ALERT BREACHES
            </span>
            <p className="font-display text-3xl text-paper">{activeAlertsCount}</p>
            <p className="explainer">Active unresolved</p>
          </div>

          <div className="inline-metric">
            <span className="label-mono block text-mute">TRAFFIC COUNT</span>
            <p className="font-display text-3xl text-paper">{totalPredictionsCount}</p>
            <p className="explainer font-mono">Predictions logged</p>
          </div>
        </div>
      </div>

      {/* 4. WORKSPACE STICKY ANCHOR NAVIGATION */}
      <div className="sticky top-16 z-40 bg-ink border-2 border-line p-2 flex items-center gap-2 overflow-x-auto">
        <span className="badge-research shrink-0">ANCHORS:</span>
        {[
          { key: "monitoring", label: "01 // Novelty & Monitoring" },
          { key: "health", label: "02 // Dataset Health" },
          { key: "performance", label: "03 // Performance" },
          { key: "drift_analysis", label: "04 // Drift Analysis" },
          { key: "explainability", label: "05 // SHAP Explanations" },
        ].map((anchor) => (
          <button
            key={anchor.key}
            onClick={() => scrollToSection(anchor.key)}
            className={`font-mono text-xs font-bold uppercase px-3 py-1 border-2 border-line whitespace-nowrap transition-colors ${
              expandedSections[anchor.key]
                ? "bg-accent text-ink"
                : "bg-panel/40 text-paper hover:bg-ink"
            }`}
          >
            {anchor.label}
          </button>
        ))}
      </div>

      {/* 5. WORKSPACE ACCORDION SECTIONS */}

      {/* SECTION 01: MONITORING DASHBOARD (Level 1 Research Windows) */}
      <section id="section-monitoring" className="space-y-6 scroll-mt-32">
        <div className="border-b-2 border-line pb-2 flex items-center justify-between">
          <button
            onClick={() => toggleSection("monitoring")}
            className="flex items-center gap-3 text-left group cursor-pointer"
          >
            <span className="font-mono text-lg font-bold text-accent">
              {expandedSections.monitoring ? "▼" : "▶"}
            </span>
            <div>
              <span className="badge-research-finding">SECTION 01</span>
              <h2 className="font-serif font-bold text-2xl text-paper group-hover:text-accent transition-colors">
                Real-Time Novelty &amp; Feature Drift Analysis
              </h2>
            </div>
          </button>
          <span className="label-mono">LIVE FEED</span>
        </div>

        {expandedSections.monitoring && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* LEVEL 1 RESEARCH WINDOW: NOVELTY TIMELINE */}
              <div className="research-window">
                <div className="window-titlebar">
                  <div className="window-dots">
                    <span className="window-dot bg-rose-400" />
                    <span className="window-dot bg-amber-400" />
                    <span className="window-dot bg-emerald-400" />
                  </div>
                  <span className="font-mono text-xs font-bold text-paper">RESEARCH_WINDOW // NOVELTY_DISTANCE</span>
                  <span className="badge-research">FAISS k-NN</span>
                </div>

                <div className="window-content space-y-4">
                  <ChartFrameHeader
                    title="Penultimate Activation Distance Timeline"
                    what="Nearest-neighbor FAISS distance for each live prediction vector."
                    why="Spikes above the 3σ line signal traffic landing in unhandled confidence regions."
                  />

                  <div className="h-64 w-full">
                    {timelineData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
                          <XAxis dataKey="created_at" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                          <YAxis stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                          <Tooltip contentStyle={TOOLTIP_STYLE} />
                          <ReferenceLine y={baselineMean} stroke={MUTE} strokeWidth={1} label={{ value: "Mean", fill: MUTE, fontSize: 9 }} />
                          <ReferenceLine y={threshold} stroke={ROSE} strokeDasharray="4 4" strokeWidth={1.5} label={{ value: "Limit (3σ)", fill: ROSE, fontSize: 9 }} />
                          <Line type="monotone" dataKey="faiss_distance" stroke={PAPER} strokeWidth={1.5} dot={<CustomDot />} activeDot={{ r: 6 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center text-center p-6 bg-panel/30 border border-line">
                        <Clock className="h-8 w-8 text-mute mb-2" />
                        <span className="font-mono text-xs text-paper font-bold">No predictions logged yet</span>
                        <span className="explainer mt-1">Run the traffic simulator above to plot live novelty events.</span>
                      </div>
                    )}
                  </div>

                  <div className="pt-3 border-t border-line flex items-center justify-between font-mono text-xs">
                    <span>Baseline Mean: <strong className="text-paper">{baselineMean.toFixed(3)}</strong></span>
                    <span>Threshold Limit: <strong className="text-rose-600 font-bold">{threshold.toFixed(3)}</strong></span>
                  </div>
                </div>
              </div>

              {/* LEVEL 1 RESEARCH WINDOW: FEATURE DRIFT KS CHART */}
              <div className="research-window">
                <div className="window-titlebar">
                  <div className="window-dots">
                    <span className="window-dot bg-rose-400" />
                    <span className="window-dot bg-amber-400" />
                    <span className="window-dot bg-emerald-400" />
                  </div>
                  <span className="font-mono text-xs font-bold text-paper">RESEARCH_WINDOW // FEATURE_DRIFT_KS</span>
                  <span className="badge-research">KS STATISTIC</span>
                </div>

                <div className="window-content space-y-4">
                  <ChartFrameHeader
                    title="Feature-Level KS Statistic Scores"
                    what="Kolmogorov-Smirnov distance comparing probed baseline distributions against live traffic."
                    why="Features crossing 0.10 (amber) or 0.20 (rose) have shifted significantly from training assumptions."
                  />

                  <div className="h-64 w-full">
                    {featureDriftData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart layout="vertical" data={featureDriftData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
                          <XAxis type="number" domain={[0, 1.0]} stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                          <YAxis type="category" dataKey="name" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                          <Tooltip contentStyle={TOOLTIP_STYLE} />
                          <ReferenceLine x={0.1} stroke={AMBER} strokeDasharray="3 3" />
                          <ReferenceLine x={0.2} stroke={ROSE} strokeDasharray="3 3" />
                          <Bar dataKey="score" radius={0}>
                            {featureDriftData.map((entry, index) => {
                              let fill = PAPER;
                              if (entry.score >= 0.2) fill = ROSE;
                              else if (entry.score >= 0.1) fill = AMBER;
                              return <Cell key={`cell-${index}`} fill={fill} />;
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center text-center p-6 bg-panel/30 border border-line">
                        <Compass className="h-8 w-8 text-mute mb-2" />
                        <span className="font-mono text-xs text-paper font-bold">No drift evaluations recorded</span>
                        <span className="explainer mt-1">Evaluated automatically every 50 predictions.</span>
                      </div>
                    )}
                  </div>

                  <div className="pt-3 border-t border-line flex items-center justify-between font-mono text-xs">
                    <span>Warning Bound: <strong className="text-amber-600">0.10</strong></span>
                    <span>Critical Bound: <strong className="text-rose-600 font-bold">0.20</strong></span>
                  </div>
                </div>
              </div>
            </div>

            {/* SIDE-BY-SIDE: ACTIVE ALERTS & EXTRACTED LAYER TOPOLOGY */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* LEVEL 4 UTILITY PANEL: ACTIVE ALERTS */}
              <div className="utility-panel space-y-3 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b-2 border-line pb-2">
                    <div>
                      <span className="badge-research-finding">ACTIVE ACTION ITEMS</span>
                      <h3 className="font-serif font-bold text-lg text-paper">Active Observability Alerts ({alerts.length})</h3>
                    </div>
                    <span className="badge-research">{alerts.length} ALERTS</span>
                  </div>

                  {alerts.length > 0 ? (
                    <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                      {alerts.map((alertItem) => (
                        <div
                          key={alertItem.id}
                          className={
                            alertItem.severity === "critical"
                              ? "utility-panel-rose p-3 space-y-2"
                              : "utility-panel-amber p-3 space-y-2"
                          }
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[10px] font-bold uppercase text-paper border border-line px-1.5 py-0.5 bg-ink">
                              {alertItem.alert_type}
                            </span>
                            <span className={alertItem.severity === "critical" ? "badge-research border-rose-500 text-rose-700" : "badge-research border-amber-500 text-amber-700"}>
                              {alertItem.severity.toUpperCase()}
                            </span>
                          </div>

                          <div className="font-mono text-xs text-paper/90 space-y-1">
                            {alertItem.alert_type === "LATENT_NOVELTY" ? (
                              <p>
                                Distance: <strong className="text-rose-700 font-bold">{alertItem.metadata.distance ? Number(alertItem.metadata.distance).toFixed(4) : "N/A"}</strong>
                              </p>
                            ) : (
                              <div className="space-y-0.5 text-[11px]">
                                {alertItem.metadata.drifted_features?.map((df: any, idx: number) => (
                                  <p key={idx}>
                                    Feature <strong className="text-amber-800">{df.feature_name}</strong>: KS = <strong className="text-rose-700">{df.ks_statistic ? Number(df.ks_statistic).toFixed(4) : "N/A"}</strong>, PSI = <strong>{df.psi_score ? Number(df.psi_score).toFixed(4) : "N/A"}</strong>.
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>

                          <div className="pt-1.5 border-t border-line flex items-center justify-between">
                            <span className="font-mono text-[10px] text-mute">
                              {new Date(alertItem.created_at).toLocaleTimeString()}
                            </span>
                            <button
                              onClick={() => handleResolveAlert(alertItem.id)}
                              disabled={resolvingId === alertItem.id}
                              className="btn-physical py-0.5 px-2 text-[10px]"
                            >
                              {resolvingId === alertItem.id ? "Resolving..." : "Resolve Alert ✓"}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6">
                      <ShieldCheck className="h-7 w-7 text-emerald-600 mx-auto mb-1.5" />
                      <h4 className="font-serif font-bold text-sm text-paper">No Active Alerts</h4>
                      <p className="explainer">Model inference behavior remains stable.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* LEVEL 2 EDITORIAL NOTEBOOK: EXTRACTED LAYER TOPOLOGY */}
              <div className="border-2 border-line bg-ink p-4 space-y-3 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b-2 border-line pb-2">
                    <div>
                      <span className="badge-research-finding">NOTEBOOK DOCUMENT</span>
                      <h3 className="font-serif font-bold text-lg text-paper">Extracted Layer Topology</h3>
                    </div>
                    {model.architecture?.layers && (
                      <span className="badge-research">{model.architecture.layers.length} LAYERS</span>
                    )}
                  </div>

                  {model.architecture?.layers && model.architecture.layers.length > 0 ? (
                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                      {model.architecture.layers.map((layer: any, idx: number) => (
                        <div key={idx} className="bg-panel/30 border border-line p-2.5 font-mono text-xs flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="badge-research font-bold text-[9px] shrink-0">L{idx}</span>
                            <span className="font-bold text-paper truncate">{layer.name || `layer_${idx}`}</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <code className="text-[11px] text-mute max-w-[160px] truncate">{layer.details || "Standard Layer"}</code>
                            <span className="badge-research-finding text-[9px]">{layer.type}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 explainer font-mono">
                      No extracted layer topology recorded for this artifact.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* SECTION 02: DATASET HEALTH (Unboxed Editorial Layout + Level 3 Metric Strip) */}
      <section id="section-health" className="space-y-6 scroll-mt-32 pt-6 border-t-2 border-line">
        <div className="flex items-center justify-between">
          <button
            onClick={() => toggleSection("health")}
            className="flex items-center gap-3 text-left group cursor-pointer"
          >
            <span className="font-mono text-lg font-bold text-accent">
              {expandedSections.health ? "▼" : "▶"}
            </span>
            <div>
              <span className="badge-research">SECTION 02</span>
              <h2 className="font-serif font-bold text-2xl text-paper group-hover:text-accent transition-colors">
                Dataset Health &amp; Input Data Quality
              </h2>
            </div>
          </button>
          <span className="label-mono">PRODUCTION QUALITY</span>
        </div>

        {expandedSections.health && (
          <div>
            {datasetHealthLoading ? (
              <div className="text-center py-12 font-mono text-xs font-bold animate-pulse">
                Analyzing dataset health &amp; IQR outliers...
              </div>
            ) : datasetHealth ? (
              <div className="space-y-6">
                {/* Level 3 Inline Metric Strip */}
                <div className="metric-strip">
                  <div className="inline-metric">
                    <span className="label-mono block text-mute">NULL VALUES</span>
                    <p className="font-display text-3xl text-paper">{datasetHealth.missing_values.percentage}%</p>
                    <p className="explainer">{datasetHealth.missing_values.total_missing} missing values</p>
                  </div>
                  <div className="inline-metric">
                    <span className="label-mono block text-mute">DUPLICATES</span>
                    <p className="font-display text-3xl text-paper">{datasetHealth.duplicates.percentage}%</p>
                    <p className="explainer">{datasetHealth.duplicates.duplicate_count} duplicates</p>
                  </div>
                  <div className="inline-metric">
                    <span className="label-mono block text-accent font-bold">OUTLIERS</span>
                    <p className="font-display text-3xl text-paper">{datasetHealth.outliers.percentage}%</p>
                    <p className="explainer">{datasetHealth.outliers.total_outliers} IQR outliers</p>
                  </div>
                  <div className="inline-metric">
                    <span className="label-mono block text-mute">CLASS ENTROPY</span>
                    <p className="font-display text-3xl text-paper">{datasetHealth.class_imbalance.entropy}</p>
                    <p className="explainer">Shannon scale</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="border-2 border-line p-5 space-y-4 bg-ink">
                    <h3 className="font-serif font-bold text-lg text-paper">Class Balance Distribution</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={Object.entries(datasetHealth.class_imbalance.counts).map(([cls, cnt]) => ({ name: `Class ${cls}`, count: cnt }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
                          <XAxis dataKey="name" stroke={AXIS_STROKE} fontSize={10} tickLine={false} />
                          <YAxis stroke={AXIS_STROKE} fontSize={10} tickLine={false} />
                          <Tooltip contentStyle={TOOLTIP_STYLE} />
                          <Bar dataKey="count" fill={PAPER} radius={0} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="border-2 border-line p-5 space-y-4 bg-panel/30">
                    <h3 className="font-serif font-bold text-lg text-paper">Outliers per Feature (IQR)</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart layout="vertical" data={Object.entries(datasetHealth.outliers.by_feature).map(([feat, cnt]) => ({ name: feat, count: cnt }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
                          <XAxis type="number" stroke={AXIS_STROKE} fontSize={10} tickLine={false} />
                          <YAxis type="category" dataKey="name" stroke={AXIS_STROKE} fontSize={10} tickLine={false} />
                          <Tooltip contentStyle={TOOLTIP_STYLE} />
                          <Bar dataKey="count" fill={ROSE} radius={0} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </section>

      {/* SECTION 03: INFERENCE PERFORMANCE */}
      <section id="section-performance" className="space-y-6 scroll-mt-32 pt-6 border-t-2 border-line">
        <div className="flex items-center justify-between">
          <button
            onClick={() => toggleSection("performance")}
            className="flex items-center gap-3 text-left group cursor-pointer"
          >
            <span className="font-mono text-lg font-bold text-accent">
              {expandedSections.performance ? "▼" : "▶"}
            </span>
            <div>
              <span className="badge-research">SECTION 03</span>
              <h2 className="font-serif font-bold text-2xl text-paper group-hover:text-accent transition-colors">
                Inference Performance &amp; Latency Percentiles
              </h2>
            </div>
          </button>
          <span className="label-mono font-bold">LATENCY &amp; RPS</span>
        </div>

        {expandedSections.performance && (
          <div>
            {performanceLoading ? (
              <div className="text-center py-12 font-mono text-xs font-bold animate-pulse">
                Fetching inference latency percentiles...
              </div>
            ) : performanceProfile ? (
              <div className="space-y-6">
                <div className="metric-strip">
                  <div className="inline-metric">
                    <span className="label-mono block text-mute">THROUGHPUT</span>
                    <p className="font-display text-3xl text-paper">{performanceProfile.throughput.rps_1m} RPS</p>
                    <p className="explainer">1-minute average</p>
                  </div>
                  <div className="inline-metric">
                    <span className="label-mono block text-accent font-bold">P95 LATENCY</span>
                    <p className="font-display text-3xl text-paper">{performanceProfile.latency.p95} ms</p>
                    <p className="explainer">95th percentile</p>
                  </div>
                  <div className="inline-metric">
                    <span className="label-mono block text-mute">CPU LOAD</span>
                    <p className="font-display text-3xl text-paper">{performanceProfile.cpu.mean_pct}%</p>
                    <p className="explainer">Peak: {performanceProfile.cpu.peak_pct}%</p>
                  </div>
                  <div className="inline-metric">
                    <span className="label-mono block text-mute">MEMORY RSS</span>
                    <p className="font-display text-3xl text-paper">{performanceProfile.memory.mean_mb} MB</p>
                    <p className="explainer">Peak: {performanceProfile.memory.peak_mb} MB</p>
                  </div>
                </div>

                <div className="border-2 border-line p-5 space-y-4 bg-ink">
                  <h3 className="font-serif font-bold text-lg text-paper">Latency Profile Across Percentiles</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[
                        { name: "Min", val: performanceProfile.latency.min },
                        { name: "P50", val: performanceProfile.latency.p50 },
                        { name: "Mean", val: performanceProfile.latency.mean },
                        { name: "P95", val: performanceProfile.latency.p95 },
                        { name: "P99", val: performanceProfile.latency.p99 },
                        { name: "Max", val: performanceProfile.latency.max }
                      ]}>
                        <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
                        <XAxis dataKey="name" stroke={AXIS_STROKE} fontSize={10} tickLine={false} />
                        <YAxis stroke={AXIS_STROKE} fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={TOOLTIP_STYLE} />
                        <Bar dataKey="val" fill={PAPER} radius={0}>
                          <Cell fill={PAPER} />
                          <Cell fill={PAPER} />
                          <Cell fill={PAPER} />
                          <Cell fill={AMBER} />
                          <Cell fill={ROSE} />
                          <Cell fill={ROSE} />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </section>

      {/* SECTION 04: DRIFT ANALYSIS */}
      <section id="section-drift_analysis" className="space-y-6 scroll-mt-32 pt-6 border-t-2 border-line">
        <div className="flex items-center justify-between">
          <button
            onClick={() => toggleSection("drift_analysis")}
            className="flex items-center gap-3 text-left group cursor-pointer"
          >
            <span className="font-mono text-lg font-bold text-accent">
              {expandedSections.drift_analysis ? "▼" : "▶"}
            </span>
            <div>
              <span className="badge-research">SECTION 04</span>
              <h2 className="font-serif font-bold text-2xl text-paper group-hover:text-accent transition-colors">
                Statistical Drift Analysis (KS &amp; PSI)
              </h2>
            </div>
          </button>
          <span className="label-mono">DISTRIBUTION SHIFT</span>
        </div>

        {expandedSections.drift_analysis && (
          <div>
            {driftLoading ? (
              <div className="text-center py-12 font-mono text-xs font-bold animate-pulse">
                Calculating distribution shift (KS &amp; PSI)...
              </div>
            ) : driftAnalysis ? (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="border-2 border-line p-5 space-y-3 bg-panel/30">
                    <span className="badge-research-finding font-bold">TARGET DRIFT</span>
                    <h4 className="font-serif font-bold text-xl text-paper">Target Classification Output Shift</h4>
                    <div className="flex items-baseline justify-between pt-2">
                      <div>
                        <span className="label-mono block text-mute">PSI SCORE</span>
                        <span className="font-display text-3xl text-paper">{driftAnalysis.target_drift.class_drift.psi_score}</span>
                      </div>
                      <span className="badge-research border-2 font-bold uppercase">
                        {driftAnalysis.target_drift.class_drift.verdict}
                      </span>
                    </div>
                  </div>

                  <div className="border-2 border-line p-5 space-y-3 bg-ink">
                    <span className="badge-research-finding font-bold">CONFIDENCE DRIFT</span>
                    <h4 className="font-serif font-bold text-xl text-paper">Output Certainty Distribution Shift</h4>
                    <div className="flex items-baseline justify-between pt-2 font-mono">
                      <div>
                        <span className="label-mono block text-mute">KS STATISTIC</span>
                        <span className="font-display text-3xl text-paper">{driftAnalysis.target_drift.confidence_drift.ks_statistic}</span>
                      </div>
                      <span className="badge-research border-2 font-bold uppercase">
                        {driftAnalysis.target_drift.confidence_drift.verdict}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </section>

      {/* SECTION 05: SHAP EXPLAINABILITY (Level 1 Research Windows) */}
      <section id="section-explainability" className="space-y-6 scroll-mt-32 pt-6 border-t-2 border-line">
        <div className="flex items-center justify-between">
          <button
            onClick={() => toggleSection("explainability")}
            className="flex items-center gap-3 text-left group cursor-pointer"
          >
            <span className="font-mono text-lg font-bold text-accent">
              {expandedSections.explainability ? "▼" : "▶"}
            </span>
            <div>
              <span className="badge-research-finding">SECTION 05</span>
              <h2 className="font-serif font-bold text-2xl text-paper group-hover:text-accent transition-colors">
                Shapley Feature Attributions (Kernel SHAP)
              </h2>
            </div>
          </button>
          <span className="label-mono font-bold">EXPLAINABILITY</span>
        </div>

        {expandedSections.explainability && (
          <div>
            {globalLoading ? (
              <div className="text-center py-12 font-mono text-xs font-bold animate-pulse">
                Solving Kernel SHAP coalition weights across probes...
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* LEVEL 1 RESEARCH WINDOW: GLOBAL SHAP */}
                <div className="research-window">
                  <div className="window-titlebar">
                    <div className="window-dots">
                      <span className="window-dot bg-rose-400" />
                      <span className="window-dot bg-amber-400" />
                      <span className="window-dot bg-emerald-400" />
                    </div>
                    <span className="font-mono text-xs font-bold text-paper">RESEARCH_WINDOW // GLOBAL_SHAP</span>
                    <span className="badge-research">KERNEL SHAP</span>
                  </div>

                  <div className="window-content space-y-4">
                    <ChartFrameHeader
                      title="Global Feature Importance"
                      what="Ranks overall feature influence across probe baseline samples."
                      why="Identifies which features dominate model predictions at large."
                    />

                    {globalExplain?.feature_importance?.length > 0 ? (
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart layout="vertical" data={globalExplain.feature_importance}>
                            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
                            <XAxis type="number" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                            <YAxis type="category" dataKey="feature" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                            <Tooltip contentStyle={TOOLTIP_STYLE} />
                            <Bar dataKey="importance" fill={PAPER} radius={0} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="p-8 text-center bg-panel/30 border border-line explainer font-mono">
                        No background data found for SHAP evaluation.
                      </div>
                    )}
                  </div>
                </div>

                {/* LEVEL 1 RESEARCH WINDOW: LOCAL SHAP */}
                <div className="research-window">
                  <div className="window-titlebar">
                    <div className="window-dots">
                      <span className="window-dot bg-rose-400" />
                      <span className="window-dot bg-amber-400" />
                      <span className="window-dot bg-emerald-400" />
                    </div>
                    <span className="font-mono text-xs font-bold text-paper">RESEARCH_WINDOW // LOCAL_SHAP</span>
                    <span className="badge-research">PREDICTION BREAKDOWN</span>
                  </div>

                  <div className="window-content space-y-4">
                    <div className="flex items-center justify-between">
                      <ChartFrameHeader
                        title="Local Prediction Breakdown"
                        what="Quantifies feature contributions for one specific inference."
                        why="Shows why the model predicted a given class."
                      />
                      {predictions.length > 0 && (
                        <select
                          value={selectedPredId || ""}
                          onChange={(e) => setSelectedPredId(e.target.value)}
                          className="bg-ink border-2 border-line p-1 text-xs font-mono"
                        >
                          {predictions.map((p, idx) => (
                            <option key={p.id} value={p.id}>
                              {idx + 1}. Class {p.predicted_class}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {explanationLoading ? (
                      <div className="py-12 text-center font-mono text-xs font-bold animate-pulse">
                        Calculating local attribution values...
                      </div>
                    ) : predExplanation ? (
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart layout="vertical" data={predExplanation.breakdown}>
                            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
                            <XAxis type="number" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                            <YAxis type="category" dataKey="feature" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                            <Tooltip contentStyle={TOOLTIP_STYLE} />
                            <Bar dataKey="contribution" radius={0}>
                              {predExplanation.breakdown.map((entry: any, index: number) => (
                                <Cell key={`cell-${index}`} fill={entry.contribution > 0 ? ROSE : EMERALD} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
