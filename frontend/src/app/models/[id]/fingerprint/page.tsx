"use client";

import React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  useModelDetail,
  useModelFingerprints,
  useUncertaintyRegions,
} from "@/hooks/useModelHealth";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  ArrowLeft,
  AlertTriangle,
  Layers,
  ShieldCheck,
  Info,
} from "lucide-react";

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
const ROSE = "#E11D48";
const AMBER = "#D97706";
const PAPER = "#1A1613";

export default function FingerprintViewer() {
  const params = useParams();
  const router = useRouter();
  const modelId = params.id as string;

  const { data: model, loading: modelLoading, error: modelError } = useModelDetail(modelId);
  const { data: fingerprints, loading: fpLoading, error: fpError } = useModelFingerprints(modelId);

  const activeFingerprint = fingerprints && fingerprints.length > 0 ? fingerprints[0] : undefined;

  const {
    data: regions,
    loading: regionsLoading,
    error: regionsError,
  } = useUncertaintyRegions(activeFingerprint?.id);

  if (modelLoading || fpLoading || (activeFingerprint && regionsLoading)) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-panel" />
        <div className="h-10 w-64 bg-panel" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 research-window" />
          <div className="h-80 editorial-card" />
        </div>
      </div>
    );
  }

  if (modelError || !model) {
    return (
      <div className="utility-panel-rose max-w-lg mx-auto p-8 text-center mt-12 shadow-[6px_6px_0px_#211C19]">
        <div className="p-3 w-fit mx-auto border-2 border-rose-400 bg-ink text-rose-600 mb-4">
          <AlertTriangle className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-serif text-paper font-bold mb-2">Model Artifact Not Found</h2>
        <p className="explainer mb-6">
          The model ID &quot;{modelId}&quot; does not exist or has been deleted.
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

  if (fpError || !activeFingerprint) {
    return (
      <div className="utility-panel-amber max-w-lg mx-auto p-8 text-center mt-12 shadow-[6px_6px_0px_#211C19]">
        <div className="p-3 w-fit mx-auto border-2 border-amber-400 bg-ink text-amber-700 mb-4">
          <Layers className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-serif text-paper font-bold mb-2">No Behavioral Baseline Found</h2>
        <p className="explainer mb-6">
          This model artifact has not completed its Latin Hypercube synthetic probing sweep yet.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href={`/models/${model.id}`}
            className="btn-physical"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const histogramBins = [
    "0.0-0.1",
    "0.1-0.2",
    "0.2-0.3",
    "0.3-0.4",
    "0.4-0.5",
    "0.5-0.6",
    "0.6-0.7",
    "0.7-0.8",
    "0.8-0.9",
    "0.9-1.0",
  ];
  const histogramData = activeFingerprint.confidence_histogram.map((val, idx) => ({
    bin: histogramBins[idx] || `${(idx / 10).toFixed(1)}-${((idx + 1) / 10).toFixed(1)}`,
    fraction: parseFloat((val * 100).toFixed(2)),
  }));

  const formatBounds = (bounds: Record<string, [number | null, number | null]>) => {
    const boundStrings = Object.entries(bounds).map(([feature, range]) => {
      const [min, max] = range;
      if (min !== null && max !== null) {
        return `${min.toFixed(2)} < ${feature} <= ${max.toFixed(2)}`;
      }
      if (min !== null) {
        return `${feature} > ${min.toFixed(2)}`;
      }
      if (max !== null) {
        return `${feature} <= ${max.toFixed(2)}`;
      }
      return `${feature}: any`;
    });

    if (boundStrings.length === 0) return "Global / No bounds";
    return boundStrings.join(" ∧ ");
  };

  return (
    <div className="space-y-8">
      {/* Header & Navigation */}
      <div className="border-b-2 border-line pb-6 space-y-2">
        <Link
          href={`/models/${model.id}`}
          className="badge-research hover:border-accent hover:text-accent cursor-pointer transition-colors w-fit"
        >
          ← BACK TO MODEL WORKSPACE
        </Link>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="font-serif font-extrabold text-4xl sm:text-5xl text-paper tracking-tight">
            Behavioral Fingerprint Analysis
          </h1>
          <span className="badge-research-finding">BASELINE PROBE</span>
          <span className="badge-research-baseline">FAISS INDEXED</span>
        </div>
        <p className="explainer max-w-3xl">
          Statistical summary of model decision boundary response compiled across 1,000 synthetic Latin Hypercube probe samples on{" "}
          {new Date(activeFingerprint.created_at).toLocaleDateString(undefined, {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
          . All real-time drift and novelty checks benchmark against this baseline.
        </p>
      </div>

      {/* Stats Summary Panel (4 Editorial Cards) */}
      <div className="space-y-3">
        <span className="badge-research">BASELINE METRICS</span>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research">PROBE COUNT</span>
            <p className="stat-huge text-3xl mt-2">1,000</p>
            <p className="explainer mt-1 font-mono">LHS Synthetic Samples</p>
          </div>
          <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research-baseline">MEAN CERTAINTY</span>
            <p className="stat-huge text-3xl mt-2">
              {activeFingerprint.mean_confidence.toFixed(4)}
            </p>
            <p className="explainer mt-1 font-mono">Output Confidence</p>
          </div>
          <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research">ENTROPY</span>
            <p className="stat-huge text-3xl mt-2">
              {activeFingerprint.entropy.toFixed(4)}
            </p>
            <p className="explainer mt-1 font-mono">Shannon Scale (0 to 1)</p>
          </div>
          <div className="editorial-card-white shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research-finding">LOW CONF RATE</span>
            <p className="stat-huge text-3xl mt-2">
              {(activeFingerprint.uncertainty_rate * 100).toFixed(1)}%
            </p>
            <p className="explainer mt-1 font-mono">Probes with Conf &lt; 0.60</p>
          </div>
        </div>
      </div>

      {/* Two Columns Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* RESEARCH WINDOW 1: CONFIDENCE HISTOGRAM */}
        <div className="research-window">
          <div className="window-titlebar">
            <div className="window-dots">
              <span className="window-dot bg-rose-400" />
              <span className="window-dot bg-amber-400" />
              <span className="window-dot bg-emerald-400" />
            </div>
            <span className="font-mono text-xs font-bold text-paper">RESEARCH_WINDOW // CONFIDENCE_HISTOGRAM</span>
            <span className="badge-research">10 BINS</span>
          </div>

          <div className="window-content space-y-4">
            <div className="border-b-2 border-line pb-3 space-y-1">
              <h3 className="font-serif font-bold text-xl text-paper">Baseline Confidence Distribution</h3>
              <div className="grid grid-cols-1 gap-2 pt-1 font-mono text-[11px]">
                <div className="bg-panel/40 border border-line p-2">
                  <span className="label-mono block text-accent font-bold">WHAT AM I LOOKING AT?</span>
                  <p className="text-paper/90 mt-0.5 leading-relaxed">10-bin histogram showing output prediction confidence across 1,000 LHS probe vectors.</p>
                </div>
                <div className="bg-ink border border-line p-2">
                  <span className="label-mono block text-paper font-bold">WHY DOES IT MATTER?</span>
                  <p className="explainer mt-0.5 leading-relaxed">Heavily weighted low-confidence bins (amber/rose) indicate intrinsic model uncertainty even on baseline bounds.</p>
                </div>
              </div>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={histogramData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
                  <XAxis dataKey="bin" stroke={AXIS_STROKE} fontSize={9} tickLine={false} />
                  <YAxis stroke={AXIS_STROKE} fontSize={9} tickLine={false} unit="%" />
                  <Tooltip formatter={(value: any) => [`${value}%`, "Density"]} contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="fraction" radius={0}>
                    {histogramData.map((entry, index) => {
                      const binVal = index / 10;
                      let fill = PAPER;
                      if (binVal < 0.6) {
                        fill = binVal < 0.3 ? ROSE : AMBER;
                      }
                      return <Cell key={`cell-${index}`} fill={fill} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-start gap-2.5 bg-panel border-2 border-line p-3 text-[11px] font-mono text-paper shadow-[2px_2px_0px_#211C19]">
              <Info className="h-4 w-4 text-paper shrink-0 mt-0.5" />
              <p>
                Bars below 0.6 confidence threshold are highlighted in amber (0.3–0.6) or rose (&lt;0.3), marking volatile decision regions.
              </p>
            </div>
          </div>
        </div>

        {/* EDITORIAL CARD / TABLE: UNCERTAINTY REGIONS */}
        <div className="editorial-card shadow-[6px_6px_0px_#211C19] flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="border-b-2 border-line pb-3">
              <div className="flex items-center justify-between">
                <span className="badge-research-finding">VOLATILITY REGIONS</span>
                <span className="badge-research">DECISION TREE SPLITS</span>
              </div>
              <h3 className="font-serif font-bold text-xl text-paper mt-1">Extracted Uncertainty Boundaries</h3>
              <p className="explainer mt-1">
                Hyper-rectangular partitions of feature space where predictions exhibit low mean certainty or high output variance.
              </p>
            </div>

            {regionsError ? (
              <div className="utility-panel-rose text-xs text-rose-700 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                <span>Failed to compute uncertainty regions: {regionsError}</span>
              </div>
            ) : regions && regions.length > 0 ? (
              <div className="overflow-y-auto max-h-64 pr-1">
                <div className="space-y-2">
                  {regions.map((region, idx) => (
                    <div key={idx} className="bg-ink border-2 border-line p-3 font-mono text-xs shadow-[2px_2px_0px_#211C19] space-y-1">
                      <div className="flex items-center justify-between border-b border-line pb-1">
                        <span className="badge-research">REGION 0{idx + 1}</span>
                        <div className="flex items-center gap-3 text-[10px]">
                          <span>Mean Conf: <strong className="text-rose-600">{region.mean_confidence.toFixed(3)}</strong></span>
                          <span>Density: <strong>{(region.sample_density * 100).toFixed(1)}%</strong></span>
                        </div>
                      </div>
                      <p className="text-paper font-bold pt-1">
                        {formatBounds(region.feature_bounds)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="editorial-card-white text-center py-12">
                <ShieldCheck className="h-8 w-8 text-emerald-600 mx-auto mb-2" />
                <span className="font-serif font-bold text-base text-paper block">No Volatile Regions Extracted</span>
                <span className="explainer max-w-xs mx-auto mt-1">
                  Predictions are homogeneous across all probed feature hyperplanes.
                </span>
              </div>
            )}
          </div>

          <div className="flex items-start gap-2.5 bg-ink p-3 border-2 border-line text-[11px] font-mono text-mute shadow-[2px_2px_0px_#211C19]">
            <Info className="h-4 w-4 text-paper shrink-0 mt-0.5" />
            <p>
              Uncertainty regions are dynamically fitted using a scikit-learn DecisionTreeRegressor over the 1,000 synthetic LHS probe outcomes.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
