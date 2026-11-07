"use client";

import React, { useCallback, useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  ExternalLink,
  FileCheck,
  FileText,
  HelpCircle,
  Layers,
  Loader2,
  Mail,
  Paperclip,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  User,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  ApplicationEmail,
  ApplicationPreparation,
  assistantApi,
  ChecklistItem,
  CoverLetter,
  GmailConnectionStatus,
  googleIntegrationsApi,
  Job,
  jobsApi,
  QAItem,
  ResumeSummary,
  resumesApi,
} from "@/lib/api";

export default function ApplicationAssistantPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-12 text-center text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
          <p className="text-sm">Loading AI Application Assistant...</p>
        </div>
      }
    >
      <ApplicationAssistantContent />
    </React.Suspense>
  );
}

function ApplicationAssistantContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: isAuthLoading } = useAuth();

  const queryJobId = searchParams.get("job_id");
  const queryAppId = searchParams.get("application_id");

  // State
  const [selectedJobId, setSelectedJobId] = useState<string>(queryJobId || "");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [availableJobs, setAvailableJobs] = useState<Job[]>([]);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [selectedResumeVersionId, setSelectedResumeVersionId] = useState<string>("");

  // Preparation Session
  const [preparation, setPreparation] = useState<ApplicationPreparation | null>(null);
  const [activeTab, setActiveTab] = useState<"checklist" | "cover_letter" | "email" | "qa">(
    "checklist"
  );
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Gmail OAuth State
  const [gmailStatus, setGmailStatus] = useState<GmailConnectionStatus | null>(null);
  const [isGmailConnecting, setIsGmailConnecting] = useState(false);

  // Cover Letter State
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
  const [selectedLetter, setSelectedLetter] = useState<CoverLetter | null>(null);
  const [clInstructions, setClInstructions] = useState("");
  const [isGeneratingCL, setIsGeneratingCL] = useState(false);
  const [clTitle, setClTitle] = useState("");
  const [clContent, setClContent] = useState("");

  // Recruiter Email State
  const [emails, setEmails] = useState<ApplicationEmail[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<ApplicationEmail | null>(null);
  const [emailType, setEmailType] = useState<string>("direct_application");
  const [emailRecipient, setEmailRecipient] = useState<string>("");
  const [emailRecipientName, setEmailRecipientName] = useState<string>("");
  const [emailSubject, setEmailSubject] = useState<string>("");
  const [emailBody, setEmailBody] = useState<string>("");
  const [includeResumeAttach, setIncludeResumeAttach] = useState<boolean>(true);
  const [includeCLAttach, setIncludeCLAttach] = useState<boolean>(false);
  const [isGeneratingEmail, setIsGeneratingEmail] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [showSendConfirmModal, setShowSendConfirmModal] = useState(false);

  // Application Q&A State
  const [qaItems, setQaItems] = useState<QAItem[]>([]);
  const [isGeneratingQA, setIsGeneratingQA] = useState(false);
  const [customQuestionInput, setCustomQuestionInput] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // External Portal Modal
  const [showPortalConfirmModal, setShowPortalConfirmModal] = useState(false);
  const [portalNotes, setPortalNotes] = useState("");

  // Auth Protection
  useEffect(() => {
    if (!isAuthLoading && !user) {
      router.push("/login");
    }
  }, [user, isAuthLoading, router]);

  // Load Gmail Connection Status
  const loadGmailStatus = useCallback(async () => {
    try {
      const status = await googleIntegrationsApi.getStatus();
      setGmailStatus(status);
    } catch {
      setGmailStatus({
        is_connected: false,
        email: null,
        scopes: [],
        connected_at: null,
        is_token_valid: false,
      });
    }
  }, []);

  // Load candidate resumes
  const loadResumes = useCallback(async () => {
    try {
      const res = await resumesApi.listResumes();
      setResumes(res);
      if (res.length > 0 && res[0].current_version_id) {
        setSelectedResumeVersionId(res[0].current_version_id);
      }
    } catch (err) {
      loggerError("Failed to load resumes", err);
    }
  }, []);

  // Load available jobs for selector
  const loadJobs = useCallback(async () => {
    try {
      const res = await jobsApi.listJobs({ page: 1, page_size: 50 });
      setAvailableJobs(res.items);
      if (!selectedJobId && res.items.length > 0) {
        setSelectedJobId(res.items[0].id);
        setSelectedJob(res.items[0]);
      } else if (selectedJobId) {
        const found = res.items.find((j: Job) => j.id === selectedJobId);
        if (found) setSelectedJob(found);
      }
    } catch (err) {
      loggerError("Failed to load jobs", err);
    }
  }, [selectedJobId]);

  // Load or Initialize Preparation
  const loadPreparation = useCallback(
    async (jobId: string) => {
      if (!jobId) return;
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const prep = await assistantApi.getOrCreatePreparation(
          jobId,
          queryAppId || undefined,
          selectedResumeVersionId || undefined
        );
        setPreparation(prep);
        if (prep.qa_answers && prep.qa_answers.length > 0) {
          setQaItems(prep.qa_answers);
        }

        // Load associated cover letters & emails
        const [cls, ems] = await Promise.all([
          assistantApi.listCoverLettersForJob(jobId),
          assistantApi.listEmailsForJob(jobId),
        ]);
        setCoverLetters(cls);
        if (cls.length > 0) {
          setSelectedLetter(cls[0]);
          setClTitle(cls[0].title);
          setClContent(cls[0].content);
        } else {
          setSelectedLetter(null);
          setClTitle("");
          setClContent("");
        }

        setEmails(ems);
        if (ems.length > 0) {
          setSelectedEmail(ems[0]);
          setEmailRecipient(ems[0].recipient_email || "");
          setEmailRecipientName(ems[0].recipient_name || "");
          setEmailSubject(ems[0].subject);
          setEmailBody(ems[0].body);
          setIncludeResumeAttach(ems[0].include_resume_attachment);
          setIncludeCLAttach(ems[0].include_cover_letter_attachment);
        } else {
          setSelectedEmail(null);
          setEmailRecipient("");
          setEmailRecipientName("");
          setEmailSubject("");
          setEmailBody("");
        }
      } catch (err: unknown) {
        const e = err as { message?: string };
        setErrorMsg(e.message || "Failed to load application preparation session");
      } finally {
        setIsLoading(false);
      }
    },
    [queryAppId, selectedResumeVersionId]
  );

  useEffect(() => {
    loadGmailStatus();
    loadResumes();
    loadJobs();
  }, [loadGmailStatus, loadResumes, loadJobs]);

  useEffect(() => {
    if (selectedJobId) {
      loadPreparation(selectedJobId);
    }
  }, [selectedJobId, loadPreparation]);

  // Handle URL query feedback (e.g. from Google OAuth callback)
  useEffect(() => {
    if (searchParams.get("connected") === "true") {
      setSuccessMsg("Google Gmail account connected successfully!");
      loadGmailStatus();
    } else if (searchParams.get("error")) {
      setErrorMsg(`Gmail connection failed: ${searchParams.get("error")}`);
    }
  }, [searchParams, loadGmailStatus]);

  function loggerError(msg: string, err: unknown) {
    console.error(msg, err);
  }

  // Checklist Item Toggle
  const handleToggleChecklist = async (item: ChecklistItem) => {
    if (!preparation) return;
    try {
      const updated = await assistantApi.updateChecklistItem(
        preparation.id,
        item.id,
        !item.completed
      );
      setPreparation(updated);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to update checklist item");
    }
  };

  // Google OAuth Connect
  const handleConnectGmail = async () => {
    try {
      setIsGmailConnecting(true);
      setErrorMsg(null);
      const res = await googleIntegrationsApi.getAuthUrl();
      // Redirect to Google's official authorization page
      window.location.href = res.authorization_url;
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to initiate Google OAuth");
      setIsGmailConnecting(false);
    }
  };

  // Google OAuth Disconnect
  const handleDisconnectGmail = async () => {
    if (!confirm("Are you sure you want to disconnect your Gmail account?")) return;
    try {
      await googleIntegrationsApi.disconnect();
      setGmailStatus({
        is_connected: false,
        email: null,
        scopes: [],
        connected_at: null,
        is_token_valid: false,
      });
      setSuccessMsg("Gmail account disconnected successfully");
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to disconnect Gmail account");
    }
  };

  // Cover Letter Generate
  const handleGenerateCoverLetter = async () => {
    if (!selectedJobId) return;
    try {
      setIsGeneratingCL(true);
      setErrorMsg(null);
      const letter = await assistantApi.generateCoverLetter({
        job_id: selectedJobId,
        preparation_id: preparation?.id,
        resume_version_id: selectedResumeVersionId || undefined,
        user_instructions: clInstructions.trim() || undefined,
      });
      setSelectedLetter(letter);
      setClTitle(letter.title);
      setClContent(letter.content);
      setCoverLetters((prev) => [letter, ...prev]);
      setSuccessMsg("Cover letter generated from verified resume evidence!");
      if (preparation) {
        const updated = await assistantApi.getPreparation(preparation.id);
        setPreparation(updated);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to generate cover letter");
    } finally {
      setIsGeneratingCL(false);
    }
  };

  // Cover Letter Save
  const handleSaveCoverLetter = async () => {
    if (!selectedLetter) return;
    try {
      const updated = await assistantApi.updateCoverLetter(selectedLetter.id, {
        title: clTitle,
        content: clContent,
      });
      setSelectedLetter(updated);
      setCoverLetters((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setSuccessMsg("Cover letter changes saved successfully");
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to save cover letter");
    }
  };

  // Cover Letter Approve
  const handleApproveCoverLetter = async () => {
    if (!selectedLetter) return;
    try {
      const updated = await assistantApi.updateCoverLetter(selectedLetter.id, {
        is_approved: true,
      });
      setSelectedLetter(updated);
      setCoverLetters((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setSuccessMsg("Cover letter approved for application submission!");
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to approve cover letter");
    }
  };

  // Recruiter Email Generate
  const handleGenerateEmail = async () => {
    if (!selectedJobId) return;
    try {
      setIsGeneratingEmail(true);
      setErrorMsg(null);
      const emailRec = await assistantApi.generateEmail({
        job_id: selectedJobId,
        preparation_id: preparation?.id,
        resume_version_id: selectedResumeVersionId || undefined,
        cover_letter_id: selectedLetter?.id || undefined,
        email_type: emailType,
        recipient_email: emailRecipient.trim() || undefined,
        recipient_name: emailRecipientName.trim() || undefined,
      });
      setSelectedEmail(emailRec);
      setEmailRecipient(emailRec.recipient_email || "");
      setEmailRecipientName(emailRec.recipient_name || "");
      setEmailSubject(emailRec.subject);
      setEmailBody(emailRec.body);
      setEmails((prev) => [emailRec, ...prev]);
      setSuccessMsg(`Drafted ${emailType.replace("_", " ")} email!`);
      if (preparation) {
        const updated = await assistantApi.getPreparation(preparation.id);
        setPreparation(updated);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to generate recruiter email");
    } finally {
      setIsGeneratingEmail(false);
    }
  };

  // Recruiter Email Save
  const handleSaveEmail = async () => {
    if (!selectedEmail) return;
    try {
      const updated = await assistantApi.updateEmail(selectedEmail.id, {
        recipient_email: emailRecipient.trim() || undefined,
        recipient_name: emailRecipientName.trim() || undefined,
        subject: emailSubject,
        body: emailBody,
        include_resume_attachment: includeResumeAttach,
        resume_version_id: selectedResumeVersionId || undefined,
        include_cover_letter_attachment: includeCLAttach,
        cover_letter_id: selectedLetter?.id || undefined,
      });
      setSelectedEmail(updated);
      setEmails((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setSuccessMsg("Email updated successfully");
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to update email");
    }
  };

  // Create Gmail Draft
  const handleCreateGmailDraft = async () => {
    if (!selectedEmail) return;
    if (!emailRecipient.trim()) {
      setErrorMsg("Please specify a valid recipient email before creating a Gmail draft.");
      return;
    }
    try {
      await handleSaveEmail();
      const updated = await assistantApi.createGmailDraft(selectedEmail.id);
      setSelectedEmail(updated);
      setEmails((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setSuccessMsg("Draft created in your connected Gmail account!");
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to create Gmail draft");
    }
  };

  // Send Email with Explicit Confirmation
  const handleConfirmSendEmail = async () => {
    if (!selectedEmail) return;
    try {
      setIsSendingEmail(true);
      setErrorMsg(null);
      await handleSaveEmail();
      const updated = await assistantApi.sendEmail(selectedEmail.id, true);
      setSelectedEmail(updated);
      setEmails((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setShowSendConfirmModal(false);
      setSuccessMsg(`Email successfully dispatched via Gmail (Message ID: ${updated.gmail_message_id})!`);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to send email");
    } finally {
      setIsSendingEmail(false);
    }
  };

  // Generate Application Q&A
  const handleGenerateQA = async () => {
    if (!selectedJobId) return;
    try {
      setIsGeneratingQA(true);
      setErrorMsg(null);
      const res = await assistantApi.generateQA({
        job_id: selectedJobId,
        preparation_id: preparation?.id,
        resume_version_id: selectedResumeVersionId || undefined,
        custom_questions: customQuestionInput.trim()
          ? [customQuestionInput.trim()]
          : undefined,
      });
      setQaItems(res.items);
      setCustomQuestionInput("");
      setSuccessMsg("Generated answers grounded in your verified resume!");
      if (preparation) {
        const updated = await assistantApi.getPreparation(preparation.id);
        setPreparation(updated);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to generate Q&A");
    } finally {
      setIsGeneratingQA(false);
    }
  };

  // Launch External Portal
  const handleOpenPortal = async () => {
    if (!selectedJob?.job_url && !selectedJob?.application_url) {
      setErrorMsg("No external application URL available for this listing.");
      return;
    }
    const targetUrl = selectedJob.application_url || selectedJob.job_url;
    window.open(targetUrl, "_blank", "noopener,noreferrer");

    if (preparation) {
      try {
        const updated = await assistantApi.recordPortalOpened(preparation.id);
        setPreparation(updated);
      } catch (err) {
        console.warn("Could not record portal opened timestamp", err);
      }
    }
  };

  // Confirm External Submission
  const handleConfirmSubmission = async () => {
    if (!selectedJobId) return;
    try {
      const updated = await assistantApi.confirmPortalSubmission({
        job_id: selectedJobId,
        preparation_id: preparation?.id,
        application_id: queryAppId || undefined,
        notes: portalNotes.trim() || undefined,
      });
      setPreparation(updated);
      setShowPortalConfirmModal(false);
      setSuccessMsg("Application submission recorded! Application status updated to Applied.");
    } catch (err: unknown) {
      const e = err as { message?: string };
      setErrorMsg(e.message || "Failed to confirm submission");
    }
  };

  // Copy QA answer
  const handleCopyAnswer = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return {
          label: "Completed",
          classes: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
          icon: CheckCircle2,
        };
      case "ready_for_review":
        return {
          label: "Ready for Review",
          classes: "bg-blue-500/10 text-blue-400 border-blue-500/30",
          icon: ShieldCheck,
        };
      case "in_progress":
        return {
          label: "In Progress",
          classes: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          icon: Clock,
        };
      default:
        return {
          label: "Not Started",
          classes: "bg-slate-700/40 text-slate-400 border-slate-600/30",
          icon: AlertCircle,
        };
    }
  };

  const statusInfo = getStatusBadge(preparation?.checklist_status || "not_started");
  const StatusIcon = statusInfo.icon;

  const completedChecklistCount =
    preparation?.checklist_items.filter((i) => i.completed).length || 0;
  const totalChecklistCount = preparation?.checklist_items.length || 0;
  const checklistPercent =
    totalChecklistCount > 0
      ? Math.round((completedChecklistCount / totalChecklistCount) * 100)
      : 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
              </Link>
              <span className="text-slate-600">/</span>
              <Link
                href="/dashboard/applications"
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                Applications
              </Link>
              <span className="text-slate-600">/</span>
              <span className="text-xs text-indigo-400 font-medium">AI Application Assistant</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <Sparkles className="w-7 h-7 text-indigo-400" />
              Application Assistant & Gmail Integration
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Prepare tailored resumes, grounded cover letters, personalized outreach emails, and
              portal answers with zero fabrication.
            </p>
          </div>

          {/* Connected Gmail Pill */}
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/90 shadow-sm flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
                <Mail className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <div className="text-slate-400 font-medium">Google Gmail</div>
                {gmailStatus?.is_connected ? (
                  <div className="flex items-center gap-1.5 text-emerald-400 font-semibold truncate max-w-[170px]">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    {gmailStatus.email}
                  </div>
                ) : (
                  <span className="text-slate-500">Not connected</span>
                )}
              </div>
              {gmailStatus?.is_connected ? (
                <button
                  onClick={handleDisconnectGmail}
                  className="px-2.5 py-1 text-xs rounded-md border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                  title="Disconnect Gmail Account"
                >
                  Disconnect
                </button>
              ) : (
                <button
                  onClick={handleConnectGmail}
                  disabled={isGmailConnecting}
                  className="px-2.5 py-1 text-xs font-medium rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Connect
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Global Alerts */}
        {errorMsg && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 flex items-start justify-between gap-3 text-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-200">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {successMsg && (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 flex items-start justify-between gap-3 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Selected Job Banner & Controls */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400 font-medium">Active Opportunity:</span>
              <select
                value={selectedJobId}
                onChange={(e) => {
                  setSelectedJobId(e.target.value);
                  const found = availableJobs.find((j) => j.id === e.target.value);
                  if (found) setSelectedJob(found);
                }}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {availableJobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title} – {j.company?.name || "Company"} ({j.work_arrangement})
                  </option>
                ))}
              </select>

              <span className={`px-2 py-0.5 rounded-full border text-xs font-semibold flex items-center gap-1 ${statusInfo.classes}`}>
                <StatusIcon className="w-3 h-3" /> {statusInfo.label}
              </span>
            </div>

            {selectedJob && (
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-indigo-400" />
                  {selectedJob.title}
                </h2>
                <span className="text-slate-400 text-sm flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5 text-slate-500" />
                  {selectedJob.company?.name || "Company"}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {selectedJob.work_arrangement}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {selectedJob.seniority_level || "Early Career"}
                </span>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Resume Selector */}
            <div className="flex items-center gap-1.5 text-xs bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <FileText className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-400">Resume:</span>
              <select
                value={selectedResumeVersionId}
                onChange={(e) => setSelectedResumeVersionId(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
              >
                {resumes.map((r) => (
                  <option key={r.id} value={r.current_version_id || ""}>
                    {r.title} (v{r.current_version_number || 1})
                  </option>
                ))}
              </select>
            </div>

            {/* Quick Tailoring Shortcut */}
            {selectedJobId && (
              <Link
                href={`/dashboard/resumes/tailor?job_id=${selectedJobId}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 transition-colors"
              >
                <Layers className="w-3.5 h-3.5" /> Tailor in Studio
              </Link>
            )}

            {/* Official Portal Link */}
            {selectedJob && (
              <button
                onClick={handleOpenPortal}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                title="Open Official Job Application Link"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Career Portal
              </button>
            )}
          </div>
        </div>

        {/* Workspace Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-1">
          <button
            onClick={() => setActiveTab("checklist")}
            className={`px-4 py-2.5 text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "checklist"
                ? "bg-slate-800 text-indigo-400 border-b-2 border-indigo-500"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <FileCheck className="w-4 h-4" /> Preparation Checklist
            <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-slate-700 text-slate-300">
              {completedChecklistCount}/{totalChecklistCount}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("cover_letter")}
            className={`px-4 py-2.5 text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "cover_letter"
                ? "bg-slate-800 text-indigo-400 border-b-2 border-indigo-500"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <FileText className="w-4 h-4" /> AI Cover Letter
            {coverLetters.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-slate-700 text-slate-300">
                {coverLetters.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("email")}
            className={`px-4 py-2.5 text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "email"
                ? "bg-slate-800 text-indigo-400 border-b-2 border-indigo-500"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Mail className="w-4 h-4" /> Recruiter Outreach & Gmail
            {emails.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-slate-700 text-slate-300">
                {emails.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("qa")}
            className={`px-4 py-2.5 text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "qa"
                ? "bg-slate-800 text-indigo-400 border-b-2 border-indigo-500"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <HelpCircle className="w-4 h-4" /> Application Q&A
            {qaItems.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-slate-700 text-slate-300">
                {qaItems.length}
              </span>
            )}
          </button>
        </div>

        {/* Tab 1: Preparation Checklist */}
        {activeTab === "checklist" && (
          <div className="space-y-6">
            {/* Progress Meter */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold text-white">Application Readiness</span>
                <span className="font-mono text-indigo-400 font-bold">{checklistPercent}% Complete</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-indigo-500 h-2.5 rounded-full transition-all duration-500"
                  style={{ width: `${checklistPercent}%` }}
                />
              </div>
              <p className="text-xs text-slate-400">
                Complete the milestones below to ensure your resume, cover letter, and application materials
                are aligned and verified before external submission.
              </p>
            </div>

            {/* Checklist Items */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-4">
              <h3 className="text-base font-semibold text-white">Milestones & Tasks</h3>
              <div className="divide-y divide-slate-800">
                {preparation?.checklist_items.map((item) => (
                  <div key={item.id} className="py-3.5 flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={item.completed}
                        onChange={() => handleToggleChecklist(item)}
                        className="mt-1 w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-800 cursor-pointer"
                      />
                      <div>
                        <div className={`text-sm font-medium ${item.completed ? "text-slate-400 line-through" : "text-slate-200"}`}>
                          {item.label}
                        </div>
                        {item.required && (
                          <span className="text-[10px] uppercase tracking-wider font-semibold text-indigo-400/90">
                            Required
                          </span>
                        )}
                        {item.notes && <p className="text-xs text-slate-400 mt-0.5">{item.notes}</p>}
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-2">
                      {item.id === "tailor_resume" && selectedJobId && (
                        <Link
                          href={`/dashboard/resumes/tailor?job_id=${selectedJobId}`}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          Open Tailoring Studio &rarr;
                        </Link>
                      )}
                      {item.id === "generate_cover_letter" && (
                        <button
                          onClick={() => setActiveTab("cover_letter")}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          Generate &rarr;
                        </button>
                      )}
                      {item.id === "prepare_recruiter_email" && (
                        <button
                          onClick={() => setActiveTab("email")}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          Draft Email &rarr;
                        </button>
                      )}
                      {item.id === "open_official_portal" && (
                        <button
                          onClick={handleOpenPortal}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                        >
                          <ExternalLink className="w-3 h-3" /> Launch Portal
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* External Portal Submission Confirmation Box */}
            <div className="p-6 rounded-2xl border border-indigo-500/20 bg-indigo-500/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Have you submitted on the official career portal?
                </h4>
                <p className="text-xs text-slate-400 max-w-xl">
                  Nexora never automatically submits your application or bypasses security gates.
                  Once you finish submitting on the employer’s site, confirm it here to track your progress.
                </p>
              </div>

              <button
                onClick={() => setShowPortalConfirmModal(true)}
                disabled={preparation?.checklist_status === "completed"}
                className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors shadow-sm shrink-0 flex items-center gap-1.5 ${
                  preparation?.checklist_status === "completed"
                    ? "bg-emerald-600/30 text-emerald-300 cursor-default"
                    : "bg-emerald-600 hover:bg-emerald-500 text-white"
                }`}
              >
                <Check className="w-4 h-4" />
                {preparation?.checklist_status === "completed" ? "Submission Confirmed" : "Confirm Submitted"}
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: AI Cover Letter */}
        {activeTab === "cover_letter" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Generation Controls */}
            <div className="lg:col-span-5 space-y-4">
              <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  Cover Letter Generator
                </h3>
                <p className="text-xs text-slate-400">
                  Synthesizes your analyzed resume evidence and the target job description into an authentic,
                  job-specific cover letter. Zero fabrication guaranteed.
                </p>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Special Instructions (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={clInstructions}
                    onChange={(e) => setClInstructions(e.target.value)}
                    placeholder="e.g. Highlight my distributed systems coursework and Docker project..."
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <button
                  onClick={handleGenerateCoverLetter}
                  disabled={isGeneratingCL}
                  className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800/50 text-white font-medium text-xs transition-colors shadow-sm flex items-center justify-center gap-2"
                >
                  {isGeneratingCL ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Grounding Evidence...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" /> Generate Cover Letter
                    </>
                  )}
                </button>
              </div>

              {/* Version History List */}
              {coverLetters.length > 0 && (
                <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Saved Revisions ({coverLetters.length})
                  </h4>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {coverLetters.map((l) => (
                      <button
                        key={l.id}
                        onClick={() => {
                          setSelectedLetter(l);
                          setClTitle(l.title);
                          setClContent(l.content);
                        }}
                        className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                          selectedLetter?.id === l.id
                            ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold"
                            : "bg-slate-800/40 text-slate-300 hover:bg-slate-800"
                        }`}
                      >
                        <span className="truncate">{l.title}</span>
                        {l.is_approved && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                            Approved
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Editor & Preview */}
            <div className="lg:col-span-7 space-y-4">
              {selectedLetter ? (
                <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                    <input
                      type="text"
                      value={clTitle}
                      onChange={(e) => setClTitle(e.target.value)}
                      className="bg-transparent text-base font-bold text-white border-b border-transparent hover:border-slate-700 focus:border-indigo-500 focus:outline-none px-1 py-0.5"
                    />

                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleSaveCoverLetter}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={handleApproveCoverLetter}
                        disabled={selectedLetter.is_approved}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1 ${
                          selectedLetter.is_approved
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            : "bg-indigo-600 hover:bg-indigo-500 text-white"
                        }`}
                      >
                        <Check className="w-3 h-3" />
                        {selectedLetter.is_approved ? "Approved" : "Approve"}
                      </button>
                      <a
                        href={`/api/v1/application-assistant/cover-letters/${selectedLetter.id}/pdf`}
                        download
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1"
                        title="Download Clean A4 PDF"
                      >
                        <Download className="w-3 h-3" /> PDF
                      </a>
                    </div>
                  </div>

                  {/* Grounded Evidence Badges */}
                  {selectedLetter.skill_alignment && selectedLetter.skill_alignment.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="text-slate-400">Evidenced Skills:</span>
                      {selectedLetter.skill_alignment.slice(0, 6).map((s, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 text-[11px]">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Content Editor */}
                  <textarea
                    rows={16}
                    value={clContent}
                    onChange={(e) => setClContent(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-4 text-xs font-sans text-slate-200 leading-relaxed focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              ) : (
                <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/20 text-center space-y-3">
                  <FileText className="w-8 h-8 text-slate-600 mx-auto" />
                  <h3 className="text-sm font-semibold text-slate-300">No Cover Letter Generated Yet</h3>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Click &quot;Generate Cover Letter&quot; to synthesize a tailored, grounded cover letter using your verified resume.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Recruiter Outreach & Gmail Workflow */}
        {activeTab === "email" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Email Configuration */}
            <div className="lg:col-span-5 space-y-4">
              <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Mail className="w-4 h-4 text-indigo-400" />
                  Email Type & Context
                </h3>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Communication Purpose</label>
                  <select
                    value={emailType}
                    onChange={(e) => setEmailType(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="direct_application">Direct Application Email</option>
                    <option value="recruiter_outreach">Recruiter Cold Outreach</option>
                    <option value="referral_request">Employee Referral Request</option>
                    <option value="follow_up">Application Follow-up</option>
                    <option value="interview_follow_up">Post-Interview Follow-up</option>
                    <option value="thank_you">Interview Thank You Note</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Recipient Verified Email <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="email"
                    value={emailRecipient}
                    onChange={(e) => setEmailRecipient(e.target.value)}
                    placeholder="recruiter@company.com"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Nexora never guesses or infers email addresses. Enter verified contact details.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Recipient Name (Optional)</label>
                  <input
                    type="text"
                    value={emailRecipientName}
                    onChange={(e) => setEmailRecipientName(e.target.value)}
                    placeholder="e.g. Alex Morgan"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                {/* Attachments Selector */}
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <span className="text-xs font-semibold text-slate-300 block">PDF Attachments</span>
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeResumeAttach}
                      onChange={(e) => setIncludeResumeAttach(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                    />
                    <Paperclip className="w-3.5 h-3.5 text-indigo-400" />
                    Attach Active Resume PDF (v{resumes[0]?.current_version_number || 1})
                  </label>
                  {selectedLetter && (
                    <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={includeCLAttach}
                        onChange={(e) => setIncludeCLAttach(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
                      />
                      <Paperclip className="w-3.5 h-3.5 text-indigo-400" />
                      Attach Approved Cover Letter PDF
                    </label>
                  )}
                </div>

                <button
                  onClick={handleGenerateEmail}
                  disabled={isGeneratingEmail}
                  className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800/50 text-white font-medium text-xs transition-colors shadow-sm flex items-center justify-center gap-2"
                >
                  {isGeneratingEmail ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Drafting Email...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" /> Draft Personalized Email
                    </>
                  )}
                </button>
              </div>

              {/* Saved Emails List */}
              {emails.length > 0 && (
                <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Drafted Communications ({emails.length})
                  </h4>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {emails.map((e) => (
                      <button
                        key={e.id}
                        onClick={() => {
                          setSelectedEmail(e);
                          setEmailRecipient(e.recipient_email || "");
                          setEmailRecipientName(e.recipient_name || "");
                          setEmailSubject(e.subject);
                          setEmailBody(e.body);
                          setIncludeResumeAttach(e.include_resume_attachment);
                          setIncludeCLAttach(e.include_cover_letter_attachment);
                        }}
                        className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                          selectedEmail?.id === e.id
                            ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold"
                            : "bg-slate-800/40 text-slate-300 hover:bg-slate-800"
                        }`}
                      >
                        <span className="truncate">{e.subject}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                            e.status === "sent"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : e.status === "approved"
                              ? "bg-blue-500/20 text-blue-400"
                              : "bg-slate-700 text-slate-400"
                          }`}
                        >
                          {e.status}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Email Content & Dispatch */}
            <div className="lg:col-span-7 space-y-4">
              {selectedEmail ? (
                <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-4">
                  <div className="space-y-3 border-b border-slate-800 pb-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Email Review & Dispatch
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSaveEmail}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                        >
                          Save Changes
                        </button>
                        {gmailStatus?.is_connected ? (
                          <>
                            <button
                              onClick={handleCreateGmailDraft}
                              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1"
                              title="Create draft in connected Gmail"
                            >
                              <Mail className="w-3.5 h-3.5 text-red-400" /> Create Gmail Draft
                            </button>
                            <button
                              onClick={() => setShowSendConfirmModal(true)}
                              disabled={selectedEmail.status === "sent"}
                              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
                                selectedEmail.status === "sent"
                                  ? "bg-emerald-500/20 text-emerald-400 cursor-default"
                                  : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
                              }`}
                            >
                              <Send className="w-3.5 h-3.5" />
                              {selectedEmail.status === "sent" ? "Dispatched" : "Send Email"}
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={handleConnectGmail}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1"
                          >
                            Connect Gmail to Send
                          </button>
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400">Subject</label>
                      <input
                        type="text"
                        value={emailSubject}
                        onChange={(e) => setEmailSubject(e.target.value)}
                        className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-semibold text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  </div>

                  {/* Body Editor */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">Body</label>
                    <textarea
                      rows={12}
                      value={emailBody}
                      onChange={(e) => setEmailBody(e.target.value)}
                      className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-4 text-xs font-sans text-slate-200 leading-relaxed focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  {/* Attachment Overview */}
                  <div className="flex flex-wrap items-center gap-2 pt-2 text-xs text-slate-400">
                    <span className="font-medium">Attached to Dispatch:</span>
                    {includeResumeAttach && (
                      <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 flex items-center gap-1 border border-slate-700">
                        <Paperclip className="w-3 h-3 text-indigo-400" /> Resume PDF
                      </span>
                    )}
                    {includeCLAttach && selectedLetter && (
                      <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 flex items-center gap-1 border border-slate-700">
                        <Paperclip className="w-3 h-3 text-indigo-400" /> Cover Letter PDF
                      </span>
                    )}
                    {!includeResumeAttach && !includeCLAttach && (
                      <span className="text-slate-500 italic">No attachments selected</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/20 text-center space-y-3">
                  <Mail className="w-8 h-8 text-slate-600 mx-auto" />
                  <h3 className="text-sm font-semibold text-slate-300">No Email Draft Selected</h3>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Select a communication type on the left and click &quot;Draft Personalized Email&quot; to begin.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Application Q&A */}
        {activeTab === "qa" && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <HelpCircle className="w-5 h-5 text-indigo-400" />
                    Truthful Application Question Answering
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-2xl">
                    Answers common portal screening questions using verified evidence from your resume.
                    Missing qualifications or candidate-specific details are explicitly flagged for your input.
                  </p>
                </div>

                <button
                  onClick={handleGenerateQA}
                  disabled={isGeneratingQA}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800/50 text-white font-medium text-xs transition-colors shadow-sm flex items-center gap-2 shrink-0"
                >
                  {isGeneratingQA ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Grounding Answers...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" /> Generate Truthful Answers
                    </>
                  )}
                </button>
              </div>

              {/* Add Custom Question Field */}
              <div className="pt-3 border-t border-slate-800 flex items-center gap-2">
                <input
                  type="text"
                  value={customQuestionInput}
                  onChange={(e) => setCustomQuestionInput(e.target.value)}
                  placeholder="Ask a custom portal question (e.g. 'Describe a challenging bug you debugged')..."
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <button
                  onClick={handleGenerateQA}
                  disabled={!customQuestionInput.trim() || isGeneratingQA}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
                >
                  Answer Custom
                </button>
              </div>
            </div>

            {/* QA Items Display */}
            {qaItems.length > 0 ? (
              <div className="space-y-4">
                {qaItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-3 relative group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        {item.question}
                      </h4>

                      <button
                        onClick={() => handleCopyAnswer(item.answer, idx)}
                        className="px-2.5 py-1 text-xs rounded-md border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors flex items-center gap-1 shrink-0"
                        title="Copy answer to clipboard"
                      >
                        {copiedIndex === idx ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-400" /> Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" /> Copy
                          </>
                        )}
                      </button>
                    </div>

                    <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
                      {item.answer}
                    </p>

                    {/* Missing Info Warning */}
                    {item.missing_info && (
                      <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <strong className="font-semibold block">Missing Candidate Information:</strong>
                          <span>{item.missing_info}</span>
                        </div>
                      </div>
                    )}

                    {/* Grounded Evidence Pills */}
                    {item.grounded_evidence && item.grounded_evidence.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 text-xs pt-1">
                        <span className="text-slate-500 text-[11px]">Grounded in:</span>
                        {item.grounded_evidence.map((ev, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded-full bg-slate-800 text-indigo-300 text-[11px] border border-slate-700"
                          >
                            {ev}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-12 rounded-2xl border border-slate-800 bg-slate-900/20 text-center space-y-3">
                <HelpCircle className="w-8 h-8 text-slate-600 mx-auto" />
                <h3 className="text-sm font-semibold text-slate-300">No Questions Answered Yet</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Click &quot;Generate Truthful Answers&quot; to formulate grounded answers to standard screening questions.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Explicit Send Email Confirmation Modal */}
      {showSendConfirmModal && selectedEmail && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-indigo-400" />
                Confirm Email Dispatch
              </h3>
              <button
                onClick={() => setShowSendConfirmModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-300">
              <p className="text-slate-400">
                You are about to send this email through your connected Google Gmail account:
              </p>

              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 font-mono">
                <div>
                  <span className="text-slate-500">From: </span>
                  <span className="text-slate-200">{gmailStatus?.email}</span>
                </div>
                <div>
                  <span className="text-slate-500">To: </span>
                  <span className="text-indigo-400 font-semibold">{emailRecipient}</span>
                </div>
                <div>
                  <span className="text-slate-500">Subject: </span>
                  <span className="text-slate-200">{emailSubject}</span>
                </div>
                <div>
                  <span className="text-slate-500">Attachments: </span>
                  <span className="text-slate-200">
                    {[
                      includeResumeAttach ? "Resume.pdf" : null,
                      includeCLAttach && selectedLetter ? "Cover_Letter.pdf" : null,
                    ]
                      .filter(Boolean)
                      .join(", ") || "None"}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold block">Irreversible Action:</strong>
                  <span>
                    This message will be dispatched immediately via Google&apos;s official Gmail API.
                    Nexora prevents duplicate sends, but sent messages cannot be un-sent.
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowSendConfirmModal(false)}
                className="px-4 py-2 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSendEmail}
                disabled={isSendingEmail}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-colors flex items-center gap-1.5"
              >
                {isSendingEmail ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Dispatching...
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" /> Yes, Send Email
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* External Portal Submission Modal */}
      {showPortalConfirmModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Confirm Application Submission
              </h3>
              <button
                onClick={() => setShowPortalConfirmModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Confirming submission marks your application preparation as completed and updates
              your application tracker to <strong>Applied</strong>.
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Optional Notes / Confirmation Number
              </label>
              <textarea
                rows={3}
                value={portalNotes}
                onChange={(e) => setPortalNotes(e.target.value)}
                placeholder="e.g. Application ID #REQ-88219 submitted via Greenhouse..."
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowPortalConfirmModal(false)}
                className="px-4 py-2 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSubmission}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" /> Confirm Submission
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
