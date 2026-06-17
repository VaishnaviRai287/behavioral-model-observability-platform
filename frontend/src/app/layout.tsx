import "./globals.css";
import React from "react";
import Link from "next/link";
import { Activity, ShieldAlert, Cpu } from "lucide-react";

export const metadata = {
  title: "ModelMesh — Behavioral Model Observability",
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
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <style>{`
          body {
            font-family: 'Outfit', sans-serif;
          }
        `}</style>
      </head>
      <body className="bg-darkBg text-slate-100 flex flex-col min-h-screen">
        {/* Navigation Bar */}
        <header className="sticky top-0 z-50 glass-panel border-b border-darkBorder/60 bg-darkBg/60 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/" className="flex items-center gap-2.5 group">
                <div className="p-2 rounded-xl bg-teal-500/10 border border-teal-500/30 group-hover:border-teal-500/60 transition-all duration-300">
                  <Activity className="h-5 w-5 text-teal-400 group-hover:rotate-12 transition-transform duration-300" />
                </div>
                <div>
                  <span className="font-bold text-lg tracking-tight text-gradient font-sans">
                    ModelMesh
                  </span>
                  <span className="text-[10px] block text-slate-400 font-medium tracking-widest uppercase">
                    Observability
                  </span>
                </div>
              </Link>

              <nav className="hidden md:flex items-center gap-6">
                <Link
                  href="/"
                  className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
                >
                  Registry
                </Link>
              </nav>
            </div>

            {/* Server Health Status Ping */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 font-medium bg-darkBorder px-2.5 py-1 rounded-full border border-darkBorder flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-slate-400" />
                API V1
              </span>
              <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1 rounded-full text-xs font-semibold">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Active
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-darkBorder bg-darkBg py-6 mt-auto">
          <div className="max-w-7xl mx-auto px-4 text-center sm:px-6 lg:px-8">
            <p className="text-xs text-slate-500">
              ModelMesh © 2026. Real-Time Behavioral Observability Engine.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
