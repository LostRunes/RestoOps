"use client";

import React, { useState } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X } from "lucide-react";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import { useNotifications } from "@/hooks/use-notifications";

interface LeadImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function LeadImportDialog({ isOpen, onClose, onSuccess }: LeadImportDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const { jobProgress } = useNotifications();

  if (!isOpen) return null;

  const currentProgress = jobId ? jobProgress[jobId] : null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.upload<{ job_id: string; message: string }>("/leads/import", formData);
      setJobId(response.job_id);
      toast.success("CSV import started", { description: "Processing leads and Queueing email verification..." });
      onSuccess();
    } catch (err: any) {
      toast.error(err.message || "Failed to import CSV file");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-[#0f172a] border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-5 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
        >
          <X className="w-4 h-4" />
        </button>

        <div>
          <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <Upload className="w-4 h-4 text-indigo-400" />
            Import Leads from CSV
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Upload a CSV containing columns: <code className="text-slate-300">company_name, contact_name, email, phone</code>
          </p>
        </div>

        {/* Drag and Drop Zone */}
        <div className="border-2 border-dashed border-slate-700/60 hover:border-indigo-500/50 rounded-xl p-6 text-center transition-colors bg-[#141c2e]/50">
          <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" id="csv-upload-input" />
          <label htmlFor="csv-upload-input" className="cursor-pointer flex flex-col items-center gap-2">
            <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400">
              <FileText className="w-6 h-6" />
            </div>
            {file ? (
              <span className="text-xs font-semibold text-slate-200">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
            ) : (
              <>
                <span className="text-xs font-semibold text-slate-200">Click to select CSV file</span>
                <span className="text-[11px] text-slate-500">Supported format: .csv</span>
              </>
            )}
          </label>
        </div>

        {/* Real-time Job Progress Tracker */}
        {currentProgress && (
          <div className="p-4 rounded-xl bg-[#141c2e] border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-300">Import & Verification Progress</span>
              <span className="font-semibold text-indigo-400">{currentProgress.percentage}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${currentProgress.percentage}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>Processed: {currentProgress.processed} / {currentProgress.total}</span>
              <span>Status: {currentProgress.status}</span>
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-2 disabled:opacity-50 transition-all shadow-md shadow-indigo-950/40"
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Start Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
