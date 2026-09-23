"use client";

import React from "react";
import { Activity, Radio, RefreshCw } from "lucide-react";

interface HeaderProps {
  connected: boolean;
  sessionId: string;
  onReset: () => void;
}

export function Header({ connected, sessionId, onReset }: HeaderProps) {
  return (
    <header className="glass-panel sticky top-0 z-50 px-6 py-3.5 border-b border-slate-800 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
              NEXUS
            </h1>
            <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
              Console v1.0
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">
            Interruptible Real-Time Multimodal Agent
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full glass-card border border-slate-700/50">
          <span className="relative flex h-2.5 w-2.5">
            {connected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                connected ? "bg-emerald-500" : "bg-rose-500"
              }`}
            ></span>
          </span>
          <span className="text-xs font-semibold text-slate-300">
            {connected ? "LIVE REALTIME" : "DISCONNECTED"}
          </span>
        </div>

        {/* Session ID badge */}
        {sessionId && (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs font-mono text-slate-400">
            <Radio className="w-3.5 h-3.5 text-indigo-400" />
            <span>SID: {sessionId}</span>
          </div>
        )}

        {/* Reset button */}
        <button
          onClick={onReset}
          title="Reset Session"
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700/60"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Reset Session</span>
        </button>
      </div>
    </header>
  );
}
