"use client";

import React from "react";
import { NexusEvent } from "../lib/types";
import { Terminal } from "lucide-react";

interface EventTimelineProps {
  events: NexusEvent[];
}

export function EventTimeline({ events }: EventTimelineProps) {
  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toTimeString().split(" ")[0] + "." + String(d.getMilliseconds()).padStart(3, "0");
    } catch {
      return ts;
    }
  };

  const getEventBadgeColor = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes("INTERRUPTION")) return "bg-rose-500/20 text-rose-300 border-rose-500/30";
    if (t.includes("PLAN_DIFF") || t.includes("REPLAN")) return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    if (t.includes("COMPLETED")) return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    if (t.includes("STARTED")) return "bg-cyan-500/20 text-cyan-300 border-cyan-500/30";
    if (t.includes("CANCELLED")) return "bg-slate-700 text-slate-300 border-slate-600";
    return "bg-indigo-500/20 text-indigo-300 border-indigo-500/30";
  };

  return (
    <div className="glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col h-full font-mono">
      <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Realtime Event Bus Timeline
          </h2>
        </div>
        <span className="text-[10px] text-slate-500">{events.length} events logged</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[160px] text-[11px]">
        {events.length === 0 ? (
          <div className="text-slate-600 italic text-center py-6 text-xs">
            Listening for backend EventBus broadcasts...
          </div>
        ) : (
          events.map((evt, i) => (
            <div
              key={i}
              className="flex items-center gap-3 p-1.5 rounded-lg hover:bg-slate-800/40 transition-colors"
            >
              <span className="text-[10px] text-slate-500 shrink-0">
                {formatTime(evt.timestamp)}
              </span>
              <span
                className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border shrink-0 ${getEventBadgeColor(
                  evt.type
                )}`}
              >
                {evt.type}
              </span>
              <span className="text-slate-300 truncate">
                {evt.data?.state
                  ? `State -> ${evt.data.state} (${evt.data.reason || "transition"})`
                  : evt.data?.task_id
                  ? `Task: ${evt.data.task_id} ${evt.data?.tool ? `[${evt.data.tool}]` : ""}`
                  : evt.data?.text
                  ? `"${evt.data.text.slice(0, 45)}..."`
                  : evt.data?.diff?.summary
                  ? evt.data.diff.summary
                  : JSON.stringify(evt.data)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
