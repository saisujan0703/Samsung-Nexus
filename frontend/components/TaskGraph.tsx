"use client";

import React from "react";
import { Task, PlanDiff } from "../lib/types";
import { CheckCircle2, Clock, Loader2, XCircle, AlertCircle, RefreshCw, GitFork, Layers } from "lucide-react";

interface TaskGraphProps {
  tasks: Task[];
  planDiff: PlanDiff | null;
}

export function TaskGraph({ tasks, planDiff }: TaskGraphProps) {
  const completedCount = tasks.filter((t) => t.status === "COMPLETED").length;
  const runningCount = tasks.filter((t) => t.status === "RUNNING").length;

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-emerald-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Task Graph DAG
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
            {tasks.length} tasks ({completedCount} done, {runningCount} active)
          </span>
        </div>
      </div>

      {/* Plan Diff Box (Visible when replanning occurs) */}
      {planDiff && (
        <div className="p-3 rounded-xl bg-slate-900/90 border border-indigo-500/30 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-indigo-300 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Plan Diff Engine
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {planDiff.summary || "Selective plan updates calculated"}
            </span>
          </div>

          <div className="grid grid-cols-4 gap-2 text-center text-xs">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <span className="text-[10px] text-emerald-400 font-semibold block">KEEP</span>
              <span className="text-xs font-bold text-emerald-200">
                {planDiff.keep?.length || 0}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <span className="text-[10px] text-rose-400 font-semibold block">CANCEL</span>
              <span className="text-xs font-bold text-rose-200">
                {planDiff.cancel?.length || 0}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <span className="text-[10px] text-amber-400 font-semibold block">MODIFY</span>
              <span className="text-xs font-bold text-amber-200">
                {planDiff.modify?.length || 0}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
              <span className="text-[10px] text-cyan-400 font-semibold block">ADD</span>
              <span className="text-xs font-bold text-cyan-200">
                {planDiff.add?.length || 0}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Task List */}
      <div className="flex flex-col gap-2.5 max-h-[360px] overflow-y-auto pr-1">
        {tasks.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs italic">
            No active tasks. Enter an instruction to initiate planning.
          </div>
        ) : (
          tasks.map((task) => {
            const isCompleted = task.status === "COMPLETED";
            const isRunning = task.status === "RUNNING";
            const isCancelled = task.status === "CANCELLED";
            const isModified = task.diff_action === "MODIFY";

            return (
              <div
                key={task.id}
                className={`p-3 rounded-xl border transition-all ${
                  isRunning
                    ? "bg-emerald-950/20 border-emerald-500/50 shadow-md shadow-emerald-500/5"
                    : isCompleted
                    ? "bg-slate-900/60 border-slate-800"
                    : isCancelled
                    ? "bg-rose-950/15 border-rose-900/40 opacity-60"
                    : "bg-slate-900/40 border-slate-800/80"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    {/* Status Icon */}
                    {isRunning && (
                      <Loader2 className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
                    )}
                    {isCompleted && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    )}
                    {isCancelled && (
                      <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    )}
                    {task.status === "FAILED" && (
                      <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                    )}
                    {task.status === "PENDING" && (
                      <Clock className="w-4 h-4 text-slate-500 shrink-0" />
                    )}

                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-semibold ${
                            isCancelled
                              ? "line-through text-slate-400"
                              : "text-slate-200"
                          }`}
                        >
                          {task.name}
                        </span>
                        {isModified && (
                          <span className="flex items-center gap-0.5 text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            <RefreshCw className="w-2.5 h-2.5" /> REPLANNED
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Tool: {task.tool}
                      </span>
                    </div>
                  </div>

                  {/* Status Pill */}
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full ${
                      isRunning
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : isCompleted
                        ? "bg-slate-800 text-slate-400"
                        : isCancelled
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : "bg-slate-800 text-slate-500"
                    }`}
                  >
                    {task.status}
                  </span>
                </div>

                {/* Output Summary / Cancellation details */}
                {task.output?.summary && (
                  <p className="mt-2 text-[11px] text-slate-300 pl-6.5 font-medium border-l border-emerald-500/30 ml-2">
                    {task.output.summary}
                  </p>
                )}
                {isCancelled && task.cancellation_reason && (
                  <p className="mt-1 text-[10px] text-rose-400 pl-6.5 italic">
                    Reason: {task.cancellation_reason}
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
