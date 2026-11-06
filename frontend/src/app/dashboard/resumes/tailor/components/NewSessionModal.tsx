"use client";

import React, { useState } from "react";
import {
  Briefcase,
  CheckCircle2,
  FileText,
  History,
  Loader2,
  Plus,
  Sparkles,
  X,
} from "lucide-react";

import { Job, ResumeSummary, TailoringSessionSummary } from "@/lib/api";

interface NewSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobs: Job[];
  resumes: ResumeSummary[];
  pastSessions: TailoringSessionSummary[];
  preselectedJobId?: string | null;
  onStartSession: (jobId: string, resumeId: string) => Promise<void>;
  onResumeSession: (sessionId: string) => void;
  isLoading: boolean;
}

export function NewSessionModal({
  isOpen,
  onClose,
  jobs,
  resumes,
  pastSessions,
  preselectedJobId,
  onStartSession,
  onResumeSession,
  isLoading,
}: NewSessionModalProps) {
  const [selectedJobId, setSelectedJobId] = useState<string>(
    preselectedJobId || (jobs.length > 0 ? jobs[0].id : "")
  );
  const [selectedResumeId, setSelectedResumeId] = useState<string>(
    resumes.length > 0 ? resumes[0].id : ""
  );
  const [tab, setTab] = useState<"new" | "history">("new");

  if (!isOpen) return null;

  const handleCreate = async () => {
    if (!selectedJobId || !selectedResumeId || isLoading) return;
    await onStartSession(selectedJobId, selectedResumeId);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl text-slate-200 space-y-5">
        {/* Modal Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-indigo-950/80 text-indigo-400 border border-indigo-800/40">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Resume Tailoring Studio</h3>
              <p className="text-xs text-slate-400">
                Optimize your resume for a specific job with zero factual fabrication
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Selector */}
        {pastSessions.length > 0 && (
          <div className="flex border-b border-slate-800 gap-4 text-xs font-medium">
            <button
              onClick={() => setTab("new")}
              className={`pb-2 border-b-2 transition flex items-center gap-1.5 ${
                tab === "new"
                  ? "border-indigo-500 text-indigo-300 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              Start New Tailoring
            </button>
            <button
              onClick={() => setTab("history")}
              className={`pb-2 border-b-2 transition flex items-center gap-1.5 ${
                tab === "history"
                  ? "border-indigo-500 text-indigo-300 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <History className="w-3.5 h-3.5" />
              Past Sessions ({pastSessions.length})
            </button>
          </div>
        )}

        {tab === "new" ? (
          <div className="space-y-4">
            {/* Step 1: Select Target Job Requisition */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1">
                <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
                1. Select Target Job Opportunity:
              </label>
              {jobs.length === 0 ? (
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-500">
                  No discovered jobs found. Please browse Jobs first.
                </div>
              ) : (
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {jobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.title} — {job.company?.name || job.company_name || "Company"} ({job.work_arrangement})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Step 2: Select Base Candidate Resume */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1">
                <FileText className="w-3.5 h-3.5 text-emerald-400" />
                2. Select Base Resume:
              </label>
              {resumes.length === 0 ? (
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-500">
                  No uploaded resumes found. Please upload a resume first in Resume Studio.
                </div>
              ) : (
                <select
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.title} ({r.version_count} versions)
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Zero Fabrication standard reminder */}
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 leading-relaxed">
              <span className="font-semibold text-slate-200">Zero-Fabrication Promise:</span> Nexora analyzes your resume against the target requisition, aligns genuine keywords, reorders competencies, and sharpens action verbs. It will never invent missing qualifications.
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={!selectedJobId || !selectedResumeId || isLoading}
                className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-md disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                {isLoading ? "Analyzing & Generating..." : "Start Tailoring Session"}
              </button>
            </div>
          </div>
        ) : (
          /* Past Sessions List */
          <div className="max-h-80 overflow-y-auto space-y-2.5 pr-1">
            {pastSessions.map((session) => (
              <div
                key={session.id}
                onClick={() => onResumeSession(session.id)}
                className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-600/60 transition cursor-pointer flex items-center justify-between gap-3 text-xs"
              >
                <div>
                  <h4 className="font-semibold text-white">{session.job_title}</h4>
                  <p className="text-slate-400 text-[11px]">{session.company_name} &bull; {session.resume_title}</p>
                  <p className="text-slate-500 text-[10px] mt-0.5">
                    {session.accepted_changes}/{session.total_changes} changes approved &bull; Status: {session.status}
                  </p>
                </div>
                <button className="px-3 py-1.5 rounded-lg bg-indigo-950/80 text-indigo-300 border border-indigo-800/40 hover:bg-indigo-900 transition font-medium">
                  Open
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
