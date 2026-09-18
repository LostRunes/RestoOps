"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { AIRun, AIAction } from "@/types";
import { formatDate } from "@/lib/utils";
import { Brain, Sparkles, CheckCircle2, XCircle, Clock, Zap } from "lucide-react";

export default function AIActivityPage() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ["ai-runs"],
    queryFn: async () => {
      const res = await api.get<{ items: AIRun[] }>("/ai/runs");
      return res.items || [];
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <Brain className="w-5 h-5 text-indigo-400" /> AI Activity & Agent Execution Log
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Audit trail of autonomous AI LLM decisions, token usage & action proposals</p>
      </div>

      <div className="rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#141c2e]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Agent Type</th>
                <th className="py-3 px-4">Model</th>
                <th className="py-3 px-4">Prompt Summary</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4">Tokens</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading AI run logs...
                  </td>
                </tr>
              ) : !runs || runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No AI execution runs logged yet.
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-indigo-300">{r.agent_type}</td>
                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">{r.model_name}</td>
                    <td className="py-3 px-4 text-slate-300 truncate max-w-xs">{r.prompt_summary || "—"}</td>
                    <td className="py-3 px-4 text-slate-400 font-mono">{r.latency_ms}ms</td>
                    <td className="py-3 px-4 text-slate-400 font-mono">{r.token_count}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {r.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(r.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
