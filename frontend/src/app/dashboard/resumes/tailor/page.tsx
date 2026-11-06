"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BookmarkCheck,
  Briefcase,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Code,
  FileCode,
  FileText,
  History,
  Layers,
  LayoutGrid,
  Loader2,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  fetchBlob,
  Job,
  JobListResponse,
  ResumeSummary,
  tailoringApi,
  TailoringSession,
  TailoringSessionSummary,
} from "@/lib/api";

import { JobAlignmentPanel } from "./components/JobAlignmentPanel";
import { MonacoResumeEditor } from "./components/MonacoResumeEditor";
import { NewSessionModal } from "./components/NewSessionModal";
import { PdfPreviewPanel } from "./components/PdfPreviewPanel";
import { SaveVersionModal } from "./components/SaveVersionModal";
import { SuggestionReviewPanel } from "./components/SuggestionReviewPanel";

function TailoringStudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading } = useAuth();

  const paramSessionId = searchParams.get("sessionId");
  const paramJobId = searchParams.get("jobId");
  const paramResumeId = searchParams.get("resumeId");

  const [session, setSession] = useState<TailoringSession | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [pastSessions, setPastSessions] = useState<TailoringSessionSummary[]>([]);

  const [isLoadingSession, setIsLoadingSession] = useState<boolean>(true);
  const [isCompilingPdf, setIsCompilingPdf] = useState<boolean>(false);
  const [isSavingContent, setIsSavingContent] = useState<boolean>(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [compilationEngine, setCompilationEngine] = useState<string>("structured_layout_renderer");

  const [activeCenterTab, setActiveCenterTab] = useState<"suggestions" | "editor">("suggestions");
  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState<boolean>(true);
  const [isNewSessionModalOpen, setIsNewSessionModalOpen] = useState<boolean>(false);
  const [isSaveModalOpen, setIsSaveModalOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const showToast = (text: string, type: "success" | "error" = "success") => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  // 1. Fetch auxiliary jobs and resumes
  const fetchAuxiliaryData = useCallback(async () => {
    try {
      const [jobsData, resumesData, sessionsData] = await Promise.all([
        apiClient<JobListResponse>("/jobs?per_page=50"),
        apiClient<ResumeSummary[]>("/resumes"),
        tailoringApi.listSessions(0, 20).catch(() => []),
      ]);
      setJobs(jobsData.items || []);
      setResumes(resumesData || []);
      setPastSessions(sessionsData || []);
      return { jobs: jobsData.items || [], resumes: resumesData || [] };
    } catch (err) {
      console.error("Failed to load auxiliary data:", err);
      return { jobs: [], resumes: [] };
    }
  }, []);

  // 2. Load PDF Blob
  const loadPdfBlob = useCallback(async (sessionId: string) => {
    setIsCompilingPdf(true);
    try {
      const blob = await fetchBlob(`/tailoring/sessions/${sessionId}/pdf`);
      const url = URL.createObjectURL(blob);
      setPdfBlobUrl(url);
    } catch (err) {
      console.error("Failed to load PDF:", err);
      showToast("Could not load PDF document preview.", "error");
    } finally {
      setIsCompilingPdf(false);
    }
  }, []);

  // 3. Load or initialize session
  const loadSession = useCallback(
    async (sessionId: string) => {
      setIsLoadingSession(true);
      try {
        const sess = await tailoringApi.getSession(sessionId);
        setSession(sess);
        await loadPdfBlob(sessionId);
      } catch (err) {
        console.error("Failed to load session:", err);
        showToast("Tailoring session not found.", "error");
        setIsNewSessionModalOpen(true);
      } finally {
        setIsLoadingSession(false);
      }
    },
    [loadPdfBlob]
  );

  useEffect(() => {
    if (authLoading) return;

    const init = async () => {
      const { jobs: loadedJobs, resumes: loadedResumes } = await fetchAuxiliaryData();

      if (paramSessionId) {
        await loadSession(paramSessionId);
      } else if (paramJobId && loadedResumes.length > 0) {
        // Auto-create session if jobId provided and resume available
        try {
          setIsLoadingSession(true);
          const resumeId = paramResumeId || loadedResumes[0].id;
          const newSession = await tailoringApi.createSession({
            job_id: paramJobId,
            resume_id: resumeId,
          });
          setSession(newSession);
          router.replace(`/dashboard/resumes/tailor?sessionId=${newSession.id}`);
          await loadPdfBlob(newSession.id);
        } catch (err) {
          console.error("Failed to auto-create session:", err);
          setIsNewSessionModalOpen(true);
        } finally {
          setIsLoadingSession(false);
        }
      } else {
        setIsLoadingSession(false);
        setIsNewSessionModalOpen(true);
      }
    };

    init();
  }, [authLoading, paramSessionId, paramJobId, paramResumeId, fetchAuxiliaryData, loadSession, router, loadPdfBlob]);

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
      }
    };
  }, [pdfBlobUrl]);

  // Handle individual change approval / rejection / edit
  const handleUpdateChangeStatus = async (
    changeId: string,
    status: "pending" | "accepted" | "rejected" | "modified",
    userContent?: string
  ) => {
    if (!session) return;
    try {
      const updated = await tailoringApi.updateChangeStatus(session.id, changeId, {
        status,
        user_content: userContent,
      });
      setSession(updated);
      showToast(
        status === "accepted"
          ? "Modification approved and synced!"
          : status === "rejected"
          ? "Modification rejected."
          : "Custom edit saved and synced."
      );
    } catch (err) {
      console.error("Failed to update change status:", err);
      showToast("Failed to update modification status.", "error");
    }
  };

  // Handle batch actions
  const handleBatchAction = async (action: "accept_all" | "reject_all" | "restore_original") => {
    if (!session) return;
    try {
      const updated = await tailoringApi.batchUpdateChanges(session.id, action);
      setSession(updated);
      await loadPdfBlob(session.id);
      showToast(
        action === "accept_all"
          ? "Approved all suggestions and updated document!"
          : action === "reject_all"
          ? "Rejected suggestions."
          : "Restored original resume source."
      );
    } catch (err) {
      console.error("Failed batch action:", err);
      showToast("Failed to process batch action.", "error");
    }
  };

  // Handle direct Monaco LaTeX editor save
  const handleSaveEditorContent = async (latexContent: string) => {
    if (!session) return;
    setIsSavingContent(true);
    try {
      const updated = await tailoringApi.updateContent(session.id, latexContent);
      setSession(updated);
      await loadPdfBlob(session.id);
      showToast("LaTeX document saved and recompiled successfully!");
    } catch (err) {
      console.error("Failed to save content:", err);
      showToast("Failed to save LaTeX edits. Check sandbox restrictions.", "error");
    } finally {
      setIsSavingContent(false);
    }
  };

  // Handle Recompile
  const handleRecompile = async () => {
    if (!session) return;
    await loadPdfBlob(session.id);
    showToast("PDF document recompiled successfully.");
  };

  // Handle Downloads
  const handleDownloadPdf = async () => {
    if (!session) return;
    await tailoringApi.downloadPdf(session.id, `tailored_resume_${session.id.slice(0, 8)}.pdf`);
    showToast("PDF download started.");
  };

  const handleDownloadLatex = async () => {
    if (!session) return;
    await tailoringApi.downloadLatex(session.id, `tailored_resume_${session.id.slice(0, 8)}.tex`);
    showToast("LaTeX source download started.");
  };

  // Handle Saving Final Tailored Resume Version
  const handleSaveTailoredVersion = async (title: string) => {
    if (!session) return;
    try {
      const tailoredVer = await tailoringApi.saveTailoredVersion(session.id, {
        title,
        latex_content: session.latex_content || undefined,
      });
      // Refresh session state
      const updatedSession = await tailoringApi.getSession(session.id);
      setSession(updatedSession);
      showToast(`Tailored version v${tailoredVer.version_number} saved to your Resume Studio!`);
    } catch (err) {
      console.error("Failed to save tailored version:", err);
      showToast("Failed to save tailored version.", "error");
      throw err;
    }
  };

  // Handle starting a new session from modal
  const handleStartSession = async (jobId: string, resumeId: string) => {
    try {
      setIsLoadingSession(true);
      const newSession = await tailoringApi.createSession({
        job_id: jobId,
        resume_id: resumeId,
      });
      setSession(newSession);
      setIsNewSessionModalOpen(false);
      router.replace(`/dashboard/resumes/tailor?sessionId=${newSession.id}`);
      await loadPdfBlob(newSession.id);
      showToast("Tailoring session initialized with Zero-Fabrication analysis!");
    } catch (err) {
      console.error("Failed to create session:", err);
      showToast("Failed to initialize session.", "error");
    } finally {
      setIsLoadingSession(false);
    }
  };

  if (isLoadingSession && !session) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-300">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
        <h2 className="text-base font-semibold text-white">Loading Resume Tailoring Studio...</h2>
        <p className="text-xs text-slate-500 mt-1">Grounding requirements and initializing Monaco workspace</p>
      </div>
    );
  }

  const jobTitle = session?.job?.title || "Target Role";
  const compName = session?.job?.company?.name || session?.job?.company_name || "Company";
  const defaultVersionTitle = `Tailored for ${jobTitle} at ${compName}`;
  const isSavedVersion = session?.status === "saved";

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Navigation & Workspace Header */}
      <header className="h-14 border-b border-slate-800 bg-slate-900/90 px-4 flex items-center justify-between gap-4 shrink-0 z-10">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/resumes"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center gap-1 text-xs"
            title="Back to Resume Studio"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline font-medium">Studio</span>
          </Link>

          <div className="h-4 w-[1px] bg-slate-800" />

          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-950/80 text-indigo-400 border border-indigo-800/40">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-white leading-none">
                  Resume Tailoring Studio
                </h1>
                {isSavedVersion ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/50">
                    Saved Version
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/40">
                    Workspace Active
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 truncate max-w-md">
                {session ? `${jobTitle} @ ${compName} — Base: ${session.resume_title || "Resume"}` : "Select target job to begin"}
              </p>
            </div>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2">
          {session && (
            <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-400 px-2 py-1 rounded bg-slate-950 border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Zero-Fabrication Guard Active</span>
            </div>
          )}

          <button
            onClick={() => setIsNewSessionModalOpen(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Session</span>
          </button>

          <button
            onClick={() => setIsSaveModalOpen(true)}
            disabled={!session}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs rounded-lg font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm disabled:opacity-50"
          >
            <BookmarkCheck className="w-3.5 h-3.5" />
            <span>Save Version</span>
          </button>
        </div>
      </header>

      {/* Main 3-Panel Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* LEFT PANEL: Job & Grounded Alignment Analysis */}
        <aside
          className={`border-r border-slate-800 bg-slate-900/40 flex flex-col shrink-0 transition-all duration-200 ease-in-out ${
            isLeftPanelOpen ? "w-80 lg:w-96" : "w-0 overflow-hidden border-r-0"
          }`}
        >
          <div className="p-2.5 px-4 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-300 shrink-0">
            <span className="flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
              Target Requisition & Alignment
            </span>
            <button
              onClick={() => setIsLeftPanelOpen(false)}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
              title="Collapse panel"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <JobAlignmentPanel
              job={session?.job}
              analysis={session?.job_analysis}
            />
          </div>
        </aside>

        {/* Toggle button if left panel is collapsed */}
        {!isLeftPanelOpen && (
          <button
            onClick={() => setIsLeftPanelOpen(true)}
            className="absolute top-3 left-3 z-20 p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 shadow-md transition"
            title="Open requisition panel"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        {/* CENTER PANEL: Monaco Editor & Suggestion Review Tabs */}
        <section className="flex-1 flex flex-col min-w-[320px] border-r border-slate-800 bg-slate-950 overflow-hidden">
          {/* Tab Selector Header */}
          <div className="p-2 px-4 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveCenterTab("suggestions")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeCenterTab === "suggestions"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                AI Suggestion Review
                {session?.changes && session.changes.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-950/80 text-indigo-300 border border-indigo-700/60 ml-1">
                    {session.changes.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveCenterTab("editor")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeCenterTab === "editor"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                Monaco LaTeX Editor
              </button>
            </div>

            <div className="text-[11px] text-slate-500 hidden sm:flex items-center gap-2">
              <span>Engine: {session?.provider || "deterministic"}</span>
            </div>
          </div>

          {/* Active Tab View */}
          <div className="flex-1 overflow-hidden">
            {activeCenterTab === "suggestions" ? (
              <SuggestionReviewPanel
                changes={session?.changes || []}
                onUpdateStatus={handleUpdateChangeStatus}
                onBatchAction={handleBatchAction}
                isLoading={isLoadingSession}
              />
            ) : (
              <MonacoResumeEditor
                initialContent={session?.latex_content || ""}
                onSave={handleSaveEditorContent}
                isSaving={isSavingContent}
              />
            )}
          </div>
        </section>

        {/* RIGHT PANEL: Live PDF Preview & Export */}
        <section className="w-96 lg:w-[480px] xl:w-[540px] flex flex-col shrink-0 bg-slate-950 overflow-hidden">
          <PdfPreviewPanel
            sessionId={session?.id || ""}
            pdfBlobUrl={pdfBlobUrl}
            compilationEngine={compilationEngine}
            isCompiling={isCompilingPdf}
            onRecompile={handleRecompile}
            onDownloadPdf={handleDownloadPdf}
            onDownloadLatex={handleDownloadLatex}
            onOpenSaveModal={() => setIsSaveModalOpen(true)}
            isSavedVersion={isSavedVersion}
          />
        </section>
      </div>

      {/* Save Tailored Version Modal */}
      <SaveVersionModal
        isOpen={isSaveModalOpen}
        onClose={() => setIsSaveModalOpen(false)}
        onConfirm={handleSaveTailoredVersion}
        defaultTitle={defaultVersionTitle}
        jobTitle={jobTitle}
        companyName={compName}
        parentVersionNumber={session?.parent_version_number}
      />

      {/* New Session Initiation Modal */}
      <NewSessionModal
        isOpen={isNewSessionModalOpen}
        onClose={() => {
          if (session) setIsNewSessionModalOpen(false);
          else router.push("/dashboard/resumes");
        }}
        jobs={jobs}
        resumes={resumes}
        pastSessions={pastSessions}
        preselectedJobId={paramJobId}
        onStartSession={handleStartSession}
        onResumeSession={(sid) => {
          setIsNewSessionModalOpen(false);
          router.replace(`/dashboard/resumes/tailor?sessionId=${sid}`);
          loadSession(sid);
        }}
        isLoading={isLoadingSession}
      />

      {/* Toast Feedback Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-medium bg-slate-900 border border-slate-700 text-white animate-in fade-in slide-in-from-bottom-2">
          {toastMessage.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}
    </div>
  );
}

export default function TailoringStudioPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-xs">
          Loading Tailoring Studio...
        </div>
      }
    >
      <TailoringStudioContent />
    </Suspense>
  );
}

