"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Compass,
  Database,
  ExternalLink,
  Filter,
  Globe,
  Layers,
  Loader2,
  MapPin,
  Play,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Tag,
  Trash2,
  X,
} from "lucide-react";

import { NotificationBell } from "@/components/NotificationBell";
import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  CompanyListResponse,
  discoveryApi,
  DiscoveryOverview,
  DiscoveryScanLogItem,
  DiscoverySource,
  JobListResponse,
  Job,
} from "@/lib/api";

type ActiveTab = "jobs" | "sources" | "logs";

export default function DiscoveryPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>("jobs");

  // Overview stats
  const [overview, setOverview] = useState<DiscoveryOverview | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);

  // Sources
  const [sources, setSources] = useState<DiscoverySource[]>([]);
  const [loadingSources, setLoadingSources] = useState(false);

  // Discovered Jobs
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRoleFamily, setSelectedRoleFamily] = useState("all");
  const [selectedSeniority, setSelectedSeniority] = useState("all");

  // Scan Logs
  const [logs, setLogs] = useState<DiscoveryScanLogItem[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Companies for Add Source modal
  const [companies, setCompanies] = useState<{ id: string; name: string }[]>([]);

  // Modals & Actions
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<DiscoverySource | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  // Add/Edit Source Form State
  const [formCompanyId, setFormCompanyId] = useState("");
  const [formSourceName, setFormSourceName] = useState("");
  const [formAdapterName, setFormAdapterName] = useState("greenhouse");
  const [formBoardToken, setFormBoardToken] = useState("");
  const [formSourceUrl, setFormSourceUrl] = useState("");
  const [formScanFrequency, setFormScanFrequency] = useState(24);
  const [formIsEnabled, setFormIsEnabled] = useState(true);
  const [formSaving, setFormSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Test Source State
  const [testingSource, setTestingSource] = useState(false);
  const [testResult, setTestResult] = useState<{
    is_success: boolean;
    message: string;
    jobs_detected: number;
    sample_jobs: any[];
  } | null>(null);

  // Triggering Scans
  const [scanningSourceId, setScanningSourceId] = useState<string | null>(null);
  const [batchScanning, setBatchScanning] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch Overview Stats
  const loadOverview = useCallback(async () => {
    try {
      const data = await discoveryApi.getOverview();
      setOverview(data);
    } catch (err: any) {
      console.error("Failed to load discovery overview:", err);
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  // Fetch Sources
  const loadSources = useCallback(async () => {
    setLoadingSources(true);
    try {
      const res = await discoveryApi.listSources({ limit: 100 });
      setSources(res.items);
    } catch (err: any) {
      console.error("Failed to load discovery sources:", err);
    } finally {
      setLoadingSources(false);
    }
  }, []);

  // Fetch Discovered Jobs
  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const params = new URLSearchParams();
      params.append("per_page", "30");
      if (searchQuery.trim()) params.append("search", searchQuery.trim());
      if (selectedRoleFamily !== "all") params.append("role_family", selectedRoleFamily);
      if (selectedSeniority !== "all") params.append("seniority_level", selectedSeniority);

      const res = await apiClient<JobListResponse>(`/jobs?${params.toString()}`);
      setJobs(res.items);
      setTotalJobs(res.total);
    } catch (err: any) {
      console.error("Failed to load discovered jobs:", err);
    } finally {
      setLoadingJobs(false);
    }
  }, [searchQuery, selectedRoleFamily, selectedSeniority]);

  // Fetch Scan Logs
  const loadLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const res = await discoveryApi.getLogs({ limit: 50 });
      setLogs(res.items);
    } catch (err: any) {
      console.error("Failed to load discovery logs:", err);
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  // Initial Load
  useEffect(() => {
    loadOverview();
    loadSources();
    loadJobs();
    loadLogs();

    // Load companies for the modal
    apiClient<CompanyListResponse>("/companies?per_page=100")
      .then((res) => {
        setCompanies(res.items.map((c) => ({ id: c.id, name: c.name })));
      })
      .catch((e) => console.error("Failed to load companies:", e));
  }, [loadOverview, loadSources, loadJobs, loadLogs]);

  // Filter effect for Jobs
  useEffect(() => {
    const timer = setTimeout(() => {
      loadJobs();
    }, 300);
    return () => clearTimeout(timer);
  }, [loadJobs]);

  // Handle Manual Scan of a Single Source
  const handleScanSource = async (sourceId: string) => {
    setScanningSourceId(sourceId);
    setActionMessage(null);
    try {
      const res = await discoveryApi.scanSource(sourceId);
      setActionMessage({
        type: res.status === "success" ? "success" : "error",
        text: res.message,
      });
      await loadSources();
      await loadOverview();
      await loadJobs();
      await loadLogs();
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: err.message || "Failed to scan source.",
      });
    } finally {
      setScanningSourceId(null);
    }
  };

  // Handle Batch Scan
  const handleScanAll = async () => {
    setBatchScanning(true);
    setActionMessage(null);
    try {
      const res = await discoveryApi.scanAll(false);
      setActionMessage({
        type: res.failed_sources === 0 ? "success" : "error",
        text: `Batch scan complete: ${res.total_jobs_imported} new jobs, ${res.total_jobs_updated} updated across ${res.sources_scanned} sources (${res.failed_sources} failed).`,
      });
      await loadSources();
      await loadOverview();
      await loadJobs();
      await loadLogs();
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: err.message || "Failed to trigger batch discovery scan.",
      });
    } finally {
      setBatchScanning(false);
    }
  };

  // Handle Testing a Source
  const handleTestSource = async () => {
    setTestingSource(true);
    setTestResult(null);
    setFormError(null);
    try {
      const res = await discoveryApi.testSource({
        adapter_name: formAdapterName,
        source_url: formSourceUrl.trim() || undefined,
        board_token: formBoardToken.trim() || undefined,
      });
      setTestResult(res);
    } catch (err: any) {
      setFormError(err.message || "Connection test failed.");
    } finally {
      setTestingSource(false);
    }
  };

  // Open Add Modal
  const openAddModal = () => {
    setEditingSource(null);
    setFormCompanyId(companies[0]?.id || "");
    setFormSourceName("");
    setFormAdapterName("greenhouse");
    setFormBoardToken("");
    setFormSourceUrl("");
    setFormScanFrequency(24);
    setFormIsEnabled(true);
    setFormError(null);
    setTestResult(null);
    setIsAddModalOpen(true);
  };

  // Open Edit Modal
  const openEditModal = (src: DiscoverySource) => {
    setEditingSource(src);
    setFormCompanyId(src.company_id);
    setFormSourceName(src.source_name);
    setFormAdapterName(src.adapter_name || "greenhouse");
    setFormBoardToken(src.board_token || "");
    setFormSourceUrl(src.source_url || "");
    setFormScanFrequency(src.scan_frequency_hours);
    setFormIsEnabled(src.is_enabled);
    setFormError(null);
    setTestResult(null);
    setIsAddModalOpen(true);
  };

  // Save Source (Create or Update)
  const handleSaveSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formSourceName.trim()) {
      setFormError("Source name is required.");
      return;
    }
    if (!formCompanyId) {
      setFormError("Associated company is required.");
      return;
    }
    if (!formBoardToken.trim() && !formSourceUrl.trim()) {
      setFormError("Either board token/slug or source URL is required.");
      return;
    }

    setFormSaving(true);
    setFormError(null);
    try {
      if (editingSource) {
        await discoveryApi.updateSource(editingSource.id, {
          source_name: formSourceName.trim(),
          adapter_name: formAdapterName,
          board_token: formBoardToken.trim() || undefined,
          source_url: formSourceUrl.trim() || undefined,
          scan_frequency_hours: formScanFrequency,
          is_enabled: formIsEnabled,
        });
      } else {
        await discoveryApi.createSource({
          company_id: formCompanyId,
          source_name: formSourceName.trim(),
          source_type: "careers_page",
          adapter_name: formAdapterName,
          board_token: formBoardToken.trim() || undefined,
          source_url: formSourceUrl.trim() || undefined,
          scan_frequency_hours: formScanFrequency,
          is_enabled: formIsEnabled,
        });
      }
      setIsAddModalOpen(false);
      await loadSources();
      await loadOverview();
    } catch (err: any) {
      setFormError(err.message || "Failed to save discovery source.");
    } finally {
      setFormSaving(false);
    }
  };

  // Toggle Source Enabled/Disabled
  const handleToggleSourceEnabled = async (src: DiscoverySource) => {
    try {
      await discoveryApi.updateSource(src.id, { is_enabled: !src.is_enabled });
      await loadSources();
      await loadOverview();
    } catch (err: any) {
      console.error("Failed to toggle source:", err);
    }
  };

  // Delete Source
  const handleDeleteSource = async (id: string) => {
    if (!confirm("Are you sure you want to remove this discovery source?")) return;
    try {
      await discoveryApi.deleteSource(id);
      await loadSources();
      await loadOverview();
    } catch (err: any) {
      console.error("Failed to delete source:", err);
    }
  };

  const getAdapterBadgeColor = (adapter?: string | null) => {
    switch (adapter) {
      case "greenhouse":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
      case "lever":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
      case "ashby":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      case "rss_feed":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "json_feed":
        return "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20";
      default:
        return "bg-muted text-muted-foreground border-border";
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground pb-16">
      {/* Top Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Dashboard
            </Link>
            <span className="text-border">/</span>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                <Compass className="w-5 h-5" />
              </div>
              <h1 className="text-lg font-bold">Automated Job Discovery</h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleScanAll}
              disabled={batchScanning}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium border border-border bg-card hover:bg-secondary transition-colors disabled:opacity-50"
            >
              {batchScanning ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              Scan All Sources
            </button>

            <button
              onClick={openAddModal}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" /> Add Source
            </button>

            <NotificationBell />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Action Banner */}
        {actionMessage && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between text-sm ${
              actionMessage.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
                : "bg-destructive/10 border-destructive/30 text-destructive"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {actionMessage.type === "success" ? (
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
              )}
              <span>{actionMessage.text}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-muted-foreground hover:text-foreground p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Discovery Overview KPI Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-4 rounded-xl border border-border bg-card">
            <p className="text-xs font-medium text-muted-foreground">Active Sources</p>
            <p className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">
              {loadingOverview ? "..." : `${overview?.total_active_sources || 0} / ${overview?.total_sources || 0}`}
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <p className="text-xs font-medium text-muted-foreground">Sources Scanned</p>
            <p className="text-2xl font-bold mt-1 text-foreground">
              {loadingOverview ? "..." : overview?.sources_scanned || 0}
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <p className="text-xs font-medium text-muted-foreground">Jobs Discovered</p>
            <p className="text-2xl font-bold mt-1 text-primary">
              {loadingOverview ? "..." : overview?.new_jobs_discovered || 0}
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <p className="text-xs font-medium text-muted-foreground">Jobs Updated</p>
            <p className="text-2xl font-bold mt-1 text-blue-600 dark:text-blue-400">
              {loadingOverview ? "..." : overview?.updated_jobs || 0}
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <p className="text-xs font-medium text-muted-foreground">Failed Scans</p>
            <p className="text-2xl font-bold mt-1 text-destructive">
              {loadingOverview ? "..." : overview?.failed_source_scans || 0}
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card">
            <p className="text-xs font-medium text-muted-foreground">Last Run</p>
            <p className="text-xs font-semibold mt-2 text-foreground truncate">
              {loadingOverview
                ? "..."
                : overview?.last_discovery_run
                ? new Date(overview.last_discovery_run).toLocaleDateString([], {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "Never"}
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="border-b border-border flex items-center justify-between">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab("jobs")}
              className={`pb-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                activeTab === "jobs"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Briefcase className="w-4 h-4" /> Discovered Opportunities
              <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs bg-secondary text-secondary-foreground">
                {totalJobs}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("sources")}
              className={`pb-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                activeTab === "sources"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Server className="w-4 h-4" /> Source Integrations
              <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs bg-secondary text-secondary-foreground">
                {sources.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("logs")}
              className={`pb-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                activeTab === "logs"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Clock className="w-4 h-4" /> Scan History & Audit
            </button>
          </nav>

          <Link
            href="/dashboard/jobs"
            className="text-xs text-primary hover:underline inline-flex items-center gap-1 mb-3"
          >
            Manage Ingested Jobs in Job Catalog <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* TAB 1: DISCOVERED JOBS */}
        {activeTab === "jobs" && (
          <div className="space-y-6">
            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search by job title, skill, or keyword..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <select
                value={selectedRoleFamily}
                onChange={(e) => setSelectedRoleFamily(e.target.value)}
                className="px-3 py-2 bg-card border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">All Role Families</option>
                <option value="AI Engineer">AI Engineer</option>
                <option value="Machine Learning Engineer">Machine Learning Engineer</option>
                <option value="Generative AI / LLM Engineer">Generative AI / LLM Engineer</option>
                <option value="Python Backend Developer">Python Backend Developer</option>
                <option value="Frontend Developer">Frontend Developer</option>
                <option value="Full Stack Developer">Full Stack Developer</option>
                <option value="Software Development Engineer">Software Development Engineer</option>
                <option value="Data Analyst">Data Analyst</option>
                <option value="Data Engineer">Data Engineer</option>
                <option value="Automation Engineer">Automation Engineer</option>
              </select>

              <select
                value={selectedSeniority}
                onChange={(e) => setSelectedSeniority(e.target.value)}
                className="px-3 py-2 bg-card border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">All Seniority</option>
                <option value="internship">Internship / Co-op</option>
                <option value="entry_level">Fresher / Entry-Level</option>
                <option value="junior">Junior Developer</option>
                <option value="mid_level">Mid-Level</option>
              </select>
            </div>

            {/* Jobs List */}
            {loadingJobs ? (
              <div className="py-20 text-center text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary mb-3" />
                <p>Loading discovered opportunities...</p>
              </div>
            ) : jobs.length === 0 ? (
              <div className="py-16 text-center border border-dashed border-border rounded-xl bg-card/40 p-8">
                <Compass className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <h3 className="text-base font-semibold">No opportunities found</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                  Add career sources or click &quot;Scan All Sources&quot; to fetch fresh opportunities from official Greenhouse, Lever, Ashby, or RSS feeds.
                </p>
                <button
                  onClick={openAddModal}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  <Plus className="w-4 h-4" /> Add Discovery Source
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {jobs.map((j) => (
                  <div
                    key={j.id}
                    className="p-5 rounded-xl border border-border bg-card hover:border-primary/40 hover:shadow-md transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                          {j.role_family || "Technical"}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                          {j.verification_status || "corroborated"}
                        </span>
                      </div>

                      <h3 className="text-base font-semibold text-foreground line-clamp-1 hover:text-primary transition-colors">
                        {j.title}
                      </h3>

                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                        <Building2 className="w-3.5 h-3.5" />
                        <span className="font-medium text-foreground">{j.company_name || "Official Career Board"}</span>
                        <span>•</span>
                        <span className="capitalize">{j.work_arrangement}</span>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-2">
                        <MapPin className="w-3.5 h-3.5" />
                        <span className="truncate">{j.location_text || "Flexible"}</span>
                      </div>

                      {/* Explicit Salary if present */}
                      {(j.salary_min || j.salary_max) && (
                        <div className="mt-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                          {j.salary_currency || "INR"}{" "}
                          {j.salary_min ? j.salary_min.toLocaleString() : ""}{" "}
                          {j.salary_max ? `- ${j.salary_max.toLocaleString()}` : ""}{" "}
                          /{j.salary_period || "yr"}
                        </div>
                      )}

                      {/* Skills Tags */}
                      {j.skills_tags && j.skills_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {j.skills_tags.slice(0, 4).map((s) => (
                            <span
                              key={s}
                              className="px-2 py-0.5 rounded text-[10px] bg-secondary text-secondary-foreground"
                            >
                              {s}
                            </span>
                          ))}
                          {j.skills_tags.length > 4 && (
                            <span className="text-[10px] text-muted-foreground self-center">
                              +{j.skills_tags.length - 4}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="pt-4 mt-4 border-t border-border flex items-center justify-between">
                      <button
                        onClick={() => setSelectedJob(j)}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        View Details
                      </button>

                      <a
                        href={j.job_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        Apply <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: SOURCE INTEGRATIONS */}
        {activeTab === "sources" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold">Configured Discovery Sources</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Manage career ATS boards (Greenhouse, Lever, Ashby) and RSS/JSON feeds scanned periodically.
                </p>
              </div>
              <button
                onClick={openAddModal}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" /> Add New Source
              </button>
            </div>

            {loadingSources ? (
              <div className="py-20 text-center text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary mb-3" />
                <p>Loading configured sources...</p>
              </div>
            ) : sources.length === 0 ? (
              <div className="py-16 text-center border border-dashed border-border rounded-xl bg-card/40 p-8">
                <Server className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <h3 className="text-base font-semibold">No discovery sources configured</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                  Add a company&apos;s Greenhouse, Lever, Ashby, or RSS feed to automatically discover fresh career opportunities.
                </p>
                <button
                  onClick={openAddModal}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  <Plus className="w-4 h-4" /> Add First Source
                </button>
              </div>
            ) : (
              <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
                <table className="min-w-full divide-y divide-border text-left">
                  <thead className="bg-muted/40 text-xs font-medium text-muted-foreground">
                    <tr>
                      <th className="px-6 py-3">Source & Company</th>
                      <th className="px-6 py-3">Adapter / Type</th>
                      <th className="px-6 py-3">Scan Cadence</th>
                      <th className="px-6 py-3">Last Scan</th>
                      <th className="px-6 py-3">Jobs Discovered</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-xs">
                    {sources.map((src) => (
                      <tr key={src.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-6 py-4">
                          <p className="font-semibold text-foreground text-sm">{src.source_name}</p>
                          <p className="text-muted-foreground text-xs mt-0.5">
                            {src.company_name || "Company Record"}
                          </p>
                          {src.board_token && (
                            <span className="font-mono text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded mt-1 inline-block">
                              token: {src.board_token}
                            </span>
                          )}
                        </td>

                        <td className="px-6 py-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${getAdapterBadgeColor(
                              src.adapter_name
                            )}`}
                          >
                            {src.adapter_name || "manual"}
                          </span>
                        </td>

                        <td className="px-6 py-4 text-muted-foreground">
                          Every {src.scan_frequency_hours}h
                        </td>

                        <td className="px-6 py-4">
                          <p className="text-foreground font-medium">
                            {src.last_successful_scan_at
                              ? new Date(src.last_successful_scan_at).toLocaleDateString([], {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "Never"}
                          </p>
                          {src.last_scan_message && (
                            <p className="text-[11px] text-muted-foreground truncate max-w-xs mt-0.5">
                              {src.last_scan_message}
                            </p>
                          )}
                        </td>

                        <td className="px-6 py-4">
                          <span className="font-semibold text-primary">
                            {src.jobs_discovered_count}
                          </span>{" "}
                          jobs
                          {src.error_count > 0 && (
                            <span className="ml-2 text-destructive font-semibold">
                              ({src.error_count} err)
                            </span>
                          )}
                        </td>

                        <td className="px-6 py-4">
                          <button
                            onClick={() => handleToggleSourceEnabled(src)}
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition-colors ${
                              src.is_enabled
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                                : "bg-muted text-muted-foreground border-border"
                            }`}
                          >
                            {src.is_enabled ? "Enabled" : "Disabled"}
                          </button>
                        </td>

                        <td className="px-6 py-4 text-right space-x-2">
                          <button
                            onClick={() => handleScanSource(src.id)}
                            disabled={scanningSourceId === src.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-secondary hover:bg-secondary/80 text-secondary-foreground font-medium transition-colors disabled:opacity-50"
                          >
                            {scanningSourceId === src.id ? (
                              <Loader2 className="w-3 h-3 animate-spin text-primary" />
                            ) : (
                              <Play className="w-3 h-3" />
                            )}
                            Scan Now
                          </button>

                          <button
                            onClick={() => openEditModal(src)}
                            className="px-2 py-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground font-medium"
                          >
                            Edit
                          </button>

                          <button
                            onClick={() => handleDeleteSource(src.id)}
                            className="px-2 py-1 rounded hover:bg-destructive/10 text-destructive font-medium"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: SCAN HISTORY & AUDIT LOGS */}
        {activeTab === "logs" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold">Discovery Execution History</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Chronological audit records tracking every automated and manual discovery scan.
                </p>
              </div>
              <button
                onClick={loadLogs}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-card hover:bg-secondary transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh Logs
              </button>
            </div>

            {loadingLogs ? (
              <div className="py-20 text-center text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary mb-3" />
                <p>Loading execution history...</p>
              </div>
            ) : logs.length === 0 ? (
              <div className="py-16 text-center border border-dashed border-border rounded-xl bg-card/40 p-8">
                <Clock className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <h3 className="text-base font-semibold">No scan logs recorded yet</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                  Scan logs will automatically populate as Celery background workers and manual scans execute.
                </p>
              </div>
            ) : (
              <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
                <table className="min-w-full divide-y divide-border text-left">
                  <thead className="bg-muted/40 text-xs font-medium text-muted-foreground">
                    <tr>
                      <th className="px-6 py-3">Scan Time</th>
                      <th className="px-6 py-3">Company / Source</th>
                      <th className="px-6 py-3">Adapter</th>
                      <th className="px-6 py-3">Type</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Results</th>
                      <th className="px-6 py-3">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-xs">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                          {new Date(log.started_at).toLocaleString([], {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </td>

                        <td className="px-6 py-3">
                          <p className="font-semibold text-foreground">
                            {log.company_name || "Company Discovery"}
                          </p>
                        </td>

                        <td className="px-6 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${getAdapterBadgeColor(
                              log.adapter_name
                            )}`}
                          >
                            {log.adapter_name}
                          </span>
                        </td>

                        <td className="px-6 py-3 text-muted-foreground capitalize">
                          {log.scan_type}
                        </td>

                        <td className="px-6 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              log.status === "success"
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                                : "bg-destructive/10 text-destructive border-destructive/30"
                            }`}
                          >
                            {log.status.toUpperCase()}
                          </span>
                        </td>

                        <td className="px-6 py-3">
                          {log.status === "success" ? (
                            <span>
                              <strong className="text-foreground">{log.jobs_found}</strong> found (
                              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                +{log.jobs_imported} new
                              </span>
                              , {log.jobs_updated} updated)
                            </span>
                          ) : (
                            <span className="text-destructive truncate max-w-xs inline-block">
                              {log.error_message || "Scan error"}
                            </span>
                          )}
                        </td>

                        <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                          {log.duration_seconds ? `${log.duration_seconds}s` : "<1s"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      {/* MODAL: ADD / EDIT SOURCE */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-primary" />
                <h3 className="text-base font-semibold">
                  {editingSource ? "Edit Discovery Source" : "Configure Discovery Source"}
                </h3>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSource} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Company Selection */}
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
                  Associated Company <span className="text-destructive">*</span>
                </label>
                <select
                  value={formCompanyId}
                  onChange={(e) => setFormCompanyId(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                >
                  <option value="">Select a company...</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Source Name */}
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
                  Source Name <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Stripe Official Careers (Greenhouse)"
                  value={formSourceName}
                  onChange={(e) => setFormSourceName(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>

              {/* Adapter Type */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Source Adapter <span className="text-destructive">*</span>
                  </label>
                  <select
                    value={formAdapterName}
                    onChange={(e) => setFormAdapterName(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="greenhouse">Greenhouse Job Board</option>
                    <option value="lever">Lever Job Postings</option>
                    <option value="ashby">Ashby Job Board</option>
                    <option value="rss_feed">RSS / Atom XML Feed</option>
                    <option value="json_feed">Custom JSON Job Feed</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Scan Cadence
                  </label>
                  <select
                    value={formScanFrequency}
                    onChange={(e) => setFormScanFrequency(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value={6}>Every 6 Hours</option>
                    <option value={12}>Every 12 Hours</option>
                    <option value={24}>Every 24 Hours (Daily)</option>
                    <option value={48}>Every 48 Hours</option>
                    <option value={168}>Once a Week</option>
                  </select>
                </div>
              </div>

              {/* Dynamic Tokens/URLs depending on adapter */}
              {formAdapterName === "greenhouse" && (
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Greenhouse Board Token or URL <span className="text-destructive">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 'stripe' or 'https://boards.greenhouse.io/stripe'"
                    value={formBoardToken}
                    onChange={(e) => setFormBoardToken(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Official Greenhouse boards-api endpoint will query public job listings with full content.
                  </p>
                </div>
              )}

              {formAdapterName === "lever" && (
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Lever Site Slug or URL <span className="text-destructive">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 'netflix' or 'https://jobs.lever.co/netflix'"
                    value={formBoardToken}
                    onChange={(e) => setFormBoardToken(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Public Lever API query extracts postings, categories, and descriptions.
                  </p>
                </div>
              )}

              {formAdapterName === "ashby" && (
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Ashby Board Name or URL <span className="text-destructive">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 'linear' or 'https://jobs.ashbyhq.com/linear'"
                    value={formBoardToken}
                    onChange={(e) => setFormBoardToken(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Official Ashby posting-api endpoint retrieves listings with compensation tiers.
                  </p>
                </div>
              )}

              {(formAdapterName === "rss_feed" || formAdapterName === "json_feed") && (
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Feed Endpoint URL <span className="text-destructive">*</span>
                  </label>
                  <input
                    type="url"
                    placeholder="https://example.com/careers/rss.xml"
                    value={formSourceUrl}
                    onChange={(e) => setFormSourceUrl(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Outbound HTTP queries apply SSRF protection and connection-time host validation.
                  </p>
                </div>
              )}

              {/* Active Toggle */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="isEnabled"
                  checked={formIsEnabled}
                  onChange={(e) => setFormIsEnabled(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <label htmlFor="isEnabled" className="text-xs font-medium text-foreground cursor-pointer">
                  Enable automated recurring scanning for this source
                </label>
              </div>

              {/* Test Connection Button & Preview Box */}
              <div className="pt-2 border-t border-border">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Test connectivity before saving:</span>
                  <button
                    type="button"
                    onClick={handleTestSource}
                    disabled={testingSource}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    {testingSource ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                    ) : (
                      <Play className="w-3.5 h-3.5" />
                    )}
                    Test Connection
                  </button>
                </div>

                {testResult && (
                  <div
                    className={`mt-3 p-3 rounded-lg border text-xs ${
                      testResult.is_success
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
                        : "bg-destructive/10 border-destructive/30 text-destructive"
                    }`}
                  >
                    <div className="flex items-center gap-2 font-semibold">
                      {testResult.is_success ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : (
                        <AlertCircle className="w-4 h-4" />
                      )}
                      <span>
                        {testResult.message} ({testResult.jobs_detected} opportunities detected)
                      </span>
                    </div>

                    {testResult.sample_jobs && testResult.sample_jobs.length > 0 && (
                      <div className="mt-2 space-y-1 pl-6">
                        <p className="text-[11px] font-semibold text-foreground">Sample Opportunities:</p>
                        {testResult.sample_jobs.map((s, idx) => (
                          <p key={idx} className="text-[11px] text-muted-foreground truncate">
                            • {s.title} ({s.location || "Flexible"})
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium border border-border text-foreground hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
                >
                  {formSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {editingSource ? "Update Source" : "Save Source"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: JOB DETAILS PREVIEW */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-card border border-border rounded-xl shadow-xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-primary" />
                <h3 className="text-base font-semibold">Job Opportunity Details</h3>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                  {selectedJob.role_family || "Technical"}
                </span>
                <h2 className="text-xl font-bold text-foreground mt-2">{selectedJob.title}</h2>
                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mt-2">
                  <span className="font-semibold text-foreground">
                    {selectedJob.company_name || "Direct Company Listing"}
                  </span>
                  <span>•</span>
                  <span>{selectedJob.location_text || "Flexible"}</span>
                  <span>•</span>
                  <span className="capitalize">{selectedJob.work_arrangement}</span>
                  <span>•</span>
                  <span className="capitalize">{selectedJob.employment_type || "Full-time"}</span>
                </div>
              </div>

              {/* Skills Tags */}
              {selectedJob.skills_tags && selectedJob.skills_tags.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2">
                    Extracted Skill Requirements
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedJob.skills_tags.map((s) => (
                      <span
                        key={s}
                        className="px-2.5 py-1 rounded text-xs bg-secondary text-secondary-foreground font-medium"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              <div>
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2">
                  Job Description
                </h4>
                <div className="text-xs text-muted-foreground whitespace-pre-line leading-relaxed bg-muted/20 p-4 rounded-lg border border-border">
                  {selectedJob.description}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-border flex items-center justify-between bg-muted/20">
              <Link
                href="/dashboard/jobs"
                className="text-xs text-primary hover:underline font-medium"
              >
                Open in Full Job Catalog →
              </Link>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedJob(null)}
                  className="px-4 py-2 rounded-lg text-xs font-medium border border-border text-foreground hover:bg-secondary transition-colors"
                >
                  Close
                </button>
                <a
                  href={selectedJob.job_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
                >
                  Visit Original Listing <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

