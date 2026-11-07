"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  Bell,
  BookOpen,
  Bot,
  Brain,
  Briefcase,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  Clock,
  Code,
  Compass,
  CornerDownRight,
  ExternalLink,
  FileCode,
  FileText,
  Filter,
  GraduationCap,
  HelpCircle,
  History,
  Layers,
  Lightbulb,
  ListChecks,
  Loader2,
  MessageSquare,
  Pin,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  Sparkles,
  Target,
  Terminal,
  Trash2,
  User,
  Zap,
} from "lucide-react";

import { NotificationBell } from "@/components/NotificationBell";
import { useAuth } from "@/context/auth-context";
import {
  applicationsApi,
  InterviewAnalyticsResponse,
  InterviewAnswerDetail,
  InterviewEvaluationDetail,
  InterviewNoteResponse,
  interviewPrepApi,
  InterviewQuestionDetail,
  InterviewSessionDetail,
  InterviewSessionSummary,
  Job,
  JobApplicationSummary,
  jobsApi,
  ProjectBreakdownResponse,
  resumesApi,
  ResumeSummary,
} from "@/lib/api";

const CATEGORIES = [
  {
    id: "technical",
    label: "General CS & Core Tech",
    description: "Memory models, async execution, connection pools, debugging",
  },
  {
    id: "coding_problem_solving",
    label: "Coding & DSA",
    description: "Hash maps, two-pointer, interval merging, LRU cache logic",
  },
  {
    id: "backend_python",
    label: "Backend & Python",
    description: "FastAPI, GIL, async/def, SQLAlchemy 2.0, Celery tuning",
  },
  {
    id: "frontend_fullstack",
    label: "Frontend & Full-Stack",
    description: "React Virtual DOM, Next.js, Web Vitals, server caching",
  },
  {
    id: "ai_ml_genai",
    label: "AI / ML & GenAI",
    description: "RAG vs fine-tuning, prompt defense, vector search (HNSW)",
  },
  {
    id: "database_sql",
    label: "Database & SQL",
    description: "Joins, B-Tree vs Hash indexes, N+1 query solving, MVCC",
  },
  {
    id: "system_design",
    label: "System Design",
    description: "Horizontal scaling, delayed notifications, search indexing",
  },
  {
    id: "project_deep_dive",
    label: "Resume Project Deep-Dive",
    description: "Architectural choices, production bottlenecks, trade-offs",
  },
  {
    id: "internship_experience",
    label: "Internship & Teamwork",
    description: "PR reviews, deployment safety, stakeholder communication",
  },
  {
    id: "behavioral_hr",
    label: "Behavioral & STAR",
    description: "Conflict resolution, difficult bug post-mortems, priorities",
  },
];

const DIFFICULTIES = [
  { id: "beginner", label: "Beginner", desc: "Core syntax, foundations, basic queries" },
  { id: "intermediate", label: "Intermediate", desc: "Concurrency, error handling, trade-offs" },
  { id: "advanced", label: "Advanced", desc: "Distributed scale, caching, race conditions" },
];

const ROUNDS = [
  { id: "screening", label: "Initial Screening" },
  { id: "technical", label: "Technical Round" },
  { id: "coding", label: "Live Coding / DSA" },
  { id: "system_design", label: "System Design" },
  { id: "behavioral", label: "Behavioral / Culture Fit" },
  { id: "final_round", label: "Final / Partner Round" },
];

export default function InterviewPrepPage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500 mb-3" />
          <p className="text-sm text-muted-foreground">Loading AI Interview Preparation Workspace...</p>
        </div>
      }
    >
      <InterviewPrepContent />
    </React.Suspense>
  );
}

