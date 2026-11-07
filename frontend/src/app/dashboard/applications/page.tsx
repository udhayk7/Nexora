"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Bot,
  Briefcase,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  Filter,
  Layers,
  Link as LinkIcon,
  Loader2,
  Mail,
  MessageSquare,
  Phone,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Tag,
  Trash2,
  User,
  Users,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import { NotificationBell } from "@/components/NotificationBell";
import {
  ApplicationActivity,
  ApplicationAnalytics,
  ApplicationChannel,
  ApplicationInterview,
  ApplicationStatus,
  applicationsApi,
  JobApplicationDetail,
  JobApplicationSummary,
  resumesApi,
  ResumeSummary,
  UpcomingEvent,
} from "@/lib/api";

const STATUS_CONFIG: Record<
  ApplicationStatus,
  { label: string; bg: string; text: string; border: string; step: number }
> = {
  interested: {
    label: "Interested",
    bg: "bg-slate-500/10",
    text: "text-slate-400",
    border: "border-slate-500/30",
    step: 1,
  },
  preparing: {
    label: "Preparing",
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/30",
    step: 2,
  },
  applied: {
    label: "Applied",
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/30",
    step: 3,
  },
  shortlisted: {
    label: "Shortlisted",
    bg: "bg-indigo-500/10",
    text: "text-indigo-400",
    border: "border-indigo-500/30",
    step: 4,
  },
  assessment: {
    label: "Assessment",
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/30",
    step: 5,
  },
  interview: {
    label: "Interview",
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/30",
    step: 6,
  },
  offer: {
    label: "Offer",
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    step: 7,
  },
  rejected: {
    label: "Rejected",
    bg: "bg-rose-500/10",
    text: "text-rose-400",
    border: "border-rose-500/30",
    step: 8,
  },
  withdrawn: {
    label: "Withdrawn",
    bg: "bg-neutral-500/10",
    text: "text-neutral-400",
    border: "border-neutral-500/30",
    step: 9,
  },
};

const CHANNEL_LABELS: Record<ApplicationChannel, string> = {
  official_portal: "Official Portal",
  email: "Direct Email",
  referral: "Referral",
  external_form: "External Form",
  other: "Other Channel",
};

export default function ApplicationsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-12 text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Loading Application Tracker...</p>
        </div>
      }
    >
      <ApplicationsContent />
    </React.Suspense>
  );
}

function ApplicationsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading } = useAuth();

  // State
  const [applications, setApplications] = useState<JobApplicationSummary[]>([]);
  const [analytics, setAnalytics] = useState<ApplicationAnalytics | null>(null);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Modals & Drawers
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [appDetail, setAppDetail] = useState<JobApplicationDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // New Application Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newCompany, setNewCompany] = useState("");
  const [newChannel, setNewChannel] = useState<ApplicationChannel>("official_portal");
  const [newStatus, setNewStatus] = useState<ApplicationStatus>("interested");
  const [newUrl, setNewUrl] = useState("");
  const [newDeadline, setNewDeadline] = useState("");
  const [newFollowUp, setNewFollowUp] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [newResumeId, setNewResumeId] = useState<string>("");
  const [newJobId, setNewJobId] = useState<string>("");
  const [newRecruiterName, setNewRecruiterName] = useState("");
  const [newRecruiterEmail, setNewRecruiterEmail] = useState("");
  const [newLocationType, setNewLocationType] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  // Quick Status Transition Modal
  const [quickStatusApp, setQuickStatusApp] = useState<JobApplicationSummary | null>(null);
  const [transitionStatus, setTransitionStatus] = useState<ApplicationStatus>("applied");
  const [transitionNote, setTransitionNote] = useState("");
  const [transitionConfirmSub, setTransitionConfirmSub] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  // Interview Scheduler Modal
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [ivRound, setIvRound] = useState(1);
  const [ivType, setIvType] = useState("technical");
  const [ivTitle, setIvTitle] = useState("Technical Screen");
  const [ivDate, setIvDate] = useState("");
  const [ivDuration, setIvDuration] = useState(45);
  const [ivUrl, setIvUrl] = useState("");
  const [ivInterviewers, setIvInterviewers] = useState("");
  const [ivNotes, setIvNotes] = useState("");
  const [isScheduling, setIsScheduling] = useState(false);

  // Interview Outcome Modal
  const [updatingInterview, setUpdatingInterview] = useState<ApplicationInterview | null>(null);
  const [ivOutcome, setIvOutcome] = useState<"pending" | "passed" | "failed" | "cancelled" | "waived">("pending");
  const [ivFeedback, setIvFeedback] = useState("");
  const [ivNextSteps, setIvNextSteps] = useState("");
  const [isUpdatingInterview, setIsUpdatingInterview] = useState(false);

  // New Activity Modal
  const [showActivityModal, setShowActivityModal] = useState(false);
  const [actType, setActType] = useState<"note" | "recruiter_contact" | "follow_up">("note");
  const [actTitle, setActTitle] = useState("");
  const [actDesc, setActDesc] = useState("");
  const [isAddingActivity, setIsAddingActivity] = useState(false);

  // Delete Application Confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Check auth
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Handle URL query parameters for prefilling New Application
  useEffect(() => {
    const action = searchParams.get("action");
    if (action === "new") {
      const qTitle = searchParams.get("title");
      const qCompany = searchParams.get("company");
      const qJobId = searchParams.get("jobId");
      const qUrl = searchParams.get("url");

      if (qTitle) setNewTitle(decodeURIComponent(qTitle));
      if (qCompany) setNewCompany(decodeURIComponent(qCompany));
      if (qJobId) setNewJobId(qJobId);
      if (qUrl) setNewUrl(decodeURIComponent(qUrl));

      setShowCreateModal(true);
    }
  }, [searchParams]);

  // Load Data
  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [appsResp, analyticsResp, resumesResp] = await Promise.all([
        applicationsApi.listApplications({ limit: 100 }),
        applicationsApi.getAnalytics(),
        resumesApi.listResumes(),
      ]);

      setApplications(appsResp.items);
      setAnalytics(analyticsResp);
      setResumes(resumesResp);
    } catch (err) {
      console.error("Failed to load application data:", err);
      setError("Unable to load application records. Please try again.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user, loadData]);

  // Load detail when application selected
  const loadDetail = useCallback(async (appId: string) => {
    setIsLoadingDetail(true);
    try {
      const detail = await applicationsApi.getApplication(appId);
      setAppDetail(detail);
    } catch (err) {
      console.error("Failed to fetch application details:", err);
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  const handleSelectApp = (appId: string) => {
    setSelectedAppId(appId);
    loadDetail(appId);
  };

  // Create Application
  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newCompany.trim()) return;

    setIsCreating(true);
    try {
      const created = await applicationsApi.createApplication({
        title: newTitle.trim(),
        company_name: newCompany.trim(),
        application_channel: newChannel,
        status: newStatus,
        application_url: newUrl.trim() || undefined,
        deadline_at: newDeadline ? new Date(newDeadline).toISOString() : undefined,
        next_follow_up_at: newFollowUp ? new Date(newFollowUp).toISOString() : undefined,
        notes: newNotes.trim() || undefined,
        resume_id: newResumeId || undefined,
        job_id: newJobId || undefined,
        recruiter_name: newRecruiterName.trim() || undefined,
        recruiter_email: newRecruiterEmail.trim() || undefined,
        location_workplace_type: newLocationType.trim() || undefined,
        submission_confirmed: newStatus === "applied",
      });

      setShowCreateModal(false);
      // Reset form
      setNewTitle("");
      setNewCompany("");
      setNewUrl("");
      setNewDeadline("");
      setNewFollowUp("");
      setNewNotes("");
      setNewResumeId("");
      setNewJobId("");
      setNewRecruiterName("");
      setNewRecruiterEmail("");

      await loadData();
      handleSelectApp(created.id);
    } catch (err) {
      console.error("Failed to create application:", err);
      alert("Failed to create application. Check all required fields.");
    } finally {
      setIsCreating(false);
    }
  };

  // Link Opened Tracker
  const handleOpenLink = async (app: JobApplicationSummary) => {
    if (!app.application_url) return;
    try {
      await applicationsApi.markLinkOpened(app.id);
      window.open(app.application_url, "_blank", "noopener,noreferrer");
      if (selectedAppId === app.id) {
        loadDetail(app.id);
      }
    } catch (err) {
      console.error("Failed to mark link opened:", err);
      window.open(app.application_url, "_blank", "noopener,noreferrer");
    }
  };

  // Status Update
  const handleUpdateStatus = async () => {
    if (!quickStatusApp) return;
    setIsUpdatingStatus(true);
    try {
      await applicationsApi.updateStatus(quickStatusApp.id, {
        status: transitionStatus,
        note: transitionNote.trim() || undefined,
        submission_confirmed:
          transitionConfirmSub ||
          (transitionStatus === "applied" && quickStatusApp.submission_confirmed),
        applied_at:
          transitionStatus === "applied" && !quickStatusApp.applied_at
            ? new Date().toISOString()
            : undefined,
      });

      setQuickStatusApp(null);
      setTransitionNote("");
      setTransitionConfirmSub(false);
      await loadData();
      if (selectedAppId === quickStatusApp.id) {
        loadDetail(quickStatusApp.id);
      }
    } catch (err) {
      console.error("Failed to update status:", err);
      alert("Status update failed. Please try again.");
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  // Delete Application
  const handleDeleteApplication = async () => {
    if (!selectedAppId) return;
    setIsDeleting(true);
    try {
      await applicationsApi.deleteApplication(selectedAppId);
      setSelectedAppId(null);
      setAppDetail(null);
      setShowDeleteConfirm(false);
      await loadData();
    } catch (err) {
      console.error("Failed to delete application:", err);
      alert("Could not delete application. Try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  // Schedule Interview
  const handleScheduleInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId || !ivTitle.trim() || !ivDate) return;

    setIsScheduling(true);
    try {
      await applicationsApi.createInterview(selectedAppId, {
        round_number: ivRound,
        interview_type: ivType,
        title: ivTitle.trim(),
        scheduled_at: new Date(ivDate).toISOString(),
        duration_minutes: ivDuration,
        meeting_url: ivUrl.trim() || undefined,
        interviewers: ivInterviewers
          ? ivInterviewers.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        preparation_notes: ivNotes.trim() || undefined,
      });

      setShowScheduleModal(false);
      setIvTitle("Technical Screen");
      setIvDate("");
      setIvUrl("");
      setIvInterviewers("");
      setIvNotes("");
      loadDetail(selectedAppId);
      loadData();
    } catch (err) {
      console.error("Failed to schedule interview:", err);
      alert("Error scheduling interview round.");
    } finally {
      setIsScheduling(false);
    }
  };

  // Update Interview Outcome
  const handleSaveInterviewOutcome = async () => {
    if (!selectedAppId || !updatingInterview) return;
    setIsUpdatingInterview(true);
    try {
      await applicationsApi.updateInterview(selectedAppId, updatingInterview.id, {
        outcome: ivOutcome,
        feedback: ivFeedback.trim() || undefined,
        next_steps: ivNextSteps.trim() || undefined,
        status: ivOutcome !== "pending" ? "completed" : "scheduled",
      });

      setUpdatingInterview(null);
      loadDetail(selectedAppId);
      loadData();
    } catch (err) {
      console.error("Failed to update interview outcome:", err);
      alert("Error saving interview feedback.");
    } finally {
      setIsUpdatingInterview(false);
    }
  };

  // Add Activity / Note
  const handleAddActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId || !actTitle.trim()) return;

    setIsAddingActivity(true);
    try {
      await applicationsApi.createActivity(selectedAppId, {
        activity_type: actType,
        title: actTitle.trim(),
        description: actDesc.trim() || undefined,
      });

      setShowActivityModal(false);
      setActTitle("");
      setActDesc("");
      loadDetail(selectedAppId);
    } catch (err) {
      console.error("Failed to add activity:", err);
      alert("Error adding activity entry.");
    } finally {
      setIsAddingActivity(false);
    }
  };

  // Filtered Applications
  const filteredApps = useMemo(() => {
    return applications.filter((app) => {
      if (statusFilter !== "all" && app.status !== statusFilter) return false;
      if (channelFilter !== "all" && app.application_channel !== channelFilter) return false;
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchTitle = app.title.toLowerCase().includes(query);
        const matchCompany = app.company_name.toLowerCase().includes(query);
        if (!matchTitle && !matchCompany) return false;
      }
      return true;
    });
  }, [applications, statusFilter, channelFilter, searchTerm]);

  // Pipeline summary numbers
  const pipelineStages: ApplicationStatus[] = [
    "interested",
    "preparing",
    "applied",
    "shortlisted",
    "assessment",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
  ];

  if (authLoading || (!user && isLoading)) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Loading Application Management...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition"
              title="Return to Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight">Application Tracker</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium border border-primary/20">
                  Prompt 11
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Centralized career pipeline, interview intelligence & real DB tracking
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <NotificationBell />
            <button
              onClick={() => {
                setIsRefreshing(true);
                loadData();
              }}
              disabled={isRefreshing}
              className="p-2 text-xs rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground transition flex items-center gap-1.5"
              title="Refresh applications"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <button
              onClick={() => {
                setNewTitle("");
                setNewCompany("");
                setNewUrl("");
                setNewDeadline("");
                setNewFollowUp("");
                setNewNotes("");
                setShowCreateModal(true);
              }}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Track Application</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-sm flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadData}
              className="text-xs underline font-semibold hover:opacity-80"
            >
              Retry
            </button>
          </div>
        )}

        {/* Real DB Analytics KPI Cards */}
        {analytics && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 rounded-xl border border-border bg-card flex flex-col justify-between shadow-sm">
              <span className="text-xs font-medium text-muted-foreground flex items-center justify-between">
                Total
                <Briefcase className="w-3.5 h-3.5 text-muted-foreground/60" />
              </span>
              <span className="text-2xl font-bold tracking-tight mt-2 text-foreground">
                {analytics.total_applications}
              </span>
              <span className="text-[11px] text-muted-foreground mt-1">Logged applications</span>
            </div>

            <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5 flex flex-col justify-between shadow-sm">
              <span className="text-xs font-medium text-blue-400 flex items-center justify-between">
                In Progress
                <Clock className="w-3.5 h-3.5 text-blue-400/80" />
              </span>
              <span className="text-2xl font-bold tracking-tight mt-2 text-blue-400">
                {analytics.in_progress_count}
              </span>
              <span className="text-[11px] text-muted-foreground mt-1">Active pipelines</span>
            </div>

            <div className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/5 flex flex-col justify-between shadow-sm">
              <span className="text-xs font-medium text-purple-400 flex items-center justify-between">
                Interviews
                <Users className="w-3.5 h-3.5 text-purple-400/80" />
              </span>
              <span className="text-2xl font-bold tracking-tight mt-2 text-purple-400">
                {analytics.interviews_scheduled_count}
              </span>
              <span className="text-[11px] text-muted-foreground mt-1">Rounds scheduled</span>
            </div>

            <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 flex flex-col justify-between shadow-sm">
              <span className="text-xs font-medium text-amber-400 flex items-center justify-between">
                Assessments
                <Tag className="w-3.5 h-3.5 text-amber-400/80" />
              </span>
              <span className="text-2xl font-bold tracking-tight mt-2 text-amber-400">
                {analytics.assessments_pending_count}
              </span>
              <span className="text-[11px] text-muted-foreground mt-1">Pending tasks</span>
            </div>

            <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 flex flex-col justify-between shadow-sm">
              <span className="text-xs font-medium text-emerald-400 flex items-center justify-between">
                Offers
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400/80" />
              </span>
              <span className="text-2xl font-bold tracking-tight mt-2 text-emerald-400">
                {analytics.offers_count}
              </span>
              <span className="text-[11px] text-muted-foreground mt-1">Offers extended</span>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card flex flex-col justify-between shadow-sm">
              <span className="text-xs font-medium text-muted-foreground flex items-center justify-between">
                Deadlines & Follow-ups
                <Calendar className="w-3.5 h-3.5 text-muted-foreground/60" />
              </span>
              <span className="text-2xl font-bold tracking-tight mt-2 text-foreground">
                {analytics.upcoming_deadlines_count + analytics.upcoming_follow_ups_count}
              </span>
              <span className="text-[11px] text-muted-foreground mt-1">Next 14 days</span>
            </div>
          </div>
        )}

        {/* Upcoming Action Alerts Banner (if any) */}
        {analytics && analytics.upcoming_events.length > 0 && (
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-400">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Upcoming High-Priority Schedule (Next 14 Days)</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1">
              {analytics.upcoming_events.slice(0, 3).map((event, idx) => (
                <div
                  key={idx}
                  onClick={() => handleSelectApp(event.application_id)}
                  className="p-2.5 rounded-lg border border-border bg-card hover:border-amber-500/40 transition cursor-pointer flex items-start justify-between gap-2 text-xs"
                >
                  <div>
                    <span className="font-semibold text-foreground line-clamp-1">{event.title}</span>
                    <span className="text-muted-foreground text-[11px] flex items-center gap-1 mt-0.5">
                      <Clock className="w-3 h-3 text-amber-400" />
                      {new Date(event.date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase bg-secondary text-muted-foreground border border-border">
                    {event.type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pipeline Stage Bar */}
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-primary" />
              Pipeline Overview
            </span>
            <span className="text-xs text-muted-foreground">Click a stage to filter</span>
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-9 gap-2">
            {pipelineStages.map((stage) => {
              const conf = STATUS_CONFIG[stage];
              const count = analytics?.status_distribution[stage] || 0;
              const isSelected = statusFilter === stage;
              return (
                <button
                  key={stage}
                  onClick={() => setStatusFilter(isSelected ? "all" : stage)}
                  className={`p-2.5 rounded-lg border text-left transition flex flex-col justify-between ${
                    isSelected
                      ? "ring-2 ring-primary border-primary bg-primary/10"
                      : "border-border hover:border-border/80 bg-background/50 hover:bg-secondary/40"
                  }`}
                >
                  <span className={`text-[11px] font-medium truncate ${conf.text}`}>
                    {conf.label}
                  </span>
                  <span className="text-lg font-bold text-foreground mt-1">{count}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by job title or company name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Status Filter */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Filter className="w-3.5 h-3.5" />
              <span>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">All Statuses</option>
                {pipelineStages.map((st) => (
                  <option key={st} value={st}>
                    {STATUS_CONFIG[st].label}
                  </option>
                ))}
              </select>
            </div>

            {/* Channel Filter */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span>Channel:</span>
              <select
                value={channelFilter}
                onChange={(e) => setChannelFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">All Channels</option>
                <option value="official_portal">Official Portal</option>
                <option value="email">Direct Email</option>
                <option value="referral">Referral</option>
                <option value="external_form">External Form</option>
                <option value="other">Other Channel</option>
              </select>
            </div>

            {(statusFilter !== "all" || channelFilter !== "all" || searchTerm) && (
              <button
                onClick={() => {
                  setStatusFilter("all");
                  setChannelFilter("all");
                  setSearchTerm("");
                }}
                className="px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground underline transition"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Application List / Table */}
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="p-12 text-center text-muted-foreground text-xs flex flex-col items-center justify-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span>Loading applications...</span>
            </div>
          ) : filteredApps.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mx-auto text-muted-foreground">
                <Briefcase className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">No applications found</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                {searchTerm || statusFilter !== "all" || channelFilter !== "all"
                  ? "No applications matched your current filters. Try resetting the filters."
                  : "You haven't tracked any applications yet. Click 'Track Application' to start your job hunt dashboard."}
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
              >
                <Plus className="w-3.5 h-3.5" /> Track First Application
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border bg-secondary/30 text-muted-foreground font-semibold">
                    <th className="py-3 px-4">Application</th>
                    <th className="py-3 px-3">Company</th>
                    <th className="py-3 px-3">Channel</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Submission</th>
                    <th className="py-3 px-3">Key Dates</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredApps.map((app) => {
                    const stConf = STATUS_CONFIG[app.status];
                    return (
                      <tr
                        key={app.id}
                        onClick={() => handleSelectApp(app.id)}
                        className={`hover:bg-secondary/40 transition cursor-pointer ${
                          selectedAppId === app.id ? "bg-primary/5 border-l-2 border-l-primary" : ""
                        }`}
                      >
                        {/* Title & Links */}
                        <td className="py-3 px-4">
                          <div className="font-semibold text-foreground">{app.title}</div>
                          <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                            {app.application_url ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenLink(app);
                                }}
                                className="inline-flex items-center gap-1 text-primary hover:underline"
                                title="Open application link (tracked)"
                              >
                                <ExternalLink className="w-3 h-3" />
                                {app.link_opened_at ? "Link Opened" : "Open Portal"}
                              </button>
                            ) : null}
                            {app.job_id && (
                              <Link
                                href={`/dashboard/jobs`}
                                onClick={(e) => e.stopPropagation()}
                                className="inline-flex items-center gap-0.5 text-muted-foreground hover:text-foreground"
                              >
                                <Tag className="w-2.5 h-2.5" /> Job Requisition
                              </Link>
                            )}
                          </div>
                        </td>

                        {/* Company */}
                        <td className="py-3 px-3">
                          <span className="font-medium text-foreground">{app.company_name}</span>
                        </td>

                        {/* Channel */}
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded text-[11px] bg-secondary text-muted-foreground border border-border">
                            {CHANNEL_LABELS[app.application_channel] || app.application_channel}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="py-3 px-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${stConf.bg} ${stConf.text} ${stConf.border}`}
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-current" />
                            {stConf.label}
                          </span>
                        </td>

                        {/* Submission */}
                        <td className="py-3 px-3">
                          {app.submission_confirmed ? (
                            <span className="inline-flex items-center gap-1 text-emerald-400 font-medium text-[11px]">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Submitted
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-muted-foreground text-[11px]">
                              <Clock className="w-3.5 h-3.5" /> Draft / Unconfirmed
                            </span>
                          )}
                        </td>

                        {/* Dates */}
                        <td className="py-3 px-3 text-[11px] text-muted-foreground">
                          {app.deadline_at ? (
                            <div className="flex items-center gap-1 text-amber-400">
                              <Calendar className="w-3 h-3" />
                              <span>Due {new Date(app.deadline_at).toLocaleDateString()}</span>
                            </div>
                          ) : app.next_follow_up_at ? (
                            <div className="flex items-center gap-1 text-blue-400">
                              <Clock className="w-3 h-3" />
                              <span>Follow up {new Date(app.next_follow_up_at).toLocaleDateString()}</span>
                            </div>
                          ) : (
                            <span>{new Date(app.created_at).toLocaleDateString()}</span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            <Link
                              href={`/dashboard/application-assistant?application_id=${app.id}${app.job_id ? `&job_id=${app.job_id}` : ""}`}
                              className="px-2 py-1 text-xs rounded border border-primary/30 bg-primary/10 hover:bg-primary/20 text-primary transition inline-flex items-center gap-1 font-medium"
                              title="Prepare with AI Assistant"
                            >
                              <Bot className="w-3 h-3" />
                              Assistant
                            </Link>
                            <button
                              onClick={() => {
                                setQuickStatusApp(app);
                                setTransitionStatus(app.status);
                                setTransitionConfirmSub(app.submission_confirmed);
                              }}
                              className="px-2 py-1 text-xs rounded border border-border bg-background hover:bg-secondary text-foreground transition"
                              title="Update status"
                            >
                              Update Status
                            </button>
                            <button
                              onClick={() => handleSelectApp(app.id)}
                              className="px-2 py-1 text-xs rounded bg-secondary hover:bg-secondary/80 text-foreground transition"
                            >
                              Details
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Slide-over Detail Drawer */}
      {selectedAppId && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-card border-l border-border h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-border flex items-start justify-between gap-3 bg-secondary/30">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                  Application Details
                </span>
                <h2 className="text-base font-bold text-foreground mt-0.5">
                  {appDetail?.title || "Application"}
                </h2>
                <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                  <Building2 className="w-3.5 h-3.5" />
                  {appDetail?.company_name}
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="p-1.5 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 transition"
                  title="Delete Application"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setSelectedAppId(null);
                    setAppDetail(null);
                  }}
                  className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-secondary transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Drawer Body */}
            {isLoadingDetail ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-xs text-muted-foreground">
                <Loader2 className="w-6 h-6 animate-spin text-primary mb-2" />
                <span>Loading application timeline & history...</span>
              </div>
            ) : appDetail ? (
              <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs">
                {/* Status & Pipeline Header Card */}
                <div className="p-4 rounded-xl border border-border bg-secondary/20 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border ${
                          STATUS_CONFIG[appDetail.status].bg
                        } ${STATUS_CONFIG[appDetail.status].text} ${
                          STATUS_CONFIG[appDetail.status].border
                        }`}
                      >
                        <span className="w-2 h-2 rounded-full bg-current" />
                        {STATUS_CONFIG[appDetail.status].label}
                      </span>
                      <span className="text-muted-foreground text-xs">
                        via {CHANNEL_LABELS[appDetail.application_channel]}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <Link
                        href={`/dashboard/application-assistant?application_id=${appDetail.id}${appDetail.job_id ? `&job_id=${appDetail.job_id}` : ""}`}
                        className="px-2.5 py-1 text-xs font-semibold rounded border border-primary/40 bg-primary/10 text-primary hover:bg-primary/20 transition inline-flex items-center gap-1"
                      >
                        <Bot className="w-3.5 h-3.5" /> AI Assistant
                      </Link>
                      <button
                        onClick={() => {
                          setQuickStatusApp(appDetail);
                          setTransitionStatus(appDetail.status);
                          setTransitionConfirmSub(appDetail.submission_confirmed);
                        }}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 transition"
                      >
                        Change Status
                      </button>
                    </div>
                  </div>

                  {/* Submission Flag */}
                  <div className="pt-2 border-t border-border flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Submission Confirmation:</span>
                    {appDetail.submission_confirmed ? (
                      <span className="text-emerald-400 font-semibold flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" /> Confirmed Submitted (
                        {appDetail.applied_at
                          ? new Date(appDetail.applied_at).toLocaleDateString()
                          : "Yes"}
                        )
                      </span>
                    ) : (
                      <span className="text-amber-400 font-medium">Unconfirmed Draft</span>
                    )}
                  </div>

                  {/* Direct Link */}
                  {appDetail.application_url && (
                    <div className="pt-2 border-t border-border flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Portal URL:</span>
                      <button
                        onClick={() => handleOpenLink(appDetail)}
                        className="inline-flex items-center gap-1 text-primary hover:underline font-medium"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        {appDetail.link_opened_at ? "Opened previously" : "Open Application Link"}
                      </button>
                    </div>
                  )}
                </div>

                {/* Deadlines & Follow-ups */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl border border-border bg-card">
                    <span className="text-muted-foreground text-[11px] block">Application Deadline</span>
                    <span className="font-semibold text-foreground text-xs mt-1 block">
                      {appDetail.deadline_at
                        ? new Date(appDetail.deadline_at).toLocaleDateString()
                        : "No deadline specified"}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl border border-border bg-card">
                    <span className="text-muted-foreground text-[11px] block">Next Follow-up</span>
                    <span className="font-semibold text-foreground text-xs mt-1 block">
                      {appDetail.next_follow_up_at
                        ? new Date(appDetail.next_follow_up_at).toLocaleDateString()
                        : "No follow-up set"}
                    </span>
                  </div>
                </div>

                {/* Recruiter / Contact Info */}
                {(appDetail.recruiter_name ||
                  appDetail.recruiter_email ||
                  appDetail.recruiter_phone ||
                  appDetail.recruiter_linkedin_url) && (
                  <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block">
                      Recruiter & Contact Details
                    </span>
                    <div className="space-y-1.5 text-xs">
                      {appDetail.recruiter_name && (
                        <div className="flex items-center gap-2">
                          <User className="w-3.5 h-3.5 text-muted-foreground" />
                          <span className="font-medium text-foreground">
                            {appDetail.recruiter_name}
                          </span>
                        </div>
                      )}
                      {appDetail.recruiter_email && (
                        <div className="flex items-center gap-2">
                          <Mail className="w-3.5 h-3.5 text-muted-foreground" />
                          <a
                            href={`mailto:${appDetail.recruiter_email}`}
                            className="text-primary hover:underline"
                          >
                            {appDetail.recruiter_email}
                          </a>
                        </div>
                      )}
                      {appDetail.recruiter_phone && (
                        <div className="flex items-center gap-2">
                          <Phone className="w-3.5 h-3.5 text-muted-foreground" />
                          <span className="text-foreground">{appDetail.recruiter_phone}</span>
                        </div>
                      )}
                      {appDetail.recruiter_linkedin_url && (
                        <div className="flex items-center gap-2">
                          <LinkIcon className="w-3.5 h-3.5 text-muted-foreground" />
                          <a
                            href={appDetail.recruiter_linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            LinkedIn Profile
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Notes */}
                {appDetail.notes && (
                  <div className="p-4 rounded-xl border border-border bg-card space-y-1">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block">
                      Application Notes
                    </span>
                    <p className="text-xs text-foreground whitespace-pre-wrap">{appDetail.notes}</p>
                  </div>
                )}

                {/* Resume Version Used */}
                {appDetail.resume_id && (
                  <div className="p-3 rounded-xl border border-border bg-secondary/20 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-primary" />
                      <div>
                        <span className="font-semibold text-foreground">Attached Resume</span>
                        <span className="text-muted-foreground text-[11px] block">
                          Version: {appDetail.resume_version_id ? "Specific Version" : "Latest"}
                        </span>
                      </div>
                    </div>
                    <Link
                      href={`/dashboard/resumes`}
                      className="text-xs text-primary font-semibold hover:underline flex items-center gap-1"
                    >
                      View in Studio <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                )}

                {/* Interviews & Assessments Section */}
                <div className="space-y-3 pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                        Interviews & Assessments ({appDetail.interviews.length})
                      </h3>
                      <p className="text-[11px] text-muted-foreground">
                        Structured interview rounds, technical tests and candidate feedback
                      </p>
                    </div>
                    <button
                      onClick={() => setShowScheduleModal(true)}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-purple-600 hover:bg-purple-500 text-white transition flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Schedule Round
                    </button>
                  </div>

                  {appDetail.interviews.length === 0 ? (
                    <div className="p-4 rounded-xl border border-dashed border-border text-center text-muted-foreground text-[11px]">
                      No interviews scheduled yet.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {appDetail.interviews.map((iv) => (
                        <div
                          key={iv.id}
                          className="p-3.5 rounded-xl border border-border bg-card space-y-2"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-foreground text-xs">
                                  Round {iv.round_number}: {iv.title}
                                </span>
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-medium uppercase bg-secondary text-muted-foreground border border-border">
                                  {iv.interview_type}
                                </span>
                              </div>
                              <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-0.5">
                                <Calendar className="w-3 h-3 text-primary" />
                                {new Date(iv.scheduled_at).toLocaleString(undefined, {
                                  dateStyle: "medium",
                                  timeStyle: "short",
                                })}{" "}
                                ({iv.duration_minutes} min)
                              </span>
                            </div>

                            <div className="flex items-center gap-1">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  iv.outcome === "passed"
                                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                    : iv.outcome === "failed"
                                    ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                                    : "bg-secondary text-muted-foreground border border-border"
                                }`}
                              >
                                {iv.outcome || "Pending"}
                              </span>

                              <button
                                onClick={() => {
                                  setUpdatingInterview(iv);
                                  setIvOutcome(iv.outcome || "pending");
                                  setIvFeedback(iv.feedback || "");
                                  setIvNextSteps(iv.next_steps || "");
                                }}
                                className="px-2 py-1 text-[11px] rounded bg-secondary hover:bg-secondary/80 text-foreground transition"
                              >
                                Log Outcome
                              </button>
                            </div>
                          </div>

                          {iv.meeting_url && (
                            <div className="text-[11px]">
                              <a
                                href={iv.meeting_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-primary hover:underline"
                              >
                                <ExternalLink className="w-3 h-3" /> Join Meeting Link
                              </a>
                            </div>
                          )}

                          {iv.feedback && (
                            <div className="p-2 rounded bg-secondary/50 text-[11px] text-foreground">
                              <span className="font-semibold text-muted-foreground block">
                                Feedback / Notes:
                              </span>
                              {iv.feedback}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Activity & Timeline Section */}
                <div className="space-y-3 pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                        Activity Timeline ({appDetail.activities.length})
                      </h3>
                      <p className="text-[11px] text-muted-foreground">
                        Audited event records, status transitions and user notes
                      </p>
                    </div>
                    <button
                      onClick={() => setShowActivityModal(true)}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-secondary hover:bg-secondary/80 text-foreground transition flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add Note
                    </button>
                  </div>

                  <div className="space-y-2 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                    {appDetail.activities.map((act) => (
                      <div key={act.id} className="relative pl-7 text-xs space-y-0.5">
                        <div className="absolute left-2 top-1 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-primary border-2 border-card" />
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-foreground">{act.title}</span>
                          <span className="text-[10px] text-muted-foreground">
                            {new Date(act.occurred_at || act.created_at).toLocaleString()}
                          </span>
                        </div>
                        {act.description && (
                          <p className="text-[11px] text-muted-foreground whitespace-pre-wrap">
                            {act.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Status History Audit */}
                <div className="space-y-2 pt-2 border-t border-border">
                  <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Status Transition History
                  </h4>
                  <div className="space-y-1.5">
                    {appDetail.status_history.map((hist) => (
                      <div
                        key={hist.id}
                        className="p-2 rounded bg-secondary/30 text-[11px] flex items-center justify-between text-muted-foreground"
                      >
                        <div>
                          <span>
                            {hist.from_status ? (
                              <>
                                <span className="font-medium text-foreground">
                                  {STATUS_CONFIG[hist.from_status]?.label || hist.from_status}
                                </span>{" "}
                                &rarr;{" "}
                              </>
                            ) : (
                              "Created as "
                            )}
                            <span className="font-semibold text-foreground">
                              {STATUS_CONFIG[hist.to_status]?.label || hist.to_status}
                            </span>
                          </span>
                          {hist.note && (
                            <span className="block text-muted-foreground italic text-[10px]">
                              &quot;{hist.note}&quot;
                            </span>
                          )}
                        </div>
                        <span className="text-[10px]">
                          {new Date(hist.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* New Application Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="text-base font-bold text-foreground">Track New Application</h3>
                <p className="text-xs text-muted-foreground">
                  Manual application entry with career pipeline provenance
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateApplication} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Application Title / Role <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Early Career Backend Engineer"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Company Name <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Corp"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">
                    Application Channel
                  </label>
                  <select
                    value={newChannel}
                    onChange={(e) => setNewChannel(e.target.value as ApplicationChannel)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="official_portal">Official Portal</option>
                    <option value="email">Direct Email</option>
                    <option value="referral">Referral</option>
                    <option value="external_form">External Form</option>
                    <option value="other">Other Channel</option>
                  </select>
                </div>

                <div>
                  <label className="block text-muted-foreground font-medium mb-1">
                    Initial Status
                  </label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value as ApplicationStatus)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {pipelineStages.map((st) => (
                      <option key={st} value={st}>
                        {STATUS_CONFIG[st].label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Application Portal / Posting URL
                </label>
                <input
                  type="url"
                  placeholder="https://company.com/careers/..."
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">
                    Application Deadline
                  </label>
                  <input
                    type="date"
                    value={newDeadline}
                    onChange={(e) => setNewDeadline(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-muted-foreground font-medium mb-1">
                    Next Follow-up Date
                  </label>
                  <input
                    type="date"
                    value={newFollowUp}
                    onChange={(e) => setNewFollowUp(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              {/* Resume Attached */}
              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Attached Resume Version
                </label>
                <select
                  value={newResumeId}
                  onChange={(e) => setNewResumeId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">None / Unspecified</option>
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.title} (v{r.current_version_number || 1})
                    </option>
                  ))}
                </select>
              </div>

              {/* Recruiter Details */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">
                    Recruiter Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Jane Doe"
                    value={newRecruiterName}
                    onChange={(e) => setNewRecruiterName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-muted-foreground font-medium mb-1">
                    Recruiter Email
                  </label>
                  <input
                    type="email"
                    placeholder="jane@company.com"
                    value={newRecruiterEmail}
                    onChange={(e) => setNewRecruiterEmail(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Personal Notes / Strategy
                </label>
                <textarea
                  rows={2}
                  placeholder="Notes on role requirements, questions for recruiter..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-secondary text-foreground transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 font-semibold transition flex items-center gap-1.5"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving...
                    </>
                  ) : (
                    "Track Application"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Quick Status Update Modal */}
      {quickStatusApp && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div>
                <h3 className="text-sm font-bold text-foreground">Update Application Status</h3>
                <p className="text-xs text-muted-foreground line-clamp-1">
                  {quickStatusApp.title} ({quickStatusApp.company_name})
                </p>
              </div>
              <button
                onClick={() => setQuickStatusApp(null)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-muted-foreground font-medium mb-1">Target Stage</label>
                <select
                  value={transitionStatus}
                  onChange={(e) => setTransitionStatus(e.target.value as ApplicationStatus)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {pipelineStages.map((st) => (
                    <option key={st} value={st}>
                      {STATUS_CONFIG[st].label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Audit / Transition Note (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Received email invite for Round 1"
                  value={transitionNote}
                  onChange={(e) => setTransitionNote(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {transitionStatus === "applied" && (
                <label className="flex items-center gap-2 p-2 rounded bg-secondary/40 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={transitionConfirmSub}
                    onChange={(e) => setTransitionConfirmSub(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary"
                  />
                  <span className="text-[11px] text-foreground">
                    I confirm that I submitted this application on the company portal.
                  </span>
                </label>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setQuickStatusApp(null)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary text-foreground transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUpdateStatus}
                  disabled={isUpdatingStatus}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 font-semibold transition flex items-center gap-1"
                >
                  {isUpdatingStatus ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving...
                    </>
                  ) : (
                    "Save Status"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Interview Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div>
                <h3 className="text-sm font-bold text-foreground">Schedule Interview / Assessment</h3>
                <p className="text-xs text-muted-foreground">{appDetail?.company_name}</p>
              </div>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleScheduleInterview} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">Round Number</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={ivRound}
                    onChange={(e) => setIvRound(Number(e.target.value))}
                    className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">Type</label>
                  <select
                    value={ivType}
                    onChange={(e) => setIvType(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                  >
                    <option value="technical">Technical Round</option>
                    <option value="coding_assessment">Coding Assessment</option>
                    <option value="system_design">System Design</option>
                    <option value="behavioral">Behavioral / HR</option>
                    <option value="hiring_manager">Hiring Manager</option>
                    <option value="take_home">Take-home Task</option>
                    <option value="other">Other Round</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Technical Coding Round with Team"
                  value={ivTitle}
                  onChange={(e) => setIvTitle(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">Date & Time</label>
                  <input
                    type="datetime-local"
                    required
                    value={ivDate}
                    onChange={(e) => setIvDate(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground font-medium mb-1">Duration (min)</label>
                  <input
                    type="number"
                    min={15}
                    step={15}
                    value={ivDuration}
                    onChange={(e) => setIvDuration(Number(e.target.value))}
                    className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                  />
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Meeting URL / Video Link
                </label>
                <input
                  type="url"
                  placeholder="https://meet.google.com/... or Zoom"
                  value={ivUrl}
                  onChange={(e) => setIvUrl(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Interviewers (comma separated)
                </label>
                <input
                  type="text"
                  placeholder="Alice Smith (Staff Engineer), Bob Lee"
                  value={ivInterviewers}
                  onChange={(e) => setIvInterviewers(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Preparation Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Review algorithms, ask about tech stack..."
                  value={ivNotes}
                  onChange={(e) => setIvNotes(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary text-foreground transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isScheduling}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition flex items-center gap-1"
                >
                  {isScheduling ? "Saving..." : "Schedule Round"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Log Interview Outcome Modal */}
      {updatingInterview && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div>
                <h3 className="text-sm font-bold text-foreground">Log Interview Outcome</h3>
                <p className="text-xs text-muted-foreground">{updatingInterview.title}</p>
              </div>
              <button
                onClick={() => setUpdatingInterview(null)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-muted-foreground font-medium mb-1">Outcome</label>
                <select
                  value={ivOutcome}
                  onChange={(e) => setIvOutcome(e.target.value as any)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                >
                  <option value="pending">Pending Decision</option>
                  <option value="passed">Passed / Advanced</option>
                  <option value="failed">Did Not Advance</option>
                  <option value="waived">Waived</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Feedback & Impressions
                </label>
                <textarea
                  rows={3}
                  placeholder="How did the round go? Questions asked, self-assessment..."
                  value={ivFeedback}
                  onChange={(e) => setIvFeedback(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">Next Steps</label>
                <input
                  type="text"
                  placeholder="e.g. Expecting follow-up by Tuesday"
                  value={ivNextSteps}
                  onChange={(e) => setIvNextSteps(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setUpdatingInterview(null)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary text-foreground transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveInterviewOutcome}
                  disabled={isUpdatingInterview}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition"
                >
                  {isUpdatingInterview ? "Saving..." : "Save Outcome"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Activity Modal */}
      {showActivityModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div>
                <h3 className="text-sm font-bold text-foreground">Add Timeline Note / Activity</h3>
                <p className="text-xs text-muted-foreground">{appDetail?.company_name}</p>
              </div>
              <button
                onClick={() => setShowActivityModal(false)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddActivity} className="space-y-3 text-xs">
              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Activity Type
                </label>
                <select
                  value={actType}
                  onChange={(e) => setActType(e.target.value as any)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                >
                  <option value="note">Personal Note</option>
                  <option value="recruiter_contact">Recruiter Communication</option>
                  <option value="follow_up">Follow-Up Sent</option>
                </select>
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sent thank you note to interviewer"
                  value={actTitle}
                  onChange={(e) => setActTitle(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div>
                <label className="block text-muted-foreground font-medium mb-1">
                  Details / Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Add details, notes or summary..."
                  value={actDesc}
                  onChange={(e) => setActDesc(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowActivityModal(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary text-foreground transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAddingActivity}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition"
                >
                  {isAddingActivity ? "Saving..." : "Save Note"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-card border border-destructive/40 rounded-xl shadow-2xl p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-full bg-destructive/10 text-destructive">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-foreground">Delete Application?</h3>
                <p className="text-xs text-muted-foreground">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Deleting this tracked application will delete its timeline events and interview
              records.
              <span className="block mt-1 font-medium text-foreground">
                Your uploaded resumes, job requisitions, and company records will remain completely
                untouched.
              </span>
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary text-foreground text-xs transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteApplication}
                disabled={isDeleting}
                className="px-3.5 py-1.5 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold transition"
              >
                {isDeleting ? "Deleting..." : "Delete Application"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
