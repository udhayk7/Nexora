"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  DollarSign,
  DownloadCloud,
  ExternalLink,
  Filter,
  Globe,
  HelpCircle,
  History,
  Layers,
  Link as LinkIcon,
  Loader2,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Tag,
  Trash2,
  Users,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  Company,
  CompanyListResponse,
  FeedIngestResult,
  Job,
  JobDetail,
  JobDuplicateCheckResponse,
  JobEvidenceType,
  JobFreshnessType,
  JobListResponse,
  JobObservedStatusType,
  JobRecheckResponse,
  JobSource,
  JobSourceType,
  JobStatusType,
  JobVerification,
  JobVerificationStatusType,
  WorkArrangementType,
} from "@/lib/api";

const ROLE_FAMILIES: Record<string, string> = {
  all: "All Role Families",
  backend_engineer: "Backend Engineer",
  frontend_engineer: "Frontend Engineer",
  full_stack_engineer: "Full Stack Engineer",
  ai_ml_engineer: "AI / ML Engineer",
  devops_cloud: "DevOps & Cloud Engineer",
  data_engineer: "Data Engineer",
  qa_engineer: "QA / Test Automation",
  product_manager: "Technical Product Manager",
  other: "Other Engineering",
};

const WORK_ARRANGEMENTS: Record<WorkArrangementType, { label: string; color: string }> = {
  remote: { label: "Remote", color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" },
  hybrid: { label: "Hybrid", color: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20" },
  onsite: { label: "On-site", color: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20" },
  unspecified: { label: "Unspecified", color: "bg-secondary text-muted-foreground border-border" },
};

const VERIFICATION_CONFIG: Record<
  JobVerificationStatusType,
  { label: string; icon: React.ElementType; color: string; bg: string }
> = {
  verified: {
    label: "Verified",
    icon: ShieldCheck,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  corroborated: {
    label: "Corroborated",
    icon: CheckCircle2,
    color: "text-blue-500",
    bg: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  },
  unverified: {
    label: "Unverified",
    icon: HelpCircle,
    color: "text-amber-500",
    bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  },
  expired: {
    label: "Expired",
    icon: Clock,
    color: "text-muted-foreground",
    bg: "bg-secondary text-muted-foreground border-border",
  },
  suspicious: {
    label: "Suspicious",
    icon: AlertTriangle,
    color: "text-destructive",
    bg: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

const FRESHNESS_CONFIG: Record<
  JobFreshnessType,
  { label: string; icon: React.ElementType; color: string; bg: string; description: string }
> = {
  recent: {
    label: "Recent",
    icon: CheckCircle2,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    description: "Checked within last 7 days",
  },
  due_for_review: {
    label: "Due for Review",
    icon: Clock,
    color: "text-amber-500",
    bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    description: "Checked 7-14 days ago",
  },
  stale: {
    label: "Stale",
    icon: AlertTriangle,
    color: "text-rose-500",
    bg: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
    description: "Not checked for over 14 days",
  },
  unknown: {
    label: "Unknown",
    icon: HelpCircle,
    color: "text-muted-foreground",
    bg: "bg-secondary text-muted-foreground border-border",
    description: "No recent availability check recorded",
  },
};

const EVIDENCE_TYPE_LABELS: Record<JobEvidenceType, string> = {
  careers_page: "Company Careers Portal",
  permitted_api: "ATS API Integration",
  announcement: "Official Announcement",
  user_evidence: "Community Verified Evidence",
  other: "Other Corroborated Source",
};

const SOURCE_TYPE_LABELS: Record<JobSourceType, string> = {
  careers_page: "Company Careers Portal",
  official_api: "Official ATS API",
  permitted_feed: "Permitted Public Feed",
  user_added: "User Submission",
  curated_record: "Curated Early-Career Entry",
  other: "Other Permitted Source",
};

export default function JobsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [selectedRole, setSelectedRole] = useState("all");
  const [selectedWorkArrangement, setSelectedWorkArrangement] = useState<string>("all");
  const [selectedVerification, setSelectedVerification] = useState<string>("all");
  const [selectedFreshness, setSelectedFreshness] = useState<string>("all");
  const [selectedJobStatus, setSelectedJobStatus] = useState<string>("active");
  const [selectedSeniority, setSelectedSeniority] = useState("all");
  const [unassociatedOnly, setUnassociatedOnly] = useState(false);
  const [userOnly, setUserOnly] = useState(false);
  const [page, setPage] = useState(1);

  // Data State
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Companies Reference for dropdowns
  const [companiesList, setCompaniesList] = useState<Company[]>([]);

  // Modals & Recheck State
  const [detailJob, setDetailJob] = useState<JobDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showFeedModal, setShowFeedModal] = useState(false);
  const [verifyJobId, setVerifyJobId] = useState<string | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<JobVerificationStatusType>("verified");
  const [verifyJobStatus, setVerifyJobStatus] = useState<JobStatusType>("active");
  const [verifyNotes, setVerifyNotes] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);

  // Recheck & Evidence State
  const [isRechecking, setIsRechecking] = useState(false);
  const [recheckFeedback, setRecheckFeedback] = useState<{
    type: "success" | "warning" | "error";
    message: string;
  } | null>(null);

  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [evidenceOutcome, setEvidenceOutcome] = useState<JobVerificationStatusType>("verified");
  const [evidenceObservedStatus, setEvidenceObservedStatus] =
    useState<JobObservedStatusType>("active");
  const [evidenceType, setEvidenceType] = useState<JobEvidenceType>("careers_page");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [evidenceSummary, setEvidenceSummary] = useState("");
  const [evidenceReason, setEvidenceReason] = useState("");
  const [isSubmittingEvidence, setIsSubmittingEvidence] = useState(false);

  // Add Source State
  const [showAddSource, setShowAddSource] = useState(false);
  const [sourceName, setSourceName] = useState("");
  const [sourceType, setSourceType] = useState<JobSourceType>("careers_page");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceEvidence, setSourceEvidence] = useState("");
  const [isAddingSource, setIsAddingSource] = useState(false);

  // Form State for Adding Job
  const [newTitle, setNewTitle] = useState("");
  const [newCompanyId, setNewCompanyId] = useState<string>("");
  const [newJobUrl, setNewJobUrl] = useState("");
  const [newApplicationUrl, setNewApplicationUrl] = useState("");
  const [newWorkArrangement, setNewWorkArrangement] = useState<WorkArrangementType>("unspecified");
  const [newRoleFamily, setNewRoleFamily] = useState("backend_engineer");
  const [newSeniority, setNewSeniority] = useState("entry_level");
  const [newEmploymentType, setNewEmploymentType] = useState("full_time");
  const [newLocationText, setNewLocationText] = useState("");
  const [newCity, setNewCity] = useState("");
  const [newCountry, setNewCountry] = useState("India");
  const [newSkillsTags, setNewSkillsTags] = useState("");
  const [newSalaryMin, setNewSalaryMin] = useState<string>("");
  const [newSalaryMax, setNewSalaryMax] = useState<string>("");
  const [newSalaryCurrency, setNewSalaryCurrency] = useState("INR");
  const [newSalaryPeriod, setNewSalaryPeriod] = useState("annual");
  const [newDescription, setNewDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [duplicateMatches, setDuplicateMatches] = useState<JobDuplicateCheckResponse | null>(null);

  // Feed Ingestion Form State
  const [feedName, setFeedName] = useState("");
  const [feedSourceUrl, setFeedSourceUrl] = useState("");
  const [feedJsonPayload, setFeedJsonPayload] = useState("");
  const [isIngestingFeed, setIsIngestingFeed] = useState(false);
  const [feedResult, setFeedResult] = useState<FeedIngestResult | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Load companies for select inputs
  useEffect(() => {
    if (user) {
      apiClient<CompanyListResponse>("/api/v1/companies?per_page=100")
        .then((res) => setCompaniesList(res.items))
        .catch(() => {});
    }
  }, [user]);

  const loadJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if (selectedRole !== "all") params.set("role_family", selectedRole);
      if (selectedWorkArrangement !== "all") params.set("work_arrangement", selectedWorkArrangement);
      if (selectedVerification !== "all") params.set("verification_status", selectedVerification);
      if (selectedFreshness !== "all") params.set("freshness", selectedFreshness);
      if (selectedJobStatus !== "all") params.set("job_status", selectedJobStatus);
      if (selectedSeniority !== "all") params.set("seniority", selectedSeniority);
      if (unassociatedOnly) params.set("unassociated_only", "true");
      if (userOnly) params.set("user_only", "true");
      params.set("page", page.toString());
      params.set("per_page", "12");

      const res = await apiClient<JobListResponse>(`/api/v1/jobs?${params.toString()}`);
      setJobs(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to load jobs";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [
    search,
    selectedRole,
    selectedWorkArrangement,
    selectedVerification,
    selectedFreshness,
    selectedJobStatus,
    selectedSeniority,
    unassociatedOnly,
    userOnly,
    page,
  ]);

  useEffect(() => {
    if (user) {
      loadJobs();
    }
  }, [user, loadJobs]);

  const openJobDetail = async (jobId: string) => {
    setIsDetailLoading(true);
    try {
      const detail = await apiClient<JobDetail>(`/api/v1/jobs/${jobId}`);
      setDetailJob(detail);
    } catch {
      alert("Failed to load job details");
    } finally {
      setIsDetailLoading(false);
    }
  };

  const checkDuplicatesLive = async (url: string, title: string, companyId?: string) => {
    if (!url.trim()) {
      setDuplicateMatches(null);
      return;
    }
    try {
      const params = new URLSearchParams({ job_url: url.trim() });
      if (title.trim()) params.set("title", title.trim());
      if (companyId) params.set("company_id", companyId);

      const res = await apiClient<JobDuplicateCheckResponse>(
        `/api/v1/jobs/duplicates/check?${params.toString()}`
      );
      if (res.matches && res.matches.length > 0) {
        setDuplicateMatches(res);
      } else {
        setDuplicateMatches(null);
      }
    } catch {
      // Ignore background check errors
    }
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newJobUrl.trim() || !newDescription.trim()) return;

    setIsSubmitting(true);
    try {
      const skillsTags = newSkillsTags
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      await apiClient("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle.trim(),
          description: newDescription.trim(),
          company_id: newCompanyId || undefined,
          job_url: newJobUrl.trim(),
          application_url: newApplicationUrl.trim() || undefined,
          work_arrangement: newWorkArrangement,
          role_family: newRoleFamily,
          seniority_level: newSeniority,
          employment_type: newEmploymentType,
          location_text: newLocationText.trim() || undefined,
          city: newCity.trim() || undefined,
          country: newCountry.trim() || undefined,
          skills_tags: skillsTags,
          salary_min: newSalaryMin ? parseFloat(newSalaryMin) : undefined,
          salary_max: newSalaryMax ? parseFloat(newSalaryMax) : undefined,
          salary_currency: newSalaryMin || newSalaryMax ? newSalaryCurrency : undefined,
          salary_period: newSalaryMin || newSalaryMax ? newSalaryPeriod : undefined,
        }),
      });

      setShowAddModal(false);
      resetForm();
      loadJobs();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to register job";
      alert(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyJobId || !verifyNotes.trim() || verifyNotes.trim().length < 5) {
      alert("Evidence notes of at least 5 characters are required.");
      return;
    }

    setIsVerifying(true);
    try {
      await apiClient(`/api/v1/jobs/${verifyJobId}/verify`, {
        method: "POST",
        body: JSON.stringify({
          verification_status: verifyStatus,
          job_status: verifyJobStatus,
          verification_notes: verifyNotes.trim(),
        }),
      });

      setVerifyJobId(null);
      setVerifyNotes("");
      loadJobs();
      if (detailJob && detailJob.id === verifyJobId) {
        openJobDetail(verifyJobId);
      }
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to verify job";
      alert(msg);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleRecheckJob = async (jobId: string) => {
    setIsRechecking(true);
    setRecheckFeedback(null);
    try {
      const res = await apiClient<JobRecheckResponse>(`/api/v1/jobs/${jobId}/recheck`, {
        method: "POST",
        body: JSON.stringify({ force_remote_check: true }),
      });

      if (res.recheck_status === "completed") {
        setRecheckFeedback({
          type: "success",
          message: `Recheck complete: ${res.message} (Status: ${res.observed_status})`,
        });
      } else if (res.recheck_status === "manual_evidence_required") {
        setRecheckFeedback({
          type: "warning",
          message: res.message,
        });
      } else {
        setRecheckFeedback({
          type: "error",
          message: `Recheck flagged issue: ${res.message}`,
        });
      }

      loadJobs();
      if (detailJob && detailJob.id === jobId) {
        openJobDetail(jobId);
      }
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Freshness recheck failed";
      setRecheckFeedback({
        type: "error",
        message: msg,
      });
    } finally {
      setIsRechecking(false);
    }
  };

  const handleSubmitEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detailJob || !evidenceReason.trim() || evidenceReason.trim().length < 5) {
      alert("Mandatory rationale of at least 5 characters is required.");
      return;
    }

    setIsSubmittingEvidence(true);
    try {
      const updated = await apiClient<JobDetail>(`/api/v1/jobs/${detailJob.id}/verifications`, {
        method: "POST",
        body: JSON.stringify({
          evidence_type: evidenceType,
          evidence_url: evidenceUrl.trim() || undefined,
          evidence_summary: evidenceSummary.trim() || undefined,
          observed_status: evidenceObservedStatus,
          verification_outcome: evidenceOutcome,
          reason: evidenceReason.trim(),
        }),
      });

      setShowEvidenceModal(false);
      setEvidenceUrl("");
      setEvidenceSummary("");
      setEvidenceReason("");
      setDetailJob(updated);
      setRecheckFeedback({
        type: "success",
        message: `Evidence submitted. Outcome updated to "${evidenceOutcome}".`,
      });
      loadJobs();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Failed to submit verification evidence";
      alert(msg);
    } finally {
      setIsSubmittingEvidence(false);
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detailJob || !sourceName.trim()) return;

    setIsAddingSource(true);
    try {
      await apiClient(`/api/v1/jobs/${detailJob.id}/sources`, {
        method: "POST",
        body: JSON.stringify({
          source_name: sourceName.trim(),
          source_type: sourceType,
          source_url: sourceUrl.trim() || undefined,
          evidence_summary: sourceEvidence.trim() || undefined,
        }),
      });

      setShowAddSource(false);
      setSourceName("");
      setSourceUrl("");
      setSourceEvidence("");
      openJobDetail(detailJob.id);
      loadJobs();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to add source";
      alert(msg);
    } finally {
      setIsAddingSource(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (!detailJob || !confirm("Are you sure you want to delete this provenance citation?")) return;

    try {
      await apiClient(`/api/v1/jobs/${detailJob.id}/sources/${sourceId}`, {
        method: "DELETE",
      });
      openJobDetail(detailJob.id);
      loadJobs();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to delete source";
      alert(msg);
    }
  };

  const handleFeedIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedName.trim() || !feedJsonPayload.trim()) return;

    let parsedRecords: unknown[];
    try {
      const json = JSON.parse(feedJsonPayload);
      if (!Array.isArray(json)) {
        throw new Error("Feed payload must be a JSON array of job objects");
      }
      parsedRecords = json;
    } catch (parseErr: unknown) {
      alert("Invalid JSON format: " + (parseErr instanceof Error ? parseErr.message : "check array format"));
      return;
    }

    setIsIngestingFeed(true);
    try {
      const res = await apiClient<FeedIngestResult>("/api/v1/jobs/ingest/feed", {
        method: "POST",
        body: JSON.stringify({
          feed_name: feedName.trim(),
          source_type: "permitted_feed",
          source_url: feedSourceUrl.trim() || undefined,
          records: parsedRecords,
        }),
      });

      setFeedResult(res);
      loadJobs();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Feed ingestion failed";
      alert(msg);
    } finally {
      setIsIngestingFeed(false);
    }
  };

  const resetForm = () => {
    setNewTitle("");
    setNewCompanyId("");
    setNewJobUrl("");
    setNewApplicationUrl("");
    setNewLocationText("");
    setNewCity("");
    setNewSkillsTags("");
    setNewSalaryMin("");
    setNewSalaryMax("");
    setNewDescription("");
    setDuplicateMatches(null);
  };

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
            <Briefcase className="w-7 h-7 text-primary" /> Job Discovery & Ingestion
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Ingest and explore technical career opportunities with verified company association and audit provenance.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadJobs()}
            className="p-2 rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh listings"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={() => {
              setShowFeedModal(true);
              setFeedResult(null);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary transition-colors"
          >
            <DownloadCloud className="w-4 h-4 text-primary" /> Ingest Feed
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> Add Job
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <section className="p-4 rounded-xl border border-border bg-card mb-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by role title, technologies, city, or description..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            {search && (
              <button
                onClick={() => {
                  setSearch("");
                  setPage(1);
                }}
                className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
            <select
              value={selectedRole}
              onChange={(e) => {
                setSelectedRole(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {Object.entries(ROLE_FAMILIES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>

            <select
              value={selectedWorkArrangement}
              onChange={(e) => {
                setSelectedWorkArrangement(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Arrangements</option>
              <option value="remote">Remote Only</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site</option>
            </select>

            <select
              value={selectedVerification}
              onChange={(e) => {
                setSelectedVerification(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Verification</option>
              <option value="verified">Verified</option>
              <option value="corroborated">Corroborated</option>
              <option value="unverified">Unverified</option>
              <option value="expired">Expired</option>
              <option value="suspicious">Suspicious</option>
            </select>

            <select
              value={selectedFreshness}
              onChange={(e) => {
                setSelectedFreshness(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Freshness</option>
              <option value="recent">Recent (≤7 days)</option>
              <option value="due_for_review">Due for Review (7-14 days)</option>
              <option value="stale">Stale (&gt;14 days)</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>
        </div>

        {/* Secondary Filter Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/60 text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={unassociatedOnly}
                onChange={(e) => {
                  setUnassociatedOnly(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-border text-primary focus:ring-primary/20"
              />
              <span>Unassociated Only (Pending Review)</span>
            </label>

            <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={userOnly}
                onChange={(e) => {
                  setUserOnly(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-border text-primary focus:ring-primary/20"
              />
              <span>My Submissions Only</span>
            </label>
          </div>

          <div className="flex items-center gap-2">
            <span>Status:</span>
            <select
              value={selectedJobStatus}
              onChange={(e) => {
                setSelectedJobStatus(e.target.value);
                setPage(1);
              }}
              className="px-2 py-1 text-xs rounded border border-border bg-background"
            >
              <option value="active">Active Only</option>
              <option value="all">All (Include Closed)</option>
              <option value="expired">Expired</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      {error && (
        <div className="p-4 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-sm flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadJobs()}
            className="text-xs underline hover:no-underline font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-8 h-8 text-primary animate-spin mb-3" />
          <p className="text-sm text-muted-foreground">Searching opportunity index...</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-12 rounded-xl border border-dashed border-border text-center bg-card/40 my-8">
          <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mx-auto mb-4 text-muted-foreground">
            <Briefcase className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-foreground">No job opportunities found</h3>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-6">
            {search || selectedRole !== "all" || selectedWorkArrangement !== "all" || selectedVerification !== "all"
              ? "No job listings match your active filters. Try broadening your criteria or resetting filters."
              : "No job postings have been ingested yet. Add opportunities manually or ingest permitted feeds."}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => {
                setSearch("");
                setSelectedRole("all");
                setSelectedWorkArrangement("all");
                setSelectedVerification("all");
                setSelectedFreshness("all");
                setUnassociatedOnly(false);
                setUserOnly(false);
                setPage(1);
              }}
              className="px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background hover:bg-secondary transition-colors"
            >
              Reset Filters
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" /> Add Opportunity
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {jobs.map((job) => {
              const statusCfg = VERIFICATION_CONFIG[job.verification_status];
              const StatusIcon = statusCfg.icon;
              const workCfg = WORK_ARRANGEMENTS[job.work_arrangement];

              return (
                <div
                  key={job.id}
                  className="rounded-xl border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Top Badges */}
                    <div className="flex items-start justify-between gap-2 mb-2.5">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${workCfg.color}`}>
                          {workCfg.label}
                        </span>

                        {job.seniority_level && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground font-medium capitalize">
                            {job.seniority_level.replace("_", " ")}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 flex-wrap justify-end">
                        {(() => {
                          const fCfg = FRESHNESS_CONFIG[job.freshness || "unknown"];
                          const FIcon = fCfg.icon;
                          return (
                            <div
                              className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${fCfg.bg}`}
                              title={`Freshness: ${fCfg.label} — ${fCfg.description}`}
                            >
                              <FIcon className="w-2.5 h-2.5" />
                              {fCfg.label}
                            </div>
                          );
                        })()}

                        <div
                          className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border ${statusCfg.bg}`}
                          title={job.verification_notes || `Status: ${statusCfg.label}`}
                        >
                          <StatusIcon className="w-3 h-3" />
                          {statusCfg.label}
                        </div>
                      </div>
                    </div>

                    {/* Title */}
                    <h3 className="text-base font-semibold text-foreground tracking-tight line-clamp-1">
                      {job.title}
                    </h3>

                    {/* Company link / name */}
                    <div className="flex items-center gap-1.5 mt-1 text-xs">
                      {job.company ? (
                        <span className="font-medium text-foreground hover:text-primary transition-colors inline-flex items-center gap-1">
                          <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                          {job.company.name}
                        </span>
                      ) : (
                        <span className="text-amber-600 dark:text-amber-400 font-medium inline-flex items-center gap-1 text-[11px]">
                          <AlertTriangle className="w-3 h-3" /> Unassociated Company
                        </span>
                      )}
                    </div>

                    {/* Location & Salary */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground mt-3 pt-2.5 border-t border-border/60">
                      {(job.location_text || job.city || job.country) && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-muted-foreground/80" />
                          {job.location_text || [job.city, job.country].filter(Boolean).join(", ")}
                        </span>
                      )}

                      {/* Explicit salary display only */}
                      {(job.salary_min || job.salary_max) && (
                        <span className="inline-flex items-center gap-1 font-medium text-foreground">
                          <DollarSign className="w-3 h-3 text-emerald-500" />
                          {[
                            job.salary_min ? `${job.salary_currency || ""} ${job.salary_min.toLocaleString()}` : "",
                            job.salary_max ? `${job.salary_currency || ""} ${job.salary_max.toLocaleString()}` : "",
                          ]
                            .filter(Boolean)
                            .join(" - ")}{" "}
                          {job.salary_period ? `/${job.salary_period}` : ""}
                        </span>
                      )}
                    </div>

                    {/* Description excerpt */}
                    <p className="text-xs text-muted-foreground/90 mt-2.5 line-clamp-2 leading-relaxed">
                      {job.description}
                    </p>

                    {/* Skills tags */}
                    {job.skills_tags && job.skills_tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {job.skills_tags.slice(0, 4).map((skill, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/80 text-foreground font-mono"
                          >
                            {skill}
                          </span>
                        ))}
                        {job.skills_tags.length > 4 && (
                          <span className="text-[10px] px-1 py-0.5 rounded text-muted-foreground font-mono">
                            +{job.skills_tags.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Footer & Actions */}
                  <div className="pt-4 mt-4 border-t border-border flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <a
                        href={job.application_url || job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                      >
                        Apply <ArrowUpRight className="w-3 h-3" />
                      </a>

                      <span className="text-[11px] text-muted-foreground inline-flex items-center gap-1">
                        <Layers className="w-3 h-3" /> {job.sources_count}
                      </span>

                      {job.last_checked_at && (
                        <span
                          className="text-[10px] text-muted-foreground/75 hidden sm:inline-flex items-center gap-1"
                          title={`Last checked on ${new Date(job.last_checked_at).toLocaleString()}`}
                        >
                          <Clock className="w-2.5 h-2.5" />
                          {new Date(job.last_checked_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Link
                        href={`/dashboard/applications?action=new&jobId=${job.id}&title=${encodeURIComponent(
                          job.title
                        )}&company=${encodeURIComponent(job.company?.name || "")}&url=${encodeURIComponent(
                          job.application_url || job.job_url || ""
                        )}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-blue-950/70 text-blue-300 border border-blue-800/50 hover:bg-blue-900 transition"
                        title="Track this job in Application Tracker"
                      >
                        <Briefcase className="w-3 h-3 text-blue-400" />
                        Track
                      </Link>

                      <Link
                        href={`/dashboard/resumes/tailor?jobId=${job.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-indigo-950/70 text-indigo-300 border border-indigo-800/50 hover:bg-indigo-900 transition"
                        title="Tailor your resume for this requisition"
                      >
                        <Sparkles className="w-3 h-3 text-indigo-400" />
                        Tailor
                      </Link>

                      <button
                        onClick={() => {
                          setVerifyJobId(job.id);
                          setVerifyStatus(job.verification_status);
                          setVerifyJobStatus(job.job_status);
                          setVerifyNotes(job.verification_notes || "");
                        }}
                        className="px-2 py-1 text-xs rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                        title="Verify status"
                      >
                        Review
                      </button>

                      <button
                        onClick={() => openJobDetail(job.id)}
                        className="px-2.5 py-1 text-xs font-medium rounded bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                      >
                        Details
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between py-4 border-t border-border text-xs text-muted-foreground">
              <span>
                Showing {jobs.length} of {total} jobs
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded border border-border disabled:opacity-40 hover:bg-secondary"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span>
                  Page {page} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="p-1.5 rounded border border-border disabled:opacity-40 hover:bg-secondary"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* JOB DETAIL & PROVENANCE MODAL */}
      {detailJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl space-y-5">
            <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  {/* Freshness Badge */}
                  {(() => {
                    const fCfg = FRESHNESS_CONFIG[detailJob.freshness || "unknown"];
                    const FIcon = fCfg.icon;
                    return (
                      <span
                        className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full border ${fCfg.bg}`}
                        title={fCfg.description}
                      >
                        <FIcon className="w-3 h-3" />
                        Freshness: {fCfg.label}
                      </span>
                    );
                  })()}

                  <span
                    className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full border ${
                      VERIFICATION_CONFIG[detailJob.verification_status].bg
                    }`}
                  >
                    {VERIFICATION_CONFIG[detailJob.verification_status].label}
                  </span>

                  <span className="text-xs px-2 py-0.5 rounded bg-secondary font-medium capitalize">
                    {detailJob.work_arrangement}
                  </span>

                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${
                      detailJob.job_status === "active"
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "bg-secondary text-muted-foreground"
                    }`}
                  >
                    {detailJob.job_status}
                  </span>
                </div>

                <h2 className="text-xl font-bold">{detailJob.title}</h2>
                {detailJob.company ? (
                  <p className="text-xs font-medium text-muted-foreground mt-0.5 flex items-center gap-1">
                    <Building2 className="w-3.5 h-3.5" /> {detailJob.company.name}
                  </p>
                ) : (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                    Unassociated Company (Pending Manual Association)
                  </p>
                )}
              </div>

              <button
                onClick={() => {
                  setDetailJob(null);
                  setRecheckFeedback(null);
                }}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Verification & Freshness Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2.5 p-3 rounded-lg border border-border bg-secondary/30">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleRecheckJob(detailJob.id)}
                  disabled={isRechecking}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-background hover:bg-secondary text-xs font-medium transition-colors disabled:opacity-50"
                  title="Check target URL availability with connection-time SSRF guards"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 text-primary ${isRechecking ? "animate-spin" : ""}`}
                  />
                  {isRechecking ? "Rechecking Status..." : "Recheck Status"}
                </button>

                <button
                  onClick={() => {
                    setEvidenceOutcome(detailJob.verification_status);
                    setEvidenceObservedStatus(
                      detailJob.job_status === "closed" ? "closed" : "active"
                    );
                    setEvidenceType("careers_page");
                    setEvidenceUrl(detailJob.job_url || "");
                    setEvidenceSummary("");
                    setEvidenceReason("");
                    setShowEvidenceModal(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-sm"
                >
                  <ShieldCheck className="w-3.5 h-3.5" /> Submit Evidence
                </button>
              </div>

              <span className="text-[11px] text-muted-foreground">
                Last checked:{" "}
                {detailJob.last_checked_at
                  ? new Date(detailJob.last_checked_at).toLocaleString()
                  : "Never"}
              </span>
            </div>

            {/* Recheck Feedback Banner */}
            {recheckFeedback && (
              <div
                className={`p-3 rounded-lg border text-xs flex items-center justify-between gap-2 animate-in fade-in ${
                  recheckFeedback.type === "success"
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                    : recheckFeedback.type === "warning"
                    ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
                    : "bg-destructive/10 text-destructive border-destructive/20"
                }`}
              >
                <span>{recheckFeedback.message}</span>
                <button
                  onClick={() => setRecheckFeedback(null)}
                  className="p-1 hover:opacity-70 flex-shrink-0"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Freshness & Verification Status Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-lg border border-border bg-secondary/10 text-xs">
              <div>
                <span className="text-[10px] text-muted-foreground block">Freshness Tier</span>
                <span className="font-semibold capitalize text-foreground">
                  {detailJob.freshness?.replace(/_/g, " ") || "Unknown"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-muted-foreground block">Last Verified Date</span>
                <span className="font-semibold text-foreground">
                  {detailJob.last_verified_at
                    ? new Date(detailJob.last_verified_at).toLocaleDateString()
                    : "Pending"}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-muted-foreground block">Verification State</span>
                <span className="font-semibold capitalize text-foreground">
                  {detailJob.verification_status}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-muted-foreground block">Total Audit Checks</span>
                <span className="font-semibold text-foreground">
                  {detailJob.verification_history?.length || 0} checks
                </span>
              </div>
            </div>

            {/* External Links Bar */}
            <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg border border-border bg-secondary/30 text-xs">
              <a
                href={detailJob.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-primary hover:underline font-medium"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Original Job Posting
              </a>

              {detailJob.application_url && detailJob.application_url !== detailJob.job_url && (
                <a
                  href={detailJob.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 hover:underline font-medium"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" /> Direct Application URL
                </a>
              )}
            </div>

            {/* Verification notes */}
            {detailJob.verification_notes && (
              <div className="p-3.5 rounded-lg border border-border bg-secondary/20 text-xs">
                <span className="font-semibold block mb-0.5">Verification & Review Evidence:</span>
                <p className="text-muted-foreground">{detailJob.verification_notes}</p>
                {detailJob.last_verified_at && (
                  <span className="text-[10px] text-muted-foreground/70 block mt-1">
                    Last reviewed: {new Date(detailJob.last_verified_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            )}

            {/* Job Description Text */}
            <div className="space-y-1.5 text-xs">
              <span className="font-semibold text-muted-foreground block">Job Description</span>
              <div className="p-4 rounded-lg border border-border bg-background whitespace-pre-wrap leading-relaxed text-foreground max-h-48 overflow-y-auto">
                {detailJob.description}
              </div>
            </div>

            {/* Verification & Freshness History Timeline */}
            <div className="space-y-3 pt-2 border-t border-border">
              <div>
                <h4 className="text-sm font-semibold flex items-center gap-1.5">
                  <History className="w-4 h-4 text-primary" /> Verification & Freshness History
                </h4>
                <p className="text-[11px] text-muted-foreground">
                  Immutable chronological record of automated availability rechecks and verified
                  evidence reviews.
                </p>
              </div>

              <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                {!detailJob.verification_history || detailJob.verification_history.length === 0 ? (
                  <div className="p-3 rounded-lg border border-dashed border-border text-center text-xs text-muted-foreground">
                    No verification records logged yet. Click &quot;Recheck Status&quot; or &quot;Submit
                    Evidence&quot; to log a verification event.
                  </div>
                ) : (
                  detailJob.verification_history.map((vh) => {
                    const outcomeCfg =
                      VERIFICATION_CONFIG[vh.verification_outcome] ||
                      VERIFICATION_CONFIG.unverified;
                    const VIcon = outcomeCfg.icon;

                    return (
                      <div
                        key={vh.id}
                        className="p-3 rounded-lg border border-border bg-background space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${outcomeCfg.bg}`}
                            >
                              <VIcon className="w-2.5 h-2.5" />
                              {outcomeCfg.label}
                            </span>

                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground font-mono">
                              {vh.verifier_type === "system" ? "System Recheck" : "User Submission"}
                            </span>

                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/60 text-muted-foreground capitalize">
                              Observed: {vh.observed_status}
                            </span>
                          </div>

                          <span className="text-[10px] text-muted-foreground">
                            {new Date(vh.checked_at).toLocaleString()}
                          </span>
                        </div>

                        <p className="text-foreground leading-relaxed text-[11px]">{vh.reason}</p>

                        {(vh.evidence_summary || vh.evidence_url) && (
                          <div className="pt-1 text-[11px] text-muted-foreground flex flex-wrap items-center gap-2 border-t border-border/40 mt-1">
                            {vh.evidence_summary && <span>{vh.evidence_summary}</span>}
                            {vh.evidence_url && (
                              <a
                                href={vh.evidence_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline inline-flex items-center gap-0.5"
                              >
                                <ExternalLink className="w-2.5 h-2.5" /> Source Link
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Provenance Citations */}
            <div className="space-y-3 pt-2 border-t border-border">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-primary" /> Source Provenance & Citations
                  </h4>
                  <p className="text-[11px] text-muted-foreground">
                    Verifiable origin links and ingestion citations for this job opportunity.
                  </p>
                </div>

                <button
                  onClick={() => setShowAddSource(!showAddSource)}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary"
                >
                  {showAddSource ? "Cancel" : "+ Add Citation"}
                </button>
              </div>

              {/* Add Source Form */}
              {showAddSource && (
                <form
                  onSubmit={handleAddSource}
                  className="p-4 rounded-lg border border-border bg-secondary/20 space-y-3 animate-in fade-in text-xs"
                >
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="font-medium text-muted-foreground block mb-1">
                        Source Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={sourceName}
                        onChange={(e) => setSourceName(e.target.value)}
                        placeholder="e.g., Campus Placement Feed 2026"
                        className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                      />
                    </div>

                    <div>
                      <label className="font-medium text-muted-foreground block mb-1">
                        Source Type
                      </label>
                      <select
                        value={sourceType}
                        onChange={(e) => setSourceType(e.target.value as JobSourceType)}
                        className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                      >
                        <option value="careers_page">Careers Page</option>
                        <option value="official_api">Official API</option>
                        <option value="permitted_feed">Permitted Feed</option>
                        <option value="user_added">User Added</option>
                        <option value="curated_record">Curated Record</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="font-medium text-muted-foreground block mb-1">Source URL</label>
                    <input
                      type="url"
                      value={sourceUrl}
                      onChange={(e) => setSourceUrl(e.target.value)}
                      placeholder="https://source-board.org/listing"
                      className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                    />
                  </div>

                  <div>
                    <label className="font-medium text-muted-foreground block mb-1">
                      Evidence / Notes
                    </label>
                    <textarea
                      rows={2}
                      value={sourceEvidence}
                      onChange={(e) => setSourceEvidence(e.target.value)}
                      placeholder="Observed active job posting on official employer portal..."
                      className="w-full px-2.5 py-1.5 rounded border border-border bg-background resize-none"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setShowAddSource(false)}
                      className="px-3 py-1 text-xs rounded border border-border hover:bg-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isAddingSource}
                      className="px-3 py-1 text-xs font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      {isAddingSource ? "Saving..." : "Save Citation"}
                    </button>
                  </div>
                </form>
              )}

              {/* Sources List */}
              <div className="space-y-2">
                {detailJob.sources.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic py-1">No sources attached.</p>
                ) : (
                  detailJob.sources.map((src) => (
                    <div
                      key={src.id}
                      className="p-3 rounded-lg border border-border bg-background flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{src.source_name}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-secondary text-muted-foreground">
                            {SOURCE_TYPE_LABELS[src.source_type]}
                          </span>
                        </div>

                        {src.source_url && (
                          <a
                            href={src.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline inline-flex items-center gap-1 line-clamp-1"
                          >
                            <ExternalLink className="w-3 h-3" /> {src.source_url}
                          </a>
                        )}

                        {src.evidence_summary && (
                          <p className="text-muted-foreground text-[11px]">{src.evidence_summary}</p>
                        )}
                      </div>

                      <button
                        onClick={() => handleDeleteSource(src.id)}
                        className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        title="Delete source"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-border flex items-center justify-between">
              <Link
                href={`/dashboard/applications?action=new&jobId=${detailJob.id}&title=${encodeURIComponent(
                  detailJob.title
                )}&company=${encodeURIComponent(
                  detailJob.company?.name || ""
                )}&url=${encodeURIComponent(
                  detailJob.application_url || detailJob.job_url || ""
                )}`}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1.5 transition"
              >
                <Briefcase className="w-3.5 h-3.5" /> Track Application
              </Link>

              <button
                onClick={() => setDetailJob(null)}
                className="px-4 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ADD JOB MODAL */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-xl w-full max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h2 className="text-lg font-bold">Register Job Opportunity</h2>
                <p className="text-xs text-muted-foreground">
                  Add an early-career technical posting with verified URL and provenance citation.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateJob} className="space-y-3.5">
              <div>
                <label className="font-medium block mb-1">Job Title *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => {
                    setNewTitle(e.target.value);
                    checkDuplicatesLive(newJobUrl, e.target.value, newCompanyId);
                  }}
                  placeholder="e.g., Junior Backend Engineer, SDE 1"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20"
                />
              </div>

              {/* Duplicate check warning */}
              {duplicateMatches && duplicateMatches.matches.length > 0 && (
                <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <AlertTriangle className="w-3.5 h-3.5" /> Duplicate Posting Alert
                  </div>
                  <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                    {duplicateMatches.matches.map((m, idx) => (
                      <li key={idx}>
                        <span className="font-medium">{m.job.title}</span> ({m.reason})
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium block mb-1">Company</label>
                  <select
                    value={newCompanyId}
                    onChange={(e) => {
                      setNewCompanyId(e.target.value);
                      checkDuplicatesLive(newJobUrl, newTitle, e.target.value);
                    }}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="">-- Auto-detect from URL or None --</option>
                    {companiesList.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="font-medium block mb-1">Role Family</label>
                  <select
                    value={newRoleFamily}
                    onChange={(e) => setNewRoleFamily(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    {Object.entries(ROLE_FAMILIES)
                      .filter(([k]) => k !== "all")
                      .map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium block mb-1">Work Arrangement</label>
                  <select
                    value={newWorkArrangement}
                    onChange={(e) => setNewWorkArrangement(e.target.value as WorkArrangementType)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="unspecified">Unspecified</option>
                    <option value="remote">Remote</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="onsite">On-site</option>
                  </select>
                </div>

                <div>
                  <label className="font-medium block mb-1">Seniority Level</label>
                  <select
                    value={newSeniority}
                    onChange={(e) => setNewSeniority(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="entry_level">Entry Level / Early Career</option>
                    <option value="internship">Internship</option>
                    <option value="mid_level">Mid Level</option>
                    <option value="senior">Senior</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-medium block mb-1">Job Posting URL *</label>
                <input
                  type="url"
                  required
                  value={newJobUrl}
                  onChange={(e) => {
                    setNewJobUrl(e.target.value);
                    checkDuplicatesLive(e.target.value, newTitle, newCompanyId);
                  }}
                  placeholder="https://company.com/careers/job-1234"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                />
              </div>

              <div>
                <label className="font-medium block mb-1">Application URL (if distinct)</label>
                <input
                  type="url"
                  value={newApplicationUrl}
                  onChange={(e) => setNewApplicationUrl(e.target.value)}
                  placeholder="https://jobs.lever.co/company/job-1234/apply"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="font-medium block mb-1">Location Text</label>
                  <input
                    type="text"
                    value={newLocationText}
                    onChange={(e) => setNewLocationText(e.target.value)}
                    placeholder="Bengaluru, Karnataka"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">City</label>
                  <input
                    type="text"
                    value={newCity}
                    onChange={(e) => setNewCity(e.target.value)}
                    placeholder="Bengaluru"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">Country</label>
                  <input
                    type="text"
                    value={newCountry}
                    onChange={(e) => setNewCountry(e.target.value)}
                    placeholder="India"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium block mb-1">Skills & Tech Tags (comma separated)</label>
                <input
                  type="text"
                  value={newSkillsTags}
                  onChange={(e) => setNewSkillsTags(e.target.value)}
                  placeholder="Python, FastAPI, Docker, SQL"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                />
              </div>

              {/* Explicit Salary Fields */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div>
                  <label className="font-medium block mb-1">Salary Min</label>
                  <input
                    type="number"
                    value={newSalaryMin}
                    onChange={(e) => setNewSalaryMin(e.target.value)}
                    placeholder="800000"
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">Salary Max</label>
                  <input
                    type="number"
                    value={newSalaryMax}
                    onChange={(e) => setNewSalaryMax(e.target.value)}
                    placeholder="1200000"
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">Currency</label>
                  <input
                    type="text"
                    value={newSalaryCurrency}
                    onChange={(e) => setNewSalaryCurrency(e.target.value)}
                    placeholder="INR"
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">Period</label>
                  <select
                    value={newSalaryPeriod}
                    onChange={(e) => setNewSalaryPeriod(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-background"
                  >
                    <option value="annual">Annual</option>
                    <option value="monthly">Monthly</option>
                    <option value="hourly">Hourly</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-medium block mb-1">Job Description Text *</label>
                <textarea
                  rows={4}
                  required
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Paste the official job description verbatim..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? "Registering..." : "Register Job"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VERIFY / STATUS MODAL */}
      {verifyJobId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full rounded-xl border border-border bg-card p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-base font-bold flex items-center gap-1.5">
                <ShieldCheck className="w-5 h-5 text-primary" /> Update Verification & Active State
              </h2>
              <button
                onClick={() => setVerifyJobId(null)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleVerify} className="space-y-3.5">
              <div>
                <label className="font-medium block mb-1">Verification Status</label>
                <select
                  value={verifyStatus}
                  onChange={(e) => setVerifyStatus(e.target.value as JobVerificationStatusType)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                >
                  <option value="verified">Verified (Official listing confirmed active)</option>
                  <option value="corroborated">Corroborated (Multiple verified signals)</option>
                  <option value="unverified">Unverified (Pending confirmation)</option>
                  <option value="expired">Expired (Job closed by employer)</option>
                  <option value="suspicious">Suspicious (Misleading or scam listing)</option>
                </select>
              </div>

              <div>
                <label className="font-medium block mb-1">Job Listing Status</label>
                <select
                  value={verifyJobStatus}
                  onChange={(e) => setVerifyJobStatus(e.target.value as JobStatusType)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                >
                  <option value="active">Active</option>
                  <option value="closed">Closed</option>
                  <option value="expired">Expired</option>
                  <option value="suspicious">Suspicious</option>
                </select>
              </div>

              <div>
                <label className="font-medium block mb-1">
                  Evidence Notes * (Minimum 5 characters)
                </label>
                <textarea
                  rows={3}
                  required
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  placeholder="e.g., Active campus recruitment listing verified on employer ATS..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setVerifyJobId(null)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isVerifying}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {isVerifying ? "Updating..." : "Confirm Status"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SUBMIT VERIFICATION EVIDENCE MODAL */}
      {showEvidenceModal && detailJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-lg w-full rounded-xl border border-border bg-card p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h2 className="text-base font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-5 h-5 text-primary" /> Submit Verification Evidence
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  Record verifiable proof, observed availability, and evidence rationale for{" "}
                  {detailJob.title}.
                </p>
              </div>
              <button
                onClick={() => setShowEvidenceModal(false)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitEvidence} className="space-y-3.5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium block mb-1">Verification Outcome *</label>
                  <select
                    value={evidenceOutcome}
                    onChange={(e) =>
                      setEvidenceOutcome(e.target.value as JobVerificationStatusType)
                    }
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="verified">Verified (Confirmed Official)</option>
                    <option value="corroborated">Corroborated (Multiple Signals)</option>
                    <option value="unverified">Unverified (Pending Review)</option>
                    <option value="expired">Expired (Closed by Employer)</option>
                    <option value="suspicious">Suspicious (Questionable/Spam)</option>
                  </select>
                </div>

                <div>
                  <label className="font-medium block mb-1">Observed Listing State *</label>
                  <select
                    value={evidenceObservedStatus}
                    onChange={(e) =>
                      setEvidenceObservedStatus(e.target.value as JobObservedStatusType)
                    }
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="active">Active (Currently Open)</option>
                    <option value="closed">Closed (No longer accepting)</option>
                    <option value="removed">Removed (404/Page Deleted)</option>
                    <option value="expired">Expired (Deadline Passed)</option>
                    <option value="unknown">Unknown / Inconclusive</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-medium block mb-1">Evidence Source Type *</label>
                <select
                  value={evidenceType}
                  onChange={(e) => setEvidenceType(e.target.value as JobEvidenceType)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                >
                  <option value="careers_page">Official Careers Page</option>
                  <option value="permitted_api">ATS API Endpoint</option>
                  <option value="announcement">Official Announcement</option>
                  <option value="user_evidence">Community / User Submission</option>
                  <option value="other">Other Corroborated Source</option>
                </select>
              </div>

              <div>
                <label className="font-medium block mb-1">Evidence URL (Optional)</label>
                <input
                  type="url"
                  value={evidenceUrl}
                  onChange={(e) => setEvidenceUrl(e.target.value)}
                  placeholder="https://employer.com/careers/listing"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                />
              </div>

              <div>
                <label className="font-medium block mb-1">Evidence Summary (Optional)</label>
                <input
                  type="text"
                  value={evidenceSummary}
                  onChange={(e) => setEvidenceSummary(e.target.value)}
                  placeholder="e.g., Confirmed active on Greenhouse ATS board"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                />
              </div>

              <div>
                <label className="font-medium block mb-1">
                  Mandatory Explanation Rationale * (Minimum 5 characters)
                </label>
                <textarea
                  rows={3}
                  required
                  value={evidenceReason}
                  onChange={(e) => setEvidenceReason(e.target.value)}
                  placeholder="Explain why this verification outcome was assigned, citing specific verified indicators..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowEvidenceModal(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEvidence}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {isSubmittingEvidence ? "Recording..." : "Save Verification"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FEED BATCH INGEST MODAL */}
      {showFeedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-xl w-full max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h2 className="text-base font-bold flex items-center gap-1.5">
                  <DownloadCloud className="w-5 h-5 text-primary" /> Permitted Feed Ingestion
                </h2>
                <p className="text-xs text-muted-foreground">
                  Batch ingest structured job opportunities from permitted feeds with deduplication.
                </p>
              </div>
              <button
                onClick={() => setShowFeedModal(false)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {feedResult ? (
              <div className="space-y-4 animate-in fade-in">
                <div className="p-4 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                  <h4 className="font-semibold text-sm mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Ingestion Completed
                  </h4>
                  <p className="text-xs">
                    Processed {feedResult.total_processed} records from feed &apos;{feedResult.feed_name}&apos;.
                  </p>
                  <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                    <div className="p-2 rounded bg-background border border-border">
                      <span className="text-lg font-bold text-foreground">{feedResult.created_count}</span>
                      <span className="text-[10px] text-muted-foreground block">Created</span>
                    </div>
                    <div className="p-2 rounded bg-background border border-border">
                      <span className="text-lg font-bold text-foreground">{feedResult.updated_count}</span>
                      <span className="text-[10px] text-muted-foreground block">Updated (Idempotent)</span>
                    </div>
                    <div className="p-2 rounded bg-background border border-border">
                      <span className="text-lg font-bold text-destructive">{feedResult.errors_count}</span>
                      <span className="text-[10px] text-muted-foreground block">Errors</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={() => {
                      setShowFeedModal(false);
                      setFeedResult(null);
                    }}
                    className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground font-medium"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleFeedIngest} className="space-y-3.5">
                <div>
                  <label className="font-medium block mb-1">Feed / Dataset Name *</label>
                  <input
                    type="text"
                    required
                    value={feedName}
                    onChange={(e) => setFeedName(e.target.value)}
                    placeholder="e.g., Campus Placement Feed 2026"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">Source URL (optional)</label>
                  <input
                    type="url"
                    value={feedSourceUrl}
                    onChange={(e) => setFeedSourceUrl(e.target.value)}
                    placeholder="https://feed-provider.org/jobs.json"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium block mb-1">
                    JSON Records Array * (Array of Job Objects)
                  </label>
                  <textarea
                    rows={6}
                    required
                    value={feedJsonPayload}
                    onChange={(e) => setFeedJsonPayload(e.target.value)}
                    placeholder='[{"title": "Junior Python Dev", "description": "...", "job_url": "https://..."}]'
                    className="w-full font-mono text-[11px] px-3 py-2 rounded-lg border border-border bg-background resize-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setShowFeedModal(false)}
                    className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isIngestingFeed}
                    className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                  >
                    {isIngestingFeed ? "Ingesting..." : "Start Ingestion"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

