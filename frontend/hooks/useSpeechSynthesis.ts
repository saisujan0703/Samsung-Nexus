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
        // Strip markdown formatting symbols for natural speech output
        const cleanedText = text
          .replace(/[\*\_\`\#]/g, "")
          .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1") // strip links
          .trim();

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
