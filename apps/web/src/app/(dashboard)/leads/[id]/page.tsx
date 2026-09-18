"use client";

import React, { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Lead } from "@/types";
import { formatDate } from "@/lib/utils";
import {
  Building2,
  Mail,
  Phone,
  MapPin,
  Flame,
  ShieldCheck,
  Activity,
  FileText,
  MessageSquare,
  Sparkles,
  ArrowLeft,
  Loader2,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: lead, isLoading } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => api.get<Lead>(`/leads/${id}`),
  });

  const verifyMutation = useMutation({
    mutationFn: () => api.post(`/leads/${id}/verify`),
    onSuccess: () => {
      toast.success("Email verification completed");
      queryClient.invalidateQueries({ queryKey: ["lead", id] });
    },
    onError: (err: any) => toast.error(err.message || "Verification failed"),
  });

  const scoreMutation = useMutation({
    mutationFn: () => api.post(`/leads/${id}/score`),
    onSuccess: () => {
      toast.success("Lead scoring completed");
      queryClient.invalidateQueries({ queryKey: ["lead", id] });
    },
    onError: (err: any) => toast.error(err.message || "Scoring failed"),
  });

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin" /> Loading lead details...
      </div>
    );
  }

  if (!lead) {
    return <div className="p-8 text-center text-slate-500 text-sm">Lead not found.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/leads" className="p-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-3">
              {lead.company_name}
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
                {lead.status}
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Contact: {lead.contact_name}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700/60"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Verify Email
          </button>
          <button
            onClick={() => scoreMutation.mutate()}
            disabled={scoreMutation.isPending}
            className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-md shadow-indigo-950/40"
          >
            <Sparkles className="w-3.5 h-3.5" /> Score Lead
          </button>
        </div>
      </div>

      {/* Two-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column — Info & Metadata */}
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2">Lead Information</h3>

            <div className="space-y-3 text-xs">
              <div className="flex items-center gap-3 text-slate-300">
                <Building2 className="w-4 h-4 text-slate-500" />
                <span>{lead.company_name}</span>
              </div>
              <div className="flex items-center gap-3 text-slate-300">
                <Mail className="w-4 h-4 text-slate-500" />
                <span className="font-mono text-[11px]">{lead.email}</span>
              </div>
              {lead.phone && (
                <div className="flex items-center gap-3 text-slate-300">
                  <Phone className="w-4 h-4 text-slate-500" />
                  <span>{lead.phone}</span>
                </div>
              )}
              {lead.address && (
                <div className="flex items-center gap-3 text-slate-300">
                  <MapPin className="w-4 h-4 text-slate-500" />
                  <span>{lead.address}, {lead.city}</span>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">Score</span>
                <span className="text-lg font-bold text-slate-100">{lead.score || 0}/100</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">Priority</span>
                <span className="text-xs font-bold text-amber-400">{lead.priority}</span>
              </div>
            </div>
          </div>

          {/* Verification Box */}
          <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> Email Verification
            </h3>
            <div className="p-3 rounded-xl bg-[#141c2e] border border-slate-800 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Result:</span>
                <span className="font-bold text-emerald-400">{lead.verification_status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Checked:</span>
                <span className="text-slate-300">{formatDate(lead.updated_at)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column — Activity & Quotes */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" /> Lead Activity Timeline
              </h3>
            </div>

            <div className="space-y-4 text-xs">
              <div className="flex gap-3 relative before:absolute before:left-2 before:top-6 before:bottom-0 before:w-0.5 before:bg-slate-800">
                <div className="w-4 h-4 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-0.5">
                  •
                </div>
                <div>
                  <p className="font-semibold text-slate-200">Lead Registered in RestoOps</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">{formatDate(lead.created_at)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
