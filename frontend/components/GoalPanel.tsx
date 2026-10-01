"use client";

import React from "react";
import { Target, ShieldCheck, AlertTriangle, Users, IndianRupee, Footprints, Calendar } from "lucide-react";

interface GoalPanelProps {
  goalSummary: string;
  constraints: Record<string, any>;
  planStatus?: string;
  activeInterruption: {
    type: string;
    confidence: number;
    text: string;
    timestamp: string;
  } | null;
}

export function GoalPanel({ goalSummary, constraints, planStatus, activeInterruption }: GoalPanelProps) {
  // Sanitize any accidental placeholder marks
  const sanitizedGoal = (goalSummary || "")
    .replace(/\?-day/g, "3-day")
    .replace(/\? people/g, "1 person")
    .replace(/for \? people/g, "for 1 person");

  const hasBudget = constraints?.budget !== undefined && constraints?.budget !== null;
  const hasGroup = constraints?.num_people !== undefined && constraints?.num_people !== null;
  const hasWalking = Boolean(constraints?.max_walking);
  const hasDuration = constraints?.duration_days !== undefined && constraints?.duration_days !== null;
  const hasAnyTravelConstraint = hasBudget || hasGroup || hasWalking || hasDuration;
  const isTravelQuery = Boolean(
    sanitizedGoal &&
      /trip|travel|tour|hotel|itinerary|vacation|chennai|bangalore|delhi|mumbai|goa|jaipur|hyderabad/i.test(
        sanitizedGoal
      )
  );
  const showTravelGrid = hasAnyTravelConstraint || isTravelQuery;

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Active Goal & Constraints
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {planStatus && (
            <span
              className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border uppercase ${
                planStatus === "COMPLETE"
                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                  : planStatus === "PARTIAL"
                  ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                  : planStatus === "FAILED"
                  ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                  : "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"
              }`}
            >
              {planStatus}
            </span>
          )}
          <div className="flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            Context Preserved
          </div>
        </div>
      </div>

      {/* Interruption Alert Banner (if active) */}
      {activeInterruption && (
        <div className="p-3 rounded-xl bg-gradient-to-r from-amber-500/15 via-rose-500/15 to-transparent border border-amber-500/30 flex items-start gap-2.5 animate-pulse">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-amber-300 tracking-wide">
                INTERRUPTION DETECTED
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-200">
                {activeInterruption.type}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5 italic">
              &quot;{activeInterruption.text}&quot;
            </p>
          </div>
        </div>
      )}

      {/* Goal Summary Display */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
          Objective
        </span>
        <p className="text-sm font-semibold text-white leading-relaxed">
          {goalSummary || "Awaiting initial task objective from user..."}
        </p>
      </div>

      {/* Conditional Constraints Grid / General Purpose Indicator */}
      {showTravelGrid ? (
        <div className="grid grid-cols-2 gap-2.5">
          {/* Budget */}
          <div className="glass-card rounded-xl p-2.5 flex items-center gap-2.5 border border-slate-800">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
              <IndianRupee className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-medium">Budget</div>
              <div className="text-xs font-bold text-slate-200">
                {hasBudget ? `₹${constraints.budget.toLocaleString()}` : "Not set"}
              </div>
            </div>
          </div>

          {/* Travellers */}
          <div className="glass-card rounded-xl p-2.5 flex items-center gap-2.5 border border-slate-800">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/15 flex items-center justify-center text-indigo-400">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-medium">Group Size</div>
              <div className="text-xs font-bold text-slate-200">
                {hasGroup ? `${constraints.num_people} Travellers` : "1 Person"}
              </div>
            </div>
          </div>

          {/* Walking Preference */}
          <div className="glass-card rounded-xl p-2.5 flex items-center gap-2.5 border border-slate-800">
            <div className="w-7 h-7 rounded-lg bg-cyan-500/15 flex items-center justify-center text-cyan-400">
              <Footprints className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-medium">Walking</div>
              <div className="text-xs font-bold text-slate-200 capitalize">
                {hasWalking ? `${constraints.max_walking} Walking` : "Normal"}
              </div>
            </div>
          </div>

          {/* Duration */}
          <div className="glass-card rounded-xl p-2.5 flex items-center gap-2.5 border border-slate-800">
            <div className="w-7 h-7 rounded-lg bg-purple-500/15 flex items-center justify-center text-purple-400">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-medium">Duration</div>
              <div className="text-xs font-bold text-slate-200">
                {hasDuration ? `${constraints.duration_days} Days` : "3 Days"}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-card rounded-xl p-3 border border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="text-xs text-slate-300 font-medium">Domain Mode</span>
          </div>
          <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 uppercase">
            General Purpose AI
          </span>
        </div>
      )}
    </div>
  );
}

