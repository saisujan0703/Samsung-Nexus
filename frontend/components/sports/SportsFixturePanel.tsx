"use client";

import React, { useState, useMemo } from "react";
import { SportsFixturesPayload, MatchItem } from "../../lib/types";
import { Trophy, Clock, Globe, X, MapPin } from "lucide-react";
import { MatchFilters } from "./MatchFilters";
import { MatchList } from "./MatchList";

interface SportsFixturePanelProps {
  payload: SportsFixturesPayload;
  onClose?: () => void;
}

export const SportsFixturePanel: React.FC<SportsFixturePanelProps> = ({ payload, onClose }) => {
  const [activeStatus, setActiveStatus] = useState<string>("ALL");
  const [activeDateFilter, setActiveDateFilter] = useState<string>("ALL_DATES");
  const [activeCompetition, setActiveCompetition] = useState<string>("ALL");
  const [selectedMatch, setSelectedMatch] = useState<MatchItem | null>(null);

  const allMatches = payload.matches || [];

  // Extract unique competitions for filtering
  const availableCompetitions = useMemo(() => {
    const set = new Set<string>();
    allMatches.forEach((m) => {
      if (m.competition) set.add(m.competition);
    });
    return Array.from(set);
  }, [allMatches]);

  // Extract unique dates for filtering
  const availableDates = useMemo(() => {
    const set = new Set<string>();
    allMatches.forEach((m) => {
      if (m.local_date) set.add(m.local_date);
    });
    return Array.from(set);
  }, [allMatches]);

  // Status counts
  const counts = useMemo(() => {
    return {
      all: allMatches.length,
      live: allMatches.filter((m) => m.status === "LIVE" || m.status === "HALFTIME").length,
      upcoming: allMatches.filter((m) => m.status === "SCHEDULED").length,
      finished: allMatches.filter((m) => m.status === "FINISHED").length,
    };
  }, [allMatches]);

  // Determine dates representation
  const dateLabel = useMemo(() => {
    if (payload.query?.date_from && payload.query?.date_to && payload.query.date_from !== payload.query.date_to) {
      return `${payload.query.date_from} to ${payload.query.date_to}`;
    }
    if (payload.query?.date_from) {
      return payload.query.date_from;
    }
    if (allMatches.length > 0) {
      const uniqueDates = Array.from(new Set(allMatches.map((m) => m.local_date)));
      if (uniqueDates.length === 1) return uniqueDates[0];
      return `${uniqueDates[0]} – ${uniqueDates[uniqueDates.length - 1]}`;
    }
    return "Schedule";
  }, [allMatches, payload.query]);

  // Filtered matches
  const filteredMatches = useMemo(() => {
    return allMatches.filter((m) => {
      // 1. Status filter
      if (activeStatus === "LIVE" && m.status !== "LIVE" && m.status !== "HALFTIME") {
        return false;
      }
      if (activeStatus === "UPCOMING" && m.status !== "SCHEDULED") {
        return false;
      }
      if (activeStatus === "FINISHED" && m.status !== "FINISHED") {
        return false;
      }

      // 2. Competition filter
      if (activeCompetition !== "ALL" && m.competition !== activeCompetition) {
        return false;
      }

      // 3. Date filter (if specific date selected)
      if (activeDateFilter !== "ALL_DATES") {
        if (m.local_date !== activeDateFilter) {
          return false;
        }
      }

      return true;
    });
  }, [allMatches, activeStatus, activeCompetition, activeDateFilter]);


  const competitionTitle =
    payload.query?.competition ||
    payload.query?.sport ||
    (allMatches.length > 0 ? allMatches[0].competition : "Sports Schedule");

  return (
    <div className="glass-panel rounded-2xl p-4 md:p-5 border border-slate-800 flex flex-col gap-3 shadow-xl">
      {/* Panel Header */}
      <div className="flex items-center justify-between gap-2 pb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shrink-0">
            <Trophy className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              {competitionTitle}
            </h2>
            <div className="flex items-center gap-2 text-[10px] text-slate-400">
              <span className="flex items-center gap-1">
                <Globe className="w-2.5 h-2.5 text-cyan-400" />
                {payload.timezone || "Asia/Kolkata"}
              </span>
              <span>&bull;</span>
              <span className="flex items-center gap-1 font-mono">
                <Clock className="w-2.5 h-2.5 text-slate-400" />
                {dateLabel}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            {allMatches.length} Matches
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Spoken Summary Pill (Voice behavior) */}
      {payload.summary && (
        <div className="px-3 py-2 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-medium">
          {payload.summary}
        </div>
      )}

      {/* Filters Bar */}
      <MatchFilters
        activeStatus={activeStatus}
        onStatusChange={setActiveStatus}
        activeDateFilter={activeDateFilter}
        onDateFilterChange={setActiveDateFilter}
        availableDates={availableDates}
        availableCompetitions={availableCompetitions}
        activeCompetition={activeCompetition}
        onCompetitionChange={setActiveCompetition}
        counts={counts}
      />

      {/* Match Cards List */}
      <MatchList matches={filteredMatches} onSelectMatch={(m) => setSelectedMatch(m)} />

      {/* Selected Match Modal / Detail Drawer */}
      {selectedMatch && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-5 border border-slate-700 bg-slate-950 text-slate-100 flex flex-col gap-4 shadow-2xl animate-fadeIn">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                Match Details
              </span>
              <button
                onClick={() => setSelectedMatch(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Teams & Score */}
            <div className="flex items-center justify-around py-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <div className="flex flex-col items-center gap-1.5 text-center max-w-[120px]">
                {selectedMatch.home_team.logo ? (
                  <img
                    src={selectedMatch.home_team.logo}
                    alt={selectedMatch.home_team.name}
                    className="w-10 h-10 object-contain"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs">
                    {selectedMatch.home_team.short_name}
                  </div>
                )}
                <span className="text-xs font-semibold">{selectedMatch.home_team.name}</span>
              </div>

              <div className="flex flex-col items-center">
                {selectedMatch.home_score !== null && selectedMatch.home_score !== undefined ? (
                  <div className="text-2xl font-bold font-mono tracking-wider text-white">
                    {selectedMatch.home_score} - {selectedMatch.away_score}
                  </div>
                ) : (
                  <div className="text-base font-bold text-slate-400">VS</div>
                )}
                <span className="text-[10px] font-mono text-cyan-300 mt-1">
                  {selectedMatch.status_detail || selectedMatch.status}
                </span>
              </div>

              <div className="flex flex-col items-center gap-1.5 text-center max-w-[120px]">
                {selectedMatch.away_team.logo ? (
                  <img
                    src={selectedMatch.away_team.logo}
                    alt={selectedMatch.away_team.name}
                    className="w-10 h-10 object-contain"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs">
                    {selectedMatch.away_team.short_name}
                  </div>
                )}
                <span className="text-xs font-semibold">{selectedMatch.away_team.name}</span>
              </div>
            </div>

            {/* Information Grid */}
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-300 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
              <div>
                <span className="text-slate-500 block text-[10px]">Competition</span>
                <span className="font-medium">{selectedMatch.competition}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Date & Kickoff</span>
                <span className="font-mono text-slate-200">
                  {selectedMatch.local_date} at {selectedMatch.local_start_time}
                </span>
              </div>
              {selectedMatch.venue && (
                <div className="col-span-2">
                  <span className="text-slate-500 block text-[10px]">Venue</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span>{selectedMatch.venue}</span>
                  </div>
                </div>
              )}
              <div>
                <span className="text-slate-500 block text-[10px]">Timezone</span>
                <span className="font-mono text-slate-400">{selectedMatch.timezone}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Data Source</span>
                <span className="text-slate-400">{selectedMatch.source}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
