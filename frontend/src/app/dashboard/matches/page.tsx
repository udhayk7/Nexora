"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  Briefcase,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  DollarSign,
  Eye,
  EyeOff,
  Filter,
  HelpCircle,
  Info,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Tag,
  ThumbsDown,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  GapSignal,
  JobMatch,
  JobMatchFilterParams,
  matchingApi,
  PositiveSignal,
  ResumeSummary,
  ResumeVersionSummary,
  ScoreBreakdown,
  UserMatchingPreference,
  UserMatchingPreferenceUpdate,
} from "@/lib/api";

const FRESHNESS_BADGES: Record<
  string,
  { label: string; icon: React.ElementType; color: string; bg: string }
> = {
  recent: {
    label: "Recent",
    icon: CheckCircle2,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  due_for_review: {
    label: "Due Review",
    icon: Clock,
    color: "text-amber-500",
    bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  },
  stale: {
    label: "Stale",
    icon: AlertTriangle,
    color: "text-rose-500",
    bg: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
  },
  unknown: {
    label: "Unverified",
    icon: HelpCircle,
    color: "text-muted-foreground",
    bg: "bg-secondary text-muted-foreground border-border",
  },
};

const VERIFICATION_BADGES: Record<
  string,
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
  suspicious: {
    label: "Suspicious",
    icon: AlertTriangle,
    color: "text-destructive",
    bg: "bg-destructive/10 text-destructive border-destructive/20",
  },
  expired: {
    label: "Closed/Expired",
    icon: Clock,
    color: "text-muted-foreground",
    bg: "bg-secondary text-muted-foreground border-border",
  },
};

