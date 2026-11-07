"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  Award,
  BarChart2,
  Bookmark,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Code2,
  Copy,
  Download,
  ExternalLink,
  Eye,
  FileCode,
  FileText,
  Globe,
  GraduationCap,
  Layers,
  Layout,
  Link2,
  Monitor,
  Palette,
  Play,
  Plus,
  RefreshCw,
  Share2,
  Smartphone,
  Sparkles,
  Star,
  Trash2,
  Undo2,
  User,
  Wand2,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  AIPortfolioAssistResult,
  LearningProject,
  learningRoadmapsApi,
  PortfolioAnalytics,
  PortfolioDetail,
  PortfolioProfileData,
  PortfolioProjectItem,
  PortfolioSection,
  PortfolioThemeConfig,
  PortfolioVersionItem,
  portfoliosApi,
} from "@/lib/api";

type StudioTab =
  | "editor"
  | "projects"
  | "sections"
  | "themes"
  | "preview"
  | "analytics"
  | "versions";

const COLOR_PRESETS = [
  { name: "Ocean Blue", hex: "#3B82F6" },
  { name: "Emerald", hex: "#10B981" },
  { name: "Violet", hex: "#8B5CF6" },
  { name: "Amber", hex: "#F59E0B" },
  { name: "Rose", hex: "#EC4899" },
  { name: "Cyan", hex: "#06B6D4" },
  { name: "Slate", hex: "#64748B" },
];

