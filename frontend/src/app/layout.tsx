import "./globals.css";
import React from "react";
import Link from "next/link";
import { Activity, Terminal, Workflow, BookOpen } from "lucide-react";

export const metadata = {
  title: "ModelMesh — Behavioral Model Observability Platform",
  description: "Real-time behavioral observation, latent space novelty detection, and drift monitoring.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Anton&family=JetBrains+Mono:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-ink text-paper flex flex-col min-h-screen">
        {/* Navigation Bar */}
        <header className="sticky top-0 z-50 border-b-2 border-line bg-ink/95 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/" className="flex items-center gap-3 group">
                <div className="p-1.5 border-2 border-line bg-panel group-hover:bg-accent group-hover:text-ink transition-colors shadow-[2px_2px_0px_#211C19]">
                  <Activity className="h-4 w-4 text-paper group-hover:text-ink transition-colors" />
                </div>
                <div>
                  <span className="font-display text-xl tracking-tight text-paper block leading-none">
                    MODELMESH
                  </span>
                  <span className="label-mono text-[9px] block mt-0.5 text-mute">
                    BEHAVIORAL LAB // OBS-1
                  </span>
                </div>
              </Link>

              <nav className="hidden md:flex items-center gap-6">
                <Link
                  href="/registry"
                  className="font-mono text-xs uppercase tracking-wider font-semibold text-paper hover:text-accent transition-colors flex items-center gap-1.5 px-2.5 py-1 border border-transparent hover:border-line"
                >
                  <Terminal className="h-3.5 w-3.5 text-accent" />
                  [ Model Registry ]
                </Link>
                <Link
                  href="/flow"
                  className="font-mono text-xs uppercase tracking-wider font-semibold text-paper hover:text-accent transition-colors flex items-center gap-1.5 px-2.5 py-1 border border-transparent hover:border-line"
                >
                  <Workflow className="h-3.5 w-3.5 text-accent" />
                  [ System Flow ]
                </Link>
                <Link
                  href="/guide"
                  className="font-mono text-xs uppercase tracking-wider font-semibold text-paper hover:text-accent transition-colors flex items-center gap-1.5 px-2.5 py-1 border border-transparent hover:border-line"
                >
                  <BookOpen className="h-3.5 w-3.5 text-accent" />
                  [ User Manual ]
                </Link>
              </nav>
            </div>

            {/* Server Health Status */}
            <div className="flex items-center gap-3">
              <span className="badge-research hidden sm:inline-flex">
                API V1.4
              </span>
              <div className="flex items-center gap-2 border-2 border-line bg-ink px-3 py-1 font-mono text-[10px] uppercase font-bold text-paper shadow-[2px_2px_0px_#211C19]">
                <span className="inline-flex rounded-full h-2 w-2 bg-emerald-500 animate-pulse" />
                SYSTEM READY
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t-2 border-line bg-ink mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="space-y-3 md:col-span-2">
              <div className="flex items-center gap-2">
                <span className="badge-research-finding">RESEARCH NOTE</span>
                <p className="label-mono text-paper">About ModelMesh Engine</p>
              </div>
              <p className="explainer max-w-md leading-relaxed">
                ModelMesh is a self-hosted behavioral observability platform. Rather than monitoring only HTTP wrappers, it probes model decision boundaries at registration time with Latin Hypercube Sampling (LHS) and scores live inference against latent FAISS manifolds.
              </p>
            </div>

            <div className="space-y-3">
              <p className="label-mono text-paper">Navigation & Docs</p>
              <div className="flex flex-col gap-2 font-mono text-xs">
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-accent transition-colors w-fit flex items-center gap-1.5"
                >
                  <span className="text-accent">→</span> Swagger API Docs
                </a>
                <Link href="/registry" className="hover:text-accent transition-colors w-fit flex items-center gap-1.5">
                  <span className="text-accent">→</span> Model Registry
                </Link>
                <Link href="/flow" className="hover:text-accent transition-colors w-fit flex items-center gap-1.5">
                  <span className="text-accent">→</span> System Flow
                </Link>
                <Link href="/guide" className="hover:text-accent transition-colors w-fit flex items-center gap-1.5">
                  <span className="text-accent">→</span> User Manual
                </Link>
                <Link href="/" className="hover:text-accent transition-colors w-fit flex items-center gap-1.5">
                  <span className="text-accent">→</span> Research Overview
                </Link>
              </div>
            </div>

            <div className="space-y-3 md:text-right">
              <p className="label-mono text-paper">SPECIFICATION // 2026</p>
              <p className="explainer">ModelMesh · Geometric Observability Infrastructure</p>
              <div className="inline-block border border-line bg-panel px-3 py-1 font-mono text-[9px] uppercase tracking-widest text-paper">
                Mac OS / System 7 Research Edition
              </div>
            </div>
          </div>

          {/* Oversized wordmark lockup */}
          <div className="border-t-2 border-line overflow-hidden select-none bg-panel/30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <span className="font-display text-paper block leading-none tracking-tight text-[18vw] md:text-[9.5vw] -mb-[2vw] md:-mb-[1.2vw] whitespace-nowrap opacity-90">
                MODELMESH
              </span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
