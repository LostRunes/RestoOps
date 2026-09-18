"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Lead } from "@/types";
import { formatDate } from "@/lib/utils";
import {
  Users,
  Search,
  Upload,
  Plus,
  Flame,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Filter,
  MoreVertical,
  CheckCircle,
} from "lucide-react";
import Link from "next/link";
import { LeadImportDialog } from "@/components/leads/lead-import-dialog";
import { toast } from "sonner";

export default function LeadsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [page, setPage] = useState(1);
  const [isImportOpen, setIsImportOpen] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["leads", search, statusFilter, priorityFilter, page],
    queryFn: () =>
      api.get<{ items: Lead[]; total: number; pages: number }>("/leads", {
        search,
        status: statusFilter,
        priority: priorityFilter,
        page,
        limit: 15,
      }),
  });

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "HOT":
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20 flex items-center gap-1 w-max">
            <Flame className="w-3 h-3 text-red-400" /> HOT
          </span>
        );
      case "HIGH":
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 w-max">
            HIGH
          </span>
        );
      case "MEDIUM":
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 w-max">
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700 w-max">
            LOW
          </span>
        );
    }
  };

  const getVerificationIcon = (res: string) => {
    switch (res) {
      case "VALID":
        return (
          <span title="Valid email address">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </span>
        );
      case "RISKY":
        return (
          <span title="Risky email address">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </span>
        );
      case "INVALID":
        return (
          <span title="Invalid email address">
            <ShieldX className="w-4 h-4 text-red-400" />
          </span>
        );
      default:
        return (
          <span title="Unverified">
            <HelpCircle className="w-4 h-4 text-slate-500" />
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            Leads Directory
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Manage, verify, score and engage dining prospects</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsImportOpen(true)}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-2 transition-colors border border-slate-700/60"
          >
            <Upload className="w-3.5 h-3.5" />
            Import CSV
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company, contact, or email..."
            className="w-full bg-[#141c2e] border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/60"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-[#141c2e] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none"
          >
            <option value="">All Priorities</option>
            <option value="HOT">HOT</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#141c2e] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="NEW">NEW</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="SCORED">SCORED</option>
            <option value="ENGAGED">ENGAGED</option>
            <option value="QUOTED">QUOTED</option>
            <option value="WON">WON</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#141c2e]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-4">Contact</th>
                <th className="py-3 px-4">Email Verification</th>
                <th className="py-3 px-4">Score</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    Loading leads...
                  </td>
                </tr>
              ) : data?.items?.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No leads found matching query.
                  </td>
                </tr>
              ) : (
                data?.items?.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200">
                      <Link href={`/leads/${lead.id}`} className="hover:text-indigo-400">
                        {lead.company_name}
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{lead.contact_name}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {getVerificationIcon(lead.verification_status)}
                        <span className="text-slate-400 font-mono text-[11px] truncate max-w-[140px]">{lead.email}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-200">{lead.score || 0}</td>
                    <td className="py-3 px-4">{getPriorityBadge(lead.priority)}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
                        {lead.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(lead.created_at)}</td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/leads/${lead.id}`}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-300 text-[11px] font-medium transition-colors"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-[#141c2e]/40">
          <span>Showing page {page} of {data?.pages || 1}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => (data?.pages && page < data.pages ? p + 1 : p))}
              disabled={!data?.pages || page >= data.pages}
              className="p-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <LeadImportDialog isOpen={isImportOpen} onClose={() => setIsImportOpen(false)} onSuccess={refetch} />
    </div>
  );
}
