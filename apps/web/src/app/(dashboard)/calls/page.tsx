"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Call } from "@/types";
import { formatDate } from "@/lib/utils";
import { Phone, Plus, Globe, Radio, CheckCircle2, Clock } from "lucide-react";
import { CallDialog } from "@/components/calls/call-dialog";

export default function CallsPage() {
  const [isCallOpen, setIsCallOpen] = useState(false);

  const { data: calls, isLoading } = useQuery({
    queryKey: ["calls"],
    queryFn: async () => {
      const res = await api.get<{ items: Call[] }>("/calls");
      return res.items || [];
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Phone className="w-5 h-5 text-indigo-400" /> Call Log & WebRTC Center
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Telephony records & real-time browser calling session logs</p>
        </div>
        <button
          onClick={() => setIsCallOpen(true)}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40 w-max"
        >
          <Plus className="w-4 h-4" /> Start New Call
        </button>
      </div>

      <div className="rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#141c2e]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Provider</th>
                <th className="py-3 px-4">Lead / Contact</th>
                <th className="py-3 px-4">Direction</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    Loading call history...
                  </td>
                </tr>
              ) : !calls || calls.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No calls recorded yet. Click "Start New Call" to test WebRTC / Exotel calling.
                  </td>
                </tr>
              ) : (
                calls.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-950/60 text-indigo-300 border border-indigo-800/40 flex items-center gap-1 w-max">
                        {c.provider === "WEBRTC" ? <Globe className="w-3 h-3" /> : <Radio className="w-3 h-3" />}
                        {c.provider}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-200">
                      {c.lead?.company_name || c.lead?.contact_name || `Lead #${c.lead_id.slice(0, 6)}`}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">{c.direction}</td>
                    <td className="py-3 px-4 text-slate-300 font-mono">{c.duration_seconds || 0}s</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(c.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <CallDialog isOpen={isCallOpen} onClose={() => setIsCallOpen(false)} />
    </div>
  );
}
