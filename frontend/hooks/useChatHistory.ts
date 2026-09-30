"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { StoredChatSession, TranscriptMessage, SportsFixturesPayload, Task, AuthUser } from "../lib/types";

/**
 * Generic title generator from user's first prompt.
 */
export function generateChatTitle(firstMessage: string): string {
  let clean = firstMessage.trim();
  clean = clean.replace(
    /^(?:please\s+)?(?:could\s+you\s+|can\s+you\s+|would\s+you\s+)?(?:tell\s+me\s+about|tell\s+me|show\s+me|give\s+me|find|explain|what\s+is|what\s+are|how\s+to|how\s+do\s+i|who\s+is|search\s+for|look\s+up)\s+/i,
    ""
  );
  clean = clean.replace(/^(?:the\s+|a\s+|an\s+)/i, "");
  clean = clean.replace(/[?.!,:;]+$/, "").trim();

  if (!clean) return "New Conversation";

  const words = clean.split(/\s+/).slice(0, 5);
  const title = words
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");

  return title.length > 36 ? title.substring(0, 36) + "..." : title;
}

export function useChatHistory(user: AuthUser | null) {
  const [sessions, setSessions] = useState<StoredChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const isLoadedRef = useRef(false);
  const userRef = useRef<AuthUser | null>(user);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  // Load from backend DB whenever user logs in or changes
  useEffect(() => {
    if (!user) {
      setSessions([]);
      setActiveSessionId("");
      isLoadedRef.current = true;
      return;
    }

    const storageKey = `suru_chat_user_${user.id}`;
    let loadedFromCache = false;

    // Load from local cache first for instant feedback
    try {
      const cached = localStorage.getItem(storageKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSessions(parsed);
          setActiveSessionId(parsed[0].id);
          loadedFromCache = true;
        }
      }
    } catch (e) {
      console.warn("Failed to load local chat cache:", e);
    }

    // Fetch authoritative sessions from backend SQLite database
    const fetchUserChats = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/user/${user.id}/chats`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "ok" && Array.isArray(data.chats)) {
            setSessions(data.chats);
            if (data.chats.length > 0) {
              setActiveSessionId(data.chats[0].id);
            } else if (!loadedFromCache) {
              setActiveSessionId("");
            }
            try {
              localStorage.setItem(storageKey, JSON.stringify(data.chats));
            } catch (err) {}
          }
        }
      } catch (err) {
        console.warn("Could not fetch remote user chats:", err);
      } finally {
        isLoadedRef.current = true;
      }
    };

    fetchUserChats();
  }, [user]);

  // Persist sessions to local cache & backend DB
  const persistSessions = useCallback((updatedSessions: StoredChatSession[]) => {
    const currentUser = userRef.current;
    if (!currentUser) return;

    const storageKey = `suru_chat_user_${currentUser.id}`;
    try {
      localStorage.setItem(storageKey, JSON.stringify(updatedSessions));
    } catch (e) {
      console.warn("Failed to persist local cache:", e);
    }
  }, []);

  // Save single session to backend database
  const saveSessionToDb = useCallback(async (session: StoredChatSession) => {
    const currentUser = userRef.current;
    if (!currentUser) return;

    try {
      await fetch(`http://127.0.0.1:8000/api/user/${currentUser.id}/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: session.id,
          title: session.title,
          messages: session.messages,
          sports_fixtures: session.sportsFixtures,
          goal_summary: session.goalSummary || "",
        }),
      });
    } catch (e) {
      console.warn("Failed to sync chat to backend database:", e);
    }
  }, []);

  // Create a genuinely new session
  const createNewSession = useCallback(
    (customId?: string, initialMessages?: TranscriptMessage[]): StoredChatSession => {
      const id = customId || Math.random().toString(36).substring(2, 10);
      const newSession: StoredChatSession = {
        id,
        title: "New Chat",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: initialMessages || [],
        sportsFixtures: null,
        goalSummary: "",
        tasks: [],
      };

      setSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== id);
        const updated = [newSession, ...filtered];
        persistSessions(updated);
        return updated;
      });

      setActiveSessionId(id);

      if (userRef.current) {
        saveSessionToDb(newSession);
      }

      return newSession;
    },
    [persistSessions, saveSessionToDb]
  );

  // Save / sync active session messages
  const updateSession = useCallback(
    (
      sessionId: string,
      updates: {
        messages?: TranscriptMessage[];
        sportsFixtures?: SportsFixturesPayload | null;
        goalSummary?: string;
        tasks?: Task[];
      }
    ) => {
      if (!sessionId) return;

      setSessions((prev) => {
        const existingIndex = prev.findIndex((s) => s.id === sessionId);
        const existing = existingIndex >= 0 ? prev[existingIndex] : null;

        const messages = updates.messages ?? existing?.messages ?? [];
        let title = existing?.title || "New Chat";

        // Auto-generate title from the first user message if default
        if (title === "New Chat" && messages.length > 0) {
          const firstUserMsg = messages.find((m) => m.role === "user");
          if (firstUserMsg && firstUserMsg.content) {
            title = generateChatTitle(firstUserMsg.content);
          }
        }

        const updatedSession: StoredChatSession = {
          id: sessionId,
          title,
          createdAt: existing?.createdAt || Date.now(),
          updatedAt: Date.now(),
          messages,
          sportsFixtures:
            updates.sportsFixtures !== undefined
              ? updates.sportsFixtures
              : existing?.sportsFixtures ?? null,
          goalSummary:
            updates.goalSummary !== undefined
              ? updates.goalSummary
              : existing?.goalSummary ?? "",
          tasks: updates.tasks !== undefined ? updates.tasks : existing?.tasks ?? [],
        };

        const updatedList =
          existingIndex >= 0
            ? prev.map((s, idx) => (idx === existingIndex ? updatedSession : s))
            : [updatedSession, ...prev];

        // Keep sorted by updatedAt descending
        const sorted = [...updatedList].sort((a, b) => b.updatedAt - a.updatedAt);
        persistSessions(sorted);

        // Async sync to backend SQLite database
        saveSessionToDb(updatedSession);

        return sorted;
      });
    },
    [persistSessions, saveSessionToDb]
  );

  // Delete a session
  const deleteSession = useCallback(
    (sessionId: string) => {
      const currentUser = userRef.current;
      if (currentUser) {
        fetch(`http://127.0.0.1:8000/api/user/${currentUser.id}/chats/${sessionId}`, {
          method: "DELETE",
        }).catch((err) => console.warn("Failed to delete chat in backend:", err));
      }

      setSessions((prev) => {
        const updated = prev.filter((s) => s.id !== sessionId);
        persistSessions(updated);

        // If active session was deleted, select next or create new
        if (activeSessionId === sessionId) {
          if (updated.length > 0) {
            setActiveSessionId(updated[0].id);
          } else {
            setActiveSessionId("");
          }
        }
        return updated;
      });
    },
    [activeSessionId, persistSessions]
  );

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return {
    sessions,
    activeSessionId,
    activeSession,
    createNewSession,
    updateSession,
    selectSession: setActiveSessionId,
    deleteSession,
    isLoaded: isLoadedRef.current,
  };
}
