"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNexusWebSocket } from "../hooks/useNexusWebSocket";
import { useChatHistory } from "../hooks/useChatHistory";
import { Header } from "../components/Header";
import { NavRail } from "../components/NavRail";
import { Transcript } from "../components/Transcript";
import { InputArea } from "../components/InputArea";
import { ChatHistorySidebar } from "../components/ChatHistorySidebar";
import { NavDrawerModal, NavModalTab } from "../components/NavDrawerModal";
import { AuthModal } from "../components/AuthModal";
import { StoredChatSession, AuthUser, TranscriptMessage } from "../lib/types";

export default function Home() {
  const [modalTab, setModalTab] = useState<NavModalTab | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isAuthChecked, setIsAuthChecked] = useState(false);

  // Check saved auth session on mount
  useEffect(() => {
    try {
      const savedUser = localStorage.getItem("suru_auth_user");
      if (savedUser) {
        setUser(JSON.parse(savedUser));
      } else {
        setIsAuthModalOpen(true);
      }
    } catch (e) {
      setIsAuthModalOpen(true);
    } finally {
      setIsAuthChecked(true);
    }
  }, []);

  const {
    sessions,
    activeSessionId,
    activeSession,
    createNewSession,
    updateSession,
    selectSession,
    deleteSession,
    isLoaded: isHistoryLoaded,
  } = useChatHistory(user);

  const {
    sessionId,
    connected,
    agentState,
    tasks,
    goalSummary,
    constraints,
    planStatus,
    planDiff,
    messages,
    activeInterruption,
    sportsFixtures,
    sendUserInput,
    uploadImage,
    sendSpeechStarted,
    resetSession,
    switchSession,
    isSpeaking,
    isMuted,
    toggleMute,
    cancelSpeech,
    isTtsSupported,
  } = useNexusWebSocket();

  // Keep history updated when live messages, sports fixtures, or tasks change
  useEffect(() => {
    if (!sessionId || !user) return;
    if (messages.length > 0 || sportsFixtures || goalSummary) {
      updateSession(sessionId, {
        messages,
        sportsFixtures,
        goalSummary,
        tasks,
      });
    }
  }, [sessionId, user, messages, sportsFixtures, goalSummary, tasks, updateSession]);

  // Handle successful login or account registration
  const handleAuthSuccess = useCallback(
    async (authedUser: AuthUser, isNew: boolean) => {
      setUser(authedUser);
      try {
        localStorage.setItem("suru_auth_user", JSON.stringify(authedUser));
      } catch (err) {}
      setIsAuthModalOpen(false);

      if (isNew) {
        // Create personalized opening greeting for the new user as requested
        const greetings = [
          `Hey ${authedUser.display_name}! Great to meet you. What's on your mind today?`,
          `Hey ${authedUser.display_name}, what's up? I'm SURU, your real-time AI assistant. How can I help you today?`,
          `Welcome ${authedUser.display_name}! What are we working on or exploring today?`,
        ];
        const greetingText = greetings[Math.floor(Math.random() * greetings.length)];
        const initialMsg: TranscriptMessage = {
          id: `welcome-${Date.now()}`,
          role: "assistant",
          content: greetingText,
          timestamp: new Date().toISOString(),
        };

        const freshSession = createNewSession(undefined, [initialMsg]);
        await resetSession(freshSession.id);
        switchSession(freshSession.id, [initialMsg], null, "", []);
      }
    },
    [createNewSession, resetSession, switchSession]
  );

  // Handle Logout
  const handleLogout = useCallback(() => {
    try {
      localStorage.removeItem("suru_auth_user");
    } catch (err) {}
    setUser(null);
    setIsAuthModalOpen(true);
  }, []);

  // Handle "+ New Chat"
  const handleNewChat = useCallback(async () => {
    const freshSession = createNewSession();
    await resetSession(freshSession.id);
  }, [createNewSession, resetSession]);

  // Handle selecting a past conversation from the History sidebar
  const handleSelectSession = useCallback(
    (selected: StoredChatSession) => {
      selectSession(selected.id);
      switchSession(
        selected.id,
        selected.messages || [],
        selected.sportsFixtures || null,
        selected.goalSummary || "",
        selected.tasks || []
      );
    },
    [selectSession, switchSession]
  );

  // Quick suggestion click from empty state
  const handleSuggestionClick = useCallback(
    (promptText: string) => {
      sendUserInput(promptText);
    },
    [sendUserInput]
  );

  return (
    <div className="h-screen w-screen aurora-backdrop text-slate-100 flex flex-col font-sans overflow-hidden selection:bg-emerald-500/30 selection:text-emerald-200 relative">
      {/* Realistic Organic Aurora Light Streams (Upper-Left, Upper-Right, Center Arch, Bottom Drift) */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        {/* Primary Green Aurora Plume - Upper Left */}
        <div className="aurora-layer-1 absolute -top-[12%] -left-[6%] w-[720px] h-[720px] rounded-full bg-gradient-to-br from-emerald-500/22 via-emerald-600/14 to-transparent blur-[120px]" />
        
        {/* Secondary Jade/Teal Aurora Plume - Upper Right */}
        <div className="aurora-layer-2 absolute -top-[8%] -right-[6%] w-[680px] h-[680px] rounded-full bg-gradient-to-bl from-teal-500/18 via-emerald-600/12 to-transparent blur-[130px]" />

        {/* Soft Central Celestial Arch */}
        <div className="aurora-layer-3 absolute -top-[20%] left-[28%] w-[750px] h-[500px] rounded-full bg-gradient-to-b from-emerald-400/14 via-green-600/8 to-transparent blur-[140px]" />

        {/* Bottom subtle ambient grounding glow */}
        <div className="aurora-layer-2 absolute -bottom-[15%] left-[25%] w-[850px] h-[450px] rounded-full bg-gradient-to-t from-emerald-800/16 via-emerald-950/8 to-transparent blur-[150px]" />
      </div>

      {/* If user is not authenticated, show ONLY the dedicated Auth Screen */}
      {!user ? (
        <AuthModal
          isOpen={true}
          onSuccess={handleAuthSuccess}
        />
      ) : (
        /* Full AI Chat Application (rendered only after logging in) */
        <>
          <div className="flex-1 flex flex-col p-3 md:p-5 max-w-[1720px] w-full mx-auto h-full min-h-0 relative z-0">
            {/* Top Header Pill Bar */}
            <Header
              connected={connected}
              sessionId={sessionId}
              onReset={handleNewChat}
              isSpeaking={isSpeaking}
              cancelSpeech={cancelSpeech}
              user={user}
              onLogout={handleLogout}
              onOpenLogin={() => {}}
            />

            {/* Main Work Area */}
            <div className="flex-1 flex gap-4 min-h-0 overflow-hidden">
              {/* Column 1: Far Left Nav Rail */}
              <NavRail onOpenModal={setModalTab} activeModalTab={modalTab} />

              {/* Column 2: Central Chat Assistant */}
              <main className="flex-1 flex flex-col min-w-0 h-full min-h-0">
                <div className="flex-1 flex flex-col gap-3 h-full min-h-0">
                  {/* Central Chat Transcript */}
                  <div className="flex-1 min-h-0">
                    <Transcript
                      messages={messages}
                      latestSportsFixtures={sportsFixtures}
                      onSuggestionClick={handleSuggestionClick}
                      onSpeakMessage={(text) => {
                        // Optional inline speech trigger
                      }}
                    />
                  </div>

                  {/* Bottom Modern Composer */}
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
              </main>

              {/* Column 3: Right Chat History Sidebar */}
              <div className="w-72 xl:w-80 shrink-0 h-full hidden lg:block">
                <ChatHistorySidebar
                  sessions={sessions}
                  activeSessionId={activeSessionId || sessionId}
                  onSelectSession={handleSelectSession}
                  onNewChat={handleNewChat}
                  onDeleteSession={deleteSession}
                />
              </div>
            </div>
          </div>

          {/* Interactive Consumer Modal / Drawer (Option 1) */}
          <NavDrawerModal
            isOpen={modalTab !== null}
            activeTab={modalTab}
            onClose={() => setModalTab(null)}
            onSelectPrompt={handleSuggestionClick}
            onClearChat={handleNewChat}
            messages={messages}
            connected={connected}
            sessionId={sessionId}
            user={user}
            onLogout={handleLogout}
          />
        </>
      )}
    </div>
  );
}
