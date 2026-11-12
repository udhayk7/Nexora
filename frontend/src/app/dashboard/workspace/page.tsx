"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  Building2,
  CheckCircle2,
  Clock,
  Compass,
  ExternalLink,
  FileText,
  Globe,
  Layers,
  Loader2,
  MapPin,
  RefreshCw,
  Rocket,
  Settings,
  Sparkles,
  Target,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";

import {
  applicationsApi,
  ApplicationAnalytics,
  careerWorkflowApi,
  CareerWorkflowRunSummary,
  JobApplicationListResponse,
  JobApplicationSummary,
  matchingApi,
  UnifiedDiscoveryData,
  UnifiedOpportunityItem,
  WorkflowDashboardData,
} from "@/lib/api";

// ─── Helpers ────────────────────────────────────────────────────────────────

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function humanizeWorkflowType(wt: string): string {
  return wt
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function matchScoreClass(score?: number | null): string {
  if (!score) return "bg-zinc-700 text-zinc-300";
  if (score >= 80) return "bg-emerald-500/20 text-emerald-400";
  if (score >= 60) return "bg-yellow-500/20 text-yellow-400";
  return "bg-zinc-700 text-zinc-400";
}

function statusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (["completed", "applied", "shortlisted", "offer"].includes(s))
    return "bg-emerald-500/20 text-emerald-400";
  if (["running", "preparing", "interview", "assessment"].includes(s))
    return "bg-blue-500/20 text-blue-400";
  if (["pending", "interested"].includes(s))
    return "bg-zinc-700 text-zinc-300";
  if (["paused_awaiting_input"].includes(s))
    return "bg-yellow-500/20 text-yellow-400";
  if (["failed", "rejected", "withdrawn", "cancelled"].includes(s))
    return "bg-red-500/20 text-red-400";
  return "bg-zinc-700 text-zinc-300";
}

const SUBMITTED_STATUSES = new Set(["applied", "shortlisted", "assessment", "interview", "offer", "rejected", "withdrawn"]);

