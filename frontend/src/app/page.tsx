"use client";

import Link from "next/link";
import {
  ArrowRight,
  Database,
  Compass,
  Activity,
  Sparkles,
  Upload,
  Layers,
  FileCode,
  ShieldAlert,
} from "lucide-react";
import { useModels } from "@/hooks/useModelHealth";
import CornerBrackets from "@/components/CornerBrackets";

const CAPABILITIES = [
  {
    icon: Database,
    title: "Multi-Framework Autopsy",
    body: "Ingests scikit-learn, PyTorch, and TensorFlow/Keras artifacts. Auto-detects the framework and extracts layer topology plus a deterministic model signature.",
    tag: "INGESTION",
  },
  {
    icon: Compass,
    title: "Decision Boundary Probing",
    body: "A Latin Hypercube Sampling sweep across the feature space maps confidence, entropy, and class bias before the model ever sees production traffic.",
    tag: "PROBING",
  },
  {
    icon: Activity,
    title: "Behavioral Observability",
    body: "A FAISS-indexed latent space watches every live prediction for combinatorial novelty, while KS/PSI statistics track feature and output drift.",
    tag: "OBSERVABILITY",
  },
  {
    icon: Sparkles,
    title: "Shapley Explanations",
    body: "Framework-agnostic Kernel SHAP gives global feature importance and per-prediction local attributions, visualized on the dashboard.",
    tag: "EXPLAINABILITY",
  },
];

const PIPELINE = [
  { icon: Upload, label: "01 // UPLOAD", detail: "Model artifact + input schema definition" },
  { icon: Compass, label: "02 // PROBE", detail: "LHS synthetic sweep across feature bounds" },
  { icon: Sparkles, label: "03 // FINGERPRINT", detail: "Baseline entropy, confidence & FAISS manifold" },
  { icon: Activity, label: "04 // MONITOR", detail: "Live novelty, drift & Kernel SHAP attributions" },
];

function NoveltyRadar() {
  return (
    <CornerBrackets className="grid-texture-light border-2 border-line aspect-square w-full max-w-sm mx-auto flex items-center justify-center text-paper/50 bg-ink shadow-[6px_6px_0px_#211C19]">
      <span className="absolute top-4 left-1/2 -translate-x-1/2 badge-research-finding">
        STATUS: NOVELTY_OK
      </span>
      <span className="absolute top-10 left-6 label-mono text-paper/60 hidden sm:inline">SYS_READY</span>
      <span className="absolute top-10 right-6 label-mono text-paper/60 hidden sm:inline">FAISS_kNN</span>
      <span className="absolute bottom-10 left-6 label-mono text-paper/60 hidden sm:inline">KS_PSI: OK</span>
      <span className="absolute bottom-10 right-6 label-mono text-paper/60 hidden sm:inline">NODE_01</span>

      <div className="relative h-44 w-44">
        <div className="absolute inset-0 rounded-full border-2 border-line/40" />
        <div className="absolute inset-6 rounded-full border border-line/30 bg-panel/20" />
        <div className="absolute inset-12 rounded-full border border-dashed border-line/60" />
        <span className="absolute top-1/2 left-1/2 h-2.5 w-2.5 -mt-1.25 -ml-1.25 rounded-full bg-accent animate-pulse" />
        <div
          className="absolute top-1/2 left-1/2 h-2 w-2 -mt-1 -ml-1 rounded-full bg-paper animate-orbit"
          style={{ ["--orbit-radius" as any]: "75px" }}
        />
      </div>

      <span className="absolute bottom-4 left-1/2 -translate-x-1/2 badge-research">
        LIVE INFERENCE MANIFOLD
      </span>
    </CornerBrackets>
  );
}

