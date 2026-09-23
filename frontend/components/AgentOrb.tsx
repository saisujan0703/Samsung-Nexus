"use client";

import React from "react";
import { AgentState } from "../lib/types";
import { Cpu, Zap, PauseCircle, Activity, Mic, Volume2, Sparkles } from "lucide-react";

interface AgentOrbProps {
  state: AgentState;
}

const STATE_CONFIG: Record<
  AgentState,
  {
    label: string;
    description: string;
    color: string;
    glow: string;
    border: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  IDLE: {
    label: "IDLE",
    description: "Agent standby — waiting for instruction",
    color: "from-slate-600 to-slate-800",
    glow: "shadow-slate-500/20",
    border: "border-slate-700",
    icon: Activity,
  },
  LISTENING: {
    label: "LISTENING",
    description: "Receiving user voice or input",
    color: "from-cyan-500 to-blue-600",
    glow: "shadow-cyan-500/40",
    border: "border-cyan-400",
    icon: Mic,
  },
  THINKING: {
    label: "THINKING",
    description: "Analyzing prompt & generating plan",
    color: "from-purple-500 to-indigo-600",
    glow: "shadow-purple-500/40",
    border: "border-purple-400",
    icon: Sparkles,
  },
  EXECUTING: {
    label: "EXECUTING",
    description: "Running asynchronous tool tasks",
    color: "from-emerald-500 to-teal-600",
    glow: "shadow-emerald-500/40",
    border: "border-emerald-400",
    icon: Cpu,
  },
  SPEAKING: {
    label: "SPEAKING",
    description: "Streaming natural language response",
    color: "from-sky-400 to-blue-600",
    glow: "shadow-sky-500/40",
    border: "border-sky-400",
    icon: Volume2,
  },
  INTERRUPTED: {
    label: "INTERRUPTED",
    description: "User interrupted — evaluating impact",
    color: "from-rose-500 to-red-600",
    glow: "shadow-rose-500/50",
    border: "border-rose-400",
    icon: PauseCircle,
  },
  REPLANNING: {
    label: "REPLANNING",
    description: "Computing plan diff & selective update",
    color: "from-amber-500 to-orange-600",
    glow: "shadow-amber-500/40",
    border: "border-amber-400",
    icon: Zap,
  },
};

export function AgentOrb({ state }: AgentOrbProps) {
  const config = STATE_CONFIG[state] || STATE_CONFIG.IDLE;
  const Icon = config.icon;

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col items-center justify-center text-center relative overflow-hidden">
      {/* Background radial glow */}
      <div
        className={`absolute inset-0 bg-gradient-radial ${config.color} opacity-10 blur-2xl pointer-events-none transition-all duration-700`}
      />

      {/* Animated Orb Container */}
      <div className="relative w-36 h-36 flex items-center justify-center my-2">
        {/* Outer Ring */}
        <div
          className={`absolute inset-0 rounded-full border border-dashed ${config.border} opacity-40 animate-spin-slow`}
        />

        {/* Middle Pulse Ring */}
        <div
          className={`absolute inset-3 rounded-full border ${config.border} opacity-60 animate-ping`}
          style={{ animationDuration: state === "INTERRUPTED" ? "1s" : "3s" }}
        />

        {/* Core Glowing Orb */}
        <div
          className={`w-24 h-24 rounded-full bg-gradient-to-tr ${config.color} shadow-2xl ${config.glow} flex items-center justify-center transition-all duration-500 transform animate-orb-pulse`}
        >
          <Icon className="w-10 h-10 text-white drop-shadow-md" />
        </div>
      </div>

      {/* State Label & Description */}
      <div className="mt-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-700/80">
          <span
            className={`w-2 h-2 rounded-full ${
              state === "INTERRUPTED"
                ? "bg-rose-500 animate-ping"
                : state === "REPLANNING"
                ? "bg-amber-400 animate-pulse"
                : state === "EXECUTING"
                ? "bg-emerald-400"
                : "bg-cyan-400"
            }`}
          />
          <span className="text-xs font-bold tracking-wider text-white">
            {config.label}
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-1.5 font-medium max-w-[220px]">
          {config.description}
        </p>
      </div>
    </div>
  );
}
