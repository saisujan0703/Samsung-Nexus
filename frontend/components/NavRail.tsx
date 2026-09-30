"use client";

import React from "react";
import { MessageSquare, Compass, Settings, Globe, Sliders } from "lucide-react";

export type NavModalTab = "explore" | "engines" | "preferences" | "settings";

interface NavRailProps {
  onOpenModal?: (tab: NavModalTab) => void;
  activeModalTab?: NavModalTab | null;
}

export function NavRail({ onOpenModal, activeModalTab }: NavRailProps) {
  return (
    <nav className="w-16 h-full flex flex-col items-center justify-between py-6 aurora-panel rounded-3xl border border-emerald-900/20 bg-[#0a0f0c]/90 backdrop-blur-xl shrink-0">
      {/* Top Brand Logo */}
      <div className="flex flex-col items-center gap-6">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 via-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-950/60 ring-1 ring-emerald-400/30">
          <span className="text-slate-950 font-black text-lg select-none">S</span>
        </div>

        {/* Primary Navigation Icons */}
        <div className="flex flex-col gap-3">
          {/* Active AI Chat */}
          <button
            type="button"
            className="w-10 h-10 rounded-xl flex items-center justify-center bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-sm shadow-emerald-950/40 transition-all cursor-default"
            title="AI Chat (Active)"
          >
            <MessageSquare className="w-4 h-4" />
          </button>

          {/* 1. Explore Capabilities & Prompt Gallery */}
          <button
            type="button"
            onClick={() => onOpenModal?.("explore")}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              activeModalTab === "explore"
                ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-950/40"
                : "text-slate-400 hover:text-emerald-300 hover:bg-emerald-950/30 border border-transparent"
            }`}
            title="Explore Capabilities & Prompts"
          >
            <Compass className="w-4 h-4" />
          </button>

          {/* 2. Connected Engines & Knowledge */}
          <button
            type="button"
            onClick={() => onOpenModal?.("engines")}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              activeModalTab === "engines"
                ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-950/40"
                : "text-slate-400 hover:text-emerald-300 hover:bg-emerald-950/30 border border-transparent"
            }`}
            title="Connected Engines & Tools"
          >
            <Globe className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bottom Settings & Preferences */}
      <div className="flex flex-col items-center gap-3">
        {/* 3. Interaction & Voice Preferences */}
        <button
          type="button"
          onClick={() => onOpenModal?.("preferences")}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
            activeModalTab === "preferences"
              ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-950/40"
              : "text-slate-400 hover:text-emerald-300 hover:bg-emerald-950/30 border border-transparent"
          }`}
          title="Interaction & Voice Preferences"
        >
          <Sliders className="w-4 h-4" />
        </button>

        {/* 4. Session & System Settings */}
        <button
          type="button"
          onClick={() => onOpenModal?.("settings")}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
            activeModalTab === "settings"
              ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-950/40"
              : "text-slate-400 hover:text-emerald-300 hover:bg-emerald-950/30 border border-transparent"
          }`}
          title="Session & System Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </nav>
  );
}
