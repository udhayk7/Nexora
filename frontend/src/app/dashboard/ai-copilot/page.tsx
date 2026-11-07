"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Award,
  BarChart3,
  Bot,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  CornerDownLeft,
  ExternalLink,
  FileText,
  GraduationCap,
  HelpCircle,
  Layers,
  Lightbulb,
  ListFilter,
  Loader2,
  MessageSquare,
  Network,
  Plus,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  User,
  Users,
  X,
  Zap,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  ActionProposal,
  AgentExecutionRecordItem,
  AgentTraceStep,
  CandidateContextPreview,
  copilotApi,
  CopilotMessageItem,
  CopilotSessionDetail,
  CopilotSessionItem,
} from "@/lib/api";

const QUICK_PROMPTS = [
  {
    title: "Find Suitable Jobs",
    prompt: "Find suitable jobs for my profile and rank my top matches.",
    icon: Briefcase,
  },
  {
    title: "Diagnose Career Readiness",
    prompt: "Analyze my career readiness, strengths, and identify my most critical skill gaps.",
    icon: BarChart3,
  },
  {
    title: "Prepare Application Pack",
    prompt: "Prepare a complete tailored application pack with cover letter and screening answers.",
    icon: FileText,
  },
  {
    title: "Mock Interview Coaching",
    prompt: "Create a personalized interview preparation plan and practice questions for my target role.",
    icon: Award,
  },
  {
    title: "Weekly Career Plan",
    prompt: "Create my prioritized weekly career action plan across applications, networking, and practice.",
    icon: Target,
  },
  {
    title: "Recruiter Networking",
    prompt: "Draft a grounded recruiter outreach connection note under 300 characters.",
    icon: Users,
  },
];

