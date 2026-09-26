"use client";

import React, { useEffect, useRef } from "react";
import { TranscriptMessage } from "../lib/types";
import { MessageSquare, User, Bot, Zap } from "lucide-react";

interface TranscriptProps {
  messages: TranscriptMessage[];
}

export function Transcript({ messages }: TranscriptProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 pb-3 mb-3 border-b border-slate-800 shrink-0">
        <MessageSquare className="w-4 h-4 text-cyan-400" />
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
          Live Conversation Transcript
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 min-h-[300px]">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs italic">
            No dialogue yet. Use the prompt box or scenario chips below to start.
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                    isUser
                      ? msg.isInterruption
                        ? "bg-amber-950/40 border border-amber-500/40 text-amber-100"
                        : "bg-indigo-600/20 border border-indigo-500/30 text-slate-100"
                      : "glass-card border border-slate-800 text-slate-200"
                  }`}
                >
                  {/* Interruption Badge */}
                  {isUser && msg.isInterruption && (
                    <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[9px] font-bold uppercase mb-1.5 border border-amber-500/30">
                      <Zap className="w-2.5 h-2.5" />
                      Interruption Detected &bull; {msg.category || "CLASSIFIED"}
                    </div>
                  )}

                  {/* Image Attachment Preview */}
                  {msg.imageUrl && (
                    <div className="mb-2.5 overflow-hidden rounded-xl border border-indigo-500/40 max-w-[220px]">
                      <img
                        src={msg.imageUrl}
                        alt="Attached content"
                        className="w-full h-auto object-cover max-h-[160px]"
                      />
                    </div>
                  )}

                  <div className="whitespace-pre-wrap">{msg.content || "..."}</div>
                </div>

                {isUser && (
                  <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300 shrink-0 mt-0.5 border border-slate-700">
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
