"use client";

import React from "react";
import { Activity, Radio, RefreshCw, Volume2, VolumeX, Square } from "lucide-react";

interface HeaderProps {
  connected: boolean;
  sessionId: string;
  onReset: () => void;
  isSpeaking?: boolean;
  isMuted?: boolean;
  toggleMute?: () => void;
  cancelSpeech?: () => void;
  isTtsSupported?: boolean;
}

export function Header({
  connected,
  sessionId,
  onReset,
  isSpeaking,
  isMuted,
  toggleMute,
  cancelSpeech,
  isTtsSupported = true,
}: HeaderProps) {
  return (
    <header className="glass-panel sticky top-0 z-50 px-6 py-3.5 border-b border-slate-800 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
              SURU AI
            </h1>
            <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
              Console v1.0
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">
            Interruptible Real-Time Agent
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 md:gap-4">
        {/* Speaking indicator and Stop Speech button */}
        {isSpeaking && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/20 border border-sky-400/50 text-sky-300 animate-pulse text-xs font-semibold">
            <Volume2 className="w-3.5 h-3.5 text-sky-400 animate-bounce" />
            <span className="hidden sm:inline">SURU is speaking...</span>
            {cancelSpeech && (
              <button
                type="button"
                onClick={cancelSpeech}
                title="Stop Speech"
                className="ml-1 px-2 py-0.5 rounded bg-rose-500/30 hover:bg-rose-500/50 text-rose-200 border border-rose-400/40 text-[11px] font-bold flex items-center gap-1 transition-colors"
              >
                <Square className="w-2.5 h-2.5 fill-current" />
                <span>Stop</span>
              </button>
            )}
          </div>
        )}

        {/* TTS Mute / Unmute Toggle */}
        {isTtsSupported && toggleMute && (
          <button
            type="button"
            onClick={toggleMute}
            title={isMuted ? "Unmute Voice Output" : "Mute Voice Output"}
            className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
              isMuted
                ? "bg-rose-500/20 border-rose-500/40 text-rose-400"
                : "bg-slate-800/80 hover:bg-slate-700 border-slate-700/60 text-cyan-400"
            }`}
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
        )}

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
