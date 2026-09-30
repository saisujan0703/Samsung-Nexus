"use client";

import React from "react";
import { MatchStatus } from "../../lib/types";

interface MatchFiltersProps {
  activeStatus: string;
  onStatusChange: (status: string) => void;
  activeDateFilter: string;
  onDateFilterChange: (date: string) => void;
  availableDates: string[];
  availableCompetitions: string[];
  activeCompetition: string;
  onCompetitionChange: (comp: string) => void;
  counts: {
    all: number;
    live: number;
    upcoming: number;
    finished: number;
  };
}

export const MatchFilters: React.FC<MatchFiltersProps> = ({
  activeStatus,
  onStatusChange,
  activeDateFilter,
  onDateFilterChange,
  availableDates,
  availableCompetitions,
  activeCompetition,
  onCompetitionChange,
  counts,
}) => {
  return (
    <div className="flex flex-col gap-2 pb-1">
      {/* Top row: Status & Date Filters */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Status Filter Buttons */}
        <div className="flex items-center gap-1 bg-slate-900/80 p-0.5 rounded-lg border border-slate-800 text-[11px]">
          <button
            onClick={() => onStatusChange("ALL")}
            className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
              activeStatus === "ALL"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            All ({counts.all})
          </button>

          {counts.live > 0 && (
            <button
              onClick={() => onStatusChange("LIVE")}
              className={`px-2 py-0.5 rounded-md font-medium transition-colors flex items-center gap-1 ${
                activeStatus === "LIVE"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold"
                  : "text-emerald-400 hover:text-emerald-300"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live ({counts.live})
            </button>
          )}

          <button
            onClick={() => onStatusChange("UPCOMING")}
            className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
              activeStatus === "UPCOMING"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Upcoming ({counts.upcoming})
          </button>

          <button
            onClick={() => onStatusChange("FINISHED")}
            className={`px-2 py-0.5 rounded-md font-medium transition-colors ${
              activeStatus === "FINISHED"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Finished ({counts.finished})
          </button>
        </div>

        {/* Dynamic Date Filter Chips */}
        {availableDates.length > 1 && (
          <div className="flex items-center gap-1 text-[10px] text-slate-400 overflow-x-auto py-0.5 scrollbar-none">
            <button
              onClick={() => onDateFilterChange("ALL_DATES")}
              className={`px-2 py-0.5 rounded border transition-colors shrink-0 ${
                activeDateFilter === "ALL_DATES"
                  ? "bg-indigo-600/30 text-indigo-200 border-indigo-500/50"
                  : "border-slate-800 hover:border-slate-700 hover:text-slate-300"
              }`}
            >
              All Dates
            </button>
            {availableDates.map((d) => (
              <button
                key={d}
                onClick={() => onDateFilterChange(d)}
                className={`px-2 py-0.5 rounded border transition-colors shrink-0 ${
                  activeDateFilter === d
                    ? "bg-indigo-600/30 text-indigo-200 border-indigo-500/50"
                    : "border-slate-800 hover:border-slate-700 hover:text-slate-300"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Optional: Competition Pills if matches span multiple competitions */}
      {availableCompetitions.length > 1 && (
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none text-[10px]">
          <span className="text-slate-500 shrink-0 font-medium">Competition:</span>
          <button
            onClick={() => onCompetitionChange("ALL")}
            className={`px-2 py-0.5 rounded-full shrink-0 border transition-colors ${
              activeCompetition === "ALL"
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                : "bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700"
            }`}
          >
            All Competitions
          </button>
          {availableCompetitions.map((comp) => (
            <button
              key={comp}
              onClick={() => onCompetitionChange(comp)}
              className={`px-2 py-0.5 rounded-full shrink-0 border transition-colors truncate max-w-[160px] ${
                activeCompetition === comp
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                  : "bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700"
              }`}
            >
              {comp}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
