"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bot,
  Brain,
  Briefcase,
  Check,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  Download,
  FileQuestion,
  FileText,
  GraduationCap,
  HelpCircle,
  History,
  Info,
  Layers,
  Lightbulb,
  Link as LinkIcon,
  Loader2,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  UploadCloud,
  X,
  Zap,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  downloadFile,
  EvidenceItem,
  ResumeAnalysisDetail,
  ResumeAnalysisSummary,
  ResumeDetail,
  ResumeSummary,
  ResumeVersionDetail,
} from "@/lib/api";

export default function ResumeStudioPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Detail & Version viewing state
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [resumeDetail, setResumeDetail] = useState<ResumeDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"profile" | "history" | "intelligence">("profile");

  // Selected version for inspection in version history
  const [selectedVersionDetail, setSelectedVersionDetail] = useState<ResumeVersionDetail | null>(null);

  // AI Resume Intelligence state
  const [analysesList, setAnalysesList] = useState<ResumeAnalysisSummary[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<ResumeAnalysisDetail | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [evidenceModalData, setEvidenceModalData] = useState<{
    title: string;
    evidence: EvidenceItem[];
  } | null>(null);

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [uploadMode, setUploadMode] = useState<"new_resume" | "new_version">("new_resume");
  const [targetResumeId, setTargetResumeId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState<string>("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Delete modal state
  const [deleteTarget, setDeleteTarget] = useState<ResumeSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Redirect unauthenticated users
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Fetch all resumes
  const fetchResumes = useCallback(async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const data = await apiClient<ResumeSummary[]>("/api/v1/resumes");
      setResumes(data);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setErrorMessage(errorObj.message || "Failed to load resumes");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchResumes();
    }
  }, [user, fetchResumes]);

  // Fetch AI analysis history for a resume
  const fetchAnalyses = useCallback(async (resumeId: string) => {
    try {
      setIsLoadingAnalysis(true);
      setAnalysisError(null);
      const history = await apiClient<ResumeAnalysisSummary[]>(
        `/api/v1/resumes/${resumeId}/analysis`
      );
      setAnalysesList(history);
      if (history.length > 0) {
        // Load the latest completed or first analysis detail
        const latestDetail = await apiClient<ResumeAnalysisDetail>(
          `/api/v1/resumes/${resumeId}/analysis/${history[0].id}`
        );
        setActiveAnalysis(latestDetail);
      } else {
        setActiveAnalysis(null);
      }
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setAnalysisError(errorObj.message || "Failed to load AI intelligence data");
    } finally {
      setIsLoadingAnalysis(false);
    }
  }, []);

  // Fetch full details of a resume
  const handleSelectResume = async (resumeId: string) => {
    setSelectedResumeId(resumeId);
    setSelectedVersionDetail(null);
    setActiveTab("profile");
    try {
      setIsLoadingDetail(true);
      const detail = await apiClient<ResumeDetail>(`/api/v1/resumes/${resumeId}`);
      setResumeDetail(detail);
      setSelectedVersionDetail(detail.current_version || null);
      await fetchAnalyses(resumeId);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setErrorMessage(errorObj.message || "Failed to load resume details");
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Run AI analysis
  const handleRunAnalysis = async (forceRefresh = false) => {
    if (!resumeDetail) return;
    const versionId =
      selectedVersionDetail?.id || resumeDetail.current_version?.id;
    if (!versionId) return;

    try {
      setIsAnalyzing(true);
      setAnalysisError(null);
      const result = await apiClient<ResumeAnalysisDetail>(
        `/api/v1/resumes/${resumeDetail.id}/versions/${versionId}/analysis`,
        {
          method: "POST",
          body: JSON.stringify({ force_refresh: forceRefresh }),
        }
      );
      setActiveAnalysis(result);
      await fetchAnalyses(resumeDetail.id);
    } catch (err: unknown) {
      const errorObj = err as { message?: string; code?: string };
      if (errorObj.code === "AI_CONFIG_ERROR") {
        setAnalysisError(
          "AI Provider Unavailable: Please configure GEMINI_API_KEY or OPENAI_API_KEY in the backend environment."
        );
      } else {
        setAnalysisError(errorObj.message || "AI Analysis request failed.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Load a past analysis
  const handleLoadAnalysis = async (analysisId: string) => {
    if (!resumeDetail) return;
    try {
      setIsLoadingAnalysis(true);
      const detail = await apiClient<ResumeAnalysisDetail>(
        `/api/v1/resumes/${resumeDetail.id}/analysis/${analysisId}`
      );
      setActiveAnalysis(detail);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setAnalysisError(errorObj.message || "Failed to load past analysis");
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  // Inspect a past version
  const handleInspectVersion = async (resumeId: string, versionId: string) => {
    try {
      const vDetail = await apiClient<ResumeVersionDetail>(
        `/api/v1/resumes/${resumeId}/versions/${versionId}`
      );
      setSelectedVersionDetail(vDetail);
      setActiveTab("profile");
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setErrorMessage(errorObj.message || "Failed to load version details");
    }
  };

  // Open upload modal for brand new resume
  const openNewResumeUpload = () => {
    setUploadMode("new_resume");
    setTargetResumeId(null);
    setUploadFile(null);
    setUploadTitle("");
    setUploadError(null);
    setIsUploadOpen(true);
  };

  // Open upload modal for a new version of existing resume
  const openNewVersionUpload = (resumeId: string, resumeTitle: string) => {
    setUploadMode("new_version");
    setTargetResumeId(resumeId);
    setUploadFile(null);
    setUploadTitle(`Version of ${resumeTitle}`);
    setUploadError(null);
    setIsUploadOpen(true);
  };

  // Handle file selection and client-side validation
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const lowerName = file.name.toLowerCase();
    const isPdf = lowerName.endsWith(".pdf");
    const isDocx = lowerName.endsWith(".docx");

    if (!isPdf && !isDocx) {
      setUploadError("Only .pdf and .docx files are supported.");
      setUploadFile(null);
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError("File size must not exceed 10MB.");
      setUploadFile(null);
      return;
    }

    setUploadError(null);
    setUploadFile(file);
    if (!uploadTitle && uploadMode === "new_resume") {
      setUploadTitle(file.name.replace(/\.[^/.]+$/, ""));
    }
  };

  // Submit file upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a valid resume document.");
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);

      const formData = new FormData();
      formData.append("file", uploadFile);
      if (uploadTitle.trim()) {
        formData.append("title", uploadTitle.trim());
      }

      if (uploadMode === "new_resume") {
        const newResume = await apiClient<ResumeDetail>("/api/v1/resumes", {
          method: "POST",
          body: formData,
        });
        setIsUploadOpen(false);
        await fetchResumes();
        await handleSelectResume(newResume.id);
      } else if (uploadMode === "new_version" && targetResumeId) {
        await apiClient<ResumeVersionDetail>(
          `/api/v1/resumes/${targetResumeId}/versions`,
          {
            method: "POST",
            body: formData,
          }
        );
        setIsUploadOpen(false);
        await fetchResumes();
        await handleSelectResume(targetResumeId);
      }
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setUploadError(errorObj.message || "Upload and parsing failed.");
    } finally {
      setIsUploading(false);
    }
  };

  // Download document
  const handleDownload = async (
    resumeId: string,
    versionId?: string,
    filename?: string
  ) => {
    try {
      const endpoint = versionId
        ? `/api/v1/resumes/${resumeId}/versions/${versionId}/download`
        : `/api/v1/resumes/${resumeId}/download`;
      await downloadFile(endpoint, filename || "resume-document");
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      alert(`Download failed: ${errorObj.message || "Unknown error"}`);
    }
  };

  // Confirm delete
  const handleDeleteResume = async () => {
    if (!deleteTarget) return;

    try {
      setIsDeleting(true);
      await apiClient(`/api/v1/resumes/${deleteTarget.id}`, {
        method: "DELETE",
      });
      setDeleteTarget(null);
      if (selectedResumeId === deleteTarget.id) {
        setSelectedResumeId(null);
        setResumeDetail(null);
      }
      await fetchResumes();
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      alert(`Deletion failed: ${errorObj.message || "Unknown error"}`);
    } finally {
      setIsDeleting(false);
    }
  };

  if (authLoading || (!user && isLoading)) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Authenticating session...</p>
      </main>
    );
  }

  return (
    <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between pb-6 border-b border-border mb-6">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="p-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                <Sparkles className="w-3.5 h-3.5" /> Resume Studio
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-1">
              Resume Studio & AI Intelligence
            </h1>
            <p className="text-sm text-muted-foreground">
              Deterministic parsing, versioning, and grounded AI insights for your career journey.
            </p>
          </div>
        </div>

        <button
          onClick={openNewResumeUpload}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm shadow hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" /> Upload Resume
        </button>
      </div>

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span className="text-sm">{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs hover:underline font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid Layout: List on Left, Detail Viewer on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Resumes List (4 cols) */}
        <section className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <FileText className="w-4 h-4" /> My Resumes ({resumes.length})
            </h2>
            <button
              onClick={fetchResumes}
              className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
              title="Refresh resumes"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>

          {isLoading ? (
            <div className="p-8 text-center bg-card border border-border rounded-xl">
              <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">Loading resumes...</p>
            </div>
          ) : resumes.length === 0 ? (
            <div className="p-8 text-center bg-card border border-dashed border-border rounded-xl">
              <UploadCloud className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
              <h3 className="text-sm font-semibold">No resumes uploaded yet</h3>
              <p className="text-xs text-muted-foreground mt-1 mb-4">
                Upload your first PDF or DOCX resume to extract skills, experience, and unlock AI Intelligence.
              </p>
              <button
                onClick={openNewResumeUpload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Upload Now
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {resumes.map((item) => {
                const isSelected = selectedResumeId === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => handleSelectResume(item.id)}
                    className={`group relative p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border-border bg-card hover:border-primary/50 hover:bg-secondary/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold truncate text-foreground">
                          {item.title}
                        </h3>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {item.original_filename || "Document"}
                        </p>
                      </div>

                      {/* Status Badge */}
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider shrink-0 ${
                          item.parsing_status === "parsed"
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                            : item.parsing_status === "failed"
                            ? "bg-destructive/10 text-destructive"
                            : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                        }`}
                      >
                        {item.parsing_status === "parsed" && (
                          <CheckCircle2 className="w-3 h-3" />
                        )}
                        {item.parsing_status === "failed" && (
                          <AlertCircle className="w-3 h-3" />
                        )}
                        {item.parsing_status === "uploaded" && (
                          <Clock className="w-3 h-3" />
                        )}
                        {item.parsing_status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-muted-foreground mt-3 pt-2 border-t border-border/50">
                      <span className="flex items-center gap-1 font-mono text-[11px]">
                        <Layers className="w-3.5 h-3.5" /> v{item.current_version_number || 1}{" "}
                        ({item.version_count} {item.version_count === 1 ? "version" : "versions"})
                      </span>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownload(item.id, undefined, item.original_filename || undefined);
                          }}
                          title="Download original file"
                          className="p-1 hover:text-foreground rounded transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(item);
                          }}
                          title="Delete resume"
                          className="p-1 hover:text-destructive rounded transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Right Column: Resume Detail, Profile, & AI Intelligence (8 cols) */}
        <section className="lg:col-span-8">
          {!selectedResumeId ? (
            <div className="p-12 text-center bg-card border border-border rounded-xl">
              <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
              <h3 className="text-base font-semibold">Select a resume to inspect</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                Choose a resume from the list on the left to review its parsed profile, examine version history, or trigger grounded AI Intelligence analysis.
              </p>
            </div>
          ) : isLoadingDetail ? (
            <div className="p-12 text-center bg-card border border-border rounded-xl">
              <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">Extracting resume profile...</p>
            </div>
          ) : resumeDetail ? (
            <div className="bg-card border border-border rounded-xl p-6 space-y-6">
              {/* Detail Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold tracking-tight">{resumeDetail.title}</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono font-medium bg-secondary text-secondary-foreground">
                      v{selectedVersionDetail?.version_number || resumeDetail.current_version?.version_number || 1}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Uploaded {new Date(resumeDetail.created_at).toLocaleDateString()} •{" "}
                    {selectedVersionDetail?.original_filename || resumeDetail.current_version?.original_filename} (
                    {Math.round(((selectedVersionDetail?.file_size || resumeDetail.current_version?.file_size || 0) / 1024) * 10) / 10} KB)
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      handleDownload(
                        resumeDetail.id,
                        selectedVersionDetail?.id,
                        selectedVersionDetail?.original_filename
                      )
                    }
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary transition-colors"
                  >
                    <Download className="w-3.5 h-3.5 text-muted-foreground" /> Download
                  </button>
                  <button
                    onClick={() => openNewVersionUpload(resumeDetail.id, resumeDetail.title)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
                  >
                    <Plus className="w-3.5 h-3.5" /> Upload New Version
                  </button>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-border gap-2">
                <button
                  onClick={() => setActiveTab("profile")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === "profile"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <FileText className="w-4 h-4" /> Parsed Profile
                </button>
                <button
                  onClick={() => setActiveTab("intelligence")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === "intelligence"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Brain className="w-4 h-4" /> AI Intelligence
                  {activeAnalysis && (
                    <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                  )}
                </button>
                <button
                  onClick={() => setActiveTab("history")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === "history"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <History className="w-4 h-4" /> Version History ({resumeDetail.version_count})
                </button>
              </div>

              {/* TAB 1: Structured Profile View */}
              {activeTab === "profile" && (
                <div className="space-y-6">
                  {/* Parsing Error Warning */}
                  {selectedVersionDetail?.parsing_status === "failed" && (
                    <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-sm font-semibold">Parsing Incomplete</h4>
                          <p className="text-xs mt-1">
                            {selectedVersionDetail.error_summary ||
                              "No readable text found. If this is a scanned document, please upload a text-based PDF or DOCX."}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Contact Info Header */}
                  {selectedVersionDetail?.parsed_content?.contact && (
                    <div className="p-4 rounded-lg bg-secondary/40 border border-border/60">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                        Contact Information
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                        {selectedVersionDetail.parsed_content.contact.name && (
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Full Name</span>
                            <span className="font-semibold text-foreground text-sm">
                              {selectedVersionDetail.parsed_content.contact.name}
                            </span>
                          </div>
                        )}
                        {selectedVersionDetail.parsed_content.contact.email && (
                          <div className="flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                            <span className="font-mono">{selectedVersionDetail.parsed_content.contact.email}</span>
                          </div>
                        )}
                        {selectedVersionDetail.parsed_content.contact.phone && (
                          <div className="flex items-center gap-1.5">
                            <Phone className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                            <span className="font-mono">{selectedVersionDetail.parsed_content.contact.phone}</span>
                          </div>
                        )}
                      </div>

                      {/* External Links */}
                      {selectedVersionDetail.parsed_content.contact.links &&
                        selectedVersionDetail.parsed_content.contact.links.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-border/50 flex flex-wrap gap-2">
                            {selectedVersionDetail.parsed_content.contact.links.map((link, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-background border border-border font-mono text-muted-foreground"
                              >
                                <LinkIcon className="w-3 h-3 text-primary" /> {link}
                              </span>
                            ))}
                          </div>
                        )}
                    </div>
                  )}

                  {/* Summary */}
                  {selectedVersionDetail?.parsed_content?.summary && (
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-primary" /> Professional Summary
                      </h3>
                      <p className="text-sm text-foreground/90 leading-relaxed p-3.5 rounded-lg bg-secondary/30 border border-border/40">
                        {selectedVersionDetail.parsed_content.summary}
                      </p>
                    </div>
                  )}

                  {/* Skills Tag Cloud */}
                  {selectedVersionDetail?.parsed_content?.skills &&
                    selectedVersionDetail.parsed_content.skills.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                          Extracted Skills ({selectedVersionDetail.parsed_content.skills.length})
                        </h3>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedVersionDetail.parsed_content.skills.map((skill, idx) => (
                            <span
                              key={idx}
                              className="px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Experience Timeline */}
                  {selectedVersionDetail?.parsed_content?.experience &&
                    selectedVersionDetail.parsed_content.experience.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                          <Briefcase className="w-3.5 h-3.5 text-primary" /> Work Experience
                        </h3>
                        <div className="space-y-4">
                          {selectedVersionDetail.parsed_content.experience.map((exp, idx) => (
                            <div
                              key={idx}
                              className="p-4 rounded-lg bg-secondary/20 border border-border/50 space-y-2"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                                <h4 className="text-sm font-semibold text-foreground">
                                  {exp.title} {exp.company && <span className="text-muted-foreground font-normal">at {exp.company}</span>}
                                </h4>
                                {exp.date_range && (
                                  <span className="text-xs text-muted-foreground font-mono">
                                    {exp.date_range}
                                  </span>
                                )}
                              </div>
                              {exp.bullets && exp.bullets.length > 0 && (
                                <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1 pl-1">
                                  {exp.bullets.map((b, bIdx) => (
                                    <li key={bIdx}>{b}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Education */}
                  {selectedVersionDetail?.parsed_content?.education &&
                    selectedVersionDetail.parsed_content.education.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                          <GraduationCap className="w-3.5 h-3.5 text-primary" /> Education
                        </h3>
                        <div className="space-y-3">
                          {selectedVersionDetail.parsed_content.education.map((edu, idx) => (
                            <div
                              key={idx}
                              className="p-3.5 rounded-lg bg-secondary/20 border border-border/50 text-xs"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-foreground">{edu.degree || edu.institution}</span>
                                {edu.year && <span className="text-muted-foreground font-mono">{edu.year}</span>}
                              </div>
                              {edu.institution && edu.degree && (
                                <p className="text-muted-foreground mt-0.5">{edu.institution}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              )}

              {/* TAB 2: AI Resume Intelligence View */}
              {activeTab === "intelligence" && (
                <div className="space-y-6">
                  {/* AI Transparency & Privacy Banner */}
                  <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5">
                        <Cpu className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold flex items-center gap-2">
                          Grounded AI Resume Intelligence
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary uppercase">
                            Evidence Based
                          </span>
                        </h3>
                        <p className="text-xs text-muted-foreground mt-0.5 max-w-xl">
                          Analyzes your resume version strictly against extracted evidence. We do not rewrite, overwrite, or fabricate claims. Resume text is transmitted securely to your configured AI provider.
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {activeAnalysis && (
                        <button
                          onClick={() => handleRunAnalysis(true)}
                          disabled={isAnalyzing}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary transition-colors disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? "animate-spin" : ""}`} /> Re-analyze
                        </button>
                      )}
                      <button
                        onClick={() => handleRunAnalysis(false)}
                        disabled={isAnalyzing}
                        className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50"
                      >
                        {isAnalyzing ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Sparkles className="w-4 h-4" />
                        )}
                        {isAnalyzing ? "Analyzing Resume..." : activeAnalysis ? "Refresh Analysis" : "Analyze Resume"}
                      </button>
                    </div>
                  </div>

                  {/* Analysis Error Alert */}
                  {analysisError && (
                    <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-sm font-semibold">Analysis Unavailable</h4>
                        <p className="text-xs mt-1 leading-relaxed">{analysisError}</p>
                      </div>
                    </div>
                  )}

                  {/* Loading State */}
                  {isAnalyzing && (
                    <div className="p-12 text-center bg-card border border-border rounded-xl space-y-3">
                      <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
                      <h4 className="text-sm font-semibold">Generating Grounded Analysis...</h4>
                      <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                        Evaluating candidate profile, auditing skill evidence, scoring role suitability heuristics, and compiling prioritized recommendations.
                      </p>
                    </div>
                  )}

                  {/* Empty State */}
                  {!isAnalyzing && !activeAnalysis && !analysisError && (
                    <div className="p-12 text-center bg-card border border-dashed border-border rounded-xl space-y-4">
                      <Brain className="w-12 h-12 text-muted-foreground mx-auto opacity-50" />
                      <div>
                        <h3 className="text-base font-semibold">No AI Analysis for this Version Yet</h3>
                        <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                          Click &quot;Analyze Resume&quot; above to generate grounded career domains, supported vs. unevidenced skill audits, role suitability scores, and prioritized improvements.
                        </p>
                      </div>
                      <button
                        onClick={() => handleRunAnalysis(false)}
                        className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                      >
                        <Sparkles className="w-4 h-4" /> Start AI Analysis
                      </button>
                    </div>
                  )}

                  {/* Active Analysis Results */}
                  {!isAnalyzing && activeAnalysis && activeAnalysis.result && (
                    <div className="space-y-6">
                      {/* Top Summary Banner */}
                      <div className="p-5 rounded-xl bg-card border border-border shadow-sm space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/60">
                          <div>
                            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                              Candidate Stated Profile
                            </span>
                            <h3 className="text-base font-bold text-foreground mt-0.5">
                              {activeAnalysis.result.profile.summary}
                            </h3>
                          </div>

                          {/* Career Level Estimate Badge */}
                          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground font-semibold text-xs border border-border shrink-0 self-start sm:self-auto">
                            <Compass className="w-4 h-4 text-primary" />
                            <span>{activeAnalysis.result.profile.career_level_estimate}</span>
                          </div>
                        </div>

                        {/* Domains & Provider Metadata */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-muted-foreground mr-1">Primary Domains:</span>
                            {activeAnalysis.result.profile.domains.map((dom, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded text-[11px] font-medium bg-secondary text-foreground"
                              >
                                {dom}
                              </span>
                            ))}
                          </div>

                          <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                            <span>
                              Provider: <strong className="text-foreground">{activeAnalysis.provider}</strong> ({activeAnalysis.model})
                            </span>
                            {activeAnalysis.total_tokens && (
                              <span>• {activeAnalysis.total_tokens} tokens</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* SECTION 1: Role Suitability Matrix */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <h3 className="text-sm font-semibold flex items-center gap-2">
                              <Target className="w-4 h-4 text-primary" /> Role Suitability Heuristics
                            </h3>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Heuristic AI evaluations based strictly on evidenced skills. Not a hiring probability.
                            </p>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {activeAnalysis.result.role_suitability.map((role, idx) => (
                            <div
                              key={idx}
                              className="p-4 rounded-xl border border-border bg-card space-y-3"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <h4 className="text-sm font-semibold text-foreground">
                                    {role.role_name}
                                  </h4>
                                  <span className="text-[10px] text-muted-foreground">
                                    Confidence: {role.confidence}
                                  </span>
                                </div>

                                <div className="text-right">
                                  <span
                                    className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                      role.heuristic_score >= 80
                                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                        : role.heuristic_score >= 60
                                        ? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                                        : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                    }`}
                                  >
                                    {role.suitability_band} ({role.heuristic_score}%)
                                  </span>
                                </div>
                              </div>

                              {/* Progress bar */}
                              <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all duration-500 ${
                                    role.heuristic_score >= 80
                                      ? "bg-emerald-500"
                                      : role.heuristic_score >= 60
                                      ? "bg-blue-500"
                                      : "bg-amber-500"
                                  }`}
                                  style={{ width: `${role.heuristic_score}%` }}
                                />
                              </div>

                              {/* Strengths & Gaps */}
                              <div className="space-y-1.5 text-xs">
                                {role.strengths && role.strengths.length > 0 && (
                                  <div>
                                    <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 block mb-1">
                                      Key Strengths:
                                    </span>
                                    <ul className="list-disc list-inside text-muted-foreground space-y-0.5 pl-1">
                                      {role.strengths.map((s, sIdx) => (
                                        <li key={sIdx}>{s}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {role.gaps && role.gaps.length > 0 && (
                                  <div className="pt-1">
                                    <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 block mb-1">
                                      Identified Gaps:
                                    </span>
                                    <ul className="list-disc list-inside text-muted-foreground space-y-0.5 pl-1">
                                      {role.gaps.map((g, gIdx) => (
                                        <li key={gIdx}>{g}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>

                              {/* Evidence Inspection Button */}
                              {role.evidence && role.evidence.length > 0 && (
                                <div className="pt-2 border-t border-border/50">
                                  <button
                                    onClick={() =>
                                      setEvidenceModalData({
                                        title: `${role.role_name} Evidence`,
                                        evidence: role.evidence,
                                      })
                                    }
                                    className="text-[11px] font-medium text-primary hover:underline flex items-center gap-1"
                                  >
                                    <Info className="w-3 h-3" /> View Source Evidence ({role.evidence.length})
                                  </button>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* SECTION 2: Skills Evidence Breakdown */}
                      <div className="p-5 rounded-xl border border-border bg-card space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-semibold flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-primary" /> Skills Evidence Breakdown
                          </h3>
                          <span className="text-xs text-muted-foreground">
                            Self-reported • Unverified
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Supported Skills */}
                          <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                            <div className="flex items-center gap-2 mb-2 text-emerald-700 dark:text-emerald-400 font-semibold text-xs">
                              <Check className="w-4 h-4" /> Supported by Experience Evidence
                            </div>
                            <p className="text-[11px] text-muted-foreground mb-3">
                              Skills contextualized with project or employment descriptions:
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {activeAnalysis.result.skills.supported_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Unevidenced Skills */}
                          <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
                            <div className="flex items-center gap-2 mb-2 text-amber-700 dark:text-amber-400 font-semibold text-xs">
                              <HelpCircle className="w-4 h-4" /> Mentioned Without Context
                            </div>
                            <p className="text-[11px] text-muted-foreground mb-3">
                              Listed in skills section but lacking detail in work experience:
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {activeAnalysis.result.skills.unevidenced_skills.length > 0 ? (
                                activeAnalysis.result.skills.unevidenced_skills.map((s, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-0.5 rounded text-xs bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30"
                                  >
                                    {s}
                                  </span>
                                ))
                              ) : (
                                <span className="text-xs text-muted-foreground italic">
                                  All listed skills appear supported by experience.
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* SECTION 3: Measurable Outcomes & Vague Claims */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Measurable Outcomes */}
                        <div className="p-4 rounded-xl border border-border bg-card space-y-3">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4" /> Explicit Measurable Outcomes
                          </h4>
                          {activeAnalysis.result.experience_evidence.measurable_outcomes.length > 0 ? (
                            <ul className="space-y-2">
                              {activeAnalysis.result.experience_evidence.measurable_outcomes.map((m, idx) => (
                                <li
                                  key={idx}
                                  className="p-2.5 rounded-lg bg-secondary/30 text-xs text-foreground/90 border border-border/40"
                                >
                                  {m}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-muted-foreground italic">
                              No explicit quantified metrics found in experience statements.
                            </p>
                          )}
                        </div>

                        {/* Vague Claims */}
                        <div className="p-4 rounded-xl border border-border bg-card space-y-3">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                            <FileQuestion className="w-4 h-4" /> Vague or Unsupported Claims
                          </h4>
                          {activeAnalysis.result.experience_evidence.vague_or_unsupported_claims.length > 0 ? (
                            <ul className="space-y-2">
                              {activeAnalysis.result.experience_evidence.vague_or_unsupported_claims.map((v, idx) => (
                                <li
                                  key={idx}
                                  className="p-2.5 rounded-lg bg-secondary/30 text-xs text-muted-foreground border border-border/40"
                                >
                                  {v}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-muted-foreground italic">
                              No overtly vague claims detected.
                            </p>
                          )}
                        </div>
                      </div>

                      {/* SECTION 4: Prioritized Recommendations */}
                      <div className="p-5 rounded-xl border border-border bg-card space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-semibold flex items-center gap-2">
                            <Lightbulb className="w-4 h-4 text-primary" /> Prioritized Actionable Recommendations
                          </h3>
                          <span className="text-xs text-muted-foreground">
                            Sorted by impact
                          </span>
                        </div>

                        <div className="space-y-3">
                          {activeAnalysis.result.recommendations.map((rec, idx) => (
                            <div
                              key={idx}
                              className="p-4 rounded-lg bg-secondary/20 border border-border/60 space-y-2"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <h4 className="text-xs font-semibold text-foreground flex items-center gap-2">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                                      rec.priority === "high"
                                        ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
                                        : rec.priority === "medium"
                                        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                                        : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
                                    }`}
                                  >
                                    {rec.priority} Priority
                                  </span>
                                  {rec.title}
                                </h4>
                              </div>

                              <p className="text-xs text-foreground/90 leading-relaxed">
                                <strong>Issue:</strong> {rec.issue}
                              </p>
                              <p className="text-xs text-muted-foreground leading-relaxed">
                                <strong>Why It Matters:</strong> {rec.why_it_matters}
                              </p>
                              <div className="pt-1.5 text-xs text-primary font-medium">
                                <strong>Action:</strong> {rec.suggested_action}
                              </div>

                              {rec.referenced_evidence && (
                                <p className="text-[11px] text-muted-foreground font-mono bg-background/50 p-2 rounded border border-border/40">
                                  Source text: &quot;{rec.referenced_evidence}&quot;
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* SECTION 5: Analysis History */}
                      {analysesList.length > 1 && (
                        <div className="p-4 rounded-xl border border-border bg-card space-y-3">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                            <History className="w-4 h-4" /> Previous Analyses ({analysesList.length})
                          </h4>
                          <div className="space-y-2">
                            {analysesList.map((a) => {
                              const isCurrent = activeAnalysis.id === a.id;
                              return (
                                <div
                                  key={a.id}
                                  onClick={() => handleLoadAnalysis(a.id)}
                                  className={`p-3 rounded-lg border text-xs flex items-center justify-between cursor-pointer transition-colors ${
                                    isCurrent
                                      ? "border-primary bg-primary/5"
                                      : "border-border bg-background hover:bg-secondary/40"
                                  }`}
                                >
                                  <div>
                                    <span className="font-semibold">{a.career_level || "Analysis"}</span>
                                    <span className="text-muted-foreground block text-[11px]">
                                      {new Date(a.created_at).toLocaleString()} via {a.provider} ({a.model})
                                    </span>
                                  </div>
                                  <span
                                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                                      a.status === "completed"
                                        ? "bg-emerald-500/10 text-emerald-600"
                                        : "bg-amber-500/10 text-amber-600"
                                    }`}
                                  >
                                    {a.status}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Version History */}
              {activeTab === "history" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-border">
                    <p className="text-xs text-muted-foreground">
                      Each document upload is saved as an immutable version with preserved parsed snapshots.
                    </p>
                    <button
                      onClick={() => openNewVersionUpload(resumeDetail.id, resumeDetail.title)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
                    >
                      <Plus className="w-3 h-3" /> New Version
                    </button>
                  </div>

                  <div className="space-y-2">
                    {resumeDetail.versions.map((ver) => {
                      const isCurrentInspected =
                        selectedVersionDetail?.id === ver.id;
                      return (
                        <div
                          key={ver.id}
                          className={`p-3.5 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
                            isCurrentInspected
                              ? "border-primary bg-primary/5"
                              : "border-border bg-card hover:bg-secondary/40"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center font-mono text-xs font-semibold">
                              v{ver.version_number}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold">{ver.original_filename}</span>
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                                    ver.parsing_status === "parsed"
                                      ? "bg-emerald-500/10 text-emerald-600"
                                      : "bg-amber-500/10 text-amber-600"
                                  }`}
                                >
                                  {ver.parsing_status}
                                </span>
                              </div>
                              <span className="text-[11px] text-muted-foreground">
                                Uploaded on {new Date(ver.created_at).toLocaleString()} •{" "}
                                {Math.round((ver.file_size / 1024) * 10) / 10} KB
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 self-end sm:self-center">
                            <button
                              onClick={() => handleInspectVersion(resumeDetail.id, ver.id)}
                              className="px-2.5 py-1 text-xs rounded border border-border bg-background hover:bg-secondary transition-colors"
                            >
                              View Profile
                            </button>
                            <button
                              onClick={() =>
                                handleDownload(resumeDetail.id, ver.id, ver.original_filename)
                              }
                              className="p-1.5 rounded border border-border bg-background hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                              title="Download version file"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </section>
      </div>

      {/* Evidence Excerpt Inspection Modal */}
      {evidenceModalData && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => setEvidenceModalData(null)}
              className="absolute top-4 right-4 p-1 text-muted-foreground hover:text-foreground rounded"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-base font-semibold flex items-center gap-2">
              <Info className="w-4 h-4 text-primary" /> {evidenceModalData.title}
            </h3>
            <p className="text-xs text-muted-foreground mt-1 mb-4">
              Direct source excerpts extracted from your uploaded resume version:
            </p>

            <div className="space-y-2 max-h-80 overflow-y-auto">
              {evidenceModalData.evidence.map((ev, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-secondary/30 border border-border/50 text-xs space-y-1"
                >
                  <span className="font-semibold text-primary uppercase text-[10px] tracking-wider block">
                    Section: {ev.section}
                  </span>
                  <p className="text-foreground/90 font-mono text-[11px] leading-relaxed">
                    &quot;{ev.excerpt}&quot;
                  </p>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-4 border-t border-border mt-4">
              <button
                onClick={() => setEvidenceModalData(null)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal (New Resume or New Version) */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-md w-full p-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => setIsUploadOpen(false)}
              className="absolute top-4 right-4 p-1 text-muted-foreground hover:text-foreground rounded"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-base font-semibold">
              {uploadMode === "new_resume" ? "Upload New Resume" : "Upload New Resume Version"}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Supports .pdf and .docx documents (up to 10MB). Text is extracted deterministically.
            </p>

            {uploadError && (
              <div className="mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
              {uploadMode === "new_resume" && (
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Resume Title
                  </label>
                  <input
                    type="text"
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                    placeholder="e.g. Senior Software Engineer"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
              )}

              {/* Dropzone File Picker */}
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
                  File Document (.pdf, .docx)
                </label>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                />

                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="p-6 border-2 border-dashed border-border hover:border-primary rounded-xl text-center cursor-pointer bg-secondary/20 hover:bg-secondary/40 transition-colors"
                >
                  <UploadCloud className="w-8 h-8 text-primary mx-auto mb-2" />
                  {uploadFile ? (
                    <div>
                      <p className="text-xs font-semibold text-foreground truncate max-w-xs mx-auto">
                        {uploadFile.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {Math.round((uploadFile.size / 1024) * 10) / 10} KB • Click to change
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-medium text-foreground">
                        Click or drag file here to upload
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        PDF or DOCX up to 10MB
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-3 py-2 text-xs font-medium rounded-lg border border-border hover:bg-secondary transition-colors"
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
                >
                  {isUploading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {isUploading ? "Uploading & Parsing..." : "Upload & Parse"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-sm w-full p-6 shadow-xl animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-base font-semibold text-destructive flex items-center gap-2">
              <Trash2 className="w-4 h-4" /> Delete Resume
            </h3>
            <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
              Are you sure you want to permanently delete{" "}
              <span className="font-semibold text-foreground">{deleteTarget.title}</span>? All
              versions, parsed profile snapshots, and stored documents will be removed. This cannot
              be undone.
            </p>

            <div className="flex items-center justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-secondary transition-colors"
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteResume}
                disabled={isDeleting}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50"
              >
                {isDeleting && <Loader2 className="w-3 h-3 animate-spin" />}
                {isDeleting ? "Deleting..." : "Confirm Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
