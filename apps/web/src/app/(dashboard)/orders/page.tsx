"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Order } from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { ShoppingBag, DollarSign, CheckCircle2 } from "lucide-react";

export default function OrdersPage() {
  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: async () => {
      const res = await api.get<{ items: Order[] }>("/orders");
      return res.items || [];
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <ShoppingBag className="w-5 h-5 text-indigo-400" /> Orders & Confirmed Revenue
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Track catering orders converted from accepted client quotes</p>
      </div>

      <div className="rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#141c2e]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Order #</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Event Date</th>
                <th className="py-3 px-4">Total Amount</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    Loading catering orders...
                  </td>
                </tr>
              ) : !orders || orders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No confirmed catering orders yet.
                  </td>
                </tr>
              ) : (
                orders.map((o) => (
                  <tr key={o.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-indigo-300">{o.order_number}</td>
                    <td className="py-3 px-4 text-slate-200">{o.lead?.company_name || o.lead?.contact_name || `Lead #${o.lead_id.slice(0, 6)}`}</td>
                    <td className="py-3 px-4 text-slate-400">{formatDate(o.event_date)}</td>
                    <td className="py-3 px-4 font-bold text-emerald-400">{formatCurrency(o.total_amount)}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {o.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(o.created_at)}</td>
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
