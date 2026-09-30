"use client";

import React from "react";
import { MatchItem } from "../../lib/types";
import { MatchCard } from "./MatchCard";
import { CalendarX } from "lucide-react";

interface MatchListProps {
  matches: MatchItem[];
  onSelectMatch?: (match: MatchItem) => void;
}

export const MatchList: React.FC<MatchListProps> = ({ matches, onSelectMatch }) => {
  if (matches.length === 0) {
    return (
      <div className="py-8 flex flex-col items-center justify-center text-center text-slate-500 gap-2">
        <CalendarX className="w-8 h-8 text-slate-600 stroke-[1.5]" />
        <span className="text-xs font-medium">No matches found for the selected filter.</span>
        <span className="text-[10px] text-slate-600">Try selecting "All" or a different date filter above.</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2.5 overflow-y-auto max-h-[420px] pr-1 scrollbar-thin">
      {matches.map((match) => (
        <MatchCard key={match.id} match={match} onSelect={onSelectMatch} />
      ))}
    </div>
  );
};
