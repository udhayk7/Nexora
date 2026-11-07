"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Briefcase,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  Copy,
  ExternalLink,
  FileCheck,
  FileText,
  Filter,
  GraduationCap,
  HelpCircle,
  Layers,
  Lightbulb,
  Loader2,
  Mail,
  MapPin,
  Play,
  RefreshCw,
  SendHorizontal,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  UserCheck,
  Users,
  X,
  XCircle,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  careerWorkflowApi,
  CareerWorkflowRunSummary,
  OnboardingStartResult,
  PreparationDetailData,
  UnifiedDiscoveryData,
  UnifiedOpportunityItem,
  WorkflowDashboardData,
  WorkflowRecommendedAction,
} from "@/lib/api";

const WORKFLOW_STAGES = [
  { id: "resume", name: "1. Upload Resume", desc: "Extract candidate facts" },
  { id: "understand", name: "2. Understand Profile", desc: "Roles & verified skills" },
  { id: "discover", name: "3. Discover Jobs", desc: "Ingested active listings" },
  { id: "rank", name: "4. Rank Matches", desc: "Compatibility & tier ranking" },
  { id: "prepare", name: "5. Prepare Workspace", desc: "8 connected assets" },
  { id: "approval", name: "6. Approval & Apply", desc: "Explicit sign-off gate" },
];

