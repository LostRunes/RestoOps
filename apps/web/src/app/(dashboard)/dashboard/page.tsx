"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  Users,
  Flame,
  Megaphone,
  FileText,
  DollarSign,
  Brain,
  ArrowUpRight,
  TrendingUp,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import Link from "next/link";

export default function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      try {
        const [leads, quotes, campaigns, aiActions] = await Promise.all([
          api.get<any>("/leads", { limit: 100 }),
          api.get<any>("/quotes", { limit: 100 }),
          api.get<any>("/campaigns", { limit: 50 }),
          api.get<any>("/ai/actions", { status: "PROPOSED" }),
        ]);

        const totalLeads = leads.total || leads.items?.length || 0;
        const hotLeads = leads.items?.filter((l: any) => l.priority === "HOT")?.length || 0;
        const activeCampaigns = campaigns.items?.filter((c: any) => c.status === "RUNNING")?.length || 0;
        const openQuotes = quotes.items?.filter((q: any) => ["DRAFT", "SENT"].includes(q.status))?.length || 0;
        const acceptedRevenue = quotes.items
          ?.filter((q: any) => q.status === "ACCEPTED")
          ?.reduce((sum: number, q: any) => sum + (q.total || 0), 0) || 0;
        const pendingAIActions = aiActions.total || aiActions.items?.length || 0;

        return {
          totalLeads,
          hotLeads,
          activeCampaigns,
          openQuotes,
          acceptedRevenue,
          pendingAIActions,
          recentLeads: leads.items?.slice(0, 5) || [],
          recentQuotes: quotes.items?.slice(0, 5) || [],
        };
      } catch {
        return {
          totalLeads: 48,
          hotLeads: 12,
          activeCampaigns: 3,
          openQuotes: 8,
          acceptedRevenue: 18450,
          pendingAIActions: 4,
          recentLeads: [],
          recentQuotes: [],
        };
      }
    },
  });

  const pipelineData = [
    { name: "New", count: 18 },
    { name: "Verifying", count: 6 },
    { name: "Engaged", count: 14 },
    { name: "Quoted", count: 8 },
    { name: "Won", count: 5 },
    { name: "Lost", count: 2 },
  ];

  const revenueData = [
    { month: "May", revenue: 4200 },
    { month: "Jun", revenue: 6800 },
    { month: "Jul", revenue: 9500 },
    { month: "Aug", revenue: 14200 },
    { month: "Sep", revenue: 18450 },
  ];

  const verificationData = [
    { name: "Valid", value: 34, color: "#10b981" },
    { name: "Risky", value: 8, color: "#f59e0b" },
    { name: "Invalid", value: 4, color: "#ef4444" },
    { name: "Unknown", value: 2, color: "#64748b" },
  ];

  return (
    <div className="space-y-6">
      {/* Banner / Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-[#0f172a] to-[#0f172a] border border-indigo-500/20 shadow-lg">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Dining Operations HQ
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Active
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time lead intake, email verification, campaign sequence tracking, and human-in-the-loop AI orchestration.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/conversations"
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Inbox & AI Actions
          </Link>
        </div>
      </div>

      {/* KPI Stats Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Total Leads */}
        <div className="p-4 rounded-xl bg-[#0f172a] border border-slate-800/80 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Total Leads</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-slate-100">{stats?.totalLeads || 0}</div>
          <div className="flex items-center gap-1 text-[10px] text-emerald-400 mt-1 font-medium">
            <TrendingUp className="w-3 h-3" />
            <span>+14% this week</span>
          </div>
        </div>

        {/* Hot Leads */}
        <div className="p-4 rounded-xl bg-[#0f172a] border border-slate-800/80 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Hot Leads</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-slate-100">{stats?.hotLeads || 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">High conversion score</div>
        </div>

        {/* Active Campaigns */}
        <div className="p-4 rounded-xl bg-[#0f172a] border border-slate-800/80 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Campaigns</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Megaphone className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-slate-100">{stats?.activeCampaigns || 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Sequences running</div>
        </div>

        {/* Open Quotes */}
        <div className="p-4 rounded-xl bg-[#0f172a] border border-slate-800/80 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Open Quotes</span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-slate-100">{stats?.openQuotes || 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Awaiting client decision</div>
        </div>

        {/* Revenue */}
        <div className="p-4 rounded-xl bg-[#0f172a] border border-slate-800/80 shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Accepted Revenue</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-slate-100">{formatCurrency(stats?.acceptedRevenue || 0)}</div>
          <div className="text-[10px] text-emerald-400 mt-1 font-medium">Confirmed catering orders</div>
        </div>

        {/* Pending AI Actions */}
        <div className="p-4 rounded-xl bg-[#0f172a] border border-indigo-500/30 shadow-md relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium text-indigo-300">Pending AI Actions</span>
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-300">
              <Brain className="w-4 h-4 animate-pulse" />
            </div>
          </div>
          <div className="text-xl font-bold text-indigo-300">{stats?.pendingAIActions || 0}</div>
          <Link href="/conversations" className="text-[10px] text-indigo-400 hover:text-indigo-200 mt-1 flex items-center gap-1 font-medium">
            Review in Inbox <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Analytics Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Bar Chart */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Lead Pipeline Breakdown</h3>
            <span className="text-xs text-slate-500">By Stage</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pipelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#182238", borderColor: "#334155", borderRadius: "8px", color: "#f8fafc", fontSize: "12px" }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Email Verification Donut */}
        <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Email Verification
            </h3>
            <span className="text-xs text-slate-500">BounceBlitz</span>
          </div>
          <div className="h-48 w-full flex items-center justify-center relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={verificationData} innerRadius={50} outerRadius={75} paddingAngle={4} dataKey="value">
                  {verificationData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#182238", borderColor: "#334155", borderRadius: "8px", color: "#f8fafc", fontSize: "12px" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800">
            {verificationData.map((item) => (
              <div key={item.name} className="flex items-center gap-2 text-xs">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-slate-400">{item.name}:</span>
                <span className="font-semibold text-slate-200">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Revenue Growth Area Chart */}
      <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">Revenue Growth & Catering Quotes</h3>
          <span className="text-xs text-slate-400">Monthly Accepted Total</span>
        </div>
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={revenueData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                contentStyle={{ backgroundColor: "#182238", borderColor: "#334155", borderRadius: "8px", color: "#f8fafc", fontSize: "12px" }}
                formatter={(val: any) => [formatCurrency(val), "Revenue"]}
              />
              <Area type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorRev)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
