"use client";

import React from "react";
import { Activity, CheckCircle2, Clock, Play } from "lucide-react";
import { useNotifications } from "@/hooks/use-notifications";

export default function JobsPage() {
  const { jobProgress } = useNotifications();
  const jobsList = Object.values(jobProgress);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-400" /> Background Processing Jobs
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Real-time status of email verifications, AI batches & background tasks</p>
      </div>

      <div className="space-y-4">
        {jobsList.length === 0 ? (
          <div className="p-8 rounded-2xl bg-[#0f172a] border border-slate-800 text-center text-xs text-slate-500">
            No active background jobs running. Start a CSV import or email verification to monitor real-time progress.
          </div>
        ) : (
          jobsList.map((job) => (
            <div key={job.job_id} className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-xs text-slate-200">{job.job_type}</h3>
                  <span className="text-[10px] text-slate-500 font-mono">Job ID: {job.job_id}</span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  {job.status}
                </span>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Progress ({job.processed} / {job.total})</span>
                  <span className="font-bold text-indigo-400">{job.percentage}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div className="bg-indigo-500 h-2 rounded-full transition-all duration-300" style={{ width: `${job.percentage}%` }} />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
