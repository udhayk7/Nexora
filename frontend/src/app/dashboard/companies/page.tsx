"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Building2,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  Filter,
  GitMerge,
  Globe,
  HelpCircle,
  Layers,
  Link as LinkIcon,
  Loader2,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Tag,
  Trash2,
  Users,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  apiClient,
  Company,
  CompanyCategory,
  CompanyDetail,
  CompanyDuplicateCheckResponse,
  CompanyListResponse,
  CompanySource,
  CompanySourceType,
  VerificationStatus,
} from "@/lib/api";

const CATEGORY_LABELS: Record<CompanyCategory, string> = {
  product_company: "Product Company",
  mnc: "MNC",
  gcc: "Global Capability Center (GCC)",
  big_four: "Big Four",
  large_it_services: "Large IT Services",
  established_startup: "Established Startup",
  other: "Other",
};

const STATUS_CONFIG: Record<
  VerificationStatus,
  { label: string; icon: React.ElementType; color: string; bg: string }
> = {
  verified: {
    label: "Verified",
    icon: ShieldCheck,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
  corroborated: {
    label: "Corroborated",
    icon: CheckCircle2,
    color: "text-blue-500",
    bg: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  },
  unverified: {
    label: "Unverified",
    icon: HelpCircle,
    color: "text-amber-500",
    bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  },
  suspicious: {
    label: "Suspicious",
    icon: AlertTriangle,
    color: "text-destructive",
    bg: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

const SOURCE_TYPE_LABELS: Record<CompanySourceType, string> = {
  official_website: "Official Website",
  careers_page: "Careers Page",
  public_directory: "Public Directory",
  user_added: "User Submission",
  curated_dataset: "Curated Dataset",
  other: "Other Permitted Source",
};

export default function CompaniesPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [userOnly, setUserOnly] = useState(false);
  const [page, setPage] = useState(1);

  // Data State
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals State
  const [detailCompany, setDetailCompany] = useState<CompanyDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [verifyCompanyId, setVerifyCompanyId] = useState<string | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<VerificationStatus>("verified");
  const [verifyNotes, setVerifyNotes] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);

  // Merge State
  const [mergeTargetCompany, setMergeTargetCompany] = useState<Company | null>(null);
  const [secondaryCompanyId, setSecondaryCompanyId] = useState<string>("");
  const [mergeReason, setMergeReason] = useState("");
  const [isMerging, setIsMerging] = useState(false);

  // Add Source State
  const [showAddSource, setShowAddSource] = useState(false);
  const [sourceName, setSourceName] = useState("");
  const [sourceType, setSourceType] = useState<CompanySourceType>("careers_page");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceEvidence, setSourceEvidence] = useState("");
  const [isAddingSource, setIsAddingSource] = useState(false);

  // Form State for Adding Company
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState<CompanyCategory>("product_company");
  const [newWebsite, setNewWebsite] = useState("");
  const [newCareersUrl, setNewCareersUrl] = useState("");
  const [newHqCountry, setNewHqCountry] = useState("India");
  const [newHqCity, setNewHqCity] = useState("");
  const [newRegions, setNewRegions] = useState("India");
  const [newTechTags, setNewTechTags] = useState("");
  const [newIndustryTags, setNewIndustryTags] = useState("");
  const [newSizeBand, setNewSizeBand] = useState("51-200");
  const [newDescription, setNewDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [duplicateMatches, setDuplicateMatches] = useState<CompanyDuplicateCheckResponse | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const loadCompanies = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if (selectedCategory !== "all") params.set("category", selectedCategory);
      if (selectedStatus !== "all") params.set("verification_status", selectedStatus);
      if (userOnly) params.set("user_only", "true");
      params.set("page", page.toString());
      params.set("per_page", "12");

      const res = await apiClient<CompanyListResponse>(`/api/v1/companies?${params.toString()}`);
      setCompanies(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to load companies";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [search, selectedCategory, selectedStatus, userOnly, page]);

  useEffect(() => {
    if (user) {
      loadCompanies();
    }
  }, [user, loadCompanies]);

  const openCompanyDetail = async (companyId: string) => {
    setIsDetailLoading(true);
    try {
      const detail = await apiClient<CompanyDetail>(`/api/v1/companies/${companyId}`);
      setDetailCompany(detail);
    } catch (err: unknown) {
      alert("Failed to load company details");
    } finally {
      setIsDetailLoading(false);
    }
  };

  const checkDuplicatesLive = async (name: string, url: string) => {
    if (!name.trim()) {
      setDuplicateMatches(null);
      return;
    }
    try {
      const params = new URLSearchParams({ name: name.trim() });
      if (url.trim()) params.set("website_url", url.trim());
      const res = await apiClient<CompanyDuplicateCheckResponse>(
        `/api/v1/companies/duplicates/check?${params.toString()}`
      );
      if (res.matches && res.matches.length > 0) {
        setDuplicateMatches(res);
      } else {
        setDuplicateMatches(null);
      }
    } catch {
      // Ignore background check errors
    }
  };

  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    setIsSubmitting(true);
    try {
      const operatingRegions = newRegions
        .split(",")
        .map((r) => r.trim())
        .filter(Boolean);
      const technologyTags = newTechTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const industryTags = newIndustryTags
        .split(",")
        .map((i) => i.trim())
        .filter(Boolean);

      await apiClient("/api/v1/companies", {
        method: "POST",
        body: JSON.stringify({
          name: newName.trim(),
          category: newCategory,
          website_url: newWebsite.trim() || undefined,
          careers_url: newCareersUrl.trim() || undefined,
          headquarters_country: newHqCountry.trim() || undefined,
          headquarters_city: newHqCity.trim() || undefined,
          operating_regions: operatingRegions,
          technology_tags: technologyTags,
          industry_tags: industryTags,
          size_band: newSizeBand,
          description: newDescription.trim() || undefined,
        }),
      });

      setShowAddModal(false);
      resetForm();
      loadCompanies();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to register company";
      alert(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyCompanyId || !verifyNotes.trim() || verifyNotes.trim().length < 5) {
      alert("Evidence notes of at least 5 characters are required.");
      return;
    }

    setIsVerifying(true);
    try {
      await apiClient(`/api/v1/companies/${verifyCompanyId}/verify`, {
        method: "POST",
        body: JSON.stringify({
          verification_status: verifyStatus,
          verification_notes: verifyNotes.trim(),
        }),
      });

      setVerifyCompanyId(null);
      setVerifyNotes("");
      loadCompanies();
      if (detailCompany && detailCompany.id === verifyCompanyId) {
        openCompanyDetail(verifyCompanyId);
      }
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to verify company";
      alert(msg);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detailCompany || !sourceName.trim()) return;

    setIsAddingSource(true);
    try {
      await apiClient(`/api/v1/companies/${detailCompany.id}/sources`, {
        method: "POST",
        body: JSON.stringify({
          source_name: sourceName.trim(),
          source_type: sourceType,
          source_url: sourceUrl.trim() || undefined,
          evidence_summary: sourceEvidence.trim() || undefined,
        }),
      });

      setShowAddSource(false);
      setSourceName("");
      setSourceUrl("");
      setSourceEvidence("");
      openCompanyDetail(detailCompany.id);
      loadCompanies();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to add source";
      alert(msg);
    } finally {
      setIsAddingSource(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (!detailCompany || !confirm("Are you sure you want to delete this provenance source?")) return;

    try {
      await apiClient(`/api/v1/companies/${detailCompany.id}/sources/${sourceId}`, {
        method: "DELETE",
      });
      openCompanyDetail(detailCompany.id);
      loadCompanies();
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to delete source";
      alert(msg);
    }
  };

  const handleMerge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mergeTargetCompany || !secondaryCompanyId || !mergeReason.trim()) {
      alert("Target, duplicate secondary company, and merge reason are required.");
      return;
    }

    setIsMerging(true);
    try {
      await apiClient(`/api/v1/companies/${mergeTargetCompany.id}/merge`, {
        method: "POST",
        body: JSON.stringify({
          secondary_company_id: secondaryCompanyId,
          merge_reason: mergeReason.trim(),
        }),
      });

      setMergeTargetCompany(null);
      setSecondaryCompanyId("");
      setMergeReason("");
      loadCompanies();
      if (detailCompany) {
        openCompanyDetail(detailCompany.id);
      }
      alert("Companies merged successfully. Sources transferred and secondary record archived.");
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Failed to merge companies";
      alert(msg);
    } finally {
      setIsMerging(false);
    }
  };

  const resetForm = () => {
    setNewName("");
    setNewWebsite("");
    setNewCareersUrl("");
    setNewHqCity("");
    setNewTechTags("");
    setNewIndustryTags("");
    setNewDescription("");
    setDuplicateMatches(null);
  };

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
            <Building2 className="w-7 h-7 text-primary" /> Company Discovery
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Discover, evaluate, and curate entry-level tech opportunities across product companies, GCCs, MNCs, and startups.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadCompanies()}
            className="p-2 rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> Add Company
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <section className="p-4 rounded-xl border border-border bg-card mb-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search companies by name, domain, tech stack, or location..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            {search && (
              <button
                onClick={() => {
                  setSearch("");
                  setPage(1);
                }}
                className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2.5">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Categories</option>
              <option value="product_company">Product Companies</option>
              <option value="mnc">MNCs</option>
              <option value="gcc">GCCs</option>
              <option value="big_four">Big Four</option>
              <option value="large_it_services">Large IT Services</option>
              <option value="established_startup">Established Startups</option>
              <option value="other">Other</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Statuses</option>
              <option value="verified">Verified</option>
              <option value="corroborated">Corroborated</option>
              <option value="unverified">Unverified</option>
              <option value="suspicious">Suspicious</option>
            </select>

            <label className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border bg-background text-xs cursor-pointer select-none">
              <input
                type="checkbox"
                checked={userOnly}
                onChange={(e) => {
                  setUserOnly(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-border text-primary focus:ring-primary/20"
              />
              <span className="text-muted-foreground whitespace-nowrap">My Additions</span>
            </label>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      {error && (
        <div className="p-4 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-sm flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadCompanies()}
            className="text-xs underline hover:no-underline font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-8 h-8 text-primary animate-spin mb-3" />
          <p className="text-sm text-muted-foreground">Searching company database...</p>
        </div>
      ) : companies.length === 0 ? (
        <div className="p-12 rounded-xl border border-dashed border-border text-center bg-card/40 my-8">
          <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mx-auto mb-4 text-muted-foreground">
            <Building2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-foreground">No companies found</h3>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-6">
            {search || selectedCategory !== "all" || selectedStatus !== "all" || userOnly
              ? "No records match your active filters. Try broadening your search or resetting category filters."
              : "No discovery companies have been registered yet. Add companies manually or configure discovery datasets to explore opportunities."}
          </p>
          <div className="flex items-center justify-center gap-3">
            {(search || selectedCategory !== "all" || selectedStatus !== "all" || userOnly) && (
              <button
                onClick={() => {
                  setSearch("");
                  setSelectedCategory("all");
                  setSelectedStatus("all");
                  setUserOnly(false);
                  setPage(1);
                }}
                className="px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-border bg-background hover:bg-secondary transition-colors"
              >
                Reset Filters
              </button>
            )}
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" /> Add First Company
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {companies.map((company) => {
              const statusCfg = STATUS_CONFIG[company.verification_status];
              const StatusIcon = statusCfg.icon;

              return (
                <div
                  key={company.id}
                  className="rounded-xl border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Top Badges */}
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground">
                        {CATEGORY_LABELS[company.category]}
                      </span>

                      <div
                        className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border ${statusCfg.bg}`}
                        title={company.verification_notes || `Status: ${statusCfg.label}`}
                      >
                        <StatusIcon className="w-3 h-3" />
                        {statusCfg.label}
                      </div>
                    </div>

                    {/* Name & Domain */}
                    <h3 className="text-base font-semibold text-foreground tracking-tight line-clamp-1">
                      {company.name}
                    </h3>
                    {company.website_url ? (
                      <a
                        href={company.website_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-0.5 line-clamp-1"
                      >
                        <Globe className="w-3 h-3" />
                        {company.normalized_domain || company.website_url}
                      </a>
                    ) : (
                      <span className="text-xs text-muted-foreground mt-0.5 block">Domain not set</span>
                    )}

                    {/* Location & Size */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground mt-3 pt-2.5 border-t border-border/60">
                      {(company.headquarters_city || company.headquarters_country) && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-muted-foreground/80" />
                          {[company.headquarters_city, company.headquarters_country].filter(Boolean).join(", ")}
                        </span>
                      )}

                      {company.size_band && (
                        <span className="inline-flex items-center gap-1">
                          <Users className="w-3 h-3 text-muted-foreground/80" />
                          {company.size_band}
                        </span>
                      )}
                    </div>

                    {/* Description preview */}
                    {company.description && (
                      <p className="text-xs text-muted-foreground/90 mt-2.5 line-clamp-2">
                        {company.description}
                      </p>
                    )}

                    {/* Tech & Industry Tags */}
                    {company.technology_tags && company.technology_tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {company.technology_tags.slice(0, 4).map((tech, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/80 text-foreground font-mono"
                          >
                            {tech}
                          </span>
                        ))}
                        {company.technology_tags.length > 4 && (
                          <span className="text-[10px] px-1 py-0.5 rounded text-muted-foreground font-mono">
                            +{company.technology_tags.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Footer & Actions */}
                  <div className="pt-4 mt-4 border-t border-border flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {company.careers_url && (
                        <a
                          href={company.careers_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                        >
                          Careers <ArrowUpRight className="w-3 h-3" />
                        </a>
                      )}

                      <span className="text-[11px] text-muted-foreground inline-flex items-center gap-1">
                        <Layers className="w-3 h-3" /> {company.sources_count} source{company.sources_count === 1 ? "" : "s"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Link
                        href={`/dashboard/company-intelligence?company_id=${company.id}`}
                        className="px-2 py-1 text-xs font-semibold rounded bg-primary/10 hover:bg-primary/20 text-primary transition-colors inline-flex items-center gap-1"
                        title="Explore evidence-backed company intelligence"
                      >
                        Intelligence
                      </Link>

                      <button
                        onClick={() => {
                          setVerifyCompanyId(company.id);
                          setVerifyStatus(company.verification_status);
                          setVerifyNotes(company.verification_notes || "");
                        }}
                        className="px-2 py-1 text-xs rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                        title="Verify company"
                      >
                        Verify
                      </button>

                      <button
                        onClick={() => openCompanyDetail(company.id)}
                        className="px-2.5 py-1 text-xs font-medium rounded bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                      >
                        Provenance
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between py-4 border-t border-border text-xs text-muted-foreground">
              <span>
                Showing {companies.length} of {total} companies
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded border border-border disabled:opacity-40 hover:bg-secondary"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span>
                  Page {page} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="p-1.5 rounded border border-border disabled:opacity-40 hover:bg-secondary"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* DETAIL & PROVENANCE MODAL */}
      {detailCompany && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl space-y-6">
            <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 rounded bg-secondary font-medium">
                    {CATEGORY_LABELS[detailCompany.category]}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${
                      STATUS_CONFIG[detailCompany.verification_status].bg
                    }`}
                  >
                    {STATUS_CONFIG[detailCompany.verification_status].label}
                  </span>
                </div>
                <h2 className="text-xl font-bold">{detailCompany.name}</h2>
                {detailCompany.website_url && (
                  <a
                    href={detailCompany.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-0.5"
                  >
                    <Globe className="w-3 h-3" /> {detailCompany.website_url}
                  </a>
                )}
              </div>

              <button
                onClick={() => setDetailCompany(null)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Verification rationale */}
            {detailCompany.verification_notes && (
              <div className="p-3.5 rounded-lg border border-border bg-secondary/30 text-xs">
                <span className="font-semibold block mb-0.5">Verification Evidence:</span>
                <p className="text-muted-foreground">{detailCompany.verification_notes}</p>
                {detailCompany.last_verified_at && (
                  <span className="text-[10px] text-muted-foreground/70 block mt-1">
                    Last reviewed: {new Date(detailCompany.last_verified_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            )}

            {/* Description & Metadata */}
            {detailCompany.description && (
              <div className="text-xs space-y-1">
                <span className="font-semibold text-muted-foreground block">About</span>
                <p className="text-foreground leading-relaxed">{detailCompany.description}</p>
              </div>
            )}

            {/* Provenance Discovery Sources */}
            <div className="space-y-3 pt-2 border-t border-border">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-primary" /> Discovery Sources & Provenance
                  </h4>
                  <p className="text-[11px] text-muted-foreground">
                    Verifiable links, directory datasets, or audit evidence for this company record.
                  </p>
                </div>

                <button
                  onClick={() => setShowAddSource(!showAddSource)}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary"
                >
                  {showAddSource ? "Cancel" : "+ Add Source"}
                </button>
              </div>

              {/* Add Source Form */}
              {showAddSource && (
                <form
                  onSubmit={handleAddSource}
                  className="p-4 rounded-lg border border-border bg-secondary/20 space-y-3 animate-in fade-in"
                >
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                        Source Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={sourceName}
                        onChange={(e) => setSourceName(e.target.value)}
                        placeholder="e.g., Campus Careers Portal 2026"
                        className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                        Source Type
                      </label>
                      <select
                        value={sourceType}
                        onChange={(e) => setSourceType(e.target.value as CompanySourceType)}
                        className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background"
                      >
                        <option value="careers_page">Careers Page</option>
                        <option value="official_website">Official Website</option>
                        <option value="public_directory">Public Directory</option>
                        <option value="curated_dataset">Curated Dataset</option>
                        <option value="user_added">User Submission</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                      Source URL
                    </label>
                    <input
                      type="url"
                      value={sourceUrl}
                      onChange={(e) => setSourceUrl(e.target.value)}
                      placeholder="https://company.com/careers"
                      className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                      Evidence / Verification Notes
                    </label>
                    <textarea
                      rows={2}
                      value={sourceEvidence}
                      onChange={(e) => setSourceEvidence(e.target.value)}
                      placeholder="Observed active campus recruitment drive or official business registration..."
                      className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background resize-none"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setShowAddSource(false)}
                      className="px-3 py-1 text-xs rounded border border-border hover:bg-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isAddingSource}
                      className="px-3 py-1 text-xs font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      {isAddingSource ? "Saving..." : "Save Source"}
                    </button>
                  </div>
                </form>
              )}

              {/* Sources List */}
              <div className="space-y-2.5">
                {detailCompany.sources.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic py-2">
                    No individual discovery sources attached yet.
                  </p>
                ) : (
                  detailCompany.sources.map((src) => (
                    <div
                      key={src.id}
                      className="p-3 rounded-lg border border-border bg-background flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground">{src.source_name}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-secondary text-muted-foreground">
                            {SOURCE_TYPE_LABELS[src.source_type]}
                          </span>
                        </div>

                        {src.source_url && (
                          <a
                            href={src.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline inline-flex items-center gap-1 line-clamp-1"
                          >
                            <ExternalLink className="w-3 h-3" /> {src.source_url}
                          </a>
                        )}

                        {src.evidence_summary && (
                          <p className="text-muted-foreground text-[11px]">{src.evidence_summary}</p>
                        )}

                        <span className="text-[10px] text-muted-foreground/60 block">
                          Recorded: {new Date(src.first_seen_at).toLocaleDateString()}
                        </span>
                      </div>

                      <button
                        onClick={() => handleDeleteSource(src.id)}
                        className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        title="Delete source"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Merge Action Drawer */}
            <div className="pt-4 border-t border-border flex items-center justify-between">
              <button
                onClick={() => {
                  setMergeTargetCompany(detailCompany);
                  setDetailCompany(null);
                }}
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-medium"
              >
                <GitMerge className="w-3.5 h-3.5 text-primary" /> Merge Duplicate into this Record
              </button>

              <button
                onClick={() => setDetailCompany(null)}
                className="px-4 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ADD COMPANY MODAL */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-xl w-full max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h2 className="text-lg font-bold">Register Company</h2>
                <p className="text-xs text-muted-foreground">
                  Add an employer record to track for career opportunities and early-career discovery.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCompany} className="space-y-3.5 text-xs">
              <div>
                <label className="font-medium text-foreground block mb-1">Company Name *</label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => {
                    setNewName(e.target.value);
                    checkDuplicatesLive(e.target.value, newWebsite);
                  }}
                  placeholder="e.g., Stripe, Zoho, Infosys"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20"
                />
              </div>

              {/* Duplicate Detection Alert */}
              {duplicateMatches && duplicateMatches.matches.length > 0 && (
                <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <AlertTriangle className="w-3.5 h-3.5" /> Potential Duplicate Detected
                  </div>
                  <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                    {duplicateMatches.matches.map((m, idx) => (
                      <li key={idx}>
                        <span className="font-medium">{m.company.name}</span> ({m.reason})
                      </li>
                    ))}
                  </ul>
                  <p className="text-[10px] text-muted-foreground pt-1">
                    Consider verifying or merging rather than creating duplicate records.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium text-foreground block mb-1">Category</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value as CompanyCategory)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="product_company">Product Company</option>
                    <option value="mnc">MNC</option>
                    <option value="gcc">Global Capability Center (GCC)</option>
                    <option value="big_four">Big Four</option>
                    <option value="large_it_services">Large IT Services</option>
                    <option value="established_startup">Established Startup</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="font-medium text-foreground block mb-1">Size Band</label>
                  <select
                    value={newSizeBand}
                    onChange={(e) => setNewSizeBand(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  >
                    <option value="1-10">1-10 employees</option>
                    <option value="11-50">11-50 employees</option>
                    <option value="51-200">51-200 employees</option>
                    <option value="201-500">201-500 employees</option>
                    <option value="501-1000">501-1,000 employees</option>
                    <option value="1001-5000">1,001-5,000 employees</option>
                    <option value="5001-10000">5,001-10,000 employees</option>
                    <option value="10000+">10,000+ enterprise</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium text-foreground block mb-1">Website URL</label>
                  <input
                    type="url"
                    value={newWebsite}
                    onChange={(e) => {
                      setNewWebsite(e.target.value);
                      checkDuplicatesLive(newName, e.target.value);
                    }}
                    placeholder="https://company.com"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium text-foreground block mb-1">Careers Portal URL</label>
                  <input
                    type="url"
                    value={newCareersUrl}
                    onChange={(e) => setNewCareersUrl(e.target.value)}
                    placeholder="https://company.com/careers"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium text-foreground block mb-1">HQ Country</label>
                  <input
                    type="text"
                    value={newHqCountry}
                    onChange={(e) => setNewHqCountry(e.target.value)}
                    placeholder="e.g., India"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium text-foreground block mb-1">HQ City</label>
                  <input
                    type="text"
                    value={newHqCity}
                    onChange={(e) => setNewHqCity(e.target.value)}
                    placeholder="e.g., Bengaluru, Kochi, Hyderabad"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium text-foreground block mb-1">
                  Operating Regions (comma separated)
                </label>
                <input
                  type="text"
                  value={newRegions}
                  onChange={(e) => setNewRegions(e.target.value)}
                  placeholder="India, United States, Europe"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-medium text-foreground block mb-1">
                    Tech Stack Tags (comma separated)
                  </label>
                  <input
                    type="text"
                    value={newTechTags}
                    onChange={(e) => setNewTechTags(e.target.value)}
                    placeholder="Python, React, AWS, Go"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="font-medium text-foreground block mb-1">
                    Industry Tags (comma separated)
                  </label>
                  <input
                    type="text"
                    value={newIndustryTags}
                    onChange={(e) => setNewIndustryTags(e.target.value)}
                    placeholder="SaaS, FinTech, E-commerce"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium text-foreground block mb-1">Description</label>
                <textarea
                  rows={3}
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Brief overview of engineering focus, campus hiring history, or business model..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? "Registering..." : "Register Company"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VERIFY MODAL */}
      {verifyCompanyId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-base font-bold flex items-center gap-1.5">
                <ShieldCheck className="w-5 h-5 text-primary" /> Update Verification Status
              </h2>
              <button
                onClick={() => setVerifyCompanyId(null)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleVerify} className="space-y-3.5 text-xs">
              <div>
                <label className="font-medium block mb-1">Target Status</label>
                <select
                  value={verifyStatus}
                  onChange={(e) => setVerifyStatus(e.target.value as VerificationStatus)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                >
                  <option value="verified">Verified (Definitive official proof)</option>
                  <option value="corroborated">Corroborated (Multiple reliable signals)</option>
                  <option value="unverified">Unverified (Pending confirmation)</option>
                  <option value="suspicious">Suspicious (Inconsistent or fake claims)</option>
                </select>
              </div>

              <div>
                <label className="font-medium block mb-1">
                  Evidence & Verification Rationale *
                </label>
                <textarea
                  rows={3}
                  required
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  placeholder="Provide concrete evidence (e.g. Official MCA filing verified, active LinkedIn campus recruiting drive observed)..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background resize-none"
                />
                <span className="text-[10px] text-muted-foreground">Minimum 5 characters required.</span>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setVerifyCompanyId(null)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isVerifying}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {isVerifying ? "Updating..." : "Confirm Status"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MERGE MODAL */}
      {mergeTargetCompany && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-base font-bold flex items-center gap-1.5">
                <GitMerge className="w-5 h-5 text-primary" /> Merge Duplicate Company
              </h2>
              <button
                onClick={() => setMergeTargetCompany(null)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-lg border border-primary/20 bg-primary/5 text-xs">
              <span className="font-semibold text-primary block mb-0.5">Primary Target Record:</span>
              <p className="font-medium text-foreground">{mergeTargetCompany.name}</p>
              <span className="text-[10px] text-muted-foreground">
                All sources and missing tags will be consolidated into this record.
              </span>
            </div>

            <form onSubmit={handleMerge} className="space-y-3 text-xs">
              <div>
                <label className="font-medium block mb-1">
                  Select Duplicate Company to Merge (Secondary) *
                </label>
                <select
                  required
                  value={secondaryCompanyId}
                  onChange={(e) => setSecondaryCompanyId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                >
                  <option value="">-- Choose duplicate company --</option>
                  {companies
                    .filter((c) => c.id !== mergeTargetCompany.id)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.normalized_domain || "no domain"})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="font-medium block mb-1">Auditable Merge Justification *</label>
                <textarea
                  rows={2}
                  required
                  value={mergeReason}
                  onChange={(e) => setMergeReason(e.target.value)}
                  placeholder="e.g., Duplicate manual submission of regional entity into main parent record..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background resize-none"
                />
              </div>

              <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-700 dark:text-amber-400">
                Warning: The secondary company will be marked as merged and archived from discovery lists.
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setMergeTargetCompany(null)}
                  className="px-3.5 py-1.5 rounded-lg border border-border hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isMerging}
                  className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
                >
                  {isMerging ? "Merging..." : "Confirm Merge"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

