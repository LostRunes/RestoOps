"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Campaign } from "@/types";
import { formatDate } from "@/lib/utils";
import { Megaphone, Plus, Play, Pause, CheckCircle2, Clock, Users, ArrowRight } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

export default function CampaignsPage() {
  const queryClient = useQueryClient();

  const { data: campaigns, isLoading } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api.get<{ items: Campaign[] }>("/campaigns").then((res) => res.items || []),
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => api.post(`/campaigns/${id}/start`),
    onSuccess: () => {
      toast.success("Campaign sequence started");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to start campaign"),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => api.post(`/campaigns/${id}/pause`),
    onSuccess: () => {
      toast.info("Campaign sequence paused");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to pause campaign"),
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "RUNNING":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 w-max">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" /> RUNNING
          </span>
        );
      case "PAUSED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 w-max">
            PAUSED
          </span>
        );
      case "COMPLETED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 w-max">
            COMPLETED
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700 w-max">
            DRAFT
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-indigo-400" />
            Marketing Campaigns
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Drip sequences and automated multi-channel lead outreach</p>
        </div>
        <Link
          href="/campaigns/new"
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40 w-max"
        >
          <Plus className="w-4 h-4" /> New Campaign
        </Link>
      </div>

      {/* Campaign Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-full text-center py-12 text-slate-500 text-xs">Loading campaigns...</div>
        ) : campaigns?.length === 0 ? (
          <div className="col-span-full text-center py-12 text-slate-500 text-xs bg-[#0f172a] rounded-2xl border border-slate-800">
            No marketing campaigns yet. Click "New Campaign" to create your first email drip sequence.
          </div>
        ) : (
          campaigns?.map((c) => {
            const pct = c.total_leads_targeted > 0 ? Math.round((c.leads_processed / c.total_leads_targeted) * 100) : 0;
            return (
              <div
                key={c.id}
                className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-slate-200 text-sm">{c.name}</h3>
                    {getStatusBadge(c.status)}
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">{c.description || "No description provided."}</p>
                </div>

                <div className="space-y-3 pt-3 border-t border-slate-800">
                  <div className="flex justify-between items-center text-xs text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-indigo-400" />
                      {c.leads_processed} / {c.total_leads_targeted} leads
                    </span>
                    <span className="font-semibold text-slate-200">{pct}%</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-indigo-500 h-1.5 rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center gap-2">
                    {c.status === "DRAFT" || c.status === "PAUSED" ? (
                      <button
                        onClick={() => startMutation.mutate(c.id)}
                        className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-400 hover:bg-emerald-900/60 text-xs font-semibold flex items-center gap-1"
                        title="Start Sequence"
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>
                    ) : c.status === "RUNNING" ? (
                      <button
                        onClick={() => pauseMutation.mutate(c.id)}
                        className="p-2 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-400 hover:bg-amber-900/60 text-xs font-semibold flex items-center gap-1"
                        title="Pause Sequence"
                      >
                        <Pause className="w-3.5 h-3.5" />
                      </button>
                    ) : null}
                  </div>

                  <Link
                    href={`/campaigns/${c.id}`}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                  >
                    Edit & Analytics <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
