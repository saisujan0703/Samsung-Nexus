"use client";

import { Volume2, Square, User, LogOut } from "lucide-react";
import { AuthUser } from "../lib/types";

interface HeaderProps {
  connected: boolean;
  sessionId: string;
  onReset: () => void;
  isSpeaking?: boolean;
  cancelSpeech?: () => void;
  user: AuthUser | null;
  onLogout: () => void;
  onOpenLogin: () => void;
}

export function Header({
  connected,
  sessionId,
  onReset,
  isSpeaking,
  cancelSpeech,
  user,
  onLogout,
  onOpenLogin,
}: HeaderProps) {
  return (
    <header className="w-full flex items-center justify-between px-2 py-2 mb-4 shrink-0">
      {/* Left Navigation Pill Group */}
      <div className="flex items-center gap-1.5 p-1.5 rounded-full bg-[#0a0f0c]/90 border border-emerald-900/30 backdrop-blur-xl shadow-sm">
        <button
          type="button"
          className="flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium bg-[#183122] text-emerald-300 border border-emerald-500/40 shadow-sm"
        >
          <span>AI Chat</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
        </button>

        <button
          type="button"
          onClick={onReset}
          className="px-4 py-1.5 rounded-full text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all"
          title="Start fresh conversation"
        >
          New Chat
        </button>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2">
        {/* Speaking indicator and Stop Speech button */}
        {isSpeaking && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/15 border border-emerald-400/40 text-emerald-300 animate-pulse text-xs font-semibold shadow-sm">
            <Volume2 className="w-3.5 h-3.5 text-emerald-400 animate-bounce" />
            <span className="hidden sm:inline">Speaking</span>
            {cancelSpeech && (
              <button
                type="button"
                onClick={cancelSpeech}
                title="Stop Speech"
                className="ml-1 px-2 py-0.5 rounded-full bg-rose-500/30 hover:bg-rose-500/50 text-rose-200 border border-rose-400/40 text-[10px] font-bold flex items-center gap-1 transition-colors"
              >
                <Square className="w-2.5 h-2.5 fill-current" />
                <span>Stop</span>
              </button>
            )}
          </div>
        )}

        {/* User Account / Profile & Logout (Replaces cluttered pill) */}
        {user ? (
          <div className="flex items-center gap-2 p-1.5 pl-3 rounded-full bg-[#0a0f0c]/90 border border-emerald-900/30 backdrop-blur-xl shadow-sm">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold text-xs shadow-sm">
                {user.display_name ? user.display_name.charAt(0).toUpperCase() : "U"}
              </div>
              <span className="text-xs font-semibold text-slate-200 hidden sm:inline max-w-[120px] truncate">
                {user.display_name}
              </span>
            </div>

            <button
              type="button"
              onClick={onLogout}
              className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-medium transition-all active:scale-95 ml-1 cursor-pointer"
              title="Log out of account"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Log Out</span>
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onOpenLogin}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold shadow-sm transition-all cursor-pointer"
          >
            <User className="w-3.5 h-3.5" />
            <span>Log In</span>
          </button>
        )}
      </div>
    </header>
  );
}
