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
  Activity,
  Compass,
  AlertTriangle,
  FileSpreadsheet,
  Layers,
  ShieldCheck,
  TrendingDown,
  Info,
} from "lucide-react";

export default function FingerprintViewer() {
  const params = useParams();
  const router = useRouter();
  const modelId = params.id as string;

  const { data: model, loading: modelLoading, error: modelError } = useModelDetail(modelId);
  const { data: fingerprints, loading: fpLoading, error: fpError } = useModelFingerprints(modelId);

  // Take the latest fingerprint as the active baseline
  const activeFingerprint = fingerprints && fingerprints.length > 0 ? fingerprints[0] : undefined;

  const {
    data: regions,
    loading: regionsLoading,
    error: regionsError,
  } = useUncertaintyRegions(activeFingerprint?.id);

  if (modelLoading || fpLoading || (activeFingerprint && regionsLoading)) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-slate-800 rounded" />
        <div className="h-10 w-64 bg-slate-800 rounded" />
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
          The model ID "{modelId}" does not exist.
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

  if (fpError || !activeFingerprint) {
    return (
      <div className="glass-panel max-w-lg mx-auto p-8 text-center rounded-2xl mt-12">
        <div className="p-3 w-fit mx-auto rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 mb-4">
          <Layers className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">No Behavioral Baseline</h2>
        <p className="text-slate-400 text-sm mb-6">
          This model has not been probed yet. You must complete a synthetic probe session to generate its behavioral fingerprint and FAISS index.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href={`/models/${model.id}`}
            className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-medium transition-colors text-sm"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Format confidence histogram (10 bins)
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

  // Helper to format bounds for humans
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
    <div className="space-y-6">
      {/* Back button & title */}
      <div className="space-y-1">
        <Link
          href={`/models/${model.id}`}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors w-fit"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Behavioral Fingerprint
          </h1>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 uppercase tracking-wider">
            Baseline
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Deterministic probe autopsy details generated on{" "}
          {new Date(activeFingerprint.created_at).toLocaleDateString(undefined, {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
        </p>
      </div>

      {/* Stats Summary Panel */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4.5 rounded-2xl">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Probing Count
          </p>
          <p className="text-xl font-bold text-white mt-1">1,000</p>
        </div>
        <div className="glass-panel p-4.5 rounded-2xl">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Mean Confidence
          </p>
          <p className="text-xl font-bold text-white mt-1">
            {activeFingerprint.mean_confidence.toFixed(4)}
          </p>
        </div>
        <div className="glass-panel p-4.5 rounded-2xl">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Entropy
          </p>
          <p className="text-xl font-bold text-white mt-1">
            {activeFingerprint.entropy.toFixed(4)}
          </p>
        </div>
        <div className="glass-panel p-4.5 rounded-2xl">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Low Conf Rate
          </p>
          <p className="text-xl font-bold text-white mt-1">
            {(activeFingerprint.uncertainty_rate * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Two Panels Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Panel 1: Confidence Histogram */}
        <div className="glass-panel p-5 rounded-2xl space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Confidence Histogram
            </h3>
            <p className="text-[11px] text-slate-400">
              Distribution of prediction confidence values during synthetic probing
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={histogramData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1F293D" vertical={false} />
                <XAxis
                  dataKey="bin"
                  stroke="#475569"
                  fontSize={9}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#475569"
                  fontSize={9}
                  tickLine={false}
                  axisLine={false}
                  unit="%"
                />
                <Tooltip
                  formatter={(value: any) => [`${value}%`, "Density"]}
                  contentStyle={{
                    backgroundColor: "#161B2E",
                    borderColor: "#1F293D",
                    borderRadius: "8px",
                    fontSize: "11px",
                    color: "#f1f5f9",
                  }}
                />
                <Bar dataKey="fraction" radius={[4, 4, 0, 0]}>
                  {histogramData.map((entry, index) => {
                    // Highlight low confidence (< 0.6) with amber/rose, higher with teal
                    const binVal = index / 10;
                    let fill = "#0D9488"; // teal
                    if (binVal < 0.6) {
                      fill = binVal < 0.3 ? "#F43F5E" : "#F59E0B"; // rose / amber
                    }
                    return <Cell key={`cell-${index}`} fill={fill} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Panel 2: Uncertainty Regions */}
        <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Uncertainty Regions
              </h3>
              <p className="text-[11px] text-slate-400">
                Partitions of input feature space where model predictions are highly volatile
              </p>
            </div>

            {regionsError ? (
              <div className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs">
                <AlertTriangle className="h-4.5 w-4.5" />
                <span>Failed to compute uncertainty regions: {regionsError}</span>
              </div>
            ) : regions && regions.length > 0 ? (
              <div className="overflow-y-auto max-h-56 pr-1">
                <table className="min-w-full divide-y divide-darkBorder text-left">
                  <thead>
                    <tr>
                      <th className="pb-2 text-left text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        Feature bounds
                      </th>
                      <th className="pb-2 text-right text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        Mean Conf
                      </th>
                      <th className="pb-2 text-right text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        Density
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-darkBorder/60">
                    {regions.map((region, idx) => (
                      <tr key={idx} className="hover:bg-darkHover/10">
                        <td className="py-2.5 text-xs font-mono text-cyan-300">
                          {formatBounds(region.feature_bounds)}
                        </td>
                        <td className="py-2.5 text-right text-xs text-white font-semibold">
                          {region.mean_confidence.toFixed(3)}
                        </td>
                        <td className="py-2.5 text-right text-xs text-slate-400">
                          {(region.sample_density * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center p-6 bg-slate-900/30 rounded-xl border border-darkBorder/40 py-10">
                <ShieldCheck className="h-8 w-8 text-emerald-500/60 mb-2" />
                <span className="text-xs text-slate-400 font-medium">No Uncertainty Regions</span>
                <span className="text-[10px] text-slate-500 mt-1 max-w-[240px]">
                  Model predictions are stable and homogeneous across the entire input space.
                </span>
              </div>
            )}
          </div>

          <div className="flex items-start gap-2 bg-slate-950/40 p-3 rounded-xl border border-darkBorder/30 mt-4 text-[10px] text-slate-400 leading-relaxed">
            <Info className="h-4 w-4 text-teal-400 shrink-0 mt-0.5" />
            <span>
              Uncertainty regions are extracted dynamically using a scikit-learn decision tree fitted on the 1,000 synthetic LHS probe results. Bounds define hyper-rectangles with low mean confidence and high variance.
            </span>
          </div>
        </div>

      </div>
    </div>
  );
}
