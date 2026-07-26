"use client";

import Link from "next/link";
import {
  ArrowRight,
  ArrowDown,
  Database,
  Server,
  Workflow,
  Braces,
  Compass,
} from "lucide-react";
import { useModels } from "@/hooks/useModelHealth";

const STACK = [
  {
    tag: "FRONTEND UI",
    name: "Next.js / React",
    body: "App Router, client components for the live registry, dashboard, and fingerprint views. Talks to the API over a typed fetch wrapper, never touches the database directly.",
  },
  {
    tag: "REST API + AUTH",
    name: "FastAPI",
    body: "Validates uploads, enforces the Bearer API-key gate on every non-health route, orchestrates ingestion, and serves prediction requests synchronously.",
  },
  {
    tag: "RELATIONAL STORE",
    name: "SQLAlchemy + Postgres",
    body: "Persists models, probe sweeps, fingerprints, prediction logs, drift events, alerts, and API keys. The single source of truth for everything the dashboard renders.",
  },
  {
    tag: "LATENT GEOMETRY INDEX",
    name: "FAISS",
    body: "An IndexFlatL2 built from the model's baseline probe activations. Queried in-process on every prediction for k-NN novelty distance — no network hop.",
  },
  {
    tag: "ASYNC TASK EXECUTION",
    name: "Celery",
    body: "Runs drift recomputation in a separate worker process so the prediction request path never blocks on statistical analysis, regardless of traffic volume.",
  },
  {
    tag: "MESSAGE BROKER",
    name: "Redis",
    body: "Carries task messages from the API to the Celery worker and back. The only coupling between the synchronous request path and the background analysis path.",
  },
  {
    tag: "EXPLAINABILITY ENGINE",
    name: "Kernel SHAP",
    body: "A framework-agnostic implementation that treats every wrapped model as a black box, producing global feature importance and per-prediction local attributions.",
  },
];

const USE_CASES = [
  {
    n: "01",
    q: "Is this input something the model has never confidently handled?",
    a: "Every prediction's latent activation vector is queried against the FAISS baseline manifold. If the k-NN distance exceeds mean + 3σ of the baseline distribution, a LATENT_NOVELTY alert fires — even when the model's own output confidence looks fine.",
  },
  {
    n: "02",
    q: "Is the incoming data quietly drifting from what the model was trained on?",
    a: "A sliding window of recent predictions is compared against the baseline probe distribution using the KS statistic and PSI, per feature and on the output distribution. Crossing threshold raises a FEATURE_DRIFT alert.",
  },
  {
    n: "03",
    q: "Which features actually drove this one prediction?",
    a: "Kernel SHAP computes local attributions for any logged prediction on demand — the exact feature contributions behind that specific output, not just a global ranking.",
  },
  {
    n: "04",
    q: "Did a new model version change behavior before I promoted it?",
    a: "Two fingerprints can be diffed directly: confidence histograms, entropy, and class bias are compared with a Wasserstein distance, surfacing behavioral shift between versions before either is trusted with live traffic.",
  },
];

const LIFECYCLE = [
  {
    n: "01",
    from: "Browser",
    to: "FastAPI",
    mode: "sync",
    title: "The client submits a prediction request",
    body: "The dashboard (or any external caller) sends a single HTTP request carrying the feature payload and an Authorization: Bearer <key> header.",
    code: "POST /api/v1/models/{id}/predict — JSON feature vector, Bearer mmk_ key required.",
  },
  {
    n: "02",
    from: "FastAPI",
    to: "Model Wrapper",
    mode: "sync",
    title: "The model runs and its activations are captured",
    body: "The cached framework wrapper (sklearn / PyTorch / TensorFlow) runs inference and also exposes the penultimate-layer activation vector for the same input.",
    code: "load_model(path) → wrapper.predict(x) + wrapper.get_activations(x)",
  },
  {
    n: "03",
    from: "FastAPI",
    to: "FAISS Index",
    mode: "sync",
    title: "The activation is scored for novelty in-process",
    body: "The activation vector is queried against the model's baseline FAISS index. No network round trip — the index lives in the API process's memory.",
    code: "distance = faiss_index.search(activation, k=5) → novelty_flag = mean_dist > (mean + 3·std)",
  },
  {
    n: "04",
    from: "FastAPI",
    to: "Browser",
    mode: "sync",
    title: "The response returns immediately",
    body: "Prediction, confidence, and the novelty flag are returned in the same request. The client never waits on drift analysis to get an answer.",
    code: "201 Created → { prediction, confidence, novelty_flag }",
  },
  {
    n: "05",
    from: "FastAPI",
    to: "Redis",
    mode: "async",
    title: "Every 50th prediction, drift analysis is queued",
    body: "Rather than recomputing statistical drift inline, the API drops a task message onto the Celery broker and moves on. The request path stays flat no matter how expensive drift analysis gets.",
    code: "if prediction_count % 50 == 0: run_drift_check.delay(model_id)",
  },
  {
    n: "06",
    from: "Celery Worker",
    to: "Postgres",
    mode: "async",
    title: "The worker recomputes drift and raises alerts",
    body: "A separate worker process opens its own DB session, recomputes KS/PSI drift over the recent prediction window, and writes DriftEvent rows — raising an Alert row if any feature has crossed threshold.",
    code: "detect_drift(db, model_id) → process_feature_drift(db, model_id, events)",
  },
];

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="label-mono font-bold text-line/70">{children}</span>;
}