export default function CareerWorkflowPage() {
  const { user, isLoading: authLoading } = useAuth();

  // Primary State
  const [dashboard, setDashboard] = useState<WorkflowDashboardData | null>(null);
  const [discovery, setDiscovery] = useState<UnifiedDiscoveryData | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<CareerWorkflowRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);

  // Discovery Filters
  const [filterEntryLevel, setFilterEntryLevel] = useState(true);
  const [prioritizeTiers, setPrioritizeTiers] = useState(true);
  const [activeTab, setActiveTab] = useState<"discovery" | "preparations" | "runs">("discovery");

  // Onboarding Review Modal
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);
  const [onboardingLoading, setOnboardingLoading] = useState(false);
  const [onboardingResult, setOnboardingResult] = useState<OnboardingStartResult | null>(null);
  const [reviewRoles, setReviewRoles] = useState<string[]>([]);
  const [reviewLocations, setReviewLocations] = useState<string[]>([]);
  const [reviewArrangements, setReviewArrangements] = useState<string[]>(["hybrid", "remote"]);
  const [reviewSeniority, setReviewSeniority] = useState("entry");

  // Preparation Workspace Modal
  const [activePrep, setActivePrep] = useState<PreparationDetailData | null>(null);
  const [prepLoading, setPrepLoading] = useState(false);
  const [prepError, setPrepError] = useState<string | null>(null);
  const [showPrepModal, setShowPrepModal] = useState(false);
  const [activePrepJobId, setActivePrepJobId] = useState<string | null>(null);
  const [prepSubTab, setPrepSubTab] = useState<"overview" | "resume_cl" | "qa" | "company">("overview");

  // Execution Modals
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<"official_portal" | "gmail" | "external_form">("official_portal");
  const [approvalNotes, setApprovalNotes] = useState("");
  const [actionInProgress, setActionInProgress] = useState(false);

  // Portal Assisted View
  const [portalAssistedData, setPortalAssistedData] = useState<Record<string, string> | null>(null);
  const [showPortalAssistModal, setShowPortalAssistModal] = useState(false);
  const [confirmNotes, setConfirmNotes] = useState("");
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Gmail Send Modal
  const [showGmailModal, setShowGmailModal] = useState(false);

  // Load Dashboard Data
  const loadDashboardData = useCallback(async () => {
    try {
      const [dashData, runsData] = await Promise.all([
        careerWorkflowApi.getDashboard(),
        careerWorkflowApi.listRuns(),
      ]);
      setDashboard(dashData);
      setWorkflowRuns(runsData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load workflow dashboard";
      setError(msg);
    }
  }, []);

  // Load Discovery Data
  const loadDiscoveryData = useCallback(async () => {
    try {
      const discData = await careerWorkflowApi.getDiscovery(filterEntryLevel, prioritizeTiers, 30);
      setDiscovery(discData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load job opportunities";
      setError(msg);
    }
  }, [filterEntryLevel, prioritizeTiers]);

  useEffect(() => {
    if (user) {
      Promise.all([loadDashboardData(), loadDiscoveryData()]).finally(() => {
        setLoading(false);
      });
    }
  }, [user, loadDashboardData, loadDiscoveryData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadDashboardData(), loadDiscoveryData()]);
    setRefreshing(false);
  };

  // Open Preparation Workspace
  const handleOpenPreparation = async (jobId: string) => {
    setActivePrepJobId(jobId);
    setPrepLoading(true);
    setPrepError(null);
    setShowPrepModal(true);
    try {
      const data = await careerWorkflowApi.startPreparation(jobId);
      setActivePrep(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load preparation workspace";
      setPrepError(msg);
    } finally {
      setPrepLoading(false);
    }
  };

  // Start Candidate Onboarding Flow
  const handleStartOnboarding = async () => {
    setOnboardingLoading(true);
    setError(null);
    try {
      const result = await careerWorkflowApi.startOnboarding();
      setOnboardingResult(result);
      setReviewRoles(result.extracted_roles.length > 0 ? result.extracted_roles : ["Software Engineer"]);
      setReviewLocations(
        Array.isArray(result.inferred_preferences?.preferred_locations)
          ? (result.inferred_preferences.preferred_locations as string[])
          : ["Bengaluru", "Remote"]
      );
      setShowOnboardingModal(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate onboarding";
      setError(msg);
    } finally {
      setOnboardingLoading(false);
    }
  };

  // Confirm Onboarding Preferences
  const handleConfirmOnboarding = async () => {
    setActionInProgress(true);
    try {
      await careerWorkflowApi.confirmOnboarding({
        target_role_families: reviewRoles,
        preferred_locations: reviewLocations,
        work_arrangement_preferences: reviewArrangements,
        seniority: reviewSeniority,
      });
      setShowOnboardingModal(false);
      setNotification({
        type: "success",
        message: "Onboarding preferences confirmed and job matching personalized!",
      });
      await handleRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to confirm onboarding";
      setError(msg);
    } finally {
      setActionInProgress(false);
    }
  };

  // Approve Preparation Gate
  const handleApprovePreparation = async () => {
    if (!activePrep) return;
    setActionInProgress(true);
    try {
      const updated = await careerWorkflowApi.approvePreparation(
        activePrep.job_id,
        selectedChannel,
        approvalNotes
      );
      setActivePrep(updated);
      setShowApprovalModal(false);
      setNotification({
        type: "success",
        message: `Application materials approved for ${selectedChannel.replace("_", " ")}!`,
      });
      await loadDashboardData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to approve application";
      setNotification({ type: "error", message: msg });
    } finally {
      setActionInProgress(false);
    }
  };

  // Open Official Application Portal
  const handleOpenPortal = async () => {
    if (!activePrep) return;
    setActionInProgress(true);
    try {
      const result = await careerWorkflowApi.openPortal(activePrep.job_id);
      setPortalAssistedData(result.assisted_form_data);
      setShowPortalAssistModal(true);
      // Refresh prep record to reflect 'application_page_opened'
      const refreshed = await careerWorkflowApi.getPreparation(activePrep.job_id);
      setActivePrep(refreshed);
      // Open portal URL in new tab
      if (result.portal_url) {
        window.open(result.portal_url, "_blank", "noopener,noreferrer");
      }
      await loadDashboardData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to open application portal";
      setNotification({ type: "error", message: msg });
    } finally {
      setActionInProgress(false);
    }
  };

  // Confirm Portal Submission
  const handleConfirmPortalSubmission = async () => {
    if (!activePrep) return;
    setActionInProgress(true);
    try {
      await careerWorkflowApi.confirmPortalSubmission(activePrep.job_id, confirmNotes);
      setShowConfirmModal(false);
      setShowPortalAssistModal(false);
      setShowPrepModal(false);
      setNotification({
        type: "success",
        message: "Application confirmed and moved to applied tracking!",
      });
      await handleRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to confirm submission";
      setNotification({ type: "error", message: msg });
    } finally {
      setActionInProgress(false);
    }
  };

  // Execute Gmail Dispatch
  const handleExecuteGmail = async () => {
    if (!activePrep || !activePrep.recruiter_email?.id) return;
    setActionInProgress(true);
    try {
      await careerWorkflowApi.executeGmail(
        activePrep.job_id,
        activePrep.recruiter_email.id,
        true
      );
      setShowGmailModal(false);
      setShowPrepModal(false);
      setNotification({
        type: "success",
        message: "Application email dispatched via Gmail and tracked in applications!",
      });
      await handleRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send email application";
      setNotification({ type: "error", message: msg });
    } finally {
      setActionInProgress(false);
    }
  };

  // Withdraw Application
  const handleWithdraw = async (jobId: string) => {
    if (!confirm("Are you sure you want to withdraw this application?")) return;
    try {
      await careerWorkflowApi.withdraw(jobId);
      setShowPrepModal(false);
      setNotification({
        type: "info",
        message: "Application withdrawn from active workflow.",
      });
      await handleRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to withdraw application";
      setNotification({ type: "error", message: msg });
    }
  };

  // Cancel Workflow Run
  const handleCancelRun = async (runId: string) => {
    try {
      await careerWorkflowApi.cancelRun(runId);
      setNotification({ type: "info", message: "Workflow run cancelled." });
      await loadDashboardData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to cancel workflow run";
      setNotification({ type: "error", message: msg });
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
        <h2 className="text-lg font-semibold text-foreground">Initializing Career Workflow...</h2>
        <p className="text-sm text-muted-foreground mt-1">Connecting intelligence across pipeline stages.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Notification Toast */}
      {notification && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between shadow-sm animate-in fade-in duration-200 ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : notification.type === "error"
              ? "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300"
              : "bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
            {notification.type === "error" && <AlertCircle className="w-5 h-5 text-rose-500" />}
            {notification.type === "info" && <Lightbulb className="w-5 h-5 text-blue-500" />}
            <span className="text-sm font-medium">{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="p-1 rounded-md hover:bg-secondary/40 text-muted-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header & Global Workflow Navigation */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary mb-2">
            <Sparkles className="w-3.5 h-3.5" /> Prompt 21 • Unified Career Workflow
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Unified Career Workflow & Automation
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            A single connected pipeline: Upload Resume → Understand Profile → Discover Jobs → Rank Matches →
            Prepare 8 Connected Assets → Approval Gate → Apply & Confirm.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleStartOnboarding}
            disabled={onboardingLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm disabled:opacity-50"
          >
            {onboardingLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Run Candidate Onboarding
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary transition-colors"
          >
            <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Visual Pipeline Stage Tracker */}
      <div className="p-5 rounded-2xl border border-border bg-card shadow-sm">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
          Autonomous Career Pipeline Flow
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {WORKFLOW_STAGES.map((stg, idx) => (
            <div
              key={stg.id}
              className="p-3 rounded-xl border border-border/70 bg-secondary/30 relative flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-primary">Stage 0{idx + 1}</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              </div>
              <div className="mt-2">
                <h3 className="text-xs font-semibold text-foreground">{stg.name}</h3>
                <p className="text-[11px] text-muted-foreground mt-0.5">{stg.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">Profile Health</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-foreground">{dashboard.profile_completion_pct}%</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 truncate">
              {dashboard.profile_missing_items.length === 0 ? "Complete" : `${dashboard.profile_missing_items.length} items missing`}
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">Active Jobs</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-foreground">{dashboard.new_opportunities_count}</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Ingested listings</p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">Strong Matches</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {dashboard.recommended_opportunities_count}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">&ge; 60% compatibility</p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">Needs Approval</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                {dashboard.applications_awaiting_approval_count}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Sign-off required</p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">In Preparation</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {dashboard.incomplete_preparations_count}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Incomplete assets</p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">Submitted</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-foreground">{dashboard.applications_submitted_count}</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Confirmed applied</p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <span className="text-xs font-medium text-muted-foreground">Interviews</span>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {dashboard.upcoming_interviews_count}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Scheduled calls</p>
          </div>
        </div>
      )}

      {/* Recommended Next Actions */}
      {dashboard && dashboard.recommended_next_actions.length > 0 && (
        <div className="p-5 rounded-2xl border border-primary/20 bg-primary/5 space-y-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-primary" />
            <h2 className="text-sm font-bold text-foreground">Prioritized Pipeline Actions</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {dashboard.recommended_next_actions.map((act, i) => (
              <div
                key={i}
                className="p-3.5 rounded-xl border border-border/80 bg-card hover:border-primary/40 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        act.priority === "high"
                          ? "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                          : act.priority === "medium"
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                      }`}
                    >
                      {act.priority} Priority
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">{act.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{act.description}</p>
                </div>
                <div className="mt-3 pt-2 border-t border-border/50 flex justify-end">
                  {act.action_type === "approve_application" ? (
                    <button
                      onClick={() => setActiveTab("discovery")}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                    >
                      View Preparations <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ) : act.action_type === "explore_recommendations" ? (
                    <button
                      onClick={() => setActiveTab("discovery")}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                    >
                      Explore Opportunities <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <Link
                      href={act.target_route}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                    >
                      Go to Section <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-border flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("discovery")}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-all ${
              activeTab === "discovery"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Curated Opportunities & Discovery
          </button>
          <button
            onClick={() => setActiveTab("runs")}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-all ${
              activeTab === "runs"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Workflow Execution History ({workflowRuns.length})
          </button>
        </div>

        {activeTab === "discovery" && (
          <div className="flex items-center gap-3 pb-3">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={filterEntryLevel}
                onChange={(e) => setFilterEntryLevel(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary w-3.5 h-3.5"
              />
              Fresher / Entry-Level Only
            </label>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={prioritizeTiers}
                onChange={(e) => setPrioritizeTiers(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary w-3.5 h-3.5"
              />
              Prioritize Product / GCC / MNC
            </label>
          </div>
        )}
      </div>

      {/* Discovery Opportunities Grid */}
      {activeTab === "discovery" && (
        <div className="space-y-4">
          {discovery && (
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span>
                Showing {discovery.opportunities.length} opportunities (
                {discovery.entry_level_count} early-career, {discovery.priority_tier_count} premier employers)
              </span>
            </div>
          )}

          {discovery && discovery.opportunities.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-dashed border-border bg-card">
              <Briefcase className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
              <h3 className="text-base font-semibold text-foreground">No matching opportunities found</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                Try disabling the early-career filter or run candidate onboarding to expand matching parameters.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {discovery?.opportunities.map((opp) => (
                <div
                  key={opp.job_id}
                  className="p-5 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all flex flex-col justify-between shadow-sm"
                >
                  <div>
                    {/* Header Badges */}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-secondary text-foreground">
                        {opp.company_tier}
                      </span>
                      {opp.match_score !== null && opp.match_score !== undefined && (
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            opp.match_score >= 70
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : opp.match_score >= 50
                              ? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                              : "bg-secondary text-muted-foreground"
                          }`}
                        >
                          {opp.match_score}% Match
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-foreground line-clamp-1">{opp.title}</h3>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                      <span className="font-medium text-foreground">{opp.company_name}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {opp.location_text || opp.work_arrangement}
                      </span>
                    </div>

                    {/* Verification Provenance */}
                    <div className="mt-3 flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md ${
                          opp.verification_status === "verified"
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                            : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                        }`}
                      >
                        {opp.verification_status === "verified" ? (
                          <>
                            <ShieldCheck className="w-3 h-3" /> Direct Verified
                          </>
                        ) : (
                          <>
                            <ShieldAlert className="w-3 h-3" /> Unverified Portal
                          </>
                        )}
                      </span>
                      {opp.is_entry_level && (
                        <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-600 dark:text-purple-400">
                          Fresher Friendly
                        </span>
                      )}
                    </div>

                    {/* Why Recommended / Signals */}
                    {opp.match_reasons.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {opp.match_reasons.slice(0, 2).map((r, ri) => (
                          <p key={ri} className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                            <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                            <span className="truncate">{r}</span>
                          </p>
                        ))}
                      </div>
                    )}

                    {/* Missing Skills Warning */}
                    {opp.skill_gaps.length > 0 && (
                      <div className="mt-2.5 flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400">
                        <AlertTriangle className="w-3 h-3 shrink-0" />
                        <span className="truncate">Missing: {opp.skill_gaps.slice(0, 3).join(", ")}</span>
                      </div>
                    )}
                  </div>

                  <div className="mt-5 pt-3 border-t border-border flex items-center justify-between">
                    {opp.application_url ? (
                      <a
                        href={opp.application_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                      >
                        Listing <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-muted-foreground">Original Source</span>
                    )}

                    <button
                      onClick={() => handleOpenPreparation(opp.job_id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
                    >
                      <Layers className="w-3.5 h-3.5" /> Prepare Application
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execution Runs Tab */}
      {activeTab === "runs" && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-border bg-card">
            <h2 className="text-sm font-semibold text-foreground">Orchestrated Workflow Runs</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Persistent state machine tracking background asynchronous tasks, bounded retries (3), and candidate approval checkpoints.
            </p>
          </div>

          {workflowRuns.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-dashed border-border bg-card">
              <Clock className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm font-medium text-foreground">No workflow runs recorded yet.</p>
              <p className="text-xs text-muted-foreground mt-1">
                Run Candidate Onboarding or initiate application preparation to trigger orchestration runs.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {workflowRuns.map((r) => (
                <div key={r.id} className="p-4 rounded-xl border border-border bg-card flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-semibold text-primary">{r.workflow_type}</span>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          r.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                            : r.status === "running"
                            ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 animate-pulse"
                            : r.status === "cancelled"
                            ? "bg-secondary text-muted-foreground"
                            : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                        }`}
                      >
                        {r.status}
                      </span>
                      {r.retry_count > 0 && (
                        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-mono">
                          (retries: {r.retry_count}/3)
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-foreground font-medium">Step: {r.current_step || "initialized"}</p>
                    <p className="text-[11px] text-muted-foreground">Started: {new Date(r.created_at).toLocaleString()}</p>
                    {r.error_message && (
                      <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{r.error_message}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="w-32">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1">
                        <span>Progress</span>
                        <span>{r.progress_pct}%</span>
                      </div>
                      <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-primary h-full rounded-full transition-all duration-300"
                          style={{ width: `${r.progress_pct}%` }}
                        />
                      </div>
                    </div>

                    {r.status === "running" && (
                      <button
                        onClick={() => handleCancelRun(r.id)}
                        className="px-2.5 py-1 text-xs font-medium rounded-md border border-rose-500/30 text-rose-600 hover:bg-rose-500/10 transition-colors"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL 1: Candidate Onboarding Review Drawer */}
      {showOnboardingModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div>
                <div className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
                  <UserCheck className="w-3.5 h-3.5" /> Candidate Sign-Off Gate
                </div>
                <h3 className="text-lg font-bold text-foreground">Review Inferred Career Preferences</h3>
              </div>
              <button
                onClick={() => setShowOnboardingModal(false)}
                className="p-1 rounded-md hover:bg-secondary text-muted-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Nexora strictly treats AI inferences as proposals until you review and confirm them.
              Confirm or update the roles and parameters below:
            </p>

            <div className="space-y-4 text-xs">
              <div>
                <label className="font-semibold text-foreground block mb-1">Target Roles (Comma-separated)</label>
                <input
                  type="text"
                  value={reviewRoles.join(", ")}
                  onChange={(e) =>
                    setReviewRoles(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
                  }
                  className="w-full p-2.5 rounded-lg border border-border bg-secondary/30 text-foreground text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-foreground block mb-1">Preferred Locations</label>
                <input
                  type="text"
                  value={reviewLocations.join(", ")}
                  onChange={(e) =>
                    setReviewLocations(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
                  }
                  className="w-full p-2.5 rounded-lg border border-border bg-secondary/30 text-foreground text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-foreground block mb-1">Seniority Preference</label>
                  <select
                    value={reviewSeniority}
                    onChange={(e) => setReviewSeniority(e.target.value)}
                    className="w-full p-2.5 rounded-lg border border-border bg-secondary/30 text-foreground text-xs"
                  >
                    <option value="entry">Entry-Level / Fresher</option>
                    <option value="junior">Junior (1-2 years)</option>
                    <option value="mid">Mid-Level (3-5 years)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-foreground block mb-1">Work Arrangement</label>
                  <div className="flex gap-2 mt-1">
                    {["remote", "hybrid", "onsite"].map((arr) => (
                      <button
                        key={arr}
                        type="button"
                        onClick={() => {
                          if (reviewArrangements.includes(arr)) {
                            setReviewArrangements(reviewArrangements.filter((a) => a !== arr));
                          } else {
                            setReviewArrangements([...reviewArrangements, arr]);
                          }
                        }}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium border ${
                          reviewArrangements.includes(arr)
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-secondary/40 border-border text-muted-foreground"
                        }`}
                      >
                        {arr.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
              <button
                onClick={() => setShowOnboardingModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmOnboarding}
                disabled={actionInProgress}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm disabled:opacity-50"
              >
                {actionInProgress ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                Confirm & Initialize Matching
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Intelligent Application Preparation Workspace (8 Connected Assets) */}
      {showPrepModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-5 border-b border-border flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-primary">Connected Application Workspace</span>
                  {activePrep && (
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        activePrep.execution_status === "ready_to_apply"
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : activePrep.execution_status === "awaiting_approval"
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : activePrep.execution_status === "submitted_and_confirmed"
                          ? "bg-emerald-500 text-white"
                          : "bg-secondary text-muted-foreground"
                      }`}
                    >
                      Status: {activePrep.execution_status.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-bold text-foreground">
                  {activePrep?.job_title || "Loading Workspace..."}
                </h3>
                <p className="text-xs text-muted-foreground">{activePrep?.company_name}</p>
              </div>

              <button
                onClick={() => setShowPrepModal(false)}
                className="p-1 rounded-md hover:bg-secondary text-muted-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Sub-tabs */}
            <div className="px-5 pt-3 border-b border-border flex items-center gap-2">
              <button
                onClick={() => setPrepSubTab("overview")}
                className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
                  prepSubTab === "overview"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                Job Intel & Compatibility
              </button>
              <button
                onClick={() => setPrepSubTab("resume_cl")}
                className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
                  prepSubTab === "resume_cl"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                Tailored Resume & Letter
              </button>
              <button
                onClick={() => setPrepSubTab("qa")}
                className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
                  prepSubTab === "qa"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                Screening Q&A Prep ({activePrep?.screening_qa_prep.length || 0})
              </button>
              <button
                onClick={() => setPrepSubTab("company")}
                className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
                  prepSubTab === "company"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                Company Dossier & Interview Prep
              </button>
            </div>

            {/* Content Body */}
            <div className="p-6 flex-1 overflow-y-auto space-y-5">
              {prepLoading ? (
                <div className="py-16 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Gathering connected career assets...</p>
                </div>
              ) : prepError ? (
                <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs">
                  {prepError}
                </div>
              ) : activePrep ? (
                <>
                  {/* TAB 1: OVERVIEW */}
                  {prepSubTab === "overview" && (
                    <div className="space-y-4">
                      {/* Job Intelligence Asset */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">
                          1. Grounded Job Intelligence
                        </h4>
                        <p className="text-xs text-foreground font-medium">
                          {activePrep.job_intelligence?.role_summary || "Role requirements analyzed"}
                        </p>
                        {activePrep.job_intelligence?.must_have_skills && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {activePrep.job_intelligence.must_have_skills.map((s, i) => (
                              <span key={i} className="text-[11px] px-2 py-0.5 rounded-md bg-secondary text-foreground">
                                {s}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Compatibility Assessment Asset */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-primary">
                            2. Candidate Compatibility Assessment
                          </h4>
                          {activePrep.compatibility_assessment?.overall_score && (
                            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                              {activePrep.compatibility_assessment.overall_score}% Match
                            </span>
                          )}
                        </div>

                        {activePrep.compatibility_assessment?.strengths && (
                          <div className="space-y-1">
                            <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                              Demonstrated Strengths:
                            </span>
                            <p className="text-xs text-muted-foreground">
                              {activePrep.compatibility_assessment.strengths.join(", ")}
                            </p>
                          </div>
                        )}

                        {activePrep.compatibility_assessment?.gaps && (
                          <div className="mt-2 space-y-1">
                            <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400">
                              Identified Gaps:
                            </span>
                            <p className="text-xs text-muted-foreground">
                              {activePrep.compatibility_assessment.gaps.join(", ")}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 2: RESUME & COVER LETTER */}
                  {prepSubTab === "resume_cl" && (
                    <div className="space-y-4">
                      {/* Tailored Resume Asset */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-primary">
                            3. Tailored Resume Version
                          </h4>
                          {activePrep.tailored_resume?.is_tailored && (
                            <span className="text-[10px] font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded-full">
                              Tailored to Job Requisition
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-foreground">
                          Version {activePrep.tailored_resume?.version_number || 1} •{" "}
                          {activePrep.tailored_resume?.filename || "Primary Resume"}
                        </p>
                      </div>

                      {/* Cover Letter Asset */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-primary">
                            4. Grounded Cover Letter
                          </h4>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              activePrep.cover_letter?.is_approved
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                            }`}
                          >
                            {activePrep.cover_letter?.is_approved ? "Approved" : "Draft / Needs Approval"}
                          </span>
                        </div>
                        <div className="p-3 rounded-lg bg-card border border-border text-xs text-muted-foreground whitespace-pre-wrap font-serif leading-relaxed max-h-40 overflow-y-auto">
                          {activePrep.cover_letter?.content || "Cover letter draft generated from resume facts."}
                        </div>
                      </div>

                      {/* Recruiter Email Asset */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">
                          5. Recruiter Outreach Email
                        </h4>
                        <p className="text-xs font-semibold text-foreground">
                          Subject: {activePrep.recruiter_email?.subject || "Application Outreach"}
                        </p>
                        <div className="mt-2 p-3 rounded-lg bg-card border border-border text-xs text-muted-foreground whitespace-pre-wrap max-h-32 overflow-y-auto">
                          {activePrep.recruiter_email?.body_text || "Email draft"}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: SCREENING QA */}
                  {prepSubTab === "qa" && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary">
                          6. Grounded Screening Q&A Prep
                        </h4>
                        <span className="text-[11px] text-muted-foreground">Factual & STAR aligned</span>
                      </div>

                      {activePrep.screening_qa_prep.map((qa, qi) => (
                        <div key={qi} className="p-3.5 rounded-xl border border-border bg-secondary/20 space-y-1.5">
                          <p className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                            <HelpCircle className="w-3.5 h-3.5 text-primary shrink-0" />
                            {qa.question}
                          </p>
                          <p className="text-xs text-muted-foreground pl-5">{qa.answer_outline}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* TAB 4: COMPANY DOSSIER & INTERVIEW */}
                  {prepSubTab === "company" && (
                    <div className="space-y-4">
                      {/* Company Intelligence Asset */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">
                          7. Company Intelligence Dossier
                        </h4>
                        <p className="text-xs text-foreground">
                          {activePrep.company_research?.company_overview || "Evidence-backed company research profile."}
                        </p>
                        {activePrep.company_research?.technologies_confirmed && (
                          <div className="mt-2">
                            <span className="text-[11px] font-semibold text-muted-foreground">Confirmed Tech Stack:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {activePrep.company_research.technologies_confirmed.map((t, ti) => (
                                <span key={ti} className="text-[10px] px-2 py-0.5 rounded bg-card border text-foreground">
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Interview Prep Starter */}
                      <div className="p-4 rounded-xl border border-border bg-secondary/20">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary mb-2">
                          8. Interview Prep Starter Topics
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {activePrep.interview_prep_starter?.suggested_topics.map((top, ti) => (
                            <span key={ti} className="text-xs px-2.5 py-1 rounded-md bg-purple-500/10 text-purple-600 dark:text-purple-400 font-medium">
                              {top}
                            </span>
                          ))}
                        </div>
                        <div className="mt-3">
                          <Link
                            href="/dashboard/interview-prep"
                            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                          >
                            Launch Full Mock Coaching <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Footer Execution & Approval Gate */}
            {activePrep && (
              <div className="p-4 border-t border-border bg-card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Gate:</span>
                  <span className="text-xs font-bold text-foreground">
                    {activePrep.execution_status === "not_started" || activePrep.execution_status === "preparation_in_progress"
                      ? "Awaiting Candidate Sign-Off"
                      : activePrep.execution_status === "awaiting_approval"
                      ? "Review Pending Approval"
                      : activePrep.execution_status === "ready_to_apply"
                      ? "Ready for Application Dispatch"
                      : activePrep.execution_status === "application_page_opened"
                      ? "Portal Opened (Pending Confirmation)"
                      : activePrep.execution_status === "submitted_and_confirmed"
                      ? "Submitted & Confirmed"
                      : activePrep.execution_status}
                  </span>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {/* Approval Button */}
                  {activePrep.execution_status !== "ready_to_apply" &&
                    activePrep.execution_status !== "application_page_opened" &&
                    activePrep.execution_status !== "submitted_and_confirmed" && (
                      <button
                        onClick={() => setShowApprovalModal(true)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
                      >
                        <FileCheck className="w-3.5 h-3.5" /> Approve Materials
                      </button>
                    )}

                  {/* Channel Execution Buttons */}
                  {activePrep.execution_status === "ready_to_apply" && (
                    <>
                      {activePrep.execution_channel === "gmail" ? (
                        <button
                          onClick={() => setShowGmailModal(true)}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
                        >
                          <Mail className="w-3.5 h-3.5" /> Send via Gmail
                        </button>
                      ) : (
                        <button
                          onClick={handleOpenPortal}
                          disabled={actionInProgress}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm disabled:opacity-50"
                        >
                          {actionInProgress ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ExternalLink className="w-3.5 h-3.5" />}
                          Open Application Portal
                        </button>
                      )}
                    </>
                  )}

                  {/* Confirm Submission Button (if portal opened) */}
                  {activePrep.execution_status === "application_page_opened" && (
                    <button
                      onClick={() => setShowConfirmModal(true)}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Portal Submission
                    </button>
                  )}

                  {/* Withdraw Button */}
                  <button
                    onClick={() => handleWithdraw(activePrep.job_id)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-secondary text-muted-foreground hover:text-foreground"
                  >
                    Withdraw
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 3: Explicit Candidate Approval Gate */}
      {showApprovalModal && activePrep && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="text-base font-bold text-foreground">Candidate Explicit Approval Gate</h3>
              <button onClick={() => setShowApprovalModal(false)} className="p-1 rounded-md text-muted-foreground hover:bg-secondary">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              By approving, you confirm you have reviewed the tailored resume, cover letter, and screening talking points.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-foreground block mb-1">Execution Channel</label>
                <select
                  value={selectedChannel}
                  onChange={(e) => setSelectedChannel(e.target.value as "official_portal" | "gmail" | "external_form")}
                  className="w-full p-2.5 rounded-lg border border-border bg-secondary/30 text-foreground text-xs"
                >
                  <option value="official_portal">Official Careers Portal (Assisted Form Guidance)</option>
                  <option value="gmail">Gmail Recruiter Dispatch (OAuth Send)</option>
                  <option value="external_form">External Application Form</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-foreground block mb-1">Approval Notes (Optional)</label>
                <textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="Notes or special considerations..."
                  rows={2}
                  className="w-full p-2.5 rounded-lg border border-border bg-secondary/30 text-foreground text-xs"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => setShowApprovalModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={handleApprovePreparation}
                disabled={actionInProgress}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm disabled:opacity-50"
              >
                {actionInProgress ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                Sign Off & Ready to Apply
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: Assisted Portal Auto-Fill & Non-Submission Notice */}
      {showPortalAssistModal && portalAssistedData && activePrep && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <ExternalLink className="w-4 h-4 text-primary" />
                <h3 className="text-base font-bold text-foreground">Application Portal Opened</h3>
              </div>
              <button onClick={() => setShowPortalAssistModal(false)} className="p-1 rounded-md text-muted-foreground hover:bg-secondary">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Critical Non-Submission Warning */}
            <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200 text-xs space-y-1">
              <div className="flex items-center gap-1.5 font-bold">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                IMPORTANT: Opening the portal is NOT application submission.
              </div>
              <p>
                Complete the submission in the newly opened browser tab. Once submitted, return here and click
                &ldquo;Confirm Portal Submission&rdquo; to officially record the application.
              </p>
            </div>

            {/* Quick-Copy Assisted Form Data */}
            <div className="space-y-2 text-xs">
              <span className="font-semibold text-foreground">Verified Candidate Information for Auto-Fill:</span>
              <div className="p-3 rounded-xl border border-border bg-secondary/30 space-y-2 text-xs">
                {Object.entries(portalAssistedData).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-2">
                    <span className="text-muted-foreground font-medium capitalize">{k.replace(/_/g, " ")}:</span>
                    <div className="flex items-center gap-1.5 truncate max-w-[240px]">
                      <span className="font-mono text-foreground truncate">{v || "N/A"}</span>
                      {v && (
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(v);
                            setNotification({ type: "info", message: `Copied ${k} to clipboard!` });
                          }}
                          className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground"
                          title="Copy"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => setShowPortalAssistModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground"
              >
                Close Guidance
              </button>
              <button
                onClick={() => {
                  setShowPortalAssistModal(false);
                  setShowConfirmModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> I Have Submitted
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: Explicit Submission Confirmation */}
      {showConfirmModal && activePrep && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="text-base font-bold text-foreground">Confirm Submission</h3>
              <button onClick={() => setShowConfirmModal(false)} className="p-1 rounded-md text-muted-foreground hover:bg-secondary">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Confirming moves this application from &ldquo;in progress&rdquo; to &ldquo;applied&rdquo; and tracks it in your career funnel.
            </p>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Confirmation Notes (Optional)</label>
              <textarea
                value={confirmNotes}
                onChange={(e) => setConfirmNotes(e.target.value)}
                placeholder="Application ID, confirmation email number, or portal response..."
                rows={3}
                className="w-full p-2.5 rounded-lg border border-border bg-secondary/30 text-foreground text-xs"
              />
            </div>

            <div className="pt-3 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPortalSubmission}
                disabled={actionInProgress}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm disabled:opacity-50"
              >
                {actionInProgress ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                Confirm Submission
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 6: Gmail Send Confirmation */}
      {showGmailModal && activePrep && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-primary" />
                <h3 className="text-base font-bold text-foreground">Confirm Gmail Send</h3>
              </div>
              <button onClick={() => setShowGmailModal(false)} className="p-1 rounded-md text-muted-foreground hover:bg-secondary">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3.5 rounded-xl border border-blue-500/30 bg-blue-500/10 text-blue-800 dark:text-blue-200 text-xs">
              <p className="font-semibold">Explicit Send Authorization:</p>
              <p className="mt-1">
                This will dispatch an actual recruiter email through your connected Gmail account with your approved tailored materials.
              </p>
            </div>

            <div className="text-xs space-y-1">
              <p className="text-muted-foreground">Recipient: <span className="font-mono text-foreground">{activePrep.recruiter_email?.recipient_email || "Company Recruiter"}</span></p>
              <p className="text-muted-foreground">Subject: <span className="font-medium text-foreground">{activePrep.recruiter_email?.subject}</span></p>
            </div>

            <div className="pt-3 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => setShowGmailModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteGmail}
                disabled={actionInProgress}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 shadow-sm disabled:opacity-50"
              >
                {actionInProgress ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <SendHorizontal className="w-3.5 h-3.5" />}
                Send Email Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
