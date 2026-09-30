"use client";

import React, { useState } from "react";
import { MatchItem } from "../../lib/types";
import { Clock, MapPin, Shield, ChevronDown, ChevronUp, Radio } from "lucide-react";

interface MatchCardProps {
  match: MatchItem;
  onSelect?: (match: MatchItem) => void;
}

export const MatchCard: React.FC<MatchCardProps> = ({ match, onSelect }) => {
  const [expanded, setExpanded] = useState(false);

  const isLive = match.status === "LIVE" || match.status === "HALFTIME";
  const isFinished = match.status === "FINISHED";
  const isScheduled = match.status === "SCHEDULED";

  const getStatusBadge = () => {
    if (isLive) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 animate-pulse">
          <Radio className="w-2.5 h-2.5" />
          {match.status === "HALFTIME" ? "HT" : (match.elapsed_time || "LIVE")}
        </span>
      );
    }
    if (isFinished) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide uppercase bg-slate-800 text-slate-400 border border-slate-700/60">
          {match.status_detail || "FT"}
        </span>
      );
    }
    if (match.status === "POSTPONED" || match.status === "CANCELLED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide uppercase bg-rose-500/20 text-rose-400 border border-rose-500/30">
          {match.status}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium tracking-wide text-cyan-300 bg-cyan-950/40 border border-cyan-800/40">
        <Clock className="w-2.5 h-2.5" />
        {match.local_start_time}
      </span>
    );
  };

  const renderLogo = (logoUrl: string | null | undefined, name: string, short: string) => {
    if (logoUrl) {
      return (
        <img
          src={logoUrl}
          alt={name}
          className="w-6 h-6 object-contain shrink-0"
          onError={(e) => {
            (e.target as HTMLElement).style.display = "none";
          }}
        />
      );
    }
    return (
      <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[9px] font-bold text-slate-300 shrink-0">
        {short ? short.slice(0, 3) : <Shield className="w-3 h-3 text-slate-400" />}
      </div>
    );
  };

  return (
    <div
      onClick={() => {
        setExpanded(!expanded);
        if (onSelect) onSelect(match);
      }}
      className={`glass-card rounded-xl p-3 border transition-all duration-200 cursor-pointer ${
        isLive
          ? "border-emerald-500/40 bg-emerald-950/10 hover:border-emerald-500/60 shadow-lg shadow-emerald-950/20"
          : "border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-900/60"
      }`}
    >
      {/* Top Meta Bar */}
      <div className="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-slate-800/60 text-[10px]">
        <div className="flex items-center gap-1.5 text-slate-400 truncate">
          <span className="font-semibold text-slate-300 truncate max-w-[150px]">
            {match.competition}
          </span>
          {match.stage && (
            <span className="text-slate-500">&bull; {match.stage}</span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-slate-400 font-mono text-[9px]">
            {match.local_date}
          </span>
          {getStatusBadge()}
        </div>
      </div>

      {/* Main Competitors Grid */}
      <div className="grid grid-cols-12 items-center gap-2 py-1">
        {/* Home Team */}
        <div className="col-span-5 flex items-center gap-2 justify-end text-right">
          <span className="text-xs font-semibold text-slate-100 truncate">
            {match.home_team.name}
          </span>
          {renderLogo(match.home_team.logo, match.home_team.name, match.home_team.short_name)}
        </div>

        {/* Center Score / VS */}
        <div className="col-span-2 flex flex-col items-center justify-center">
          {match.home_score !== null && match.home_score !== undefined ? (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900/80 border border-slate-700/60 font-mono text-xs font-bold text-white shadow-inner">
              <span className={isLive ? "text-emerald-400" : ""}>{match.home_score}</span>
              <span className="text-slate-500">-</span>
              <span className={isLive ? "text-emerald-400" : ""}>{match.away_score}</span>
            </div>
          ) : (
            <span className="text-[10px] font-bold text-slate-400 tracking-wider">
              VS
            </span>
          )}
          {isLive && match.elapsed_time && (
            <span className="text-[9px] font-mono text-emerald-400 mt-0.5">
              {match.elapsed_time}
            </span>
          )}
        </div>

        {/* Away Team */}
        <div className="col-span-5 flex items-center gap-2 justify-start text-left">
          {renderLogo(match.away_team.logo, match.away_team.name, match.away_team.short_name)}
          <span className="text-xs font-semibold text-slate-100 truncate">
            {match.away_team.name}
          </span>
        </div>
      </div>

      {/* Expand/Collapse Indicator */}
      <div className="flex items-center justify-center mt-1 text-slate-500 hover:text-slate-300">
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </div>

      {/* Expanded Details Drawer */}
      {expanded && (
        <div className="mt-2.5 pt-2.5 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[10px] text-slate-300 bg-slate-950/40 p-2.5 rounded-lg animate-fadeIn">
          {match.venue && (
            <div className="col-span-2 flex items-center gap-1.5 text-slate-400">
              <MapPin className="w-3 h-3 text-cyan-400 shrink-0" />
              <span className="truncate">{match.venue}</span>
            </div>
          )}
          <div>
            <span className="text-slate-500 block">Kickoff (Local):</span>
            <span className="font-mono text-slate-200">
              {match.local_date} at {match.local_start_time} ({match.timezone})
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Status:</span>
            <span className="font-semibold text-slate-200">
              {match.status_detail || match.status}
            </span>
          </div>
          <div className="col-span-2 flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-800/40">
            <span>Source: {match.source}</span>
            <span>Match ID: {match.id}</span>
          </div>
        </div>
      )}
    </div>
  );
};
