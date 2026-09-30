"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Compass,
  Globe,
  Sliders,
  Settings,
  Sparkles,
  Search,
  Trophy,
  Mic,
  Clock,
  Download,
  Trash2,
  ChevronRight,
  ShieldCheck,
  Cpu,
  Volume2,
  LogOut,
} from "lucide-react";
import { TranscriptMessage, AuthUser } from "../lib/types";

export type NavModalTab = "explore" | "engines" | "preferences" | "settings";

interface NavDrawerModalProps {
  isOpen: boolean;
  activeTab: NavModalTab | null;
  onClose: () => void;
  onSelectPrompt: (prompt: string) => void;
  onClearChat: () => void;
  messages: TranscriptMessage[];
  connected: boolean;
  sessionId: string;
  user: AuthUser | null;
  onLogout?: () => void;
}

export function NavDrawerModal({
  isOpen,
  activeTab,
  onClose,
  onSelectPrompt,
  onClearChat,
  messages,
  connected,
  sessionId,
  user,
  onLogout,
}: NavDrawerModalProps) {
  const [currentTab, setCurrentTab] = useState<NavModalTab>("explore");
  const [speechRate, setSpeechRate] = useState(1.0);
  const [speechPitch, setSpeechPitch] = useState(1.0);
  const [responseStyle, setResponseStyle] = useState<"concise" | "detailed">("concise");

  useEffect(() => {
    if (activeTab) {
      setCurrentTab(activeTab);
    }
  }, [activeTab]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Export as Markdown
  const handleExportMarkdown = () => {
    if (messages.length === 0) {
      alert("No messages to export.");
      return;
    }
    const mdContent = messages
      .map(
        (m) =>
          `### ${m.role === "user" ? "User" : "SURU AI"} (${new Date(
            m.timestamp
          ).toLocaleTimeString()})\n\n${m.content}\n`
      )
      .join("\n---\n\n");

    const blob = new Blob([`# SURU AI Conversation Transcript\n\n${mdContent}`], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `suru-ai-chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export as JSON
  const handleExportJSON = () => {
    if (messages.length === 0) {
      alert("No messages to export.");
      return;
    }
    const jsonContent = JSON.stringify(messages, null, 2);
    const blob = new Blob([jsonContent], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `suru-ai-transcript-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 md:p-10">
      {/* Blurred Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-md transition-opacity animate-in fade-in"
        onClick={onClose}
      />

      {/* Main Glass Modal Window */}
      <div className="relative w-full max-w-2xl max-h-[85vh] flex flex-col aurora-panel rounded-3xl border border-emerald-500/25 bg-[#090f0c]/95 shadow-[0_25px_60px_rgba(0,0,0,0.85)] z-10 overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Subtle Ambient Aurora Light Accent */}
        <div className="absolute -top-16 -left-16 w-64 h-64 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="absolute -bottom-16 -right-16 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -z-10" />

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-emerald-900/30 shrink-0">
          <div className="flex items-center gap-2">
            {currentTab === "explore" && <Compass className="w-5 h-5 text-emerald-400" />}
            {currentTab === "engines" && <Globe className="w-5 h-5 text-teal-400" />}
            {currentTab === "preferences" && <Sliders className="w-5 h-5 text-emerald-300" />}
            {currentTab === "settings" && <Settings className="w-5 h-5 text-emerald-400" />}
            <h2 className="text-base font-semibold text-slate-100 tracking-tight">
              {currentTab === "explore" && "Capabilities & Prompt Gallery"}
              {currentTab === "engines" && "Connected Engines & Sources"}
              {currentTab === "preferences" && "Interaction & Voice Preferences"}
              {currentTab === "settings" && "Session & System Settings"}
            </h2>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Tab Switcher inside Modal */}
            <div className="flex items-center bg-[#101a14] p-1 rounded-xl border border-emerald-950/60 mr-2">
              <button
                type="button"
                onClick={() => setCurrentTab("explore")}
                className={`p-1.5 rounded-lg text-xs transition-colors ${
                  currentTab === "explore"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Capabilities Gallery"
              >
                <Compass className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentTab("engines")}
                className={`p-1.5 rounded-lg text-xs transition-colors ${
                  currentTab === "engines"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Connected Engines"
              >
                <Globe className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentTab("preferences")}
                className={`p-1.5 rounded-lg text-xs transition-colors ${
                  currentTab === "preferences"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Preferences"
              >
                <Sliders className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentTab("settings")}
                className={`p-1.5 rounded-lg text-xs transition-colors ${
                  currentTab === "settings"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-emerald-950/40 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* TAB 1: EXPLORE CAPABILITIES */}
          {currentTab === "explore" && (
            <div className="space-y-6 text-sm">
              <p className="text-slate-400 text-xs leading-relaxed">
                Click any prompt below to automatically launch it in SURU AI with real-time streaming:
              </p>

              {/* Group 1: Live Sports */}
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                  <Trophy className="w-3.5 h-3.5" />
                  <span>Real-Time Sports Radar & Fixtures</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    "Tell me today's UEFA Champions League matches",
                    "What matches are scheduled for September 28?",
                    "Give me the complete schedule of IPL 2025",
                    "What is the next match for Real Madrid?",
                  ].map((p, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        onSelectPrompt(p);
                        onClose();
                      }}
                      className="p-3 text-left rounded-2xl bg-[#121c17]/80 hover:bg-[#192b1f] border border-emerald-900/30 hover:border-emerald-500/50 text-slate-200 hover:text-emerald-200 text-xs transition-all shadow-sm flex items-center justify-between group"
                    >
                      <span className="truncate pr-2">{p}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-emerald-600 group-hover:text-emerald-400 shrink-0 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>

              {/* Group 2: Web Intelligence */}
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-teal-400 uppercase tracking-wider">
                  <Search className="w-3.5 h-3.5" />
                  <span>Deep Web Intelligence & Verified Facts</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    "What are the latest developments in generative AI this week?",
                    "What happened in global space exploration recently?",
                    "Explain photosynthesis in 2 clear sentences",
                    "How do quantum computers differ from classical binary computers?",
                  ].map((p, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        onSelectPrompt(p);
                        onClose();
                      }}
                      className="p-3 text-left rounded-2xl bg-[#121c17]/80 hover:bg-[#192b1f] border border-emerald-900/30 hover:border-emerald-500/50 text-slate-200 hover:text-emerald-200 text-xs transition-all shadow-sm flex items-center justify-between group"
                    >
                      <span className="truncate pr-2">{p}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-emerald-600 group-hover:text-emerald-400 shrink-0 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>

              {/* Group 3: Voice & Interruption */}
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300 uppercase tracking-wider">
                  <Mic className="w-3.5 h-3.5" />
                  <span>Interruptible Voice & Multi-Step Reasoning</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    "Give me a detailed 5-day itinerary for a trip to Japan",
                    "Compare Mars colonization challenges versus ocean exploration",
                  ].map((p, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        onSelectPrompt(p);
                        onClose();
                      }}
                      className="p-3 text-left rounded-2xl bg-[#121c17]/80 hover:bg-[#192b1f] border border-emerald-900/30 hover:border-emerald-500/50 text-slate-200 hover:text-emerald-200 text-xs transition-all shadow-sm flex items-center justify-between group"
                    >
                      <span className="truncate pr-2">{p}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-emerald-600 group-hover:text-emerald-400 shrink-0 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CONNECTED ENGINES & SOURCES */}
          {currentTab === "engines" && (
            <div className="space-y-4 text-xs">
              <p className="text-slate-400 leading-relaxed">
                SURU AI operates with autonomous multi-source retrieval engines synchronized in real-time:
              </p>

              <div className="space-y-2.5">
                {/* Engine 1 */}
                <div className="p-3.5 rounded-2xl bg-[#121c17]/70 border border-emerald-900/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                      <Search className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-100">Bing Web & News Search Engine</h4>
                      <p className="text-[11px] text-slate-400">Live authoritative web verification & recency lookup</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Active
                  </span>
                </div>

                {/* Engine 2 */}
                <div className="p-3.5 rounded-2xl bg-[#121c17]/70 border border-emerald-900/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                      <Trophy className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-100">Global Sports Radar Provider</h4>
                      <p className="text-[11px] text-slate-400">Structured fixtures, scores & multi-league schedules</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    Connected
                  </span>
                </div>

                {/* Engine 3 */}
                <div className="p-3.5 rounded-2xl bg-[#121c17]/70 border border-emerald-900/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-300">
                      <Mic className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-100">Neural Voice & Interruption Bus</h4>
                      <p className="text-[11px] text-slate-400">Web Speech STT with sub-second interruption handling</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/40 text-[10px] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
                    Ready
                  </span>
                </div>

                {/* Engine 4 */}
                <div className="p-3.5 rounded-2xl bg-[#121c17]/70 border border-emerald-900/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                      <Clock className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-100">Temporal Grounding Engine</h4>
                      <p className="text-[11px] text-slate-400">Asia/Kolkata timezone & relative date interpretation</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    Synchronized
                  </span>
                </div>

                {/* Engine 5 */}
                <div className="p-3.5 rounded-2xl bg-[#121c17]/70 border border-emerald-900/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                      <Cpu className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-100">Gemini 2.5 Flash Reasoning Core</h4>
                      <p className="text-[11px] text-slate-400">Autonomous planning and zero-latency WebSocket stream</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    Active
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: PREFERENCES */}
          {currentTab === "preferences" && (
            <div className="space-y-6 text-xs">
              {/* Response Mode */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-200">Response Mode</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setResponseStyle("concise")}
                    className={`p-3 rounded-2xl border text-left transition-all ${
                      responseStyle === "concise"
                        ? "bg-[#183122] border-emerald-500/50 text-emerald-200"
                        : "bg-[#101813] border-emerald-950/60 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <div className="font-semibold text-xs mb-0.5">Direct & Concise</div>
                    <div className="text-[10px] text-slate-400">Crisp, fast, and straight to the answer</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setResponseStyle("detailed")}
                    className={`p-3 rounded-2xl border text-left transition-all ${
                      responseStyle === "detailed"
                        ? "bg-[#183122] border-emerald-500/50 text-emerald-200"
                        : "bg-[#101813] border-emerald-950/60 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <div className="font-semibold text-xs mb-0.5">Comprehensive</div>
                    <div className="text-[10px] text-slate-400">In-depth breakdown and full structured details</div>
                  </button>
                </div>
              </div>

              {/* Speech Controls */}
              <div className="space-y-4 p-4 rounded-2xl bg-[#121c17]/60 border border-emerald-900/30">
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                  <Volume2 className="w-4 h-4" />
                  <span>Speech Synthesis Tuning</span>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-slate-300">
                    <span>Voice Rate ({speechRate.toFixed(1)}x)</span>
                    <span className="text-slate-500">Normal: 1.0x</span>
                  </div>
                  <input
                    type="range"
                    min="0.8"
                    max="1.5"
                    step="0.1"
                    value={speechRate}
                    onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                    className="w-full accent-emerald-500 cursor-pointer"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-slate-300">
                    <span>Voice Pitch ({speechPitch.toFixed(1)}x)</span>
                    <span className="text-slate-500">Natural: 1.0x</span>
                  </div>
                  <input
                    type="range"
                    min="0.8"
                    max="1.2"
                    step="0.1"
                    value={speechPitch}
                    onChange={(e) => setSpeechPitch(parseFloat(e.target.value))}
                    className="w-full accent-emerald-500 cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: SYSTEM & SESSION SETTINGS */}
          {currentTab === "settings" && (
            <div className="space-y-6 text-xs">
              {/* Connection Status Card */}
              <div className="p-4 rounded-2xl bg-[#121c17]/60 border border-emerald-900/30">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">WebSocket Gateway</span>
                  <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                    {connected ? "Connected (Live)" : "Disconnected"}
                  </span>
                </div>
              </div>

              {/* Export Transcript */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-200">Export Conversation</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={handleExportMarkdown}
                    className="p-3 rounded-2xl bg-[#121c17]/80 hover:bg-[#18291f] border border-emerald-900/30 hover:border-emerald-500/40 text-slate-200 hover:text-emerald-200 text-left transition-all flex items-center gap-2.5 group"
                  >
                    <Download className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-semibold text-xs">Export Markdown</div>
                      <div className="text-[10px] text-slate-400">Save as formatted .md file</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={handleExportJSON}
                    className="p-3 rounded-2xl bg-[#121c17]/80 hover:bg-[#18291f] border border-emerald-900/30 hover:border-emerald-500/40 text-slate-200 hover:text-emerald-200 text-left transition-all flex items-center gap-2.5 group"
                  >
                    <Download className="w-4 h-4 text-teal-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-semibold text-xs">Export JSON</div>
                      <div className="text-[10px] text-slate-400">Raw messages & payloads</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* User Account & Logout */}
              {user && (
                <div className="p-4 rounded-2xl bg-[#121c17]/60 border border-emerald-900/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold text-sm shadow-sm">
                      {user.display_name ? user.display_name.charAt(0).toUpperCase() : "U"}
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-100">{user.display_name}</h4>
                      <p className="text-[11px] text-slate-400">{user.email}</p>
                    </div>
                  </div>
                  {onLogout && (
                    <button
                      type="button"
                      onClick={() => {
                        onLogout();
                        onClose();
                      }}
                      className="px-3.5 py-1.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Log Out</span>
                    </button>
                  )}
                </div>
              )}

              {/* Danger Zone: Clear Current Conversation */}
              <div className="p-4 rounded-2xl bg-rose-950/15 border border-rose-900/30 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-rose-300">Reset Current Conversation</h4>
                    <p className="text-[10px] text-slate-400">
                      Clears current transcript and resets agent working memory
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (confirm("Reset current conversation?")) {
                        onClearChat();
                        onClose();
                      }
                    }}
                    className="px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/40 text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-95"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear Chat</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-emerald-900/30 bg-[#070c09] flex items-center justify-between text-[11px] text-slate-400 shrink-0">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>SURU AI Autonomous Real-Time Assistant</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
