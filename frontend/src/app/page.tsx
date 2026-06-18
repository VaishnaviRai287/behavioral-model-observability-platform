"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useModels, useModelHealth } from "@/hooks/useModelHealth";
import { api, ModelListItem } from "@/lib/api";
import {
  Search,
  Database,
  Cpu,
  Trash2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  PlusCircle,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

// Sub-component for each row to fetch its own health dynamically
function ModelRow({
  model,
  onDelete,
}: {
  model: ModelListItem;
  onDelete: (id: string) => void;
}) {
  const { data: health, error: healthError } = useModelHealth(model.id);
  const [deleting, setDeleting] = useState(false);

  // Health color mapping
  let healthIndicator = (
    <div className="flex items-center gap-1.5 text-slate-400">
      <span className="h-2.5 w-2.5 rounded-full bg-slate-500 animate-pulse" />
      <span>Loading</span>
    </div>
  );

  if (health) {
    if (health.active_alerts > 0) {
      // Simple logic: if active alerts, color based on severity (if we had it), or amber/red.
      // Let's assume > 2 alerts = red, 1-2 = amber
      if (health.active_alerts >= 2) {
        healthIndicator = (
          <div className="flex items-center gap-1.5 text-rose-400 font-semibold bg-rose-500/10 border border-rose-500/30 px-2.5 py-0.5 rounded-full text-xs">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
            <span>Red Alert ({health.active_alerts})</span>
          </div>
        );
      } else {
        healthIndicator = (
          <div className="flex items-center gap-1.5 text-amber-400 font-semibold bg-amber-500/10 border border-amber-500/30 px-2.5 py-0.5 rounded-full text-xs">
            <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            <span>Amber Alert ({health.active_alerts})</span>
          </div>
        );
      }
    } else {
      healthIndicator = (
        <div className="flex items-center gap-1.5 text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 rounded-full text-xs">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span>Healthy</span>
        </div>
      );
    }
  } else if (healthError) {
    healthIndicator = (
      <div className="flex items-center gap-1.5 text-rose-400">
        <AlertTriangle className="h-4.5 w-4.5" />
        <span>Error</span>
      </div>
    );
  }

  const handleDeleteClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete model "${model.name}"?`)) {
      setDeleting(true);
      try {
        await api.deleteModel(model.id);
        onDelete(model.id);
      } catch (err: any) {
        alert(`Failed to delete model: ${err.message}`);
      } finally {
        setDeleting(false);
      }
    }
  };

  const getFrameworkBadge = (fw: string) => {
    const fwLower = fw.toLowerCase();
    if (fwLower.includes("sklearn") || fwLower.includes("scikit")) {
      return (
        <span className="bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs px-2.5 py-0.5 rounded-full font-medium">
          scikit-learn
        </span>
      );
    }
    if (fwLower.includes("torch") || fwLower.includes("pytorch")) {
      return (
        <span className="bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs px-2.5 py-0.5 rounded-full font-medium">
          PyTorch
        </span>
      );
    }
    if (fwLower.includes("tensorflow") || fwLower.includes("keras")) {
      return (
        <span className="bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs px-2.5 py-0.5 rounded-full font-medium">
          TensorFlow
        </span>
      );
    }
    return (
      <span className="bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs px-2.5 py-0.5 rounded-full font-medium">
        ONNX
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === "ready") {
      return (
        <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/20 w-fit">
          <CheckCircle className="h-3 w-3" />
          Ready
        </span>
      );
    }
    if (s === "failed") {
      return (
        <span className="flex items-center gap-1 text-xs text-rose-400 font-medium bg-rose-500/5 px-2 py-0.5 rounded border border-rose-500/20 w-fit">
          <XCircle className="h-3 w-3" />
          Failed
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-xs text-slate-400 font-medium bg-slate-500/5 px-2 py-0.5 rounded border border-slate-500/20 w-fit animate-pulse">
        <span className="h-2 w-2 rounded-full bg-slate-400" />
        {status}
      </span>
    );
  };

  return (
    <tr className="hover:bg-darkHover/40 border-b border-darkBorder transition-all duration-150 group cursor-pointer">
      <td className="px-6 py-4.5 whitespace-nowrap">
        <Link href={`/models/${model.id}`} className="block">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-slate-800 text-slate-400 group-hover:text-teal-400 group-hover:bg-teal-500/10 transition-colors">
              <Database className="h-4.5 w-4.5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white group-hover:text-teal-400 transition-colors">
                {model.name}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                {model.id}
              </div>
            </div>
          </div>
        </Link>
      </td>
      <td className="px-6 py-4.5 whitespace-nowrap">
        <Link href={`/models/${model.id}`} className="block">
          {getFrameworkBadge(model.framework)}
        </Link>
      </td>
      <td className="px-6 py-4.5 whitespace-nowrap">
        <Link href={`/models/${model.id}`} className="block">
          {getStatusBadge(model.status)}
        </Link>
      </td>
      <td className="px-6 py-4.5 whitespace-nowrap">
        <Link href={`/models/${model.id}`} className="block">
          {healthIndicator}
        </Link>
      </td>
      <td className="px-6 py-4.5 whitespace-nowrap text-sm text-slate-400">
        <Link href={`/models/${model.id}`} className="block">
          {new Date(model.created_at).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Link>
      </td>
      <td className="px-6 py-4.5 whitespace-nowrap text-right text-sm font-medium">
        <div className="flex items-center justify-end gap-2">
          <Link
            href={`/models/${model.id}`}
            className="p-1.5 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 hover:bg-teal-500/20 hover:border-teal-500/40 transition-colors"
          >
            <ArrowRight className="h-4 w-4" />
          </Link>
          <button
            onClick={handleDeleteClick}
            disabled={deleting}
            className="p-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 hover:border-rose-500/40 transition-colors disabled:opacity-50"
            title="Delete Model"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function ModelsRegistry() {
  const { data: models, loading, error } = useModels();
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [localModels, setLocalModels] = useState<ModelListItem[]>([]);

  // Modal Ingestion States
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadSchema, setUploadSchema] = useState(
    JSON.stringify(
      {
        features: [
          { name: "tenure", type: "float", min: 0, max: 100 },
          { name: "age", type: "float", min: 18, max: 80 },
          { name: "balance", type: "float", min: 0, max: 200000 },
        ],
      },
      null,
      2
    )
  );
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStep, setUploadStep] = useState<
    "idle" | "uploading" | "probing" | "fingerprinting" | "done"
  >("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Update local model list when query completes
  React.useEffect(() => {
    if (models) {
      setLocalModels(models);
    }
  }, [models]);

  const handleModelDeleted = (id: string) => {
    setLocalModels((prev) => prev.filter((m) => m.id !== id));
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadName || !uploadSchema || !uploadFile) {
      setUploadError("All fields are required.");
      return;
    }
    setUploadError(null);
    setUploadStep("uploading");
    try {
      // Step 1: Upload Model
      const model = await api.uploadModel(uploadName, uploadSchema, uploadFile);

      // Step 2: Auto-Run Probe Suite (100 synthetic probes)
      setUploadStep("probing");
      const session = await api.probeModel(model.id, 100);

      // Step 3: Compile Behavioral Fingerprint baseline
      setUploadStep("fingerprinting");
      await api.generateFingerprint(session.id);

      setUploadStep("done");
      // Redirect to Dashboard
      router.push(`/models/${model.id}`);
    } catch (err: any) {
      setUploadStep("idle");
      setUploadError(err.message || "Failed to complete model ingestion.");
    }
  };

  const filteredModels = localModels.filter(
    (m) =>
      m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Stats computation
  const totalModels = localModels.length;
  const readyModels = localModels.filter((m) => m.status.toLowerCase() === "ready").length;

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="h-8 w-48 bg-slate-800 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-28 bg-darkCard border border-darkBorder rounded-2xl animate-pulse" />
          <div className="h-28 bg-darkCard border border-darkBorder rounded-2xl animate-pulse" />
          <div className="h-28 bg-darkCard border border-darkBorder rounded-2xl animate-pulse" />
        </div>
        <div className="h-64 bg-darkCard border border-darkBorder rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel max-w-2xl mx-auto p-8 text-center rounded-2xl border-rose-500/20 mt-12">
        <div className="p-3 w-fit mx-auto rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-4">
          <AlertTriangle className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Connection Failed</h2>
        <p className="text-slate-400 text-sm mb-6">
          Unable to establish connection to the ModelMesh API. Check that the FastAPI container is running.
        </p>
        <div className="bg-rose-500/5 border border-rose-500/20 rounded-lg p-3 text-left font-mono text-xs text-rose-300 max-h-48 overflow-y-auto mb-6">
          {error}
        </div>
        <button
          onClick={() => window.location.reload()}
          className="px-5 py-2.5 bg-rose-500 text-white rounded-xl font-medium hover:bg-rose-600 transition-colors shadow-lg shadow-rose-500/20 text-sm"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Title & Hero */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Model Registry
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Deterministic model autopsies, synthetic behavior probing, and real-time observability indicators.
          </p>
        </div>

        {/* Upload Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setUploadName("");
              setUploadFile(null);
              setUploadStep("idle");
              setUploadError(null);
              setIsUploadModalOpen(true);
            }}
            className="flex items-center gap-2 px-5 py-2.5 bg-teal-500 hover:bg-teal-600 text-white rounded-xl font-semibold transition-all shadow-lg shadow-teal-500/10 text-sm hover:scale-[1.02] active:scale-[0.98]"
          >
            <PlusCircle className="h-4.5 w-4.5 text-white" />
            <span>Upload Model</span>
          </button>
        </div>
      </div>

      {/* Aggregate Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute right-0 bottom-0 translate-x-2 translate-y-2 opacity-5 text-teal-400">
            <Database className="h-28 w-28" />
          </div>
          <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            Registered Models
          </p>
          <div className="flex items-baseline gap-2.5 mt-2">
            <span className="text-4xl font-extrabold text-white">
              {totalModels}
            </span>
            <span className="text-xs text-slate-500">models total</span>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute right-0 bottom-0 translate-x-2 translate-y-2 opacity-5 text-emerald-400">
            <CheckCircle className="h-28 w-28" />
          </div>
          <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            Active Serving
          </p>
          <div className="flex items-baseline gap-2.5 mt-2">
            <span className="text-4xl font-extrabold text-white">
              {readyModels}
            </span>
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-0.5">
              <TrendingUp className="h-3.5 w-3.5" />
              100% online
            </span>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group border-amber-500/10">
          <div className="absolute right-0 bottom-0 translate-x-2 translate-y-2 opacity-5 text-amber-400">
            <AlertTriangle className="h-28 w-28" />
          </div>
          <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            Platform Status
          </p>
          <div className="flex items-baseline gap-2.5 mt-2">
            <span className="text-2xl font-bold text-slate-200">
              Operational
            </span>
            <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded uppercase">
              Stable
            </span>
          </div>
        </div>
      </div>

      {/* Main Table Panel */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        {/* Table Search Header */}
        <div className="px-6 py-4.5 border-b border-darkBorder flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h2 className="text-base font-semibold text-white">Registered Models</h2>
          
          {/* Search Box */}
          <div className="relative max-w-xs w-full">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-slate-500" />
            </span>
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full pl-9 pr-4 py-2 bg-slate-900 border border-darkBorder rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50 focus:ring-1 focus:ring-teal-500/50 text-sm transition-all"
            />
          </div>
        </div>

        {/* Table Data */}
        {filteredModels.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-darkBorder">
              <thead className="bg-slate-900/50">
                <tr>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider"
                  >
                    Model
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider"
                  >
                    Framework
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider"
                  >
                    Serving Status
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider"
                  >
                    Observability Health
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider"
                  >
                    Uploaded
                  </th>
                  <th scope="col" className="relative px-6 py-3.5">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder bg-transparent">
                {filteredModels.map((model) => (
                  <ModelRow
                    key={model.id}
                    model={model}
                    onDelete={handleModelDeleted}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-16 text-center max-w-md mx-auto">
            <div className="p-3 w-fit mx-auto rounded-full bg-slate-800 text-slate-500 mb-4 border border-darkBorder">
              <Cpu className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1">
              {searchTerm ? "No results found" : "No models registered"}
            </h3>
            <p className="text-xs text-slate-400">
              {searchTerm
                ? "Try adjusting your search criteria to locate your model."
                : "Get started by running the demo scripts or uploading your model artifacts."}
            </p>
          </div>
        )}
      </div>

      {/* Model Upload Ingestion Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-xl rounded-2xl overflow-hidden shadow-2xl border-darkBorder flex flex-col max-h-[90vh]">
            
            {/* Modal Header */}
            <div className="px-6 py-4.5 border-b border-darkBorder flex items-center justify-between bg-slate-900/40">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Database className="h-4.5 w-4.5 text-teal-400" />
                Upload Trained Model
              </h3>
              <button
                onClick={() => {
                  if (uploadStep === "idle" || uploadStep === "done") {
                    setIsUploadModalOpen(false);
                    setUploadError(null);
                  }
                }}
                disabled={uploadStep !== "idle" && uploadStep !== "done"}
                className="text-slate-400 hover:text-white transition-colors disabled:opacity-50 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleUploadSubmit} className="p-6 space-y-4 overflow-y-auto flex-grow">
              {uploadError && (
                <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadStep !== "idle" ? (
                /* Stepper Loading screen */
                <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
                  <div className="relative flex items-center justify-center h-14 w-14 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-500/10 opacity-75"></span>
                    <Cpu className="h-6 w-6 animate-spin" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      {uploadStep === "uploading" && "1. Uploading Model Artifact..."}
                      {uploadStep === "probing" && "2. Running LHS Synthetic Probe Suite..."}
                      {uploadStep === "fingerprinting" && "3. Compiling Behavioral Baseline..."}
                      {uploadStep === "done" && "4. Ingestion Complete!"}
                    </h4>
                    <p className="text-xs text-slate-400 max-w-[320px] mx-auto">
                      {uploadStep === "uploading" && "Saving file and automatically detecting ML framework (scikit-learn/PyTorch/ONNX)..."}
                      {uploadStep === "probing" && "Executing 100 synthetic Latin Hypercube probes to analyze model confidence space..."}
                      {uploadStep === "fingerprinting" && "Building entropy profiles, confidence histogram bins, and storing FAISS index..."}
                      {uploadStep === "done" && "Redirecting to your new model dashboard..."}
                    </p>
                  </div>
                </div>
              ) : (
                /* Input Form */
                <>
                  {/* Model Name */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Model Name
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. churn_prediction_model"
                      value={uploadName}
                      onChange={(e) => setUploadName(e.target.value)}
                      className="block w-full px-4 py-2.5 bg-slate-900 border border-darkBorder rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50 focus:ring-1 focus:ring-teal-500/50 text-sm transition-all"
                    />
                  </div>

                  {/* Schema Textarea */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Input Schema (JSON)
                      </label>
                      <span className="text-[10px] text-slate-500 font-normal">
                        Defines names, bounds, and features order
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2 py-1">
                      <button
                        type="button"
                        onClick={() => setUploadSchema(JSON.stringify({
                          features: [
                            { name: "x1", type: "float", min: 0.0, max: 1.0 },
                            { name: "x2", type: "float", min: 0.0, max: 1.0 }
                          ]
                        }, null, 2))}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-teal-400 hover:text-teal-300 border border-darkBorder rounded text-[10px] font-semibold transition-colors"
                      >
                        Load Demo Model Schema (x1, x2)
                      </button>
                      <button
                        type="button"
                        onClick={() => setUploadSchema(JSON.stringify({
                          features: [
                            { name: "tenure", type: "float", min: 0, max: 100 },
                            { name: "age", type: "float", min: 18, max: 80 },
                            { name: "balance", type: "float", min: 0, max: 200000 },
                          ]
                        }, null, 2))}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-300 border border-darkBorder rounded text-[10px] font-semibold transition-colors"
                      >
                        Load Churn Model Schema
                      </button>
                    </div>
                    <textarea
                      rows={6}
                      required
                      value={uploadSchema}
                      onChange={(e) => setUploadSchema(e.target.value)}
                      className="block w-full px-4 py-2.5 bg-slate-900 border border-darkBorder rounded-xl text-slate-200 font-mono text-xs focus:outline-none focus:border-teal-500/50 focus:ring-1 focus:ring-teal-500/50 transition-all"
                    />
                  </div>

                  {/* Model File Input */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Model File (.pkl, .joblib, .pt, .pth, .onnx, .h5, .keras, .zip, .tar.gz)
                    </label>
                    <div className="relative border-2 border-dashed border-darkBorder rounded-xl p-6 flex flex-col items-center justify-center bg-slate-900/30 hover:bg-slate-900/50 transition-all cursor-pointer">
                      <input
                        type="file"
                        required
                        accept=".pkl,.joblib,.pt,.pth,.onnx,.h5,.keras,.zip,.tar.gz,.tgz"
                        onChange={(e) => {
                          if (e.target.files && e.target.files.length > 0) {
                            setUploadFile(e.target.files[0]);
                          }
                        }}
                        className="absolute inset-0 opacity-0 cursor-pointer"
                      />
                      <Cpu className="h-7 w-7 text-slate-500 mb-2" />
                      <span className="text-xs text-slate-400 font-medium">
                        {uploadFile ? uploadFile.name : "Select or drag model file here"}
                      </span>
                      {uploadFile && (
                        <span className="text-[10px] text-slate-500 mt-1">
                          {(uploadFile.size / 1024).toFixed(1)} KB
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="pt-4 flex gap-3">
                    <button
                      type="button"
                      onClick={() => setIsUploadModalOpen(false)}
                      className="flex-1 py-2.5 bg-slate-900 hover:bg-slate-850 text-slate-300 border border-darkBorder rounded-xl font-medium transition-colors text-sm"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="flex-1 py-2.5 bg-teal-500 hover:bg-teal-600 text-white rounded-xl font-semibold transition-all shadow-lg shadow-teal-500/10 text-sm hover:scale-[1.01]"
                    >
                      Ingest & Auto-Probe
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