function PlatformAtAGlance() {
  const { data: models } = useModels();
  const total = models?.length ?? 0;
  const ready = models?.filter((m) => m.status.toLowerCase() === "ready").length ?? 0;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <section className="max-w-5xl mx-auto px-4">
      <div className="flex items-center justify-between gap-4 border-b-2 border-line pb-3 mb-6">
        <div>
          <span className="badge-research mb-1">PLATFORM STATUS</span>
          <h2 className="font-serif text-2xl sm:text-3xl text-paper">System At A Glance</h2>
        </div>
        <span className="label-mono font-bold text-accent">READOUT // {today}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
          <span className="badge-research">METRIC 01</span>
          <p className="label-mono mt-2">Registered Models</p>
          <p className="font-display text-4xl mt-1 text-paper">{total}</p>
          <p className="explainer mt-1">Uploaded & probed model artifacts</p>
        </div>

        <div className="editorial-card shadow-[4px_4px_0px_#211C19]">
          <span className="badge-research-finding">METRIC 02</span>
          <p className="label-mono mt-2">Active Serving</p>
          <p className="font-display text-4xl mt-1 text-paper">{ready}</p>
          <p className="explainer mt-1">Ready for real-time inference monitoring</p>
        </div>

        <div className="editorial-card-white shadow-[4px_4px_0px_#211C19]">
          <span className="badge-research-baseline">METRIC 03</span>
          <p className="label-mono mt-2">Observability Status</p>
          <p className="font-display text-2xl mt-2 text-paper">Operational</p>
          <p className="explainer mt-1">FAISS + KS/PSI workers online</p>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <div className="space-y-24 -mt-8">
      {/* 1. HERO — Full-bleed publication banner */}
      <section className="full-bleed bg-panel border-b-2 border-line text-paper">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <span className="badge-research-finding mb-4">
              RESEARCH INSTRUMENTATION // SELF-HOSTED
            </span>
            <h1 className="font-serif font-extrabold text-paper leading-[0.95] tracking-tight text-5xl sm:text-6xl lg:text-7xl">
              Automated<br />
              <span className="italic font-serif font-normal">Model</span> Insight
            </h1>
            <p className="text-paper/80 text-sm sm:text-base max-w-md mt-6 leading-relaxed font-mono">
              ModelMesh inspects trained model artifacts, probes decision boundary geometry with Latin Hypercube Sampling, and scores live inference against FAISS latent manifolds.
            </p>
            <div className="flex flex-wrap items-center gap-4 mt-8">
              <Link
                href="/registry"
                className="btn-physical-accent"
              >
                Start Integration
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
                target="_blank"
                rel="noreferrer"
                className="btn-physical"
              >
                API Reference Docs
              </a>
            </div>
          </div>

          <NoveltyRadar />
        </div>
      </section>

      {/* 2. EDITORIAL THESIS / QUOTE */}
      <section className="max-w-3xl mx-auto text-center px-4">
        <span className="badge-research mb-3">CORE THESIS</span>
        <blockquote className="font-serif text-2xl sm:text-3xl text-paper leading-snug font-medium italic">
          &ldquo;Most ML monitoring tools watch the wrapper around a model. ModelMesh observes the model itself.&rdquo;
        </blockquote>
        <p className="explainer max-w-xl mx-auto mt-4 leading-relaxed">
          By compiling a geometric fingerprint at registration time, ModelMesh identifies when live production inference drifts into out-of-distribution regions the model was never trained to handle.
        </p>
      </section>

      {/* 3. PLATFORM AT A GLANCE (3 Cards) */}
      <PlatformAtAGlance />

      {/* 4. HUGE FEATURE SPOTLIGHT (1 Huge Research Window) */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="research-window">
          <div className="window-titlebar">
            <div className="window-dots">
              <span className="window-dot bg-rose-400" />
              <span className="window-dot bg-amber-400" />
              <span className="window-dot bg-emerald-400" />
            </div>
            <span className="font-mono text-xs font-bold text-paper">RESEARCH_INSTRUMENT // FEATURE_INSPECTOR</span>
            <span className="badge-research">v2.4</span>
          </div>

          <div className="window-content p-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-7 space-y-4">
              <span className="badge-research-finding">FEATURE SPOTLIGHT</span>
              <h3 className="font-serif text-3xl sm:text-4xl text-paper font-bold">
                Penultimate Latent-Space Novelty Detection
              </h3>
              <p className="text-sm text-paper/80 leading-relaxed font-mono">
                Every model upload triggers a 1,000-probe Latin Hypercube sweep. The internal activation vectors are stored inside a FAISS L2 index. During live inference, incoming feature vectors are transformed into latent activations and queried against the k-NN index.
              </p>
              <div className="flex flex-wrap gap-3 pt-2">
                <span className="badge-research">FAISS IndexFlatL2</span>
                <span className="badge-research">k-NN Distance (k=5)</span>
                <span className="badge-research">3σ Novelty Threshold</span>
              </div>
            </div>

            <div className="lg:col-span-5 bg-panel border-2 border-line p-6 shadow-[4px_4px_0px_#211C19] space-y-4">
              <div className="flex justify-between items-center border-b border-line pb-2">
                <span className="label-mono text-paper">Live Scored Equation</span>
                <span className="badge-research">EQUATION 01</span>
              </div>
              <div className="bg-ink border border-line p-3 font-mono text-xs text-paper space-y-1">
                <p className="text-accent font-bold">threshold = mean + (3 * std)</p>
                <p className="text-mute">novelty_flag = mean_dist &gt; threshold</p>
              </div>
              <p className="explainer">
                Provides instant out-of-distribution warnings even when prediction output confidence remains falsely elevated.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. CAPABILITIES GRID (4 Editorial Cards) */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between border-b-2 border-line pb-3 mb-8">
          <div>
            <span className="badge-research">SYSTEM CAPABILITIES</span>
            <h2 className="font-serif text-3xl text-paper">Modular Analysis Modules</h2>
          </div>
          <span className="label-mono">4 MODULES ACTIVE</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {CAPABILITIES.map((cap, idx) => {
            const Icon = cap.icon;
            const isAccent = idx === 0;
            return (
              <div
                key={cap.title}
                className={`border-2 border-line p-5 flex flex-col justify-between shadow-[5px_5px_0px_#211C19] transition-all hover:-translate-y-0.5 ${
                  isAccent ? "bg-accent text-ink" : "bg-panel text-paper"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className={isAccent ? "badge-research border-ink text-ink bg-transparent" : "badge-research"}>
                      {cap.tag}
                    </span>
                    <span className="font-mono text-xs font-bold opacity-60">0{idx + 1}</span>
                  </div>

                  <div className="p-4 border-2 border-line bg-ink text-paper mb-4 flex items-center justify-center shadow-[2px_2px_0px_#211C19]">
                    <Icon className="h-8 w-8" strokeWidth={1.5} />
                  </div>

                  <h3 className="text-base font-bold font-serif mb-2">{cap.title}</h3>
                  <p className="text-xs leading-relaxed opacity-90 font-mono">{cap.body}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 6. PIPELINE WORKFLOW (Utility Panels) */}
      <section className="max-w-5xl mx-auto px-4 pb-8">
        <div className="text-center space-y-2 mb-10">
          <span className="badge-research-finding">PIPELINE WORKFLOW</span>
          <h2 className="font-serif text-3xl text-paper">From Model Ingestion to Live Drift Monitoring</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {PIPELINE.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={step.label}
                className="utility-panel shadow-[4px_4px_0px_#211C19] space-y-3"
              >
                <div className="p-2 border border-line bg-panel w-fit">
                  <Icon className="h-4 w-4 text-paper" />
                </div>
                <h4 className="font-mono text-xs font-bold text-paper">{step.label}</h4>
                <p className="explainer">{step.detail}</p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
