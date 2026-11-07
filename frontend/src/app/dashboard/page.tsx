"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Bell, Bot, Briefcase, Building2, CheckSquare, Compass, FileText, GraduationCap, Layers, LogOut, SendHorizontal, ShieldCheck, Sparkles, User } from "lucide-react";
import { useAuth } from "@/context/auth-context";
import { NotificationBell } from "@/components/NotificationBell";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading || !user) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Validating session...</p>
      </main>
    );
  }

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-12">
      <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-border mb-8">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" /> Authenticated Session
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Protected User Area</h1>
          <p className="text-sm text-muted-foreground">
            Signed in as <span className="font-semibold text-foreground">{user.full_name}</span> ({user.email})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <NotificationBell />
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-md border border-border bg-background hover:bg-secondary transition-colors"
          >
            <LogOut className="w-4 h-4 text-muted-foreground" /> Log Out
          </button>
        </div>
      </header>

      <section className="p-6 rounded-lg border border-border bg-card">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-full bg-secondary">
            <User className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-base font-semibold">User Identity Profile</h2>
            <p className="text-xs text-muted-foreground">Resolved from /api/v1/users/me</p>
          </div>
        </div>

        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="p-3 rounded-md bg-secondary/50">
            <dt className="text-xs text-muted-foreground">User ID</dt>
            <dd className="font-mono text-xs mt-1 truncate">{user.id}</dd>
          </div>

          <div className="p-3 rounded-md bg-secondary/50">
            <dt className="text-xs text-muted-foreground">Account Status</dt>
            <dd className="font-medium mt-1">
              {user.is_active ? (
                <span className="text-emerald-600 dark:text-emerald-400">Active</span>
              ) : (
                <span className="text-destructive">Disabled</span>
              )}
            </dd>
          </div>

          <div className="p-3 rounded-md bg-secondary/50">
            <dt className="text-xs text-muted-foreground">Registered On</dt>
            <dd className="mt-1 font-mono text-xs">
              {new Date(user.created_at).toLocaleString()}
            </dd>
          </div>

          <div className="p-3 rounded-md bg-secondary/50">
            <dt className="text-xs text-muted-foreground">Last Login</dt>
            <dd className="mt-1 font-mono text-xs">
              {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "First Session"}
            </dd>
          </div>
        </dl>
      </section>

      {/* Quick Launch Cards */}
      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
          Core Workspaces
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link
            href="/dashboard/resumes"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-primary/10 text-primary">
                <FileText className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Open Studio <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Resume Studio
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Upload PDF/DOCX resumes, extract structured skills and career history, and view AI recommendations.
            </p>
          </Link>

          <Link
            href="/dashboard/companies"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <Building2 className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Discover Companies <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Company Discovery
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Explore and curate early-career tech employers across product firms, GCCs, MNCs, and startups with verified provenance.
            </p>
          </Link>

          <Link
            href="/dashboard/company-intelligence"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                <Building2 className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Research Employers <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Company Intelligence & Research
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Evidence-backed tech stack classification, DB hiring analytics, candidate fit assessment, and 10-section AI research dossiers.
            </p>
          </Link>

          <Link
            href="/dashboard/jobs"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
                <Briefcase className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Browse Jobs <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Job Discovery & Ingestion
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Discover and ingest early-career technical listings from verified careers pages and permitted feeds with audit provenance.
            </p>
          </Link>

          <Link
            href="/dashboard/discovery"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400">
                <Compass className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Configure Feeds <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Automated Job Discovery
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Automated ATS integrations (Greenhouse, Lever, Ashby, RSS, JSON), recurring background scans, and execution logs.
            </p>
          </Link>

          <Link
            href="/dashboard/matches"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <Sparkles className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                View Matches <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Job Matching & Ranking
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Personalized alignment scoring with transparent evidence citations, preference controls, and freshness trust badges.
            </p>
          </Link>

          <Link
            href="/dashboard/recommendations"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400">
                <Bot className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Explore AI Recommendations <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              AI Job Recommendations
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Deep AI job intelligence, resume-to-job compatibility analysis, transferable skills recognition, and grounded career advice.
            </p>
          </Link>

          <Link
            href="/dashboard/applications"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <CheckSquare className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Track Applications <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Application Management
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Centralized application tracker, 9-stage pipeline, interview scheduler, activity timeline, and database analytics.
            </p>
          </Link>

          <Link
            href="/dashboard/application-assistant"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <SendHorizontal className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Open Assistant <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              AI Application Assistant
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Grounded cover letters, recruiter email composer, Gmail OAuth integration, and job application preparation workspace.
            </p>
          </Link>

          <Link
            href="/dashboard/resumes/tailor"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                <Layers className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Open Studio <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Resume Tailoring Studio
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Factual AI alignment, change-by-change acceptance, PDF compilation, and tailored resume export.
            </p>
          </Link>

          <Link
            href="/dashboard/interview-prep"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-orange-500/10 text-orange-600 dark:text-orange-400">
                <GraduationCap className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Start Prep <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              AI Interview Prep & Coaching
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Personalized preparation plans, 10-category mock interviews with rubric scoring, safe static code review, STAR project deep-dive, and notes.
            </p>
          </Link>

          <Link
            href="/dashboard/notifications"
            className="group p-6 rounded-xl border border-border bg-card hover:border-primary/50 hover:bg-secondary/40 transition-all shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400">
                <Bell className="w-6 h-6" />
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                Open Alerts <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
            <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
              Notifications & Reminders
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Scheduled interview alarms, deadline alerts, follow-up notifications, and timezone preferences.
            </p>
          </Link>
        </div>
      </section>
    </main>
  );
}

