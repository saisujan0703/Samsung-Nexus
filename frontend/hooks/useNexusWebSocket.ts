"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  AgentState,
  NexusEvent,
  PlanDiff,
  SessionSnapshot,
  Task,
  TranscriptMessage,
} from "../lib/types";
import { useSpeechSynthesis } from "./useSpeechSynthesis";

const BACKEND_HTTP = process.env.NEXT_PUBLIC_BACKEND_HTTP || "http://localhost:8000";
const BACKEND_WS = process.env.NEXT_PUBLIC_BACKEND_WS || "ws://localhost:8000";

export function useNexusWebSocket() {
  const {
    isSupported: isTtsSupported,
    isSpeaking,
    isMuted,
    speak,
    cancel: cancelSpeech,
    toggleMute,
  } = useSpeechSynthesis();
  const [sessionId, setSessionId] = useState<string>("");
  const [connected, setConnected] = useState<boolean>(false);
  const [agentState, setAgentState] = useState<AgentState>("IDLE");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [goalSummary, setGoalSummary] = useState<string>("");
  const [constraints, setConstraints] = useState<Record<string, any>>({});
  const [planDiff, setPlanDiff] = useState<PlanDiff | null>(null);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [events, setEvents] = useState<NexusEvent[]>([]);
  const [activeInterruption, setActiveInterruption] = useState<{
    type: string;
    confidence: number;
    text: string;
    timestamp: string;
  } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize or fetch session
  const initSession = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_HTTP}/api/session`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        return data.session_id;
      }
    } catch (err) {
      console.warn("Failed to create session via REST, using generated ID:", err);
    }
    const fallbackId = Math.random().toString(36).substring(2, 10);
    setSessionId(fallbackId);
    return fallbackId;
  }, []);

  // Connect WebSocket
  useEffect(() => {
    let active = true;

    async function setup() {
      const id = await initSession();
      if (!active) return;

      const wsUrl = `${BACKEND_WS}/ws/${id}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!active) return;
        setConnected(true);
        console.log(`[NEXUS] WebSocket connected to session: ${id}`);
      };

      ws.onmessage = (event) => {
        if (!active) return;
        try {
          const raw = JSON.parse(event.data);
          handleWebSocketMessage(raw);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      ws.onclose = () => {
        if (!active) return;
        setConnected(false);
        console.log("[NEXUS] WebSocket disconnected, reconnecting in 2s...");
        reconnectTimeoutRef.current = setTimeout(setup, 2000);
      };

      ws.onerror = (err) => {
        console.warn("[NEXUS] WebSocket error:", err);
      };
    }

    setup();

    return () => {
      active = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [initSession]);

  // Handler for typed events
  const handleWebSocketMessage = (msg: any) => {
    const msgType = msg.type || msg.event_type;

    // Initial snapshot on connection
    if (msgType === "initial_state" && msg.payload) {
      const p: SessionSnapshot = msg.payload;
      setAgentState(p.state || "IDLE");
      if (p.task_graph?.tasks) setTasks(p.task_graph.tasks);
      if (p.goal?.current_goal?.summary) setGoalSummary(p.goal.current_goal.summary);
      if (p.goal?.current_goal?.constraints) setConstraints(p.goal.current_goal.constraints);
      return;
    }

    // Append to Event Timeline
    const nexusEvent: NexusEvent = {
      type: msgType,
      event_type: msg.event_type || msgType,
      timestamp: msg.timestamp || new Date().toISOString(),
      session_id: msg.session_id || "",
      data: msg.data || {},
    };
    setEvents((prev) => [nexusEvent, ...prev.slice(0, 150)]);

    // Handle specific event kinds
    switch (msgType) {
      case "agent_state_changed":
        if (msg.data?.state) {
          setAgentState(msg.data.state);
        }
        break;

      case "user_text_input":
        if (msg.data?.text) {
          setMessages((prev) => [
            ...prev,
            {
              id: Math.random().toString(),
              role: "user",
              content: msg.data.text,
              timestamp: msg.timestamp || new Date().toISOString(),
            },
          ]);
        }
        break;

      case "interruption_detected":
        setActiveInterruption({
          type: "DETECTED",
          confidence: 1.0,
          text: msg.data?.text || "",
          timestamp: msg.timestamp || new Date().toISOString(),
        });
        break;

      case "interruption_classified":
        setActiveInterruption({
          type: msg.data?.type || "CONSTRAINT_CHANGE",
          confidence: msg.data?.confidence || 0.9,
          text: msg.data?.text || "",
          timestamp: msg.timestamp || new Date().toISOString(),
        });
        // Tag last user message with classification
        setMessages((prev) => {
          if (!prev.length) return prev;
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "user") {
            last.isInterruption = true;
            last.category = msg.data?.type;
          }
          return updated;
        });
        break;

      case "plan_created":
        if (msg.data?.tasks) {
          setTasks(
            msg.data.tasks.map((t: any) => ({
              ...t,
              status: "PENDING",
            }))
          );
        }
        if (msg.data?.goal) {
          setGoalSummary(msg.data.goal);
        }
        break;

      case "plan_diff_computed":
        if (msg.data?.diff) {
          setPlanDiff(msg.data.diff);
        }
        break;

      case "plan_updated":
        // Sync tasks based on plan update
        setPlanDiff((prev) => prev); // keep active diff visible
        break;

      case "task_started":
        setTasks((prev) =>
          prev.map((t) => (t.id === msg.data?.task_id ? { ...t, status: "RUNNING" } : t))
        );
        break;

      case "task_completed":
        setTasks((prev) =>
          prev.map((t) =>
            t.id === msg.data?.task_id
              ? { ...t, status: "COMPLETED", output: { summary: msg.data?.output_summary } }
              : t
          )
        );
        break;

      case "task_cancelled":
        setTasks((prev) =>
          prev.map((t) =>
            t.id === msg.data?.task_id
              ? { ...t, status: "CANCELLED", cancellation_reason: msg.data?.reason }
              : t
          )
        );
        break;

      case "goal_set":
      case "goal_changed":
        if (msg.data?.new_summary || msg.data?.summary) {
          setGoalSummary(msg.data.new_summary || msg.data.summary);
        }
        if (msg.data?.new_constraints || msg.data?.constraints) {
          setConstraints(msg.data.new_constraints || msg.data.constraints);
        }
        break;

      case "response_started":
        setMessages((prev) => [
          ...prev,
          {
            id: Math.random().toString(),
            role: "assistant",
            content: "",
            timestamp: msg.timestamp || new Date().toISOString(),
          },
        ]);
        break;

      case "response_chunk":
        setMessages((prev) => {
          if (!prev.length) return prev;
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            last.content = msg.data?.text || last.content + (msg.data?.chunk || "");
          }
          return updated;
        });
        break;

      case "response_completed":
        if (msg.data?.text) {
          const finalResponseText = msg.data.text;
          setMessages((prev) => {
            if (!prev.length) return prev;
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              last.content = finalResponseText;
            }
            return updated;
          });
          speak(finalResponseText);
        }
        break;
    }
  };

  // Send text to backend
  const sendUserInput = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      // Immediately silence any active TTS speech when user sends input
      cancelSpeech();

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "user_input", text }));
      } else {
        // Fallback to REST
        fetch(`${BACKEND_HTTP}/api/session/${sessionId}/input`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        }).catch(console.error);
      }
    },
    [cancelSpeech, sessionId]
  );

  // Restart session
  const resetSession = useCallback(async () => {
    cancelSpeech();
    setMessages([]);
    setTasks([]);
    setPlanDiff(null);
    setEvents([]);
    setActiveInterruption(null);
    setGoalSummary("");
    setConstraints({});
    await initSession();
  }, [cancelSpeech, initSession]);

  return {
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
    resetSession,
    // TTS Voice Output properties
    isSpeaking,
    isMuted,
    toggleMute,
    cancelSpeech,
    isTtsSupported,
  };
}
