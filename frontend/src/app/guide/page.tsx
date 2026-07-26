"use client";

import Link from "next/link";
import { ArrowRight, Compass, Fingerprint, Activity, BarChart3, Sparkles } from "lucide-react";

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-ink border border-line px-4 py-3 font-mono text-[11px] text-paper overflow-x-auto whitespace-pre-wrap leading-relaxed">
      {children}
    </pre>
  );
}

function Term({
  name,
  meta,
  children,
}: {
  name: string;
  meta?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-line/40 py-3.5 last:border-0 last:pb-0 first:pt-0">
      <div className="flex flex-wrap items-baseline gap-2 mb-1">
        <code className="font-mono text-sm font-bold text-paper bg-panel px-1.5 py-0.5">{name}</code>
        {meta && <span className="badge-research">{meta}</span>}
      </div>
      <p className="explainer">{children}</p>
    </div>
  );
}

function Reference({
  icon: Icon,
  title,
  tag,
  children,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: string | number }>;
  title: string;
  tag: string;
  children: React.ReactNode;
}) {
  return (
    <div className="research-window">
      <div className="window-titlebar">
        <div className="window-dots">
          <span className="window-dot bg-rose-400" />
          <span className="window-dot bg-amber-400" />
          <span className="window-dot bg-emerald-500" />
        </div>
        <span className="font-mono text-xs font-bold text-paper flex items-center gap-2">
          <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
          {title}
        </span>
        <span className="badge-research">{tag}</span>
      </div>
      <div className="window-content p-6">{children}</div>
    </div>
  );
}

function Step({
  n,
  title,
  children,
  code,
}: {
  n: string;
  title: string;
  children: React.ReactNode;
  code?: string;
}) {
  return (
    <div className="utility-panel shadow-[4px_4px_0px_#211C19]">
      <div className="flex items-baseline gap-3 mb-2">
        <span className="font-display text-2xl text-mute leading-none">{n}</span>
        <h4 className="font-serif text-lg text-paper font-bold">{title}</h4>
      </div>
      <p className="explainer mb-3">{children}</p>
      {code && <CodeBlock>{code}</CodeBlock>}
    </div>
  );
}

