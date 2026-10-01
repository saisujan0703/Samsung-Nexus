"use client";

import React from "react";
import { Plus, MessageSquare, Trash2, Calendar, ChevronRight } from "lucide-react";
import { StoredChatSession } from "../lib/types";

interface ChatHistorySidebarProps {
  sessions: StoredChatSession[];
  activeSessionId: string;
  onSelectSession: (session: StoredChatSession) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
}

export function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}: ChatHistorySidebarProps) {
  // Helper to group sessions by relative time
  const now = Date.now();
  const ONE_DAY = 24 * 60 * 60 * 1000;

  const groups: { label: string; items: StoredChatSession[] }[] = [];

  const todayItems = sessions.filter((s) => now - (s.updatedAt || s.createdAt) < ONE_DAY);
  const yesterdayItems = sessions.filter((s) => {
    const age = now - (s.updatedAt || s.createdAt);
    return age >= ONE_DAY && age < 2 * ONE_DAY;
  });
  const earlierItems = sessions.filter((s) => now - (s.updatedAt || s.createdAt) >= 2 * ONE_DAY);

  if (todayItems.length > 0) groups.push({ label: "Today", items: todayItems });
  if (yesterdayItems.length > 0) groups.push({ label: "Yesterday", items: yesterdayItems });
  if (earlierItems.length > 0) groups.push({ label: "Earlier", items: earlierItems });

  return (
    <aside className="w-full h-full flex flex-col aurora-panel rounded-3xl p-5 border border-emerald-900/20 bg-[#0a0f0c]/90 backdrop-blur-xl relative overflow-hidden">
      {/* Ambient soft glow accents for the right panel */}
      <div className="absolute top-4 right-0 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-6 left-0 w-52 h-52 bg-teal-600/8 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-emerald-950/40 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-200 tracking-wide">History Chat</h2>
        </div>
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 hover:text-emerald-200 border border-emerald-500/30 hover:border-emerald-400/50 text-xs font-medium transition-all shadow-sm shadow-emerald-950/40 active:scale-95"
          title="Start a new conversation"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto space-y-5 pr-1 text-xs">
        {sessions.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <MessageSquare className="w-8 h-8 mb-2 opacity-30 text-emerald-400" />
            <p className="font-medium text-slate-400 text-xs">No chat history yet</p>
            <p className="text-[11px] text-slate-600 mt-1">
              Your conversations will automatically appear here.
            </p>
          </div>
        ) : (
          groups.map((group) => (
            <div key={group.label} className="space-y-1.5">
              <span className="text-[11px] font-semibold text-emerald-500/60 px-2 tracking-wider">
                {group.label}
              </span>
              <div className="space-y-1 mt-1">
                {group.items.map((session) => {
                  const isActive = session.id === activeSessionId;
                  return (
                    <div
                      key={session.id}
                      className={`group relative flex items-center justify-between rounded-xl px-3 py-2.5 transition-all cursor-pointer border ${
                        isActive
                          ? "bg-[#183122]/70 border-emerald-500/40 text-emerald-200 shadow-sm shadow-emerald-900/30 font-medium"
                          : "bg-[#0d1612]/40 hover:bg-[#132219]/60 border-emerald-950/30 hover:border-emerald-500/30 text-slate-300 hover:text-emerald-100"
                      }`}
                      onClick={() => onSelectSession(session)}
                    >
                      <div className="flex items-center gap-2.5 overflow-hidden flex-1 min-w-0 pr-2">
                        <MessageSquare
                          className={`w-3.5 h-3.5 shrink-0 transition-colors ${
                            isActive ? "text-emerald-400" : "text-slate-500 group-hover:text-emerald-400/80"
                          }`}
                        />
                        <span className="truncate text-xs tracking-tight">
                          {session.title || "Untitled Conversation"}
                        </span>
                      </div>

                      {/* Delete button on hover */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-rose-500/20 rounded text-slate-500 hover:text-rose-400 transition-all shrink-0"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
