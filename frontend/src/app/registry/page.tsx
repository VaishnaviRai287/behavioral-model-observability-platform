"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useModels, useModelHealth } from "@/hooks/useModelHealth";
import {
  api,
  ModelListItem,
  getStoredApiKey,
  setStoredApiKey,
  getPendingKeyReveal,
  setPendingKeyReveal,
  clearPendingKeyReveal,
  getStoredKeyOwnerName,
  setStoredKeyOwnerName,
} from "@/lib/api";
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
  KeyRound,
  Copy,
  Check,
  RefreshCw,
  LayoutGrid,
  List,
  Layers,
  Terminal,
} from "lucide-react";

// API-key bootstrap/regenerate panel — Utility Panel Family
function ApiKeyPanel({ onKeyChange }: { onKeyChange?: () => void }) {
  const [storedKey, setStoredKeyState] = useState<string | null>(null);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [manualKey, setManualKey] = useState("");
  const [name, setName] = useState("");
  const [showLostKey, setShowLostKey] = useState(false);
  const [adminSecret, setAdminSecret] = useState("");
  const [lostKeyError, setLostKeyError] = useState<string | null>(null);
  const inFlightRef = React.useRef(false);

  React.useEffect(() => {
    setStoredKeyState(getStoredApiKey());
    setName(getStoredKeyOwnerName() || "");
    const pending = getPendingKeyReveal();
    if (pending) setNewlyCreatedKey(pending);
  }, []);

  const handleGenerate = async () => {
    if (inFlightRef.current) return;
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Enter your name first — it's how a lost key gets matched back to you later.");
      return;
    }
    inFlightRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createApiKey(trimmedName);
      setStoredApiKey(created.key);
      setStoredKeyState(created.key);
      setStoredKeyOwnerName(trimmedName);
      setPendingKeyReveal(created.key);
      setNewlyCreatedKey(created.key);
      onKeyChange?.();
    } catch (err: any) {
      setError(err.message || "Failed to create API key.");
    } finally {
      inFlightRef.current = false;
      setBusy(false);
    }
  };

  const handleLostKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inFlightRef.current) return;
    const trimmedName = name.trim();
    const trimmedSecret = adminSecret.trim();
    if (!trimmedName || !trimmedSecret) return;
    inFlightRef.current = true;
    setBusy(true);
    setLostKeyError(null);
    try {
      const created = await api.resetApiKey(trimmedName, trimmedSecret);
      setStoredApiKey(created.key);
      setStoredKeyState(created.key);
      setStoredKeyOwnerName(trimmedName);
      setPendingKeyReveal(created.key);
      setNewlyCreatedKey(created.key);
      setShowLostKey(false);
      setAdminSecret("");
      onKeyChange?.();
    } catch (err: any) {
      setLostKeyError(err.message || "Failed to reset API key.");
    } finally {
      inFlightRef.current = false;
      setBusy(false);
    }
  };

  const handleRegenerate = async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createApiKey(getStoredKeyOwnerName() || "dashboard");
      const previousKey = storedKey;
      setStoredApiKey(created.key);
      setStoredKeyState(created.key);
      setPendingKeyReveal(created.key);
      setNewlyCreatedKey(created.key);
      onKeyChange?.();
      if (previousKey) {
        try {
          const keys = await api.listApiKeys();
          const previous = keys.find((k) => previousKey.startsWith(k.key_prefix));
          if (previous) await api.revokeApiKey(previous.id);
        } catch {}
      }
    } catch (err: any) {
      setError(err.message || "Failed to regenerate API key.");
    } finally {
      inFlightRef.current = false;
      setBusy(false);
    }
  };

  const handleCopy = () => {
    if (!newlyCreatedKey) return;
    navigator.clipboard.writeText(newlyCreatedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDone = () => {
    clearPendingKeyReveal();
    setNewlyCreatedKey(null);
  };

  const handleUseManualKey = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = manualKey.trim();
    if (!trimmed) return;
    setStoredApiKey(trimmed);
    setStoredKeyState(trimmed);
    setManualKey("");
    setShowManualEntry(false);
    onKeyChange?.();
  };

  if (newlyCreatedKey) {
    return (
      <div className="utility-panel-amber space-y-3 shadow-[4px_4px_0px_#211C19]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-amber-700" />
            <span className="badge-research-finding">AUTHENTICATION KEY GENERATED</span>
          </div>
          <span className="label-mono font-bold text-amber-800">SAVE ONCE</span>
        </div>
        <div className="flex items-center gap-2 bg-ink border-2 border-line px-4 py-2.5 font-mono text-sm text-paper overflow-x-auto shadow-[2px_2px_0px_#211C19]">
          <span className="flex-grow font-bold">{newlyCreatedKey}</span>
          <button
            onClick={handleCopy}
            className="btn-physical py-1 px-3 text-xs"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy Key"}
          </button>
        </div>
        <p className="explainer">
          Use as <code className="text-paper font-bold">Authorization: Bearer &lt;key&gt;</code> on programmatic API calls. Saved automatically in this browser.
        </p>
        <button
          onClick={handleDone}
          className="btn-physical-accent py-1 px-4 text-xs"
        >
          Acknowledge & Continue →
        </button>
      </div>
    );
  }

  if (storedKey) {
    return (
      <div className="utility-panel flex flex-wrap items-center justify-between gap-3 shadow-[4px_4px_0px_#211C19]">
        <div className="flex items-center gap-3">
          <div className="p-1.5 border border-line bg-panel">
            <KeyRound className="h-4 w-4 text-paper" />
          </div>
          <div>
            <span className="badge-research">AUTHENTICATION ACTIVE</span>
            <p className="font-mono text-xs text-mute mt-0.5">Key Prefix: <strong className="text-paper">{storedKey.slice(0, 12)}...</strong></p>
          </div>
        </div>
        <button
          onClick={handleRegenerate}
          disabled={busy}
          className="btn-physical text-xs py-1.5 px-3"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
          Regenerate Key
        </button>
      </div>
    );
  }

  return (
    <div className="utility-panel-amber space-y-3 shadow-[4px_4px_0px_#211C19]">
      <div>
        <span className="badge-research-finding">AUTHENTICATION REQUIRED</span>
        <p className="explainer mt-1 text-paper/90">
          Generate an API key to enable programmatic inference & monitoring calls to the ModelMesh backend.
          Bootstrap-generate only works once, ever, on a given backend — if someone else already has a key,
          ask them to share it instead of generating a new one.
        </p>
        {error && <p className="text-xs font-mono text-rose-700 mt-1">{error}</p>}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="Your name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-grow min-w-[180px] px-3 py-2 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent"
        />
        <button
          onClick={handleGenerate}
          disabled={busy}
          className="btn-physical-accent"
        >
          <KeyRound className="h-4 w-4" />
          {busy ? "Generating..." : "Generate API Key"}
        </button>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {!showManualEntry ? (
          <button
            type="button"
            onClick={() => setShowManualEntry(true)}
            className="label-mono text-paper hover:text-accent transition-colors underline underline-offset-2"
          >
            Already have a key? Paste it instead →
          </button>
        ) : (
          <form onSubmit={handleUseManualKey} className="flex flex-wrap items-center gap-2 w-full pt-1">
            <input
              type="text"
              autoFocus
              placeholder="mmk_..."
              value={manualKey}
              onChange={(e) => setManualKey(e.target.value)}
              className="flex-grow min-w-[240px] px-3 py-2 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent"
            />
            <button type="submit" className="btn-physical-accent text-xs py-2 px-3">
              Use This Key
            </button>
            <button
              type="button"
              onClick={() => {
                setShowManualEntry(false);
                setManualKey("");
              }}
              className="btn-physical text-xs py-2 px-3"
            >
              Cancel
            </button>
          </form>
        )}

        {!showLostKey ? (
          <button
            type="button"
            onClick={() => setShowLostKey(true)}
            className="label-mono text-paper hover:text-accent transition-colors underline underline-offset-2"
          >
            Lost your key? Reset it →
          </button>
        ) : (
          <form onSubmit={handleLostKey} className="w-full pt-1 space-y-2">
            <p className="explainer">
              Requires the deployer-set admin secret — resets only the key registered under your name,
              nobody else&rsquo;s.
            </p>
            {lostKeyError && <p className="text-xs font-mono text-rose-700">{lostKeyError}</p>}
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                placeholder="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="min-w-[160px] px-3 py-2 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent"
              />
              <input
                type="password"
                autoFocus
                placeholder="Admin secret"
                value={adminSecret}
                onChange={(e) => setAdminSecret(e.target.value)}
                className="flex-grow min-w-[160px] px-3 py-2 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent"
              />
              <button type="submit" disabled={busy} className="btn-physical-accent text-xs py-2 px-3">
                {busy ? "Resetting..." : "Reset My Key"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowLostKey(false);
                  setAdminSecret("");
                  setLostKeyError(null);
                }}
                className="btn-physical text-xs py-2 px-3"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// Sub-component for Linear-style Model Item (Linear Row & Card rendering)
function ModelItem({
  model,
  onDelete,
  viewMode,
}: {
  model: ModelListItem;
  onDelete: (id: string) => void;
  viewMode: "list" | "grid";
}) {
  const { data: health, error: healthError } = useModelHealth(model.id);
  const [deleting, setDeleting] = useState(false);

  let healthIndicator = (
    <span className="badge-research text-mute">
      <span className="h-1.5 w-1.5 rounded-full bg-mute" />
      LOADING
    </span>
  );

  if (health) {
    if (health.active_alerts > 0) {
      if (health.active_alerts >= 2) {
        healthIndicator = (
          <span className="badge-research border-rose-400 bg-rose-50 text-rose-700">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
            CRITICAL ({health.active_alerts})
          </span>
        );
      } else {
        healthIndicator = (
          <span className="badge-research border-amber-400 bg-amber-50 text-amber-700">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            WARNING ({health.active_alerts})
          </span>
        );
      }
    } else {
      healthIndicator = (
        <span className="badge-research border-emerald-400 bg-emerald-50 text-emerald-700">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          HEALTHY
        </span>
      );
    }
  } else if (healthError) {
    healthIndicator = (
      <span className="badge-research border-rose-300 text-rose-600">
        <AlertTriangle className="h-3 w-3" />
        ERROR
      </span>
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
    let label = "ONNX";
    if (fwLower.includes("sklearn") || fwLower.includes("scikit")) label = "scikit-learn";
    if (fwLower.includes("torch") || fwLower.includes("pytorch")) label = "PyTorch";
    if (fwLower.includes("tensorflow") || fwLower.includes("keras")) label = "TensorFlow";
    return <span className="badge-research">{label}</span>;
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === "ready") {
      return (
        <span className="badge-research border-emerald-400 text-emerald-700">
          <CheckCircle className="h-3 w-3 text-emerald-600" />
          READY
        </span>
      );
    }
    if (s === "failed") {
      return (
        <span className="badge-research border-rose-400 text-rose-700">
          <XCircle className="h-3 w-3 text-rose-600" />
          FAILED
        </span>
      );
    }
    return (
      <span className="badge-research text-paper">
        <span className="h-1.5 w-1.5 rounded-full bg-mute animate-pulse" />
        {status}
      </span>
    );
  };

  // GRID VIEW CARD
  if (viewMode === "grid") {
    return (
      <div className="editorial-card shadow-[5px_5px_0px_#211C19] flex flex-col justify-between space-y-4 hover:-translate-y-0.5 transition-all">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            {getFrameworkBadge(model.framework)}
            {healthIndicator}
          </div>
          <Link href={`/models/${model.id}`} className="block group">
            <h3 className="font-serif font-bold text-xl text-paper group-hover:text-accent transition-colors">
              {model.name}
            </h3>
            <p className="font-mono text-[10px] text-mute mt-0.5 truncate">
              ID: {model.id}
            </p>
          </Link>
        </div>

        <div className="pt-3 border-t border-line flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="label-mono block text-[9px]">Serving Status</span>
            {getStatusBadge(model.status)}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDeleteClick}
              disabled={deleting}
              className="p-1.5 border border-line text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
              title="Delete Model"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <Link
              href={`/models/${model.id}`}
              className="btn-physical py-1 px-3 text-xs"
            >
              Open →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // LINEAR-STYLE DENSE LIST ROW (Curated Research Artifact)
  return (
    <div className="bg-ink border-2 border-line p-4 shadow-[3px_3px_0px_#211C19] hover:border-accent hover:-translate-y-0.5 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-center gap-4 flex-grow min-w-0">
        <div className="p-2.5 border-2 border-line bg-panel shrink-0">
          <Database className="h-5 w-5 text-paper" />
        </div>

        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Link
              href={`/models/${model.id}`}
              className="font-serif font-bold text-lg text-paper hover:text-accent transition-colors truncate"
            >
              {model.name}
            </Link>
            {getFrameworkBadge(model.framework)}
          </div>
          <p className="font-mono text-[10px] text-mute truncate">
            ID: {model.id} · Uploaded {new Date(model.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 shrink-0 justify-between sm:justify-end border-t sm:border-t-0 border-line pt-2 sm:pt-0">
        <div className="flex items-center gap-2">
          {getStatusBadge(model.status)}
          {healthIndicator}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDeleteClick}
            disabled={deleting}
            className="p-1.5 border-2 border-line bg-ink text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
            title="Delete Model"
          >
            <Trash2 className="h-4 w-4" />
          </button>
          <Link
            href={`/models/${model.id}`}
            className="btn-physical py-1.5 px-3 text-xs"
          >
            Open →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ModelsRegistry() {
  const { data: models, loading, error, refetch: refetchModels } = useModels();
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [localModels, setLocalModels] = useState<ModelListItem[]>([]);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");

  // Ingestion Modal States
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
      const model = await api.uploadModel(uploadName, uploadSchema, uploadFile);
      setUploadStep("probing");
      const session = await api.probeModel(model.id, 100);
      setUploadStep("fingerprinting");
      await api.generateFingerprint(session.id);
      setUploadStep("done");
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

  const totalModels = localModels.length;
  const readyModels = localModels.filter((m) => m.status.toLowerCase() === "ready").length;

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 w-64 bg-panel" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-28 editorial-card" />
          <div className="h-28 editorial-card" />
          <div className="h-28 editorial-card" />
        </div>
        <div className="h-64 research-window" />
      </div>
    );
  }

  if (error) {
    const isAuthError = error.toLowerCase().includes("api key");
    return (
      <div className="max-w-2xl mx-auto mt-12 space-y-6">
        <ApiKeyPanel onKeyChange={refetchModels} />
        <div className="utility-panel-rose text-center p-8 space-y-4 shadow-[6px_6px_0px_#211C19]">
          <div className="p-3 w-fit mx-auto border-2 border-rose-400 bg-ink text-rose-600">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="text-2xl font-serif text-paper font-bold">API Connection Failed</h2>
          <p className="explainer">
            {isAuthError
              ? "Generate an API key above to authenticate backend requests."
              : "Unable to connect to the ModelMesh FastAPI server."}
          </p>
          <div className="bg-ink border-2 border-line p-3 text-left font-mono text-xs text-rose-700 max-h-48 overflow-y-auto">
            {error}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="btn-physical-accent mx-auto"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header & Hero */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b-2 border-line pb-6">
        <div>
          <span className="badge-research mb-2">COLLECTION // RESEARCH ARTIFACTS</span>
          <h1 className="font-serif font-bold text-4xl sm:text-5xl text-paper tracking-tight">
            Model Registry
          </h1>
          <p className="explainer mt-1 max-w-xl">
            Curated list of registered ML model artifacts. Each entry has undergone automated boundary probing and FAISS manifold compilation.
          </p>
        </div>

        <button
          onClick={() => {
            setUploadName("");
            setUploadFile(null);
            setUploadStep("idle");
            setUploadError(null);
            setIsUploadModalOpen(true);
          }}
          className="btn-physical-accent shrink-0"
        >
          <PlusCircle className="h-4.5 w-4.5" />
          Upload Model Artifact
        </button>
      </div>

      {/* API Key Panel */}
      <ApiKeyPanel onKeyChange={refetchModels} />

      {/* Aggregate Stats Cards */}
      <div className="space-y-3">
        <span className="badge-research">REGISTRY READOUT</span>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research-baseline">TOTAL ARTIFACTS</span>
            <p className="stat-huge mt-2">{totalModels}</p>
            <p className="explainer mt-1">Models registered in storage</p>
          </div>

          <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research-finding">ACTIVE SERVING</span>
            <p className="stat-huge mt-2 text-paper">{readyModels}</p>
            <p className="explainer mt-1">Verified ready for live inference</p>
          </div>

          <div className="editorial-card-white shadow-[4px_4px_0px_#211C19]">
            <span className="badge-research">PLATFORM HEALTH</span>
            <p className="font-serif font-bold text-2xl mt-2 text-paper">Operational</p>
            <p className="explainer mt-1">LHS + FAISS pipeline online</p>
          </div>
        </div>
      </div>

      {/* Main Model List / Grid Section */}
      <div className="space-y-4">
        {/* Controls bar: Search & List/Grid Toggle */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b-2 border-line pb-3">
          <div className="flex items-center gap-2">
            <span className="badge-research">CATALOG</span>
            <span className="font-mono text-xs font-bold text-paper">
              {filteredModels.length} Models Found
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative max-w-xs w-full">
              <Search className="absolute inset-y-0 left-3 my-auto h-3.5 w-3.5 text-mute" />
              <input
                type="text"
                placeholder="Search models by name or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent shadow-[2px_2px_0px_#211C19]"
              />
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center border-2 border-line bg-ink p-0.5 shadow-[2px_2px_0px_#211C19]">
              <button
                onClick={() => setViewMode("list")}
                className={`p-1.5 font-mono text-xs transition-colors ${
                  viewMode === "list" ? "bg-accent text-ink font-bold" : "text-mute hover:text-paper"
                }`}
                title="Linear Dense List View"
              >
                <List className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode("grid")}
                className={`p-1.5 font-mono text-xs transition-colors ${
                  viewMode === "grid" ? "bg-accent text-ink font-bold" : "text-mute hover:text-paper"
                }`}
                title="Grid View"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Model Data Display */}
        {filteredModels.length > 0 ? (
          <div className={viewMode === "grid" ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" : "space-y-3"}>
            {filteredModels.map((model) => (
              <ModelItem
                key={model.id}
                model={model}
                onDelete={handleModelDeleted}
                viewMode={viewMode}
              />
            ))}
          </div>
        ) : (
          <div className="editorial-card-white text-center py-16 max-w-md mx-auto shadow-[5px_5px_0px_#211C19]">
            <div className="p-3 w-fit mx-auto border-2 border-line bg-panel text-paper mb-3">
              <Cpu className="h-6 w-6" />
            </div>
            <h3 className="font-serif font-bold text-lg text-paper mb-1">
              {searchTerm ? "No matching models found" : "No models registered"}
            </h3>
            <p className="explainer">
              {searchTerm
                ? "Try adjusting your search criteria."
                : "Upload your model artifact to begin automated probing and FAISS indexing."}
            </p>
          </div>
        )}
      </div>

      {/* Model Ingestion Research Window Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-paper/70 backdrop-blur-xs">
          <div className="research-window w-full max-w-xl max-h-[90vh] shadow-[8px_8px_0px_#211C19]">
            <div className="window-titlebar">
              <div className="window-dots">
                <span className="window-dot bg-rose-400" />
                <span className="window-dot bg-amber-400" />
                <span className="window-dot bg-emerald-400" />
              </div>
              <span className="font-mono text-xs font-bold text-paper">RESEARCH_INGESTION // UPLOAD_ARTIFACT</span>
              <button
                onClick={() => {
                  if (uploadStep === "idle" || uploadStep === "done") {
                    setIsUploadModalOpen(false);
                    setUploadError(null);
                  }
                }}
                disabled={uploadStep !== "idle" && uploadStep !== "done"}
                className="font-mono text-xs font-bold text-paper hover:text-accent transition-colors disabled:opacity-50"
              >
                [ ESC ✕ ]
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="window-content p-6 space-y-5 overflow-y-auto">
              {uploadError && (
                <div className="utility-panel-rose text-xs text-rose-700 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadStep !== "idle" ? (
                <div className="py-12 flex flex-col items-center justify-center text-center space-y-5">
                  <div className="relative flex items-center justify-center h-16 w-16 border-2 border-line bg-panel shadow-[4px_4px_0px_#211C19]">
                    <Cpu className="h-8 w-8 text-paper animate-spin" />
                  </div>
                  <div className="space-y-2">
                    <span className="badge-research-finding">
                      {uploadStep === "uploading" && "STEP 1/3 // UPLOADING MODEL"}
                      {uploadStep === "probing" && "STEP 2/3 // RUNNING LHS PROBES"}
                      {uploadStep === "fingerprinting" && "STEP 3/3 // COMPILING FAISS INDEX"}
                      {uploadStep === "done" && "INGESTION COMPLETE"}
                    </span>
                    <h4 className="font-serif font-bold text-xl text-paper">
                      {uploadStep === "uploading" && "Parsing & Framework Detection..."}
                      {uploadStep === "probing" && "Executing 100 LHS Synthetic Probes..."}
                      {uploadStep === "fingerprinting" && "Compiling Latent Activation Manifold..."}
                      {uploadStep === "done" && "Model Successfully Registered!"}
                    </h4>
                    <p className="explainer max-w-sm mx-auto">
                      {uploadStep === "uploading" && "Detecting scikit-learn / PyTorch / TensorFlow / ONNX signatures..."}
                      {uploadStep === "probing" && "Mapping confidence boundary across input schema feature ranges..."}
                      {uploadStep === "fingerprinting" && "Storing penultimate layer vectors into FAISS IndexFlatL2..."}
                      {uploadStep === "done" && "Redirecting to your new model research workspace..."}
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="space-y-1.5">
                    <label className="label-mono font-bold text-paper">Model Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. churn_classifier_v2"
                      value={uploadName}
                      onChange={(e) => setUploadName(e.target.value)}
                      className="w-full px-4 py-2 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent shadow-[2px_2px_0px_#211C19]"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="label-mono font-bold text-paper">Input Feature Schema (JSON)</label>
                    <div className="flex flex-wrap gap-2 py-1">
                      <button
                        type="button"
                        onClick={() => setUploadSchema(JSON.stringify({
                          features: [
                            { name: "x1", type: "float", min: 0.0, max: 1.0 },
                            { name: "x2", type: "float", min: 0.0, max: 1.0 }
                          ]
                        }, null, 2))}
                        className="badge-research hover:border-accent cursor-pointer"
                      >
                        [ Demo Schema (x1, x2) ]
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
                        className="badge-research hover:border-accent cursor-pointer"
                      >
                        [ Churn Model Schema ]
                      </button>
                    </div>
                    <textarea
                      rows={6}
                      required
                      value={uploadSchema}
                      onChange={(e) => setUploadSchema(e.target.value)}
                      className="w-full px-4 py-2 bg-ink border-2 border-line text-paper font-mono text-xs focus:outline-none focus:border-accent shadow-[2px_2px_0px_#211C19]"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="label-mono font-bold text-paper">
                      Model Artifact File (.pkl, .joblib, .pt, .pth, .onnx, .h5, .keras)
                    </label>
                    <div className="border-2 border-dashed border-line p-6 flex flex-col items-center justify-center bg-panel/30 hover:bg-panel/60 transition-colors cursor-pointer relative">
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
                      <Cpu className="h-8 w-8 text-paper mb-2" />
                      <span className="font-mono text-xs text-paper font-bold">
                        {uploadFile ? uploadFile.name : "Select or Drop Model Artifact"}
                      </span>
                      {uploadFile && (
                        <span className="badge-research mt-2">
                          {(uploadFile.size / 1024).toFixed(1)} KB
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="pt-4 flex gap-3">
                    <button
                      type="button"
                      onClick={() => setIsUploadModalOpen(false)}
                      className="btn-physical flex-1"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn-physical-accent flex-1"
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
