"use client";

// =============================================================================
// Nexora Onboarding Wizard — /dashboard/onboarding
// 7-step wizard: Resume Upload → Personal Info → Education/Experience →
//   Job Preferences → Application Info → Integrations → Review & Launch
// =============================================================================

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  ChevronRight,
  Database,
  ExternalLink,
  FileText,
  GraduationCap,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Plus,
  Rocket,
  Sparkles,
  Star,
  User,
  X,
  Zap,
} from "lucide-react";

import {
  apiClient,
  careerWorkflowApi,
  GmailConnectionStatus,
  googleIntegrationsApi,
  integrationsApi,
  IntegrationsHealthOverview,
  matchingApi,
  OnboardingConfirmPayload,
  OnboardingStartResult,
  ResumeDetail,
  ResumeSummary,
  resumesApi,
} from "@/lib/api";

// =============================================================================
// Types
// =============================================================================

type WorkArrangement = "Remote" | "Hybrid" | "Onsite";
type SeniorityLevel = "Entry" | "Mid" | "Senior" | "Lead" | "Executive";
type NoticePeriod = "Immediate" | "2 weeks" | "1 month" | "2 months" | "3+ months";
type WorkAuthorization = "Citizen" | "PR" | "H1B" | "Need Sponsorship" | "Other";
type EmploymentStatus = "Employed" | "Unemployed" | "Student" | "Freelance";
type Currency = "USD" | "GBP" | "EUR" | "INR" | "AUD" | "CAD";

interface PersonalInfo {
  fullName: string;
  email: string;
  phone: string;
  location: string;
  linkedinUrl: string;
  githubUrl: string;
  portfolioUrl: string;
}

interface EducationItem {
  degree: string;
  institution: string;
  year: string;
  fieldOfStudy: string;
}

interface EducationExperienceData {
  education: EducationItem[];
  skills: string[];
  roles: string[];
  yearsOfExperience: number | "";
}

interface JobPreferences {
  targetRoles: string[];
  preferredLocations: string[];
  workArrangements: WorkArrangement[];
  minSalary: number | "";
  currency: Currency;
  seniority: SeniorityLevel | "";
}

interface ApplicationInfo {
  noticePeriod: NoticePeriod | "";
  workAuthorization: WorkAuthorization | "";
  employmentStatus: EmploymentStatus | "";
  willingToRelocate: boolean;
}

interface StoredProgress {
  currentStep: number;
  resumeId: string | null;
  runId: string | null;
  stepData: {
    personal?: PersonalInfo;
    educationExperience?: EducationExperienceData;
    jobPreferences?: JobPreferences;
    applicationInfo?: ApplicationInfo;
  };
}

const STORAGE_KEY = "nexora_onboarding";
const TOTAL_STEPS = 7;

const STEP_LABELS = [
  "Resume",
  "Personal",
  "Education",
  "Preferences",
  "Application",
  "Integrations",
  "Review",
];

// =============================================================================
// Utility helpers
// =============================================================================

function extractErrorMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    if ("message" in err && typeof (err as { message: unknown }).message === "string") {
      return (err as { message: string }).message;
    }
  }
  return "An unexpected error occurred";
}

function saveProgress(data: Partial<StoredProgress>) {
  try {
    const existing = loadProgress();
    const merged = { ...existing, ...data };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  } catch {
    // ignore
  }
}

function loadProgress(): StoredProgress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as StoredProgress;
  } catch {
    // ignore
  }
  return { currentStep: 1, resumeId: null, runId: null, stepData: {} };
}

function clearProgress() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

// =============================================================================
// Sub-components
// =============================================================================

// --- Tag Input ---
interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
}

function TagInput({ tags, onChange, placeholder = "Type and press Enter", className = "" }: TagInputProps) {
  const [input, setInput] = useState("");

  const addTag = (val: string) => {
    const trimmed = val.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInput("");
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  return (
    <div className={`flex flex-wrap gap-2 p-2 rounded-lg border border-gray-700 bg-gray-800 min-h-[44px] ${className}`}>
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            className="ml-1 hover:text-indigo-100"
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            addTag(input);
          } else if (e.key === "Backspace" && input === "" && tags.length > 0) {
            onChange(tags.slice(0, -1));
          }
        }}
        onBlur={() => { if (input.trim()) addTag(input); }}
        placeholder={tags.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[120px] bg-transparent text-sm text-gray-200 placeholder-gray-500 outline-none"
      />
    </div>
  );
}

// --- Progress Bar ---
interface ProgressBarProps {
  current: number;
}

