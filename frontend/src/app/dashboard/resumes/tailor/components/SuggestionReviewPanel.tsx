"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCheck,
  Edit3,
  FileCheck2,
  FileText,
  Filter,
  History,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";

import { TailoringChange } from "@/lib/api";

interface SuggestionReviewPanelProps {
  changes: TailoringChange[];
  onUpdateStatus: (
    changeId: string,
    status: "pending" | "accepted" | "rejected" | "modified",
    userContent?: string
  ) => Promise<void>;
  onBatchAction: (action: "accept_all" | "reject_all" | "restore_original") => Promise<void>;
  isLoading: boolean;
}

export function SuggestionReviewPanel({
  changes,
  onUpdateStatus,
  onBatchAction,
  isLoading,
}: SuggestionReviewPanelProps) {
  const [activeFilter, setActiveFilter] = useState<string>("all");
  const [editingChangeId, setEditingChangeId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>("");
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const sections = ["all", "summary", "skills", "experience", "projects"];

  const filteredChanges = changes.filter((c) => {
    if (activeFilter === "all") return true;
    return c.section_name.toLowerCase() === activeFilter.toLowerCase();
  });

  const acceptedCount = changes.filter((c) => c.status === "accepted" || c.status === "modified").length;
  const rejectedCount = changes.filter((c) => c.status === "rejected").length;
  const pendingCount = changes.filter((c) => c.status === "pending").length;

  const handleStartEdit = (change: TailoringChange) => {
    setEditingChangeId(change.id);
    setEditContent(change.user_content || change.proposed_content);
  };

  const handleSaveEdit = async (changeId: string) => {
    if (!editContent.trim()) return;
    setActionInProgress(changeId);
    try {
      await onUpdateStatus(changeId, "modified", editContent.trim());
      setEditingChangeId(null);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleStatusChange = async (
    changeId: string,
    status: "pending" | "accepted" | "rejected"
  ) => {
    setActionInProgress(changeId);
    try {
      await onUpdateStatus(changeId, status);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleBatch = async (action: "accept_all" | "reject_all" | "restore_original") => {
    setActionInProgress(`batch_${action}`);
    try {
      await onBatchAction(action);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden text-slate-200">
      {/* Top Batch Controls & Filter Toolbar */}
      <div className="p-3 border-b border-slate-800 bg-slate-900/70 space-y-3 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Status Metric Pills */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400 font-medium">
              {changes.length} Suggestions
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-medium">
              {acceptedCount} Approved
            </span>
            {pendingCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-400 border border-amber-800/40 font-medium">
                {pendingCount} Pending
              </span>
            )}
            {rejectedCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
                {rejectedCount} Rejected
              </span>
            )}
          </div>

          {/* Batch Action Buttons */}
          <div className="flex items-center gap-1.5 text-xs">
            <button
              onClick={() => handleBatch("accept_all")}
              disabled={isLoading || actionInProgress !== null}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50"
              title="Accept all suggested modifications"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Accept All
            </button>
            <button
              onClick={() => handleBatch("reject_all")}
              disabled={isLoading || actionInProgress !== null}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition disabled:opacity-50 border border-slate-700"
              title="Reject all modifications"
            >
              <X className="w-3.5 h-3.5" />
              Reject All
            </button>
            <button
              onClick={() => handleBatch("restore_original")}
              disabled={isLoading || actionInProgress !== null}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium transition disabled:opacity-50 border border-slate-700"
              title="Reset all content to original resume"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Restore Original
            </button>
          </div>
        </div>

        {/* Section Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
          <span className="text-[11px] text-slate-500 flex items-center gap-1 mr-1">
            <Filter className="w-3 h-3" />
            Section:
          </span>
          {sections.map((sec) => (
            <button
              key={sec}
              onClick={() => setActiveFilter(sec)}
              className={`px-2.5 py-1 text-xs rounded-lg capitalize font-medium transition ${
                activeFilter === sec
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {sec}
            </button>
          ))}
        </div>
      </div>

      {/* Changes List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {filteredChanges.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
            <Sparkles className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-sm font-medium">No suggestions for this section.</p>
            <p className="text-xs text-slate-600 mt-1">
              Select another filter or review other sections.
            </p>
          </div>
        ) : (
          filteredChanges.map((change) => {
            const isEditing = editingChangeId === change.id;
            const isPending = change.status === "pending";
            const isAccepted = change.status === "accepted";
            const isModified = change.status === "modified";
            const isRejected = change.status === "rejected";

            const cardBorder = isAccepted
              ? "border-emerald-600/50 bg-emerald-950/10"
              : isModified
              ? "border-cyan-600/50 bg-cyan-950/10"
              : isRejected
              ? "border-slate-800/80 bg-slate-900/30 opacity-70"
              : "border-slate-800 bg-slate-900/60";

            return (
              <div
                key={change.id}
                className={`border rounded-xl p-4 transition shadow-sm space-y-3 ${cardBorder}`}
              >
                {/* Change Metadata Header */}
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-slate-800 text-indigo-300 border border-slate-700/60">
                      {change.section_name}
                    </span>
                    <span className="text-xs text-slate-400 capitalize">
                      {change.change_type.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 text-xs">
                    {isAccepted && (
                      <span className="px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 font-medium">
                        Approved
                      </span>
                    )}
                    {isModified && (
                      <span className="px-2 py-0.5 rounded bg-cyan-900/60 text-cyan-300 border border-cyan-700/50 font-medium">
                        Customized
                      </span>
                    )}
                    {isRejected && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-medium">
                        Rejected
                      </span>
                    )}
                    {isPending && (
                      <span className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800/40 font-medium">
                        Review Needed
                      </span>
                    )}
                  </div>
                </div>

                {/* Diff Comparison View */}
                <div className="space-y-2 text-xs">
                  {/* Original Content */}
                  <div className="rounded-lg bg-rose-950/20 border border-rose-900/40 p-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-rose-400 mb-1 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                      Original Text
                    </div>
                    <p className="text-rose-200/90 leading-relaxed font-mono text-[11.5px]">
                      {change.original_content}
                    </p>
                  </div>

                  {/* Proposed Content or Inline Editor */}
                  {isEditing ? (
                    <div className="rounded-lg bg-slate-950 border border-indigo-600 p-3 space-y-2">
                      <label className="text-[11px] font-semibold text-indigo-300">
                        Customize Tailored Text:
                      </label>
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        rows={3}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                      />
                      <div className="flex justify-end gap-2 pt-1">
                        <button
                          onClick={() => setEditingChangeId(null)}
                          className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveEdit(change.id)}
                          disabled={actionInProgress === change.id}
                          className="px-3 py-1 text-xs rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
                        >
                          Save & Apply
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div
                      className={`rounded-lg p-2.5 border ${
                        isModified
                          ? "bg-cyan-950/20 border-cyan-800/40"
                          : "bg-emerald-950/20 border-emerald-900/40"
                      }`}
                    >
                      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1 flex items-center justify-between">
                        <span
                          className={`flex items-center gap-1 ${
                            isModified ? "text-cyan-400" : "text-emerald-400"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isModified ? "bg-cyan-400" : "bg-emerald-400"
                            }`}
                          />
                          {isModified ? "Your Tailored Text" : "Proposed Tailored Text"}
                        </span>
                        <button
                          onClick={() => handleStartEdit(change)}
                          className="text-slate-400 hover:text-white flex items-center gap-1 text-[11px]"
                        >
                          <Edit3 className="w-3 h-3" />
                          Edit
                        </button>
                      </div>
                      <p
                        className={`leading-relaxed font-mono text-[11.5px] ${
                          isModified ? "text-cyan-200" : "text-emerald-200/90"
                        }`}
                      >
                        {change.active_content}
                      </p>
                    </div>
                  )}
                </div>

                {/* Grounding & Traceability Citation */}
                {change.supporting_evidence && (
                  <div className="rounded-lg bg-slate-950/60 border border-slate-800/80 p-2.5 text-[11px] space-y-1">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="font-medium text-slate-300 flex items-center gap-1">
                        <FileCheck2 className="w-3 h-3 text-emerald-400" />
                        Original Resume Evidence
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {change.supporting_evidence.section}
                      </span>
                    </div>
                    <p className="text-slate-400 italic">
                      &ldquo;{change.supporting_evidence.excerpt}&rdquo;
                    </p>
                    <div className="pt-1 text-[10px] text-slate-400 flex items-center gap-1">
                      <span className="font-semibold text-slate-300">Target Requisition:</span>
                      <span>{change.related_job_requirement}</span>
                    </div>
                    <div className="text-[10px] text-slate-500">
                      Reason: {change.reason}
                    </div>
                  </div>
                )}

                {/* Inline Action Controls */}
                <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-800/60">
                  <button
                    onClick={() => handleStatusChange(change.id, "accepted")}
                    disabled={isAccepted || actionInProgress === change.id}
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition ${
                      isAccepted
                        ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/50 cursor-default"
                        : "bg-emerald-600 hover:bg-emerald-500 text-white"
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                    {isAccepted ? "Approved" : "Approve"}
                  </button>

                  <button
                    onClick={() => handleStatusChange(change.id, "rejected")}
                    disabled={isRejected || actionInProgress === change.id}
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition ${
                      isRejected
                        ? "bg-slate-800 text-slate-400 border border-slate-700 cursor-default"
                        : "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                    }`}
                  >
                    <X className="w-3.5 h-3.5" />
                    {isRejected ? "Rejected" : "Reject"}
                  </button>

                  {!isEditing && (
                    <button
                      onClick={() => handleStartEdit(change)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 transition"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      Edit
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

