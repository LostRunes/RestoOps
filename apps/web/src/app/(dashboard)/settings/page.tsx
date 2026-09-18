"use client";

import React, { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { Settings, Building2, Utensils, Mail, Save } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const { user } = useAuth();
  const [orgName, setOrgName] = useState("Savor Hospitality Group");
  const [domain, setDomain] = useState("savorhospitality.com");

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Organization settings updated");
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <Settings className="w-5 h-5 text-indigo-400" /> Organization & Restaurant Settings
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Configure restaurant locations, SMTP credentials & system defaults</p>
      </div>

      <div className="p-6 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-5">
        <h3 className="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-3 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-indigo-400" /> General Info
        </h3>

        <form onSubmit={handleSave} className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1">Organization Name</label>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3.5 py-2 text-slate-200 focus:outline-none"
            />
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1">Primary Custom Domain</label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3.5 py-2 text-slate-200 focus:outline-none"
            />
          </div>

          <div className="pt-3">
            <button
              type="submit"
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center gap-2 shadow-md shadow-indigo-950/40"
            >
              <Save className="w-4 h-4" /> Save Settings
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