function InterviewPrepContent() {
  const { user, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();

  // Active workspace tab: 'dashboard' | 'setup' | 'mock' | 'projects' | 'notes' | 'history'
  const [activeTab, setActiveTab] = useState<string>("dashboard");

  // Global loading states
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Data states
  const [analytics, setAnalytics] = useState<InterviewAnalyticsResponse | null>(null);
  const [sessions, setSessions] = useState<InterviewSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<InterviewSessionDetail | null>(null);
  const [activeQuestionIdx, setActiveQuestionIdx] = useState<number>(0);

  // Available user records for session setup
  const [applications, setApplications] = useState<JobApplicationSummary[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);

  // Setup Form State
  const [selectedAppId, setSelectedAppId] = useState<string>(
    searchParams.get("application_id") || ""
  );
  const [selectedJobId, setSelectedJobId] = useState<string>(
    searchParams.get("job_id") || ""
  );
  const [selectedRound, setSelectedRound] = useState<string>("technical");
  const [selectedCategory, setSelectedCategory] = useState<string>("technical");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("intermediate");
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [userInstructions, setUserInstructions] = useState<string>("");
  const [selectedProjectName, setSelectedProjectName] = useState<string>("");
  const [isCreatingSession, setIsCreatingSession] = useState<boolean>(false);

  // Answer submission state
  const [answerText, setAnswerText] = useState<string>("");
  const [submittedCode, setSubmittedCode] = useState<string>("");
  const [submittedLang, setSubmittedLang] = useState<string>("python");
  const [showCodeInput, setShowCodeInput] = useState<boolean>(false);
  const [showContextHint, setShowContextHint] = useState<boolean>(false);
  const [showExpectedPoints, setShowExpectedPoints] = useState<boolean>(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState<boolean>(false);

  // Project breakdown studio state
  const [projectStudioName, setProjectStudioName] = useState<string>("");
  const [projectStudioInstructions, setProjectStudioInstructions] = useState<string>("");
  const [projectBreakdown, setProjectBreakdown] = useState<ProjectBreakdownResponse | null>(null);
  const [isGeneratingProject, setIsGeneratingProject] = useState<boolean>(false);

  // Notes state
  const [notes, setNotes] = useState<InterviewNoteResponse[]>([]);
  const [noteFilterType, setNoteFilterType] = useState<string>("all");
  const [newNoteTitle, setNewNoteTitle] = useState<string>("");
  const [newNoteContent, setNewNoteContent] = useState<string>("");
  const [newNoteType, setNewNoteType] = useState<string>("topics_to_revise");
  const [isSavingNote, setIsSavingNote] = useState<boolean>(false);
  const [showNoteModal, setShowNoteModal] = useState<boolean>(false);

  // Reminder state
  const [reminderDate, setReminderDate] = useState<string>("");
  const [reminderType, setReminderType] = useState<string>("interview_reminder");
  const [isSchedulingReminder, setIsSchedulingReminder] = useState<boolean>(false);
  const [reminderSuccess, setReminderSuccess] = useState<string | null>(null);

  // Initial Data Load
  const loadWorkspaceData = useCallback(async () => {
    try {
      setLoading(true);
      setErrorMsg(null);

      const [analyticsData, sessionsData, appsData, jobsData, resumesData, notesData] =
        await Promise.allSettled([
          interviewPrepApi.getAnalytics(),
          interviewPrepApi.listSessions(),
          applicationsApi.listApplications(),
          jobsApi.listJobs({ page_size: 40 }),
          resumesApi.listResumes(),
          interviewPrepApi.listNotes(),
        ]);

      if (analyticsData.status === "fulfilled") setAnalytics(analyticsData.value);
      if (sessionsData.status === "fulfilled") setSessions(sessionsData.value);
      if (appsData.status === "fulfilled") setApplications(appsData.value.items || []);
      if (jobsData.status === "fulfilled") setJobs(jobsData.value.items || []);
      if (resumesData.status === "fulfilled") setResumes(resumesData.value || []);
      if (notesData.status === "fulfilled") setNotes(notesData.value || []);

      // If user came with application_id or job_id in query params, switch to setup tab
      const qApp = searchParams.get("application_id");
      const qJob = searchParams.get("job_id");
      if (qApp || qJob) {
        setActiveTab("setup");
      }
    } catch (err: any) {
      console.error("Failed to load interview prep data:", err);
      setErrorMsg("Failed to load interview prep workspace data.");
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  useEffect(() => {
    if (user && !authLoading) {
      loadWorkspaceData();
    }
  }, [user, authLoading, loadWorkspaceData]);

  // Current active question
  const currentQuestion: InterviewQuestionDetail | null = useMemo(() => {
    if (!activeSession || !activeSession.questions || activeSession.questions.length === 0) {
      return null;
    }
    return activeSession.questions[activeQuestionIdx] || null;
  }, [activeSession, activeQuestionIdx]);

  // Auto-fill answer fields when question index changes
  useEffect(() => {
    if (currentQuestion) {
      if (currentQuestion.answer) {
        setAnswerText(currentQuestion.answer.answer_text || "");
        setSubmittedCode(currentQuestion.answer.submitted_code || "");
        setShowCodeInput(!!currentQuestion.answer.submitted_code);
      } else {
        setAnswerText("");
        setSubmittedCode("");
        setShowCodeInput(
          currentQuestion.category === "coding_problem_solving" ||
            currentQuestion.category === "backend_python"
        );
      }
      setShowContextHint(false);
      setShowExpectedPoints(false);
    }
  }, [currentQuestion]);

  // Create Interview Preparation Session
  const handleStartSession = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsCreatingSession(true);
      setErrorMsg(null);

      const session = await interviewPrepApi.createSession({
        application_id: selectedAppId || undefined,
        job_id: selectedJobId || undefined,
        interview_round: selectedRound,
        interview_type: "mock_interview",
        category: selectedCategory,
        difficulty: selectedDifficulty,
        question_count: questionCount,
        user_instructions: userInstructions.trim() || undefined,
        selected_project_name: selectedProjectName.trim() || undefined,
      });

      setActiveSession(session);
      setActiveQuestionIdx(0);
      setActiveTab("mock");
      setSessions((prev) => [
        {
          id: session.id,
          user_id: session.user_id,
          job_id: session.job_id,
          job_title: session.title,
          company_name: null,
          interview_round: session.interview_round,
          interview_type: session.interview_type,
          difficulty: session.difficulty,
          status: session.status,
          title: session.title,
          total_questions: session.total_questions,
          completed_questions: session.completed_questions,
          average_score: session.average_score,
          created_at: session.created_at,
          updated_at: session.updated_at,
        },
        ...prev,
      ]);
    } catch (err: any) {
      console.error("Failed to create prep session:", err);
      setErrorMsg(
        err.message ||
          "Could not initialize session. Please verify you have uploaded and analyzed a resume."
      );
    } finally {
      setIsCreatingSession(false);
    }
  };

  // Resume or View Existing Session
  const handleSelectSession = async (sessionId: string) => {
    try {
      setLoading(true);
      const detail = await interviewPrepApi.getSession(sessionId);
      setActiveSession(detail);
      // Find first unanswered question or default to 0
      const firstUnanswered = detail.questions.findIndex((q) => !q.answer);
      setActiveQuestionIdx(firstUnanswered >= 0 ? firstUnanswered : 0);
      setActiveTab("mock");
    } catch (err: any) {
      console.error("Failed to load session detail:", err);
      setErrorMsg("Unable to retrieve session details.");
    } finally {
      setLoading(false);
    }
  };

  // Submit Answer to Active Question
  const handleSubmitAnswer = async () => {
    if (!activeSession || !currentQuestion) return;
    if (!answerText.trim() && !submittedCode.trim()) {
      alert("Please provide an explanation or code snippet before submitting.");
      return;
    }

    try {
      setIsSubmittingAnswer(true);
      setErrorMsg(null);

      const resp = await interviewPrepApi.submitAnswer(
        activeSession.id,
        currentQuestion.id,
        {
          answer_text: answerText.trim(),
          submitted_code: submittedCode.trim() || undefined,
          submitted_language: submittedLang,
        }
      );

      // Update question state in active session
      const updatedQuestions = [...activeSession.questions];
      updatedQuestions[activeQuestionIdx] = {
        ...currentQuestion,
        status: "answered",
        answer: resp,
        evaluation: resp.evaluation,
      };

      // Fetch fresh session detail to get exact progress and average score
      const freshSession = await interviewPrepApi.getSession(activeSession.id);
      setActiveSession(freshSession);

      // Refresh analytics in background
      interviewPrepApi.getAnalytics().then((a) => setAnalytics(a)).catch(() => {});
    } catch (err: any) {
      console.error("Failed to submit answer:", err);
      setErrorMsg(err.message || "Failed to evaluate answer. Please try again.");
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  // Generate Project Breakdown
  const handleGenerateProjectBreakdown = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectStudioName.trim()) {
      alert("Please enter a project name from your resume.");
      return;
    }

    try {
      setIsGeneratingProject(true);
      setErrorMsg(null);
      const resp = await interviewPrepApi.getProjectBreakdown(
        projectStudioName.trim(),
        selectedJobId || undefined,
        projectStudioInstructions.trim() || undefined
      );
      setProjectBreakdown(resp);
    } catch (err: any) {
      console.error("Failed to generate project breakdown:", err);
      setErrorMsg(err.message || "Failed to generate project breakdown.");
    } finally {
      setIsGeneratingProject(false);
    }
  };

  // Notes CRUD
  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteTitle.trim() || !newNoteContent.trim()) return;

    try {
      setIsSavingNote(true);
      const note = await interviewPrepApi.createNote({
        title: newNoteTitle.trim(),
        content: newNoteContent.trim(),
        note_type: newNoteType,
        session_id: activeSession?.id,
        application_id: selectedAppId || undefined,
      });
      setNotes((prev) => [note, ...prev]);
      setNewNoteTitle("");
      setNewNoteContent("");
      setShowNoteModal(false);
    } catch (err: any) {
      console.error("Failed to create note:", err);
      alert("Failed to save note.");
    } finally {
      setIsSavingNote(false);
    }
  };

  const handleTogglePinNote = async (note: InterviewNoteResponse) => {
    try {
      const updated = await interviewPrepApi.updateNote(note.id, {
        is_pinned: !note.is_pinned,
      });
      setNotes((prev) => prev.map((n) => (n.id === note.id ? updated : n)));
    } catch (err) {
      console.error("Failed to toggle pin:", err);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!confirm("Are you sure you want to delete this note?")) return;
    try {
      await interviewPrepApi.deleteNote(noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (err) {
      console.error("Failed to delete note:", err);
    }
  };

  // Schedule Reminder
  const handleScheduleReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reminderDate) {
      alert("Please select a date and time for the reminder.");
      return;
    }

    try {
      setIsSchedulingReminder(true);
      setReminderSuccess(null);
      const resp = await interviewPrepApi.scheduleReminder({
        session_id: activeSession?.id,
        application_id: selectedAppId || undefined,
        scheduled_at: new Date(reminderDate).toISOString(),
        reminder_type: reminderType,
        custom_message: `Interview practice reminder for ${activeSession?.title || "upcoming round"}`,
      });
      setReminderSuccess(
        `Reminder scheduled for ${new Date(resp.scheduled_at).toLocaleString()}`
      );
      setReminderDate("");
    } catch (err: any) {
      console.error("Failed to schedule reminder:", err);
      alert(err.message || "Failed to schedule reminder.");
    } finally {
      setIsSchedulingReminder(false);
    }
  };

  // Filtered Notes
  const filteredNotes = useMemo(() => {
    if (noteFilterType === "all") return notes;
    return notes.filter((n) => n.note_type === noteFilterType);
  }, [notes, noteFilterType]);

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
            </Link>
            <span className="text-xs text-muted-foreground">•</span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
              <Sparkles className="w-3 h-3" /> AI Interview Coach
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground flex items-center gap-3">
            <GraduationCap className="w-8 h-8 text-orange-500" />
            Interview Preparation & Coaching
          </h1>
          <p className="text-sm text-muted-foreground max-w-3xl">
            Grounded practice sessions built on your verified resume and target role requirements.
            Master technical, coding, system design, and behavioral interviews with rigorous rubric feedback.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <NotificationBell />
          <button
            onClick={() => setActiveTab("setup")}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-orange-600 hover:bg-orange-500 text-white shadow-sm transition"
          >
            <Plus className="w-4 h-4" /> Start New Session
          </button>
        </div>
      </div>

      {/* Global Alerts */}
      {errorMsg && (
        <div className="p-4 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Notice</p>
            <p className="text-xs mt-0.5">{errorMsg}</p>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-xs font-semibold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Primary Navigation Tabs */}
      <nav className="flex items-center gap-2 overflow-x-auto border-b border-border pb-2 text-sm font-medium">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap ${
            activeTab === "dashboard"
              ? "bg-secondary font-bold text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          }`}
        >
          <Compass className="w-4 h-4" /> Overview & Analytics
        </button>

        <button
          onClick={() => setActiveTab("setup")}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap ${
            activeTab === "setup"
              ? "bg-secondary font-bold text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          }`}
        >
          <Play className="w-4 h-4" /> Start Prep Session
        </button>

        {activeSession && (
          <button
            onClick={() => setActiveTab("mock")}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap ${
              activeTab === "mock"
                ? "bg-orange-500/10 text-orange-600 dark:text-orange-400 font-bold border border-orange-500/30"
                : "text-orange-500 hover:bg-orange-500/10"
            }`}
          >
            <Brain className="w-4 h-4" /> Active Mock Interview ({activeQuestionIdx + 1}/
            {activeSession.total_questions})
          </button>
        )}

        <button
          onClick={() => setActiveTab("projects")}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap ${
            activeTab === "projects"
              ? "bg-secondary font-bold text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          }`}
        >
          <Code className="w-4 h-4" /> Project Deep-Dive Studio
        </button>

        <button
          onClick={() => setActiveTab("notes")}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap ${
            activeTab === "notes"
              ? "bg-secondary font-bold text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          }`}
        >
          <ListChecks className="w-4 h-4" /> Notes & Checklist ({notes.length})
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap ${
            activeTab === "history"
              ? "bg-secondary font-bold text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
          }`}
        >
          <History className="w-4 h-4" /> Session History ({sessions.length})
        </button>
      </nav>

      {/* ==================================================================== */}
      {/* TAB 1: OVERVIEW & ANALYTICS                                         */}
      {/* ==================================================================== */}
      {activeTab === "dashboard" && (
        <div className="space-y-6">
          {/* KPI Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="p-4 rounded-xl border border-border bg-card">
              <span className="text-xs text-muted-foreground font-medium">Total Sessions</span>
              <p className="text-2xl font-extrabold text-foreground mt-1">
                {analytics?.total_sessions_started ?? analytics?.total_sessions ?? sessions.length}
              </p>
              <span className="text-[11px] text-muted-foreground">Initiated prep</span>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <span className="text-xs text-muted-foreground font-medium">Completed</span>
              <p className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                {analytics?.total_sessions_completed ?? analytics?.completed_sessions ?? 0}
              </p>
              <span className="text-[11px] text-muted-foreground">Finished interviews</span>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <span className="text-xs text-muted-foreground font-medium">Questions Attempted</span>
              <p className="text-2xl font-extrabold text-foreground mt-1">
                {analytics?.total_questions_attempted || 0}
              </p>
              <span className="text-[11px] text-muted-foreground">Evaluated by AI</span>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <span className="text-xs text-muted-foreground font-medium">Overall Average</span>
              <p className="text-2xl font-extrabold text-primary mt-1">
                {analytics?.overall_average_score ? `${analytics.overall_average_score}%` : "—"}
              </p>
              <span className="text-[11px] text-muted-foreground">Weighted rubric</span>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <span className="text-xs text-muted-foreground font-medium">Technical Score</span>
              <p className="text-2xl font-extrabold text-blue-600 dark:text-blue-400 mt-1">
                {analytics?.technical_average_score ? `${analytics.technical_average_score}%` : "—"}
              </p>
              <span className="text-[11px] text-muted-foreground">DSA & System Design</span>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <span className="text-xs text-muted-foreground font-medium">Behavioral Score</span>
              <p className="text-2xl font-extrabold text-purple-600 dark:text-purple-400 mt-1">
                {analytics?.behavioral_average_score
                  ? `${analytics.behavioral_average_score}%`
                  : "—"}
              </p>
              <span className="text-[11px] text-muted-foreground">STAR communication</span>
            </div>
          </div>

          {/* Diagnostic Breakdown: Strong vs Weak Areas & Recommendations */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-5 rounded-xl border border-border bg-card space-y-3">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold text-sm">
                <CheckCircle2 className="w-4 h-4" /> Demonstrated Strengths (≥75%)
              </div>
              {analytics?.strong_areas && analytics.strong_areas.length > 0 ? (
                <ul className="space-y-2 text-xs">
                  {analytics.strong_areas.map((st, i) => (
                    <li
                      key={i}
                      className="p-2.5 rounded-lg bg-emerald-500/10 text-foreground border border-emerald-500/20 flex items-center gap-2"
                    >
                      <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      <span>{st}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground italic">
                  Complete mock interview questions to reveal your top-performing competency areas.
                </p>
              )}
            </div>

            <div className="p-5 rounded-xl border border-border bg-card space-y-3">
              <div className="flex items-center gap-2 text-rose-500 font-bold text-sm">
                <AlertTriangle className="w-4 h-4" /> Focus Areas for Revision (&lt;70%)
              </div>
              {analytics?.weak_areas && analytics.weak_areas.length > 0 ? (
                <ul className="space-y-2 text-xs">
                  {analytics.weak_areas.map((wk, i) => (
                    <li
                      key={i}
                      className="p-2.5 rounded-lg bg-rose-500/10 text-foreground border border-rose-500/20 flex items-center gap-2"
                    >
                      <AlertCircle className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
                      <span>{wk}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground italic">
                  No critical gaps identified yet. Answer more advanced questions to identify growth areas.
                </p>
              )}
            </div>

            <div className="p-5 rounded-xl border border-border bg-card space-y-3">
              <div className="flex items-center gap-2 text-primary font-bold text-sm">
                <Lightbulb className="w-4 h-4 text-amber-500" /> Recommended Revision Topics
              </div>
              {analytics?.recommended_revision_topics &&
              analytics.recommended_revision_topics.length > 0 ? (
                <ul className="space-y-2 text-xs">
                  {analytics.recommended_revision_topics.map((tp, i) => (
                    <li
                      key={i}
                      className="p-2.5 rounded-lg bg-secondary text-foreground flex items-center gap-2"
                    >
                      <CornerDownRight className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                      <span>{tp}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground italic">
                  Recommended topics will populate automatically as you complete technical answers.
                </p>
              )}
            </div>
          </div>

          {/* Quick Actions & Recent Sessions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-foreground">Recent Preparation Sessions</h2>
                <button
                  onClick={() => setActiveTab("history")}
                  className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                >
                  View All ({sessions.length}) <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {sessions.length === 0 ? (
                <div className="p-8 rounded-xl border border-dashed border-border text-center space-y-3">
                  <GraduationCap className="w-10 h-10 text-muted-foreground mx-auto" />
                  <p className="text-sm font-medium text-foreground">No sessions created yet</p>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                    Start a personalized interview prep session grounded in your resume and target role.
                  </p>
                  <button
                    onClick={() => setActiveTab("setup")}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition"
                  >
                    <Plus className="w-3.5 h-3.5" /> Start First Session
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {sessions.slice(0, 4).map((s) => (
                    <div
                      key={s.id}
                      className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition flex items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-foreground">{s.title}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              s.status === "completed"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                            }`}
                          >
                            {s.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span className="capitalize">{s.difficulty}</span>
                          <span>•</span>
                          <span>
                            {s.completed_questions} of {s.total_questions} answered
                          </span>
                          <span>•</span>
                          <span>{new Date(s.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {s.average_score !== null && s.average_score !== undefined && (
                          <div className="text-right">
                            <span className="text-xs text-muted-foreground">Avg Score</span>
                            <p className="text-base font-extrabold text-foreground">
                              {s.average_score}%
                            </p>
                          </div>
                        )}

                        <button
                          onClick={() => handleSelectSession(s.id)}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-secondary hover:bg-secondary/80 text-foreground transition flex items-center gap-1"
                        >
                          {s.status === "completed" ? "Review" : "Continue"}{" "}
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Practice Launcher */}
            <div className="p-6 rounded-xl border border-border bg-card space-y-4">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <Zap className="w-4 h-4 text-orange-500" /> Fast Prep Setup
              </h3>
              <p className="text-xs text-muted-foreground">
                Select your focus area and instantly launch a 5-question mock interview calibrated for your profile.
              </p>

              <div className="space-y-2">
                {CATEGORIES.slice(0, 5).map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => {
                      setSelectedCategory(cat.id);
                      setActiveTab("setup");
                    }}
                    className="w-full text-left p-2.5 rounded-lg border border-border bg-secondary/40 hover:bg-secondary hover:border-primary/40 transition flex items-center justify-between"
                  >
                    <div>
                      <p className="text-xs font-semibold text-foreground">{cat.label}</p>
                      <p className="text-[10px] text-muted-foreground line-clamp-1">
                        {cat.description}
                      </p>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
                  </button>
                ))}
              </div>

              <button
                onClick={() => setActiveTab("setup")}
                className="w-full py-2 text-xs font-semibold rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition text-center"
              >
                Configure Custom Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 2: START NEW PREPARATION SESSION                                */}
      {/* ==================================================================== */}
      {activeTab === "setup" && (
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="p-6 rounded-2xl border border-border bg-card space-y-6">
            <div>
              <h2 className="text-lg font-bold text-foreground">Configure Interview Prep Session</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Questions will strictly test skills and technologies grounded in your verified resume and target role.
              </p>
            </div>

            <form onSubmit={handleStartSession} className="space-y-6">
              {/* Linked Opportunity */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Link Tracked Application (Optional)
                  </label>
                  <select
                    value={selectedAppId}
                    onChange={(e) => {
                      setSelectedAppId(e.target.value);
                      const app = applications.find((a) => a.id === e.target.value);
                      if (app && app.job_id) setSelectedJobId(app.job_id);
                    }}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground focus:ring-1 focus:ring-primary"
                  >
                    <option value="">None / General Practice</option>
                    {applications.map((app) => (
                      <option key={app.id} value={app.id}>
                        {app.title} ({app.company_name}) — {app.status}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Target Job Opportunity (Optional)
                  </label>
                  <select
                    value={selectedJobId}
                    onChange={(e) => setSelectedJobId(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground focus:ring-1 focus:ring-primary"
                  >
                    <option value="">General Software Engineer Role</option>
                    {jobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title} ({j.company?.name || "Company"})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Round & Category Selection */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Interview Round</label>
                  <select
                    value={selectedRound}
                    onChange={(e) => setSelectedRound(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground"
                  >
                    {ROUNDS.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Question Difficulty</label>
                  <select
                    value={selectedDifficulty}
                    onChange={(e) => setSelectedDifficulty(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground"
                  >
                    {DIFFICULTIES.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.label} — {d.desc}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 10-Category Selector Grid */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-foreground">
                  Interview Category (Select 1 of 10 Specialized Domains)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
                  {CATEGORIES.map((cat) => {
                    const isSelected = selectedCategory === cat.id;
                    return (
                      <button
                        type="button"
                        key={cat.id}
                        onClick={() => setSelectedCategory(cat.id)}
                        className={`p-3 text-left rounded-xl border transition flex flex-col justify-between ${
                          isSelected
                            ? "border-orange-500 bg-orange-500/10 text-orange-600 dark:text-orange-400 shadow-sm"
                            : "border-border bg-card hover:bg-secondary/60 text-foreground"
                        }`}
                      >
                        <p className="font-bold text-xs">{cat.label}</p>
                        <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2">
                          {cat.description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Question Count & Project Anchor */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Number of Questions ({questionCount})
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="15"
                    value={questionCount}
                    onChange={(e) => setQuestionCount(parseInt(e.target.value))}
                    className="w-full accent-orange-500 cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>1 (Quick check)</span>
                    <span>5 (Standard)</span>
                    <span>15 (Full round)</span>
                  </div>
                </div>

                <div className="sm:col-span-2 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Anchor to Specific Resume Project (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Distributed Task Scheduler, E-Commerce API"
                    value={selectedProjectName}
                    onChange={(e) => setSelectedProjectName(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Questions will directly challenge technical choices made in this project.
                  </p>
                </div>
              </div>

              {/* Candidate Focus Instructions */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Custom Instructions or Focus Areas (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Focus on concurrency bugs, memory optimization, and concrete trade-offs with PostgreSQL vs Redis."
                  value={userInstructions}
                  onChange={(e) => setUserInstructions(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground"
                />
              </div>

              {/* Submit CTA */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setActiveTab("dashboard")}
                  className="px-4 py-2 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingSession}
                  className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-lg bg-orange-600 hover:bg-orange-500 text-white shadow-sm transition disabled:opacity-50"
                >
                  {isCreatingSession ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Generating Plan & Questions...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" /> Generate Grounded Preparation Session
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 3: INTERACTIVE MOCK INTERVIEW                                   */}
      {/* ==================================================================== */}
      {activeTab === "mock" && activeSession && (
        <div className="space-y-6">
          {/* Active Session Header Banner */}
          <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-foreground">{activeSession.title}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
                  {activeSession.difficulty}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Question {activeQuestionIdx + 1} of {activeSession.total_questions} • Completed:{" "}
                {activeSession.completed_questions}/{activeSession.total_questions}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {activeSession.average_score !== null && (
                <div className="text-right">
                  <span className="text-[11px] text-muted-foreground">Session Score</span>
                  <p className="text-xl font-extrabold text-foreground">
                    {activeSession.average_score}%
                  </p>
                </div>
              )}

              {/* Question Navigator Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto p-1 rounded-lg bg-secondary">
                {activeSession.questions.map((q, idx) => (
                  <button
                    key={q.id}
                    onClick={() => setActiveQuestionIdx(idx)}
                    className={`w-7 h-7 text-xs font-bold rounded-md flex items-center justify-center transition ${
                      activeQuestionIdx === idx
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : q.answer
                        ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                        : "text-muted-foreground hover:bg-secondary/80"
                    }`}
                  >
                    {idx + 1}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Grounded Preparation Plan Drawer / Accordion */}
          {activeSession.preparation_plan && (
            <details className="group p-4 rounded-xl border border-border bg-card/60 transition">
              <summary className="cursor-pointer font-semibold text-xs text-foreground flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-primary" /> Personalized Preparation Plan
                  (Grounded in Resume & Role)
                </span>
                <ChevronDown className="w-4 h-4 text-muted-foreground group-open:rotate-180 transition-transform" />
              </summary>
              <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {activeSession.preparation_plan.technical_topics_to_revise && (
                  <div className="space-y-2">
                    <h4 className="font-bold text-foreground flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-blue-500" /> High-Yield Topics to Revise
                    </h4>
                    <ul className="space-y-1.5 text-muted-foreground">
                      {activeSession.preparation_plan.technical_topics_to_revise.map((t, i) => (
                        <li key={i} className="p-2 rounded bg-secondary">
                          <span className="font-semibold text-foreground">{t.topic}</span>
                          <p className="text-[11px] mt-0.5">{t.rationale}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeSession.preparation_plan.potential_skill_gaps && (
                  <div className="space-y-2">
                    <h4 className="font-bold text-foreground flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> Skill Gaps & Mitigation
                    </h4>
                    <ul className="space-y-1.5 text-muted-foreground">
                      {activeSession.preparation_plan.potential_skill_gaps.map((g, i) => (
                        <li key={i} className="p-2 rounded bg-secondary">
                          <span className="font-semibold text-foreground">{g.skill_or_requirement}</span>
                          <p className="text-[11px] mt-0.5">{g.mitigation_strategy}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          )}

          {/* Question & Evaluation Card */}
          {currentQuestion ? (
            <div className="space-y-6">
              {/* Question Statement */}
              <div className="p-6 rounded-2xl border border-border bg-card space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
                      Question #{currentQuestion.question_order} • {currentQuestion.category}
                    </span>
                    <span className="text-xs text-muted-foreground capitalize">
                      {currentQuestion.difficulty}
                    </span>
                  </div>

                  {currentQuestion.answer && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      <Check className="w-3.5 h-3.5" /> Answer Evaluated
                    </span>
                  )}
                </div>

                <h3 className="text-lg font-bold text-foreground leading-snug">
                  {currentQuestion.question_text}
                </h3>

                {/* Helper toggles */}
                <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
                  {currentQuestion.context_hint && (
                    <button
                      type="button"
                      onClick={() => setShowContextHint(!showContextHint)}
                      className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground font-medium underline-offset-4 hover:underline"
                    >
                      <HelpCircle className="w-3.5 h-3.5" />
                      {showContextHint ? "Hide Context Hint" : "Show Context Hint"}
                    </button>
                  )}

                  {currentQuestion.expected_points && currentQuestion.expected_points.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setShowExpectedPoints(!showExpectedPoints)}
                      className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground font-medium underline-offset-4 hover:underline"
                    >
                      <CheckSquare className="w-3.5 h-3.5" />
                      {showExpectedPoints ? "Hide Rubric Expectations" : "Preview Expected Points"}
                    </button>
                  )}
                </div>

                {showContextHint && currentQuestion.context_hint && (
                  <div className="p-3 rounded-xl border border-primary/20 bg-primary/5 text-xs text-foreground">
                    <p className="font-semibold text-primary">Interviewer Hint:</p>
                    <p className="mt-0.5">{currentQuestion.context_hint}</p>
                  </div>
                )}

                {showExpectedPoints && currentQuestion.expected_points && (
                  <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-xs text-foreground space-y-1">
                    <p className="font-semibold text-amber-500">Evaluation Checklist:</p>
                    <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                      {currentQuestion.expected_points.map((pt, i) => (
                        <li key={i}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Candidate Answer Workspace */}
              <div className="p-6 rounded-2xl border border-border bg-card space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-primary" /> Your Response & Reasoning
                  </h4>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setShowCodeInput(!showCodeInput)}
                      className={`px-2.5 py-1 text-xs font-semibold rounded-lg border transition flex items-center gap-1.5 ${
                        showCodeInput
                          ? "bg-secondary text-foreground border-border"
                          : "border-border text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <Code className="w-3.5 h-3.5" />
                      {showCodeInput ? "Hide Code Snippet" : "+ Add Code Snippet"}
                    </button>
                    <span className="text-xs text-muted-foreground">
                      {answerText.split(/\s+/).filter(Boolean).length} words
                    </span>
                  </div>
                </div>

                <textarea
                  rows={6}
                  placeholder="Explain your approach clearly. Walk through your problem-solving process, mention trade-offs, edge cases, and any concrete projects from your experience..."
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  className="w-full p-4 rounded-xl border border-border bg-background text-foreground text-sm placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                />

                {/* Optional Static Code Snippet Box */}
                {showCodeInput && (
                  <div className="space-y-2 pt-2 border-t border-border">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                        <FileCode className="w-3.5 h-3.5 text-blue-500" /> Implementation Code (Statically Verified)
                      </span>
                      <select
                        value={submittedLang}
                        onChange={(e) => setSubmittedLang(e.target.value)}
                        className="px-2 py-1 text-xs rounded border border-border bg-background text-foreground"
                      >
                        <option value="python">Python 3</option>
                        <option value="javascript">JavaScript / TypeScript</option>
                        <option value="sql">SQL Query</option>
                      </select>
                    </div>
                    <textarea
                      rows={5}
                      placeholder="# Write or paste code snippet here. Code is safely verified statically without server execution."
                      value={submittedCode}
                      onChange={(e) => setSubmittedCode(e.target.value)}
                      className="w-full p-3 rounded-lg border border-border bg-background font-mono text-xs text-foreground placeholder:text-muted-foreground"
                    />
                  </div>
                )}

                {/* Submit Action */}
                <div className="flex items-center justify-between pt-2">
                  <div className="text-xs text-muted-foreground">
                    {currentQuestion.answer && (
                      <span>
                        Last evaluated:{" "}
                        {new Date(currentQuestion.answer.submitted_at).toLocaleTimeString()}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={handleSubmitAnswer}
                    disabled={isSubmittingAnswer}
                    className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-lg bg-orange-600 hover:bg-orange-500 text-white shadow-sm transition disabled:opacity-50"
                  >
                    {isSubmittingAnswer ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" /> Evaluating Answer Rubric...
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" /> Submit for AI Rubric Evaluation
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Rubric Evaluation Results Card */}
              {currentQuestion.evaluation && (
                <div className="p-6 rounded-2xl border border-border bg-card space-y-6">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border">
                    <div>
                      <div className="flex items-center gap-2">
                        <Award className="w-5 h-5 text-orange-500" />
                        <h4 className="text-base font-bold text-foreground">
                          AI Coach Evaluation & Rubric Breakdown
                        </h4>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Evaluated across 6 technical and communication dimensions.
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className="text-xs text-muted-foreground">Overall Question Score</span>
                        <p
                          className={`text-2xl font-black ${
                            currentQuestion.evaluation.overall_score >= 75
                              ? "text-emerald-500"
                              : currentQuestion.evaluation.overall_score >= 60
                              ? "text-amber-500"
                              : "text-rose-500"
                          }`}
                        >
                          {currentQuestion.evaluation.overall_score}/100
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 6 Rubric Dimensions Progress Bars */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="p-3 rounded-xl bg-secondary/60 space-y-1">
                      <span className="text-[11px] text-muted-foreground font-medium">
                        Correctness (30%)
                      </span>
                      <p className="text-base font-bold text-foreground">
                        {currentQuestion.evaluation.technical_correctness_score}%
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-secondary/60 space-y-1">
                      <span className="text-[11px] text-muted-foreground font-medium">
                        Relevance (20%)
                      </span>
                      <p className="text-base font-bold text-foreground">
                        {currentQuestion.evaluation.relevance_score}%
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-secondary/60 space-y-1">
                      <span className="text-[11px] text-muted-foreground font-medium">
                        Completeness (20%)
                      </span>
                      <p className="text-base font-bold text-foreground">
                        {currentQuestion.evaluation.completeness_score}%
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-secondary/60 space-y-1">
                      <span className="text-[11px] text-muted-foreground font-medium">
                        Clarity (10%)
                      </span>
                      <p className="text-base font-bold text-foreground">
                        {currentQuestion.evaluation.clarity_score}%
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-secondary/60 space-y-1">
                      <span className="text-[11px] text-muted-foreground font-medium">
                        Approach (10%)
                      </span>
                      <p className="text-base font-bold text-foreground">
                        {currentQuestion.evaluation.approach_score}%
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-secondary/60 space-y-1">
                      <span className="text-[11px] text-muted-foreground font-medium">
                        Communication (10%)
                      </span>
                      <p className="text-base font-bold text-foreground">
                        {currentQuestion.evaluation.communication_score}%
                      </p>
                    </div>
                  </div>

                  {/* Strengths & Missing Points */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-2">
                      <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" /> Demonstrated Strengths
                      </span>
                      <ul className="space-y-1.5 text-xs text-foreground">
                        {currentQuestion.evaluation.strengths.map((s, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                            <span>{s}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/5 space-y-2">
                      <span className="text-xs font-bold text-rose-500 flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4" /> Missing Key Points
                      </span>
                      <ul className="space-y-1.5 text-xs text-foreground">
                        {currentQuestion.evaluation.missing_points.map((m, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-rose-500 font-bold flex-shrink-0">•</span>
                            <span>{m}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Suggested Improvements & Stronger Answer */}
                  <div className="space-y-3">
                    <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-2">
                      <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                        <Lightbulb className="w-4 h-4 text-amber-500" /> Actionable Improvements
                      </span>
                      <ul className="space-y-1 text-xs text-muted-foreground list-disc list-inside">
                        {currentQuestion.evaluation.suggested_improvements.map((imp, i) => (
                          <li key={i}>{imp}</li>
                        ))}
                      </ul>
                    </div>

                    {currentQuestion.evaluation.stronger_answer_example && (
                      <div className="p-4 rounded-xl border border-border bg-secondary/40 space-y-2">
                        <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                          <Sparkles className="w-4 h-4 text-orange-500" /> Model Exemplar Answer
                        </span>
                        <blockquote className="text-xs text-muted-foreground italic border-l-2 border-orange-500 pl-3 leading-relaxed">
                          {currentQuestion.evaluation.stronger_answer_example}
                        </blockquote>
                      </div>
                    )}
                  </div>

                  {/* Navigation CTA: Next Question */}
                  <div className="flex items-center justify-between pt-4 border-t border-border">
                    <button
                      onClick={() =>
                        setActiveQuestionIdx(Math.max(0, activeQuestionIdx - 1))
                      }
                      disabled={activeQuestionIdx === 0}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-border hover:bg-secondary disabled:opacity-40 transition"
                    >
                      ← Previous Question
                    </button>

                    {activeQuestionIdx < activeSession.questions.length - 1 ? (
                      <button
                        onClick={() =>
                          setActiveQuestionIdx(activeQuestionIdx + 1)
                        }
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground transition shadow-sm"
                      >
                        Next Question ({activeQuestionIdx + 2}/
                        {activeSession.questions.length}) →
                      </button>
                    ) : (
                      <button
                        onClick={() => setActiveTab("dashboard")}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm"
                      >
                        <CheckCircle2 className="w-4 h-4" /> Complete Session & View Analytics
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              No active question selected.
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 4: PROJECT DEEP-DIVE STUDIO                                     */}
      {/* ==================================================================== */}
      {activeTab === "projects" && (
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="p-6 rounded-2xl border border-border bg-card space-y-6">
            <div>
              <h2 className="text-lg font-bold text-foreground">
                Resume Project Deep-Dive Studio
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Break down any project from your resume into an interview-ready STAR architectural walkthrough.
                Zero fabrication — only evidenced technical components are referenced.
              </p>
            </div>

            <form onSubmit={handleGenerateProjectBreakdown} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Select or Enter Project Name from Your Resume
                </label>
                <input
                  type="text"
                  placeholder="e.g. Distributed Task Queue, Real-Time Chat Engine, E-Commerce Microservices"
                  value={projectStudioName}
                  onChange={(e) => setProjectStudioName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Custom Focus / Target Technical Areas (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Emphasize why I chose PostgreSQL over MongoDB, how connection pooling solved timeouts, and production Docker containerization."
                  value={projectStudioInstructions}
                  onChange={(e) => setProjectStudioInstructions(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isGeneratingProject || !projectStudioName.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-lg bg-orange-600 hover:bg-orange-500 text-white shadow-sm transition disabled:opacity-50"
                >
                  {isGeneratingProject ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Analyzing Project Architecture...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" /> Generate STAR Project Breakdown
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Project Breakdown Result Display */}
            {projectBreakdown && (
              <div className="pt-6 border-t border-border space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-extrabold text-foreground flex items-center gap-2">
                    <Code className="w-5 h-5 text-orange-500" />
                    {projectBreakdown.project_name} — Technical Walkthrough
                  </h3>
                  <span className="text-[10px] text-muted-foreground uppercase px-2 py-0.5 rounded bg-secondary">
                    {projectBreakdown.provider} • {projectBreakdown.model}
                  </span>
                </div>

                {/* 30-Second Elevator Pitch */}
                <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-1.5">
                  <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" /> 30-Second Interview Elevator Pitch
                  </span>
                  <p className="text-xs text-foreground leading-relaxed">
                    {projectBreakdown.overview_pitch}
                  </p>
                </div>

                {/* Architecture & Design */}
                <div className="p-4 rounded-xl border border-border bg-card space-y-1.5">
                  <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-blue-500" /> System Architecture & Data Flow
                  </span>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {projectBreakdown.architecture_and_design}
                  </p>
                </div>

                {/* Technical Implementation */}
                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <span className="text-xs font-bold text-foreground">
                    Core Technical Implementation Highlights
                  </span>
                  <ul className="space-y-1 text-xs text-muted-foreground list-disc list-inside">
                    {projectBreakdown.technical_implementation.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>

                {/* Key Challenges & Solutions (STAR) */}
                <div className="space-y-3">
                  <span className="text-xs font-bold text-foreground">
                    Engineering Challenges & Solved Bottlenecks (STAR)
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {projectBreakdown.key_challenges_and_solutions.map((ch, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-xl border border-border bg-secondary/40 space-y-1.5 text-xs"
                      >
                        <p className="font-semibold text-rose-500">Challenge #{i + 1}:</p>
                        <p className="text-foreground">{ch.challenge}</p>
                        <p className="font-semibold text-emerald-500 pt-1">Solution Implemented:</p>
                        <p className="text-muted-foreground">{ch.solution}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Personal Ownership & Practice Questions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 rounded-xl border border-border bg-card space-y-1.5">
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-purple-500" /> Your Personal Contribution
                    </span>
                    <p className="text-muted-foreground leading-relaxed">
                      {projectBreakdown.candidate_contribution}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-orange-500" /> Anticipated Tough Questions
                    </span>
                    <ul className="space-y-1 text-muted-foreground list-disc list-inside">
                      {projectBreakdown.practice_questions.map((pq, i) => (
                        <li key={i}>{pq}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 5: PREPARATION NOTES & CHECKLIST                                */}
      {/* ==================================================================== */}
      {activeTab === "notes" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-base font-bold text-foreground">Interview Notes & Revision Checklists</h2>
              <p className="text-xs text-muted-foreground">
                Maintain personal talking points, questions to ask interviewers, company insights, and checklists.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowNoteModal(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5" /> Add Note
              </button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto text-xs">
            {[
              { id: "all", label: "All Notes" },
              { id: "topics_to_revise", label: "Topics to Revise" },
              { id: "questions_to_ask", label: "Questions to Ask Interviewer" },
              { id: "company_research", label: "Company Research" },
              { id: "checklist", label: "Preparation Checklist" },
              { id: "general", label: "General" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setNoteFilterType(f.id)}
                className={`px-3 py-1.5 rounded-lg border transition whitespace-nowrap ${
                  noteFilterType === f.id
                    ? "border-primary bg-primary/10 text-primary font-bold"
                    : "border-border bg-card hover:bg-secondary text-muted-foreground"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Notes Grid */}
          {filteredNotes.length === 0 ? (
            <div className="p-10 rounded-xl border border-dashed border-border text-center space-y-2">
              <ListChecks className="w-8 h-8 text-muted-foreground mx-auto" />
              <p className="text-xs text-muted-foreground">No notes found in this category.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredNotes.map((n) => (
                <div
                  key={n.id}
                  className={`p-4 rounded-xl border bg-card space-y-3 transition flex flex-col justify-between ${
                    n.is_pinned ? "border-amber-500/40 shadow-sm" : "border-border"
                  }`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-sm text-foreground">{n.title}</span>
                      <button
                        onClick={() => handleTogglePinNote(n)}
                        className={`p-1 rounded hover:bg-secondary transition ${
                          n.is_pinned ? "text-amber-500" : "text-muted-foreground"
                        }`}
                        title={n.is_pinned ? "Unpin note" : "Pin note to top"}
                      >
                        <Pin className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium uppercase bg-secondary text-muted-foreground">
                      {n.note_type.replace(/_/g, " ")}
                    </span>

                    <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed mt-2">
                      {n.content}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-border text-[11px] text-muted-foreground">
                    <span>{new Date(n.updated_at).toLocaleDateString()}</span>
                    <button
                      onClick={() => handleDeleteNote(n.id)}
                      className="text-destructive hover:underline p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Schedule Reminder Form Card */}
          <div className="p-5 rounded-2xl border border-border bg-card space-y-4 max-w-xl">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Bell className="w-4 h-4 text-purple-500" /> Schedule Interview Preparation Reminder
            </h3>
            <p className="text-xs text-muted-foreground">
              Schedule an automated alarm through Nexora’s Notification and Celery worker system.
            </p>

            <form onSubmit={handleScheduleReminder} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-foreground">Date & Time</label>
                  <input
                    type="datetime-local"
                    value={reminderDate}
                    onChange={(e) => setReminderDate(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background text-foreground"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-foreground">Reminder Type</label>
                  <select
                    value={reminderType}
                    onChange={(e) => setReminderType(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background text-foreground"
                  >
                    <option value="interview_reminder">Interview Round Reminder</option>
                    <option value="assessment_reminder">Technical Assessment</option>
                    <option value="application_follow_up">Preparation Checklist Review</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                {reminderSuccess && (
                  <span className="text-xs text-emerald-500 font-medium">{reminderSuccess}</span>
                )}
                <button
                  type="submit"
                  disabled={isSchedulingReminder || !reminderDate}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition disabled:opacity-50 ml-auto"
                >
                  {isSchedulingReminder ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Scheduling...
                    </>
                  ) : (
                    <>
                      <Bell className="w-3.5 h-3.5" /> Schedule Reminder
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Add Note Modal */}
          {showNoteModal && (
            <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
              <div className="w-full max-w-md p-6 rounded-2xl border border-border bg-card space-y-4 shadow-xl">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-sm text-foreground">Add Preparation Note</h3>
                  <button
                    onClick={() => setShowNoteModal(false)}
                    className="text-muted-foreground hover:text-foreground text-xs"
                  >
                    ✕
                  </button>
                </div>

                <form onSubmit={handleCreateNote} className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-foreground">Note Type</label>
                    <select
                      value={newNoteType}
                      onChange={(e) => setNewNoteType(e.target.value)}
                      className="w-full px-3 py-1.5 text-xs rounded border border-border bg-background text-foreground"
                    >
                      <option value="topics_to_revise">Topics to Revise</option>
                      <option value="questions_to_ask">Questions to Ask Interviewer</option>
                      <option value="company_research">Company Research</option>
                      <option value="checklist">Preparation Checklist</option>
                      <option value="general">General Note</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-foreground">Title</label>
                    <input
                      type="text"
                      placeholder="e.g. Questions on Sprint Lifecycle & Onboarding"
                      value={newNoteTitle}
                      onChange={(e) => setNewNoteTitle(e.target.value)}
                      className="w-full px-3 py-1.5 text-xs rounded border border-border bg-background text-foreground"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-foreground">Content</label>
                    <textarea
                      rows={4}
                      placeholder="Write your talking points, checklist items, or research findings..."
                      value={newNoteContent}
                      onChange={(e) => setNewNoteContent(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded border border-border bg-background text-foreground"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowNoteModal(false)}
                      className="px-3 py-1.5 text-xs font-semibold rounded border border-border text-foreground hover:bg-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSavingNote || !newNoteTitle.trim()}
                      className="px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      {isSavingNote ? "Saving..." : "Save Note"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 6: COMPLETE SESSION HISTORY                                      */}
      {/* ==================================================================== */}
      {activeTab === "history" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground">
              Previous Interview Preparation Sessions ({sessions.length})
            </h2>
            <button
              onClick={() => setActiveTab("setup")}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> Start New Session
            </button>
          </div>

          {sessions.length === 0 ? (
            <div className="p-10 rounded-xl border border-dashed border-border text-center space-y-2">
              <GraduationCap className="w-8 h-8 text-muted-foreground mx-auto" />
              <p className="text-xs text-muted-foreground">No sessions created yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition flex items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">{s.title}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          s.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                        }`}
                      >
                        {s.status}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase bg-secondary text-muted-foreground">
                        {s.difficulty}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>
                        Progress: {s.completed_questions}/{s.total_questions} questions
                      </span>
                      <span>•</span>
                      <span>Created {new Date(s.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {s.average_score !== null && (
                      <div className="text-right">
                        <span className="text-[11px] text-muted-foreground">Overall Score</span>
                        <p className="text-base font-extrabold text-foreground">
                          {s.average_score}%
                        </p>
                      </div>
                    )}

                    <button
                      onClick={() => handleSelectSession(s.id)}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-secondary hover:bg-secondary/80 text-foreground transition flex items-center gap-1"
                    >
                      {s.status === "completed" ? "Review" : "Continue"}{" "}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