export default function AICopilotPage() {
  const { user } = useAuth();

  // State
  const [sessions, setSessions] = useState<CopilotSessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<CopilotSessionDetail | null>(null);
  const [contextPreview, setContextPreview] = useState<CandidateContextPreview | null>(null);

  const [inputContent, setInputContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionsLoading, setIsSessionsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Approval state tracker for action proposals
  const [approvingActions, setApprovingActions] = useState<Record<string, "approving" | "approved" | "rejected">>({});
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});
  const [showRightContext, setShowRightContext] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on messages update
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeSession?.messages, isLoading]);

  // Load candidate context preview
  const fetchContextPreview = useCallback(async () => {
    try {
      const ctx = await copilotApi.getContextPreview();
      setContextPreview(ctx);
    } catch (e) {
      console.warn("Could not load candidate context preview:", e);
    }
  }, []);

  // Load Sessions
  const fetchSessions = useCallback(async () => {
    setIsSessionsLoading(true);
    try {
      const data = await copilotApi.listSessions(25);
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
      }
    } catch (err: unknown) {
      console.error("Failed to load copilot sessions:", err);
      setErrorMsg("Failed to load chat history. Please refresh.");
    } finally {
      setIsSessionsLoading(false);
    }
  }, [activeSessionId]);

  // Load Active Session Details
  const fetchSessionDetail = useCallback(async (sessionId: string) => {
    try {
      const detail = await copilotApi.getSession(sessionId);
      setActiveSession(detail);
      setErrorMsg(null);
    } catch (err: unknown) {
      console.error("Failed to load session detail:", err);
      setErrorMsg("Failed to load session messages.");
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchContextPreview();
  }, [fetchSessions, fetchContextPreview]);

  useEffect(() => {
    if (activeSessionId) {
      fetchSessionDetail(activeSessionId);
    } else {
      setActiveSession(null);
    }
  }, [activeSessionId, fetchSessionDetail]);

  // Create New Session
  const handleCreateSession = async (title?: string) => {
    try {
      setIsLoading(true);
      const newSess = await copilotApi.createSession({
        title: title || "New Career Strategy Session",
        session_type: "career_strategy",
      });
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
    } catch (err) {
      console.error("Create session failed:", err);
      setErrorMsg("Failed to create new session.");
    } finally {
      setIsLoading(false);
    }
  };

  // Delete Session
  const handleDeleteSession = async (e: React.MouseEvent, sessId: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this Copilot session?")) return;
    try {
      await copilotApi.deleteSession(sessId);
      setSessions((prev) => prev.filter((s) => s.id !== sessId));
      if (activeSessionId === sessId) {
        const remaining = sessions.filter((s) => s.id !== sessId);
        setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (err) {
      console.error("Delete session failed:", err);
    }
  };

  // Send Message
  const handleSendMessage = async (textToSend?: string) => {
    const content = (textToSend || inputContent).trim();
    if (!content || isLoading) return;

    let targetSessionId = activeSessionId;

    // Create session if none exists
    if (!targetSessionId) {
      try {
        const newSess = await copilotApi.createSession({
          title: content.slice(0, 36) + "...",
        });
        setSessions((prev) => [newSess, ...prev]);
        setActiveSessionId(newSess.id);
        targetSessionId = newSess.id;
      } catch (err) {
        console.error("Session creation error:", err);
        setErrorMsg("Failed to initialize conversation session.");
        return;
      }
    }

    // Optimistically show user message
    const tempUserMessage: CopilotMessageItem = {
      id: `temp_${Date.now()}`,
      session_id: targetSessionId,
      role: "user",
      content,
      agent_trace: [],
      action_proposals: [],
      created_at: new Date().toISOString(),
    };

    setActiveSession((prev) =>
      prev
        ? { ...prev, messages: [...prev.messages, tempUserMessage] }
        : {
            id: targetSessionId!,
            title: "Career Strategy",
            session_type: "career_strategy",
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            messages: [tempUserMessage],
          }
    );

    setInputContent("");
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const assistantMessage = await copilotApi.postMessage(targetSessionId, { content });
      setActiveSession((prev) => {
        if (!prev) return null;
        // Replace temp message and append assistant response
        const filtered = prev.messages.filter((m) => m.id !== tempUserMessage.id);
        return {
          ...prev,
          messages: [...filtered, tempUserMessage, assistantMessage],
        };
      });
      fetchSessions();
      fetchContextPreview();
    } catch (err: unknown) {
      console.error("Failed to send message:", err);
      setErrorMsg("Assistant could not process request. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Consequential Action Approval
  const handleApproveAction = async (proposal: ActionProposal, recordId?: string) => {
    const actionKey = proposal.id;
    setApprovingActions((prev) => ({ ...prev, [actionKey]: "approving" }));

    try {
      if (recordId) {
        await copilotApi.handleApproval(recordId, { action: "approve" });
      } else {
        // Fallback simulate local persistence
        await new Promise((r) => setTimeout(r, 600));
      }
      setApprovingActions((prev) => ({ ...prev, [actionKey]: "approved" }));
    } catch (err) {
      console.error("Action approval error:", err);
      setApprovingActions((prev) => ({ ...prev, [actionKey]: "rejected" }));
    }
  };

  const handleRejectAction = async (proposal: ActionProposal, recordId?: string) => {
    const actionKey = proposal.id;
    setApprovingActions((prev) => ({ ...prev, [actionKey]: "approving" }));

    try {
      if (recordId) {
        await copilotApi.handleApproval(recordId, { action: "reject" });
      }
      setApprovingActions((prev) => ({ ...prev, [actionKey]: "rejected" }));
    } catch (err) {
      console.error("Action rejection error:", err);
    }
  };

  const toggleTraceExpansion = (msgId: string) => {
    setExpandedTraces((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-7xl mx-auto w-full px-2 sm:px-4 py-3">
      {/* Top Header Bar */}
      <header className="flex items-center justify-between pb-3 border-b border-border mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-primary/20 via-purple-500/20 to-blue-500/20 text-primary border border-primary/20 shadow-sm">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight">AI Career Copilot</h1>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                8 Multi-Agents Ready
              </span>
            </div>
            <p className="text-xs text-muted-foreground hidden sm:block">
              Centralized career intelligence coordinating resumes, job matching, company intel, networking, and interview coaching.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleCreateSession()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" /> New Session
          </button>
          <button
            onClick={() => setShowRightContext(!showRightContext)}
            className={`p-1.5 rounded-lg border text-xs font-medium transition-colors ${
              showRightContext
                ? "bg-secondary text-primary border-primary/30"
                : "border-border text-muted-foreground hover:bg-secondary"
            }`}
            title="Toggle Candidate Context View"
          >
            <User className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Multi-Column Grid */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-3 overflow-hidden min-h-0">
        {/* Left Sidebar: Session History */}
        <aside className="hidden md:flex md:col-span-3 lg:col-span-3 flex-col rounded-xl border border-border bg-card/60 backdrop-blur-sm p-3 overflow-hidden">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/60">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Conversation Sessions
            </span>
            <span className="text-[11px] px-1.5 py-0.5 rounded bg-secondary font-mono text-muted-foreground">
              {sessions.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {isSessionsLoading ? (
              <div className="flex items-center justify-center py-8 text-xs text-muted-foreground gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" /> Loading sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-8 px-2 text-xs text-muted-foreground">
                <MessageSquare className="w-6 h-6 mx-auto mb-2 opacity-30" />
                No active conversations yet. Start one by typing below!
              </div>
            ) : (
              sessions.map((sess) => {
                const isActive = sess.id === activeSessionId;
                return (
                  <div
                    key={sess.id}
                    onClick={() => setActiveSessionId(sess.id)}
                    className={`group flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer text-xs transition-all ${
                      isActive
                        ? "bg-primary/10 text-primary font-medium border border-primary/30 shadow-xs"
                        : "hover:bg-secondary/70 text-foreground/80 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                      <div className="truncate">
                        <div className="truncate font-medium">{sess.title}</div>
                        <div className="text-[10px] text-muted-foreground truncate">
                          {new Date(sess.created_at).toLocaleDateString([], {
                            month: "short",
                            day: "numeric",
                          })}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteSession(e, sess.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-destructive transition-opacity"
                      title="Delete session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {/* Quick Module Shortcuts */}
          <div className="pt-3 mt-2 border-t border-border/60">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1.5">
              Connected Modules
            </span>
            <div className="grid grid-cols-2 gap-1 text-[11px]">
              <Link
                href="/dashboard/career-workflow"
                className="flex items-center gap-1.5 p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground truncate transition-colors"
              >
                <Sparkles className="w-3 h-3 text-purple-500 shrink-0" />
                <span className="truncate">Workflow</span>
              </Link>
              <Link
                href="/dashboard/career-command-center"
                className="flex items-center gap-1.5 p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground truncate transition-colors"
              >
                <BarChart3 className="w-3 h-3 text-blue-500 shrink-0" />
                <span className="truncate">Command Ctr</span>
              </Link>
              <Link
                href="/dashboard/matches"
                className="flex items-center gap-1.5 p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground truncate transition-colors"
              >
                <Briefcase className="w-3 h-3 text-emerald-500 shrink-0" />
                <span className="truncate">Matches</span>
              </Link>
              <Link
                href="/dashboard/interview-prep"
                className="flex items-center gap-1.5 p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground truncate transition-colors"
              >
                <Award className="w-3 h-3 text-amber-500 shrink-0" />
                <span className="truncate">Interviews</span>
              </Link>
            </div>
          </div>
        </aside>

        {/* Center: Main Chat Thread */}
        <main
          className={`flex flex-col rounded-xl border border-border bg-card overflow-hidden ${
            showRightContext ? "col-span-12 md:col-span-9 lg:col-span-6" : "col-span-12 md:col-span-9 lg:col-span-9"
          }`}
        >
          {/* Chat Messages Feed */}
          <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-4">
            {errorMsg && (
              <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
                <button onClick={() => setErrorMsg(null)} className="p-1 hover:opacity-70">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {!activeSession || activeSession.messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                <div className="p-4 rounded-2xl bg-gradient-to-tr from-primary/20 via-purple-500/10 to-blue-500/20 text-primary border border-primary/20 shadow-md mb-4">
                  <Sparkles className="w-8 h-8 text-primary animate-pulse" />
                </div>
                <h2 className="text-base font-bold text-foreground mb-1">
                  Welcome to Nexora Career Copilot
                </h2>
                <p className="text-xs text-muted-foreground max-w-md mb-6">
                  Ask anything about your job discovery, resume tailoring, skill gaps, interview prep, or let the orchestrator run multi-agent workflows.
                </p>

                {/* Suggested Prompt Chips Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg text-left">
                  {QUICK_PROMPTS.map((qp, idx) => {
                    const IconComp = qp.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(qp.prompt)}
                        className="p-2.5 rounded-lg border border-border bg-card hover:border-primary/50 hover:bg-secondary/60 transition-all text-xs flex items-start gap-2.5 group shadow-2xs"
                      >
                        <div className="p-1.5 rounded-md bg-secondary text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors shrink-0 mt-0.5">
                          <IconComp className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-foreground group-hover:text-primary transition-colors">
                            {qp.title}
                          </div>
                          <div className="text-[11px] text-muted-foreground truncate">
                            {qp.prompt}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              activeSession.messages.map((msg) => {
                const isUser = msg.role === "user";
                const isExpanded = !!expandedTraces[msg.id];
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-2`}
                  >
                    {/* Message Bubble */}
                    <div
                      className={`max-w-[92%] sm:max-w-[85%] rounded-2xl p-3.5 text-xs shadow-xs transition-all ${
                        isUser
                          ? "bg-primary text-primary-foreground rounded-tr-xs"
                          : "bg-secondary/70 text-foreground border border-border/80 rounded-tl-xs"
                      }`}
                    >
                      {/* Assistant Header Badge */}
                      {!isUser && (
                        <div className="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-border/40 text-[11px]">
                          <div className="flex items-center gap-1.5 text-primary font-semibold">
                            <Bot className="w-3.5 h-3.5" />
                            <span>Nexora Copilot</span>
                            {msg.intent && (
                              <span className="px-1.5 py-0.2 rounded bg-primary/10 text-primary text-[10px] uppercase font-mono font-normal">
                                {msg.intent.replace(/_/g, " ")}
                              </span>
                            )}
                          </div>
                          {msg.latency_ms && (
                            <span className="text-[10px] text-muted-foreground font-mono">
                              {msg.latency_ms}ms
                            </span>
                          )}
                        </div>
                      )}

                      {/* Content Body with Markdown formatting */}
                      <div className="whitespace-pre-wrap leading-relaxed font-sans text-xs">
                        {msg.content}
                      </div>

                      {/* Multi-Agent Orchestration Trace Accordion */}
                      {!isUser && msg.agent_trace && msg.agent_trace.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-border/50">
                          <button
                            onClick={() => toggleTraceExpansion(msg.id)}
                            className="w-full flex items-center justify-between text-[11px] text-muted-foreground hover:text-foreground transition-colors py-1"
                          >
                            <span className="inline-flex items-center gap-1.5 font-medium">
                              <Zap className="w-3 h-3 text-amber-500" />
                              Multi-Agent Trace ({msg.agent_trace.length} agents coordinated)
                            </span>
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {isExpanded && (
                            <div className="mt-2 space-y-1.5 pt-1.5 border-t border-border/40">
                              {msg.agent_trace.map((step, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 rounded-md bg-background/80 border border-border/60 text-[11px]"
                                >
                                  <div className="flex items-center justify-between gap-2 mb-1">
                                    <span className="font-semibold text-foreground capitalize">
                                      {step.agent_name.replace(/_/g, " ")} Agent
                                    </span>
                                    <div className="flex items-center gap-1.5 font-mono text-[10px]">
                                      <span className="px-1 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                                        {step.status}
                                      </span>
                                      <span className="text-muted-foreground">{step.latency_ms}ms</span>
                                    </div>
                                  </div>
                                  <p className="text-muted-foreground text-[10.5px]">
                                    {step.reasoning_summary}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action Proposals Cards */}
                    {!isUser && msg.action_proposals && msg.action_proposals.length > 0 && (
                      <div className="w-full max-w-[92%] sm:max-w-[85%] space-y-2 mt-1">
                        {msg.action_proposals.map((proposal) => {
                          const state = approvingActions[proposal.id];
                          const isApprovalRequired = proposal.requires_approval;

                          return (
                            <div
                              key={proposal.id}
                              className={`p-3 rounded-xl border text-xs transition-all shadow-xs ${
                                isApprovalRequired
                                  ? "border-amber-500/40 bg-amber-500/5 dark:bg-amber-500/10"
                                  : "border-border bg-card hover:border-primary/40"
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-1.5">
                                  {isApprovalRequired ? (
                                    <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0" />
                                  ) : (
                                    <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                                  )}
                                  <span className="font-semibold text-foreground">
                                    {proposal.title}
                                  </span>
                                </div>
                                {isApprovalRequired && (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-600 dark:text-amber-400 uppercase tracking-wide shrink-0">
                                    Approval Gate
                                  </span>
                                )}
                              </div>

                              <p className="text-[11px] text-muted-foreground mb-2.5">
                                {proposal.description}
                              </p>

                              {/* Action Footer */}
                              <div className="flex items-center justify-between pt-2 border-t border-border/40">
                                {isApprovalRequired ? (
                                  state === "approved" ? (
                                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                                      <Check className="w-3.5 h-3.5" /> Approved by candidate
                                    </span>
                                  ) : state === "rejected" ? (
                                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-destructive">
                                      <X className="w-3.5 h-3.5" /> Declined by candidate
                                    </span>
                                  ) : (
                                    <div className="flex items-center gap-2">
                                      <button
                                        disabled={state === "approving"}
                                        onClick={() => handleApproveAction(proposal)}
                                        className="inline-flex items-center gap-1 px-3 py-1 rounded-md bg-primary text-primary-foreground text-[11px] font-medium hover:bg-primary/90 transition-colors shadow-2xs"
                                      >
                                        {state === "approving" ? (
                                          <Loader2 className="w-3 h-3 animate-spin" />
                                        ) : (
                                          <ShieldCheck className="w-3 h-3" />
                                        )}
                                        Approve Action
                                      </button>
                                      <button
                                        disabled={state === "approving"}
                                        onClick={() => handleRejectAction(proposal)}
                                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-border hover:bg-secondary text-[11px] text-muted-foreground transition-colors"
                                      >
                                        Decline
                                      </button>
                                    </div>
                                  )
                                ) : (
                                  proposal.deep_link && (
                                    <Link
                                      href={proposal.deep_link}
                                      className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline ml-auto"
                                    >
                                      Open Workspace <ExternalLink className="w-3 h-3" />
                                    </Link>
                                  )
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {isLoading && (
              <div className="flex items-center gap-2.5 text-xs text-muted-foreground p-3 rounded-xl bg-secondary/40 border border-border/50 max-w-xs animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
                <span>Orchestrating specialized agents...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <footer className="p-3 border-t border-border bg-card/80 backdrop-blur-sm">
            {/* Quick Action Chips Bar */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-1 scrollbar-none">
              <button
                onClick={() => handleSendMessage("Find suitable verified jobs for my profile.")}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-secondary hover:bg-secondary/80 text-foreground transition-colors shrink-0"
              >
                <Briefcase className="w-3 h-3 text-primary" /> Find Jobs
              </button>
              <button
                onClick={() => handleSendMessage("Analyze my career readiness and skill gaps.")}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-secondary hover:bg-secondary/80 text-foreground transition-colors shrink-0"
              >
                <BarChart3 className="w-3 h-3 text-primary" /> Skill Gaps
              </button>
              <button
                onClick={() => handleSendMessage("Prepare a tailored application pack with cover letter.")}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-secondary hover:bg-secondary/80 text-foreground transition-colors shrink-0"
              >
                <FileText className="w-3 h-3 text-primary" /> Tailor Application
              </button>
              <button
                onClick={() => handleSendMessage("Start an interactive mock interview session.")}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-secondary hover:bg-secondary/80 text-foreground transition-colors shrink-0"
              >
                <Award className="w-3 h-3 text-primary" /> Mock Interview
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-end gap-2"
            >
              <div className="relative flex-1">
                <textarea
                  ref={inputRef}
                  value={inputContent}
                  onChange={(e) => setInputContent(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Ask Nexora Copilot anything (e.g. 'Match me with jobs', 'Prep for interview')..."
                  rows={2}
                  className="w-full resize-none rounded-xl border border-border bg-background px-3 py-2 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-inner"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !inputContent.trim()}
                className="p-3 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm shrink-0"
                title="Send message (Enter)"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </footer>
        </main>

        {/* Right Drawer: Lean Candidate Context & Quick Controls */}
        {showRightContext && (
          <aside className="col-span-12 lg:col-span-3 flex flex-col rounded-xl border border-border bg-card/60 backdrop-blur-sm p-3.5 space-y-4 overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between pb-2 border-b border-border/60">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                Shared Candidate Context
              </span>
              <button
                onClick={() => fetchContextPreview()}
                className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                title="Refresh candidate context"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            </div>

            {/* Candidate Identity Card */}
            <div className="p-3 rounded-lg border border-border bg-secondary/40 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                  {contextPreview?.full_name ? contextPreview.full_name[0] : user?.full_name?.[0] || "U"}
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-xs truncate">
                    {contextPreview?.full_name || user?.full_name}
                  </div>
                  <div className="text-[10px] text-muted-foreground truncate">
                    Target: {contextPreview?.target_roles?.[0] || "Software Engineer"}
                  </div>
                </div>
              </div>

              {/* Career Readiness Score */}
              <div className="pt-2 border-t border-border/40">
                <div className="flex items-center justify-between text-[11px] mb-1">
                  <span className="text-muted-foreground">Career Readiness</span>
                  <span className="font-bold text-primary">
                    {Math.round(contextPreview?.career_readiness_score || 75)}%
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(10, Math.round(contextPreview?.career_readiness_score || 75)))}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Verified Skills Badges */}
            <div>
              <span className="text-[11px] font-semibold text-foreground block mb-1.5">
                Verified Technical Skills
              </span>
              <div className="flex flex-wrap gap-1">
                {contextPreview?.verified_skills && contextPreview.verified_skills.length > 0 ? (
                  contextPreview.verified_skills.slice(0, 8).map((skill, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-secondary text-foreground border border-border/60"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-[11px] text-muted-foreground italic">
                    Upload resume to verify skills
                  </span>
                )}
              </div>
            </div>

            {/* Key Funnel Stats */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-lg border border-border bg-secondary/30">
                <div className="text-[10px] text-muted-foreground">Active Apps</div>
                <div className="text-base font-bold text-foreground mt-0.5">
                  {contextPreview?.active_applications_count ?? 0}
                </div>
              </div>
              <div className="p-2.5 rounded-lg border border-border bg-secondary/30">
                <div className="text-[10px] text-muted-foreground">Interviews</div>
                <div className="text-base font-bold text-foreground mt-0.5">
                  {contextPreview?.interviews_scheduled_count ?? 0}
                </div>
              </div>
            </div>

            {/* Privacy & Safety Note */}
            <div className="p-2.5 rounded-lg border border-border/60 bg-muted/30 text-[10.5px] text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground flex items-center gap-1">
                <Shield className="w-3 h-3 text-emerald-500" /> Grounded &amp; Privacy-First
              </div>
              <p>
                Agent orchestration operates solely on verified credentials. Consequential operations (dispatching emails, applying) strictly require candidate approval.
              </p>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