export default function MatchesPage() {
  const router = useRouter();
  const { user, isLoading: isAuthLoading } = useAuth();

  // State
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [totalMatches, setTotalMatches] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [selectedRoleFamily, setSelectedRoleFamily] = useState("all");
  const [selectedArrangement, setSelectedArrangement] = useState("all");
  const [selectedFreshness, setSelectedFreshness] = useState("all");
  const [selectedVerification, setSelectedVerification] = useState("all");
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0);
  const [savedOnly, setSavedOnly] = useState(false);
  const [includeDismissed, setIncludeDismissed] = useState(false);
  const [sortBy, setSortBy] = useState<"score" | "date">("score");

  // Preferences & Modals
  const [preferences, setPreferences] = useState<UserMatchingPreference | null>(null);
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  const [isSavingPrefs, setIsSavingPrefs] = useState(false);

  // Detailed Match Modal
  const [detailMatch, setDetailMatch] = useState<JobMatch | null>(null);

  // Run Matches Modal
  const [showRunModal, setShowRunModal] = useState(false);
  const [isRunningMatches, setIsRunningMatches] = useState(false);
  const [resumes, setResumes] = useState<any[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>("");
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [runThreshold, setRunThreshold] = useState<number>(40);
  const [runFeedback, setRunFeedback] = useState<string | null>(null);

  // Editable Preference Fields
  const [prefRolesInput, setPrefRolesInput] = useState("");
  const [prefLocationsInput, setPrefLocationsInput] = useState("");
  const [prefArrangements, setPrefArrangements] = useState<string[]>([]);
  const [prefMinSalary, setPrefMinSalary] = useState<string>("");
  const [prefSalaryPeriod, setPrefSalaryPeriod] = useState<string>("annual");
  const [prefSkillsInput, setPrefSkillsInput] = useState("");
  const [excludedRolesInput, setExcludedRolesInput] = useState("");
  const [excludedTermsInput, setExcludedTermsInput] = useState("");
  const [excludedIndustriesInput, setExcludedIndustriesInput] = useState("");

  // Auth gate
  useEffect(() => {
    if (!isAuthLoading && !user) {
      router.push("/login");
    }
  }, [user, isAuthLoading, router]);

  // Load Preferences
  const loadPreferences = useCallback(async () => {
    try {
      const prefs = await matchingApi.getPreferences();
      setPreferences(prefs);
      // Populate edit fields
      setPrefRolesInput(prefs.target_role_families.join(", "));
      setPrefLocationsInput(prefs.preferred_locations.join(", "));
      setPrefArrangements(prefs.work_arrangement_preferences || []);
      setPrefMinSalary(prefs.min_salary ? String(prefs.min_salary) : "");
      setPrefSalaryPeriod(prefs.salary_period || "annual");
      setPrefSkillsInput((prefs.preferred_skills || []).join(", "));
      setExcludedRolesInput((prefs.excluded_roles || []).join(", "));
      setExcludedTermsInput((prefs.excluded_terms || []).join(", "));
      setExcludedIndustriesInput((prefs.excluded_industries || []).join(", "));
    } catch {
      // Preferences may not be populated yet
    }
  }, []);

  // Load Matches
  const loadMatches = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const params: JobMatchFilterParams = {
        page,
        per_page: 12,
        sort_by: sortBy,
        include_dismissed: includeDismissed,
      };
      if (selectedRoleFamily !== "all") params.role_family = selectedRoleFamily;
      if (selectedArrangement !== "all") params.work_arrangement = selectedArrangement;
      if (selectedFreshness !== "all") params.freshness = selectedFreshness;
      if (selectedVerification !== "all") params.verification_status = selectedVerification;
      if (minScoreFilter > 0) params.min_score = minScoreFilter;
      if (savedOnly) params.is_saved = true;

      const res = await matchingApi.listMatches(params);
      setMatches(res.items);
      setTotalMatches(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Failed to load job matches";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [
    page,
    sortBy,
    selectedRoleFamily,
    selectedArrangement,
    selectedFreshness,
    selectedVerification,
    minScoreFilter,
    savedOnly,
    includeDismissed,
  ]);

  useEffect(() => {
    if (user) {
      loadPreferences();
      loadMatches();
    }
  }, [user, loadPreferences, loadMatches]);

  // Load User Resumes for Run Modal
  const loadResumes = async () => {
    try {
      const res = await apiClient<ResumeSummary[]>("/resumes");
      setResumes(res);
      if (res.length > 0) {
        setSelectedResumeId(res[0].id);
        if (res[0].current_version_id) {
          setSelectedVersionId(res[0].current_version_id);
        }
      }
    } catch {
      // ignore
    }
  };

  const openRunModal = () => {
    loadResumes();
    setRunFeedback(null);
    setShowRunModal(true);
  };

  // Toggle Save Match
  const toggleSaveMatch = async (match: JobMatch) => {
    const newState = !match.is_saved;
    try {
      const updated = await matchingApi.updateMatchState(match.id, { is_saved: newState });
      setMatches((prev) => prev.map((m) => (m.id === match.id ? updated : m)));
      if (detailMatch?.id === match.id) setDetailMatch(updated);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Failed to update save state";
      alert(msg);
    }
  };

  // Toggle Dismiss Match
  const toggleDismissMatch = async (match: JobMatch) => {
    const newState = !match.is_dismissed;
    try {
      const updated = await matchingApi.updateMatchState(match.id, { is_dismissed: newState });
      if (!includeDismissed && newState) {
        setMatches((prev) => prev.filter((m) => m.id !== match.id));
        setTotalMatches((t) => Math.max(0, t - 1));
      } else {
        setMatches((prev) => prev.map((m) => (m.id === match.id ? updated : m)));
      }
      if (detailMatch?.id === match.id) setDetailMatch(updated);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Failed to update dismiss state";
      alert(msg);
    }
  };

  // Save Preferences
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPrefs(true);
    try {
      const splitTags = (str: string) =>
        str
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);

      const payload: UserMatchingPreferenceUpdate = {
        target_role_families: splitTags(prefRolesInput),
        preferred_locations: splitTags(prefLocationsInput),
        preferred_work_arrangements: prefArrangements,
        min_salary: prefMinSalary ? parseFloat(prefMinSalary) : null,
        salary_period: prefSalaryPeriod,
        preferred_skills: splitTags(prefSkillsInput),
        excluded_roles: splitTags(excludedRolesInput),
        excluded_terms: splitTags(excludedTermsInput),
        excluded_industries: splitTags(excludedIndustriesInput),
      };

      const updated = await matchingApi.updatePreferences(payload);
      setPreferences(updated);
      setShowPreferencesModal(false);
      loadMatches();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Failed to save preferences";
      alert(msg);
    } finally {
      setIsSavingPrefs(false);
    }
  };

  // Execute Match Run
  const handleExecuteRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRunningMatches(true);
    setRunFeedback(null);
    try {
      const result = await matchingApi.runMatches({
        resume_id: selectedResumeId || undefined,
        version_id: selectedVersionId || undefined,
        min_score_threshold: runThreshold,
      });

      setRunFeedback(
        `Successfully generated ${result.matches_saved} matches across active listings.`
      );
      setTimeout(() => {
        setShowRunModal(false);
        loadMatches();
      }, 1200);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String(err.message)
          : "Failed to run matching engine";
      setRunFeedback(`Error: ${msg}`);
    } finally {
      setIsRunningMatches(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
    if (score >= 65) return "text-blue-500 bg-blue-500/10 border-blue-500/20";
    if (score >= 50) return "text-amber-500 bg-amber-500/10 border-amber-500/20";
    return "text-rose-500 bg-rose-500/10 border-rose-500/20";
  };

  if (isAuthLoading || !user) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Validating session...</p>
      </main>
    );
  }

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
            <Sparkles className="w-7 h-7 text-primary" /> Personalized Job Matching & Ranking
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Explainable, deterministic alignment between your analyzed resume, career preferences, and verified opportunities.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadMatches()}
            className="p-2 rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh results"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={() => setShowPreferencesModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary transition-colors"
          >
            <Settings2 className="w-4 h-4 text-primary" /> Preferences
          </button>

          <button
            onClick={openRunModal}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Sparkles className="w-4 h-4" /> Run Matches
          </button>
        </div>
      </div>

      {/* Preferences Summary Pill Bar */}
      {preferences && (
        <div className="mb-6 p-3.5 rounded-xl border border-border bg-card/60 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-muted-foreground flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Active Target Criteria:
            </span>
            {preferences.target_role_families?.length > 0 ? (
              preferences.target_role_families.map((r, i) => (
                <span key={i} className="px-2 py-0.5 rounded-md bg-primary/10 text-primary font-medium">
                  {r}
                </span>
              ))
            ) : (
              <span className="text-muted-foreground italic">All Role Families</span>
            )}

            {preferences.work_arrangement_preferences?.map((arr, i) => (
              <span key={i} className="px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground">
                {arr.charAt(0).toUpperCase() + arr.slice(1)}
              </span>
            ))}

            {preferences.min_salary && (
              <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium">
                Min: {preferences.salary_currency || "$"} {preferences.min_salary.toLocaleString()} / {preferences.salary_period || "yr"}
              </span>
            )}

            {preferences.preferred_skills?.length > 0 && (
              <span className="px-2 py-0.5 rounded-md bg-secondary text-muted-foreground">
                Priority Skills: {preferences.preferred_skills.slice(0, 3).join(", ")}
                {preferences.preferred_skills.length > 3 && ` +${preferences.preferred_skills.length - 3}`}
              </span>
            )}
          </div>

          <button
            onClick={() => setShowPreferencesModal(true)}
            className="text-primary hover:underline font-medium text-xs ml-auto"
          >
            Edit Preferences →
          </button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl border border-border bg-card mb-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {/* Work Arrangement */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1">
              Work Arrangement
            </label>
            <select
              value={selectedArrangement}
              onChange={(e) => {
                setSelectedArrangement(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs px-2.5 py-1.5 rounded-md border border-input bg-background focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Arrangements</option>
              <option value="remote">Remote Only</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site</option>
            </select>
          </div>

          {/* Freshness */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1">
              Freshness
            </label>
            <select
              value={selectedFreshness}
              onChange={(e) => {
                setSelectedFreshness(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs px-2.5 py-1.5 rounded-md border border-input bg-background focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Freshness</option>
              <option value="recent">Recent (Checked &lt;7d)</option>
              <option value="due_for_review">Due for Review</option>
              <option value="stale">Stale (&gt;14d)</option>
            </select>
          </div>

          {/* Verification */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1">
              Trust Status
            </label>
            <select
              value={selectedVerification}
              onChange={(e) => {
                setSelectedVerification(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs px-2.5 py-1.5 rounded-md border border-input bg-background focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Statuses</option>
              <option value="verified">Verified Official</option>
              <option value="corroborated">Corroborated</option>
              <option value="unverified">Unverified</option>
            </select>
          </div>

          {/* Min Score Threshold */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1 flex justify-between">
              <span>Min Score</span>
              <span className="font-semibold text-foreground">{minScoreFilter}%</span>
            </label>
            <input
              type="range"
              min="0"
              max="90"
              step="5"
              value={minScoreFilter}
              onChange={(e) => {
                setMinScoreFilter(parseInt(e.target.value));
                setPage(1);
              }}
              className="w-full accent-primary h-1.5 bg-secondary rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Sort By */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as "score" | "date");
                setPage(1);
              }}
              className="w-full text-xs px-2.5 py-1.5 rounded-md border border-input bg-background focus:ring-1 focus:ring-primary"
            >
              <option value="score">Highest Match Score</option>
              <option value="date">Most Recently Ingested</option>
            </select>
          </div>

          {/* Toggles */}
          <div className="flex items-end gap-3 pb-0.5">
            <button
              onClick={() => {
                setSavedOnly(!savedOnly);
                setPage(1);
              }}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                savedOnly
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-muted-foreground border-input hover:bg-secondary"
              }`}
            >
              <Bookmark className="w-3.5 h-3.5" /> Saved
            </button>

            <button
              onClick={() => {
                setIncludeDismissed(!includeDismissed);
                setPage(1);
              }}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                includeDismissed
                  ? "bg-secondary text-foreground border-border"
                  : "bg-background text-muted-foreground border-input hover:bg-secondary"
              }`}
              title="Show previously dismissed listings"
            >
              {includeDismissed ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              Dismissed
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="py-24 text-center">
          <div className="w-7 h-7 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Evaluating opportunity alignment...</p>
        </div>
      ) : errorMessage ? (
        <div className="p-8 rounded-xl border border-destructive/30 bg-destructive/5 text-center max-w-lg mx-auto">
          <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
          <h3 className="text-base font-semibold text-destructive">Unable to load matches</h3>
          <p className="text-xs text-muted-foreground mt-1 mb-4">{errorMessage}</p>
          <button
            onClick={openRunModal}
            className="px-4 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground"
          >
            Run New Match Scan
          </button>
        </div>
      ) : matches.length === 0 ? (
        <div className="py-20 text-center rounded-xl border border-dashed border-border bg-card/30">
          <Sparkles className="w-10 h-10 text-muted-foreground/60 mx-auto mb-3" />
          <h3 className="text-base font-semibold">No career matches found</h3>
          <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1 mb-6">
            We haven&apos;t generated matches for your profile yet, or active filters have narrowed the list. Run the matching engine to discover relevant technical roles.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => {
                setSelectedRoleFamily("all");
                setSelectedArrangement("all");
                setSelectedFreshness("all");
                setSelectedVerification("all");
                setMinScoreFilter(0);
                setSavedOnly(false);
                setIncludeDismissed(false);
              }}
              className="px-3 py-2 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
            >
              Reset Filters
            </button>
            <button
              onClick={openRunModal}
              className="px-4 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground shadow-sm hover:bg-primary/90"
            >
              Run Match Scan
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span>
              Showing {matches.length} of {totalMatches} ranked opportunities
            </span>
            <span>Deterministic Engine {matches[0]?.engine_version || "v1.0"}</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {matches.map((match) => {
              const job = match.job;
              const bd = match.score_breakdown;
              const freshBadge = FRESHNESS_BADGES[job?.freshness || "unknown"];
              const FreshIcon = freshBadge?.icon || HelpCircle;
              const verifyBadge = VERIFICATION_BADGES[job?.verification_status || "unverified"];
              const VerifyIcon = verifyBadge?.icon || HelpCircle;

              return (
                <div
                  key={match.id}
                  className={`p-5 rounded-xl border transition-all flex flex-col justify-between ${
                    match.is_dismissed
                      ? "opacity-60 bg-secondary/30 border-dashed border-border"
                      : "bg-card border-border hover:border-primary/40 shadow-sm"
                  }`}
                >
                  <div>
                    {/* Top Row: Score Badge + Actions */}
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`flex flex-col items-center justify-center w-14 h-14 rounded-xl border font-bold ${getScoreColor(
                            match.match_score
                          )}`}
                        >
                          <span className="text-lg leading-none">{Math.round(match.match_score)}</span>
                          <span className="text-[10px] font-normal uppercase opacity-75">Score</span>
                        </div>

                        <div>
                          <h3 className="text-base font-semibold text-foreground line-clamp-1">
                            {job?.title || "Requisition"}
                          </h3>
                          <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                            <Building2 className="w-3.5 h-3.5" />
                            <span className="font-medium text-foreground/80">
                              {job?.company?.name || "Direct Requisition"}
                            </span>
                            {job?.city && (
                              <>
                                <span>•</span>
                                <span className="flex items-center gap-0.5">
                                  <MapPin className="w-3 h-3" /> {job.city}
                                  {job.country ? `, ${job.country}` : ""}
                                </span>
                              </>
                            )}
                          </p>
                        </div>
                      </div>

                      {/* Bookmark & Dismiss */}
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => toggleSaveMatch(match)}
                          className={`p-1.5 rounded-lg border transition-colors ${
                            match.is_saved
                              ? "bg-primary text-primary-foreground border-primary"
                              : "border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                          }`}
                          title={match.is_saved ? "Remove from saved" : "Save opportunity"}
                        >
                          {match.is_saved ? (
                            <BookmarkCheck className="w-4 h-4" />
                          ) : (
                            <Bookmark className="w-4 h-4" />
                          )}
                        </button>

                        <button
                          onClick={() => toggleDismissMatch(match)}
                          className={`p-1.5 rounded-lg border transition-colors ${
                            match.is_dismissed
                              ? "bg-rose-500/10 text-rose-600 border-rose-500/20"
                              : "border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                          }`}
                          title={match.is_dismissed ? "Restore match" : "Dismiss from matches"}
                        >
                          <ThumbsDown className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Meta Badges */}
                    <div className="flex flex-wrap items-center gap-1.5 mb-3.5 text-[11px]">
                      {job?.work_arrangement && (
                        <span className="px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground font-medium">
                          {job.work_arrangement.charAt(0).toUpperCase() + job.work_arrangement.slice(1)}
                        </span>
                      )}

                      {job?.seniority_level && (
                        <span className="px-2 py-0.5 rounded-md bg-secondary text-muted-foreground font-medium">
                          {job.seniority_level.replace("_", " ")}
                        </span>
                      )}

                      {/* Salary Badge */}
                      {job?.salary_min ? (
                        <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium">
                          {job.salary_currency || "$"} {job.salary_min.toLocaleString()}
                          {job.salary_max ? ` - ${job.salary_max.toLocaleString()}` : "+"} /{" "}
                          {job.salary_period || "yr"}
                        </span>
                      ) : (
                        <span
                          className="px-2 py-0.5 rounded-md bg-secondary/80 text-muted-foreground italic"
                          title="Salary was not published on this listing. Nexora never penalizes undisclosed compensation."
                        >
                          Salary Undisclosed (No Penalty)
                        </span>
                      )}

                      {/* Freshness Badge */}
                      {freshBadge && (
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border font-medium ${freshBadge.bg}`}
                        >
                          <FreshIcon className="w-3 h-3" /> {freshBadge.label}
                        </span>
                      )}

                      {/* Verification Badge */}
                      {verifyBadge && (
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border font-medium ${verifyBadge.bg}`}
                        >
                          <VerifyIcon className="w-3 h-3" /> {verifyBadge.label}
                        </span>
                      )}
                    </div>

                    {/* Dimension Breakdown Meter */}
                    <div className="p-3 rounded-lg bg-secondary/40 border border-border/60 mb-3.5">
                      <div className="flex items-center justify-between text-[11px] font-semibold text-muted-foreground mb-2">
                        <span>Alignment Dimensions</span>
                        {bd.trust_adjustment !== 0 && (
                          <span
                            className={
                              bd.trust_adjustment > 0
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-rose-600 dark:text-rose-400"
                            }
                          >
                            {bd.trust_adjustment > 0 ? `+${bd.trust_adjustment}` : bd.trust_adjustment} Trust Adj.
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
                        <div className="p-1.5 rounded bg-background/80 border border-border/40">
                          <div className="text-muted-foreground">Skills</div>
                          <div className="font-semibold text-foreground text-xs mt-0.5">
                            {Math.round(bd.skills_score)}%
                          </div>
                        </div>

                        <div className="p-1.5 rounded bg-background/80 border border-border/40">
                          <div className="text-muted-foreground">Role</div>
                          <div className="font-semibold text-foreground text-xs mt-0.5">
                            {Math.round(bd.role_score)}%
                          </div>
                        </div>

                        <div className="p-1.5 rounded bg-background/80 border border-border/40">
                          <div className="text-muted-foreground">Seniority</div>
                          <div className="font-semibold text-foreground text-xs mt-0.5">
                            {Math.round(bd.experience_score)}%
                          </div>
                        </div>

                        <div className="p-1.5 rounded bg-background/80 border border-border/40">
                          <div className="text-muted-foreground">Location</div>
                          <div className="font-semibold text-foreground text-xs mt-0.5">
                            {Math.round(bd.location_score)}%
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Positive Signals Highlight */}
                    {match.positive_signals.length > 0 && (
                      <div className="mb-3 space-y-1">
                        <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Key Matching Strengths
                        </div>
                        {match.positive_signals.slice(0, 2).map((pos, idx) => (
                          <div
                            key={idx}
                            className="text-xs text-foreground/80 pl-4 border-l-2 border-emerald-500/40"
                          >
                            <p className="font-medium text-[11px] text-foreground">{pos.title}</p>
                            {pos.evidence && (
                              <p className="text-[10px] text-muted-foreground italic mt-0.5 line-clamp-1">
                                &ldquo;{pos.evidence.excerpt}&rdquo; — {pos.evidence.section}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Gap Signals Highlight */}
                    {match.gap_signals.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
                          <Info className="w-3 h-3" /> Candidate & Requisition Considerations
                        </div>
                        {match.gap_signals.slice(0, 1).map((gap, idx) => (
                          <div
                            key={idx}
                            className={`text-xs pl-4 border-l-2 ${
                              gap.type === "missing"
                                ? "border-amber-500/40 text-muted-foreground"
                                : "border-rose-500/40 text-rose-700 dark:text-rose-300"
                            }`}
                          >
                            <span className="font-medium text-[11px]">
                              [{gap.type === "missing" ? "Missing Info" : "Mismatch"}]: {gap.title}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Bottom Actions */}
                  <div className="pt-4 mt-4 border-t border-border flex items-center justify-between">
                    <button
                      onClick={() => setDetailMatch(match)}
                      className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
                    >
                      Why this matches <ArrowRight className="w-3.5 h-3.5" />
                    </button>

                    {job ? (
                      <Link
                        href={`/dashboard/applications?action=new&jobId=${job.id}&title=${encodeURIComponent(
                          job.title
                        )}&company=${encodeURIComponent(job.company?.name || "")}&url=${encodeURIComponent(
                          job.application_url || job.job_url || ""
                        )}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-950/70 text-blue-300 border border-blue-800/50 hover:bg-blue-900 transition"
                        title="Track in Application Tracker"
                      >
                        <Briefcase className="w-3.5 h-3.5 text-blue-400" />
                        Track
                      </Link>
                    ) : null}

                    {job ? (
                      <Link
                        href={`/dashboard/resumes/tailor?jobId=${job.id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-950/70 text-indigo-300 border border-indigo-800/50 hover:bg-indigo-900 transition"
                        title="Tailor your resume for this opportunity"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                        Tailor Resume
                      </Link>
                    ) : null}

                    {job?.application_url || job?.job_url ? (
                      <a
                        href={job.application_url || job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
                      >
                        Apply on Site
                      </a>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-6 border-t border-border mt-6 text-xs text-muted-foreground">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-1.5 rounded-md border border-border bg-card disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-1.5 rounded-md border border-border bg-card disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detail Modal */}
      {detailMatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl p-6">
            <div className="flex items-start justify-between pb-4 border-b border-border mb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`flex flex-col items-center justify-center w-14 h-14 rounded-xl border font-bold ${getScoreColor(
                    detailMatch.match_score
                  )}`}
                >
                  <span className="text-xl leading-none">{Math.round(detailMatch.match_score)}</span>
                  <span className="text-[10px] font-normal uppercase opacity-75">Score</span>
                </div>
                <div>
                  <h2 className="text-lg font-bold">{detailMatch.job?.title}</h2>
                  <p className="text-xs text-muted-foreground">
                    {detailMatch.job?.company?.name || "Direct Requisition"} •{" "}
                    {detailMatch.job?.city || "Remote"}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDetailMatch(null)}
                className="p-1.5 rounded-lg border border-border hover:bg-secondary text-muted-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-5 text-sm">
              {/* Detailed Breakdown Scores */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2.5">
                  Dimension Alignment Weights
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg bg-secondary/50">
                    <div className="text-xs text-muted-foreground">Skills Alignment</div>
                    <div className="text-base font-bold mt-0.5">
                      {detailMatch.score_breakdown.skills_score}%
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/50">
                    <div className="text-xs text-muted-foreground">Role Target</div>
                    <div className="text-base font-bold mt-0.5">
                      {detailMatch.score_breakdown.role_score}%
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/50">
                    <div className="text-xs text-muted-foreground">Seniority Fit</div>
                    <div className="text-base font-bold mt-0.5">
                      {detailMatch.score_breakdown.experience_score}%
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/50">
                    <div className="text-xs text-muted-foreground">Location Alignment</div>
                    <div className="text-base font-bold mt-0.5">
                      {detailMatch.score_breakdown.location_score}%
                    </div>
                  </div>
                </div>

                <div className="mt-2.5 p-2.5 rounded-md bg-secondary/30 text-xs flex items-center justify-between text-muted-foreground">
                  <span>Salary Dimension Status:</span>
                  <span className="font-semibold text-foreground capitalize">
                    {detailMatch.score_breakdown.salary_status.replace("_", " ")}
                  </span>
                </div>
              </div>

              {/* Positive Signals with Excerpts */}
              {detailMatch.positive_signals.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2">
                    Why This Matches (Evidenced Signals)
                  </h4>
                  <div className="space-y-2.5">
                    {detailMatch.positive_signals.map((sig, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-xs"
                      >
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          {sig.title}
                        </div>
                        <p className="text-muted-foreground mt-1">{sig.description}</p>
                        {sig.evidence && (
                          <div className="mt-2 pt-2 border-t border-emerald-500/15 font-mono text-[11px] text-foreground/80">
                            <span className="font-semibold text-muted-foreground">
                              Citing [{sig.evidence.section}]:
                            </span>{" "}
                            &ldquo;{sig.evidence.excerpt}&rdquo;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Gap Signals */}
              {detailMatch.gap_signals.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2">
                    Requirements &amp; Gap Analysis
                  </h4>
                  <div className="space-y-2">
                    {detailMatch.gap_signals.map((gap, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border text-xs ${
                          gap.type === "missing"
                            ? "border-amber-500/20 bg-amber-500/5 text-amber-900 dark:text-amber-200"
                            : "border-rose-500/20 bg-rose-500/5 text-rose-900 dark:text-rose-200"
                        }`}
                      >
                        <div className="font-semibold flex items-center gap-1.5">
                          {gap.type === "missing" ? (
                            <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
                          ) : (
                            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                          )}
                          [{gap.type === "missing" ? "Information Missing" : "Direct Mismatch"}]:{" "}
                          {gap.title}
                        </div>
                        <p className="text-xs opacity-90 mt-1">{gap.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Disclaimer */}
              <div className="p-3 rounded-lg bg-secondary/60 border border-border/80 text-[11px] text-muted-foreground flex items-start gap-2">
                <Info className="w-4 h-4 shrink-0 text-primary mt-0.5" />
                <p>{detailMatch.score_breakdown.disclaimer}</p>
              </div>
            </div>

            <div className="pt-4 mt-6 border-t border-border flex justify-end gap-3">
              <button
                onClick={() => setDetailMatch(null)}
                className="px-4 py-2 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
              >
                Close
              </button>
              {detailMatch.job && (
                <Link
                  href={`/dashboard/applications?action=new&jobId=${detailMatch.job.id}&title=${encodeURIComponent(
                    detailMatch.job.title
                  )}&company=${encodeURIComponent(
                    detailMatch.job.company?.name || ""
                  )}&url=${encodeURIComponent(
                    detailMatch.job.application_url || detailMatch.job.job_url || ""
                  )}`}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1.5 transition"
                >
                  <Briefcase className="w-3.5 h-3.5" />
                  Track Application
                </Link>
              )}
              {detailMatch.job && (
                <Link
                  href={`/dashboard/resumes/tailor?jobId=${detailMatch.job.id}`}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Tailor Resume for Role
                </Link>
              )}
              {detailMatch.job?.application_url || detailMatch.job?.job_url ? (
                <a
                  href={detailMatch.job.application_url || detailMatch.job.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  Apply on Official Site
                </a>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Preferences Modal */}
      {showPreferencesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-card shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-border mb-4">
              <div>
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Settings2 className="w-5 h-5 text-primary" /> Matching Preferences
                </h2>
                <p className="text-xs text-muted-foreground">
                  Personalize the deterministic matching algorithm with your preferred targets and negative exclusions.
                </p>
              </div>
              <button
                onClick={() => setShowPreferencesModal(false)}
                className="p-1.5 rounded-lg border border-border hover:bg-secondary text-muted-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSavePreferences} className="space-y-4 text-xs">
              {/* Target Role Families */}
              <div>
                <label className="font-semibold block mb-1">
                  Target Role Families (comma separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Software Engineer, Backend Developer, Full Stack Engineer"
                  value={prefRolesInput}
                  onChange={(e) => setPrefRolesInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Preferred Locations */}
              <div>
                <label className="font-semibold block mb-1">
                  Preferred Cities or Regions (comma separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. San Francisco, Bengaluru, London, Remote"
                  value={prefLocationsInput}
                  onChange={(e) => setPrefLocationsInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Work Arrangement Preferences */}
              <div>
                <label className="font-semibold block mb-1">Preferred Work Arrangements</label>
                <div className="flex items-center gap-3">
                  {["remote", "hybrid", "onsite"].map((arr) => {
                    const isChecked = prefArrangements.includes(arr);
                    return (
                      <label
                        key={arr}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer transition-colors ${
                          isChecked
                            ? "bg-primary/10 border-primary text-primary font-medium"
                            : "border-border hover:bg-secondary text-muted-foreground"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setPrefArrangements([...prefArrangements, arr]);
                            } else {
                              setPrefArrangements(prefArrangements.filter((a) => a !== arr));
                            }
                          }}
                          className="sr-only"
                        />
                        {arr.charAt(0).toUpperCase() + arr.slice(1)}
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Minimum Salary */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Minimum Desired Salary</label>
                  <input
                    type="number"
                    placeholder="e.g. 80000"
                    value={prefMinSalary}
                    onChange={(e) => setPrefMinSalary(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="font-semibold block mb-1">Salary Frequency</label>
                  <select
                    value={prefSalaryPeriod}
                    onChange={(e) => setPrefSalaryPeriod(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                  >
                    <option value="annual">Per Year (Annual)</option>
                    <option value="monthly">Per Month</option>
                    <option value="hourly">Hourly</option>
                  </select>
                </div>
              </div>

              {/* Priority Technical Skills */}
              <div>
                <label className="font-semibold block mb-1">
                  Priority Technical Skills (boosts score)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Python, FastAPI, React, PostgreSQL"
                  value={prefSkillsInput}
                  onChange={(e) => setPrefSkillsInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Negative Filters Header */}
              <div className="pt-2 border-t border-border">
                <h3 className="font-bold text-muted-foreground uppercase text-[11px] mb-2">
                  Negative Exclusions &amp; Deductions
                </h3>
              </div>

              {/* Excluded Roles */}
              <div>
                <label className="font-semibold block mb-1 text-muted-foreground">
                  Excluded Role Titles (e.g. Sales, Support, QA)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Sales Engineer, Customer Support"
                  value={excludedRolesInput}
                  onChange={(e) => setExcludedRolesInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Excluded Terms */}
              <div>
                <label className="font-semibold block mb-1 text-muted-foreground">
                  Excluded Terms / Keywords
                </label>
                <input
                  type="text"
                  placeholder="e.g. Crypto, Blockchain, unpaid"
                  value={excludedTermsInput}
                  onChange={(e) => setExcludedTermsInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Excluded Industries */}
              <div>
                <label className="font-semibold block mb-1 text-muted-foreground">
                  Excluded Industries
                </label>
                <input
                  type="text"
                  placeholder="e.g. Gambling, Tobacco"
                  value={excludedIndustriesInput}
                  onChange={(e) => setExcludedIndustriesInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowPreferencesModal(false)}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-secondary font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingPrefs}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {isSavingPrefs ? "Saving..." : "Save Preferences"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Run Matches Modal */}
      {showRunModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-border mb-4">
              <div>
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-primary" /> Run Matching Engine
                </h2>
                <p className="text-xs text-muted-foreground">
                  Compute grounded match scores across all active job opportunities.
                </p>
              </div>
              <button
                onClick={() => setShowRunModal(false)}
                className="p-1.5 rounded-lg border border-border hover:bg-secondary text-muted-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleExecuteRun} className="space-y-4 text-xs">
              {resumes.length > 0 ? (
                <div>
                  <label className="font-semibold block mb-1">Select Analyzed Resume</label>
                  <select
                    value={selectedResumeId}
                    onChange={(e) => {
                      setSelectedResumeId(e.target.value);
                      const r = resumes.find((item) => item.id === e.target.value);
                      if (r?.current_version_id) setSelectedVersionId(r.current_version_id);
                    }}
                    className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-1 focus:ring-primary"
                  >
                    {resumes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.title}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 text-amber-900 dark:text-amber-200">
                  <p className="font-semibold">No resumes found</p>
                  <p className="text-[11px] mt-0.5">
                    Upload and analyze a resume in{" "}
                    <Link href="/dashboard/resumes" className="underline font-bold">
                      Resume Studio
                    </Link>{" "}
                    first.
                  </p>
                </div>
              )}

              <div>
                <label className="font-semibold block mb-1 flex justify-between">
                  <span>Minimum Match Cutoff</span>
                  <span className="font-bold text-foreground">{runThreshold}%</span>
                </label>
                <input
                  type="range"
                  min="20"
                  max="80"
                  step="5"
                  value={runThreshold}
                  onChange={(e) => setRunThreshold(parseInt(e.target.value))}
                  className="w-full accent-primary h-1.5 bg-secondary rounded-lg appearance-none cursor-pointer"
                />
                <p className="text-[10px] text-muted-foreground mt-1">
                  Listings with scores below {runThreshold}% will not be saved into your results table.
                </p>
              </div>

              {runFeedback && (
                <div
                  className={`p-3 rounded-lg border text-xs ${
                    runFeedback.startsWith("Error")
                      ? "border-destructive/30 bg-destructive/5 text-destructive"
                      : "border-emerald-500/30 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400"
                  }`}
                >
                  {runFeedback}
                </div>
              )}

              <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowRunModal(false)}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-secondary font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isRunningMatches || resumes.length === 0}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {isRunningMatches && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  {isRunningMatches ? "Computing Matches..." : "Run Matching Engine"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
