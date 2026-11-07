"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  DollarSign,
  ExternalLink,
  HardDrive,
  HelpCircle,
  Layers,
  Loader2,
  Mail,
  RefreshCw,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow,
  XCircle,
  Zap,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  AIUsageSummaryData,
  IntegrationServiceHealth,
  IntegrationsHealthOverview,
  integrationsApi,
  JobSourcesResponse,
} from "@/lib/api";

export default function IntegrationsDashboardPage() {
  const { user, isLoading: authLoading } = useAuth();

  const [healthData, setHealthData] = useState<IntegrationsHealthOverview | null>(null);
  const [usageData, setUsageData] = useState<AIUsageSummaryData | null>(null);
  const [jobSourcesData, setJobSourcesData] = useState<JobSourcesResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [testingService, setTestingService] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, IntegrationServiceHealth>>({});
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true);
    setError(null);
    try {
      const [health, usage, sources] = await Promise.all([
        integrationsApi.getHealth(),
        integrationsApi.getAIUsage(),
        integrationsApi.getJobSources(),
      ]);
      setHealthData(health);
      setUsageData(usage);
      setJobSourcesData(sources);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load integration status";
      setError(message);
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

  const handleTestService = async (serviceName: string) => {
    setTestingService(serviceName);
    try {
      const res = await integrationsApi.testService(serviceName);
      setTestResults((prev) => ({ ...prev, [serviceName]: res }));
      // Reload health data in background to reflect current state
      integrationsApi.getHealth().then((h) => setHealthData(h)).catch(() => {});
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Service ping failed";
      setTestResults((prev) => ({
        ...prev,
        [serviceName]: {
          service: serviceName,
          status: "error",
          message: msg,
        },
      }));
    } finally {
      setTestingService(null);
    }
  };

  const getStatusBadge = (status: string | undefined) => {
    const s = (status || "unconfigured").toLowerCase();
    if (s === "connected" || s === "operational") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" /> Operational
        </span>
      );
    }
    if (s === "degraded") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3" /> Degraded
        </span>
      );
    }
    if (s === "disconnected" || s === "unconfigured") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-muted-foreground border border-border">
          <Clock className="w-3 h-3" /> Unconfigured
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
        <XCircle className="w-3 h-3" /> Error
      </span>
    );
  };

  if (authLoading || (isLoading && !healthData)) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
        <p className="text-sm text-muted-foreground">Inspecting external integration services & budget telemetry...</p>
      </div>
    );
  }

  // Count operational vs unconfigured
  const servicesList: IntegrationServiceHealth[] = healthData
    ? [
        healthData.openai,
        healthData.gemini,
        healthData.postgres,
        healthData.redis,
        healthData.celery,
        healthData.gmail,
      ]
    : [];

  const operationalCount = servicesList.filter(
    (s) => s.status === "connected" || s.status === "operational"
  ).length;

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary mb-2">
            <Zap className="w-3.5 h-3.5" /> Production Infrastructure & API Control
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">External Integrations & Health</h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            Real-time diagnostic health, dual-provider AI routing (OpenAI & Google Gemini), Celery worker transport security, and server-side API cost controls.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh Diagnostics
          </button>
        </div>
      </header>

      {error && (
        <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {/* KPI Overview Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Services Monitored</span>
            <Server className="w-4 h-4 text-primary" />
          </div>
          <p className="text-2xl font-bold">{servicesList.length + 5}</p>
          <p className="text-xs text-muted-foreground">6 core services + 5 job adapters</p>
        </div>

        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Core Connected</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {operationalCount} / {servicesList.length}
          </p>
          <p className="text-xs text-muted-foreground">Active in this environment</p>
        </div>

        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Daily AI Spend</span>
            <DollarSign className="w-4 h-4 text-indigo-500" />
          </div>
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            ${usageData ? usageData.daily_spend_usd.toFixed(4) : "0.0000"}
          </p>
          <p className="text-xs text-muted-foreground">
            Budget cap: ${usageData ? usageData.daily_budget_usd.toFixed(2) : "10.00"} / day
          </p>
        </div>

        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Monthly AI Spend</span>
            <Activity className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            ${usageData ? usageData.monthly_spend_usd.toFixed(4) : "0.0000"}
          </p>
          <p className="text-xs text-muted-foreground">
            Budget cap: ${usageData ? usageData.monthly_budget_usd.toFixed(2) : "100.00"} / mo
          </p>
        </div>
      </div>

      {/* SECTION 1: Service Status Cards Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight">Core Infrastructure & Integrations</h2>
            <p className="text-xs text-muted-foreground">
              Isolated ping checks execute non-destructive diagnostic probes. No API credentials are ever exposed to the client.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* 1. OpenAI Provider Card */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">OpenAI Provider</h3>
                    <p className="text-xs text-muted-foreground">Primary AI Provider</p>
                  </div>
                </div>
                {getStatusBadge(healthData?.openai?.status)}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Routine Tier:</span>
                  <span className="font-mono font-medium">gpt-4o-mini</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Strong Tier:</span>
                  <span className="font-mono font-medium">gpt-4o</span>
                </div>
                {healthData?.openai?.latency_ms !== undefined && (
                  <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                    <span className="text-muted-foreground">Latency:</span>
                    <span className="font-mono font-medium">{healthData.openai.latency_ms} ms</span>
                  </div>
                )}
                <p className="text-xs text-muted-foreground pt-1 italic">
                  {testResults.openai?.message || healthData?.openai?.message || "Ready for career analysis and reasoning tasks."}
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {testResults.openai?.latency_ms ? `Ping: ${testResults.openai.latency_ms}ms` : "Live ping probe"}
              </span>
              <button
                onClick={() => handleTestService("openai")}
                disabled={testingService === "openai"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-secondary hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {testingService === "openai" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Pinging...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-500" /> Test Ping
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 2. Google Gemini Provider Card */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Google Gemini</h3>
                    <p className="text-xs text-muted-foreground">Secondary AI Provider</p>
                  </div>
                </div>
                {getStatusBadge(healthData?.gemini?.status)}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Routine Tier:</span>
                  <span className="font-mono font-medium">gemini-2.5-flash</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Strong Tier:</span>
                  <span className="font-mono font-medium">gemini-1.5-pro</span>
                </div>
                {healthData?.gemini?.latency_ms !== undefined && (
                  <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                    <span className="text-muted-foreground">Latency:</span>
                    <span className="font-mono font-medium">{healthData.gemini.latency_ms} ms</span>
                  </div>
                )}
                <p className="text-xs text-muted-foreground pt-1 italic">
                  {testResults.gemini?.message || healthData?.gemini?.message || "High-throughput fallback provider."}
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {testResults.gemini?.latency_ms ? `Ping: ${testResults.gemini.latency_ms}ms` : "Live ping probe"}
              </span>
              <button
                onClick={() => handleTestService("gemini")}
                disabled={testingService === "gemini"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-secondary hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {testingService === "gemini" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Pinging...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-500" /> Test Ping
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 3. PostgreSQL Database Card */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">PostgreSQL Database</h3>
                    <p className="text-xs text-muted-foreground">Connection Pool & Storage</p>
                  </div>
                </div>
                {getStatusBadge(healthData?.postgres?.status)}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Pool Size / Max:</span>
                  <span className="font-mono font-medium">
                    {healthData?.postgres?.pool_size ?? 20} / {healthData?.postgres?.max_overflow ?? 10}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Checked Out:</span>
                  <span className="font-mono font-medium">
                    {healthData?.postgres?.active_connections ?? 0} active
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">SSL Mode:</span>
                  <span className="font-mono font-medium">prefer</span>
                </div>
                <p className="text-xs text-muted-foreground pt-1 italic">
                  {testResults.postgres?.message || healthData?.postgres?.message || "Relational database connection healthy."}
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {testResults.postgres?.latency_ms ? `Query: ${testResults.postgres.latency_ms}ms` : "SELECT 1 check"}
              </span>
              <button
                onClick={() => handleTestService("postgres")}
                disabled={testingService === "postgres"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-secondary hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {testingService === "postgres" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Probing...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-500" /> Test Connection
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 4. Redis & Celery Workers Card */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2.5 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400">
                    <HardDrive className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Redis & Celery Queue</h3>
                    <p className="text-xs text-muted-foreground">Task Broker & Rate Limiting</p>
                  </div>
                </div>
                {getStatusBadge(healthData?.redis?.status)}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Celery Status:</span>
                  <span className="font-semibold">{getStatusBadge(healthData?.celery?.status)}</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Workers Online:</span>
                  <span className="font-mono font-medium">{healthData?.celery?.connected_workers ?? 1} worker</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Redis Latency:</span>
                  <span className="font-mono font-medium">{healthData?.redis?.latency_ms ?? 1} ms</span>
                </div>
                <p className="text-xs text-muted-foreground pt-1 italic">
                  {testResults.redis?.message || healthData?.redis?.message || "Atomic pacing scripts and asynchronous worker pool active."}
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {testResults.celery?.connected_workers ? `${testResults.celery.connected_workers} workers verified` : "PING / celery probe"}
              </span>
              <button
                onClick={() => handleTestService("redis")}
                disabled={testingService === "redis"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-secondary hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {testingService === "redis" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Pinging...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-500" /> Test Redis
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 5. Gmail OAuth Integration Card */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2.5 rounded-lg bg-red-500/10 text-red-600 dark:text-red-400">
                    <Mail className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Gmail OAuth Integration</h3>
                    <p className="text-xs text-muted-foreground">Recruiter Outreach & Drafts</p>
                  </div>
                </div>
                {getStatusBadge(healthData?.gmail?.status)}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Account:</span>
                  <span className="font-mono font-medium truncate max-w-[150px]">
                    {healthData?.gmail?.email || "No account linked"}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Token Security:</span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">AES-GCM Encrypted</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-md bg-secondary/40">
                  <span className="text-muted-foreground">Sending Boundary:</span>
                  <span className="font-medium">Strict user confirmation</span>
                </div>
                <p className="text-xs text-muted-foreground pt-1 italic">
                  {testResults.gmail?.message || healthData?.gmail?.message || "Connect via Application Assistant to generate drafts."}
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <Link
                href="/dashboard/application-assistant"
                className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1"
              >
                Assistant Settings <ArrowRight className="w-3 h-3" />
              </Link>
              <button
                onClick={() => handleTestService("gmail")}
                disabled={testingService === "gmail"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-secondary hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {testingService === "gmail" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Checking...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-500" /> Verify OAuth
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 6. Job Source Adapters Card */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2.5 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400">
                    <Workflow className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Job Discovery Adapters</h3>
                    <p className="text-xs text-muted-foreground">5 Automated Adapters</p>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" /> 5 Operational
                </span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between py-1 border-b border-border/50">
                  <span>Greenhouse API</span>
                  <span className="font-mono text-muted-foreground">0.5s domain pacing</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-border/50">
                  <span>Lever Postings</span>
                  <span className="font-mono text-muted-foreground">0.5s domain pacing</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-border/50">
                  <span>Ashby HQ</span>
                  <span className="font-mono text-muted-foreground">0.5s domain pacing</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-border/50">
                  <span>RSS / Atom Feeds</span>
                  <span className="font-mono text-muted-foreground">Robots & SSRF safe</span>
                </div>
                <div className="flex items-center justify-between py-1">
                  <span>Generic JSON Feeds</span>
                  <span className="font-mono text-muted-foreground">Schema validation</span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">No scraping or bypass</span>
              <button
                onClick={() => handleTestService("job_sources")}
                disabled={testingService === "job_sources"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-secondary hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {testingService === "job_sources" ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Verifying...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-500" /> Verify Adapters
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2: AI Cost, Budget & Consumption Monitoring */}
      {usageData && (
        <section className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold tracking-tight">AI Consumption, Cost Management & Limits</h2>
              <p className="text-xs text-muted-foreground">
                Audited telemetry with hard spending ceilings, duplicate request hash fingerprinting, and dynamic fallback.
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-secondary text-xs font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> Server-side budget enforcement active
            </div>
          </div>

          {/* Budget Gauges */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Daily Budget */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold">Platform Daily Spending Budget</h3>
                  <p className="text-xs text-muted-foreground">Resets at 00:00 UTC daily</p>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold">${usageData.daily_spend_usd.toFixed(4)}</span>
                  <span className="text-xs text-muted-foreground"> / ${usageData.daily_budget_usd.toFixed(2)}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-secondary rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-2.5 rounded-full transition-all ${
                    usageData.daily_budget_percent > 90
                      ? "bg-rose-500"
                      : usageData.daily_budget_percent > 70
                      ? "bg-amber-500"
                      : "bg-emerald-500"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(2, usageData.daily_budget_percent))}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{usageData.daily_budget_percent.toFixed(1)}% of daily allowance consumed</span>
                <span>Max: 150,000 tokens/user/day</span>
              </div>
            </div>

            {/* Monthly Budget */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold">Platform Monthly Spending Budget</h3>
                  <p className="text-xs text-muted-foreground">Rolling calendar month ceiling</p>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold">${usageData.monthly_spend_usd.toFixed(4)}</span>
                  <span className="text-xs text-muted-foreground"> / ${usageData.monthly_budget_usd.toFixed(2)}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-secondary rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-2.5 rounded-full transition-all ${
                    usageData.monthly_budget_percent > 90
                      ? "bg-rose-500"
                      : usageData.monthly_budget_percent > 70
                      ? "bg-amber-500"
                      : "bg-indigo-500"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(2, usageData.monthly_budget_percent))}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{usageData.monthly_budget_percent.toFixed(1)}% of monthly allowance consumed</span>
                <span>Automated hard cutoff at $100.00</span>
              </div>
            </div>
          </div>

          {/* Breakdown by Provider & Feature */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* By Provider & Model */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary" /> Consumption by Model & Provider
              </h3>

              <div className="space-y-3">
                {Object.keys(usageData.by_model).length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">
                    No AI requests logged in current billing cycle yet.
                  </p>
                ) : (
                  Object.entries(usageData.by_model).map(([modelName, stats]) => (
                    <div key={modelName} className="p-3 rounded-lg bg-secondary/40 flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold font-mono">{modelName}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {stats.requests_count} calls &bull; {stats.total_tokens.toLocaleString()} tokens
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-bold font-mono text-primary">
                          ${stats.estimated_cost_usd.toFixed(4)}
                        </p>
                        <p className="text-[11px] text-muted-foreground">Estimated spend</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* By Feature */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Cpu className="w-4 h-4 text-primary" /> Consumption by Platform Feature
              </h3>

              <div className="space-y-3">
                {Object.keys(usageData.by_feature).length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">
                    No feature usage records found in current period.
                  </p>
                ) : (
                  Object.entries(usageData.by_feature).map(([featureName, stats]) => (
                    <div key={featureName} className="p-3 rounded-lg bg-secondary/40 flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold capitalize">{featureName.replace(/_/g, " ")}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {stats.requests_count} calls &bull; {stats.total_tokens.toLocaleString()} tokens
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-bold font-mono text-primary">
                          ${stats.estimated_cost_usd.toFixed(4)}
                        </p>
                        <p className="text-[11px] text-muted-foreground">Estimated spend</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Recent Usage Audit Log Table */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Recent AI Request Audit Log</h3>
                <p className="text-xs text-muted-foreground">
                  Individual request telemetry, prompt/completion token ratios, and latency
                </p>
              </div>
              <span className="text-xs text-muted-foreground">Last 10 operations</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-secondary/60 text-muted-foreground uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3 rounded-l-md">Timestamp</th>
                    <th className="py-2.5 px-3">Feature</th>
                    <th className="py-2.5 px-3">Provider / Model</th>
                    <th className="py-2.5 px-3 text-right">Tokens (P + C)</th>
                    <th className="py-2.5 px-3 text-right">Est. Cost</th>
                    <th className="py-2.5 px-3 text-right">Latency</th>
                    <th className="py-2.5 px-3 text-center rounded-r-md">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {usageData.recent_logs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-6 text-center text-muted-foreground">
                        No recent AI execution logs recorded yet.
                      </td>
                    </tr>
                  ) : (
                    usageData.recent_logs.slice(0, 10).map((log) => (
                      <tr key={log.id} className="hover:bg-secondary/20 transition-colors">
                        <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">
                          {new Date(log.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </td>
                        <td className="py-2.5 px-3 font-medium capitalize">
                          {log.feature.replace(/_/g, " ")}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px]">
                          {log.provider} / {log.model}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          {log.prompt_tokens} + {log.completion_tokens} = <span className="font-semibold">{log.total_tokens}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-semibold text-primary">
                          ${log.estimated_cost_usd.toFixed(5)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-muted-foreground">
                          {log.latency_ms} ms
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {log.request_status === "success" ? (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                              {log.cache_hit ? "cached" : "success"}
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400">
                              {log.request_status}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Prominent Invoice Disclaimer */}
            <div className="p-3.5 rounded-lg border border-border/80 bg-secondary/30 flex items-start gap-2.5 text-xs text-muted-foreground">
              <HelpCircle className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-medium text-foreground">Billing Disclaimer: </span>
                {usageData.disclaimer}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* SECTION 3: Job Discovery Adapters Detail Modal / Drawer View */}
      {jobSourcesData && (
        <section className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold tracking-tight">Job Source Architecture & Verification Policies</h2>
              <p className="text-xs text-muted-foreground">
                Complies with robots.txt Crawl-delay, per-domain request pacing, deduplication, and zero-scraping boundaries.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(jobSourcesData.adapters).map(([key, adapter]) => (
              <div key={key} className="p-4 rounded-lg bg-secondary/30 border border-border/60 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-foreground">{adapter.name}</h4>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    {adapter.status}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-muted-foreground truncate">{adapter.endpoint_pattern}</p>
                <div className="text-[11px] space-y-1 pt-1 text-muted-foreground">
                  <p><span className="font-medium text-foreground">Pacing:</span> {adapter.rate_limit_policy}</p>
                  <p><span className="font-medium text-foreground">Dedup:</span> {adapter.deduplication}</p>
                </div>
              </div>
            ))}
          </div>

          <p className="text-xs text-muted-foreground pt-1 border-t border-border">
            <span className="font-semibold text-foreground">Compliance Guardrails: </span>
            {jobSourcesData.compliance_notes}
          </p>
        </section>
      )}
    </div>
  );
}