// ─── Skeleton ───────────────────────────────────────────────────────────────

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded bg-zinc-800 ${className}`} />
  );
}

// ─── Toast ──────────────────────────────────────────────────────────────────

interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  // ── data state ──
  const [dashboard, setDashboard] = useState<WorkflowDashboardData | null>(null);
  const [discovery, setDiscovery] = useState<UnifiedDiscoveryData | null>(null);
  const [analytics, setAnalytics] = useState<ApplicationAnalytics | null>(null);
  const [applications, setApplications] = useState<JobApplicationSummary[]>([]);

  // ── loading/error state ──
  const [loading, setLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // ── UI state ──
  const [showConfirm, setShowConfirm] = useState(false);
  const [runningMatch, setRunningMatch] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [toastCounter, setToastCounter] = useState(0);
  const [opportunityPage, setOpportunityPage] = useState(1);
  const OPPS_PER_PAGE = 20;

  // ── toast helpers ──
  const addToast = useCallback((message: string, type: "success" | "error") => {
    const id = toastCounter + 1;
    setToastCounter((c) => c + 1);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, [toastCounter]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ── data fetch ──
  const fetchAll = useCallback(async () => {
    setLoading(true);
    setDashboardError(null);
    setDiscoveryError(null);

    const [dashRes, discRes, analyticsRes, appsRes] = await Promise.allSettled([
      careerWorkflowApi.getDashboard(),
      careerWorkflowApi.getDiscovery(),
      applicationsApi.getAnalytics(),
      applicationsApi.listApplications({ limit: 50 }),
    ]);

    if (dashRes.status === "fulfilled") {
      setDashboard(dashRes.value);
    } else {
      setDashboardError("Failed to load dashboard data. Please retry.");
    }

    if (discRes.status === "fulfilled") {
      setDiscovery(discRes.value);
    } else {
      setDiscoveryError("Failed to load opportunities.");
    }

    if (analyticsRes.status === "fulfilled") {
      setAnalytics(analyticsRes.value);
    }

    if (appsRes.status === "fulfilled") {
      const resp = appsRes.value as JobApplicationListResponse;
      setApplications(resp.items ?? []);
    }

    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── job search ──
  const handleStartJobSearch = async () => {
    setShowConfirm(false);
    setRunningMatch(true);
    try {
      await matchingApi.runMatches();
      addToast("Job matching started! Check back in a few minutes.", "success");
    } catch {
      addToast("Failed to start job matching. Please try again.", "error");
    } finally {
      setRunningMatch(false);
    }
  };

  // ── derived data ──
  const inProgressApps = applications.filter(
    (a) => !SUBMITTED_STATUSES.has(a.status)
  );

  const paginatedOpps = (discovery?.opportunities ?? []).slice(
    0,
    opportunityPage * OPPS_PER_PAGE
  );
  const hasMoreOpps =
    (discovery?.opportunities?.length ?? 0) > opportunityPage * OPPS_PER_PAGE;

  // ── funnel counts ──
  const funnelStages = [
    {
      label: "Discovered",
      count: dashboard?.new_opportunities_count ?? 0,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10",
    },
    {
      label: "Matched",
      count: analytics?.status_distribution?.["interested"] ?? 0,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
    },
    {
      label: "Preparing",
      count: analytics?.status_distribution?.["preparing"] ?? 0,
      color: "text-cyan-400",
      bg: "bg-cyan-500/10",
    },
    {
      label: "Awaiting Approval",
      count: dashboard?.applications_awaiting_approval_count ?? 0,
      color: "text-yellow-400",
      bg: "bg-yellow-500/10",
    },
    {
      label: "Submitted",
      count: dashboard?.applications_submitted_count ?? 0,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      label: "Under Review",
      count: analytics?.status_distribution?.["shortlisted"] ?? 0,
      color: "text-lime-400",
      bg: "bg-lime-500/10",
    },
    {
      label: "Interview",
      count: analytics?.status_distribution?.["interview"] ?? 0,
      color: "text-orange-400",
      bg: "bg-orange-500/10",
    },
    {
      label: "Offer",
      count: analytics?.status_distribution?.["offer"] ?? 0,
      color: "text-pink-400",
      bg: "bg-pink-500/10",
    },
  ];

  const quickLinks = [
    {
      label: "Resume Studio",
      href: "/dashboard/resumes",
      icon: FileText,
      desc: "Manage & tailor resumes",
    },
    {
      label: "Career Workflow",
      href: "/dashboard/career-workflow",
      icon: Layers,
      desc: "End-to-end job pipeline",
    },
    {
      label: "Job Discovery",
      href: "/dashboard/job-discovery",
      icon: Compass,
      desc: "Browse matched jobs",
    },
    {
      label: "Application Manager",
      href: "/dashboard/applications",
      icon: Briefcase,
      desc: "Track all applications",
    },
    {
      label: "Integration Settings",
      href: "/dashboard/integrations",
      icon: Settings,
      desc: "Connect your accounts",
    },
  ];

  // ────────────────────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* ── Toast Notifications ── */}
        <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium pointer-events-auto transition-all
                ${t.type === "success"
                  ? "bg-emerald-900 border border-emerald-700 text-emerald-200"
                  : "bg-red-900 border border-red-700 text-red-200"}`}
            >
              {t.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              )}
              <span>{t.message}</span>
              <button
                onClick={() => removeToast(t.id)}
                className="ml-auto text-current opacity-70 hover:opacity-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {/* ── Confirmation Dialog ── */}
        {showConfirm && (
          <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-full bg-indigo-500/20">
                  <Sparkles className="w-5 h-5 text-indigo-400" />
                </div>
                <h2 className="text-lg font-semibold">Start AI Job Search?</h2>
              </div>
              <p className="text-sm text-zinc-400 mb-6">
                This will run AI matching to find new opportunities. Continue?
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowConfirm(false)}
                  className="px-4 py-2 text-sm rounded-lg border border-zinc-700 hover:bg-zinc-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleStartJobSearch}
                  className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-white transition-colors"
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Header ── */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="p-1.5 rounded-lg bg-indigo-500/20">
                <Target className="w-5 h-5 text-indigo-400" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
                Job Search Workspace
              </h1>
            </div>
            <p className="text-sm text-zinc-400">Your AI-powered career command center</p>
            {lastUpdated && (
              <p className="text-xs text-zinc-500 mt-1">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          <button
            onClick={fetchAll}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-zinc-700 bg-zinc-900 hover:bg-zinc-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </header>

        {/* ── Dashboard Error Banner ── */}
        {dashboardError && (
          <div className="flex items-center gap-3 p-4 rounded-lg border border-red-700 bg-red-950 text-red-300 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{dashboardError}</span>
            <button
              onClick={fetchAll}
              className="ml-auto text-red-300 hover:text-red-100 underline underline-offset-2"
            >
              Retry
            </button>
          </div>
        )}

        {/* ── Primary Action CTA ── */}
        <section className="relative overflow-hidden rounded-2xl border border-indigo-700/40 bg-gradient-to-br from-indigo-950 via-zinc-900 to-zinc-900 p-6 sm:p-8">
          <div className="absolute inset-0 opacity-5 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-indigo-400 via-transparent to-transparent pointer-events-none" />
          <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-4 justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400 mb-1">
                AI-Powered
              </p>
              <h2 className="text-xl font-bold mb-1">Ready to find your next role?</h2>
              <p className="text-sm text-zinc-400">
                Let Nexora&apos;s AI scan thousands of opportunities and match the best ones for you.
              </p>
            </div>
            <button
              onClick={() => setShowConfirm(true)}
              disabled={runningMatch}
              className="shrink-0 inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 font-semibold text-white text-sm shadow-lg shadow-indigo-900/40 transition-all disabled:opacity-60"
            >
              {runningMatch ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Rocket className="w-4 h-4" />
              )}
              START AUTOMATED JOB SEARCH
            </button>
          </div>
        </section>

        {/* ── Pipeline Funnel Stats Bar ── */}
        <section>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-widest mb-3">
            Pipeline Funnel
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {funnelStages.map((stage) => (
              <div
                key={stage.label}
                className={`rounded-xl border border-zinc-800 p-3 text-center ${stage.bg}`}
              >
                {loading ? (
                  <Skeleton className="h-6 w-10 mx-auto mb-1" />
                ) : (
                  <p className={`text-2xl font-bold ${stage.color}`}>{stage.count}</p>
                )}
                <p className="text-xs text-zinc-400 leading-tight mt-1">{stage.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Opportunities Section ── */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-semibold">Discovered Opportunities</h2>
              {!loading && discovery && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-500/20 text-indigo-300">
                  {discovery.total_active_jobs ?? discovery.opportunities?.length ?? 0}
                </span>
              )}
            </div>
            <Link
              href="/dashboard/career-workflow"
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
            >
              View all in Career Workflow <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {discoveryError && (
            <div className="flex items-center gap-3 p-3 rounded-lg border border-red-800 bg-red-950 text-red-300 text-sm mb-4">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {discoveryError}
            </div>
          )}

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-full" />
                  <div className="flex gap-2 pt-2">
                    <Skeleton className="h-8 flex-1" />
                    <Skeleton className="h-8 w-20" />
                  </div>
                </div>
              ))}
            </div>
          ) : !discovery || discovery.opportunities?.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 rounded-xl border border-zinc-800 bg-zinc-900/50 text-center">
              <div className="p-3 rounded-full bg-zinc-800 mb-4">
                <Compass className="w-8 h-8 text-zinc-500" />
              </div>
              <p className="font-semibold text-zinc-300 mb-1">No opportunities yet</p>
              <p className="text-sm text-zinc-500 mb-4">
                Run AI matching above to discover tailored job opportunities.
              </p>
              <button
                onClick={() => setShowConfirm(true)}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 font-medium text-white transition-colors"
              >
                <Sparkles className="w-4 h-4" /> Start Matching
              </button>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {paginatedOpps.map((opp: UnifiedOpportunityItem) => (
                  <OpportunityCard key={opp.job_id} opp={opp} />
                ))}
              </div>
              {hasMoreOpps && (
                <div className="flex justify-center mt-6">
                  <button
                    onClick={() => setOpportunityPage((p) => p + 1)}
                    className="inline-flex items-center gap-2 px-5 py-2 text-sm rounded-lg border border-zinc-700 hover:bg-zinc-800 transition-colors"
                  >
                    Load more
                  </button>
                </div>
              )}
            </>
          )}
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* ── Applications In Progress ── */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Briefcase className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-semibold">Applications In Progress</h2>
              {!loading && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-cyan-500/20 text-cyan-300">
                  {inProgressApps.length}
                </span>
              )}
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                    <Skeleton className="h-4 w-3/4 mb-2" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                ))}
              </div>
            ) : inProgressApps.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 text-center">
                <p className="text-sm text-zinc-400">
                  No applications in progress. Start by preparing an application from the{" "}
                  <span className="text-indigo-400 font-medium">Opportunities</span> section above.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {inProgressApps.slice(0, 10).map((app) => (
                  <ApplicationRow key={app.id} app={app} />
                ))}
                {inProgressApps.length > 10 && (
                  <Link
                    href="/dashboard/applications"
                    className="block text-center text-xs text-indigo-400 hover:text-indigo-300 mt-2"
                  >
                    View all {inProgressApps.length} applications →
                  </Link>
                )}
              </div>
            )}
          </section>

          {/* ── Recent Activity ── */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-orange-400" />
              <h2 className="text-lg font-semibold">Recent Activity</h2>
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                    <Skeleton className="h-4 w-2/3 mb-2" />
                    <Skeleton className="h-2 w-full rounded-full" />
                  </div>
                ))}
              </div>
            ) : !dashboard?.recent_workflow_runs?.length ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 text-center">
                <p className="text-sm text-zinc-500">No recent workflow activity.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {dashboard.recent_workflow_runs.slice(0, 8).map((run) => (
                  <WorkflowRunRow key={run.id} run={run} />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* ── Quick Links ── */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-yellow-400" />
            <h2 className="text-lg font-semibold">Quick Links</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {quickLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className="group flex flex-col items-start gap-2 p-4 rounded-xl border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 hover:border-indigo-700/50 transition-all"
                >
                  <div className="p-2 rounded-lg bg-zinc-800 group-hover:bg-indigo-500/20 transition-colors">
                    <Icon className="w-4 h-4 text-zinc-400 group-hover:text-indigo-400 transition-colors" />
                  </div>
                  <div>
                    <p className="text-sm font-medium leading-tight">{link.label}</p>
                    <p className="text-xs text-zinc-500 mt-0.5 leading-tight">{link.desc}</p>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function OpportunityCard({ opp }: { opp: UnifiedOpportunityItem }) {
  return (
    <div className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-all p-4 gap-3">
      {/* Title + Company */}
      <div>
        <h3 className="font-semibold text-sm leading-snug line-clamp-2">{opp.title}</h3>
        <div className="flex items-center gap-1.5 mt-1 text-xs text-zinc-400">
          <Building2 className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{opp.company_name}</span>
        </div>
        {opp.location_text && (
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-zinc-500">
            <MapPin className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">{opp.location_text}</span>
          </div>
        )}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        {opp.match_score != null && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${matchScoreClass(opp.match_score)}`}>
            Score: {Math.round(opp.match_score)}%
          </span>
        )}
        {opp.verification_status && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-700 text-zinc-300">
            {opp.verification_status}
          </span>
        )}
        {opp.source_provenance && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400">
            <Globe className="w-3 h-3 mr-1" />
            {opp.source_provenance}
          </span>
        )}
        {opp.work_arrangement && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400">
            {opp.work_arrangement}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-auto">
        <Link
          href={`/dashboard/career-workflow?job_id=${opp.job_id}`}
          className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          Prepare Application
        </Link>
        {opp.application_url && (
          <a
            href={opp.application_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-zinc-700 hover:bg-zinc-800 text-zinc-300 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View
          </a>
        )}
      </div>
    </div>
  );
}

function ApplicationRow({ app }: { app: JobApplicationSummary }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900 hover:bg-zinc-800/60 transition-colors p-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{app.title}</p>
        <p className="text-xs text-zinc-500 truncate">{app.company_name}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass(app.status)}`}>
          {app.status}
        </span>
        <span className="text-xs text-zinc-500 hidden sm:block">
          {relativeTime(app.updated_at)}
        </span>
        <Link
          href="/dashboard/career-workflow"
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border border-zinc-700 hover:bg-zinc-700 text-zinc-300 transition-colors"
        >
          <Clock className="w-3 h-3" />
          Continue
        </Link>
      </div>
    </div>
  );
}

function WorkflowRunRow({ run }: { run: CareerWorkflowRunSummary }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {humanizeWorkflowType(run.workflow_type)}
          </p>
          {run.current_step && (
            <p className="text-xs text-zinc-500 truncate mt-0.5">{run.current_step}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass(run.status)}`}>
            {run.status.replace(/_/g, " ")}
          </span>
          <span className="text-xs text-zinc-500">{relativeTime(run.created_at)}</span>
        </div>
      </div>
      {/* Progress bar */}
      <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500 transition-all"
          style={{ width: `${Math.min(100, run.progress_pct ?? 0)}%` }}
        />
      </div>
      <p className="text-right text-xs text-zinc-600 mt-1">{run.progress_pct ?? 0}%</p>
    </div>
  );
}