function FlowBox({
  icon: Icon,
  title,
  subtitle,
  dashed = false,
  accent = false,
  children,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: string | number }>;
  title: string;
  subtitle: string;
  dashed?: boolean;
  accent?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`border-2 p-4 sm:p-5 shadow-[4px_4px_0px_#211C19] ${
        dashed ? "border-dashed" : ""
      } ${accent ? "border-line bg-accent text-ink" : "border-line bg-ink text-paper"}`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-line/40 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" strokeWidth={1.75} />
          <span className="font-mono text-xs font-bold uppercase tracking-wider">{title}</span>
        </div>
        <span className={`label-mono ${accent ? "text-ink/70" : ""}`}>{subtitle}</span>
      </div>
      {children}
    </div>
  );
}

function Connector({ label, dashed = false }: { label: string; dashed?: boolean }) {
  return (
    <div className="flex flex-col items-center py-2">
      <div className={`h-6 w-px ${dashed ? "border-l-2 border-dashed border-line/70" : "bg-line"}`} />
      <span className="label-mono bg-ink px-2 -my-1 border border-line text-center whitespace-nowrap">
        {label}
      </span>
      <div className={`h-6 w-px ${dashed ? "border-l-2 border-dashed border-line/70" : "bg-line"}`} />
      <ArrowDown className="h-3 w-3 -mt-1 text-line" strokeWidth={2.5} />
    </div>
  );
}

function SystemDiagram() {
  return (
    <div className="research-window">
      <div className="window-titlebar">
        <div className="window-dots">
          <span className="window-dot bg-rose-400" />
          <span className="window-dot bg-amber-400" />
          <span className="window-dot bg-emerald-500" />
        </div>
        <span className="font-mono text-xs font-bold text-paper">RESEARCH_INSTRUMENT // SYSTEM_TOPOLOGY</span>
        <span className="badge-research">v1.0</span>
      </div>

      <div className="window-content p-5 sm:p-8">
        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mb-8 pb-4 border-b border-line/40">
          <span className="label-mono">READING THIS DIAGRAM</span>
          <span className="flex items-center gap-2 font-mono text-[10px] text-mute">
            <span className="inline-block w-5 h-px bg-line" /> synchronous · blocks the response
          </span>
          <span className="flex items-center gap-2 font-mono text-[10px] text-mute">
            <span className="inline-block w-5 h-px border-t-2 border-dashed border-line" /> asynchronous · background worker
          </span>
        </div>

        <div className="max-w-2xl mx-auto">
          <FlowBox icon={Braces} title="Browser" subtitle="Next.js / React">
            <div className="flex flex-wrap gap-2">
              {["Registry", "Dashboard", "Fingerprint", "Flow"].map((p) => (
                <span key={p} className="badge-research">{p}</span>
              ))}
            </div>
          </FlowBox>

          <Connector label="HTTPS · Authorization: Bearer mmk_&lt;key&gt;" />

          <FlowBox icon={Server} title="FastAPI Application" subtitle="uvicorn · require_api_key">
            <div className="space-y-1.5 font-mono text-[11px] text-paper/90">
              <p><span className="text-accent font-bold">POST</span> /api/v1/models <span className="text-mute">— upload artifact + schema, extract topology</span></p>
              <p><span className="text-accent font-bold">POST</span> /api/v1/models/&#123;id&#125;/probe <span className="text-mute">— run LHS boundary sweep</span></p>
              <p><span className="text-accent font-bold">POST</span> /api/v1/models/&#123;id&#125;/predict <span className="text-mute">— score + log inference</span></p>
              <p><span className="text-accent font-bold">GET</span> /api/v1/models/&#123;id&#125;/health <span className="text-mute">— novelty rate + drift scores</span></p>
            </div>
          </FlowBox>

          {/* Branching connector row */}
          <div className="grid grid-cols-3 gap-2 items-end py-2">
            <Connector label="SQLAlchemy" />
            <Connector label="in-process query" />
            <Connector label="task.delay()" dashed />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <FlowBox icon={Database} title="Postgres" subtitle="models · logs">
              <p className="explainer">models, probes, fingerprints, prediction_logs, drift_events, alerts, api_keys</p>
            </FlowBox>
            <FlowBox icon={Compass} title="FAISS Index" subtitle="IndexFlatL2">
              <p className="explainer">baseline activation manifold, one index per registered model</p>
            </FlowBox>
            <FlowBox icon={Workflow} title="Celery Worker" subtitle="Redis broker" dashed>
              <p className="explainer">run_drift_check(model_id) — recomputes KS/PSI, writes back to Postgres</p>
            </FlowBox>
          </div>
        </div>
      </div>
    </div>
  );
}

