"use client";

import React, { useState } from "react";
import { Mail, Lock, User, ArrowRight, AlertCircle, Loader2, Sparkles } from "lucide-react";
import { AuthUser } from "../lib/types";

interface AuthModalProps {
  isOpen: boolean;
  onSuccess: (user: AuthUser, isNew: boolean) => void;
}

export function AuthModal({ isOpen, onSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    const cleanPassword = password.trim();
    const cleanName = displayName.trim();

    if (!cleanEmail || !cleanPassword) {
      setError("Please provide both email and password.");
      return;
    }

    if (mode === "register" && !cleanName) {
      setError("Please tell us what SURU should call you.");
      return;
    }

    setLoading(true);

    try {
      const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      const payload =
        mode === "register"
          ? { email: cleanEmail, password: cleanPassword, display_name: cleanName }
          : { email: cleanEmail, password: cleanPassword };

      const res = await fetch(`http://127.0.0.1:8000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      if (data.user) {
        onSuccess(data.user, mode === "register");
      } else {
        throw new Error("Invalid response from server.");
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 sm:p-6 md:p-8 relative z-20">
      {/* Main Glass Authentication Card */}
      <div className="relative w-full max-w-md aurora-panel rounded-3xl border border-emerald-500/25 bg-[#090f0c]/95 shadow-[0_25px_80px_rgba(0,0,0,0.85)] p-8 sm:p-10 overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Ambient Top Glow Accent */}
        <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-56 h-28 bg-emerald-500/20 rounded-full blur-3xl pointer-events-none -z-10" />

        {/* Brand Logo & Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-[#0e1c14] border border-[#2b5838] flex items-center justify-center shadow-[0_0_24px_rgba(52,211,153,0.35)] mb-3.5">
            <div className="w-10 h-10 rounded-full border border-[#3e804f] flex items-center justify-center">
              <div className="w-4 h-4 rounded-full bg-[#34d399] shadow-[0_0_12px_#34d399]" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">SURU AI</h1>
          <p className="text-xs text-slate-400 mt-1.5 font-normal">Real-Time Autonomous Consumer Assistant</p>
        </div>

        {/* Tab Toggle (Register vs Login) */}
        <div className="grid grid-cols-2 p-1.5 rounded-2xl bg-[#0b140f] border border-emerald-950/80 mb-7">
          <button
            type="button"
            onClick={() => {
              setMode("register");
              setError(null);
            }}
            className={`py-2.5 text-xs font-semibold rounded-xl transition-all cursor-pointer ${
              mode === "register"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Create Account
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("login");
              setError(null);
            }}
            className={`py-2.5 text-xs font-semibold rounded-xl transition-all cursor-pointer ${
              mode === "login"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Log In
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-3.5 rounded-2xl bg-rose-950/40 border border-rose-800/50 flex items-start gap-3 text-xs text-rose-200 animate-in fade-in">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        {/* Spacious, Non-Overlapping Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Email Address Field */}
          <div>
            <label className="block text-xs font-medium text-slate-200 mb-2 tracking-wide select-none">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4.5 h-4.5 text-emerald-500/70 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full h-12 pl-12 pr-4 rounded-2xl bg-[#0c1611] border border-emerald-900/40 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20 transition-all shadow-inner shadow-black/40"
              />
            </div>
          </div>

          {/* Display Name Field (Register Mode Only) */}
          {mode === "register" && (
            <div className="animate-in fade-in duration-200">
              <label className="block text-xs font-medium text-slate-200 mb-2 tracking-wide select-none">
                What should SURU call you?
              </label>
              <div className="relative">
                <User className="w-4.5 h-4.5 text-emerald-500/70 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  required={mode === "register"}
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Saksham"
                  className="w-full h-12 pl-12 pr-4 rounded-2xl bg-[#0c1611] border border-emerald-900/40 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20 transition-all shadow-inner shadow-black/40"
                />
              </div>
            </div>
          )}

          {/* Password Field */}
          <div>
            <label className="block text-xs font-medium text-slate-200 mb-2 tracking-wide select-none">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4.5 h-4.5 text-emerald-500/70 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full h-12 pl-12 pr-4 rounded-2xl bg-[#0c1611] border border-emerald-900/40 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20 transition-all shadow-inner shadow-black/40"
              />
            </div>
          </div>

          {/* Submit Action Button */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-bold text-sm shadow-lg shadow-emerald-950/60 flex items-center justify-center gap-2 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin text-slate-950" />
              ) : (
                <>
                  <span>{mode === "register" ? "Create Account & Start" : "Log In & Continue"}</span>
                  <ArrowRight className="w-4.5 h-4.5" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Footer Toggle Text */}
        <div className="mt-8 pt-5 border-t border-emerald-950/60 text-center">
          <p className="text-xs text-slate-400">
            {mode === "register" ? (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    setError(null);
                  }}
                  className="text-emerald-400 hover:text-emerald-300 hover:underline font-semibold ml-1 cursor-pointer"
                >
                  Log In
                </button>
              </>
            ) : (
              <>
                Don&apos;t have an account yet?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("register");
                    setError(null);
                  }}
                  className="text-emerald-400 hover:text-emerald-300 hover:underline font-semibold ml-1 cursor-pointer"
                >
                  Create one now
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
