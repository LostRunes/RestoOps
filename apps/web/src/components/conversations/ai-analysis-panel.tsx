"use client";

import React, { useState } from "react";
import { Brain, Check, X, Edit2, AlertCircle, Sparkles, Loader2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AIAction } from "@/types";

interface AIAnalysisPanelProps {
  conversationId: string;
}

export function AIAnalysisPanel({ conversationId }: AIAnalysisPanelProps) {
  const queryClient = useQueryClient();

  const { data: actions, isLoading } = useQuery({
    queryKey: ["ai-actions", conversationId],
    queryFn: async () => {
      const res = await api.get<{ items: AIAction[] }>("/ai/actions", { conversation_id: conversationId });
      return res.items || [];
    },
    enabled: !!conversationId,
  });

  const approveMutation = useMutation({
    mutationFn: (actionId: string) => api.post(`/ai/actions/${actionId}/approve`),
    onSuccess: () => {
      toast.success("AI Action Approved & Executed");
      queryClient.invalidateQueries({ queryKey: ["ai-actions", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to approve action"),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ actionId, reason }: { actionId: string; reason: string }) =>
      api.post(`/ai/actions/${actionId}/reject`, { reason }),
    onSuccess: () => {
      toast.info("AI Action Rejected");
      queryClient.invalidateQueries({ queryKey: ["ai-actions", conversationId] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to reject action"),
  });

  return (
    <div className="w-80 bg-[#0d1322] border-l border-slate-800 p-4 space-y-4 overflow-y-auto flex flex-col">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
          <Brain className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-xs font-bold text-slate-200">AI Intelligence & HITL</h3>
          <p className="text-[10px] text-slate-400">Human-in-the-Loop Controls</p>
        </div>
      </div>

      {/* AI Intelligence Summary */}
      <div className="p-3 rounded-xl bg-[#141c2e] border border-slate-800 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Detected Intent:</span>
          <span className="font-semibold text-indigo-300 bg-indigo-950/60 px-2 py-0.5 rounded text-[10px] border border-indigo-800/40">
            NEEDS_QUOTE
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Sentiment:</span>
          <span className="font-semibold text-emerald-400">HIGHLY INTERESTED</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Estimated Party Size:</span>
          <span className="font-bold text-slate-200">45 Guests</span>
        </div>
      </div>

      {/* Proposed Actions Section */}
      <div className="space-y-3 flex-1">
        <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
          <span>Proposed Actions</span>
          {actions && actions.length > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500 text-white font-bold">
              {actions.length}
            </span>
          )}
        </h4>

        {isLoading ? (
          <div className="text-center py-6 text-slate-500 text-xs">Loading AI proposals...</div>
        ) : !actions || actions.length === 0 ? (
          <div className="p-4 rounded-xl bg-[#141c2e]/50 border border-slate-800/60 text-center text-xs text-slate-500">
            No pending AI actions for this thread. AI is monitoring incoming replies.
          </div>
        ) : (
          actions.map((act) => (
            <div key={act.id} className="p-3.5 rounded-xl bg-[#141c2e] border border-indigo-500/30 space-y-3 shadow-md">
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-slate-200 text-xs">{act.tool_name}</span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  {act.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{act.description}</p>

              {/* Approve / Reject Controls */}
              {act.status === "PROPOSED" && (
                <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => approveMutation.mutate(act.id)}
                    disabled={approveMutation.isPending}
                    className="flex-1 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-1 shadow-sm"
                  >
                    {approveMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                    Approve
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate({ actionId: act.id, reason: "Manual rejection" })}
                    disabled={rejectMutation.isPending}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-red-950 hover:text-red-300 text-slate-400 font-medium text-xs flex items-center justify-center gap-1 border border-slate-700"
                  >
                    <X className="w-3.5 h-3.5" />
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
