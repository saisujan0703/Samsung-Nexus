"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Send, Zap, Mic, MicOff, Loader2, AlertCircle, X, Image as ImageIcon } from "lucide-react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface InputAreaProps {
  onSend: (text: string) => void;
  onUploadImage?: (imageData: string, prompt: string) => Promise<void> | void;
  disabled?: boolean;
  onCancelSpeech?: () => void;
  onSpeechStart?: () => void;
}

const DEMO_PROMPTS = [
  { label: "1. Initial Trip Goal", text: "Plan a 3-day Chennai trip for 15000 rupees." },
  { label: "2. Interrupt (Parents & Walking)", text: "Wait. I am travelling with my parents. Avoid places requiring lots of walking." },
  { label: "3. Interrupt (Budget)", text: "Actually increase the budget to 20000." },
  { label: "4. Interrupt (New Goal)", text: "Forget the trip. Help me prepare for an interview instead." },
];

export function InputArea({ onSend, onUploadImage, disabled, onCancelSpeech, onSpeechStart }: InputAreaProps) {
  const [text, setText] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [imageFileName, setImageFileName] = useState<string>("");
  const [imageValidationError, setImageValidationError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lastSubmittedRef = useRef<{ text: string; time: number }>({ text: "", time: 0 });

  const handleFinalTranscript = useCallback(
    (spokenText: string) => {
      const trimmed = spokenText.trim();
      if (!trimmed || disabled) return;

      const now = Date.now();
      if (lastSubmittedRef.current.text === trimmed && now - lastSubmittedRef.current.time < 800) {
        return;
      }
      lastSubmittedRef.current = { text: trimmed, time: now };

      setText(trimmed);
      if (selectedImage && onUploadImage) {
        onUploadImage(selectedImage, trimmed);
        setSelectedImage(null);
        setImageFileName("");
      } else {
        onSend(trimmed);
      }
      setTimeout(() => setText(""), 400);
    },
    [disabled, onSend, onUploadImage, selectedImage]
  );

  const handleSpeechStart = useCallback(() => {
    onCancelSpeech?.();
    onSpeechStart?.();
  }, [onCancelSpeech, onSpeechStart]);

  const {
    isSupported,
    status,
    interimTranscript,
    error,
    startListening,
    stopListening,
    reset,
  } = useSpeechRecognition({
    onFinalTranscript: handleFinalTranscript,
    onSpeechStart: handleSpeechStart,
  });

  useEffect(() => {
    if (status === "listening" && interimTranscript) {
      setText(interimTranscript);
    }
  }, [status, interimTranscript]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImageValidationError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setImageValidationError("Selected file is not an image (PNG, JPEG, WebP, GIF only).");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setImageValidationError("Image size exceeds 10MB limit.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setSelectedImage(reader.result);
        setImageFileName(file.name);
      }
    };
    reader.readAsDataURL(file);
  };

  const removeSelectedImage = () => {
    setSelectedImage(null);
    setImageFileName("");
    setImageValidationError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!text.trim() && !selectedImage) || disabled) return;

    if (selectedImage && onUploadImage) {
      setIsUploading(true);
      try {
        await onUploadImage(selectedImage, text);
      } finally {
        setIsUploading(false);
      }
      setSelectedImage(null);
      setImageFileName("");
      setText("");
    } else if (text.trim()) {
      onSend(text);
      setText("");
    }
    reset();
  };

  const toggleMic = () => {
    if (!isSupported || disabled) return;
    if (status === "listening") {
      stopListening();
    } else {
      onCancelSpeech?.();
      startListening();
    }
  };

  return (
    <div className="flex flex-col gap-2.5">
      {/* Error / Unsupported Alert Banner */}
      {(error || imageValidationError) && (
        <div className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error || imageValidationError}</span>
          </div>
          <button
            type="button"
            onClick={() => {
              reset();
              setImageValidationError(null);
            }}
            className="p-1 hover:bg-rose-500/20 rounded-lg text-rose-400 hover:text-rose-200 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Selected Image Thumbnail Preview Bar */}
      {selectedImage && (
        <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-200 text-xs animate-fadeIn">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <img
              src={selectedImage}
              alt="Preview"
              className="w-8 h-8 rounded object-cover border border-purple-400/40 shrink-0"
            />
            <span className="truncate max-w-[220px] font-medium">{imageFileName}</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 uppercase font-bold shrink-0">
              Ready to Send
            </span>
          </div>
          <button
            type="button"
            onClick={removeSelectedImage}
            className="p-1 hover:bg-purple-500/20 rounded-lg text-purple-300 hover:text-white transition-colors"
            title="Remove image"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Quick Scenario Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider shrink-0 flex items-center gap-1">
          <Zap className="w-3 h-3 text-amber-400" /> Scenarios:
        </span>
        {DEMO_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSend(prompt.text)}
            className="px-3 py-1 rounded-full glass-card hover:bg-slate-700/60 text-slate-300 text-xs whitespace-nowrap transition-all border border-slate-700/70 hover:border-cyan-500/50 hover:text-white"
          >
            {prompt.label}
          </button>
        ))}
      </div>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/png,image/jpeg,image/webp,image/gif"
        className="hidden"
      />

      {/* Input Form with Image, Mic, Send Buttons */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              status === "listening"
                ? "Listening... Speak your goal or interruption now..."
                : selectedImage
                ? "Add a prompt for this image or click send..."
                : "Type a goal or interrupt the agent while it works..."
            }
            disabled={disabled || isUploading}
            className={`w-full px-4 py-3 rounded-xl bg-slate-900/80 border text-sm text-white placeholder-slate-500 focus:outline-none transition-all ${
              status === "listening"
                ? "border-rose-500/60 ring-2 ring-rose-500/30 bg-slate-900"
                : selectedImage
                ? "border-purple-500/60 ring-1 ring-purple-500/30"
                : "border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            }`}
          />
          {status === "listening" && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/20 border border-rose-500/40 text-[10px] font-semibold text-rose-300 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
              LIVE STT
            </div>
          )}
        </div>

        {/* Image Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isUploading}
          title="Attach an image for visual analysis"
          className={`px-3 py-3 rounded-xl border flex items-center justify-center transition-all ${
            selectedImage
              ? "bg-purple-500/20 border-purple-500 text-purple-300"
              : "bg-slate-800/80 hover:bg-slate-700 border-slate-700/80 text-purple-400 hover:text-purple-300"
          }`}
        >
          <ImageIcon className="w-4 h-4" />
        </button>

        {/* Microphone Button */}
        <button
          type="button"
          onClick={toggleMic}
          disabled={disabled || !isSupported || isUploading}
          title={
            !isSupported
              ? "Voice input isn't supported in this browser."
              : status === "listening"
              ? "Click to stop listening"
              : "Click to speak (Voice Input)"
          }
          className={`px-3 py-3 rounded-xl border flex items-center justify-center transition-all ${
            !isSupported
              ? "bg-slate-800/40 border-slate-800 text-slate-600 cursor-not-allowed"
              : status === "listening"
              ? "bg-rose-500/20 border-rose-500 text-rose-400 shadow-lg shadow-rose-500/20 animate-pulse"
              : status === "processing"
              ? "bg-amber-500/20 border-amber-500 text-amber-300"
              : "bg-slate-800/80 hover:bg-slate-700 border-slate-700/80 text-cyan-400 hover:text-cyan-300"
          }`}
        >
          {!isSupported ? (
            <MicOff className="w-4 h-4" />
          ) : status === "listening" ? (
            <Mic className="w-4 h-4 animate-bounce" />
          ) : status === "processing" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Mic className="w-4 h-4" />
          )}
        </button>

        {/* Send Button */}
        <button
          type="submit"
          disabled={(!text.trim() && !selectedImage) || disabled || isUploading}
          className="px-4 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all shrink-0"
        >
          {isUploading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