export default function GuidePage() {
  return (
    <div className="space-y-24 -mt-8">
      {/* HEADER */}
      <section className="max-w-4xl mx-auto px-4 pt-4">
        <span className="badge-research-finding mb-4">USER MANUAL</span>
        <h1 className="font-serif font-extrabold text-paper leading-[0.95] tracking-tight text-4xl sm:text-5xl">
          Using ModelMesh, Step by Step
        </h1>
        <p className="text-sm text-paper/80 max-w-2xl mt-5 leading-relaxed font-mono">
          This page covers two things: how to wire ModelMesh into your own project as an API, and how to read
          every number it hands back to you. If the <Link href="/flow" className="text-accent underline">System Flow</Link> page
          explains how the platform is built, this page explains how to drive it — and what it&rsquo;s actually telling
          you about your model.
        </p>
      </section>

      {/* QUICKSTART */}
      <section className="max-w-5xl mx-auto px-4">
        <div className="section-label">GETTING STARTED</div>
        <h2 className="font-serif text-2xl sm:text-3xl text-paper mb-3">Five Steps to Your First Prediction</h2>
        <p className="explainer max-w-2xl mb-8">
          Everything after step 1 requires an <code className="bg-panel px-1">Authorization: Bearer &lt;key&gt;</code> header.
          Steps 2-4 are one-time setup per model; step 5 is what your application calls on every request.
        </p>

        <div className="space-y-4">
          <Step
            n="01"
            title="Create an API key"
            code={`curl -X POST http://localhost:8000/api/v1/api-keys \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-app"}'
# → { "key": "mmk_...", ... }  — shown once, save it`}
          >
            This only works unauthenticated on a fresh instance (zero keys exist yet). Every request after this
            one needs the returned key as a Bearer token. You can also do this from the Registry page&rsquo;s
            &ldquo;Generate API Key&rdquo; panel instead of curl.
          </Step>

          <Step
            n="02"
            title="Register your model"
            code={`curl -X POST http://localhost:8000/api/v1/models \\
  -H "Authorization: Bearer mmk_..." \\
  -F "name=my_model" \\
  -F 'schema={"features":[{"name":"tenure","type":"float","min":0,"max":100}]}' \\
  -F "file=@my_model.pkl"
# → { "id": "<model_id>", "framework": "sklearn", ... }`}
          >
            Upload the trained artifact (.pkl/.joblib, .pt/.pth, or .h5/.keras) plus a JSON schema describing every
            input feature&rsquo;s name, type, and realistic min/max bounds. The bounds matter — they define the space the
            next step samples from.
          </Step>

          <Step
            n="03"
            title="Run the boundary probe"
            code={`curl -X POST http://localhost:8000/api/v1/models/<model_id>/probe \\
  -H "Authorization: Bearer mmk_..." -d '{"n_probes": 100}'
# → { "id": "<session_id>", "mean_confidence": 0.87, ... }`}
          >
            A Latin Hypercube Sampling sweep generates <code className="bg-panel px-1">n_probes</code> synthetic
            inputs spread evenly across your declared feature bounds, and records how the model responds to each
            one. This is what &ldquo;normal&rdquo; looks like, before any real traffic exists.
          </Step>

          <Step
            n="04"
            title="Compile the fingerprint"
            code={`curl -X POST http://localhost:8000/api/v1/probes/<session_id>/fingerprint \\
  -H "Authorization: Bearer mmk_..."
# → { "id": "<fingerprint_id>", "entropy": 0.42, ... }`}
          >
            Turns the probe sweep into a baseline: a FAISS index of latent activations (for novelty scoring) plus
            summary statistics (for drift scoring). Every later prediction gets compared against this.
          </Step>

          <Step
            n="05"
            title="Predict — the call your app actually makes"
            code={`curl -X POST http://localhost:8000/api/v1/models/<model_id>/predict \\
  -H "Authorization: Bearer mmk_..." \\
  -d '{"features": {"tenure": 3, "monthly_charges": 95}}'
# → { "predicted_class": 1, "confidence": 0.94,
#     "novelty_flag": false, "faiss_distance": 0.42, ... }`}
          >
            Your application calls this instead of running the model itself. You get the prediction back exactly
            like a local call would return it, plus <code className="bg-panel px-1">novelty_flag</code> — and every
            call is logged and scored for drift in the background, at no extra latency cost to you.
          </Step>
        </div>
      </section>

      {/* PREDICTION RESPONSE GLOSSARY */}
      <section className="max-w-5xl mx-auto px-4">
        <div className="section-label">REFERENCE</div>
        <h2 className="font-serif text-2xl sm:text-3xl text-paper mb-8">What Every Field Actually Tells You</h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Reference icon={Activity} title="PREDICT // RESPONSE_FIELDS" tag="/models/{id}/predict">
            <Term name="predicted_class">The winning class index — same as calling the model directly.</Term>
            <Term name="confidence">
              Probability mass on the winning class. High confidence does <em>not</em> mean the input is familiar —
              a model can be confidently wrong on something it&rsquo;s never seen. That&rsquo;s what the next two fields are for.
            </Term>
            <Term name="raw_output">The full probability distribution across all classes, not just the winner.</Term>
            <Term name="novelty_flag" meta="the important one">
              True when this input&rsquo;s latent activation sits further from the baseline manifold than any probe
              sample did — i.e. this is a genuinely unfamiliar region of behavior space, independent of what the
              model&rsquo;s own confidence claims.
            </Term>
            <Term name="faiss_distance">
              The raw k-NN distance behind that flag. Flips to novel when it exceeds{" "}
              <code className="bg-panel px-1">mean + 3·std</code> of the baseline&rsquo;s own internal distances.
            </Term>
            <Term name="latency_ms">Wall-clock time for this single inference call, measured server-side.</Term>
          </Reference>

          <Reference icon={Fingerprint} title="FINGERPRINT // RESPONSE_FIELDS" tag="/probes/{id}/fingerprint">
            <Term name="confidence_histogram">Binned distribution of confidence scores across the probe sweep.</Term>
            <Term name="entropy">
              Shannon entropy of the predicted-class distribution across probes. Near 0 means the model always
              lands on one class inside its own bounds; higher means it genuinely discriminates across the space.
            </Term>
            <Term name="uncertainty_rate">Fraction of probe samples where the model&rsquo;s top-class confidence was low.</Term>
            <Term name="class_bias">How lopsided the class distribution is across probe outputs, in [0, 1].</Term>
            <Term name="mean_confidence / confidence_std">Average and spread of confidence across the whole sweep.</Term>
            <Term name="similarity_score" meta="fingerprint compare">
              When diffing two fingerprints (e.g. before/after retraining): a composite 0-1 score built from
              histogram Wasserstein distance, class-bias delta, and entropy delta — 1.0 is identical behavior.
              <code className="bg-panel px-1 ml-1">verdict</code> reads out as stable / drifted / severely_drifted.
            </Term>
          </Reference>
        </div>
      </section>

      {/* DRIFT & ALERTS */}
      <section className="max-w-5xl mx-auto px-4">
        <Reference icon={Compass} title="DRIFT & ALERTS // SEVERITY MODEL" tag="/models/{id}/health, /alerts">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <Term name="ks_statistic" meta="Kolmogorov-Smirnov">
                Max gap between the baseline&rsquo;s and live traffic&rsquo;s cumulative distributions for one feature, in [0, 1].
                Sensitive to shifts anywhere in the distribution, including the tails.
              </Term>
              <Term name="psi_score" meta="Population Stability Index">
                A binned divergence measure between the same two distributions. Standard industry rule of thumb —
                which is exactly what&rsquo;s wired in here.
              </Term>
              <Term name="severity">
                Per feature, computed from whichever statistic is worse:
              </Term>
              <CodeBlock>{`none:     ks < 0.15  and psi < 0.10
warning:  ks >= 0.15 or  psi >= 0.10
critical: ks >= 0.30 or  psi >= 0.25`}</CodeBlock>
            </div>
            <div>
              <Term name="FEATURE_DRIFT alert">
                Raised when any feature crosses warning/critical. Severity is the worst severity across all breached
                features; the alert&rsquo;s metadata lists exactly which features drifted and by how much.
              </Term>
              <Term name="LATENT_NOVELTY alert" meta="always critical">
                Raised the first time a prediction&rsquo;s FAISS distance exceeds threshold. Only one stays active at a
                time per model — resolve it to let a new one fire.
              </Term>
              <Term name="active_alerts / drift_scores" meta="GET /health">
                The at-a-glance summary: current count of unresolved alerts, plus the latest KS statistic per
                feature — this is what the Registry&rsquo;s health badge is reading.
              </Term>
            </div>
          </div>
        </Reference>
      </section>

      {/* DATASET HEALTH + PERFORMANCE */}
      <section className="max-w-5xl mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Reference icon={BarChart3} title="DATASET HEALTH // RESPONSE_FIELDS" tag="/models/{id}/dataset-health">
            <Term name="missing_values">Null/absent feature values across the last 1,000 logged predictions.</Term>
            <Term name="class_imbalance.entropy">
              Same Shannon entropy idea as the fingerprint, but computed on live predicted classes — low entropy in
              production traffic that had high entropy at baseline is itself a signal worth noticing.
            </Term>
            <Term name="outliers" meta="IQR method">
              Per feature, values outside <code className="bg-panel px-1">[Q1 - 1.5·IQR, Q3 + 1.5·IQR]</code>, with
              bounds taken from the baseline probe distribution where one exists.
            </Term>
            <Term name="duplicates">Exact repeat input vectors in the logged window — often a sign of retried or replayed traffic.</Term>
          </Reference>

          <Reference icon={Sparkles} title="PERFORMANCE // RESPONSE_FIELDS" tag="/models/{id}/performance">
            <Term name="latency.p50 / p95 / p99">
              Percentiles over the last 1,000 predictions, computed from real wall-clock timing — not estimated.
            </Term>
            <Term name="throughput.rps_1m / rps_5m">Requests-per-second over trailing 1- and 5-minute windows.</Term>
            <Term name="cpu.mean_pct / memory.mean_mb">
              Per-request resource cost, sampled via <code className="bg-panel px-1">getrusage()</code> at inference
              time — useful for sizing before you put real traffic behind a model.
            </Term>
          </Reference>
        </div>
      </section>

      {/* EXPLAINABILITY */}
      <section className="max-w-5xl mx-auto px-4">
        <Reference icon={Fingerprint} title="EXPLAINABILITY // RESPONSE_FIELDS" tag="Kernel SHAP">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <span className="badge-research mb-2">GET /models/&#123;id&#125;/explainability/global</span>
              <p className="explainer mt-2">
                Averages absolute SHAP values across the baseline probe instances — one importance score per
                feature, telling you which inputs the model leans on <em>in general</em>, independent of any single
                prediction.
              </p>
            </div>
            <div>
              <span className="badge-research mb-2">GET /predictions/&#123;id&#125;/explain</span>
              <p className="explainer mt-2">
                The per-feature contribution breakdown for one specific logged prediction — how much each input
                pushed that particular output away from the model&rsquo;s average, in that direction or the other.
              </p>
            </div>
          </div>
        </Reference>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-4 pb-8 text-center space-y-6">
        <span className="badge-research">READY TO TRY IT?</span>
        <h2 className="font-serif text-2xl sm:text-3xl text-paper">Register a Model and Read Its First Fingerprint</h2>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link href="/registry" className="btn-physical-accent">
            Enter Registry
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/flow" className="btn-physical">
            See the System Flow
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
