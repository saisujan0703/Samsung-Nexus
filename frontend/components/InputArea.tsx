"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Send, Mic, MicOff, Loader2, AlertCircle, X, Plus, Paperclip } from "lucide-react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface InputAreaProps {
  onSend: (text: string) => void;
  onUploadImage?: (imageData: string, prompt: string) => Promise<void> | void;
  disabled?: boolean;
  onCancelSpeech?: () => void;
  onSpeechStart?: () => void;
}

export function InputArea({
  onSend,
  onUploadImage,
  disabled,
  onCancelSpeech,
  onSpeechStart,
}: InputAreaProps) {
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
    <div className="flex flex-col gap-2 w-full">
      {/* Error or validation message banner */}
      {(error || imageValidationError) && (
        <div className="flex items-center justify-between px-4 py-2 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-medium">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <span>{error || imageValidationError}</span>
          </div>
          <button
            type="button"
            onClick={() => {
              reset();
              setImageValidationError(null);
            }}
            className="p-1 hover:bg-rose-500/20 rounded-md text-rose-400"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Selected Image Thumbnail Preview */}
      {selectedImage && (
        <div className="flex items-center justify-between px-3.5 py-1.5 rounded-2xl bg-[#14231b] border border-emerald-500/30 text-emerald-200 text-xs shadow-sm">
          <div className="flex items-center gap-2 overflow-hidden">
            <img
              src={selectedImage}
              alt="Thumbnail"
              className="w-7 h-7 rounded-lg object-cover border border-emerald-400/40 shrink-0"
            />
            <span className="truncate max-w-[200px] text-xs font-medium">{imageFileName}</span>
          </div>
          <button
            type="button"
            onClick={removeSelectedImage}
            className="p-1 hover:bg-emerald-500/20 rounded-md text-emerald-300 hover:text-white transition-colors"
            title="Remove image"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/png,image/jpeg,image/webp,image/gif"
        className="hidden"
      />

      {/* Modern AI Composer (matches reference image) */}
      <form
        onSubmit={handleSubmit}
        className={`flex items-center gap-2 px-3 py-2 rounded-2xl border bg-[#0a0f0c]/95 backdrop-blur-xl transition-all shadow-md ${
          status === "listening"
            ? "border-emerald-500/70 ring-1 ring-emerald-500/40"
            : "border-emerald-900/30 focus-within:border-emerald-500/50"
        }`}
      >
        {/* Left Attachment Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            title="Attach image"
            className="p-2 rounded-xl text-slate-400 hover:text-emerald-300 hover:bg-white/5 transition-all"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            title="Attach file"
            className="p-2 rounded-xl text-slate-400 hover:text-emerald-300 hover:bg-white/5 transition-all"
          >
            <Paperclip className="w-4 h-4" />
          </button>
        </div>

        {/* Center Input Field */}
        <div className="flex-1 relative flex items-center">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              status === "listening"
                ? "Listening... Speak your request now..."
                : selectedImage
                ? "Add a prompt for this image..."
                : "Ask a question or make a request..."
            }
            disabled={disabled || isUploading}
            className="w-full bg-transparent px-2 py-1.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
          />

          {status === "listening" && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-[10px] font-semibold text-emerald-300 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Listening
            </div>
          )}
        </div>

        {/* Right Action Icons: Microphone & Vibrant Send */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Microphone */}
          <button
            type="button"
            onClick={toggleMic}
            disabled={disabled || !isSupported || isUploading}
            title={
              !isSupported
                ? "Voice input not supported in this browser"
                : status === "listening"
                ? "Stop listening"
                : "Voice input"
            }
            className={`p-2 rounded-xl transition-all ${
              !isSupported
                ? "text-slate-600 cursor-not-allowed"
                : status === "listening"
                ? "bg-emerald-500/20 text-emerald-300 animate-pulse"
                : status === "processing"
                ? "text-emerald-400"
                : "text-slate-400 hover:text-emerald-300 hover:bg-white/5"
            }`}
          >
            {!isSupported ? (
              <MicOff className="w-4 h-4" />
            ) : status === "listening" ? (
              <Mic className="w-4 h-4 text-emerald-400 animate-bounce" />
            ) : status === "processing" ? (
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>

          {/* Vibrant Green Circular Send Button (matches reference image) */}
          <button
            type="submit"
            disabled={(!text.trim() && !selectedImage) || disabled || isUploading}
            title="Send request"
            className="w-9 h-9 rounded-full bg-[#34d399] hover:bg-[#22c55e] disabled:opacity-40 disabled:hover:bg-[#34d399] disabled:cursor-not-allowed text-slate-950 flex items-center justify-center transition-all shadow-[0_0_15px_rgba(52,211,153,0.35)] active:scale-95 shrink-0"
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
            ) : (
              <Send className="w-4 h-4 fill-current ml-0.5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
