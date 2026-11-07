"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  Brain,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  FileCheck,
  FileText,
  Filter,
  Globe,
  HelpCircle,
  Layers,
  Lightbulb,
  ListFilter,
  Loader2,
  MapPin,
  MessageSquare,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  Terminal,
  Trash2,
  TrendingUp,
  Users,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  Company,
  CompanyCategory,
  companyIntelligenceApi,
  CompanyFitAssessmentResponse,
  CompanyIntelligenceResponse,
  CompanyResearchReportResponse,
  CompanyResearchSourceResponse,
  TechnologyItemSchema,
} from "@/lib/api";

export default function CompanyIntelligencePage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Loading Company Intelligence Workspace...</p>
        </div>
      }
    >
      <CompanyIntelligenceContent />
    </React.Suspense>
  );
}

function CompanyIntelligenceContent() {
  const { user, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const initialCompanyId = searchParams.get("company_id");

  // Companies list state
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(initialCompanyId);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [loadingCompanies, setLoadingCompanies] = useState(false);

  // Active Company Intelligence State
  const [intelligence, setIntelligence] = useState<CompanyIntelligenceResponse | null>(null);
  const [loadingIntelligence, setLoadingIntelligence] = useState(false);
  const [fitAssessment, setFitAssessment] = useState<CompanyFitAssessmentResponse | null>(null);
  const [loadingFit, setLoadingFit] = useState(false);
  const [sources, setSources] = useState<CompanyResearchSourceResponse[]>([]);
  const [loadingSources, setLoadingSources] = useState(false);

  // Active Report State
  const [currentReport, setCurrentReport] = useState<CompanyResearchReportResponse | null>(null);
  const [savedReports, setSavedReports] = useState<CompanyResearchReportResponse[]>([]);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [forceRefreshReport, setForceRefreshReport] = useState(false);

  // Navigation tab
  const [activeTab, setActiveTab] = useState<
    "overview" | "technology" | "hiring" | "fit" | "report" | "sources"
  >("overview");

  // UI helpers
  const [techFilterStrength, setTechFilterStrength] = useState<string>("all");
  const [activeTechModal, setActiveTechModal] = useState<TechnologyItemSchema | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);

  // Fetch Companies
  const loadCompanies = useCallback(async () => {
    try {
      setLoadingCompanies(true);
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append("search", searchQuery.trim());
      if (selectedCategory && selectedCategory !== "all") params.append("category", selectedCategory);
      params.append("per_page", "50");

      const res = await apiClient<{ items: Company[]; total: number }>(`/companies?${params.toString()}`);
      setCompanies(res.items || []);

      // If initial company not selected or missing, default to first
      if (!selectedCompanyId && res.items.length > 0) {
        setSelectedCompanyId(res.items[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch companies:", err);
    } finally {
      setLoadingCompanies(false);
    }
  }, [searchQuery, selectedCategory, selectedCompanyId]);

  useEffect(() => {
    if (user && !authLoading) {
      loadCompanies();
    }
  }, [user, authLoading, loadCompanies]);

  // Fetch details for selected company
  const loadCompanyDetails = useCallback(async (companyId: string, refresh = false) => {
    try {
      setLoadingIntelligence(true);
      setLoadingFit(true);
      setLoadingSources(true);

      const [intelData, fitData, srcData, reportsData] = await Promise.allSettled([
        companyIntelligenceApi.getIntelligence(companyId, refresh),
        companyIntelligenceApi.getFit(companyId),
        companyIntelligenceApi.getSources(companyId),
        companyIntelligenceApi.listCompanyReports(companyId),
      ]);

      if (intelData.status === "fulfilled") {
        setIntelligence(intelData.value);
      }
      if (fitData.status === "fulfilled") {
        setFitAssessment(fitData.value);
      }
      if (srcData.status === "fulfilled") {
        setSources(srcData.value);
      }
      if (reportsData.status === "fulfilled") {
        setSavedReports(reportsData.value);
        if (reportsData.value.length > 0) {
          setCurrentReport(reportsData.value[0]);
        } else {
          setCurrentReport(null);
        }
      }
    } catch (err) {
      console.error("Failed to load company intelligence data:", err);
    } finally {
      setLoadingIntelligence(false);
      setLoadingFit(false);
      setLoadingSources(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCompanyId) {
      loadCompanyDetails(selectedCompanyId);
    }
  }, [selectedCompanyId, loadCompanyDetails]);

  // Handle report generation
  const handleGenerateReport = async () => {
    if (!selectedCompanyId) return;
    try {
      setGeneratingReport(true);
      const report = await companyIntelligenceApi.generateReport(selectedCompanyId, {
        force_refresh: forceRefreshReport,
        focus_areas: ["technology_landscape", "engineering_culture", "candidate_alignment"],
      });
      setCurrentReport(report);
      setSavedReports((prev) => [report, ...prev.filter((r) => r.id !== report.id)]);
      setActiveTab("report");
    } catch (err) {
      console.error("Report generation failed:", err);
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleCopyReportMarkdown = () => {
    if (!currentReport) return;
    const lines: string[] = [
      `# ${currentReport.report_title}`,
      `**Company:** ${currentReport.company_name}`,
      `**Generated:** ${new Date(currentReport.created_at).toLocaleString()}`,
      `**Provider:** ${currentReport.provider} (${currentReport.model})`,
      `---`,
      "",
    ];

    Object.values(currentReport.sections || {}).forEach((s) => {
      lines.push(`## ${s.title}`);
      lines.push(s.content);
      lines.push("");
      if (s.bullet_points && s.bullet_points.length > 0) {
        s.bullet_points.forEach((b) => lines.push(`* ${b}`));
        lines.push("");
      }
    });

    navigator.clipboard.writeText(lines.join("\n"));
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2500);
  };

  const handleDeleteReport = async (reportId: string) => {
    if (!window.confirm("Are you sure you want to delete this research report?")) return;
    try {
      await companyIntelligenceApi.deleteReport(reportId);
      setCurrentReport(null);
      setSavedReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err) {
      console.error("Failed to delete report:", err);
    }
  };

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId);

  // Filter tech stack by evidence strength
  const filteredTechStack = (intelligence?.technology_stack || []).filter((t) => {
    if (techFilterStrength === "all") return true;
    return t.evidence_strength === techFilterStrength;
  });

  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border/40">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" /> Evidence-Grounded Research
            </span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-secondary text-muted-foreground">
              Module 17
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground flex items-center gap-2">
            <Building2 className="w-7 h-7 text-primary" />
            Company Intelligence & Employer Research
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Transparent, evidence-backed company profiles, technology intelligence, and personalized candidate fit.
          </p>
        </div>

        {selectedCompany && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => selectedCompanyId && loadCompanyDetails(selectedCompanyId, true)}
              disabled={loadingIntelligence}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-background hover:bg-muted text-foreground transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingIntelligence ? "animate-spin" : ""}`} />
              Refresh Web Sources
            </button>
            <Link
              href={`/dashboard/interview-prep?company_id=${selectedCompany.id}`}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-primary hover:bg-primary/90 text-primary-foreground transition shadow-sm"
            >
              <Bot className="w-3.5 h-3.5" />
              Interview Prep
            </Link>
          </div>
        )}
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Company Search & Directory (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-card border border-border/60 rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                <Search className="w-4 h-4 text-primary" /> Select Employer
              </h2>
              <span className="text-xs text-muted-foreground">{companies.length} discovered</span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search name or domain..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
              />
            </div>

            {/* Category Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full py-1.5 px-2 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none"
              >
                <option value="all">All Company Categories</option>
                <option value="product_company">Product Companies</option>
                <option value="established_startup">Startups</option>
                <option value="mnc">MNCs</option>
                <option value="gcc">GCCs</option>
                <option value="large_it_services">IT Services</option>
              </select>
            </div>
          </div>

          {/* Companies List */}
          <div className="bg-card border border-border/60 rounded-xl shadow-sm divide-y divide-border/40 max-h-[600px] overflow-y-auto">
            {loadingCompanies ? (
              <div className="p-8 text-center text-sm text-muted-foreground flex flex-col items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                Loading companies...
              </div>
            ) : companies.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                No matching companies found.
              </div>
            ) : (
              companies.map((c) => {
                const isSelected = c.id === selectedCompanyId;
                return (
                  <button
                    key={c.id}
                    onClick={() => setSelectedCompanyId(c.id)}
                    className={`w-full text-left p-3.5 transition flex items-start justify-between gap-3 ${
                      isSelected
                        ? "bg-primary/5 border-l-4 border-l-primary"
                        : "hover:bg-muted/40"
                    }`}
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-semibold text-xs text-foreground truncate">
                          {c.name}
                        </span>
                        {c.verification_status === "verified" && (
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate">
                        {c.normalized_domain || c.website_url || "No web domain"}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                        {c.headquarters_city && (
                          <span className="flex items-center gap-0.5">
                            <MapPin className="w-2.5 h-2.5" /> {c.headquarters_city}
                          </span>
                        )}
                        <span className="capitalize">{c.category.replace(/_/g, " ")}</span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground/60 shrink-0 self-center" />
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Company Intelligence Workspace (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {!selectedCompany ? (
            <div className="bg-card border border-border/60 rounded-xl p-12 text-center text-muted-foreground">
              <Building2 className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <h3 className="font-semibold text-foreground text-base">Select an Employer to View Intelligence</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                Explore transparent technology stack evidence, verified hiring activity from discovered jobs, and candidate fit.
              </p>
            </div>
          ) : (
            <>
              {/* Employer Card Banner */}
              <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-xl font-extrabold text-foreground tracking-tight">
                        {selectedCompany.name}
                      </h2>
                      {selectedCompany.verification_status === "verified" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                          <ShieldCheck className="w-3 h-3" /> Verified Corporate Entity
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20">
                          Unverified Source
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {intelligence?.industry_domain || selectedCompany.category.replace(/_/g, " ")} •{" "}
                      {intelligence?.headquarters || "Global Presence"}
                    </p>
                  </div>

                  {/* Actions / External Links */}
                  <div className="flex items-center gap-2">
                    {selectedCompany.website_url && (
                      <a
                        href={selectedCompany.website_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium border border-border bg-background hover:bg-muted text-foreground transition"
                      >
                        <Globe className="w-3.5 h-3.5 text-muted-foreground" />
                        Website
                        <ExternalLink className="w-3 h-3 text-muted-foreground" />
                      </a>
                    )}
                    {selectedCompany.careers_url && (
                      <a
                        href={selectedCompany.careers_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium border border-border bg-background hover:bg-muted text-foreground transition"
                      >
                        <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                        Careers
                        <ExternalLink className="w-3 h-3 text-muted-foreground" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Quick Meta Pills */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-border/40 text-xs">
                  <div className="bg-secondary/40 rounded-lg p-2.5">
                    <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Active Jobs
                    </span>
                    <p className="text-base font-extrabold text-foreground">
                      {intelligence?.hiring_summary?.total_active_jobs ?? 0}
                    </p>
                  </div>
                  <div className="bg-secondary/40 rounded-lg p-2.5">
                    <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Entry-Level / Intern
                    </span>
                    <p className="text-base font-extrabold text-emerald-500">
                      {(intelligence?.hiring_summary?.entry_level_jobs ?? 0)}
                    </p>
                  </div>
                  <div className="bg-secondary/40 rounded-lg p-2.5">
                    <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Candidate Fit
                    </span>
                    <p className="text-base font-extrabold text-primary">
                      {fitAssessment ? `${fitAssessment.fit_score}%` : "Calculating..."}
                    </p>
                  </div>
                  <div className="bg-secondary/40 rounded-lg p-2.5">
                    <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                      Verified Size
                    </span>
                    <p className="text-xs font-semibold text-foreground truncate">
                      {intelligence?.size_band || "Undisclosed"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex items-center gap-1 overflow-x-auto border-b border-border/40 pb-px text-xs font-medium">
                <button
                  onClick={() => setActiveTab("overview")}
                  className={`px-3 py-2 rounded-t-lg transition flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                    activeTab === "overview"
                      ? "border-primary text-primary font-bold bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5" /> Overview & Offerings
                </button>
                <button
                  onClick={() => setActiveTab("technology")}
                  className={`px-3 py-2 rounded-t-lg transition flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                    activeTab === "technology"
                      ? "border-primary text-primary font-bold bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Terminal className="w-3.5 h-3.5" /> Verified Tech Stack ({intelligence?.technology_stack?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("hiring")}
                  className={`px-3 py-2 rounded-t-lg transition flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                    activeTab === "hiring"
                      ? "border-primary text-primary font-bold bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <TrendingUp className="w-3.5 h-3.5" /> Hiring Trends ({intelligence?.hiring_summary?.total_active_jobs || 0})
                </button>
                <button
                  onClick={() => setActiveTab("fit")}
                  className={`px-3 py-2 rounded-t-lg transition flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                    activeTab === "fit"
                      ? "border-primary text-primary font-bold bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Target className="w-3.5 h-3.5" /> Candidate Fit Assessment
                </button>
                <button
                  onClick={() => setActiveTab("report")}
                  className={`px-3 py-2 rounded-t-lg transition flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                    activeTab === "report"
                      ? "border-primary text-primary font-bold bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" /> AI Research Report
                </button>
                <button
                  onClick={() => setActiveTab("sources")}
                  className={`px-3 py-2 rounded-t-lg transition flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                    activeTab === "sources"
                      ? "border-primary text-primary font-bold bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" /> Public Sources ({sources.length})
                </button>
              </div>

              {/* Tab 1: Overview & Products */}
              {activeTab === "overview" && (
                <div className="space-y-4">
                  {/* Overview Statement */}
                  <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-primary" /> Corporate Overview & Business Domain
                    </h3>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {intelligence?.overview || selectedCompany.description || "No official description indexed."}
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-border/40 text-xs">
                      <div>
                        <span className="text-[11px] font-semibold text-foreground">Operating Locations:</span>
                        <p className="text-muted-foreground mt-0.5">
                          {intelligence?.operating_locations && intelligence.operating_locations.length > 0
                            ? intelligence.operating_locations.join(", ")
                            : intelligence?.headquarters || "Remote / Global"}
                        </p>
                      </div>
                      <div>
                        <span className="text-[11px] font-semibold text-foreground">Funding & Corporate Scale:</span>
                        <p className="text-muted-foreground mt-0.5">
                          {intelligence?.size_band ? `${intelligence.size_band}` : "Undisclosed size"}
                          {intelligence?.size_evidence ? ` (${intelligence.size_evidence})` : ""}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Products & Services */}
                  <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                      <Layers className="w-4 h-4 text-primary" /> Key Products, Services & Platform Capabilities
                    </h3>
                    {intelligence?.products_and_services && intelligence.products_and_services.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {intelligence.products_and_services.map((p, idx) => (
                          <div key={idx} className="bg-secondary/20 border border-border/40 rounded-lg p-3 space-y-1">
                            <span className="font-bold text-xs text-foreground">{p.name}</span>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">{p.description}</p>
                            {p.evidence_source && (
                              <p className="text-[10px] text-muted-foreground/70 italic pt-1 truncate">
                                Source: {p.evidence_source}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">No specific products evidenced from indexed sources.</p>
                    )}
                  </div>

                  {/* Recent Developments / News */}
                  {intelligence?.recent_developments && intelligence.recent_developments.length > 0 && (
                    <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-3">
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-primary" /> Recent Public Developments & Releases
                      </h3>
                      <div className="space-y-2">
                        {intelligence.recent_developments.map((d, idx) => (
                          <div key={idx} className="p-3 bg-secondary/10 border border-border/40 rounded-lg space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-semibold text-foreground">{d.headline}</span>
                              {d.date && <span className="text-[10px] text-muted-foreground">{d.date}</span>}
                            </div>
                            <p className="text-[11px] text-muted-foreground">{d.summary}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Technology Stack & Provenance */}
              {activeTab === "technology" && (
                <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/40">
                    <div>
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-primary" /> Verified Engineering Stack & Evidence Tiers
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Each technology is strictly classified by provenance strength.
                      </p>
                    </div>

                    {/* Filter buttons */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <button
                        onClick={() => setTechFilterStrength("all")}
                        className={`px-2.5 py-1 text-[11px] rounded font-medium transition ${
                          techFilterStrength === "all" ? "bg-primary text-primary-foreground font-semibold" : "bg-muted text-muted-foreground"
                        }`}
                      >
                        All ({intelligence?.technology_stack?.length || 0})
                      </button>
                      <button
                        onClick={() => setTechFilterStrength("confirmed")}
                        className={`px-2.5 py-1 text-[11px] rounded font-medium transition ${
                          techFilterStrength === "confirmed" ? "bg-emerald-500 text-white font-semibold" : "bg-emerald-500/10 text-emerald-600"
                        }`}
                      >
                        Confirmed
                      </button>
                      <button
                        onClick={() => setTechFilterStrength("supported")}
                        className={`px-2.5 py-1 text-[11px] rounded font-medium transition ${
                          techFilterStrength === "supported" ? "bg-blue-500 text-white font-semibold" : "bg-blue-500/10 text-blue-600"
                        }`}
                      >
                        Supported
                      </button>
                      <button
                        onClick={() => setTechFilterStrength("inferred")}
                        className={`px-2.5 py-1 text-[11px] rounded font-medium transition ${
                          techFilterStrength === "inferred" ? "bg-purple-500 text-white font-semibold" : "bg-purple-500/10 text-purple-600"
                        }`}
                      >
                        Inferred
                      </button>
                    </div>
                  </div>

                  {filteredTechStack.length === 0 ? (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      No technologies detected under selected filter.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {filteredTechStack.map((tech, idx) => {
                        const badgeColors = {
                          confirmed: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30",
                          supported: "bg-blue-500/10 text-blue-600 border-blue-500/30",
                          inferred: "bg-purple-500/10 text-purple-600 border-purple-500/30",
                          unknown: "bg-zinc-500/10 text-zinc-600 border-zinc-500/30",
                        }[tech.evidence_strength] || "bg-secondary text-foreground";

                        return (
                          <div
                            key={idx}
                            onClick={() => setActiveTechModal(tech)}
                            className="p-3 rounded-lg border border-border/50 bg-secondary/15 hover:bg-secondary/30 transition cursor-pointer space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-xs text-foreground">{tech.name}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border capitalize ${badgeColors}`}>
                                {tech.evidence_strength}
                              </span>
                            </div>
                            <span className="text-[10px] text-muted-foreground capitalize block">
                              Category: {tech.category.replace(/_/g, " ")}
                            </span>
                            <p className="text-[10px] text-muted-foreground/80 line-clamp-2 italic">
                              &ldquo;{tech.evidence_source}&rdquo;
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Hiring Intelligence */}
              {activeTab === "hiring" && (
                <div className="space-y-4">
                  <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-4">
                    <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-primary" /> Nexora Verified Requisitions Breakdown
                    </h3>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="bg-secondary/30 rounded-lg p-3 text-center">
                        <span className="text-[11px] text-muted-foreground">Active Listings</span>
                        <p className="text-lg font-black text-foreground">
                          {intelligence?.hiring_summary?.total_active_jobs || 0}
                        </p>
                      </div>
                      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">
                        <span className="text-[11px] text-emerald-600 font-semibold">Entry-Level / Fresher</span>
                        <p className="text-lg font-black text-emerald-600">
                          {intelligence?.hiring_summary?.entry_level_jobs || 0}
                        </p>
                      </div>
                      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
                        <span className="text-[11px] text-blue-600 font-semibold">Internships</span>
                        <p className="text-lg font-black text-blue-600">
                          {intelligence?.hiring_summary?.internship_jobs || 0}
                        </p>
                      </div>
                      <div className="bg-secondary/30 rounded-lg p-3 text-center">
                        <span className="text-[11px] text-muted-foreground">Stale / Expired</span>
                        <p className="text-lg font-black text-muted-foreground">
                          {intelligence?.hiring_summary?.stale_or_expired_jobs || 0}
                        </p>
                      </div>
                    </div>

                    {/* Top Role Families */}
                    {intelligence?.hiring_summary?.top_categories &&
                      intelligence.hiring_summary.top_categories.length > 0 && (
                        <div className="space-y-2 pt-2">
                          <span className="text-xs font-semibold text-foreground">Role Distribution:</span>
                          <div className="space-y-1.5">
                            {intelligence.hiring_summary.top_categories.map((cat, idx) => (
                              <div key={idx} className="flex items-center justify-between text-xs p-2 bg-secondary/20 rounded">
                                <span className="font-medium text-foreground">{cat.category}</span>
                                <span className="font-bold text-primary">{cat.count} open</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                    {/* Top Locations */}
                    {intelligence?.hiring_summary?.top_locations &&
                      intelligence.hiring_summary.top_locations.length > 0 && (
                        <div className="space-y-1.5 pt-2">
                          <span className="text-xs font-semibold text-foreground">Active Locations:</span>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {intelligence.hiring_summary.top_locations.map((loc, idx) => (
                              <span
                                key={idx}
                                className="px-2.5 py-1 rounded text-[11px] font-medium bg-secondary text-foreground flex items-center gap-1"
                              >
                                <MapPin className="w-3 h-3 text-muted-foreground" />
                                {loc}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                  </div>
                </div>
              )}

              {/* Tab 4: Candidate Fit Assessment */}
              {activeTab === "fit" && (
                <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border/40">
                    <div>
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                        <Target className="w-4 h-4 text-primary" /> Personalized Candidate-to-Employer Fit
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Evaluated against verified skills in your latest resume and target role preferences.
                      </p>
                    </div>

                    {fitAssessment && (
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                            Alignment Score
                          </span>
                          <p className="text-2xl font-black text-primary">{fitAssessment.fit_score}%</p>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-extrabold capitalize ${
                            fitAssessment.fit_level === "strong"
                              ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30"
                              : fitAssessment.fit_level === "moderate"
                              ? "bg-blue-500/10 text-blue-600 border border-blue-500/30"
                              : "bg-amber-500/10 text-amber-600 border border-amber-500/30"
                          }`}
                        >
                          {fitAssessment.fit_level} fit
                        </span>
                      </div>
                    )}
                  </div>

                  {fitAssessment ? (
                    <div className="space-y-4 text-xs">
                      {/* Summary */}
                      <div className="p-3.5 bg-primary/5 border border-primary/20 rounded-lg">
                        <p className="text-foreground leading-relaxed font-medium">
                          {fitAssessment.role_alignment_summary}
                        </p>
                      </div>

                      {/* Matching Skills vs Gap Skills */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl space-y-2">
                          <span className="font-bold text-emerald-600 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4" /> Overlapping Technical Competencies ({fitAssessment.matching_skills.length})
                          </span>
                          {fitAssessment.matching_skills.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {fitAssessment.matching_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="text-muted-foreground italic">No direct overlap identified with company tech stack.</p>
                          )}
                        </div>

                        <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-xl space-y-2">
                          <span className="font-bold text-amber-600 flex items-center gap-1.5">
                            <AlertCircle className="w-4 h-4" /> Identified Technology Growth Areas ({fitAssessment.missing_or_gap_skills.length})
                          </span>
                          {fitAssessment.missing_or_gap_skills.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {fitAssessment.missing_or_gap_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-700 dark:text-amber-300"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="text-muted-foreground italic">No high-priority gaps flagged.</p>
                          )}
                        </div>
                      </div>

                      {/* Interview Recommendations */}
                      {fitAssessment.recommended_interview_focus.length > 0 && (
                        <div className="p-4 bg-secondary/30 rounded-xl space-y-2">
                          <span className="font-bold text-foreground flex items-center gap-1.5">
                            <Lightbulb className="w-4 h-4 text-amber-500" /> Recommended Interview Focus Topics
                          </span>
                          <ul className="space-y-1.5 list-disc pl-5 text-muted-foreground">
                            {fitAssessment.recommended_interview_focus.map((f, idx) => (
                              <li key={idx} className="leading-relaxed">
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Matching Requisitions */}
                      {fitAssessment.target_role_matches.length > 0 && (
                        <div className="p-4 bg-secondary/20 rounded-xl space-y-2">
                          <span className="font-bold text-foreground flex items-center gap-1.5">
                            <BriefcaseIcon className="w-4 h-4 text-primary" /> Target Openings at this Company
                          </span>
                          <div className="space-y-1.5">
                            {fitAssessment.target_role_matches.map((m, idx) => (
                              <div
                                key={idx}
                                className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-background"
                              >
                                <div>
                                  <p className="font-semibold text-foreground">{m.title}</p>
                                  <p className="text-[10px] text-muted-foreground">
                                    {m.seniority_level} • {m.location}
                                  </p>
                                </div>
                                <Link
                                  href={`/dashboard/jobs`}
                                  className="px-2.5 py-1 text-[11px] font-medium rounded bg-secondary hover:bg-secondary/80 text-foreground transition flex items-center gap-1"
                                >
                                  View Job <ArrowRight className="w-3 h-3" />
                                </Link>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      Calculating fit assessment...
                    </div>
                  )}
                </div>
              )}

              {/* Tab 5: AI Research Report */}
              {activeTab === "report" && (
                <div className="space-y-4">
                  {/* Generation Bar */}
                  <div className="bg-card border border-border/60 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-0.5">
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-primary" /> 10-Section Comprehensive Research Dossier
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Structured, zero-fabrication report synthesized from public sources and company jobs.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
                        <input
                          type="checkbox"
                          checked={forceRefreshReport}
                          onChange={(e) => setForceRefreshReport(e.target.checked)}
                          className="rounded border-border"
                        />
                        Force Re-generate
                      </label>
                      <button
                        onClick={handleGenerateReport}
                        disabled={generatingReport}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-primary hover:bg-primary/90 text-primary-foreground transition shadow-sm disabled:opacity-50"
                      >
                        {generatingReport ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            Synthesizing Report...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3.5 h-3.5" />
                            {currentReport ? "Re-Run Report" : "Generate Report"}
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Active Report Viewer */}
                  {!currentReport ? (
                    <div className="bg-card border border-border/60 rounded-xl p-12 text-center text-muted-foreground space-y-3">
                      <FileCheck className="w-10 h-10 mx-auto opacity-40 text-primary" />
                      <h4 className="font-semibold text-foreground text-sm">No Report Generated Yet</h4>
                      <p className="text-xs max-w-sm mx-auto">
                        Click &ldquo;Generate Report&rdquo; to create a grounded 10-section dossier covering products, engineering culture, interview topics, and fit.
                      </p>
                    </div>
                  ) : (
                    <div className="bg-card border border-border/60 rounded-xl p-6 shadow-sm space-y-6">
                      {/* Report Meta Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border/40">
                        <div>
                          <h4 className="text-lg font-black text-foreground">{currentReport.report_title}</h4>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Generated on {new Date(currentReport.created_at).toLocaleString()} •{" "}
                            Provider: <span className="font-semibold">{currentReport.provider}</span> ({currentReport.model})
                            {currentReport.is_cached && (
                              <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-secondary text-foreground">
                                Cached (Deterministic SHA-256)
                              </span>
                            )}
                          </p>
                        </div>

                        <div className="flex items-center gap-2 self-start">
                          <button
                            onClick={handleCopyReportMarkdown}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-background hover:bg-muted text-foreground transition"
                          >
                            <Copy className="w-3.5 h-3.5" />
                            {copySuccess ? "Copied Markdown!" : "Copy Report"}
                          </button>
                          <button
                            onClick={() => handleDeleteReport(currentReport.id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 transition"
                            title="Delete this report"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Delete
                          </button>
                        </div>
                      </div>

                      {/* 10 Sections Accordion / Cards */}
                      <div className="space-y-4">
                        {Object.entries(currentReport.sections || {}).map(([key, section]) => (
                          <div key={key} className="border border-border/50 rounded-xl p-4 bg-secondary/10 space-y-2.5">
                            <h5 className="font-bold text-xs uppercase tracking-wider text-primary flex items-center gap-1.5">
                              <Brain className="w-3.5 h-3.5" /> {section.title}
                            </h5>
                            <p className="text-xs leading-relaxed text-foreground/90">{section.content}</p>
                            {section.bullet_points && section.bullet_points.length > 0 && (
                              <ul className="space-y-1 list-disc pl-5 text-xs text-muted-foreground">
                                {section.bullet_points.map((pt, pIdx) => (
                                  <li key={pIdx} className="leading-relaxed">
                                    {pt}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 6: Public Sources */}
              {activeTab === "sources" && (
                <div className="bg-card border border-border/60 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-border/40">
                    <div>
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary" /> Public Research Documents & Verified Provenance
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Scraped safely via SSRFSafeTransport with strict anti-bot and robots.txt compliance.
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground font-medium">{sources.length} sources</span>
                  </div>

                  {sources.length === 0 ? (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      No public research sources ingested yet. Click &ldquo;Refresh Web Sources&rdquo; above.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {sources.map((src) => (
                        <div key={src.id} className="p-3.5 border border-border/50 rounded-lg bg-secondary/15 space-y-1.5">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <span className="font-bold text-xs text-foreground">{src.title}</span>
                            <div className="flex items-center gap-1.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  src.is_verified
                                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                                }`}
                              >
                                {src.is_verified ? "Verified Official" : "Third-Party"}
                              </span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-secondary text-muted-foreground capitalize">
                                {src.source_type.replace(/_/g, " ")}
                              </span>
                            </div>
                          </div>
                          <div className="space-y-0.5">
                            <a
                              href={src.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-primary hover:underline flex items-center gap-1 truncate"
                            >
                              {src.source_url}
                              <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                            </a>
                            {src.final_url && src.final_url !== src.source_url && (
                              <p className="text-[10px] text-muted-foreground flex items-center gap-1 font-mono">
                                <span className="font-semibold text-foreground">Redirected to:</span> {src.final_url}
                              </p>
                            )}
                          </div>
                          {src.content_snippet && (
                            <p className="text-[11px] text-muted-foreground line-clamp-2">
                              {src.content_snippet}
                            </p>
                          )}
                          <div className="flex items-center gap-3 text-[10px] text-muted-foreground/80 pt-1">
                            <span>Retrieved: {new Date(src.retrieved_at).toLocaleDateString()}</span>
                            <span>•</span>
                            <span className="font-mono truncate">Hash: {src.content_hash.slice(0, 16)}...</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Technology Citation Modal */}
      {activeTechModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-xl p-5 max-w-md w-full shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" />
                <h4 className="font-extrabold text-sm text-foreground">{activeTechModal.name}</h4>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold capitalize ${
                  activeTechModal.evidence_strength === "confirmed"
                    ? "bg-emerald-500/10 text-emerald-600"
                    : activeTechModal.evidence_strength === "supported"
                    ? "bg-blue-500/10 text-blue-600"
                    : "bg-purple-500/10 text-purple-600"
                }`}
              >
                {activeTechModal.evidence_strength}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <span className="text-muted-foreground font-semibold">Category:</span>
                <p className="text-foreground capitalize">{activeTechModal.category.replace(/_/g, " ")}</p>
              </div>

              <div>
                <span className="text-muted-foreground font-semibold">Evidence Citation:</span>
                <p className="text-foreground italic bg-secondary/30 p-2.5 rounded-lg mt-1">
                  &ldquo;{activeTechModal.evidence_source}&rdquo;
                </p>
              </div>

              {activeTechModal.context && (
                <div>
                  <span className="text-muted-foreground font-semibold">Contextual Excerpt:</span>
                  <p className="text-muted-foreground bg-secondary/20 p-2 rounded mt-1 font-mono text-[10px]">
                    ...{activeTechModal.context}...
                  </p>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setActiveTechModal(null)}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BriefcaseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="20" height="14" x="2" y="7" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  );
}
