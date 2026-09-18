"use client";

import React, { useState, use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Campaign, CampaignStep } from "@/types";
import { ArrowLeft, Save, Plus, Trash2, Mail, Clock, Sparkles, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export default function CampaignBuilderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const isNew = id === "new";

  const [name, setName] = useState(isNew ? "New Catering Outreach" : "");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<CampaignStep[]>([
    {
      id: "1",
      step_number: 1,
      type: "EMAIL",
      delay_days: 0,
      subject_template: "Exclusive Catering Services for {{company_name}}",
      body_template: "Hi {{contact_name}},\n\nWe noticed {{company_name}} hosts corporate events. We'd love to cater your next occasion!\n\nBest,\nRestoOps Team",
    },
  ]);

  const { data: campaign, isLoading } = useQuery({
    queryKey: ["campaign", id],
    queryFn: async () => {
      if (isNew) return null;
      const res = await api.get<Campaign>(`/campaigns/${id}`);
      setName(res.name);
      setDescription(res.description || "");
      if (res.steps?.length > 0) setSteps(res.steps);
      return res;
    },
    enabled: !isNew,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name,
        description,
        steps: steps.map((s, idx) => ({
          step_number: idx + 1,
          type: s.type,
          delay_days: s.delay_days,
          subject_template: s.subject_template,
          body_template: s.body_template,
        })),
      };
      if (isNew) {
        return api.post<Campaign>("/campaigns", payload);
      } else {
        return api.patch<Campaign>(`/campaigns/${id}`, payload);
      }
    },
    onSuccess: () => {
      toast.success(isNew ? "Campaign created" : "Campaign updated");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      router.push("/campaigns");
    },
    onError: (err: any) => toast.error(err.message || "Failed to save campaign"),
  });

  const addStep = () => {
    setSteps([
      ...steps,
      {
        id: String(Date.now()),
        step_number: steps.length + 1,
        type: "EMAIL",
        delay_days: 2,
        subject_template: "Following up on catering for {{company_name}}",
        body_template: "Hi {{contact_name}},\n\nJust following up on my previous note. Do you have 5 minutes to chat about your catering needs?\n\nBest,",
      },
    ]);
  };

  const removeStep = (index: number) => {
    setSteps(steps.filter((_, i) => i !== index));
  };

  const insertVariable = (stepIndex: number, variable: string) => {
    const newSteps = [...steps];
    newSteps[stepIndex].body_template += ` {{${variable}}}`;
    setSteps(newSteps);
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-500 text-xs">Loading campaign builder...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/campaigns" className="p-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h2 className="text-xl font-bold text-slate-100">{isNew ? "Create Campaign Sequence" : "Edit Campaign"}</h2>
        </div>

        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending || !name}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40 disabled:opacity-50"
        >
          {saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Campaign
        </button>
      </div>

      {/* Campaign Metadata Card */}
      <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
        <h3 className="text-sm font-semibold text-slate-200">Campaign Details</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Campaign Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q4 Corporate Catering Outreach"
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Targeting executive assistants for corporate lunch orders..."
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/60"
            />
          </div>
        </div>
      </div>

      {/* Drip Sequence Steps */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">Drip Sequence Steps ({steps.length})</h3>
          <button
            onClick={addStep}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700/60"
          >
            <Plus className="w-3.5 h-3.5" /> Add Step
          </button>
        </div>

        {steps.map((step, idx) => (
          <div key={step.id || idx} className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4 relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400">
                <Mail className="w-4 h-4" /> Step {idx + 1}: Email Drip
              </div>
              {steps.length > 1 && (
                <button onClick={() => removeStep(idx)} className="text-slate-500 hover:text-red-400 text-xs">
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">Delay After Previous Step (Days)</label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                  <input
                    type="number"
                    min="0"
                    value={step.delay_days}
                    onChange={(e) => {
                      const newSteps = [...steps];
                      newSteps[idx].delay_days = parseInt(e.target.value) || 0;
                      setSteps(newSteps);
                    }}
                    className="w-full bg-[#141c2e] border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">Subject Template</label>
                <input
                  type="text"
                  value={step.subject_template || ""}
                  onChange={(e) => {
                    const newSteps = [...steps];
                    newSteps[idx].subject_template = e.target.value;
                    setSteps(newSteps);
                  }}
                  className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] font-medium text-slate-400">Body Template</label>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-slate-500">Insert Variable:</span>
                  {["contact_name", "company_name"].map((varName) => (
                    <button
                      key={varName}
                      type="button"
                      onClick={() => insertVariable(idx, varName)}
                      className="px-2 py-0.5 rounded text-[10px] bg-indigo-950/60 text-indigo-300 border border-indigo-800/40 hover:bg-indigo-900"
                    >
                      {`{{${varName}}}`}
                    </button>
                  ))}
                </div>
              </div>
              <textarea
                rows={4}
                value={step.body_template}
                onChange={(e) => {
                  const newSteps = [...steps];
                  newSteps[idx].body_template = e.target.value;
                  setSteps(newSteps);
                }}
                className="w-full bg-[#141c2e] border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
