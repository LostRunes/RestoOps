"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Quote } from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { FileText, Plus, CheckCircle2, Clock, XCircle, ChevronRight } from "lucide-react";
import Link from "next/link";

export default function QuotesPage() {
  const { data: quotes, isLoading } = useQuery({
    queryKey: ["quotes"],
    queryFn: async () => {
      const res = await api.get<{ items: Quote[] }>("/quotes");
      return res.items || [];
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACCEPTED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ACCEPTED
          </span>
        );
      case "SENT":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            SENT
          </span>
        );
      case "REJECTED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">
            REJECTED
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
            DRAFT
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" /> Quotes & Catering Estimates
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Custom event catering proposals & pricing breakdown</p>
        </div>
        <Link
          href="/quotes/new"
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40 w-max"
        >
          <Plus className="w-4 h-4" /> Create Quote
        </Link>
      </div>

      <div className="rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#141c2e]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Quote #</th>
                <th className="py-3 px-4">Lead / Client</th>
                <th className="py-3 px-4">Event Date</th>
                <th className="py-3 px-4">Guests</th>
                <th className="py-3 px-4">Total</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    Loading quotes...
                  </td>
                </tr>
              ) : !quotes || quotes.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No quotes found. Click "Create Quote" to generate a catering proposal.
                  </td>
                </tr>
              ) : (
                quotes.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-indigo-300">
                      <Link href={`/quotes/${q.id}`}>{q.quote_number}</Link>
                    </td>
                    <td className="py-3 px-4 text-slate-200 font-medium">
                      {q.lead?.company_name || q.lead?.contact_name || `Lead #${q.lead_id.slice(0, 6)}`}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{formatDate(q.event_date)}</td>
                    <td className="py-3 px-4 text-slate-300">{q.guest_count || 0}</td>
                    <td className="py-3 px-4 font-bold text-slate-100">{formatCurrency(q.total)}</td>
                    <td className="py-3 px-4">{getStatusBadge(q.status)}</td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(q.created_at)}</td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/quotes/${q.id}`}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-300 text-[11px] font-medium transition-colors"
                      >
                        Edit Quote
                      </Link>
                    </td>
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
