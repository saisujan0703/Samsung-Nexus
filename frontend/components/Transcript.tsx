"use client";

import React, { useEffect, useRef, useState } from "react";
import { TranscriptMessage, SportsFixturesPayload } from "../lib/types";
import {
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  Volume2,
  RotateCw,
  User,
  Zap,
} from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { SportsFixturePanel } from "./sports/SportsFixturePanel";

interface TranscriptProps {
  messages: TranscriptMessage[];
  latestSportsFixtures?: SportsFixturesPayload | null;
  onSuggestionClick?: (prompt: string) => void;
  onSpeakMessage?: (text: string) => void;
}


export function Transcript({
  messages,
  latestSportsFixtures,
  onSuggestionClick,
  onSpeakMessage,
}: TranscriptProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Record<string, "up" | "down">>({});

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, latestSportsFixtures]);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleFeedback = (id: string, type: "up" | "down") => {
    setFeedback((prev) => ({
      ...prev,
      [id]: prev[id] === type ? undefined! : type,
    }));
  };

  // Find the last assistant message id
  const lastAssistantMsgId = [...messages].reverse().find((m) => m.role === "assistant")?.id;

  return (
    <div className="w-full h-full flex flex-col aurora-panel chat-aurora-fog rounded-3xl p-6 border border-emerald-900/20 bg-[#0a0f0c]/90 backdrop-blur-xl relative overflow-hidden">
      {/* Ambient aurora glow (balanced across left, right, and base) */}
      <div className="absolute top-8 left-0 w-96 h-96 bg-emerald-500/14 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-16 right-0 w-80 h-80 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute -bottom-8 left-1/4 w-96 h-64 bg-emerald-600/8 rounded-full blur-3xl pointer-events-none -z-10" />



      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-2 min-h-[350px]">
        {messages.length === 0 ? (
          /* Empty State (matches reference look & feel) */
          <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto">
            {/* Concentric glowing SURU Logo avatar */}
            <div className="relative w-16 h-16 rounded-full flex items-center justify-center mb-6">
              <div className="w-14 h-14 rounded-full bg-[#0e1c14] border border-[#2b5838] flex items-center justify-center shadow-[0_0_20px_rgba(52,211,153,0.25)]">
                <div className="w-9 h-9 rounded-full border border-[#3e804f] flex items-center justify-center">
                  <div className="w-3.5 h-3.5 rounded-full bg-[#34d399] shadow-[0_0_10px_#34d399]" />
                </div>
              </div>
            </div>

            <h2 className="text-xl font-medium text-slate-100 tracking-tight mb-2">SURU AI</h2>
            <p className="text-sm text-slate-400 font-normal">How can I help you today?</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";
            const messageFixtures =
              msg.sportsFixtures ||
              (!isUser && msg.id === lastAssistantMsgId && latestSportsFixtures?.matches?.length
                ? latestSportsFixtures
                : null);

            const hasSportsFixtures =
              !isUser && !!messageFixtures && (messageFixtures.matches?.length || 0) > 0;

            return (
              <div
                key={msg.id}
                className={`flex gap-3.5 ${isUser ? "justify-end" : "justify-start"} items-start group`}
              >
                {/* Assistant Concentric Avatar (Exact match to reference) */}
                {!isUser && (
                  <div className="w-8 h-8 rounded-full bg-[#0d1812] border border-[#2b5838] flex items-center justify-center shrink-0 mt-0.5 shadow-sm shadow-emerald-950/80 relative">
                    <div className="w-5 h-5 rounded-full border border-[#3e804f] flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-[#34d399] shadow-[0_0_8px_#34d399]" />
                    </div>
                  </div>
                )}

                <div className={`flex flex-col gap-1.5 ${isUser ? "items-end max-w-[80%]" : "items-start max-w-[90%]"}`}>
                  {/* Message Bubble: User is olive-green gradient, Assistant is deep dark shade */}
                  <div
                    className={`rounded-2xl p-4 text-xs leading-relaxed transition-all duration-150 ${
                      isUser
                        ? msg.isInterruption
                          ? "bg-amber-950/40 border border-amber-500/40 text-amber-100 rounded-tr-sm"
                          : "user-bubble-gradient rounded-tr-sm"
                        : "assistant-bubble-dark rounded-tl-sm"
                    } ${hasSportsFixtures ? "w-full" : ""}`}
                  >
                    {/* Interruption Indicator */}
                    {isUser && msg.isInterruption && (
                      <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[9px] font-bold uppercase mb-2 border border-amber-500/30">
                        <Zap className="w-2.5 h-2.5" />
                        Interruption &bull; {msg.category || "CLASSIFIED"}
                      </div>
                    )}

                    {/* Image Attachment Preview */}
                    {msg.imageUrl && (
                      <div className="mb-3 overflow-hidden rounded-xl border border-emerald-500/30 max-w-[260px]">
                        <img
                          src={msg.imageUrl}
                          alt="Attached media"
                          className="w-full h-auto object-cover max-h-[180px]"
                        />
                      </div>
                    )}

                    {isUser ? (
                      <div className="whitespace-pre-wrap font-normal text-xs">{msg.content || "..."}</div>
                    ) : (
                      <>
                        <MarkdownRenderer content={msg.content || "..."} />
                        {hasSportsFixtures && messageFixtures && (
                          <div className="mt-4 pt-3 border-t border-white/5">
                            <SportsFixturePanel payload={messageFixtures} />
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Message Action Toolbar for Assistant (matches reference image) */}
                  {!isUser && msg.content && (
                    <div className="flex items-center gap-1 text-slate-500 px-1 pt-0.5">
                      <button
                        type="button"
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="p-1 rounded-md hover:text-slate-300 hover:bg-white/5 transition-colors"
                        title="Copy message"
                      >
                        {copiedId === msg.id ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleFeedback(msg.id, "up")}
                        className={`p-1 rounded-md transition-colors ${
                          feedback[msg.id] === "up"
                            ? "text-emerald-400 bg-emerald-500/10"
                            : "hover:text-slate-300 hover:bg-white/5"
                        }`}
                        title="Good response"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleFeedback(msg.id, "down")}
                        className={`p-1 rounded-md transition-colors ${
                          feedback[msg.id] === "down"
                            ? "text-rose-400 bg-rose-500/10"
                            : "hover:text-slate-300 hover:bg-white/5"
                        }`}
                        title="Poor response"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>

                      {onSpeakMessage && (
                        <button
                          type="button"
                          onClick={() => onSpeakMessage(msg.content)}
                          className="p-1 rounded-md hover:text-slate-300 hover:bg-white/5 transition-colors"
                          title="Read aloud"
                        >
                          <Volume2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* User Avatar Circle */}
                {isUser && (
                  <div className="w-8 h-8 rounded-full bg-[#182a1f] border border-[#2d4d38] flex items-center justify-center text-[#9ed4ad] shrink-0 mt-0.5 shadow-sm">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