export default function PortfolioStudioPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<StudioTab>("editor");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Core portfolio state
  const [portfolio, setPortfolio] = useState<PortfolioDetail | null>(null);
  const [learningProjects, setLearningProjects] = useState<LearningProject[]>([]);
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [versions, setVersions] = useState<PortfolioVersionItem[]>([]);

  // Profile Form state
  const [fullName, setFullName] = useState("");
  const [headline, setHeadline] = useState("");
  const [summary, setSummary] = useState("");
  const [location, setLocation] = useState("");
  const [targetRoles, setTargetRoles] = useState("");
  const [skillsInput, setSkillsInput] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");

  // Theme state
  const [selectedTemplate, setSelectedTemplate] = useState("minimal");
  const [accentColor, setAccentColor] = useState("#3B82F6");
  const [fontFamily, setFontFamily] = useState("inter");
  const [darkMode, setDarkMode] = useState("system");

  // Slug customizer
  const [customSlug, setCustomSlug] = useState("");
  const [isUpdatingSlug, setIsUpdatingSlug] = useState(false);

  // Preview device state
  const [previewDevice, setPreviewDevice] = useState<"desktop" | "mobile">("desktop");

  // Modals
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [showAIAssistModal, setShowAIAssistModal] = useState(false);
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState<PortfolioProjectItem | null>(null);

  // Project Form
  const [projTitle, setProjTitle] = useState("");
  const [projProblem, setProjProblem] = useState("");
  const [projDesc, setProjDesc] = useState("");
  const [projStack, setProjStack] = useState("");
  const [projFeatures, setProjFeatures] = useState("");
  const [projArch, setProjArch] = useState("");
  const [projRepo, setProjRepo] = useState("");
  const [projDemo, setProjDemo] = useState("");
  const [projOutcomes, setProjOutcomes] = useState("");
  const [projStatus, setProjStatus] = useState("completed");
  const [projFeatured, setProjFeatured] = useState(false);

  // AI Assistant state
  const [aiMode, setAiMode] = useState("improve_summary");
  const [aiTargetRole, setAiTargetRole] = useState("");
  const [aiNotes, setAiNotes] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiResult, setAiResult] = useState<AIPortfolioAssistResult | null>(null);

  // Version snapshot note
  const [versionNote, setVersionNote] = useState("");

  // 1. Initial Load
  const loadPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [portRes, lProjectsRes] = await Promise.allSettled([
        portfoliosApi.getMyPortfolio(),
        learningRoadmapsApi.listProjects(),
      ]);

      if (portRes.status === "fulfilled") {
        const p = portRes.value;
        setPortfolio(p);
        setCustomSlug(p.public_slug);

        // Prepopulate profile form
        const prof = p.profile_data || {};
        setFullName(prof.full_name || "");
        setHeadline(p.headline || prof.headline || "");
        setSummary(prof.summary || "");
        setLocation(prof.location || "");
        setTargetRoles((prof.target_roles || []).join(", "));
        setSkillsInput((prof.technical_skills || []).join(", "));
        setContactEmail(prof.contact_email || "");
        setPhone(prof.phone || "");
        setGithubUrl(prof.github_url || "");
        setLinkedinUrl(prof.linkedin_url || "");
        setWebsiteUrl(prof.website_url || "");

        // Prepopulate theme
        setSelectedTemplate(p.template_id || "minimal");
        setAccentColor(p.theme_config?.accent_color || "#3B82F6");
        setFontFamily(p.theme_config?.font_family || "inter");
        setDarkMode(p.theme_config?.dark_mode || "system");
      }

      if (lProjectsRes.status === "fulfilled") {
        setLearningProjects(lProjectsRes.value);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load portfolio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  // Load analytics when analytics tab is opened
  useEffect(() => {
    if (activeTab === "analytics") {
      portfoliosApi
        .getAnalytics()
        .then(setAnalytics)
        .catch((e) => console.error("Error loading analytics:", e));
    } else if (activeTab === "versions") {
      portfoliosApi
        .listVersions()
        .then(setVersions)
        .catch((e) => console.error("Error loading versions:", e));
    }
  }, [activeTab]);

  const showFeedback = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3500);
  };

  // 2. Save Profile Data
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const skillsArr = skillsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const rolesArr = targetRoles
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const existingProf = (portfolio?.profile_data || {}) as Partial<PortfolioProfileData>;
      const updatedProf: PortfolioProfileData = {
        full_name: fullName,
        headline,
        avatar_url: existingProf.avatar_url || null,
        summary,
        location,
        target_roles: rolesArr,
        technical_skills: skillsArr,
        contact_email: contactEmail || null,
        phone: phone || null,
        github_url: githubUrl || null,
        linkedin_url: linkedinUrl || null,
        website_url: websiteUrl || null,
        education: existingProf.education || [],
        work_experience: existingProf.work_experience || [],
        certifications: existingProf.certifications || [],
        achievements: existingProf.achievements || [],
      };

      const updated = await portfoliosApi.updateProfile({
        title: `${fullName} Portfolio`,
        headline,
        profile_data: updatedProf,
      });

      setPortfolio(updated);
      showFeedback("Profile details saved successfully.");
    } catch (err: any) {
      alert(`Save failed: ${err?.message}`);
    } finally {
      setSaving(false);
    }
  };

  // 3. Save Theme & Template
  const handleSaveTheme = async (templateId: string, color: string, font: string, mode: string) => {
    setSelectedTemplate(templateId);
    setAccentColor(color);
    setFontFamily(font);
    setDarkMode(mode);

    try {
      const updated = await portfoliosApi.updateTheme({
        template_id: templateId,
        theme_config: {
          accent_color: color,
          font_family: font,
          dark_mode: mode,
          show_contact_form: false,
          show_view_counter: true,
        },
      });
      setPortfolio(updated);
      showFeedback("Theme and template updated.");
    } catch (err: any) {
      alert(`Theme update failed: ${err?.message}`);
    }
  };

  // 4. Update Slug
  const handleUpdateSlug = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingSlug(true);
    try {
      const updated = await portfoliosApi.updateSlug(customSlug);
      setPortfolio(updated);
      showFeedback("Public URL slug updated successfully.");
    } catch (err: any) {
      alert(`Slug update failed: ${err?.message}`);
    } finally {
      setIsUpdatingSlug(false);
    }
  };

  // 5. Toggle Publishing
  const handleTogglePublish = async () => {
    if (!portfolio) return;
    try {
      const updated = portfolio.is_published
        ? await portfoliosApi.unpublish()
        : await portfoliosApi.publish();
      setPortfolio(updated);
      showFeedback(
        updated.is_published
          ? "Portfolio is now published and live to recruiters!"
          : "Portfolio has been unpublished and revoked from public view."
      );
    } catch (err: any) {
      alert(`Publish action failed: ${err?.message}`);
    }
  };

  // 6. Section Ordering & Visibility
  const handleMoveSection = async (index: number, direction: "up" | "down") => {
    if (!portfolio) return;
    const secs = [...portfolio.sections];
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= secs.length) return;

    // Swap order
    const temp = secs[index];
    secs[index] = secs[targetIdx];
    secs[targetIdx] = temp;

    const payload = secs.map((s, idx) => ({
      id: s.id,
      order_index: idx,
      is_visible: s.is_visible,
    }));

    try {
      const updatedSecs = await portfoliosApi.reorderSections(payload);
      setPortfolio({ ...portfolio, sections: updatedSecs });
    } catch (err: any) {
      alert(`Failed to reorder: ${err?.message}`);
    }
  };

  const handleToggleSectionVisible = async (section: PortfolioSection) => {
    if (!portfolio) return;
    try {
      const updatedSec = await portfoliosApi.updateSection(section.id, {
        is_visible: !section.is_visible,
      });
      setPortfolio({
        ...portfolio,
        sections: portfolio.sections.map((s) => (s.id === updatedSec.id ? updatedSec : s)),
      });
    } catch (err: any) {
      alert(`Failed to update visibility: ${err?.message}`);
    }
  };

  // 7. Save / Edit Project
  const handleSaveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const stackArr = projStack
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const featArr = projFeatures
        .split("\n")
        .map((f) => f.trim())
        .filter(Boolean);

      if (projectToEdit) {
        await portfoliosApi.updateProject(projectToEdit.id, {
          title: projTitle,
          problem_statement: projProblem || undefined,
          description: projDesc,
          tech_stack: stackArr,
          key_features: featArr,
          architecture_overview: projArch || undefined,
          repository_url: projRepo || undefined,
          live_demo_url: projDemo || undefined,
          outcomes: projOutcomes || undefined,
          status: projStatus,
          is_featured: projFeatured,
        });
        showFeedback("Project updated.");
      } else {
        await portfoliosApi.createProject({
          title: projTitle,
          problem_statement: projProblem || undefined,
          description: projDesc,
          tech_stack: stackArr,
          key_features: featArr,
          architecture_overview: projArch || undefined,
          repository_url: projRepo || undefined,
          live_demo_url: projDemo || undefined,
          outcomes: projOutcomes || undefined,
          status: projStatus,
          is_featured: projFeatured,
        });
        showFeedback("Project added to portfolio.");
      }

      setShowAddProjectModal(false);
      setProjectToEdit(null);
      resetProjectForm();
      const updated = await portfoliosApi.getMyPortfolio();
      setPortfolio(updated);
    } catch (err: any) {
      alert(`Project save failed: ${err?.message}`);
    }
  };

  const resetProjectForm = () => {
    setProjTitle("");
    setProjProblem("");
    setProjDesc("");
    setProjStack("");
    setProjFeatures("");
    setProjArch("");
    setProjRepo("");
    setProjDemo("");
    setProjOutcomes("");
    setProjStatus("completed");
    setProjFeatured(false);
  };

  const openEditProject = (p: PortfolioProjectItem) => {
    setProjectToEdit(p);
    setProjTitle(p.title);
    setProjProblem(p.problem_statement || "");
    setProjDesc(p.description);
    setProjStack((p.tech_stack || []).join(", "));
    setProjFeatures((p.key_features || []).join("\n"));
    setProjArch(p.architecture_overview || "");
    setProjRepo(p.repository_url || "");
    setProjDemo(p.live_demo_url || "");
    setProjOutcomes(p.outcomes || "");
    setProjStatus(p.status);
    setProjFeatured(p.is_featured);
    setShowAddProjectModal(true);
  };

  const handleDeleteProject = async (id: string) => {
    if (!confirm("Are you sure you want to remove this project from your portfolio?")) return;
    try {
      await portfoliosApi.deleteProject(id);
      if (portfolio) {
        setPortfolio({
          ...portfolio,
          projects: portfolio.projects.filter((p) => p.id !== id),
        });
      }
      showFeedback("Project removed.");
    } catch (err: any) {
      alert(`Delete failed: ${err?.message}`);
    }
  };

  const handleImportLearningProject = async (learningProjectId: string) => {
    try {
      await portfoliosApi.importLearningProject(learningProjectId);
      const updated = await portfoliosApi.getMyPortfolio();
      setPortfolio(updated);
      showFeedback("Imported project from Learning Roadmap!");
    } catch (err: any) {
      alert(`Import failed: ${err?.message}`);
    }
  };

  const handleImportResume = async () => {
    if (!confirm("Import verified skills and work history from your latest uploaded resume?"))
      return;
    try {
      const updated = await portfoliosApi.importFromResume();
      setPortfolio(updated);
      const prof = updated.profile_data || {};
      setFullName(prof.full_name || fullName);
      setSummary(prof.summary || summary);
      setSkillsInput((prof.technical_skills || []).join(", "));
      showFeedback("Imported career information from Resume Studio!");
    } catch (err: any) {
      alert(`Resume import failed: ${err?.message}`);
    }
  };

  // 8. AI Assistant
  const handleRunAIAssist = async () => {
    setAiGenerating(true);
    setAiResult(null);
    try {
      const res = await portfoliosApi.aiAssist({
        assist_type: aiMode,
        current_text: aiMode === "improve_summary" ? summary : undefined,
        target_role: aiTargetRole || (headline || "Software Engineer"),
        rough_notes: aiNotes || undefined,
        tech_stack: skillsInput.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setAiResult(res);
    } catch (err: any) {
      alert(`AI Assistant failed: ${err?.message}`);
    } finally {
      setAiGenerating(false);
    }
  };

  const handleApplyAIResult = () => {
    if (!aiResult) return;
    if (aiMode === "improve_summary") {
      setSummary(aiResult.suggested_content);
      showFeedback("Summary updated with AI suggestion! Click 'Save Details' to persist.");
    } else if (aiMode === "role_tailoring") {
      setHeadline(aiResult.suggested_content);
      showFeedback("Headline updated! Click 'Save Details' to persist.");
    }
    setShowAIAssistModal(false);
  };

  // 9. Version Snapshot & Restore
  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await portfoliosApi.createVersion(versionNote || "Manual Snapshot");
      setShowVersionModal(false);
      setVersionNote("");
      const updatedVers = await portfoliosApi.listVersions();
      setVersions(updatedVers);
      showFeedback("Portfolio version snapshot captured!");
    } catch (err: any) {
      alert(`Snapshot failed: ${err?.message}`);
    }
  };

  const handleRestoreVersion = async (verId: string) => {
    if (!confirm("Restore portfolio to this version? Any unsaved edits will be replaced."))
      return;
    try {
      const restored = await portfoliosApi.restoreVersion(verId);
      setPortfolio(restored);
      showFeedback("Portfolio restored to snapshot state.");
      loadPortfolio();
    } catch (err: any) {
      alert(`Restore failed: ${err?.message}`);
    }
  };

  // Copy public link
  const copyPublicLink = () => {
    if (!portfolio) return;
    const url = `${window.location.origin}/portfolio/${portfolio.public_slug}`;
    navigator.clipboard.writeText(url);
    showFeedback("Public portfolio link copied to clipboard!");
  };

  return (
    <div className="min-h-screen bg-background text-foreground pb-24">
      {/* Top Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Layout className="w-5 h-5" />
                </span>
                <span className="text-xs uppercase tracking-wider font-semibold text-primary">
                  Portfolio Studio & Showcase
                </span>
                {portfolio?.is_published ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                    <CheckCircle2 className="w-3 h-3" /> Live & Published
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-secondary text-muted-foreground border border-border">
                    <Clock className="w-3 h-3" /> Private Draft
                  </span>
                )}
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground mt-1">
                Recruiter-Ready Career Portfolio Studio
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl">
                Create, customize, preview, and publish your evidence-backed engineering portfolio
                with verified projects, architecture breakdowns, and downloadable formats.
              </p>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center flex-wrap gap-2.5">
              <button
                onClick={() => setShowAIAssistModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                AI Assistant
              </button>

              <button
                onClick={handleTogglePublish}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all shadow-sm ${
                  portfolio?.is_published
                    ? "bg-amber-500/10 text-amber-600 border border-amber-500/30 hover:bg-amber-500/20"
                    : "bg-emerald-600 text-white hover:bg-emerald-700"
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                {portfolio?.is_published ? "Unpublish" : "Publish to Web"}
              </button>

              {portfolio?.is_published && (
                <button
                  onClick={copyPublicLink}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                  title="Copy public link"
                >
                  <Share2 className="w-3.5 h-3.5 text-primary" />
                  Share Link
                </button>
              )}

              {/* Exports Dropdown */}
              <a
                href="/api/v1/portfolios/export/pdf"
                target="_blank"
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> PDF
              </a>
              <a
                href="/api/v1/portfolios/export/html"
                target="_blank"
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
              >
                <FileCode className="w-3.5 h-3.5" /> HTML
              </a>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 mt-6 overflow-x-auto border-b border-border/50 pb-px">
            <button
              onClick={() => setActiveTab("editor")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "editor"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <User className="w-4 h-4" />
              Profile & Experience
            </button>

            <button
              onClick={() => setActiveTab("projects")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "projects"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Code2 className="w-4 h-4" />
              Showcase Projects
              {portfolio && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-primary/10 text-primary font-mono">
                  {portfolio.projects.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("sections")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "sections"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Layers className="w-4 h-4" />
              Sections & Order
            </button>

            <button
              onClick={() => setActiveTab("themes")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "themes"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Palette className="w-4 h-4" />
              Templates & Themes
            </button>

            <button
              onClick={() => setActiveTab("preview")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "preview"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Eye className="w-4 h-4" />
              Live Preview
            </button>

            <button
              onClick={() => setActiveTab("analytics")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "analytics"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <BarChart2 className="w-4 h-4" />
              Visitor Analytics
            </button>

            <button
              onClick={() => setActiveTab("versions")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "versions"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Clock className="w-4 h-4" />
              Version History
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        {/* Success toast banner */}
        {successMsg && (
          <div className="mb-6 p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <span className="font-medium">{successMsg}</span>
            </div>
            <button
              onClick={() => setSuccessMsg(null)}
              className="text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          </div>
        )}

        {/* Public Shareable Link Alert */}
        {portfolio?.is_published && (
          <div className="mb-6 p-4 rounded-2xl border border-primary/30 bg-gradient-to-r from-card via-card to-primary/5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600">
                <Globe className="w-5 h-5" />
              </span>
              <div>
                <span className="text-xs font-bold text-foreground">
                  Your Public Recruiter Portfolio is Live!
                </span>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Available publicly at:{" "}
                  <code className="px-1.5 py-0.5 rounded bg-secondary font-mono text-primary text-[11px]">
                    /portfolio/{portfolio.public_slug}
                  </code>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <Link
                href={`/portfolio/${portfolio.public_slug}`}
                target="_blank"
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1 transition-all"
              >
                Open Live Site <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
              <button
                onClick={copyPublicLink}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 flex items-center gap-1 transition-colors"
              >
                <Copy className="w-3.5 h-3.5 text-muted-foreground" /> Copy
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center text-muted-foreground gap-3">
            <Layout className="w-10 h-10 animate-spin text-primary" />
            <p className="text-sm">Loading Portfolio Studio...</p>
          </div>
        ) : (
          <>
            {/* TAB 1: PROFILE EDITOR */}
            {activeTab === "editor" && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-8">
                  <div className="p-6 rounded-2xl border border-border bg-card shadow-sm space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-base font-bold text-foreground">
                          Candidate Profile Information
                        </h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Edit the core profile data presented across your portfolio templates.
                        </p>
                      </div>

                      <button
                        onClick={handleImportResume}
                        className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors flex items-center gap-1.5"
                      >
                        <RefreshCw className="w-3.5 h-3.5 text-primary" />
                        Pre-fill from Resume
                      </button>
                    </div>

                    <form onSubmit={handleSaveProfile} className="space-y-4">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Full Professional Name
                          </label>
                          <input
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            required
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>

                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Professional Headline
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. Distributed Systems & AI Engineer"
                            value={headline}
                            onChange={(e) => setHeadline(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-xs font-semibold text-muted-foreground">
                            Professional Summary / Bio
                          </label>
                          <button
                            type="button"
                            onClick={() => {
                              setAiMode("improve_summary");
                              setShowAIAssistModal(true);
                            }}
                            className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
                          >
                            <Sparkles className="w-3 h-3" /> Polish with AI
                          </button>
                        </div>
                        <textarea
                          rows={4}
                          value={summary}
                          onChange={(e) => setSummary(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed"
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Location (City, Country)
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. San Francisco, CA"
                            value={location}
                            onChange={(e) => setLocation(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>

                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Target Roles (comma-separated)
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. Backend Engineer, Systems Architect"
                            value={targetRoles}
                            onChange={(e) => setTargetRoles(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-muted-foreground block mb-1">
                          Technical Skills (comma-separated)
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. Python, FastAPI, Docker, Redis, PostgreSQL, Kubernetes"
                          value={skillsInput}
                          onChange={(e) => setSkillsInput(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Public Contact Email
                          </label>
                          <input
                            type="email"
                            placeholder="jane@example.com"
                            value={contactEmail}
                            onChange={(e) => setContactEmail(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>

                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Phone (Optional)
                          </label>
                          <input
                            type="text"
                            placeholder="+1 (555) 000-0000"
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            GitHub Profile URL
                          </label>
                          <input
                            type="url"
                            placeholder="https://github.com/username"
                            value={githubUrl}
                            onChange={(e) => setGithubUrl(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>

                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            LinkedIn Profile URL
                          </label>
                          <input
                            type="url"
                            placeholder="https://linkedin.com/in/username"
                            value={linkedinUrl}
                            onChange={(e) => setLinkedinUrl(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>

                        <div>
                          <label className="text-xs font-semibold text-muted-foreground block mb-1">
                            Website / Blog URL
                          </label>
                          <input
                            type="url"
                            placeholder="https://myblog.dev"
                            value={websiteUrl}
                            onChange={(e) => setWebsiteUrl(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>

                      <div className="pt-4 flex items-center justify-end">
                        <button
                          type="submit"
                          disabled={saving}
                          className="px-5 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all shadow-sm"
                        >
                          {saving ? "Saving Changes..." : "Save Profile Details"}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>

                {/* Right Panel: Slug & Publishing Controls */}
                <div className="lg:col-span-4 space-y-6">
                  {/* Public Slug Customizer */}
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-foreground">Custom Public URL</h3>
                    <p className="text-xs text-muted-foreground">
                      Choose an unguessable or personalized slug for your public portfolio link.
                    </p>

                    <form onSubmit={handleUpdateSlug} className="space-y-3">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground font-mono bg-secondary/50 px-3 py-2 rounded-lg border border-border">
                        <span className="text-muted-foreground">/portfolio/</span>
                        <input
                          type="text"
                          value={customSlug}
                          onChange={(e) => setCustomSlug(e.target.value)}
                          required
                          className="bg-transparent focus:outline-none text-foreground font-semibold flex-1"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={isUpdatingSlug || customSlug === portfolio?.public_slug}
                        className="w-full px-3 py-1.5 text-xs font-semibold rounded-lg bg-secondary hover:bg-secondary/80 text-foreground disabled:opacity-50 transition-colors"
                      >
                        {isUpdatingSlug ? "Updating..." : "Update Slug"}
                      </button>
                    </form>
                  </div>

                  {/* Portfolio Completeness Card */}
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-foreground">Portfolio Health</h3>
                    <div className="space-y-2 text-xs text-muted-foreground">
                      <div className="flex items-center justify-between">
                        <span>Profile Details:</span>
                        <span className="font-semibold text-emerald-600">Complete</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Featured Projects:</span>
                        <span className="font-semibold text-foreground font-mono">
                          {portfolio?.projects.length || 0} projects
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Visible Sections:</span>
                        <span className="font-semibold text-foreground font-mono">
                          {portfolio?.sections.filter((s) => s.is_visible).length || 0} sections
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Selected Template:</span>
                        <span className="capitalize font-semibold text-primary">
                          {portfolio?.template_id}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: PROJECTS SHOWCASE */}
            {activeTab === "projects" && (
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-bold text-foreground">
                      Showcase Projects ({portfolio?.projects.length || 0})
                    </h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Highlight evidence-backed engineering projects. Only visible projects will
                      appear on your public portfolio.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {learningProjects.length > 0 && (
                      <select
                        onChange={(e) => {
                          if (e.target.value) {
                            handleImportLearningProject(e.target.value);
                            e.target.value = "";
                          }
                        }}
                        className="px-3 py-1.5 text-xs rounded-lg border border-border bg-secondary text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        defaultValue=""
                      >
                        <option value="" disabled>
                          + Import from Learning Roadmap...
                        </option>
                        {learningProjects.map((lp) => (
                          <option key={lp.id} value={lp.id}>
                            {lp.title}
                          </option>
                        ))}
                      </select>
                    )}

                    <button
                      onClick={() => {
                        resetProjectForm();
                        setProjectToEdit(null);
                        setShowAddProjectModal(true);
                      }}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1.5 transition-all shadow-sm"
                    >
                      <Plus className="w-4 h-4" /> Add Project
                    </button>
                  </div>
                </div>

                {portfolio?.projects.length === 0 ? (
                  <div className="p-12 rounded-2xl border border-dashed border-border text-center">
                    <Code2 className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
                    <h3 className="text-sm font-semibold text-foreground">No Projects Added Yet</h3>
                    <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                      Add a technical project with repository links, architectural notes, and tech
                      stack, or import directly from your Learning Roadmap.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {portfolio?.projects.map((p) => (
                      <div
                        key={p.id}
                        className={`p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                          p.is_visible
                            ? "border-border bg-card shadow-sm"
                            : "border-border/50 bg-secondary/30 opacity-70"
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                  p.status === "completed"
                                    ? "bg-emerald-500/10 text-emerald-600"
                                    : "bg-blue-500/10 text-blue-600"
                                }`}
                              >
                                {p.status}
                              </span>
                              {p.is_featured && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-500">
                                  <Star className="w-3 h-3 fill-amber-500" /> Featured
                                </span>
                              )}
                            </div>

                            <span
                              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                                p.is_visible
                                  ? "bg-emerald-500/10 text-emerald-600"
                                  : "bg-muted text-muted-foreground"
                              }`}
                            >
                              {p.is_visible ? "Public" : "Hidden"}
                            </span>
                          </div>

                          <h3 className="text-sm font-bold text-foreground">{p.title}</h3>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-3 leading-relaxed">
                            {p.description}
                          </p>

                          {p.architecture_overview && (
                            <p className="text-[11px] text-muted-foreground mt-2 line-clamp-2 italic">
                              <strong className="font-semibold text-foreground not-italic">
                                Architecture:
                              </strong>{" "}
                              {p.architecture_overview}
                            </p>
                          )}

                          <div className="flex flex-wrap gap-1 mt-3">
                            {p.tech_stack.map((t, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.2 rounded text-[10px] bg-secondary text-secondary-foreground font-mono"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                          <div className="flex items-center gap-3 text-xs">
                            {p.repository_url && (
                              <a
                                href={p.repository_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline flex items-center gap-1"
                              >
                                <ExternalLink className="w-3 h-3" /> Code
                              </a>
                            )}
                            {p.live_demo_url && (
                              <a
                                href={p.live_demo_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline flex items-center gap-1"
                              >
                                <Play className="w-3 h-3" /> Demo
                              </a>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => openEditProject(p)}
                              className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteProject(p.id)}
                              className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                              title="Delete project"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: SECTIONS & ORDER */}
            {activeTab === "sections" && (
              <div className="max-w-2xl mx-auto space-y-6">
                <div>
                  <h2 className="text-base font-bold text-foreground">Section Ordering & Visibility</h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Reorder sections and toggle which sections are displayed to recruiters on your
                    public portfolio.
                  </p>
                </div>

                <div className="space-y-2.5">
                  {portfolio?.sections.map((sec, idx) => (
                    <div
                      key={sec.id}
                      className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
                        sec.is_visible
                          ? "border-border bg-card shadow-sm"
                          : "border-border/60 bg-secondary/30 opacity-60"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs text-muted-foreground w-4">
                          {idx + 1}.
                        </span>
                        <div>
                          <h4 className="text-xs font-bold text-foreground">{sec.title}</h4>
                          <span className="text-[10px] text-muted-foreground uppercase font-mono">
                            Type: {sec.section_type}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggleSectionVisible(sec)}
                          className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
                            sec.is_visible
                              ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {sec.is_visible ? "Visible" : "Hidden"}
                        </button>

                        <button
                          onClick={() => handleMoveSection(idx, "up")}
                          disabled={idx === 0}
                          className="p-1 rounded-md border border-border text-muted-foreground hover:text-foreground disabled:opacity-30"
                          title="Move Up"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleMoveSection(idx, "down")}
                          disabled={idx === (portfolio?.sections.length || 0) - 1}
                          className="p-1 rounded-md border border-border text-muted-foreground hover:text-foreground disabled:opacity-30"
                          title="Move Down"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 4: TEMPLATES & THEMES */}
            {activeTab === "themes" && (
              <div className="space-y-8">
                {/* 3 Template Cards */}
                <div>
                  <h2 className="text-base font-bold text-foreground mb-1">
                    Select Portfolio Layout
                  </h2>
                  <p className="text-xs text-muted-foreground mb-4">
                    Choose from 3 specialized engineering layouts designed for recruiters and
                    technical evaluators.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    {/* Minimal Professional */}
                    <div
                      onClick={() =>
                        handleSaveTheme("minimal", accentColor, fontFamily, darkMode)
                      }
                      className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                        selectedTemplate === "minimal"
                          ? "border-primary bg-primary/5 ring-2 ring-primary/20 shadow-md"
                          : "border-border bg-card hover:border-primary/50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary">
                          Recommended
                        </span>
                        {selectedTemplate === "minimal" && (
                          <Check className="w-4 h-4 text-primary" />
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-foreground">Minimal Professional</h3>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        Clean, elegant, recruiter-first presentation. Highlights summary, technical
                        competencies, work history timeline, and verified project cards.
                      </p>
                    </div>

                    {/* Developer Portfolio */}
                    <div
                      onClick={() =>
                        handleSaveTheme("developer", accentColor, fontFamily, darkMode)
                      }
                      className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                        selectedTemplate === "developer"
                          ? "border-primary bg-primary/5 ring-2 ring-primary/20 shadow-md"
                          : "border-border bg-card hover:border-primary/50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-secondary text-foreground">
                          Technical
                        </span>
                        {selectedTemplate === "developer" && (
                          <Check className="w-4 h-4 text-primary" />
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-foreground">Developer Portfolio</h3>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        Code-centric layout with monospace styling, terminal touches, architecture
                        diagrams, and deep technical repository highlights.
                      </p>
                    </div>

                    {/* AI / Technology Portfolio */}
                    <div
                      onClick={() =>
                        handleSaveTheme("ai_tech", accentColor, fontFamily, darkMode)
                      }
                      className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                        selectedTemplate === "ai_tech"
                          ? "border-primary bg-primary/5 ring-2 ring-primary/20 shadow-md"
                          : "border-border bg-card hover:border-primary/50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-secondary text-foreground">
                          AI & ML
                        </span>
                        {selectedTemplate === "ai_tech" && (
                          <Check className="w-4 h-4 text-primary" />
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-foreground">
                        AI & Technology Portfolio
                      </h3>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        Modern theme suited for AI/ML engineers, technical founders, and researchers
                        showcasing models, system benchmarks, and live demo links.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Accent Colors */}
                <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                  <h3 className="text-sm font-bold text-foreground">Accent Color</h3>
                  <div className="flex flex-wrap gap-3">
                    {COLOR_PRESETS.map((c) => (
                      <button
                        key={c.hex}
                        onClick={() =>
                          handleSaveTheme(selectedTemplate, c.hex, fontFamily, darkMode)
                        }
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                          accentColor === c.hex
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border hover:border-border/80"
                        }`}
                      >
                        <span
                          className="w-3.5 h-3.5 rounded-full"
                          style={{ backgroundColor: c.hex }}
                        />
                        {c.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Typography & Mode */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-foreground">Typography</h3>
                    <div className="grid grid-cols-3 gap-2">
                      {["inter", "system", "mono"].map((font) => (
                        <button
                          key={font}
                          onClick={() =>
                            handleSaveTheme(selectedTemplate, accentColor, font, darkMode)
                          }
                          className={`px-3 py-2 text-xs font-semibold rounded-lg border capitalize transition-all ${
                            fontFamily === font
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:bg-secondary/40"
                          }`}
                        >
                          {font}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-foreground">Color Mode</h3>
                    <div className="grid grid-cols-3 gap-2">
                      {["system", "dark", "light"].map((mode) => (
                        <button
                          key={mode}
                          onClick={() =>
                            handleSaveTheme(selectedTemplate, accentColor, fontFamily, mode)
                          }
                          className={`px-3 py-2 text-xs font-semibold rounded-lg border capitalize transition-all ${
                            darkMode === mode
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:bg-secondary/40"
                          }`}
                        >
                          {mode}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 5: LIVE PREVIEW */}
            {activeTab === "preview" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPreviewDevice("desktop")}
                      className={`px-3 py-1 text-xs font-medium rounded-lg border flex items-center gap-1.5 transition-colors ${
                        previewDevice === "desktop"
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground"
                      }`}
                    >
                      <Monitor className="w-3.5 h-3.5" /> Desktop
                    </button>
                    <button
                      onClick={() => setPreviewDevice("mobile")}
                      className={`px-3 py-1 text-xs font-medium rounded-lg border flex items-center gap-1.5 transition-colors ${
                        previewDevice === "mobile"
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground"
                      }`}
                    >
                      <Smartphone className="w-3.5 h-3.5" /> Mobile
                    </button>
                  </div>

                  {portfolio?.is_published && (
                    <Link
                      href={`/portfolio/${portfolio.public_slug}`}
                      target="_blank"
                      className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                    >
                      Open in New Tab <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>

                {/* Simulated Device Frame */}
                <div className="flex justify-center bg-secondary/30 p-4 sm:p-6 rounded-2xl border border-border">
                  <div
                    className={`bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl transition-all duration-300 ${
                      previewDevice === "mobile"
                        ? "w-[375px] min-h-[667px]"
                        : "w-full max-w-[850px] min-h-[600px]"
                    }`}
                  >
                    {/* Simulated browser top bar */}
                    <div className="bg-slate-800 px-4 py-2 border-b border-slate-700 flex items-center gap-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 mx-auto">
                        nexora.dev/portfolio/{portfolio?.public_slug}
                      </span>
                    </div>

                    {/* Preview Content */}
                    <div className="p-6 text-slate-100 space-y-6 overflow-y-auto max-h-[700px]">
                      <div className="border-b border-slate-800 pb-4">
                        <h2 className="text-xl font-black text-white">
                          {portfolio?.profile_data.full_name || "Candidate Name"}
                        </h2>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {portfolio?.headline || "Software Engineer"}
                        </p>
                        {portfolio?.profile_data.location && (
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            {portfolio.profile_data.location}
                          </p>
                        )}
                      </div>

                      {/* Summary */}
                      {portfolio?.profile_data.summary && (
                        <div>
                          <span
                            className="text-[11px] font-bold uppercase tracking-wider block mb-1"
                            style={{ color: accentColor }}
                          >
                            About
                          </span>
                          <p className="text-xs text-slate-300 leading-relaxed">
                            {portfolio.profile_data.summary}
                          </p>
                        </div>
                      )}

                      {/* Skills */}
                      {portfolio?.profile_data.technical_skills &&
                        portfolio.profile_data.technical_skills.length > 0 && (
                          <div>
                            <span
                              className="text-[11px] font-bold uppercase tracking-wider block mb-2"
                              style={{ color: accentColor }}
                            >
                              Technical Skills
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {portfolio.profile_data.technical_skills.map((s, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 border border-slate-700 text-slate-300"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Projects */}
                      {portfolio?.projects && portfolio.projects.length > 0 && (
                        <div>
                          <span
                            className="text-[11px] font-bold uppercase tracking-wider block mb-2"
                            style={{ color: accentColor }}
                          >
                            Featured Projects
                          </span>
                          <div className="space-y-3">
                            {portfolio.projects
                              .filter((p) => p.is_visible)
                              .map((p) => (
                                <div
                                  key={p.id}
                                  className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1.5"
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-white">
                                      {p.title}
                                    </span>
                                    <span className="text-[10px] text-emerald-400 font-mono">
                                      {p.status}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-slate-300 leading-relaxed">
                                    {p.description}
                                  </p>
                                  <div className="flex flex-wrap gap-1 pt-1">
                                    {p.tech_stack.map((t, i) => (
                                      <span
                                        key={i}
                                        className="text-[9px] px-1.5 py-0.2 rounded bg-slate-700 text-slate-300 font-mono"
                                      >
                                        {t}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 6: VISITOR ANALYTICS */}
            {activeTab === "analytics" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-foreground">
                      Privacy-Conscious Visitor Analytics
                    </h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Aggregated view counts and engagement metrics without collecting visitor PII.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Total Portfolio Visits</span>
                    <span className="block text-2xl font-black text-foreground font-mono mt-1">
                      {analytics?.total_views || 0}
                    </span>
                    <span className="text-[10px] text-emerald-600 mt-1 block">
                      Recruiter page views
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Project Interactions</span>
                    <span className="block text-2xl font-black text-primary font-mono mt-1">
                      {analytics?.project_views || 0}
                    </span>
                    <span className="text-[10px] text-muted-foreground mt-1 block">
                      Demo and repo clicks
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Portfolio Downloads</span>
                    <span className="block text-2xl font-black text-emerald-600 font-mono mt-1">
                      {analytics?.downloads_count || 0}
                    </span>
                    <span className="text-[10px] text-muted-foreground mt-1 block">
                      PDF & HTML exports
                    </span>
                  </div>
                </div>

                {/* Top Viewed Projects */}
                {analytics && analytics.top_viewed_projects.length > 0 && (
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm">
                    <h3 className="text-sm font-bold text-foreground mb-3">
                      Most Viewed Projects
                    </h3>
                    <div className="space-y-2">
                      {analytics.top_viewed_projects.map((proj, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-3 rounded-xl bg-secondary/30 border border-border/70"
                        >
                          <span className="text-xs font-semibold text-foreground">
                            {proj.title}
                          </span>
                          <span className="text-xs font-mono font-bold text-primary">
                            {proj.views} views
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Referrers & Devices */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm">
                    <h3 className="text-sm font-bold text-foreground mb-3">Referrer Sources</h3>
                    {analytics && Object.keys(analytics.referrers).length > 0 ? (
                      <div className="space-y-2">
                        {Object.entries(analytics.referrers).map(([ref, cnt]) => (
                          <div
                            key={ref}
                            className="flex items-center justify-between text-xs py-1 border-b border-border/40"
                          >
                            <span className="capitalize font-medium text-foreground">{ref}</span>
                            <span className="font-mono text-muted-foreground">{cnt} visits</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">No referrer data yet.</p>
                    )}
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm">
                    <h3 className="text-sm font-bold text-foreground mb-3">Visitor Devices</h3>
                    {analytics && Object.keys(analytics.devices).length > 0 ? (
                      <div className="space-y-2">
                        {Object.entries(analytics.devices).map(([dev, cnt]) => (
                          <div
                            key={dev}
                            className="flex items-center justify-between text-xs py-1 border-b border-border/40"
                          >
                            <span className="capitalize font-medium text-foreground">{dev}</span>
                            <span className="font-mono text-muted-foreground">{cnt} visits</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">No device data yet.</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 7: VERSION HISTORY */}
            {activeTab === "versions" && (
              <div className="space-y-6 max-w-3xl mx-auto">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-foreground">Portfolio Versions</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Immutable snapshots of your portfolio state. Restore previously saved drafts
                      at any time.
                    </p>
                  </div>

                  <button
                    onClick={() => setShowVersionModal(true)}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1.5 transition-all shadow-sm"
                  >
                    <Bookmark className="w-3.5 h-3.5" /> Save Snapshot
                  </button>
                </div>

                <div className="space-y-3">
                  {versions.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-10 text-center italic">
                      No version snapshots found.
                    </p>
                  ) : (
                    versions.map((v) => (
                      <div
                        key={v.id}
                        className="p-4 rounded-xl border border-border bg-card shadow-sm flex items-center justify-between"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-foreground">
                              Version {v.version_number}
                            </span>
                            <span className="text-[11px] text-muted-foreground">
                              &bull; {new Date(v.created_at).toLocaleString()}
                            </span>
                          </div>
                          {v.change_summary && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {v.change_summary}
                            </p>
                          )}
                        </div>

                        <button
                          onClick={() => handleRestoreVersion(v.id)}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors flex items-center gap-1"
                        >
                          <Undo2 className="w-3.5 h-3.5 text-primary" /> Restore
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* MODAL 1: ADD / EDIT PROJECT */}
      {showAddProjectModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-xl w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">
                {projectToEdit ? "Edit Showcase Project" : "Add Showcase Project"}
              </h3>
              <button
                onClick={() => setShowAddProjectModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveProject} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Project Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Distributed Consensus Engine"
                  value={projTitle}
                  onChange={(e) => setProjTitle(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Problem Statement
                </label>
                <input
                  type="text"
                  placeholder="What business or technical problem does this solve?"
                  value={projProblem}
                  onChange={(e) => setProjProblem(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Description / Overview
                </label>
                <textarea
                  rows={3}
                  placeholder="Detailed technical explanation of what you built..."
                  value={projDesc}
                  onChange={(e) => setProjDesc(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Architecture Overview & Highlights
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Asynchronous worker pool communicating over Redis pub/sub with PostgreSQL ACID guarantees."
                  value={projArch}
                  onChange={(e) => setProjArch(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Tech Stack (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Python, FastAPI, Redis, Docker, PostgreSQL"
                  value={projStack}
                  onChange={(e) => setProjStack(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">
                    Repository URL
                  </label>
                  <input
                    type="url"
                    placeholder="https://github.com/..."
                    value={projRepo}
                    onChange={(e) => setProjRepo(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">
                    Live Demo URL
                  </label>
                  <input
                    type="url"
                    placeholder="https://demo..."
                    value={projDemo}
                    onChange={(e) => setProjDemo(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">
                    Status
                  </label>
                  <select
                    value={projStatus}
                    onChange={(e) => setProjStatus(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="completed">Completed</option>
                    <option value="in_progress">In Progress</option>
                    <option value="planning">Planning</option>
                  </select>
                </div>

                <div className="flex items-center gap-2 pt-5">
                  <input
                    type="checkbox"
                    id="featCheck"
                    checked={projFeatured}
                    onChange={(e) => setProjFeatured(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary w-4 h-4"
                  />
                  <label htmlFor="featCheck" className="text-xs font-medium text-foreground">
                    Featured Project
                  </label>
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddProjectModal(false)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary text-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
                >
                  Save Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: AI PORTFOLIO ASSISTANT */}
      {showAIAssistModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-primary/10 text-primary">
                  <Wand2 className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-foreground">AI Portfolio Assistant</h3>
              </div>
              <button
                onClick={() => setShowAIAssistModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Grounded AI assistant strictly bound by your provided information. Never fabricates
              skills or unearned achievements.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Assistance Task
                </label>
                <select
                  value={aiMode}
                  onChange={(e) => setAiMode(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="improve_summary">Refine Professional Summary</option>
                  <option value="role_tailoring">Tailor Headline for Target Role</option>
                  <option value="gap_analysis">Portfolio Completeness & Gap Check</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Target Role Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Senior Distributed Systems Engineer"
                  value={aiTargetRole}
                  onChange={(e) => setAiTargetRole(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Additional Notes / Focus Areas
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Emphasize high-concurrency Python and cloud architecture."
                  value={aiNotes}
                  onChange={(e) => setAiNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <button
                onClick={handleRunAIAssist}
                disabled={aiGenerating}
                className="w-full px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all shadow-sm flex items-center justify-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {aiGenerating ? "Generating Grounded Advice..." : "Generate Suggestion"}
              </button>

              {/* AI Output preview */}
              {aiResult && (
                <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 space-y-3">
                  <div>
                    <span className="text-[10px] font-mono uppercase font-bold text-primary block">
                      AI Proposal ({aiResult.is_fallback ? "Rule-Based Fallback" : "AI Provider"}):
                    </span>
                    <p className="text-xs text-foreground mt-1 leading-relaxed whitespace-pre-wrap">
                      {aiResult.suggested_content}
                    </p>
                  </div>

                  {aiResult.bullet_points.length > 0 && (
                    <ul className="space-y-1 pt-1 border-t border-border/50">
                      {aiResult.bullet_points.map((b, i) => (
                        <li key={i} className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                          <Check className="w-3 h-3 text-emerald-500" />
                          {b}
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="pt-2 flex items-center justify-end">
                    <button
                      onClick={handleApplyAIResult}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                    >
                      Apply Suggestion
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: SAVE VERSION SNAPSHOT */}
      {showVersionModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">Save Portfolio Version</h3>
              <button
                onClick={() => setShowVersionModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSnapshot} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Change Note / Summary
                </label>
                <input
                  type="text"
                  placeholder="e.g. Added Rate Limiter project and updated headline"
                  value={versionNote}
                  onChange={(e) => setVersionNote(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowVersionModal(false)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary text-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
                >
                  Save Snapshot
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
