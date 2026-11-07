"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import Link from "next/link";
import {
  recommendationsApi,
  JobRecommendationItem,
  AIJobMatch,
  JobIntelligence,
} from "@/lib/api";

export default function RecommendationsPage() {
  const [items, setItems] = useState<JobRecommendationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [activeResumeTitle, setActiveResumeTitle] = useState<string | null>(null);
  const [activeResumeVersionId, setActiveResumeVersionId] = useState<string | null>(null);
  const [stats, setStats] = useState({
    top_score: 0,
    total_count: 0,
    ai_evaluated_count: 0,
    verified_count: 0,
  });

  // Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFamily, setRoleFamily] = useState("");
  const [workArrangement, setWorkArrangement] = useState("all");
  const [seniority, setSeniority] = useState("all");
  const [verificationStatus, setVerificationStatus] = useState("all");
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [salaryDisclosedOnly, setSalaryDisclosedOnly] = useState(false);
  const [includeApplied, setIncludeApplied] = useState(false);
  const [sortBy, setSortBy] = useState("recommendation_score");

  // UI state
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [evaluateTopAI, setEvaluateTopAI] = useState(false);
  const [selectedJob, setSelectedJob] = useState<JobRecommendationItem | null>(null);
  const [selectedJobAI, setSelectedJobAI] = useState<AIJobMatch | null>(null);
  const [selectedJobIntelligence, setSelectedJobIntelligence] = useState<JobIntelligence | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [evaluatingAI, setEvaluatingAI] = useState(false);
  const [activeModalTab, setActiveModalTab] = useState<"ai_match" | "intelligence" | "details">("ai_match");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [, startTransition] = useTransition();

  const loadRecommendations = useCallback(async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await recommendationsApi.getRecommendations({
        resume_version_id: activeResumeVersionId || undefined,
        search_query: searchQuery.trim() || undefined,
        role_family: roleFamily || undefined,
        work_arrangement: workArrangement !== "all" ? workArrangement : undefined,
        seniority: seniority !== "all" ? seniority : undefined,
        verification_status: verificationStatus !== "all" ? verificationStatus : undefined,
        min_score: minScore,
        salary_disclosed_only: salaryDisclosedOnly,
        include_applied: includeApplied,
        sort_by: sortBy,
        page,
        page_size: pageSize,
      });

      setItems(res.items);
      setTotal(res.total);
      setActiveResumeTitle(res.active_resume_title || null);
      setActiveResumeVersionId(res.active_resume_version_id || null);
      setStats({
        top_score: res.stats.top_score || 0,
        total_count: res.stats.total_count || 0,
        ai_evaluated_count: res.stats.ai_evaluated_count || 0,
        verified_count: res.stats.verified_count || 0,
      });
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to load recommendations. Please verify your resume is uploaded.");
    } finally {
      setLoading(false);
    }
  }, [
    activeResumeVersionId,
    includeApplied,
    minScore,
    page,
    pageSize,
    roleFamily,
    salaryDisclosedOnly,
    searchQuery,
    seniority,
    sortBy,
    verificationStatus,
    workArrangement,
  ]);

  useEffect(() => {
    loadRecommendations();
  }, [loadRecommendations]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadRecommendations();
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      setErrorMsg(null);
      const res = await recommendationsApi.refreshRecommendations({
        resume_version_id: activeResumeVersionId || undefined,
        evaluate_top_ai: evaluateTopAI,
        max_ai_evaluations: 3,
      });
      setSuccessMsg(
        `${res.message}. Found ${res.recommendations_count} opportunities (${res.ai_evaluations_run} AI evaluations run).`
      );
      setTimeout(() => setSuccessMsg(null), 5000);
      await loadRecommendations();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to refresh recommendations");
    } finally {
      setRefreshing(false);
    }
  };

  const handleToggleSave = async (jobItem: JobRecommendationItem) => {
    try {
      const newSaved = !jobItem.is_saved;
      await recommendationsApi.updateJobState(jobItem.job_id, {
        is_saved: newSaved,
      });
      setItems((prev) =>
        prev.map((item) =>
          item.job_id === jobItem.job_id ? { ...item, is_saved: newSaved } : item
        )
      );
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to update saved status");
    }
  };

  const handleDismiss = async (jobItem: JobRecommendationItem) => {
    try {
      await recommendationsApi.updateJobState(jobItem.job_id, {
        is_dismissed: true,
      });
      setItems((prev) => prev.filter((item) => item.job_id !== jobItem.job_id));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to dismiss opportunity");
    }
  };

  const handleOpenDetailModal = async (jobItem: JobRecommendationItem) => {
    setSelectedJob(jobItem);
    setSelectedJobAI(null);
    setSelectedJobIntelligence(null);
    setModalLoading(true);
    setActiveModalTab(jobItem.ai_evaluated ? "ai_match" : "intelligence");

    try {
      // 1. Load job intelligence
      const intel = await recommendationsApi.getJobIntelligence(jobItem.job_id);
      setSelectedJobIntelligence(intel);

      // 2. Load AI evaluation if available
      try {
        const aiMatch = await recommendationsApi.getAIMatch(
          jobItem.job_id,
          activeResumeVersionId || undefined
        );
        setSelectedJobAI(aiMatch);
      } catch {
        // Not evaluated yet
        setSelectedJobAI(null);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      loggerError(e.message || "Failed to load job details");
    } finally {
      setModalLoading(false);
    }
  };

  const handleRunAIMatchEvaluation = async () => {
    if (!selectedJob) return;
    try {
      setEvaluatingAI(true);
      setErrorMsg(null);
      const res = await recommendationsApi.runAIMatch(selectedJob.job_id, {
        resume_version_id: activeResumeVersionId || undefined,
        force_refresh: true,
      });
      setSelectedJobAI(res);
      setActiveModalTab("ai_match");
      // Update item in list
      setItems((prev) =>
        prev.map((item) =>
          item.job_id === selectedJob.job_id
            ? {
                ...item,
                ai_evaluated: true,
                ai_compatibility_rating: res.compatibility_rating,
                ai_fit_score: res.fit_score,
              }
            : item
        )
      );
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to run AI match evaluation");
    } finally {
      setEvaluatingAI(false);
    }
  };

  const loggerError = (msg: string) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(null), 6000);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-8">
      {/* Top Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <span className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </span>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                  AI Job Intelligence & Recommendations
                </h1>
                <p className="text-sm text-slate-400 mt-0.5">
                  Personalized technical opportunities ranked with verifiable evidence, skill gap insights, and zero fabrication.
                </p>
              </div>
            </div>

            {activeResumeTitle && (
              <div className="flex items-center gap-2 mt-3 text-xs text-slate-400">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Active Resume
                </span>
                <span className="font-semibold text-slate-200">{activeResumeTitle}</span>
                <Link
                  href="/dashboard/resumes"
                  className="text-indigo-400 hover:text-indigo-300 underline ml-2"
                >
                  Change Resume
                </Link>
                <span className="text-slate-600">|</span>
                <Link
                  href="/dashboard/matches"
                  className="text-indigo-400 hover:text-indigo-300 underline"
                >
                  Target Preferences
                </Link>
              </div>
            )}
          </div>

          {/* Action Header controls */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60 text-xs">
              <label htmlFor="eval-ai-toggle" className="text-slate-300 cursor-pointer select-none">
                Auto-evaluate top AI
              </label>
              <input
                id="eval-ai-toggle"
                type="checkbox"
                checked={evaluateTopAI}
                onChange={(e) => setEvaluateTopAI(e.target.checked)}
                className="rounded border-slate-600 text-indigo-500 focus:ring-indigo-400 h-4 w-4 bg-slate-900"
              />
            </div>

            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-600/20 disabled:opacity-50"
            >
              {refreshing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Refreshing...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Refresh Recommendations
                </>
              )}
            </button>
          </div>
        </div>

        {/* Alerts */}
        {errorMsg && (
          <div className="mt-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-200">
              ✕
            </button>
          </div>
        )}

        {successMsg && (
          <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200">
              ✕
            </button>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Top Recommendation</p>
            <p className="text-2xl font-bold text-indigo-400 mt-1">{stats.top_score} / 100</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Highest blended fit score</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Recommended Jobs</p>
            <p className="text-2xl font-bold text-slate-100 mt-1">{stats.total_count}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Active matching requisitions</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">AI Match Evaluated</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.ai_evaluated_count}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Deep compatibility assessments</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Verified / Corroborated</p>
            <p className="text-2xl font-bold text-sky-400 mt-1">{stats.verified_count}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Trustworthy official sources</p>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="mt-8 p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col gap-4">
          <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder="Search job title, company, or keyword (e.g. Python, AI, React)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-slate-500"
              />
              <svg className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium border border-slate-600/50"
            >
              Search
            </button>
          </form>

          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-xs">
            {/* Role family */}
            <div>
              <label className="block text-slate-400 mb-1">Role Family</label>
              <select
                value={roleFamily}
                onChange={(e) => setRoleFamily(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Roles</option>
                <option value="Python Backend">Python Backend</option>
                <option value="Frontend">Frontend Engineering</option>
                <option value="Full Stack">Full Stack</option>
                <option value="AI">AI / Machine Learning</option>
                <option value="Generative AI">Generative AI / LLM</option>
                <option value="Software Engineer">SDE / General</option>
                <option value="Data">Data Engineering</option>
                <option value="DevOps">DevOps & Cloud</option>
              </select>
            </div>

            {/* Work arrangement */}
            <div>
              <label className="block text-slate-400 mb-1">Arrangement</label>
              <select
                value={workArrangement}
                onChange={(e) => setWorkArrangement(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="all">All Arrangements</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="on_site">On-Site</option>
              </select>
            </div>

            {/* Seniority */}
            <div>
              <label className="block text-slate-400 mb-1">Seniority</label>
              <select
                value={seniority}
                onChange={(e) => setSeniority(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="all">All Seniorities</option>
                <option value="fresher">Fresher / Intern</option>
                <option value="entry_level">Entry Level (0-2y)</option>
                <option value="junior">Junior (1-3y)</option>
                <option value="mid">Mid Level</option>
              </select>
            </div>

            {/* Verification */}
            <div>
              <label className="block text-slate-400 mb-1">Verification</label>
              <select
                value={verificationStatus}
                onChange={(e) => setVerificationStatus(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="all">All Listings</option>
                <option value="verified">Verified Only</option>
                <option value="corroborated">Corroborated</option>
              </select>
            </div>

            {/* Sort by */}
            <div>
              <label className="block text-slate-400 mb-1">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="recommendation_score">Recommendation Fit</option>
                <option value="deterministic_score">Deterministic Match</option>
                <option value="newest">Most Recent</option>
                <option value="salary">Highest Disclosed Salary</option>
              </select>
            </div>

            {/* Toggles */}
            <div className="flex flex-col justify-end gap-1.5">
              <label className="flex items-center gap-1.5 text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={salaryDisclosedOnly}
                  onChange={(e) => setSalaryDisclosedOnly(e.target.checked)}
                  className="rounded border-slate-600 text-indigo-500 h-3.5 w-3.5 bg-slate-900"
                />
                <span>Salary Disclosed</span>
              </label>

              <label className="flex items-center gap-1.5 text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={includeApplied}
                  onChange={(e) => setIncludeApplied(e.target.checked)}
                  className="rounded border-slate-600 text-indigo-500 h-3.5 w-3.5 bg-slate-900"
                />
                <span>Include Applied</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <svg className="w-10 h-10 animate-spin text-indigo-500 mb-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <p className="text-sm">Calculating grounded AI recommendations...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl bg-slate-800/20 p-8">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400 mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-slate-200">No matching recommendations found</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
              Try broadening your filters or click Refresh Recommendations to scan latest opportunities.
            </p>
            <button
              onClick={() => {
                setRoleFamily("");
                setWorkArrangement("all");
                setSeniority("all");
                setVerificationStatus("all");
                setSalaryDisclosedOnly(false);
                setSearchQuery("");
              }}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((job) => (
              <div
                key={job.job_id}
                className="p-5 rounded-2xl bg-slate-800/50 hover:bg-slate-800/80 border border-slate-700/60 hover:border-slate-600 transition-all flex flex-col md:flex-row gap-6 justify-between"
              >
                {/* Left: Job & Match Info */}
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className="font-semibold text-indigo-400 text-sm">
                      {job.company_name}
                    </span>

                    {/* Verification Badge */}
                    {job.verification_status === "verified" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                        <svg className="w-3 h-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        Verified Job
                      </span>
                    ) : job.verification_status === "corroborated" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-sky-500/10 text-sky-300 border border-sky-500/20">
                        Corroborated
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-700 text-slate-300">
                        Unverified
                      </span>
                    )}

                    {/* Freshness Badge */}
                    <span className="px-2 py-0.5 rounded text-[11px] bg-slate-700/70 text-slate-300">
                      {job.freshness === "recent"
                        ? "Active & Fresh"
                        : job.freshness === "due_for_review"
                        ? "Due for Review"
                        : "Listing Stale"}
                    </span>

                    {/* AI Assessment Badge */}
                    {job.ai_evaluated ? (
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                          job.ai_compatibility_rating === "strong"
                            ? "bg-purple-500/10 text-purple-300 border-purple-500/20"
                            : job.ai_compatibility_rating === "moderate"
                            ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
                            : "bg-amber-500/10 text-amber-300 border-amber-500/20"
                        }`}
                      >
                        AI: {job.ai_compatibility_rating?.toUpperCase() || "EVALUATED"}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-400 border border-slate-700">
                        AI: Not Evaluated
                      </span>
                    )}

                    {job.has_applied && (
                      <span className="px-2 py-0.5 rounded text-[11px] bg-blue-500/10 text-blue-300 border border-blue-500/20">
                        Applied
                      </span>
                    )}
                  </div>

                  <h2 className="text-lg md:text-xl font-bold text-slate-100 hover:text-indigo-300 transition-colors cursor-pointer" onClick={() => handleOpenDetailModal(job)}>
                    {job.title}
                  </h2>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1.5">
                    <span className="flex items-center gap-1">
                      <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {job.location_text}
                    </span>

                    <span className="capitalize px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {job.work_arrangement}
                    </span>

                    {job.seniority_level && (
                      <span className="capitalize px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {job.seniority_level}
                      </span>
                    )}

                    {/* Salary */}
                    {job.salary_disclosed ? (
                      <span className="text-emerald-400 font-medium">
                        {job.salary_currency || "INR"} {job.salary_min?.toLocaleString()}
                        {job.salary_max ? ` - ${job.salary_max.toLocaleString()}` : ""}
                        <span className="text-slate-500"> / {job.salary_period || "year"}</span>
                      </span>
                    ) : (
                      <span className="text-slate-500 italic" title="Undisclosed salary is never penalized in Nexora">
                        Salary Undisclosed (Neutral)
                      </span>
                    )}
                  </div>

                  {/* Grounded Explanation Preview */}
                  <div className="mt-3.5 pt-3 border-t border-slate-700/50 text-xs">
                    <p className="text-slate-300">
                      <span className="font-semibold text-emerald-400">Why it matches: </span>
                      {job.explanation.why_matches.skills && job.explanation.why_matches.skills.length > 0
                        ? job.explanation.why_matches.skills.slice(0, 3).join(", ")
                        : "High technical alignment with candidate background."}
                    </p>

                    {job.explanation.potential_gaps.missing_skills &&
                      job.explanation.potential_gaps.missing_skills.length > 0 && (
                        <p className="text-slate-400 mt-1">
                          <span className="font-semibold text-amber-400">Areas to emphasize: </span>
                          {job.explanation.potential_gaps.missing_skills.slice(0, 3).join(", ")}
                        </p>
                      )}
                  </div>
                </div>

                {/* Right: Scores & Actions */}
                <div className="flex md:flex-col items-center md:items-end justify-between md:justify-center gap-3 border-t md:border-t-0 md:border-l border-slate-700/60 pt-4 md:pt-0 md:pl-6 min-w-[220px]">
                  <div className="text-right">
                    <div className="flex items-baseline justify-end gap-1.5">
                      <span className="text-2xl font-black text-indigo-400">
                        {Math.round(job.recommendation_score)}
                      </span>
                      <span className="text-xs text-slate-400">/ 100</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Base Match: <span className="font-medium text-slate-200">{Math.round(job.deterministic_score)}%</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleSave(job)}
                      className={`p-2 rounded-lg border text-xs transition-colors ${
                        job.is_saved
                          ? "bg-indigo-600/20 text-indigo-300 border-indigo-500/40"
                          : "bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200"
                      }`}
                      title={job.is_saved ? "Saved opportunity" : "Save opportunity"}
                    >
                      <svg className="w-4 h-4" fill={job.is_saved ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                      </svg>
                    </button>

                    <button
                      onClick={() => handleDismiss(job)}
                      className="p-2 rounded-lg bg-slate-800 text-slate-500 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 text-xs transition-colors"
                      title="Dismiss recommendation"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>

                    <button
                      onClick={() => handleOpenDetailModal(job)}
                      className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-xs font-medium transition-colors"
                    >
                      View AI Insights
                    </button>
                  </div>

                  <div className="flex items-center gap-2 mt-1">
                    <Link
                      href={`/dashboard/resumes/tailor?job_id=${job.job_id}`}
                      className="text-xs text-indigo-400 hover:text-indigo-300 underline"
                    >
                      Tailor Resume
                    </Link>
                    <span className="text-slate-600">•</span>
                    <a
                      href={job.application_url || job.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1"
                    >
                      Official Page
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > pageSize && (
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-4 mt-8">
            <span className="text-xs text-slate-400">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} recommendations
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-xs text-slate-400 font-medium px-2">Page {page}</span>
              <button
                disabled={page * pageSize >= total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* AI Insights & Job Intelligence Slideout / Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full min-h-screen flex flex-col shadow-2xl">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex items-start justify-between bg-slate-900/90 sticky top-0 z-10">
              <div>
                <span className="text-xs text-indigo-400 font-semibold">{selectedJob.company_name}</span>
                <h2 className="text-xl font-bold text-slate-100 mt-0.5">{selectedJob.title}</h2>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                  <span>{selectedJob.location_text}</span>
                  <span>•</span>
                  <span className="capitalize">{selectedJob.work_arrangement}</span>
                  <span>•</span>
                  <span className="text-indigo-400 font-medium">Fit Score: {Math.round(selectedJob.recommendation_score)}/100</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-slate-400 hover:text-slate-100 p-2 rounded-lg bg-slate-800/80"
              >
                ✕
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex border-b border-slate-800 px-6 text-sm">
              <button
                onClick={() => setActiveModalTab("ai_match")}
                className={`py-3 px-4 font-medium border-b-2 transition-colors ${
                  activeModalTab === "ai_match"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                AI Match Assessment
              </button>
              <button
                onClick={() => setActiveModalTab("intelligence")}
                className={`py-3 px-4 font-medium border-b-2 transition-colors ${
                  activeModalTab === "intelligence"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Structured Requirements
              </button>
              <button
                onClick={() => setActiveModalTab("details")}
                className={`py-3 px-4 font-medium border-b-2 transition-colors ${
                  activeModalTab === "details"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Match Breakdown
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6">
              {modalLoading ? (
                <div className="text-center py-16 text-slate-400">
                  <svg className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Loading job intelligence...
                </div>
              ) : activeModalTab === "ai_match" ? (
                /* Tab 1: AI Match Assessment */
                <div className="space-y-6">
                  {selectedJobAI ? (
                    <>
                      {/* Rating & Executive Summary */}
                      <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
                            Compatibility Assessment
                          </span>
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                              selectedJobAI.compatibility_rating === "strong"
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : selectedJobAI.compatibility_rating === "moderate"
                                ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                                : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            }`}
                          >
                            {selectedJobAI.compatibility_rating.toUpperCase()} FIT
                          </span>
                        </div>
                        <p className="text-sm text-slate-200 leading-relaxed font-medium">
                          {selectedJobAI.fit_summary}
                        </p>
                        <p className="text-xs text-slate-400 mt-2 italic">
                          {selectedJobAI.recommendation_rationale}
                        </p>
                      </div>

                      {/* Strengths */}
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                          Evidence-Backed Strengths
                        </h4>
                        <div className="space-y-2">
                          {selectedJobAI.strengths.map((s, idx) => (
                            <div key={idx} className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs">
                              <p className="font-semibold text-emerald-300">{s.title}</p>
                              <p className="text-slate-300 mt-1">{s.description}</p>
                              {s.evidence_resume && (
                                <p className="text-[11px] text-slate-400 mt-1">
                                  <span className="font-medium text-slate-500">Resume Citation:</span> {s.evidence_resume}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Skill Gaps & Growth Areas */}
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                          Skill Gaps & Learning Opportunities
                        </h4>
                        <div className="space-y-2">
                          {selectedJobAI.skill_gaps.map((g, idx) => (
                            <div key={idx} className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs flex items-start justify-between gap-4">
                              <div>
                                <span className="font-semibold text-amber-300">{g.skill}</span>
                                <p className="text-slate-300 mt-0.5">{g.reason}</p>
                              </div>
                              <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700 capitalize flex-shrink-0">
                                {g.importance} priority
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Actionable Next Steps */}
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                          Recommended Action Plan
                        </h4>
                        <div className="space-y-2">
                          {selectedJobAI.next_steps.map((step, idx) => (
                            <div key={idx} className="p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20 text-xs flex items-center justify-between">
                              <div>
                                <span className="font-semibold text-indigo-300">{step.step}</span>
                                <p className="text-slate-300 mt-0.5">{step.action}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl p-6">
                      <div className="w-10 h-10 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-3">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-200">Run Personalized AI Compatibility Assessment</h4>
                      <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
                        Evaluates candidate projects, internships, and transferable skills against this requisition with grounded evidence citations.
                      </p>
                      <button
                        onClick={handleRunAIMatchEvaluation}
                        disabled={evaluatingAI}
                        className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
                      >
                        {evaluatingAI ? "Analyzing with AI..." : "Run AI Assessment Now"}
                      </button>
                    </div>
                  )}
                </div>
              ) : activeModalTab === "intelligence" ? (
                /* Tab 2: Structured Requirements */
                <div className="space-y-5 text-xs">
                  {selectedJobIntelligence ? (
                    <>
                      <div>
                        <h4 className="text-slate-400 font-semibold uppercase tracking-wider mb-2">Required Technical Skills</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedJobIntelligence.required_skills.map((sk, idx) => (
                            <span key={idx} className="px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
                              {sk}
                            </span>
                          ))}
                        </div>
                      </div>

                      {selectedJobIntelligence.preferred_skills.length > 0 && (
                        <div>
                          <h4 className="text-slate-400 font-semibold uppercase tracking-wider mb-2">Preferred / Bonus Skills</h4>
                          <div className="flex flex-wrap gap-1.5">
                            {selectedJobIntelligence.preferred_skills.map((sk, idx) => (
                              <span key={idx} className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                                {sk}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Experience and Education */}
                      <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700/50">
                        <div>
                          <span className="text-slate-500 block mb-0.5">Experience Expectation:</span>
                          <span className="text-slate-200 font-medium">
                            {selectedJobIntelligence.experience_requirements.description || "Early career"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 block mb-0.5">Seniority Level:</span>
                          <span className="text-slate-200 font-medium capitalize">
                            {selectedJobIntelligence.seniority_level}
                          </span>
                        </div>
                      </div>

                      {/* Responsibilities */}
                      {selectedJobIntelligence.responsibilities.length > 0 && (
                        <div>
                          <h4 className="text-slate-400 font-semibold uppercase tracking-wider mb-2">Responsibilities</h4>
                          <ul className="space-y-1.5 list-disc list-inside text-slate-300">
                            {selectedJobIntelligence.responsibilities.map((r, idx) => (
                              <li key={idx} className="leading-relaxed">{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Evidence Excerpts */}
                      {Object.keys(selectedJobIntelligence.evidence_excerpts).length > 0 && (
                        <div>
                          <h4 className="text-slate-400 font-semibold uppercase tracking-wider mb-2">Original Evidence Excerpts</h4>
                          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 italic space-y-1">
                            {Object.entries(selectedJobIntelligence.evidence_excerpts).map(([k, v]) => (
                              <p key={k}><strong className="text-slate-300 not-italic capitalize">{k}:</strong> &ldquo;{v}&rdquo;</p>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-slate-500">No structured intelligence extracted yet.</p>
                  )}
                </div>
              ) : (
                /* Tab 3: Match Breakdown */
                <div className="space-y-4 text-xs">
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">Technical Skills Fit:</span>
                      <span className="font-semibold text-slate-100">{selectedJob.score_breakdown.skills_score} / 100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">Role & Title Fit:</span>
                      <span className="font-semibold text-slate-100">{selectedJob.score_breakdown.role_score} / 100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">Experience & Seniority Fit:</span>
                      <span className="font-semibold text-slate-100">{selectedJob.score_breakdown.experience_score} / 100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">Location & Arrangement Fit:</span>
                      <span className="font-semibold text-slate-100">{selectedJob.score_breakdown.location_score} / 100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">Compensation Status:</span>
                      <span className="font-medium text-slate-400 capitalize">{selectedJob.score_breakdown.salary_status.replace("_", " ")}</span>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-slate-700">
                      <span className="text-indigo-400 font-semibold">Final Recommendation Score:</span>
                      <span className="font-bold text-indigo-300 text-sm">{Math.round(selectedJob.recommendation_score)} / 100</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between gap-3">
              <Link
                href={`/dashboard/resumes/tailor?job_id=${selectedJob.job_id}`}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors"
              >
                Tailor Resume for this Role
              </Link>

              <div className="flex items-center gap-2">
                <Link
                  href="/dashboard/applications"
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium"
                >
                  Track Application
                </Link>

                <a
                  href={selectedJob.application_url || selectedJob.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium"
                >
                  Open Official Listing ↗
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
