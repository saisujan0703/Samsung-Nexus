"use client";

import React from "react";
import { useNexusWebSocket } from "../hooks/useNexusWebSocket";
import { Header } from "../components/Header";
import { AgentOrb } from "../components/AgentOrb";
import { GoalPanel } from "../components/GoalPanel";
import { TaskGraph } from "../components/TaskGraph";
import { Transcript } from "../components/Transcript";
import { EventTimeline } from "../components/EventTimeline";
import { InputArea } from "../components/InputArea";

export default function Home() {
  const {
    sessionId,
    connected,
    agentState,
    tasks,
    goalSummary,
    constraints,
    planDiff,
    messages,
    events,
    activeInterruption,
    sendUserInput,
    uploadImage,
    sendSpeechStarted,
    resetSession,
    isSpeaking,
    isMuted,
    toggleMute,
    cancelSpeech,
    isTtsSupported,
  } = useNexusWebSocket();

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Header */}
      <Header
        connected={connected}
        sessionId={sessionId}
        onReset={resetSession}
        isSpeaking={isSpeaking}
        isMuted={isMuted}
        toggleMute={toggleMute}
        cancelSpeech={cancelSpeech}
        isTtsSupported={isTtsSupported}
      />

      {/* Main Operations Grid */}
      <main className="flex-1 p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-5 max-w-[1700px] w-full mx-auto">
        {/* LEFT COLUMN: Agent Orb & Status (3 Cols) */}
        <div className="lg:col-span-3 flex flex-col gap-5">
          <AgentOrb state={agentState} />

          {/* Core Innovation Callout */}
          <div className="glass-panel rounded-2xl p-4.5 border border-slate-800 text-xs flex flex-col gap-2">
            <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
              SURU AI Core Innovation
            </span>
            <p className="text-slate-300 font-medium leading-relaxed">
              When interrupted, SURU AI does not restart. It classifies the intent, preserves valid findings, calculates a <span className="text-cyan-300 font-bold">Plan Diff</span>, selectively cancels only obsolete tasks, and resumes execution seamlessly.
            </p>
          </div>
        </div>

        {/* CENTER COLUMN: Live Transcript & Input (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4 min-h-[580px]">
          <div className="flex-1">
            <Transcript messages={messages} />
          </div>
          <div className="shrink-0">
            <InputArea
              onSend={sendUserInput}
              onUploadImage={uploadImage}
              disabled={!connected}
              onCancelSpeech={cancelSpeech}
              onSpeechStart={sendSpeechStarted}
            />
          </div>
        </div>

        {/* RIGHT COLUMN: Goal, Constraints & Task Graph DAG (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          <GoalPanel
            goalSummary={goalSummary}
            constraints={constraints}
            activeInterruption={activeInterruption}
          />
          <TaskGraph tasks={tasks} planDiff={planDiff} />
        </div>

        {/* BOTTOM: Event Bus Timeline (Span full 12 Cols) */}
        <div className="lg:col-span-12 mt-1">
          <EventTimeline events={events} />
        </div>
      </main>
    </div>
  );
}
