"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Send, Zap, Mic, MicOff, Loader2, AlertCircle, X } from "lucide-react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface InputAreaProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const DEMO_PROMPTS = [
  { label: "1. Initial Trip Goal", text: "Plan a 3-day Chennai trip for 15000 rupees." },
  { label: "2. Interrupt (Parents & Walking)", text: "Wait. I am travelling with my parents. Avoid places requiring lots of walking." },
  { label: "3. Interrupt (Budget)", text: "Actually increase the budget to 20000." },
  { label: "4. Interrupt (New Goal)", text: "Forget the trip. Help me prepare for an interview instead." },
];

export function InputArea({ onSend, disabled }: InputAreaProps) {
  const [text, setText] = useState("");

  const handleFinalTranscript = useCallback(
    (spokenText: string) => {
      if (!spokenText.trim() || disabled) return;
      setText(spokenText);
      onSend(spokenText);
      setTimeout(() => setText(""), 400);
    },
    [disabled, onSend]
  );

  const {
    isSupported,
    status,
    interimTranscript,
    error,
    startListening,
    stopListening,
    reset,
  } = useSpeechRecognition({
    onFinalTranscript: handleFinalTranscript,
  });

  // Display live interim transcript in input box while listening
  useEffect(() => {
    if (status === "listening" && interimTranscript) {
      setText(interimTranscript);
    }
  }, [status, interimTranscript]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
    reset();
  };

  const toggleMic = () => {
    if (!isSupported || disabled) return;
    if (status === "listening") {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="flex flex-col gap-2.5">
      {/* Error / Unsupported Alert Banner */}
      {error && (
        <div className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={reset}
            className="p-1 hover:bg-rose-500/20 rounded-lg text-rose-400 hover:text-rose-200 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Quick Scenario Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider shrink-0 flex items-center gap-1">
          <Zap className="w-3 h-3 text-amber-400" /> Scenarios:
        </span>
        {DEMO_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSend(prompt.text)}
            className="px-3 py-1 rounded-full glass-card hover:bg-slate-700/60 text-slate-300 text-xs whitespace-nowrap transition-all border border-slate-700/70 hover:border-cyan-500/50 hover:text-white"
          >
            {prompt.label}
          </button>
        ))}
      </div>

      {/* Input Form with Mic Button */}
      <form onSubmit={handleSubmit} className="flex gap-2.5">
        <div className="relative flex-1">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              status === "listening"
                ? "Listening... Speak your goal or interruption now..."
                : "Type a goal or interrupt the agent while it works..."
            }
            disabled={disabled}
            className={`w-full px-4 py-3 rounded-xl bg-slate-900/80 border text-sm text-white placeholder-slate-500 focus:outline-none transition-all ${
              status === "listening"
                ? "border-rose-500/60 ring-2 ring-rose-500/30 bg-slate-900"
                : "border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            }`}
          />
          {status === "listening" && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/20 border border-rose-500/40 text-[10px] font-semibold text-rose-300 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
              LIVE STT
            </div>
          )}
        </div>

        {/* Microphone Button */}
        <button
          type="button"
          onClick={toggleMic}
          disabled={disabled || !isSupported}
          title={
            !isSupported
              ? "Voice input isn't supported in this browser. Try Chrome or another supported browser."
              : status === "listening"
              ? "Click to stop listening"
              : "Click to speak (Voice Input)"
          }
          className={`px-3.5 py-3 rounded-xl border flex items-center justify-center transition-all ${
            !isSupported
              ? "bg-slate-800/40 border-slate-800 text-slate-600 cursor-not-allowed"
              : status === "listening"
              ? "bg-rose-500/20 border-rose-500 text-rose-400 shadow-lg shadow-rose-500/20 animate-pulse"
              : status === "processing"
              ? "bg-amber-500/20 border-amber-500 text-amber-300"
              : "bg-slate-800/80 hover:bg-slate-700 border-slate-700/80 text-cyan-400 hover:text-cyan-300"
          }`}
        >
          {!isSupported ? (
            <MicOff className="w-4 h-4" />
          ) : status === "listening" ? (
            <Mic className="w-4 h-4 animate-bounce" />
          ) : status === "processing" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Mic className="w-4 h-4" />
          )}
        </button>

        {/* Send Button */}
        <button
          type="submit"
          disabled={!text.trim() || disabled}
          className="px-5 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all shrink-0"
        >
          <Send className="w-4 h-4" />
          <span>Send / Interrupt</span>
        </button>
      </form>
    </div>
  );
}
