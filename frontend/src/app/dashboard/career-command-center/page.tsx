"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Award,
  BarChart3,
  Bookmark,
  Bot,
  Brain,
  Briefcase,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  ExternalLink,
  FileText,
  Filter,
  GraduationCap,
  HelpCircle,
  Layers,
  Lightbulb,
  ListFilter,
  Loader2,
  MapPin,
  RefreshCw,
  SendHorizontal,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  UserCheck,
  Users,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  careerCommandCenterApi,
  CareerFunnelResponse,
  CareerGoalsResponse,
  CareerGoalsUpdate,
  CareerOverviewKPIs,
  CareerReadinessResponse,
  PerformanceAnalyticsResponse,
  RecommendationsResponse,
} from "@/lib/api";

export default function CareerCommandCenterPage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Loading Career Command Center...</p>
        </div>
      }
    >
      <CareerCommandCenterContent />
    </React.Suspense>
  );
}

function CareerCommandCenterContent() {
  const { user, isLoading: authLoading } = useAuth();

  // State
  const [dateRange, setDateRange] = useState<"all" | "90d" | "30d">("all");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Data
  const [overview, setOverview] = useState<CareerOverviewKPIs | null>(null);
  const [funnel, setFunnel] = useState<CareerFunnelResponse | null>(null);
  const [readiness, setReadiness] = useState<CareerReadinessResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [analytics, setAnalytics] = useState<PerformanceAnalyticsResponse | null>(null);
  const [goals, setGoals] = useState<CareerGoalsResponse | null>(null);

  // UI State
  const [activeTab, setActiveTab] = useState<"overview" | "readiness" | "analytics">("overview");
  const [showGoalsModal, setShowGoalsModal] = useState(false);
  const [showFormulaDetails, setShowFormulaDetails] = useState(false);
  const [activityView, setActivityView] = useState<"weekly" | "monthly">("weekly");

  // Fetch all dashboard data
  const loadDashboardData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setErrorMessage(null);

    try {
      const [ovData, fnData, rdData, rcData, anData, glData] = await Promise.all([
        careerCommandCenterApi.getOverview(dateRange),
        careerCommandCenterApi.getFunnel(),
        careerCommandCenterApi.getReadiness(),
        careerCommandCenterApi.getRecommendations(),
        careerCommandCenterApi.getAnalytics(dateRange),
        careerCommandCenterApi.getGoals(),
      ]);

      setOverview(ovData);
      setFunnel(fnData);
      setReadiness(rdData);
      setRecommendations(rcData);
      setAnalytics(anData);
      setGoals(glData);
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to load Career Command Center metrics.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [dateRange]);

  useEffect(() => {
    if (!authLoading && user) {
      loadDashboardData();
    }
  }, [authLoading, user, loadDashboardData]);

  if (authLoading || (loading && !overview)) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center p-12 text-center min-h-[500px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Synthesizing career intelligence data...</p>
      </main>
    );
  }

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
      {/* Top Header & Controls */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-border mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary">
              <Sparkles className="w-3.5 h-3.5" /> Unified Intelligence
            </span>
            <span className="text-xs text-muted-foreground">• Live Pipeline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Career Command Center
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Consolidated overview of job discovery, applications, career readiness, and next actions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          {/* Date Filter */}
          <div className="inline-flex items-center rounded-lg border border-border bg-card p-0.5 text-xs font-medium">
            <button
              onClick={() => setDateRange("30d")}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                dateRange === "30d"
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              30 Days
            </button>
            <button
              onClick={() => setDateRange("90d")}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                dateRange === "90d"
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              90 Days
            </button>
            <button
              onClick={() => setDateRange("all")}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                dateRange === "all"
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All Time
            </button>
          </div>

          {/* Goals Settings Button */}
          <button
            onClick={() => setShowGoalsModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-card hover:bg-secondary text-foreground transition-colors shadow-xs"
          >
            <Settings className="w-3.5 h-3.5 text-muted-foreground" />
            Career Goals
          </button>

          {/* Refresh Button */}
          <button
            onClick={() => loadDashboardData(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors shadow-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-primary" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      {/* Error alert if any */}
      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Unable to load all dashboard components</p>
            <p className="text-xs mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Weekly Progress Banner */}
      {overview && (
        <div className="mb-6 p-4 rounded-xl border border-border bg-gradient-to-r from-card via-card to-secondary/30 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Weekly Application Target
                </span>
                <span className="px-2 py-0.2 rounded-full text-xs font-medium bg-secondary text-foreground">
                  {overview.applications_this_week} of {overview.weekly_application_target} submitted
                </span>
              </div>
              <p className="text-sm text-foreground font-medium mt-0.5">
                {overview.target_progress_percentage >= 100
                  ? "🎉 Weekly target reached! Keep the momentum going or review upcoming interviews."
                  : `${overview.weekly_application_target - overview.applications_this_week} more applications needed to hit this week's target.`}
              </p>
            </div>
          </div>

          <div className="w-full sm:w-56 shrink-0">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-semibold text-primary">
                {overview.target_progress_percentage}%
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, overview.target_progress_percentage)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-border mb-6 space-x-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "overview"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          Overview & Funnel
        </button>
        <button
          onClick={() => setActiveTab("readiness")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "readiness"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Brain className="w-4 h-4" />
          Career Readiness & Skills
          {readiness && (
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-primary/10 text-primary">
              {readiness.readiness_score}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("analytics")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "analytics"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Search Analytics
        </button>
      </div>

      {/* TAB 1: OVERVIEW & FUNNEL */}
      {activeTab === "overview" && (
        <div className="space-y-8">
          {/* Career KPIs Grid */}
          {overview && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <BarChart3 className="w-4 h-4 text-primary" /> Key Career Indicators
                </h2>
                <span className="text-xs text-muted-foreground">Derived from actual database records</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
                {/* 1. Total Discovered */}
                <div className="p-4 rounded-xl border border-border bg-card shadow-xs">
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium">Discovered Jobs</span>
                    <Compass className="w-4 h-4 text-teal-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.total_discovered_jobs}</p>
                  <p className="text-xs text-muted-foreground mt-1">Platform listings</p>
                </div>

                {/* 2. Active Verified */}
                <div className="p-4 rounded-xl border border-border bg-card shadow-xs">
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium">Verified Active</span>
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.active_verified_jobs}</p>
                  <p className="text-xs text-muted-foreground mt-1">SSRF-checked legitimate</p>
                </div>

                {/* 3. Strong Job Matches */}
                <Link
                  href="/dashboard/matches"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      Strong Matches
                    </span>
                    <Sparkles className="w-4 h-4 text-amber-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.strong_job_matches}</p>
                  <p className="text-xs text-primary mt-1 font-medium flex items-center gap-0.5">
                    Score ≥ 75% <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </p>
                </Link>

                {/* 4. Saved Opportunities */}
                <Link
                  href="/dashboard/matches"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      Saved Jobs
                    </span>
                    <Bookmark className="w-4 h-4 text-indigo-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.saved_opportunities}</p>
                  <p className="text-xs text-muted-foreground mt-1">Bookmarked or interested</p>
                </Link>

                {/* 5. Applications In Progress */}
                <Link
                  href="/dashboard/applications"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      In Progress
                    </span>
                    <Layers className="w-4 h-4 text-blue-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.applications_in_progress}</p>
                  <p className="text-xs text-muted-foreground mt-1">Preparing, test, or interview</p>
                </Link>

                {/* 6. Applications Submitted */}
                <Link
                  href="/dashboard/applications"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      Submitted
                    </span>
                    <SendHorizontal className="w-4 h-4 text-violet-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.applications_submitted}</p>
                  <p className="text-xs text-muted-foreground mt-1">Confirmed applications</p>
                </Link>

                {/* 7. Interviews Scheduled */}
                <Link
                  href="/dashboard/interview-prep"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      Interviews
                    </span>
                    <Users className="w-4 h-4 text-purple-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.interviews_scheduled}</p>
                  <p className="text-xs text-muted-foreground mt-1">Active interview stages</p>
                </Link>

                {/* 8. Offers Received */}
                <div className="p-4 rounded-xl border border-border bg-card shadow-xs">
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium">Offers</span>
                    <Award className="w-4 h-4 text-amber-500" />
                  </div>
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                    {overview.offers_received}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Formal offers</p>
                </div>

                {/* 9. Resume Versions */}
                <Link
                  href="/dashboard/resumes"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      Resume Versions
                    </span>
                    <FileText className="w-4 h-4 text-slate-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{overview.resume_versions_created}</p>
                  <p className="text-xs text-muted-foreground mt-1">Base & tailored assets</p>
                </Link>

                {/* 10. Interview Prep Sessions */}
                <Link
                  href="/dashboard/interview-prep"
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs group"
                >
                  <div className="flex items-center justify-between text-muted-foreground mb-2">
                    <span className="text-xs font-medium group-hover:text-primary transition-colors">
                      Mock Coaching
                    </span>
                    <GraduationCap className="w-4 h-4 text-sky-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">
                    {overview.interview_prep_sessions_completed}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Completed mock sessions</p>
                </Link>
              </div>
            </section>
          )}

          {/* Recommended Next Actions */}
          {recommendations && recommendations.actions.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Lightbulb className="w-4 h-4 text-amber-500" /> Recommended Next Actions
                </h2>
                <span className="text-xs text-muted-foreground">Prioritized deterministically</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {recommendations.actions.map((act) => {
                  const isHigh = act.priority === "high";
                  const isMedium = act.priority === "medium";
                  return (
                    <div
                      key={act.id}
                      className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-all flex flex-col justify-between shadow-xs"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wider ${
                              isHigh
                                ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
                                : isMedium
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                                : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
                            }`}
                          >
                            {act.priority} priority
                          </span>
                          <span className="text-xs text-muted-foreground font-mono">
                            {act.action_type.replace("_", " ")}
                          </span>
                        </div>
                        <h3 className="text-sm font-semibold text-foreground">{act.title}</h3>
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                          {act.reason}
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-end">
                        <Link
                          href={act.navigation_url}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
                        >
                          Take Action <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Visual Application Funnel */}
          {funnel && (
            <section className="p-6 rounded-xl border border-border bg-card shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
                <div>
                  <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-primary" /> Application Funnel Progression
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Conversion tracking across all pipeline stages based strictly on verified status transitions.
                  </p>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <span className="w-2 h-2 rounded-full bg-blue-500" /> Active ({funnel.outcomes.active})
                  </span>
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" /> Offered ({funnel.outcomes.offered})
                  </span>
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <span className="w-2 h-2 rounded-full bg-rose-500" /> Rejected ({funnel.outcomes.rejected})
                  </span>
                </div>
              </div>

              {/* Funnel Stage Steps */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3 mb-6">
                {funnel.stages.map((stg, idx) => (
                  <div
                    key={stg.stage_id}
                    className="p-3.5 rounded-lg border border-border bg-secondary/30 flex flex-col justify-between"
                  >
                    <div>
                      <span className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Stage {idx + 1}
                      </span>
                      <h3 className="text-xs font-semibold text-foreground mt-0.5 truncate" title={stg.label}>
                        {stg.label}
                      </h3>
                      <p className="text-xl font-bold text-foreground mt-2">{stg.count}</p>
                    </div>

                    <div className="mt-3 pt-2 border-t border-border/50 text-2xs space-y-1">
                      {stg.conversion_from_previous_percentage !== null &&
                        stg.conversion_from_previous_percentage !== undefined && (
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Conversion</span>
                          <span
                            className={`font-semibold ${
                              stg.conversion_from_previous_percentage > 0
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-muted-foreground"
                            }`}
                          >
                            {stg.conversion_from_previous_percentage}%
                          </span>
                        </div>
                      )}
                      {stg.drop_off_count > 0 && (
                        <div className="flex items-center justify-between text-muted-foreground">
                          <span>Drop-off</span>
                          <span>-{stg.drop_off_count}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Methodology disclaimer */}
              <div className="p-3 rounded-lg bg-secondary/50 border border-border/60 text-2xs text-muted-foreground flex items-center gap-2">
                <HelpCircle className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                <span>{funnel.methodology_notes}</span>
              </div>
            </section>
          )}
        </div>
      )}

      {/* TAB 2: CAREER READINESS & SKILLS */}
      {activeTab === "readiness" && readiness && (
        <div className="space-y-8">
          {/* Readiness Score Card */}
          <section className="p-6 rounded-xl border border-border bg-card shadow-xs">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-border">
              <div className="flex items-center gap-4">
                <div className="relative flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 border-4 border-primary/20 shrink-0">
                  <span className="text-2xl font-black text-primary">
                    {readiness.readiness_score}
                  </span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-foreground">Deterministic Career Readiness</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                      {readiness.target_role_alignment.alignment_tier} Alignment
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                    Evaluated from supported resume evidence, active market skill frequencies, and completed mock interview evaluations.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowFormulaDetails(!showFormulaDetails)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                {showFormulaDetails ? "Hide Formula" : "View Score Methodology"}
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showFormulaDetails ? "rotate-180" : ""}`} />
              </button>
            </div>

            {/* Formula details drawer */}
            {showFormulaDetails && (
              <div className="mt-4 p-4 rounded-lg bg-secondary/50 border border-border/80 text-xs space-y-2">
                <p className="font-semibold text-foreground">Formula Definition:</p>
                <code className="block p-2 rounded-sm bg-background font-mono text-xs text-primary">
                  {readiness.readiness_score_formula}
                </code>
                <p className="text-muted-foreground mt-2">
                  <strong className="text-foreground">Transparency & Limitations:</strong> {readiness.score_limitations}
                </p>
              </div>
            )}

            {/* Sub-score Breakdown */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
              <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
                <div className="text-xs text-muted-foreground mb-1">Skills Alignment (40%)</div>
                <div className="text-lg font-bold text-foreground">
                  {readiness.score_breakdown.skills_alignment}%
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
                <div className="text-xs text-muted-foreground mb-1">Job Match Alignment (30%)</div>
                <div className="text-lg font-bold text-foreground">
                  {readiness.score_breakdown.matching_alignment}%
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
                <div className="text-xs text-muted-foreground mb-1">Interview Readiness (20%)</div>
                <div className="text-lg font-bold text-foreground">
                  {readiness.score_breakdown.interview_readiness}%
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
                <div className="text-xs text-muted-foreground mb-1">Evidence Depth (10%)</div>
                <div className="text-lg font-bold text-foreground">
                  {readiness.score_breakdown.resume_evidence_depth}%
                </div>
              </div>
            </div>
          </section>

          {/* Skills Comparison: Demonstrated vs Market Demanded vs Gaps */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 1. Demonstrated Skills */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  Demonstrated Skills ({readiness.demonstrated_skills.length})
                </h3>
                <span className="text-2xs text-muted-foreground">Backed by resume</span>
              </div>
              {readiness.demonstrated_skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {readiness.demonstrated_skills.map((s) => (
                    <span
                      key={s.skill}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
                    >
                      {s.skill}
                      <span className="text-2xs opacity-75 font-mono">({s.evidence_count})</span>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  No demonstrated skills found. Upload and parse your resume in Resume Studio.
                </p>
              )}
            </div>

            {/* 2. Market Demand Skills */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-primary" />
                  Market Demand ({readiness.frequently_requested_skills.length})
                </h3>
                <span className="text-2xs text-muted-foreground">Target jobs</span>
              </div>
              {readiness.frequently_requested_skills.length > 0 ? (
                <div className="space-y-2">
                  {readiness.frequently_requested_skills.map((s) => (
                    <div
                      key={s.skill}
                      className="flex items-center justify-between text-xs p-2 rounded-md bg-secondary/30"
                    >
                      <div className="flex items-center gap-2">
                        {s.is_demonstrated_by_user ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                        ) : (
                          <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                        )}
                        <span className="font-medium text-foreground">{s.skill}</span>
                      </div>
                      <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
                        {s.frequency} mentions
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  Set target role families in Career Goals to analyze market demand skills.
                </p>
              )}
            </div>

            {/* 3. Skill Gaps */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  Skill Gaps ({readiness.missing_or_underrepresented_skills.length})
                </h3>
                <span className="text-2xs text-muted-foreground">Actionable advice</span>
              </div>
              {readiness.missing_or_underrepresented_skills.length > 0 ? (
                <div className="space-y-2.5">
                  {readiness.missing_or_underrepresented_skills.map((gap) => (
                    <div
                      key={gap.skill}
                      className="p-2.5 rounded-lg border border-border bg-secondary/20 text-xs"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-foreground">{gap.skill}</span>
                        <span className="text-2xs text-amber-600 dark:text-amber-400 font-medium">
                          {gap.market_demand_frequency} active requests
                        </span>
                      </div>
                      <p className="text-2xs text-muted-foreground leading-relaxed">
                        {gap.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
                  <p className="text-xs font-medium text-foreground">No critical skill gaps identified</p>
                  <p className="text-2xs text-muted-foreground mt-0.5">
                    Your demonstrated skills align well with top target role requests.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Mock Interview Evaluation Performance */}
          <section className="p-6 rounded-xl border border-border bg-card shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-primary" /> Interview Coaching & Rubric Performance
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Aggregated scores across 6 rubric dimensions evaluated by AI interview coach.
                </p>
              </div>
              <Link
                href="/dashboard/interview-prep"
                className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
              >
                Open Coach <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            {readiness.interview_performance.evaluated_answers_count > 0 ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                  {Object.entries(readiness.interview_performance.rubric_averages).map(([k, v]) => (
                    <div key={k} className="p-3 rounded-lg bg-secondary/30 border border-border/50 text-center">
                      <span className="text-2xs font-semibold uppercase text-muted-foreground block truncate">
                        {k.replace("_", " ")}
                      </span>
                      <span className="text-lg font-bold text-foreground mt-1 block">{v}%</span>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div className="p-3.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                    <h4 className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1.5 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Strengths Identified
                    </h4>
                    {readiness.interview_performance.top_strengths.length > 0 ? (
                      <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                        {readiness.interview_performance.top_strengths.map((str, idx) => (
                          <li key={idx}>{str}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground">Keep answering questions to reveal strengths.</p>
                    )}
                  </div>

                  <div className="p-3.5 rounded-lg bg-amber-500/5 border border-amber-500/20">
                    <h4 className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1.5 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" /> Areas for Improvement
                    </h4>
                    {readiness.interview_performance.areas_for_improvement.length > 0 ? (
                      <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                        {readiness.interview_performance.areas_for_improvement.map((imp, idx) => (
                          <li key={idx}>{imp}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground">No major weaknesses identified yet.</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 rounded-lg bg-secondary/20 border border-dashed border-border text-center">
                <GraduationCap className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-60" />
                <p className="text-sm font-semibold text-foreground">No Mock Interviews Evaluated Yet</p>
                <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1 mb-4">
                  Practice tailored mock questions and receive multi-dimensional rubric feedback to strengthen your readiness.
                </p>
                <Link
                  href="/dashboard/interview-prep"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
                >
                  Start Mock Interview <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            )}
          </section>
        </div>
      )}

      {/* TAB 3: SEARCH ANALYTICS */}
      {activeTab === "analytics" && analytics && (
        <div className="space-y-8">
          {/* Conversion Rates & Safeguards */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Interview Conversion Rate
                </span>
                <Users className="w-4 h-4 text-purple-500" />
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-3xl font-black text-foreground">
                  {analytics.interview_conversion_rate !== null
                    ? `${analytics.interview_conversion_rate}%`
                    : "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({analytics.interview_sample_size} submitted applications)
                </span>
              </div>
              {!analytics.is_interview_sample_meaningful && (
                <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-2xs text-amber-700 dark:text-amber-300 flex items-center gap-2">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Sample size &lt; 5 applications. Rate is indicative and requires more data.</span>
                </div>
              )}
            </div>

            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Offer Conversion Rate
                </span>
                <Award className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-3xl font-black text-emerald-600 dark:text-emerald-400">
                  {analytics.offer_conversion_rate !== null
                    ? `${analytics.offer_conversion_rate}%`
                    : "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({analytics.offer_sample_size} submitted applications)
                </span>
              </div>
              {!analytics.is_offer_sample_meaningful && (
                <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-2xs text-amber-700 dark:text-amber-300 flex items-center gap-2">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Sample size &lt; 5 applications. Rate is indicative and requires more data.</span>
                </div>
              )}
            </div>
          </section>

          {/* Time Series Activity Chart */}
          <section className="p-6 rounded-xl border border-border bg-card shadow-xs">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Clock className="w-4 h-4 text-primary" /> Application Activity Over Time
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Track weekly and monthly application pacing and interview events.
                </p>
              </div>

              <div className="inline-flex items-center rounded-lg border border-border bg-secondary p-0.5 text-xs font-medium">
                <button
                  onClick={() => setActivityView("weekly")}
                  className={`px-3 py-1 rounded-md transition-colors ${
                    activityView === "weekly"
                      ? "bg-card text-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Weekly
                </button>
                <button
                  onClick={() => setActivityView("monthly")}
                  className={`px-3 py-1 rounded-md transition-colors ${
                    activityView === "monthly"
                      ? "bg-card text-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Monthly
                </button>
              </div>
            </div>

            {/* Time Series Bar Visualization */}
            {activityView === "weekly" ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
                {analytics.weekly_activity.map((pt) => (
                  <div
                    key={pt.period}
                    className="p-3 rounded-lg border border-border bg-secondary/30 flex flex-col justify-between"
                  >
                    <span className="text-2xs font-mono text-muted-foreground truncate">{pt.period}</span>
                    <div className="my-2 space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground text-2xs">Submissions</span>
                        <span className="font-bold text-foreground">{pt.applications_submitted}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground text-2xs">Interviews</span>
                        <span className="font-bold text-primary">{pt.interviews_scheduled}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {analytics.monthly_activity.map((pt) => (
                  <div
                    key={pt.period}
                    className="p-3 rounded-lg border border-border bg-secondary/30 flex flex-col justify-between"
                  >
                    <span className="text-2xs font-mono text-muted-foreground">{pt.period}</span>
                    <div className="my-2 space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground text-2xs">Submissions</span>
                        <span className="font-bold text-foreground">{pt.applications_submitted}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground text-2xs">Interviews</span>
                        <span className="font-bold text-primary">{pt.interviews_scheduled}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Breakdown Distributions */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* By Role Family */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-1.5">
                <Briefcase className="w-4 h-4 text-purple-500" /> Applications by Role Family
              </h3>
              {analytics.applications_by_role_family.length > 0 ? (
                <div className="space-y-3">
                  {analytics.applications_by_role_family.map((rf) => (
                    <div key={rf.category} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-foreground">{rf.category}</span>
                        <span className="text-muted-foreground">
                          {rf.count} ({rf.percentage}%)
                        </span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden">
                        <div
                          className="h-full bg-purple-500 rounded-full"
                          style={{ width: `${rf.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  No applications tracked yet.
                </p>
              )}
            </div>

            {/* By Company Category */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-xs">
              <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-teal-500" /> Applications by Company Category
              </h3>
              {analytics.applications_by_company_category.length > 0 ? (
                <div className="space-y-3">
                  {analytics.applications_by_company_category.map((cc) => (
                    <div key={cc.category} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-foreground">{cc.category}</span>
                        <span className="text-muted-foreground">
                          {cc.count} ({cc.percentage}%)
                        </span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden">
                        <div
                          className="h-full bg-teal-500 rounded-full"
                          style={{ width: `${cc.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  No company categories recorded yet.
                </p>
              )}
            </div>
          </section>

          {/* Saved vs Applied Comparison */}
          <section className="p-6 rounded-xl border border-border bg-card shadow-xs">
            <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
              <Bookmark className="w-4 h-4 text-indigo-500" /> Saved vs Applied Opportunity Comparison
            </h3>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-3">
              <div className="flex items-center gap-6">
                <div>
                  <span className="text-xs text-muted-foreground block">Saved Opportunities</span>
                  <span className="text-xl font-bold text-foreground">
                    {analytics.saved_vs_applied.saved_count}
                  </span>
                </div>
                <div className="text-lg text-muted-foreground font-light">vs</div>
                <div>
                  <span className="text-xs text-muted-foreground block">Submitted Applications</span>
                  <span className="text-xl font-bold text-primary">
                    {analytics.saved_vs_applied.applied_count}
                  </span>
                </div>
              </div>
              <div className="px-3 py-1.5 rounded-lg bg-secondary text-xs font-semibold text-foreground">
                Ratio: {analytics.saved_vs_applied.ratio}x
              </div>
            </div>
            <div className="mt-2 p-3 rounded-lg bg-secondary/50 border border-border text-xs text-muted-foreground">
              <strong className="text-foreground">Pipeline Insight:</strong> {analytics.saved_vs_applied.insight}
            </div>
          </section>
        </div>
      )}

      {/* Career Goals & Preferences Modal */}
      {showGoalsModal && goals && (
        <CareerGoalsModal
          initialGoals={goals}
          onClose={() => setShowGoalsModal(false)}
          onSaved={(updated) => {
            setGoals(updated);
            setShowGoalsModal(false);
            loadDashboardData(true);
          }}
        />
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Career Goals & Preferences Modal Component
// ---------------------------------------------------------------------------

function CareerGoalsModal({
  initialGoals,
  onClose,
  onSaved,
}: {
  initialGoals: CareerGoalsResponse;
  onClose: () => void;
  onSaved: (goals: CareerGoalsResponse) => void;
}) {
  const [targetRoles, setTargetRoles] = useState(
    initialGoals.target_role_families.join(", ")
  );
  const [preferredLocations, setPreferredLocations] = useState(
    initialGoals.preferred_locations.join(", ")
  );
  const [workArrangements, setWorkArrangements] = useState<string[]>(
    initialGoals.work_arrangement_preferences
  );
  const [minSalary, setMinSalary] = useState(
    initialGoals.min_salary ? initialGoals.min_salary.toString() : ""
  );
  const [salaryCurrency, setSalaryCurrency] = useState(
    initialGoals.salary_currency || "INR"
  );
  const [companyCategories, setCompanyCategories] = useState(
    initialGoals.preferred_company_categories.join(", ")
  );
  const [prioritySkills, setPrioritySkills] = useState(
    initialGoals.priority_technical_skills.join(", ")
  );
  const [weeklyTarget, setWeeklyTarget] = useState(
    initialGoals.weekly_application_target.toString()
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggleArrangement = (val: string) => {
    if (workArrangements.includes(val)) {
      setWorkArrangements(workArrangements.filter((a) => a !== val));
    } else {
      setWorkArrangements([...workArrangements, val]);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const payload: CareerGoalsUpdate = {
      target_role_families: targetRoles
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      preferred_locations: preferredLocations
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      work_arrangement_preferences: workArrangements,
      min_salary: minSalary ? parseFloat(minSalary) : null,
      salary_currency: salaryCurrency,
      preferred_company_categories: companyCategories
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      priority_technical_skills: prioritySkills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      weekly_application_target: weeklyTarget ? parseInt(weeklyTarget, 10) : 5,
    };

    try {
      const res = await careerCommandCenterApi.updateGoals(payload);
      onSaved(res);
    } catch (err: any) {
      setError(err?.message || "Failed to update career goals.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
      <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-4 border-b border-border mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Career Goals & Preferences</h3>
              <p className="text-xs text-muted-foreground">
                Synchronized with the deterministic matching and recommendation engine.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg border border-destructive/20 bg-destructive/10 text-destructive text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4 text-xs">
          {/* Target Role Families */}
          <div>
            <label className="block font-medium text-foreground mb-1">
              Target Role Families (comma separated)
            </label>
            <input
              type="text"
              value={targetRoles}
              onChange={(e) => setTargetRoles(e.target.value)}
              placeholder="e.g. backend_engineer, fullstack_engineer, devops"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Preferred Locations */}
          <div>
            <label className="block font-medium text-foreground mb-1">
              Preferred Locations (comma separated)
            </label>
            <input
              type="text"
              value={preferredLocations}
              onChange={(e) => setPreferredLocations(e.target.value)}
              placeholder="e.g. Bengaluru, Remote, Hyderabad, Pune"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Work Arrangement */}
          <div>
            <label className="block font-medium text-foreground mb-1.5">
              Work Arrangement Preferences
            </label>
            <div className="flex gap-2">
              {["remote", "hybrid", "onsite"].map((arr) => {
                const active = workArrangements.includes(arr);
                return (
                  <button
                    key={arr}
                    type="button"
                    onClick={() => handleToggleArrangement(arr)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-medium capitalize transition-colors ${
                      active
                        ? "border-primary bg-primary text-primary-foreground font-semibold"
                        : "border-border bg-background text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {arr}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Salary Expectation */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-foreground mb-1">
                Minimum Annual Salary
              </label>
              <input
                type="number"
                value={minSalary}
                onChange={(e) => setMinSalary(e.target.value)}
                placeholder="e.g. 1200000"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div>
              <label className="block font-medium text-foreground mb-1">Currency</label>
              <select
                value={salaryCurrency}
                onChange={(e) => setSalaryCurrency(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          {/* Priority Skills */}
          <div>
            <label className="block font-medium text-foreground mb-1">
              Priority Technical Skills (comma separated)
            </label>
            <input
              type="text"
              value={prioritySkills}
              onChange={(e) => setPrioritySkills(e.target.value)}
              placeholder="e.g. Python, FastAPI, Docker, Kubernetes"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Preferred Company Categories */}
          <div>
            <label className="block font-medium text-foreground mb-1">
              Preferred Company Categories (comma separated)
            </label>
            <input
              type="text"
              value={companyCategories}
              onChange={(e) => setCompanyCategories(e.target.value)}
              placeholder="e.g. product, startup, gcc, mnc"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Weekly Target */}
          <div>
            <label className="block font-medium text-foreground mb-1">
              Weekly Application Target
            </label>
            <input
              type="number"
              min="1"
              max="50"
              value={weeklyTarget}
              onChange={(e) => setWeeklyTarget(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Buttons */}
          <div className="pt-4 border-t border-border flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 rounded-lg border border-border bg-background hover:bg-secondary text-foreground text-xs font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              Save Preferences
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