function ProgressBar({ current }: ProgressBarProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-3">
        {STEP_LABELS.map((label, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < current;
          const isCurrent = stepNum === current;
          return (
            <div key={label} className="flex flex-col items-center flex-1">
              <div className="relative flex items-center w-full">
                {/* Connector line left */}
                {idx > 0 && (
                  <div
                    className={`absolute left-0 right-1/2 h-0.5 -top-0 ${
                      isCompleted || isCurrent ? "bg-indigo-500" : "bg-gray-700"
                    }`}
                  />
                )}
                {/* Connector line right */}
                {idx < TOTAL_STEPS - 1 && (
                  <div
                    className={`absolute left-1/2 right-0 h-0.5 -top-0 ${
                      isCompleted ? "bg-indigo-500" : "bg-gray-700"
                    }`}
                  />
                )}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 z-10 mx-auto transition-all ${
                    isCompleted
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : isCurrent
                      ? "bg-gray-900 border-indigo-500 text-indigo-400"
                      : "bg-gray-800 border-gray-600 text-gray-500"
                  }`}
                >
                  {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : stepNum}
                </div>
              </div>
              <span
                className={`mt-1.5 text-[10px] font-medium text-center hidden sm:block ${
                  isCurrent ? "text-indigo-400" : isCompleted ? "text-indigo-300" : "text-gray-500"
                }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- Form Field ---
interface FieldProps {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}

function Field({ label, required, error, children }: FieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1.5">
        {label} {required && <span className="text-indigo-400">*</span>}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

function inputClass(error?: string) {
  return `w-full px-3 py-2.5 rounded-lg border ${
    error ? "border-red-500/60" : "border-gray-700"
  } bg-gray-800 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-colors`;
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function OnboardingPage() {
  const router = useRouter();

  // --- Core state ---
  const [currentStep, setCurrentStep] = useState(1);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [onboardingResult, setOnboardingResult] = useState<OnboardingStartResult | null>(null);

  // --- Step 1: Resume Upload ---
  const [existingResumes, setExistingResumes] = useState<ResumeSummary[]>([]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "polling" | "starting" | "done" | "error"
  >("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- Step 2: Personal Info ---
  const [personalInfo, setPersonalInfo] = useState<PersonalInfo>({
    fullName: "",
    email: "",
    phone: "",
    location: "",
    linkedinUrl: "",
    githubUrl: "",
    portfolioUrl: "",
  });
  const [personalErrors, setPersonalErrors] = useState<Partial<PersonalInfo>>({});

  // --- Step 3: Education & Experience ---
  const [educationExperience, setEducationExperience] = useState<EducationExperienceData>({
    education: [],
    skills: [],
    roles: [],
    yearsOfExperience: "",
  });

  // --- Step 4: Job Preferences ---
  const [jobPreferences, setJobPreferences] = useState<JobPreferences>({
    targetRoles: [],
    preferredLocations: [],
    workArrangements: [],
    minSalary: "",
    currency: "USD",
    seniority: "",
  });
  const [prefsError, setPrefsError] = useState<string | null>(null);
  const [prefsSaving, setPrefsSaving] = useState(false);

  // --- Step 5: Application Info ---
  const [applicationInfo, setApplicationInfo] = useState<ApplicationInfo>({
    noticePeriod: "",
    workAuthorization: "",
    employmentStatus: "",
    willingToRelocate: false,
  });
  const [appInfoSaving, setAppInfoSaving] = useState(false);
  const [appInfoError, setAppInfoError] = useState<string | null>(null);

  // --- Step 6: Integrations ---
  const [healthData, setHealthData] = useState<IntegrationsHealthOverview | null>(null);
  const [gmailStatus, setGmailStatus] = useState<GmailConnectionStatus | null>(null);
  const [integrationsLoading, setIntegrationsLoading] = useState(false);
  const [gmailConnecting, setGmailConnecting] = useState(false);

  // =============================================================================
  // Mount: load persisted progress
  // =============================================================================

  useEffect(() => {
    const stored = loadProgress();
    if (stored.currentStep > 1) {
      setCurrentStep(stored.currentStep);
    }
    if (stored.resumeId) setResumeId(stored.resumeId);
    if (stored.runId) setRunId(stored.runId);
    if (stored.stepData.personal) setPersonalInfo(stored.stepData.personal);
    if (stored.stepData.educationExperience) setEducationExperience(stored.stepData.educationExperience);
    if (stored.stepData.jobPreferences) setJobPreferences(stored.stepData.jobPreferences);
    if (stored.stepData.applicationInfo) setApplicationInfo(stored.stepData.applicationInfo);

    // Load existing resumes for step 1
    resumesApi
      .listResumes()
      .then((list) => {
        const completed = list.filter(
          (r) => r.parsing_status === "parsed" || r.parsing_status === "uploaded"
        );
        setExistingResumes(completed);
      })
      .catch(() => {});
  }, []);

  // =============================================================================
  // Persist on step change
  // =============================================================================

  useEffect(() => {
    saveProgress({
      currentStep,
      resumeId,
      runId,
      stepData: {
        personal: personalInfo,
        educationExperience,
        jobPreferences,
        applicationInfo,
      },
    });
  }, [currentStep, resumeId, runId, personalInfo, educationExperience, jobPreferences, applicationInfo]);

  // =============================================================================
  // Step navigation helpers
  // =============================================================================

  const goNext = () => setCurrentStep((s) => Math.min(s + 1, TOTAL_STEPS));
  const goBack = () => setCurrentStep((s) => Math.max(s - 1, 1));

  // =============================================================================
  // Step 1 — Resume Upload Logic
  // =============================================================================

  const startOnboarding = useCallback(
    async (rid: string) => {
      setUploadStatus("starting");
      try {
        const result = await careerWorkflowApi.startOnboarding(rid);
        setOnboardingResult(result);
        setRunId(result.workflow_run_id);

        // Pre-fill step 3 from result
        setEducationExperience((prev) => ({
          ...prev,
          skills: result.extracted_skills ?? prev.skills,
          roles: result.extracted_roles ?? prev.roles,
        }));

        // Pre-fill step 4
        const inferred = result.inferred_preferences as {
          locations?: string[];
          work_arrangement?: string[];
          seniority?: string;
          min_salary?: number;
          salary_currency?: string;
        } | undefined;

        setJobPreferences((prev) => ({
          ...prev,
          targetRoles: result.extracted_roles?.length ? result.extracted_roles : prev.targetRoles,
          preferredLocations: inferred?.locations?.length ? inferred.locations : prev.preferredLocations,
          workArrangements: inferred?.work_arrangement?.length
            ? (inferred.work_arrangement as WorkArrangement[])
            : prev.workArrangements,
          seniority: (inferred?.seniority as SeniorityLevel) || prev.seniority,
          minSalary: inferred?.min_salary ?? prev.minSalary,
          currency: (inferred?.salary_currency as Currency) || prev.currency,
        }));

        setUploadStatus("done");
        goNext();
      } catch (err) {
        setUploadStatus("error");
        setUploadError(extractErrorMessage(err));
      }
    },
    [] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const pollResumeStatus = useCallback(
    (rid: string) => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(async () => {
        try {
          const detail: ResumeDetail = await resumesApi.getResume(rid);
          const version = detail.current_version;
          const status = version?.parsing_status ?? "processing";

          if (status === "parsed") {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            // Also pre-fill education from parsed content
            if (version?.parsed_content) {
              const edu: EducationItem[] = (version.parsed_content.education ?? []).map((e) => ({
                degree: e.degree ?? "",
                institution: e.institution ?? "",
                year: e.year ?? "",
                fieldOfStudy: e.details?.[0] ?? "",
              }));
              if (edu.length) {
                setEducationExperience((prev) => ({ ...prev, education: edu }));
              }
            }
            await startOnboarding(rid);
          } else if (status === "failed") {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setUploadStatus("error");
            setUploadError("Resume parsing failed. Please try another file.");
          }
        } catch {
          // keep polling
        }
      }, 2000);
    },
    [startOnboarding]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleFileSelect = async (file: File) => {
    setUploadFile(file);
    setUploadError(null);
    setUploadStatus("uploading");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", file.name.replace(/\.[^/.]+$/, ""));

    try {
      const created = await apiClient<ResumeDetail>("/api/v1/resumes", {
        method: "POST",
        body: formData,
      });
      setResumeId(created.id);
      setUploadStatus("polling");
      pollResumeStatus(created.id);
    } catch (err) {
      setUploadStatus("error");
      setUploadError(extractErrorMessage(err));
    }
  };

  const handleUseExistingResume = async (resume: ResumeSummary) => {
    setUploadError(null);
    setResumeId(resume.id);
    await startOnboarding(resume.id);
  };

  // =============================================================================
  // Step 4 — Confirm Preferences
  // =============================================================================

  const handleConfirmPreferences = async () => {
    setPrefsSaving(true);
    setPrefsError(null);

    const payload: OnboardingConfirmPayload = {
      target_role_families: jobPreferences.targetRoles,
      preferred_locations: jobPreferences.preferredLocations,
      work_arrangement_preferences: jobPreferences.workArrangements,
      min_salary: jobPreferences.minSalary === "" ? undefined : Number(jobPreferences.minSalary),
      salary_currency: jobPreferences.currency,
      seniority: jobPreferences.seniority || "Mid",
    };

    const results = await Promise.allSettled([
      careerWorkflowApi.confirmOnboarding(payload),
      matchingApi.updatePreferences({
        target_role_families: jobPreferences.targetRoles,
        preferred_locations: jobPreferences.preferredLocations,
        preferred_work_arrangements: jobPreferences.workArrangements,
        min_salary: jobPreferences.minSalary === "" ? null : Number(jobPreferences.minSalary),
        salary_currency: jobPreferences.currency,
        seniority_preferences: jobPreferences.seniority ? [jobPreferences.seniority] : [],
      }),
    ]);

    const failed = results.filter((r) => r.status === "rejected");
    if (failed.length > 0) {
      setPrefsError("Warning: Preferences partially saved. You can still continue.");
    }

    setPrefsSaving(false);
    goNext();
  };

  // =============================================================================
  // Step 5 — Application Info Save
  // =============================================================================

  const handleSaveApplicationInfo = async () => {
    setAppInfoSaving(true);
    setAppInfoError(null);

    try {
      await matchingApi.updatePreferences({
        // metadata_json is not in the standard update type but we pass it anyway
        ...(({
          metadata_json: {
            notice_period: applicationInfo.noticePeriod,
            work_authorization: applicationInfo.workAuthorization,
            employment_status: applicationInfo.employmentStatus,
            willing_to_relocate: applicationInfo.willingToRelocate,
          },
        }) as unknown as Parameters<typeof matchingApi.updatePreferences>[0]),
      });
    } catch {
      setAppInfoError("Could not save application info to server. Progress saved locally.");
    }

    setAppInfoSaving(false);
    goNext();
  };

  // =============================================================================
  // Step 6 — Load Integrations
  // =============================================================================

  const loadIntegrations = useCallback(async () => {
    setIntegrationsLoading(true);
    const [healthRes, gmailRes] = await Promise.allSettled([
      integrationsApi.getHealth(),
      googleIntegrationsApi.getStatus(),
    ]);
    if (healthRes.status === "fulfilled") setHealthData(healthRes.value);
    if (gmailRes.status === "fulfilled") setGmailStatus(gmailRes.value);
    setIntegrationsLoading(false);
  }, []);

  useEffect(() => {
    if (currentStep === 6) {
      loadIntegrations();
    }
  }, [currentStep, loadIntegrations]);

  const handleConnectGmail = async () => {
    setGmailConnecting(true);
    try {
      const { authorization_url } = await googleIntegrationsApi.getAuthUrl();
      window.open(authorization_url, "_blank");
      // Refresh status after a moment
      setTimeout(() => {
        googleIntegrationsApi
          .getStatus()
          .then((s) => setGmailStatus(s))
          .catch(() => {});
        setGmailConnecting(false);
      }, 3000);
    } catch (err) {
      setGmailConnecting(false);
      console.error("Gmail auth error", err);
    }
  };

  // =============================================================================
  // Step 2 — Validation
  // =============================================================================

  const validatePersonal = (): boolean => {
    const errors: Partial<PersonalInfo> = {};
    if (!personalInfo.fullName.trim()) errors.fullName = "Name is required";
    if (personalInfo.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(personalInfo.email)) {
      errors.email = "Enter a valid email address";
    }
    setPersonalErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handlePersonalNext = () => {
    if (validatePersonal()) goNext();
  };

  // =============================================================================
  // Step 7 — Launch
  // =============================================================================

  const handleLaunch = () => {
    clearProgress();
    router.push("/dashboard/workspace");
  };

  // =============================================================================
  // Render helpers
  // =============================================================================

  const statusBadge = (status: string | undefined, label: string) => {
    const s = (status ?? "").toLowerCase();
    const isGood = s === "connected" || s === "operational";
    const isBad = s === "disconnected" || s === "failed" || s === "error";
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${
          isGood
            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
            : isBad
            ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
            : "bg-gray-700 text-gray-400 border-gray-600"
        }`}
      >
        {isGood ? <CheckCircle2 className="w-3 h-3" /> : isBad ? <X className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
        {label}
      </span>
    );
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400">
              <Rocket className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Nexora Setup</h1>
              <p className="text-xs text-gray-400">Step {currentStep} of {TOTAL_STEPS} — {STEP_LABELS[currentStep - 1]}</p>
            </div>
          </div>
          <ProgressBar current={currentStep} />
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-3xl mx-auto px-4 py-8">

        {/* ================================================================
            STEP 1 — Upload Your Resume
        ================================================================ */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Upload Your Resume</h2>
              <p className="text-gray-400 mt-1 text-sm">
                We&apos;ll extract your skills, experience, and preferences to personalise your job search.
              </p>
            </div>

            {/* Existing resumes */}
            {existingResumes.length > 0 && (
              <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/50 space-y-3">
                <p className="text-sm font-medium text-gray-300 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" /> Use an existing resume
                </p>
                <div className="space-y-2">
                  {existingResumes.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => handleUseExistingResume(r)}
                      disabled={uploadStatus !== "idle"}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-gray-600 bg-gray-800 hover:border-indigo-500 hover:bg-gray-750 transition-colors text-left disabled:opacity-50"
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-200">{r.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {new Date(r.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-px bg-gray-700" />
                  <span className="text-xs text-gray-500">or upload new</span>
                  <div className="flex-1 h-px bg-gray-700" />
                </div>
              </div>
            )}

            {/* Upload area */}
            <div
              className={`relative rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
                uploadStatus !== "idle"
                  ? "border-gray-700 bg-gray-800/30"
                  : "border-gray-600 hover:border-indigo-500 bg-gray-800/20 cursor-pointer"
              }`}
              onClick={() => uploadStatus === "idle" && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
              />

              {uploadStatus === "idle" && (
                <div className="space-y-3">
                  <div className="mx-auto w-14 h-14 rounded-full bg-indigo-600/10 flex items-center justify-center">
                    <FileText className="w-7 h-7 text-indigo-400" />
                  </div>
                  <div>
                    <p className="text-base font-medium text-gray-200">Drop your resume here</p>
                    <p className="text-sm text-gray-500 mt-1">PDF, DOC, or DOCX accepted</p>
                  </div>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
                  >
                    Browse Files
                  </button>
                </div>
              )}

              {(uploadStatus === "uploading" || uploadStatus === "polling" || uploadStatus === "starting") && (
                <div className="space-y-4">
                  <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto" />
                  <div>
                    <p className="text-base font-medium text-gray-200">
                      {uploadStatus === "uploading"
                        ? "Uploading resume…"
                        : uploadStatus === "polling"
                        ? "Parsing your resume…"
                        : "Analysing your profile…"}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {uploadStatus === "uploading"
                        ? "Sending your file to the server"
                        : uploadStatus === "polling"
                        ? "Extracting skills, experience & education"
                        : "Running AI-powered career matching"}
                    </p>
                  </div>
                  {uploadFile && (
                    <p className="text-xs text-gray-600">{uploadFile.name}</p>
                  )}
                </div>
              )}

              {uploadStatus === "done" && (
                <div className="space-y-3">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                  <p className="text-base font-medium text-emerald-300">Resume processed!</p>
                </div>
              )}
            </div>

            {uploadStatus === "error" && uploadError && (
              <div className="flex items-start gap-3 p-4 rounded-xl border border-red-500/30 bg-red-500/10">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-300">{uploadError}</p>
                  <button
                    onClick={() => {
                      setUploadStatus("idle");
                      setUploadError(null);
                      setUploadFile(null);
                    }}
                    className="text-xs text-red-400 hover:text-red-300 mt-1 underline"
                  >
                    Try again
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================================================================
            STEP 2 — Personal Information
        ================================================================ */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Personal Information</h2>
              <p className="text-gray-400 mt-1 text-sm">
                Review and complete your contact details. Pre-filled where possible from your resume.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Full Name" required error={personalErrors.fullName}>
                <input
                  type="text"
                  value={personalInfo.fullName}
                  onChange={(e) => setPersonalInfo((p) => ({ ...p, fullName: e.target.value }))}
                  placeholder="Jane Smith"
                  className={inputClass(personalErrors.fullName)}
                />
              </Field>

              <Field label="Email" error={personalErrors.email}>
                <input
                  type="email"
                  value={personalInfo.email}
                  onChange={(e) => setPersonalInfo((p) => ({ ...p, email: e.target.value }))}
                  placeholder="jane@example.com"
                  className={inputClass(personalErrors.email)}
                />
              </Field>

              <Field label="Phone">
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="tel"
                    value={personalInfo.phone}
                    onChange={(e) => setPersonalInfo((p) => ({ ...p, phone: e.target.value }))}
                    placeholder="+1 (555) 000-0000"
                    className={`${inputClass()} pl-9`}
                  />
                </div>
              </Field>

              <Field label="Location (city / country)">
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    value={personalInfo.location}
                    onChange={(e) => setPersonalInfo((p) => ({ ...p, location: e.target.value }))}
                    placeholder="San Francisco, USA"
                    className={`${inputClass()} pl-9`}
                  />
                </div>
              </Field>

              <Field label="LinkedIn URL">
                <input
                  type="url"
                  value={personalInfo.linkedinUrl}
                  onChange={(e) => setPersonalInfo((p) => ({ ...p, linkedinUrl: e.target.value }))}
                  placeholder="https://linkedin.com/in/username"
                  className={inputClass()}
                />
              </Field>

              <Field label="GitHub URL">
                <input
                  type="url"
                  value={personalInfo.githubUrl}
                  onChange={(e) => setPersonalInfo((p) => ({ ...p, githubUrl: e.target.value }))}
                  placeholder="https://github.com/username"
                  className={inputClass()}
                />
              </Field>

              <Field label="Portfolio URL" >
                <input
                  type="url"
                  value={personalInfo.portfolioUrl}
                  onChange={(e) => setPersonalInfo((p) => ({ ...p, portfolioUrl: e.target.value }))}
                  placeholder="https://myportfolio.dev"
                  className={inputClass()}
                />
              </Field>
            </div>

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="btn-secondary">Back</button>
              <button onClick={handlePersonalNext} className="btn-primary">Next</button>
            </div>
          </div>
        )}

        {/* ================================================================
            STEP 3 — Education & Experience
        ================================================================ */}
        {currentStep === 3 && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-white">Education & Experience</h2>
              <p className="text-gray-400 mt-1 text-sm">
                Review what we extracted from your resume. Add or remove as needed.
              </p>
            </div>

            {/* Education */}
            <section className="space-y-4">
              <h3 className="text-base font-semibold text-gray-200 flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-indigo-400" /> Education
              </h3>

              {educationExperience.education.length === 0 && (
                <p className="text-sm text-gray-500 italic">No education extracted. Add manually below.</p>
              )}

              {educationExperience.education.map((edu, idx) => (
                <div key={idx} className="p-4 rounded-lg border border-gray-700 bg-gray-800/50 space-y-3">
                  <div className="flex justify-between items-start">
                    <p className="text-sm font-medium text-gray-200">Education {idx + 1}</p>
                    <button
                      onClick={() => {
                        const updated = educationExperience.education.filter((_, i) => i !== idx);
                        setEducationExperience((p) => ({ ...p, education: updated }));
                      }}
                      className="text-gray-500 hover:text-red-400"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      value={edu.degree}
                      onChange={(e) => {
                        const updated = [...educationExperience.education];
                        updated[idx] = { ...updated[idx], degree: e.target.value };
                        setEducationExperience((p) => ({ ...p, education: updated }));
                      }}
                      placeholder="Degree"
                      className={inputClass()}
                    />
                    <input
                      type="text"
                      value={edu.institution}
                      onChange={(e) => {
                        const updated = [...educationExperience.education];
                        updated[idx] = { ...updated[idx], institution: e.target.value };
                        setEducationExperience((p) => ({ ...p, education: updated }));
                      }}
                      placeholder="Institution"
                      className={inputClass()}
                    />
                    <input
                      type="text"
                      value={edu.year}
                      onChange={(e) => {
                        const updated = [...educationExperience.education];
                        updated[idx] = { ...updated[idx], year: e.target.value };
                        setEducationExperience((p) => ({ ...p, education: updated }));
                      }}
                      placeholder="Year (e.g. 2022)"
                      className={inputClass()}
                    />
                    <input
                      type="text"
                      value={edu.fieldOfStudy}
                      onChange={(e) => {
                        const updated = [...educationExperience.education];
                        updated[idx] = { ...updated[idx], fieldOfStudy: e.target.value };
                        setEducationExperience((p) => ({ ...p, education: updated }));
                      }}
                      placeholder="Field of study"
                      className={inputClass()}
                    />
                  </div>
                </div>
              ))}

              <button
                onClick={() =>
                  setEducationExperience((p) => ({
                    ...p,
                    education: [
                      ...p.education,
                      { degree: "", institution: "", year: "", fieldOfStudy: "" },
                    ],
                  }))
                }
                className="inline-flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300"
              >
                <Plus className="w-4 h-4" /> Add education
              </button>
            </section>

            {/* Skills */}
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-gray-200 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" /> Skills
              </h3>
              <TagInput
                tags={educationExperience.skills}
                onChange={(skills) => setEducationExperience((p) => ({ ...p, skills }))}
                placeholder="Add skill and press Enter…"
              />
            </section>

            {/* Experience */}
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-gray-200 flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-indigo-400" /> Experience
              </h3>

              {educationExperience.roles.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {educationExperience.roles.map((role) => (
                    <span
                      key={role}
                      className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              )}

              <Field label="Years of experience">
                <input
                  type="number"
                  min={0}
                  max={50}
                  value={educationExperience.yearsOfExperience}
                  onChange={(e) =>
                    setEducationExperience((p) => ({
                      ...p,
                      yearsOfExperience: e.target.value === "" ? "" : Number(e.target.value),
                    }))
                  }
                  placeholder="e.g. 5"
                  className={inputClass()}
                />
              </Field>
            </section>

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="btn-secondary">Back</button>
              <button onClick={goNext} className="btn-primary">Next</button>
            </div>
          </div>
        )}

        {/* ================================================================
            STEP 4 — Job Preferences
        ================================================================ */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Job Preferences</h2>
              <p className="text-gray-400 mt-1 text-sm">
                Tell us what you&apos;re looking for. Pre-filled from your resume analysis.
              </p>
            </div>

            <Field label="Target roles">
              <TagInput
                tags={jobPreferences.targetRoles}
                onChange={(targetRoles) => setJobPreferences((p) => ({ ...p, targetRoles }))}
                placeholder="e.g. Software Engineer, Product Manager…"
              />
            </Field>

            <Field label="Preferred locations">
              <TagInput
                tags={jobPreferences.preferredLocations}
                onChange={(preferredLocations) =>
                  setJobPreferences((p) => ({ ...p, preferredLocations }))
                }
                placeholder="e.g. San Francisco, Remote…"
              />
            </Field>

            <Field label="Work arrangement">
              <div className="flex flex-wrap gap-3 mt-1">
                {(["Remote", "Hybrid", "Onsite"] as WorkArrangement[]).map((opt) => {
                  const checked = jobPreferences.workArrangements.includes(opt);
                  return (
                    <label
                      key={opt}
                      className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors ${
                        checked
                          ? "border-indigo-500 bg-indigo-600/10 text-indigo-300"
                          : "border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          setJobPreferences((p) => ({
                            ...p,
                            workArrangements: checked
                              ? p.workArrangements.filter((w) => w !== opt)
                              : [...p.workArrangements, opt],
                          }));
                        }}
                        className="sr-only"
                      />
                      <div
                        className={`w-4 h-4 rounded border flex items-center justify-center ${
                          checked ? "bg-indigo-600 border-indigo-600" : "border-gray-600"
                        }`}
                      >
                        {checked && <CheckCircle2 className="w-3 h-3 text-white" />}
                      </div>
                      <span className="text-sm font-medium">{opt}</span>
                    </label>
                  );
                })}
              </div>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Minimum salary">
                <input
                  type="number"
                  min={0}
                  value={jobPreferences.minSalary}
                  onChange={(e) =>
                    setJobPreferences((p) => ({
                      ...p,
                      minSalary: e.target.value === "" ? "" : Number(e.target.value),
                    }))
                  }
                  placeholder="e.g. 80000"
                  className={inputClass()}
                />
              </Field>

              <Field label="Currency">
                <select
                  value={jobPreferences.currency}
                  onChange={(e) =>
                    setJobPreferences((p) => ({ ...p, currency: e.target.value as Currency }))
                  }
                  className={inputClass()}
                >
                  {(["USD", "GBP", "EUR", "INR", "AUD", "CAD"] as Currency[]).map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </Field>
            </div>

            <Field label="Experience level">
              <select
                value={jobPreferences.seniority}
                onChange={(e) =>
                  setJobPreferences((p) => ({ ...p, seniority: e.target.value as SeniorityLevel }))
                }
                className={inputClass()}
              >
                <option value="">Select level</option>
                {(["Entry", "Mid", "Senior", "Lead", "Executive"] as SeniorityLevel[]).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </Field>

            {prefsError && (
              <div className="flex items-start gap-3 p-3 rounded-lg border border-amber-500/30 bg-amber-500/10">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-300">{prefsError}</p>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="btn-secondary">Back</button>
              <button
                onClick={handleConfirmPreferences}
                disabled={prefsSaving}
                className="btn-primary flex items-center gap-2 disabled:opacity-60"
              >
                {prefsSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                {prefsSaving ? "Saving…" : "Next"}
              </button>
            </div>
          </div>
        )}

        {/* ================================================================
            STEP 5 — Application Info
        ================================================================ */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Application Info</h2>
              <p className="text-gray-400 mt-1 text-sm">
                Help us match jobs to your availability and eligibility.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Notice period">
                <select
                  value={applicationInfo.noticePeriod}
                  onChange={(e) =>
                    setApplicationInfo((p) => ({ ...p, noticePeriod: e.target.value as NoticePeriod }))
                  }
                  className={inputClass()}
                >
                  <option value="">Select notice period</option>
                  {(["Immediate", "2 weeks", "1 month", "2 months", "3+ months"] as NoticePeriod[]).map(
                    (n) => (
                      <option key={n} value={n}>{n}</option>
                    )
                  )}
                </select>
              </Field>

              <Field label="Work authorization">
                <select
                  value={applicationInfo.workAuthorization}
                  onChange={(e) =>
                    setApplicationInfo((p) => ({
                      ...p,
                      workAuthorization: e.target.value as WorkAuthorization,
                    }))
                  }
                  className={inputClass()}
                >
                  <option value="">Select authorization</option>
                  {(["Citizen", "PR", "H1B", "Need Sponsorship", "Other"] as WorkAuthorization[]).map(
                    (w) => (
                      <option key={w} value={w}>{w}</option>
                    )
                  )}
                </select>
              </Field>

              <Field label="Employment status">
                <select
                  value={applicationInfo.employmentStatus}
                  onChange={(e) =>
                    setApplicationInfo((p) => ({
                      ...p,
                      employmentStatus: e.target.value as EmploymentStatus,
                    }))
                  }
                  className={inputClass()}
                >
                  <option value="">Select status</option>
                  {(["Employed", "Unemployed", "Student", "Freelance"] as EmploymentStatus[]).map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </Field>

              <Field label="Willing to relocate">
                <div className="flex items-center gap-4 h-[42px]">
                  {([true, false] as const).map((val) => (
                    <label key={String(val)} className="flex items-center gap-2 cursor-pointer">
                      <div
                        onClick={() => setApplicationInfo((p) => ({ ...p, willingToRelocate: val }))}
                        className={`w-10 h-5 rounded-full transition-colors relative ${
                          applicationInfo.willingToRelocate === val
                            ? "bg-indigo-600"
                            : "bg-gray-700"
                        }`}
                      >
                        <div
                          className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                            applicationInfo.willingToRelocate === val && val === true
                              ? "translate-x-5"
                              : ""
                          }`}
                        />
                      </div>
                      <span className="text-sm text-gray-300">{val ? "Yes" : "No"}</span>
                    </label>
                  ))}
                </div>
              </Field>
            </div>

            {appInfoError && (
              <div className="flex items-start gap-3 p-3 rounded-lg border border-amber-500/30 bg-amber-500/10">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-300">{appInfoError}</p>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="btn-secondary">Back</button>
              <button
                onClick={handleSaveApplicationInfo}
                disabled={appInfoSaving}
                className="btn-primary flex items-center gap-2 disabled:opacity-60"
              >
                {appInfoSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                {appInfoSaving ? "Saving…" : "Next"}
              </button>
            </div>
          </div>
        )}

        {/* ================================================================
            STEP 6 — Connect Integrations
        ================================================================ */}
        {currentStep === 6 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Connect Integrations</h2>
              <p className="text-gray-400 mt-1 text-sm">
                Connect the tools that power Nexora. Gmail is optional — you can skip and connect later.
              </p>
            </div>

            {integrationsLoading ? (
              <div className="flex flex-col items-center py-12 gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
                <p className="text-sm text-gray-500">Checking integration status…</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* OpenAI */}
                <div className="p-5 rounded-xl border border-gray-700 bg-gray-800/50 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                        <Sparkles className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-200">OpenAI</p>
                        <p className="text-xs text-gray-500">Required for AI features</p>
                      </div>
                    </div>
                    {statusBadge(healthData?.openai?.status, healthData?.openai?.status ?? "Unknown")}
                  </div>
                  <p className="text-xs text-gray-500">
                    Powers resume analysis, job matching, and application generation.
                  </p>
                </div>

                {/* Gemini */}
                <div className="p-5 rounded-xl border border-gray-700 bg-gray-800/50 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                        <Zap className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-200">Google Gemini</p>
                        <p className="text-xs text-gray-500">Secondary AI provider</p>
                      </div>
                    </div>
                    {statusBadge(healthData?.gemini?.status, healthData?.gemini?.status ?? "Unknown")}
                  </div>
                  <p className="text-xs text-gray-500">
                    High-throughput fallback for analysis and generation tasks.
                  </p>
                </div>

                {/* PostgreSQL */}
                <div className="p-5 rounded-xl border border-gray-700 bg-gray-800/50 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                        <Database className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-200">PostgreSQL</p>
                        <p className="text-xs text-gray-500">Database</p>
                      </div>
                    </div>
                    {statusBadge(healthData?.postgres?.status, healthData?.postgres?.status ?? "Unknown")}
                  </div>
                  <p className="text-xs text-gray-500">
                    Stores your profile, matches, applications, and preferences.
                  </p>
                </div>

                {/* Gmail */}
                <div className="p-5 rounded-xl border border-gray-700 bg-gray-800/50 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
                        <Mail className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-200">Gmail</p>
                        <p className="text-xs text-gray-500">Optional</p>
                      </div>
                    </div>
                    {gmailStatus?.is_connected
                      ? statusBadge("connected", "Connected")
                      : statusBadge("disconnected", "Not Connected")}
                  </div>
                  <p className="text-xs text-gray-500">
                    Send recruiter outreach and application emails directly from Nexora.
                  </p>
                  {gmailStatus?.email && (
                    <p className="text-xs text-emerald-400">{gmailStatus.email}</p>
                  )}
                  {!gmailStatus?.is_connected && (
                    <button
                      onClick={handleConnectGmail}
                      disabled={gmailConnecting}
                      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-indigo-500/40 bg-indigo-600/10 text-indigo-300 text-xs font-medium hover:bg-indigo-600/20 transition-colors disabled:opacity-60"
                    >
                      {gmailConnecting ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <ExternalLink className="w-3.5 h-3.5" />
                      )}
                      Connect Gmail
                    </button>
                  )}
                </div>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="btn-secondary">Back</button>
              <button onClick={goNext} className="btn-primary">Next</button>
            </div>
          </div>
        )}

        {/* ================================================================
            STEP 7 — Review & Launch
        ================================================================ */}
        {currentStep === 7 && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-white">Review & Launch</h2>
              <p className="text-gray-400 mt-1 text-sm">
                Everything looks good! Review your profile and launch your job search.
              </p>
            </div>

            {/* Profile summary */}
            <div className="p-5 rounded-xl border border-gray-700 bg-gray-800/40 space-y-5">
              <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                <User className="w-4 h-4 text-indigo-400" /> Profile
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                {personalInfo.fullName && (
                  <div>
                    <p className="text-xs text-gray-500">Name</p>
                    <p className="text-gray-200 font-medium">{personalInfo.fullName}</p>
                  </div>
                )}
                {personalInfo.email && (
                  <div>
                    <p className="text-xs text-gray-500">Email</p>
                    <p className="text-gray-200">{personalInfo.email}</p>
                  </div>
                )}
                {personalInfo.location && (
                  <div>
                    <p className="text-xs text-gray-500">Location</p>
                    <p className="text-gray-200">{personalInfo.location}</p>
                  </div>
                )}
                {jobPreferences.seniority && (
                  <div>
                    <p className="text-xs text-gray-500">Level</p>
                    <p className="text-gray-200">{jobPreferences.seniority}</p>
                  </div>
                )}
              </div>

              {jobPreferences.targetRoles.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Target Roles</p>
                  <div className="flex flex-wrap gap-2">
                    {jobPreferences.targetRoles.map((r) => (
                      <span key={r} className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {jobPreferences.preferredLocations.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Preferred Locations</p>
                  <div className="flex flex-wrap gap-2">
                    {jobPreferences.preferredLocations.map((l) => (
                      <span key={l} className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600">
                        {l}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {jobPreferences.workArrangements.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Work Arrangements</p>
                  <div className="flex flex-wrap gap-2">
                    {jobPreferences.workArrangements.map((w) => (
                      <span key={w} className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600">
                        {w}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {(jobPreferences.minSalary !== "") && (
                <div>
                  <p className="text-xs text-gray-500">Min. Salary</p>
                  <p className="text-gray-200 font-medium">
                    {Number(jobPreferences.minSalary).toLocaleString()} {jobPreferences.currency}
                  </p>
                </div>
              )}

              {educationExperience.skills.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {educationExperience.skills.slice(0, 10).map((s) => (
                      <span key={s} className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600">
                        {s}
                      </span>
                    ))}
                    {educationExperience.skills.length > 10 && (
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-500">
                        +{educationExperience.skills.length - 10} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Integration status */}
            <div className="p-5 rounded-xl border border-gray-700 bg-gray-800/40 space-y-3">
              <h3 className="text-sm font-semibold text-gray-200">Integration Status</h3>
              <div className="flex flex-wrap gap-3">
                {statusBadge(healthData?.openai?.status, `OpenAI: ${healthData?.openai?.status ?? "Unknown"}`)}
                {statusBadge(healthData?.gemini?.status, `Gemini: ${healthData?.gemini?.status ?? "Unknown"}`)}
                {statusBadge(healthData?.postgres?.status, `DB: ${healthData?.postgres?.status ?? "Unknown"}`)}
                {statusBadge(gmailStatus?.is_connected ? "connected" : "disconnected", `Gmail: ${gmailStatus?.is_connected ? "Connected" : "Not connected"}`)}
              </div>
            </div>

            {/* Job matches */}
            {onboardingResult && (
              <div className="p-5 rounded-xl border border-indigo-500/30 bg-indigo-600/5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                    <Star className="w-4 h-4 text-indigo-400" /> Job Matches Found
                  </h3>
                  <span className="text-2xl font-bold text-indigo-400">
                    {onboardingResult.matching_jobs_count}
                  </span>
                </div>

                {onboardingResult.top_matches.slice(0, 3).map((match, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-gray-800/60 border border-gray-700"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-200">{match.job_title}</p>
                      <p className="text-xs text-gray-500">{match.company_name}</p>
                    </div>
                    <span className="text-sm font-bold text-indigo-400">
                      {Math.round(match.match_score * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <button onClick={goBack} className="btn-secondary">Back</button>
              <button
                onClick={() => setCurrentStep(4)}
                className="btn-secondary"
              >
                Edit Preferences
              </button>
              <button
                onClick={handleLaunch}
                className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-colors shadow-lg shadow-indigo-500/20"
              >
                <Rocket className="w-4 h-4" />
                Launch My Job Search
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Global button styles via Tailwind utility class overrides as inline Tailwind */}
      <style>{`
        .btn-primary {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 0.625rem 1.5rem;
          border-radius: 0.5rem;
          background-color: rgb(79 70 229);
          color: #fff;
          font-size: 0.875rem;
          font-weight: 600;
          transition: background-color 0.15s;
          cursor: pointer;
        }
        .btn-primary:hover { background-color: rgb(99 102 241); }
        .btn-secondary {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 0.625rem 1.5rem;
          border-radius: 0.5rem;
          border: 1px solid rgb(55 65 81);
          background-color: rgb(31 41 55);
          color: rgb(209 213 219);
          font-size: 0.875rem;
          font-weight: 500;
          transition: background-color 0.15s, border-color 0.15s;
          cursor: pointer;
        }
        .btn-secondary:hover { background-color: rgb(55 65 81); border-color: rgb(75 85 99); }
      `}</style>
    </div>
  );
}