function TechStack() {
  return (
    <section className="max-w-6xl mx-auto px-4">
      <div className="section-label">TECHNOLOGY STACK</div>
      <h2 className="font-serif text-2xl sm:text-3xl text-paper mb-8">Seven Systems, One Behavioral Signal</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {STACK.map((s, idx) => (
          <div key={s.name} className="editorial-card-white flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="badge-research">{s.tag}</span>
              <span className="font-mono text-xs font-bold text-mute">0{idx + 1}</span>
            </div>
            <h3 className="font-serif text-lg text-paper font-bold">{s.name}</h3>
            <p className="explainer">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function UseCases() {
  return (
    <section className="max-w-6xl mx-auto px-4">
      <div className="section-label">USE CASES</div>
      <h2 className="font-serif text-2xl sm:text-3xl text-paper mb-8">What Questions Does This Answer?</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {USE_CASES.map((u) => (
          <div key={u.n} className="editorial-card">
            <span className="badge-research-finding mb-3">USE CASE {u.n}</span>
            <h3 className="font-serif text-xl text-paper font-bold leading-snug mb-2">{u.q}</h3>
            <p className="explainer">{u.a}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Lifecycle() {
  return (
    <section className="max-w-5xl mx-auto px-4">
      <div className="section-label">REQUEST LIFECYCLE</div>
      <h2 className="font-serif text-2xl sm:text-3xl text-paper mb-3">
        What Happens When a Prediction Request Comes In?
      </h2>
      <p className="explainer max-w-2xl mb-10">
        A single /predict call travels through six steps. The first four are synchronous and finish before the
        client sees a response; the last two run entirely in the background, decoupled by Redis.
      </p>

      <div className="space-y-4">
        {LIFECYCLE.map((step) => (
          <div key={step.n} className="utility-panel shadow-[4px_4px_0px_#211C19]">
            <div className="grid grid-cols-1 sm:grid-cols-[auto_1fr] gap-4 sm:gap-6">
              <div className="flex sm:flex-col items-center sm:items-start gap-3 sm:gap-2 sm:w-40 shrink-0">
                <span className="font-display text-3xl text-mute leading-none">{step.n}</span>
                <div className="font-mono text-[10px] uppercase tracking-wider">
                  <span className="text-paper font-bold">{step.from}</span>
                  <span className="text-mute"> {step.mode === "async" ? "╌╌▶" : "──▶"} </span>
                  <span className="text-paper font-bold">{step.to}</span>
                </div>
                <span
                  className={
                    step.mode === "async"
                      ? "badge-research border-line bg-panel text-paper"
                      : "badge-research-baseline"
                  }
                >
                  {step.mode}
                </span>
              </div>

              <div className="space-y-2">
                <h4 className="font-serif text-lg text-paper font-bold">{step.title}</h4>
                <p className="explainer">{step.body}</p>
                <div className="bg-ink border border-line px-3 py-2 font-mono text-[11px] text-mute overflow-x-auto">
                  {step.code}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Why async callout */}
      <div className="utility-panel-rose mt-8 shadow-[4px_4px_0px_#211C19]">
        <span className="badge-research-finding mb-2">WHY ASYNC?</span>
        <p className="explainer text-paper/90">
          Drift analysis used to run inline on every 50th prediction, so that single request paid the full cost of
          recomputing KS/PSI statistics before the caller got a response. Moving it behind a Celery task means the
          prediction path has flat, predictable latency no matter how much traffic the drift job is analyzing.
        </p>
      </div>

      {/* Equation panel */}
      <div className="editorial-card-white mt-6 shadow-[4px_4px_0px_#211C19] grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div>
          <span className="badge-research mb-2">EQUATION // NOVELTY</span>
          <div className="bg-panel border border-line p-3 font-mono text-xs text-paper mt-2">
            <p className="text-accent font-bold">threshold = mean + (3 * std)</p>
            <p className="text-mute">novelty_flag = mean_dist &gt; threshold</p>
          </div>
        </div>
        <div>
          <span className="badge-research mb-2">TRIGGER // DRIFT CHECK</span>
          <div className="bg-panel border border-line p-3 font-mono text-xs text-paper mt-2">
            <p className="text-accent font-bold">prediction_count % 50 == 0</p>
            <p className="text-mute">run_drift_check.delay(model_id)</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function FlowPage() {
  const { data: models } = useModels();
  const total = models?.length ?? 0;

  return (
    <div className="space-y-24 -mt-8">
      {/* 1. HEADER */}
      <section className="max-w-6xl mx-auto px-4 pt-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
          <div>
            <span className="badge-research-finding mb-4">SYSTEM ARCHITECTURE</span>
            <h1 className="font-serif font-extrabold text-paper leading-[0.95] tracking-tight text-4xl sm:text-5xl">
              How ModelMesh Works
            </h1>
            <p className="label-mono mt-4">{total} model{total === 1 ? "" : "s"} currently registered</p>
          </div>
          <div className="space-y-4 text-sm text-paper/80 leading-relaxed font-mono">
            <p>
              A user registers a trained model artifact and a feature schema. Before any real traffic arrives,
              ModelMesh runs a Latin Hypercube probe sweep across the declared feature bounds, capturing confidence,
              entropy, and latent activations to compile a geometric baseline &mdash; the model&rsquo;s behavioral
              fingerprint.
            </p>
            <p>
              Every live prediction is then measured against that same fingerprint: a k-NN query against a FAISS
              index for combinatorial novelty, and a rolling statistical comparison for feature and output drift.
              Nothing about this depends on the model&rsquo;s own reported confidence &mdash; it depends on how far
              the input actually sits from what the model was shown while its baseline was built.
            </p>
          </div>
        </div>
      </section>

      {/* 2. SYSTEM DIAGRAM */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="section-label">SYSTEM DIAGRAM</div>
        <h2 className="font-serif text-2xl sm:text-3xl text-paper mb-3">How the Components Connect</h2>
        <p className="explainer max-w-2xl mb-8">
          Think of it as a lab bench: the browser is where you look, FastAPI is the bench technician who receives
          and validates every sample, Postgres and the FAISS index are where the results and reference geometry
          live, and the Celery worker is the instrument that runs the slower analysis off to the side &mdash;
          without making you wait at the bench.
        </p>
        <SystemDiagram />
      </section>

      {/* 3. TECH STACK */}
      <TechStack />

      {/* 4. USE CASES */}
      <UseCases />

      {/* 5. REQUEST LIFECYCLE */}
      <Lifecycle />

      {/* 6. CTA */}
      <section className="max-w-4xl mx-auto px-4 pb-8 text-center space-y-6">
        <span className="badge-research">READY TO SEE IT LIVE?</span>
        <h2 className="font-serif text-2xl sm:text-3xl text-paper">Register a Model and Watch It Run</h2>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link href="/registry" className="btn-physical-accent">
            Enter Registry
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
      </section>
    </div>
  );
}
