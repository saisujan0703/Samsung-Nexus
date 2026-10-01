"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export type SpeechRecognitionStatus =
  | "idle"
  | "listening"
  | "processing"
  | "unsupported"
  | "error";

interface UseSpeechRecognitionOptions {
  onFinalTranscript?: (transcript: string) => void;
  onSpeechStart?: () => void;
  lang?: string;
}

export function useSpeechRecognition({
  onFinalTranscript,
  onSpeechStart,
  lang = "en-US",
}: UseSpeechRecognitionOptions = {}) {
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const [status, setStatus] = useState<SpeechRecognitionStatus>("idle");
  const [interimTranscript, setInterimTranscript] = useState<string>("");
  const [finalTranscript, setFinalTranscript] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setIsSupported(false);
        setStatus("unsupported");
      } else {
        setIsSupported(true);
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.warn("Speech recognition stop error:", err);
      }
    }
  }, []);

  const startListening = useCallback(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      setStatus("unsupported");
      setError("Voice input isn't supported in this browser. Try Chrome or another supported browser.");
      return;
    }

    // Abort active session if any to avoid duplicate listener conflicts
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {
        // ignore
      }
    }

    setError(null);
    setInterimTranscript("");
    setFinalTranscript("");

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        setStatus("listening");
        if (onSpeechStart) {
          onSpeechStart();
        }
      };

      recognition.onresult = (event: any) => {
        let currentInterim = "";
        let currentFinal = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i];
          if (res.isFinal) {
            currentFinal += res[0].transcript;
          } else {
            currentInterim += res[0].transcript;
          }
        }

        if (currentInterim) {
          setInterimTranscript(currentInterim);
        }

        if (currentFinal) {
          const trimmedFinal = currentFinal.trim();
          setFinalTranscript(trimmedFinal);
          setInterimTranscript("");
          setStatus("processing");
          if (onFinalTranscript && trimmedFinal) {
            onFinalTranscript(trimmedFinal);
          }
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("[SpeechRecognition Error]", event.error);
        let errorMsg = "Speech recognition error.";
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          errorMsg = "Microphone permission denied. Please allow microphone access in your browser settings.";
        } else if (event.error === "no-speech") {
          errorMsg = "No speech detected. Please try speaking again.";
        } else if (event.error === "audio-capture") {
          errorMsg = "No microphone found. Please connect a microphone and try again.";
        } else if (event.error === "network") {
          errorMsg = "Network error occurred during speech recognition.";
        }
        setError(errorMsg);
        setStatus("error");
      };

      recognition.onend = () => {
        setStatus((prev) => (prev === "listening" || prev === "processing" ? "idle" : prev));
        recognitionRef.current = null;
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      console.error("Failed to start speech recognition:", err);
      setError(err?.message || "Failed to start speech recognition.");
      setStatus("error");
    }
  }, [lang, onFinalTranscript]);

  const reset = useCallback(() => {
    stopListening();
    setStatus("idle");
    setInterimTranscript("");
    setFinalTranscript("");
    setError(null);
  }, [stopListening]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // ignore
        }
      }
    };
  }, []);

  return {
    isSupported,
    status,
    interimTranscript,
    finalTranscript,
    error,
    startListening,
    stopListening,
    reset,
  };
}
