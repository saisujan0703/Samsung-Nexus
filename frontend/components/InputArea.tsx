"use client";

import React, { useState } from "react";
import { Send, Zap, MicOff } from "lucide-react";

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  };

  return (
    <div className="flex flex-col gap-2.5">
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

      {/* Input Field */}
      <form onSubmit={handleSubmit} className="flex gap-2.5">
        <div className="relative flex-1">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type a goal or interrupt the agent while it works..."
            disabled={disabled}
            className="w-full px-4 py-3 rounded-xl bg-slate-900/80 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
          />
        </div>

        {/* Voice icon placeholder */}
        <button
          type="button"
          disabled
          title="Voice input arriving in Milestone 5"
          className="px-3.5 py-3 rounded-xl bg-slate-800/40 border border-slate-800 text-slate-600 cursor-not-allowed flex items-center justify-center"
        >
          <MicOff className="w-4 h-4" />
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
