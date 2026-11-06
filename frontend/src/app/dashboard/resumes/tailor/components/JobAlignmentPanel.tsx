"use client";

import React from "react";
import {
  AlertCircle,
  Briefcase,
  CheckCircle2,
  ExternalLink,
  Info,
  MapPin,
  ShieldAlert,
  Sparkles,
  Tag,
} from "lucide-react";

import { Job, JobRequirementAnalysis } from "@/lib/api";

interface JobAlignmentPanelProps {
  job?: Job | null;
  analysis?: JobRequirementAnalysis | null;
}

export function JobAlignmentPanel({ job, analysis }: JobAlignmentPanelProps) {
  if (!job) {
    return (
      <div className="p-6 text-center text-slate-500 text-sm">
        No job requisition loaded.
      </div>
    );
  }

  const compName = job.company?.name || job.company_name || "Company";
  const arrangement = job.work_arrangement || "unspecified";
  const seniority = job.seniority_level || "early_career";

  return (
    <div className="h-full overflow-y-auto space-y-6 p-4 pr-3 text-slate-200">
      {/* Target Job Requisition Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
              Target Requisition
            </span>
            <h2 className="text-base font-bold text-white mt-0.5 leading-snug">
              {job.title}
            </h2>
            <p className="text-xs text-slate-400 font-medium mt-0.5">{compName}</p>
          </div>
          {job.job_url && (
            <a
              href={job.job_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
              title="Open original job posting"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/90 text-slate-300 border border-slate-700/60 capitalize">
            <Briefcase className="w-3 h-3 text-slate-400" />
            {seniority.replace("_", " ")}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/90 text-slate-300 border border-slate-700/60 capitalize">
            <MapPin className="w-3 h-3 text-slate-400" />
            {arrangement}
          </span>
          {job.verification_status === "verified" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-950/40 text-emerald-300 border border-emerald-800/50">
              <CheckCircle2 className="w-3 h-3" />
              Verified
            </span>
          )}
        </div>

        {/* Required Skills from Job */}
        {job.skills_tags && job.skills_tags.length > 0 && (
          <div className="mt-3.5 pt-3 border-t border-slate-800/80">
            <p className="text-[11px] font-medium text-slate-400 mb-1.5 flex items-center gap-1">
              <Tag className="w-3 h-3" />
              Requisition Skills
            </p>
            <div className="flex flex-wrap gap-1.5">
              {job.skills_tags.map((skill, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 text-[11px] rounded bg-slate-800 text-slate-300 border border-slate-700/50"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Strict Zero-Fabrication Integrity Banner */}
      <div className="bg-amber-950/20 border border-amber-600/30 rounded-xl p-3.5 text-xs text-amber-200/90 flex gap-2.5 items-start">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-amber-300">Strict Factual Truth Standard</p>
          <p className="text-[11px] text-amber-200/80 mt-0.5 leading-relaxed">
            Nexora strictly prevents hallucinations. Every modification must be evidenced by your original resume. Unmatched requirements are never fabricated.
          </p>
        </div>
      </div>

      {/* Grounded Alignment Analysis */}
      {analysis && (
        <div className="space-y-4">
          {/* Summary Notes */}
          {analysis.summary_notes && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-300 mb-1">
                <Sparkles className="w-3.5 h-3.5" />
                Alignment Summary
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {analysis.summary_notes}
              </p>
            </div>
          )}

          {/* Relevant Skills Supported by Resume */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Relevant Evidenced Skills
              </div>
              <span className="text-[11px] px-1.5 py-0.2 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/40">
                {analysis.relevant_skills.length}
              </span>
            </div>
            {analysis.relevant_skills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {analysis.relevant_skills.map((skill, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs rounded-md bg-emerald-950/50 text-emerald-200 border border-emerald-700/50"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No exact skill matches detected.</p>
            )}
          </div>

          {/* Missing Requirements (Not in Resume) */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                <AlertCircle className="w-3.5 h-3.5" />
                Missing Qualifications (Unevidenced)
              </div>
              <span className="text-[11px] px-1.5 py-0.2 rounded bg-amber-950/80 text-amber-300 border border-amber-800/40">
                {analysis.missing_requirements.length}
              </span>
            </div>
            {analysis.missing_requirements.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {analysis.missing_requirements.map((req, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs rounded-md bg-amber-950/40 text-amber-200/90 border border-amber-700/40"
                    title="Not evidenced in candidate resume - left unclaimed to maintain truth"
                  >
                    {req}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-emerald-400/80 font-medium">
                No major qualification gaps identified!
              </p>
            )}
            <p className="text-[10px] text-slate-500 mt-2 italic">
              * Kept out of resume content to prevent false representation.
            </p>
          </div>

          {/* Keyword Opportunities */}
          {analysis.keyword_opportunities.length > 0 && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400">
                  <Info className="w-3.5 h-3.5" />
                  Truthful Terminology Opportunities
                </div>
                <span className="text-[11px] px-1.5 py-0.2 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/40">
                  {analysis.keyword_opportunities.length}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {analysis.keyword_opportunities.map((kw, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs rounded-md bg-cyan-950/50 text-cyan-200 border border-cyan-700/50"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Relevant Experience Highlights */}
          {analysis.relevant_experience && analysis.relevant_experience.length > 0 && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
              <p className="text-xs font-semibold text-slate-300 mb-2">
                Evidenced Role Relevance
              </p>
              <ul className="space-y-1.5 text-xs text-slate-400">
                {analysis.relevant_experience.map((exp, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-emerald-400 mt-0.5">&bull;</span>
                    <span>{exp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

