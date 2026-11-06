"use client";

import React, { useState } from "react";
import { BookmarkCheck, CheckCircle2, History, Loader2, ShieldCheck, X } from "lucide-react";

interface SaveVersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (title: string) => Promise<void>;
  defaultTitle: string;
  jobTitle?: string;
  companyName?: string;
  parentVersionNumber?: number | null;
}

export function SaveVersionModal({
  isOpen,
  onClose,
  onConfirm,
  defaultTitle,
  jobTitle,
  companyName,
  parentVersionNumber,
}: SaveVersionModalProps) {
  const [title, setTitle] = useState(defaultTitle);
  const [isSaving, setIsSaving] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || isSaving) return;
    setIsSaving(true);
    try {
      await onConfirm(title.trim());
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl text-slate-200 space-y-4">
        {/* Modal Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              <BookmarkCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Save Tailored Resume</h3>
              <p className="text-xs text-slate-400">Create an immutable tailored version</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Target Requisition Context */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 text-xs space-y-1.5">
          <div className="flex justify-between text-slate-400">
            <span>Target Role:</span>
            <span className="font-semibold text-slate-200">{jobTitle || "Requisition"}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Company:</span>
            <span className="font-medium text-slate-300">{companyName || "Company"}</span>
          </div>
          {parentVersionNumber && (
            <div className="flex justify-between text-slate-400 pt-1 border-t border-slate-800/60">
              <span className="flex items-center gap-1">
                <History className="w-3 h-3 text-indigo-400" />
                Parent Version:
              </span>
              <span className="font-mono text-indigo-300">v{parentVersionNumber}</span>
            </div>
          )}
        </div>

        {/* Factual Integrity Guarantee Notice */}
        <div className="bg-emerald-950/20 border border-emerald-800/30 rounded-xl p-3 text-xs text-emerald-300/90 flex gap-2 items-start">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <p className="text-[11.5px] leading-relaxed">
            Your original resume and base version remain completely untouched. This tailored version is saved independently for this role.
          </p>
        </div>

        {/* Title Input Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Tailored Version Title:
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
              placeholder="e.g. Tailored for Apex Cloud Backend Engineer"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 text-xs font-medium rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !title.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              {isSaving ? "Saving Version..." : "Confirm & Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
