"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export function useSpeechSynthesis() {
  const [isSupported, setIsSupported] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<SpeechSynthesisVoice | null>(null);

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Load browser voices on mount
  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setIsSupported(true);

      const updateVoices = () => {
        try {
          const available = window.speechSynthesis.getVoices();
          setVoices(available);

          if (available.length > 0) {
            const englishVoices = available.filter((v) => v.lang.startsWith("en"));
            const preferred =
              englishVoices.find(
                (v) =>
                  v.name.includes("Google") ||
                  v.name.includes("Natural") ||
                  v.name.includes("Samantha") ||
                  v.name.includes("Daniel") ||
                  v.name.includes("Microsoft")
              ) ||
              englishVoices[0] ||
              available[0];

            setSelectedVoice(preferred);
          }
        } catch (e) {
          console.warn("[TTS] Error fetching voices:", e);
        }
      };

      updateVoices();

      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = updateVoices;
      }
    } else {
      setIsSupported(false);
    }
  }, []);

  const cancel = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (err) {
        console.warn("[TTS] Cancel error:", err);
      }
    }
    setIsSpeaking(false);
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
      if (!text || !text.trim() || isMuted) return;

      // Cancel any ongoing speech before starting a new utterance
      cancel();

      try {
        // Strip markdown formatting, tables, raw JSON, URLs, and slashes for natural speech output
        let cleaned = text;

        // 1. Remove raw JSON blocks if present
        if (cleaned.trim().startsWith("{") && cleaned.trim().endsWith("}")) {
          try {
            const parsed = JSON.parse(cleaned.trim());
            cleaned = parsed.spoken_summary || parsed.summary || parsed.text || parsed.message || "";
          } catch {
            cleaned = cleaned.replace(/\{[\s\S]*?\}/g, " ");
          }
        }

        // 2. Remove code blocks
        cleaned = cleaned.replace(/```[\s\S]*?```/g, " ");

        // 3. Remove markdown tables (lines starting and ending with | or containing multiple |)
        cleaned = cleaned.replace(/^\s*\|.*?\|\s*$/gm, " ");
        cleaned = cleaned.replace(/\|/g, ", ");

        // 4. Remove SVG tags and raw HTML/XML elements (<svg>...</svg>, etc.)
        cleaned = cleaned.replace(/<svg[\s\S]*?<\/svg>/gi, " ");
        cleaned = cleaned.replace(/<[^>]+>/g, " ");

        // 5. Remove image tags: ![alt](url)
        cleaned = cleaned.replace(/!\[[^\]]*\]\([^\)]+\)/g, " ");

        // 5. Replace markdown links [text](url) with just text
        cleaned = cleaned.replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1");

        // 6. Remove raw URLs
        cleaned = cleaned.replace(/https?:\/\/\S+/g, " ");

        // 7. Remove headers (#, ##, etc.)
        cleaned = cleaned.replace(/^#+\s+/gm, " ");

        // 8. Remove blockquotes (>)
        cleaned = cleaned.replace(/^>\s+/gm, " ");

        // 9. Remove horizontal rules
        cleaned = cleaned.replace(/^[-*_]{3,}\s*$/gm, " ");

        // 10. Remove bullet points and numbered list markers
        cleaned = cleaned.replace(/^\s*[-*+]\s+/gm, " ");
        cleaned = cleaned.replace(/^\s*\d+\.\s+/gm, " ");

        // 11. Remove bold, italic, strikethrough, inline code
        cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, "$1");
        cleaned = cleaned.replace(/\*([^*]+)\*/g, "$1");
        cleaned = cleaned.replace(/__([^_]+)__/g, "$1");
        cleaned = cleaned.replace(/_([^_]+)_/g, "$1");
        cleaned = cleaned.replace(/~~([^~]+)~~/g, "$1");
        cleaned = cleaned.replace(/`([^`]+)`/g, "$1");

        // 12. Handle slashes intelligently so TTS never speaks 'slash':
        // Timezones like Asia/Kolkata -> Asia Kolkata, and/or -> and or, Kickoff / Score -> Kickoff, Score
        cleaned = cleaned.replace(/([a-zA-Z0-9]+)\/([a-zA-Z0-9]+)/g, "$1 $2");
        cleaned = cleaned.replace(/\s*\/\s*/g, ", ");

        // 13. Remove remaining machine symbols like backslashes, braces, brackets, raw UUIDs
        cleaned = cleaned.replace(/[\\{}\[\]^~]/g, " ");
        cleaned = cleaned.replace(/\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g, " ");
        cleaned = cleaned.replace(/\b(?:task|session|event|match)_[a-zA-Z0-9_\-]+\b/g, " ");

        // 14. Clean up parentheses around words or times: (Asia Kolkata) -> Asia Kolkata
        cleaned = cleaned.replace(/\(([^)]+)\)/g, " $1 ");

        // 15. Normalize whitespace and punctuation
        cleaned = cleaned.replace(/[\r\n]+/g, " ");
        cleaned = cleaned.replace(/\s{2,}/g, " ");
        cleaned = cleaned.replace(/\s+,/g, ",");
        cleaned = cleaned.replace(/,{2,}/g, ",");
        cleaned = cleaned.replace(/\s+\./g, ".");
        const cleanedText = cleaned.trim();

        if (!cleanedText) return;


        const utterance = new SpeechSynthesisUtterance(cleanedText);
        utteranceRef.current = utterance;

        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }

        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
          setIsSpeaking(true);
        };

        utterance.onend = () => {
          setIsSpeaking(false);
          utteranceRef.current = null;
        };

        utterance.onerror = (event) => {
          if (event.error !== "interrupted" && event.error !== "canceled") {
            console.warn("[TTS] Utterance error:", event.error);
          }
          setIsSpeaking(false);
          utteranceRef.current = null;
        };

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.error("[TTS] Speech synthesis failed:", err);
        setIsSpeaking(false);
      }
    },
    [cancel, isMuted, selectedVoice]
  );

  const pause = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.pause();
      } catch (e) {
        // ignore
      }
    }
  }, []);

  const resume = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.resume();
      } catch (e) {
        // ignore
      }
    }
  }, []);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      if (next) cancel();
      return next;
    });
  }, [cancel]);

  // Clean up speech synthesis on component unmount
  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return {
    isSupported,
    isSpeaking,
    isMuted,
    voices,
    selectedVoice,
    setSelectedVoice,
    speak,
    cancel,
    pause,
    resume,
    toggleMute,
  };
}
