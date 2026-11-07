"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  ArrowUpRight,
  Award,
  BarChart2,
  Bookmark,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Code2,
  Compass,
  ExternalLink,
  Filter,
  Flame,
  FolderGit2,
  GraduationCap,
  Layers,
  Play,
  Pause,
  Plus,
  Sparkles,
  Target,
  Trash2,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  LearningActivity,
  LearningAnalytics,
  LearningMilestone,
  LearningProject,
  LearningResource,
  LearningRoadmap,
  LearningRoadmapSummary,
  learningRoadmapsApi,
  PracticalExercise,
  SkillGapAnalysisResponse,
} from "@/lib/api";

type ActiveTab = "gaps" | "roadmaps" | "resources" | "projects" | "analytics";

const PRESET_TRACKS = [
  { key: "backend_python", label: "Backend Engineering (Python & FastAPI)" },
  { key: "fullstack", label: "Full-Stack Web (Next.js, TypeScript & Python)" },
  { key: "ai_ml", label: "Machine Learning & AI Engineering" },
  { key: "genai", label: "Generative AI & LLM Systems" },
  { key: "data_analyst", label: "Data Analyst & Analytics Engineer" },
  { key: "sde", label: "Software Development Engineer (Core CS & DSA)" },
];

export default function LearningRoadmapPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>("gaps");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [skillGaps, setSkillGaps] = useState<SkillGapAnalysisResponse | null>(null);
  const [roadmaps, setRoadmaps] = useState<LearningRoadmapSummary[]>([]);
  const [selectedRoadmap, setSelectedRoadmap] = useState<LearningRoadmap | null>(null);
  const [selectedRoadmapId, setSelectedRoadmapId] = useState<string | null>(null);
  const [resources, setResources] = useState<LearningResource[]>([]);
  const [projects, setProjects] = useState<LearningProject[]>([]);
  const [recommendedProjects, setRecommendedProjects] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<LearningAnalytics | null>(null);

  // Filters
  const [resourceSkillFilter, setResourceSkillFilter] = useState<string>("");
  const [resourceDiffFilter, setResourceDiffFilter] = useState<string>("");
  const [resourceCostFilter, setResourceCostFilter] = useState<string>("");

  // Modals
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [showLogActivityModal, setShowLogActivityModal] = useState(false);
  const [showAddResourceModal, setShowAddResourceModal] = useState(false);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState<LearningProject | null>(null);

  // Form states - Generate Roadmap
  const [genTargetRole, setGenTargetRole] = useState("backend_python");
  const [genCustomRole, setGenCustomRole] = useState("");
  const [genDifficulty, setGenDifficulty] = useState("intermediate");
  const [genSkillsInput, setGenSkillsInput] = useState("");
  const [genNotes, setGenNotes] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  // Form states - Log Activity
  const [actType, setActType] = useState("coding");
  const [actDuration, setActDuration] = useState("1.0");
  const [actSkill, setActSkill] = useState("");
  const [actNotes, setActNotes] = useState("");
  const [isLoggingAct, setIsLoggingAct] = useState(false);

  // Form states - Add Resource
  const [resSkill, setResSkill] = useState("");
  const [resTitle, setResTitle] = useState("");
  const [resProvider, setResProvider] = useState("");
  const [resUrl, setResUrl] = useState("");
  const [resCost, setResCost] = useState("free");
  const [resDifficulty, setResDifficulty] = useState("intermediate");
  const [resDesc, setResDesc] = useState("");
  const [isSavingResource, setIsSavingResource] = useState(false);

  // Form states - Edit Project
  const [editProjectStatus, setEditProjectStatus] = useState("in_progress");
  const [editRepoUrl, setEditRepoUrl] = useState("");
  const [editDemoUrl, setEditDemoUrl] = useState("");
  const [editArchOverview, setEditArchOverview] = useState("");
  const [isSavingProject, setIsSavingProject] = useState(false);

  // Expanded milestones accordion
  const [expandedMilestones, setExpandedMilestones] = useState<Record<string, boolean>>({});

  // 1. Initial Load
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [gapsRes, roadmapsRes, resourcesRes, projectsRes, recProjectsRes, analyticsRes] =
        await Promise.allSettled([
          learningRoadmapsApi.getSkillGaps(),
          learningRoadmapsApi.listRoadmaps(),
          learningRoadmapsApi.listResources(),
          learningRoadmapsApi.listProjects(),
          learningRoadmapsApi.getProjectRecommendations(),
          learningRoadmapsApi.getAnalytics(),
        ]);

      if (gapsRes.status === "fulfilled") setSkillGaps(gapsRes.value);
      if (roadmapsRes.status === "fulfilled") {
        setRoadmaps(roadmapsRes.value);
        if (roadmapsRes.value.length > 0 && !selectedRoadmapId) {
          setSelectedRoadmapId(roadmapsRes.value[0].id);
        }
      }
      if (resourcesRes.status === "fulfilled") setResources(resourcesRes.value);
      if (projectsRes.status === "fulfilled") setProjects(projectsRes.value);
      if (recProjectsRes.status === "fulfilled") setRecommendedProjects(recProjectsRes.value);
      if (analyticsRes.status === "fulfilled") setAnalytics(analyticsRes.value);
    } catch (err: any) {
      setError(err?.message || "Failed to load skill development data.");
    } finally {
      setLoading(false);
    }
  }, [selectedRoadmapId]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Load detailed roadmap when selectedRoadmapId changes
  useEffect(() => {
    if (!selectedRoadmapId) {
      setSelectedRoadmap(null);
      return;
    }
    let isMounted = true;
    learningRoadmapsApi
      .getRoadmap(selectedRoadmapId)
      .then((data) => {
        if (isMounted) {
          setSelectedRoadmap(data);
          // auto expand in-progress milestone
          const initialExpanded: Record<string, boolean> = {};
          data.milestones.forEach((m) => {
            if (m.status === "in_progress") initialExpanded[m.id] = true;
          });
          setExpandedMilestones((prev) => ({ ...initialExpanded, ...prev }));
        }
      })
      .catch((err) => console.error("Error loading roadmap detail:", err));
    return () => {
      isMounted = false;
    };
  }, [selectedRoadmapId]);

  // Handle roadmap creation
  const handleGenerateRoadmap = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    try {
      const targetRole =
        genTargetRole === "custom" ? genCustomRole || "Software Engineer" : genTargetRole;
      const customSkills = genSkillsInput
        ? genSkillsInput
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : [];

      const newRoadmap = await learningRoadmapsApi.createRoadmap({
        target_role: targetRole,
        custom_skills: customSkills,
        target_difficulty: genDifficulty,
        user_notes: genNotes || undefined,
      });

      setShowGenerateModal(false);
      setGenNotes("");
      setGenSkillsInput("");
      setGenCustomRole("");
      await loadAllData();
      setSelectedRoadmapId(newRoadmap.id);
      setActiveTab("roadmaps");
    } catch (err: any) {
      alert(`Roadmap generation failed: ${err?.message || "Unknown error"}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Toggle exercise completion
  const handleToggleExercise = async (
    milestone: LearningMilestone,
    exerciseIndex: number
  ) => {
    if (!selectedRoadmap) return;
    const updatedExercises = milestone.practical_exercises.map((ex, idx) => {
      if (idx === exerciseIndex) {
        return { ...ex, completed: !ex.completed };
      }
      return ex;
    });

    const allDone = updatedExercises.every((ex) => ex.completed);
    const newStatus = allDone ? "completed" : "in_progress";

    try {
      const updatedM = await learningRoadmapsApi.updateMilestone(milestone.id, {
        practical_exercises: updatedExercises,
        status: newStatus,
        completed_hours: allDone ? milestone.estimated_hours : milestone.completed_hours,
      });

      // Update state locally
      setSelectedRoadmap({
        ...selectedRoadmap,
        milestones: selectedRoadmap.milestones.map((m) =>
          m.id === updatedM.id ? updatedM : m
        ),
      });

      // Refresh summaries
      const updatedSummaries = await learningRoadmapsApi.listRoadmaps();
      setRoadmaps(updatedSummaries);
    } catch (err: any) {
      alert(`Failed to update exercise: ${err?.message}`);
    }
  };

  // Toggle milestone status
  const handleToggleMilestoneStatus = async (milestone: LearningMilestone) => {
    if (!selectedRoadmap) return;
    const nextStatus =
      milestone.status === "completed"
        ? "in_progress"
        : milestone.status === "in_progress"
        ? "completed"
        : "in_progress";

    try {
      const updatedM = await learningRoadmapsApi.updateMilestone(milestone.id, {
        status: nextStatus,
        completed_hours:
          nextStatus === "completed" ? milestone.estimated_hours : 0.0,
      });

      setSelectedRoadmap({
        ...selectedRoadmap,
        milestones: selectedRoadmap.milestones.map((m) =>
          m.id === updatedM.id ? updatedM : m
        ),
      });

      const updatedSummaries = await learningRoadmapsApi.listRoadmaps();
      setRoadmaps(updatedSummaries);
    } catch (err: any) {
      alert(`Failed to update milestone: ${err?.message}`);
    }
  };

  // Handle roadmap status toggle
  const handleToggleRoadmapStatus = async (roadmapId: string, currentStatus: string) => {
    const newStatus = currentStatus === "active" ? "paused" : "active";
    try {
      await learningRoadmapsApi.updateRoadmapStatus(roadmapId, newStatus);
      const updatedSummaries = await learningRoadmapsApi.listRoadmaps();
      setRoadmaps(updatedSummaries);
      if (selectedRoadmap && selectedRoadmap.id === roadmapId) {
        setSelectedRoadmap({ ...selectedRoadmap, status: newStatus });
      }
    } catch (err: any) {
      alert(`Failed to update roadmap: ${err?.message}`);
    }
  };

  // Handle delete roadmap
  const handleDeleteRoadmap = async (roadmapId: string) => {
    if (!confirm("Are you sure you want to delete this learning roadmap?")) return;
    try {
      await learningRoadmapsApi.deleteRoadmap(roadmapId);
      const updatedSummaries = await learningRoadmapsApi.listRoadmaps();
      setRoadmaps(updatedSummaries);
      if (selectedRoadmapId === roadmapId) {
        setSelectedRoadmapId(updatedSummaries.length > 0 ? updatedSummaries[0].id : null);
      }
    } catch (err: any) {
      alert(`Failed to delete roadmap: ${err?.message}`);
    }
  };

  // Handle Log Activity
  const handleLogActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingAct(true);
    try {
      await learningRoadmapsApi.logActivity({
        activity_type: actType,
        duration_hours: parseFloat(actDuration) || 1.0,
        skill: actSkill || undefined,
        notes: actNotes || undefined,
        roadmap_id: selectedRoadmapId || undefined,
      });

      setShowLogActivityModal(false);
      setActNotes("");
      setActSkill("");
      const updatedAnalytics = await learningRoadmapsApi.getAnalytics();
      setAnalytics(updatedAnalytics);
    } catch (err: any) {
      alert(`Failed to log activity: ${err?.message}`);
    } finally {
      setIsLoggingAct(false);
    }
  };

  // Handle Add Resource Bookmark
  const handleAddResource = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingResource(true);
    try {
      await learningRoadmapsApi.createCustomResource({
        skill: resSkill,
        title: resTitle,
        provider: resProvider,
        url: resUrl,
        cost_tier: resCost,
        difficulty: resDifficulty,
        description: resDesc || undefined,
      });

      setShowAddResourceModal(false);
      setResSkill("");
      setResTitle("");
      setResProvider("");
      setResUrl("");
      setResDesc("");
      const updatedRes = await learningRoadmapsApi.listResources();
      setResources(updatedRes);
    } catch (err: any) {
      alert(`Failed to add resource: ${err?.message}`);
    } finally {
      setIsSavingResource(false);
    }
  };

  // Handle Track Recommended Project
  const handleTrackRecommendedProject = async (proj: any) => {
    try {
      await learningRoadmapsApi.createProject({
        title: proj.title,
        objective: proj.objective,
        summary: proj.summary,
        target_skills: proj.target_skills || [],
        functional_requirements: proj.functional_requirements || [],
        tech_stack: proj.tech_stack || [],
        suggested_milestones: proj.suggested_milestones || [],
        expected_portfolio_outcome: proj.expected_portfolio_outcome,
        resume_bullet_sample: proj.resume_bullet_sample,
      });

      const updated = await learningRoadmapsApi.listProjects();
      setProjects(updated);
      setActiveTab("projects");
    } catch (err: any) {
      alert(`Failed to track project: ${err?.message}`);
    }
  };

  // Handle Update Project
  const handleSaveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectToEdit) return;
    setIsSavingProject(true);
    try {
      await learningRoadmapsApi.updateProject(projectToEdit.id, {
        status: editProjectStatus,
        repository_url: editRepoUrl || undefined,
        live_demo_url: editDemoUrl || undefined,
        architecture_overview: editArchOverview || undefined,
        is_portfolio_ready:
          editProjectStatus === "completed" && Boolean(editRepoUrl && editArchOverview),
      });

      setShowProjectModal(false);
      setProjectToEdit(null);
      const updated = await learningRoadmapsApi.listProjects();
      setProjects(updated);
    } catch (err: any) {
      alert(`Failed to update project: ${err?.message}`);
    } finally {
      setIsSavingProject(false);
    }
  };

  const openEditProject = (proj: LearningProject) => {
    setProjectToEdit(proj);
    setEditProjectStatus(proj.status);
    setEditRepoUrl(proj.repository_url || "");
    setEditDemoUrl(proj.live_demo_url || "");
    setEditArchOverview(proj.architecture_overview || "");
    setShowProjectModal(true);
  };

  // Filter resources
  const filteredResources = resources.filter((res) => {
    if (
      resourceSkillFilter &&
      !res.skill.toLowerCase().includes(resourceSkillFilter.toLowerCase())
    ) {
      return false;
    }
    if (
      resourceDiffFilter &&
      res.difficulty.toLowerCase() !== resourceDiffFilter.toLowerCase()
    ) {
      return false;
    }
    if (
      resourceCostFilter &&
      res.cost_tier.toLowerCase() !== resourceCostFilter.toLowerCase()
    ) {
      return false;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-background text-foreground pb-20">
      {/* Top Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Compass className="w-5 h-5" />
                </span>
                <span className="text-xs uppercase tracking-wider font-semibold text-primary">
                  Skill Development & Learning Roadmap
                </span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground mt-1">
                Personalized Learning & Skill Gap Engine
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl">
                Personalized 4-stage roadmaps adapted to verified resume evidence, practical
                exercises, verified educational resources, and portfolio project tracking.
              </p>
            </div>

            <div className="flex items-center flex-wrap gap-2.5">
              <button
                onClick={() => setShowLogActivityModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
              >
                <Clock className="w-3.5 h-3.5 text-primary" />
                Log Study Activity
              </button>
              <button
                onClick={() => setShowAddResourceModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
              >
                <Bookmark className="w-3.5 h-3.5 text-primary" />
                Add Resource
              </button>
              <button
                onClick={() => setShowGenerateModal(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Generate Roadmap
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 mt-6 overflow-x-auto border-b border-border/50 pb-px">
            <button
              onClick={() => setActiveTab("gaps")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "gaps"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Target className="w-4 h-4" />
              Skill Gap Analysis
              {skillGaps && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-primary/10 text-primary font-mono">
                  {skillGaps.total_gaps} gaps
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("roadmaps")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "roadmaps"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Compass className="w-4 h-4" />
              Learning Roadmaps
              {roadmaps.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-primary/10 text-primary font-mono">
                  {roadmaps.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("resources")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "resources"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Resource Library
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-secondary text-muted-foreground font-mono">
                {resources.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("projects")}
              className={`px-3.5 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === "projects"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <FolderGit2 className="w-4 h-4" />
              Project Portfolio Tracker
              {projects.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-primary/10 text-primary font-mono">
                  {projects.length}
                </span>
              )}
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
              Activity & Velocity
              {analytics && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/10 text-emerald-600 font-mono">
                  {analytics.total_hours_learned}h
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        {error && (
          <div className="mb-6 p-4 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Unable to load roadmap information</p>
              <p className="text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center text-muted-foreground gap-3">
            <Compass className="w-10 h-10 animate-spin text-primary" />
            <p className="text-sm">Synthesizing personalized learning roadmaps...</p>
          </div>
        ) : (
          <>
            {/* TAB 1: SKILL GAPS */}
            {activeTab === "gaps" && (
              <div className="space-y-6">
                {/* Summary Banner */}
                {skillGaps && (
                  <div className="p-6 rounded-2xl border border-border bg-gradient-to-r from-card via-card to-primary/5 shadow-sm">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                          <Target className="w-3.5 h-3.5" />
                          Target Role: {skillGaps.target_role}
                        </div>
                        <h2 className="text-lg font-bold text-foreground mt-2">
                          Skill Readiness Summary
                        </h2>
                        <p className="text-xs text-muted-foreground mt-1 max-w-3xl leading-relaxed">
                          {skillGaps.recommendation_summary}
                        </p>
                      </div>

                      <div className="flex items-center gap-4 border-t md:border-t-0 md:border-l border-border pt-4 md:pt-0 md:pl-6">
                        <div className="text-center">
                          <span className="block text-2xl font-extrabold text-foreground font-mono">
                            {skillGaps.total_demonstrated}
                          </span>
                          <span className="text-[11px] text-muted-foreground uppercase font-medium">
                            Demonstrated
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="block text-2xl font-extrabold text-amber-500 font-mono">
                            {skillGaps.partially_demonstrated_skills.length}
                          </span>
                          <span className="text-[11px] text-muted-foreground uppercase font-medium">
                            Partial
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="block text-2xl font-extrabold text-destructive font-mono">
                            {skillGaps.total_gaps}
                          </span>
                          <span className="text-[11px] text-muted-foreground uppercase font-medium">
                            Missing Gaps
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Grid of 4 Gap Categories */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Category 1: Missing Skills (High Demand) */}
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-lg bg-destructive/10 text-destructive">
                          <AlertCircle className="w-4 h-4" />
                        </span>
                        <h3 className="text-sm font-bold text-foreground">
                          Frequently Requested Missing Skills
                        </h3>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {skillGaps?.missing_skills.length || 0} skills
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-4">
                      Required by your target role listings but not yet demonstrated in your resume.
                    </p>

                    <div className="space-y-2.5 flex-1">
                      {skillGaps?.missing_skills.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-6 text-center italic">
                          No missing skill gaps detected! Excellent alignment.
                        </p>
                      ) : (
                        skillGaps?.missing_skills.map((item, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-xl border border-border/70 bg-secondary/30 flex items-center justify-between gap-3"
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-foreground">
                                  {item.skill}
                                </span>
                                <span
                                  className={`px-2 py-0.2 rounded-full text-[10px] font-semibold uppercase ${
                                    item.priority_tier === "critical"
                                      ? "bg-destructive/10 text-destructive"
                                      : item.priority_tier === "high"
                                      ? "bg-amber-500/10 text-amber-600"
                                      : "bg-blue-500/10 text-blue-600"
                                  }`}
                                >
                                  {item.priority_tier}
                                </span>
                              </div>
                              <p className="text-[11px] text-muted-foreground mt-0.5">
                                Demand frequency: {item.market_demand_frequency} listings
                              </p>
                            </div>
                            <button
                              onClick={() => {
                                setGenSkillsInput(item.skill);
                                setShowGenerateModal(true);
                              }}
                              className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors flex items-center gap-1 flex-shrink-0"
                            >
                              Learn <ArrowRight className="w-3 h-3" />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Category 2: Interview Weaknesses */}
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-600">
                          <Flame className="w-4 h-4" />
                        </span>
                        <h3 className="text-sm font-bold text-foreground">
                          Repeated Interview Weaknesses
                        </h3>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {skillGaps?.interview_weaknesses.length || 0} topics
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-4">
                      Topics identified as missing or needing improvement in your interview prep evaluations.
                    </p>

                    <div className="space-y-2.5 flex-1">
                      {skillGaps?.interview_weaknesses.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-6 text-center italic">
                          No interview weaknesses recorded. Practice mock interviews to reveal gaps!
                        </p>
                      ) : (
                        skillGaps?.interview_weaknesses.map((item, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5 flex items-center justify-between gap-3"
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-foreground">
                                  {item.skill}
                                </span>
                                <span className="px-2 py-0.2 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-600">
                                  Score: {item.priority_score}
                                </span>
                              </div>
                              <p className="text-[11px] text-muted-foreground mt-0.5">
                                {item.evidence_notes || "Repeated in recent interview answers."}
                              </p>
                            </div>
                            <Link
                              href="/dashboard/interview-prep"
                              className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-secondary hover:bg-secondary/80 text-foreground transition-colors flex items-center gap-1 flex-shrink-0"
                            >
                              Practice <ArrowRight className="w-3 h-3" />
                            </Link>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Category 3: Partially Demonstrated */}
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-lg bg-blue-500/10 text-blue-600">
                          <Code2 className="w-4 h-4" />
                        </span>
                        <h3 className="text-sm font-bold text-foreground">
                          Partially Demonstrated Skills
                        </h3>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {skillGaps?.partially_demonstrated_skills.length || 0} skills
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-4">
                      Found in your profile or job preferences, but lacking deep architectural or project evidence.
                    </p>

                    <div className="space-y-2.5 flex-1">
                      {skillGaps?.partially_demonstrated_skills.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-6 text-center italic">
                          No partial skills flagged.
                        </p>
                      ) : (
                        skillGaps?.partially_demonstrated_skills.map((item, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-xl border border-border/70 bg-secondary/30 flex items-center justify-between gap-3"
                          >
                            <div>
                              <span className="text-xs font-semibold text-foreground">
                                {item.skill}
                              </span>
                              <p className="text-[11px] text-muted-foreground mt-0.5">
                                {item.evidence_notes || "Add portfolio projects to verify proficiency."}
                              </p>
                            </div>
                            <button
                              onClick={() => {
                                setGenSkillsInput(item.skill);
                                setShowGenerateModal(true);
                              }}
                              className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors flex items-center gap-1 flex-shrink-0"
                            >
                              Deep Dive
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Category 4: Verified Demonstrated Skills */}
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600">
                          <CheckCircle2 className="w-4 h-4" />
                        </span>
                        <h3 className="text-sm font-bold text-foreground">
                          Verified Demonstrated Skills
                        </h3>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {skillGaps?.demonstrated_skills.length || 0} skills
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-4">
                      Backed by parsed resume evidence, work history, or past technical project deliverables.
                    </p>

                    <div className="flex flex-wrap gap-2 flex-1">
                      {skillGaps?.demonstrated_skills.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-6 text-center italic w-full">
                          Upload your resume in Resume Studio to extract verified skills.
                        </p>
                      ) : (
                        skillGaps?.demonstrated_skills.map((item, idx) => (
                          <span
                            key={idx}
                            title={item.evidence_notes || "Verified on resume"}
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
                          >
                            <Check className="w-3 h-3 text-emerald-500" />
                            {item.skill}
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: ROADMAPS */}
            {activeTab === "roadmaps" && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Sidebar: Roadmap List */}
                <div className="lg:col-span-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-foreground">Your Roadmaps</h2>
                    <button
                      onClick={() => setShowGenerateModal(true)}
                      className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> New Track
                    </button>
                  </div>

                  {roadmaps.length === 0 ? (
                    <div className="p-6 rounded-2xl border border-dashed border-border text-center">
                      <Compass className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                      <p className="text-xs text-muted-foreground">No roadmaps created yet.</p>
                      <button
                        onClick={() => setShowGenerateModal(true)}
                        className="mt-3 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground"
                      >
                        Generate First Roadmap
                      </button>
                    </div>
                  ) : (
                    roadmaps.map((rm) => (
                      <div
                        key={rm.id}
                        onClick={() => setSelectedRoadmapId(rm.id)}
                        className={`p-4 rounded-xl border cursor-pointer transition-all ${
                          selectedRoadmapId === rm.id
                            ? "border-primary bg-primary/5 shadow-sm"
                            : "border-border bg-card hover:border-primary/40"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              rm.status === "active"
                                ? "bg-emerald-500/10 text-emerald-600"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            {rm.status}
                          </span>
                          <span className="text-[11px] text-muted-foreground font-mono">
                            {rm.difficulty_level}
                          </span>
                        </div>
                        <h3 className="text-xs font-bold text-foreground mt-2 line-clamp-1">
                          {rm.title}
                        </h3>
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          Target: {rm.target_role}
                        </p>

                        {/* Progress Bar */}
                        <div className="mt-3">
                          <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                            <span>
                              {rm.completed_milestones_count} / {rm.milestones_count} stages
                            </span>
                            <span className="font-mono font-semibold">
                              {rm.completion_percentage}%
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all duration-300"
                              style={{ width: `${rm.completion_percentage}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Right Area: Selected Roadmap Detail */}
                <div className="lg:col-span-8">
                  {selectedRoadmap ? (
                    <div className="space-y-6">
                      {/* Roadmap Header Card */}
                      <div className="p-6 rounded-2xl border border-border bg-card shadow-sm">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase bg-primary/10 text-primary">
                                {selectedRoadmap.status}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Tier: {selectedRoadmap.difficulty_level}
                              </span>
                            </div>
                            <h2 className="text-lg font-bold text-foreground mt-1">
                              {selectedRoadmap.title}
                            </h2>
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                              {selectedRoadmap.description}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            <button
                              onClick={() =>
                                handleToggleRoadmapStatus(
                                  selectedRoadmap.id,
                                  selectedRoadmap.status
                                )
                              }
                              className="p-2 rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                              title={
                                selectedRoadmap.status === "active" ? "Pause Track" : "Resume Track"
                              }
                            >
                              {selectedRoadmap.status === "active" ? (
                                <Pause className="w-4 h-4" />
                              ) : (
                                <Play className="w-4 h-4 text-emerald-500" />
                              )}
                            </button>
                            <button
                              onClick={() => handleDeleteRoadmap(selectedRoadmap.id)}
                              className="p-2 rounded-lg border border-destructive/20 bg-destructive/10 hover:bg-destructive/20 text-destructive transition-colors"
                              title="Delete Roadmap"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* Progress Stats */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-border">
                          <div>
                            <span className="text-[11px] text-muted-foreground block">
                              Total Hours
                            </span>
                            <span className="text-sm font-bold text-foreground font-mono">
                              {selectedRoadmap.total_estimated_hours} hrs
                            </span>
                          </div>
                          <div>
                            <span className="text-[11px] text-muted-foreground block">
                              Completed Hours
                            </span>
                            <span className="text-sm font-bold text-foreground font-mono">
                              {selectedRoadmap.completed_hours} hrs
                            </span>
                          </div>
                          <div>
                            <span className="text-[11px] text-muted-foreground block">
                              Overall Progress
                            </span>
                            <span className="text-sm font-bold text-primary font-mono">
                              {selectedRoadmap.completion_percentage}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[11px] text-muted-foreground block">
                              Mastered Skills
                            </span>
                            <span className="text-sm font-bold text-emerald-600 font-mono">
                              {selectedRoadmap.already_mastered_skills.length} verified
                            </span>
                          </div>
                        </div>

                        {/* Prerequisites banner */}
                        {selectedRoadmap.prerequisites.length > 0 && (
                          <div className="mt-4 p-3 rounded-xl bg-secondary/40 border border-border/60">
                            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-2">
                              Prerequisite Topics
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {selectedRoadmap.prerequisites.map((p, idx) => (
                                <span
                                  key={idx}
                                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium ${
                                    p.is_satisfied
                                      ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                                      : "bg-secondary text-muted-foreground border border-border"
                                  }`}
                                  title={p.evidence || "Prerequisite topic"}
                                >
                                  {p.is_satisfied ? (
                                    <Check className="w-3 h-3" />
                                  ) : (
                                    <Clock className="w-3 h-3" />
                                  )}
                                  {p.topic}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 4 Stages Milestones Checklist */}
                      <div className="space-y-4">
                        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                          4-Stage Learning Path
                        </h3>

                        {selectedRoadmap.milestones.map((m) => {
                          const isExpanded = expandedMilestones[m.id] ?? true;
                          const isDone = m.status === "completed" || m.status === "skipped";
                          return (
                            <div
                              key={m.id}
                              className={`p-5 rounded-2xl border transition-all ${
                                isDone
                                  ? "border-emerald-500/30 bg-card"
                                  : m.status === "in_progress"
                                  ? "border-primary bg-card shadow-sm"
                                  : "border-border bg-card/60"
                              }`}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex items-start gap-3">
                                  <button
                                    onClick={() => handleToggleMilestoneStatus(m)}
                                    className={`mt-0.5 w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${
                                      isDone
                                        ? "bg-emerald-500 border-emerald-500 text-white"
                                        : "border-border hover:border-primary"
                                    }`}
                                  >
                                    {isDone && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                                  </button>

                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-primary">
                                        Stage {m.order_index} • {m.stage}
                                      </span>
                                      {m.completion_notes && (
                                        <span className="px-2 py-0.2 rounded text-[10px] bg-emerald-500/10 text-emerald-600 font-medium">
                                          {m.completion_notes}
                                        </span>
                                      )}
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground mt-0.5">
                                      {m.title}
                                    </h4>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {m.description}
                                    </p>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono text-muted-foreground">
                                    {m.estimated_hours}h
                                  </span>
                                  <button
                                    onClick={() =>
                                      setExpandedMilestones((prev) => ({
                                        ...prev,
                                        [m.id]: !isExpanded,
                                      }))
                                    }
                                    className="p-1 rounded-md text-muted-foreground hover:text-foreground"
                                  >
                                    {isExpanded ? (
                                      <ChevronUp className="w-4 h-4" />
                                    ) : (
                                      <ChevronDown className="w-4 h-4" />
                                    )}
                                  </button>
                                </div>
                              </div>

                              {isExpanded && (
                                <div className="mt-4 pt-4 border-t border-border space-y-4">
                                  {/* Learning Objectives */}
                                  {m.learning_objectives.length > 0 && (
                                    <div>
                                      <span className="text-[11px] font-semibold uppercase text-muted-foreground block mb-1.5">
                                        Core Objectives
                                      </span>
                                      <ul className="space-y-1">
                                        {m.learning_objectives.map((obj, i) => (
                                          <li
                                            key={i}
                                            className="text-xs text-muted-foreground flex items-center gap-2"
                                          >
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary/70 flex-shrink-0" />
                                            {obj}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  {/* Practical Exercises Checklist */}
                                  <div>
                                    <span className="text-[11px] font-semibold uppercase text-muted-foreground block mb-2">
                                      Hands-On Exercises ({m.practical_exercises.filter((x) => x.completed).length} /{" "}
                                      {m.practical_exercises.length} complete)
                                    </span>
                                    <div className="space-y-2">
                                      {m.practical_exercises.map((ex, exIdx) => (
                                        <div
                                          key={exIdx}
                                          className={`p-3 rounded-xl border transition-colors flex items-start gap-3 ${
                                            ex.completed
                                              ? "border-emerald-500/20 bg-emerald-500/5 text-muted-foreground"
                                              : "border-border/70 bg-secondary/20"
                                          }`}
                                        >
                                          <input
                                            type="checkbox"
                                            checked={ex.completed}
                                            onChange={() => handleToggleExercise(m, exIdx)}
                                            className="mt-0.5 rounded border-border text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                                          />
                                          <div className="flex-1">
                                            <div className="flex items-center justify-between">
                                              <span
                                                className={`text-xs font-semibold ${
                                                  ex.completed ? "line-through" : "text-foreground"
                                                }`}
                                              >
                                                {ex.title}
                                              </span>
                                              <span className="text-[10px] font-mono text-muted-foreground">
                                                ~{ex.estimated_minutes} min
                                              </span>
                                            </div>
                                            <p className="text-[11px] text-muted-foreground mt-0.5">
                                              {ex.instructions}
                                            </p>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="p-12 rounded-2xl border border-dashed border-border text-center">
                      <Compass className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-40" />
                      <h3 className="text-sm font-semibold text-foreground">
                        Select a Roadmap Track
                      </h3>
                      <p className="text-xs text-muted-foreground mt-1">
                        Select a roadmap from the left panel or generate a new tailored track.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: RESOURCES */}
            {activeTab === "resources" && (
              <div className="space-y-6">
                {/* Filters Bar */}
                <div className="p-4 rounded-xl border border-border bg-card flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Filter className="w-3.5 h-3.5" />
                    <span>Filter By:</span>
                  </div>

                  <input
                    type="text"
                    placeholder="Search skill (e.g. Python, Docker)..."
                    value={resourceSkillFilter}
                    onChange={(e) => setResourceSkillFilter(e.target.value)}
                    className="px-3 py-1.5 text-xs rounded-lg border border-border bg-secondary/50 focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                  />

                  <select
                    value={resourceDiffFilter}
                    onChange={(e) => setResourceDiffFilter(e.target.value)}
                    className="px-3 py-1.5 text-xs rounded-lg border border-border bg-secondary/50 focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                  >
                    <option value="">All Difficulties</option>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>

                  <select
                    value={resourceCostFilter}
                    onChange={(e) => setResourceCostFilter(e.target.value)}
                    className="px-3 py-1.5 text-xs rounded-lg border border-border bg-secondary/50 focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                  >
                    <option value="">All Pricing</option>
                    <option value="free">Free Only</option>
                    <option value="freemium">Freemium</option>
                    <option value="paid">Paid</option>
                  </select>

                  {(resourceSkillFilter || resourceDiffFilter || resourceCostFilter) && (
                    <button
                      onClick={() => {
                        setResourceSkillFilter("");
                        setResourceDiffFilter("");
                        setResourceCostFilter("");
                      }}
                      className="text-xs text-primary hover:underline ml-auto"
                    >
                      Reset Filters
                    </button>
                  )}
                </div>

                {/* Resource Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredResources.map((res) => (
                    <div
                      key={res.id}
                      className="p-5 rounded-2xl border border-border bg-card shadow-sm hover:border-primary/50 transition-all flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary">
                            {res.skill}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase ${
                              res.cost_tier === "free"
                                ? "bg-emerald-500/10 text-emerald-600"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            {res.cost_tier}
                          </span>
                        </div>

                        <h3 className="text-sm font-bold text-foreground line-clamp-2">
                          {res.title}
                        </h3>
                        <p className="text-[11px] font-medium text-primary mt-1">
                          {res.provider}
                        </p>
                        <p className="text-xs text-muted-foreground mt-2 line-clamp-3 leading-relaxed">
                          {res.description}
                        </p>
                      </div>

                      <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                          <span className="capitalize">{res.difficulty}</span>
                          {res.estimated_hours && <span>• {res.estimated_hours}h</span>}
                        </div>

                        <a
                          href={res.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                        >
                          Visit Course <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 4: PROJECTS */}
            {activeTab === "projects" && (
              <div className="space-y-8">
                {/* Resume Integration Boundary Note */}
                <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-foreground flex items-start gap-3">
                  <Award className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block">Portfolio Evidence & Resume Policy:</span>
                    <p className="text-muted-foreground mt-0.5">
                      Completing learning exercises does not automatically alter your resume. Only
                      completed projects with verified repository links and architectural notes can
                      be integrated into your professional resume evidence.
                    </p>
                  </div>
                </div>

                {/* Tracked Projects */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-base font-bold text-foreground">
                      Tracked Portfolio Projects
                    </h2>
                  </div>

                  {projects.length === 0 ? (
                    <div className="p-8 rounded-2xl border border-dashed border-border text-center">
                      <FolderGit2 className="w-10 h-10 text-muted-foreground mx-auto mb-2 opacity-50" />
                      <p className="text-xs text-muted-foreground">
                        You have not tracked any portfolio projects yet.
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-1">
                        Select a recommended project below to track your repository and architecture.
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {projects.map((p) => (
                        <div
                          key={p.id}
                          className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col justify-between"
                        >
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <span
                                className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                                  p.status === "completed"
                                    ? "bg-emerald-500/10 text-emerald-600"
                                    : "bg-blue-500/10 text-blue-600"
                                }`}
                              >
                                {p.status}
                              </span>
                              {p.is_portfolio_ready && (
                                <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-600 font-semibold flex items-center gap-1">
                                  <Award className="w-3 h-3" /> Portfolio Ready
                                </span>
                              )}
                            </div>

                            <h3 className="text-sm font-bold text-foreground">{p.title}</h3>
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                              {p.objective}
                            </p>

                            {/* Tech stack */}
                            <div className="flex flex-wrap gap-1.5 mt-3">
                              {p.tech_stack.map((t, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.2 rounded text-[10px] bg-secondary text-secondary-foreground font-mono"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>

                            {/* Links if available */}
                            {(p.repository_url || p.live_demo_url) && (
                              <div className="flex items-center gap-3 mt-4 text-xs">
                                {p.repository_url && (
                                  <a
                                    href={p.repository_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline flex items-center gap-1"
                                  >
                                    <FolderGit2 className="w-3.5 h-3.5" /> Repo
                                  </a>
                                )}
                                {p.live_demo_url && (
                                  <a
                                    href={p.live_demo_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline flex items-center gap-1"
                                  >
                                    <ExternalLink className="w-3.5 h-3.5" /> Live Demo
                                  </a>
                                )}
                              </div>
                            )}
                          </div>

                          <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                            <span className="text-[11px] text-muted-foreground">
                              {p.functional_requirements.length} functional specs
                            </span>
                            <button
                              onClick={() => openEditProject(p)}
                              className="px-3 py-1 text-xs font-semibold rounded-lg bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                            >
                              Update Evidence
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Recommended Practical Projects */}
                <div>
                  <h2 className="text-base font-bold text-foreground mb-4">
                    Recommended Projects for Your Skill Gaps
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {recommendedProjects.map((rec, idx) => (
                      <div
                        key={idx}
                        className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary">
                              {rec.target_skills?.join(", ") || "Technical"}
                            </span>
                          </div>

                          <h3 className="text-sm font-bold text-foreground">{rec.title}</h3>
                          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                            {rec.objective}
                          </p>

                          <div className="mt-3">
                            <span className="text-[11px] font-semibold text-muted-foreground block mb-1">
                              Functional Requirements:
                            </span>
                            <ul className="space-y-1">
                              {rec.functional_requirements?.slice(0, 3).map((req: string, i: number) => (
                                <li
                                  key={i}
                                  className="text-[11px] text-muted-foreground flex items-center gap-1.5"
                                >
                                  <span className="w-1 h-1 rounded-full bg-primary" />
                                  {req}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                          <div className="flex flex-wrap gap-1">
                            {rec.tech_stack?.slice(0, 3).map((t: string, i: number) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.2 rounded text-[10px] bg-secondary text-muted-foreground font-mono"
                              >
                                {t}
                              </span>
                            ))}
                          </div>

                          <button
                            onClick={() => handleTrackRecommendedProject(rec)}
                            className="px-3 py-1 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all flex items-center gap-1"
                          >
                            <Plus className="w-3.5 h-3.5" /> Track Project
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 5: ANALYTICS & VELOCITY */}
            {activeTab === "analytics" && (
              <div className="space-y-6">
                {/* 4 KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Total Study Time</span>
                    <span className="block text-2xl font-black text-foreground font-mono mt-1">
                      {analytics?.total_hours_learned || 0} hrs
                    </span>
                    <span className="text-[10px] text-emerald-600 mt-1 block">
                      Across all logged activities
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Weekly Velocity</span>
                    <span className="block text-2xl font-black text-primary font-mono mt-1">
                      {analytics?.weekly_hours_learned || 0} hrs
                    </span>
                    <span className="text-[10px] text-muted-foreground mt-1 block">
                      Past 7 rolling days
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Completed Milestones</span>
                    <span className="block text-2xl font-black text-foreground font-mono mt-1">
                      {analytics?.completed_milestones_count || 0}
                    </span>
                    <span className="text-[10px] text-muted-foreground mt-1 block">
                      Stages finished
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl border border-border bg-card">
                    <span className="text-xs text-muted-foreground">Portfolio Projects</span>
                    <span className="block text-2xl font-black text-emerald-600 font-mono mt-1">
                      {analytics?.portfolio_projects_count || 0}
                    </span>
                    <span className="text-[10px] text-muted-foreground mt-1 block">
                      Ready for resume review
                    </span>
                  </div>
                </div>

                {/* Hours by Skill Breakdown */}
                {analytics && Object.keys(analytics.hours_by_skill).length > 0 && (
                  <div className="p-5 rounded-2xl border border-border bg-card shadow-sm">
                    <h3 className="text-sm font-bold text-foreground mb-4">
                      Study Time Breakdown by Skill
                    </h3>
                    <div className="space-y-3">
                      {Object.entries(analytics.hours_by_skill).map(([skill, hrs]) => {
                        const pct = Math.min(
                          100,
                          Math.round((hrs / (analytics.total_hours_learned || 1)) * 100)
                        );
                        return (
                          <div key={skill}>
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="font-medium text-foreground">{skill}</span>
                              <span className="font-mono text-muted-foreground">
                                {hrs} hrs ({pct}%)
                              </span>
                            </div>
                            <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full transition-all duration-300"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Recent Activities Feed */}
                <div className="p-5 rounded-2xl border border-border bg-card shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-foreground">
                      Recent Activity Log
                    </h3>
                    <button
                      onClick={() => setShowLogActivityModal(true)}
                      className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Log Session
                    </button>
                  </div>

                  {analytics?.recent_activities.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-6 text-center italic">
                      No activities logged yet. Track your reading, coding, or practice sessions!
                    </p>
                  ) : (
                    <div className="space-y-2.5">
                      {analytics?.recent_activities.map((act) => (
                        <div
                          key={act.id}
                          className="p-3 rounded-xl border border-border/70 bg-secondary/30 flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <span className="p-2 rounded-lg bg-primary/10 text-primary">
                              <Clock className="w-4 h-4" />
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold capitalize text-foreground">
                                  {act.activity_type.replace("_", " ")}
                                </span>
                                {act.skill && (
                                  <span className="px-2 py-0.2 rounded text-[10px] bg-secondary text-foreground font-mono">
                                    {act.skill}
                                  </span>
                                )}
                              </div>
                              {act.notes && (
                                <p className="text-[11px] text-muted-foreground mt-0.5">
                                  {act.notes}
                                </p>
                              )}
                            </div>
                          </div>

                          <div className="text-right">
                            <span className="text-xs font-bold text-foreground font-mono">
                              +{act.duration_hours}h
                            </span>
                            <span className="text-[10px] text-muted-foreground block">
                              {new Date(act.logged_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* MODAL 1: GENERATE ROADMAP */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">
                Generate Personalized Learning Roadmap
              </h3>
              <button
                onClick={() => setShowGenerateModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerateRoadmap} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Target Track / Role
                </label>
                <select
                  value={genTargetRole}
                  onChange={(e) => setGenTargetRole(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {PRESET_TRACKS.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.label}
                    </option>
                  ))}
                  <option value="custom">Custom Role...</option>
                </select>
              </div>

              {genTargetRole === "custom" && (
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">
                    Custom Target Role Title
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Distributed Systems Engineer"
                    value={genCustomRole}
                    onChange={(e) => setGenCustomRole(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              )}

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Difficulty Level
                </label>
                <select
                  value={genDifficulty}
                  onChange={(e) => setGenDifficulty(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="beginner">Beginner (Fundamentals & Syntax)</option>
                  <option value="intermediate">Intermediate (Production Patterns)</option>
                  <option value="advanced">Advanced (Scale & System Architecture)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Specific Skills to Target (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Redis, Docker, FastAPI"
                  value={genSkillsInput}
                  onChange={(e) => setGenSkillsInput(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  User Notes or Custom Goals (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Preparing for fintech backend interviews in 30 days"
                  value={genNotes}
                  onChange={(e) => setGenNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary text-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {isGenerating ? "Generating..." : "Create Roadmap"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: LOG ACTIVITY */}
      {showLogActivityModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">Log Study Activity</h3>
              <button
                onClick={() => setShowLogActivityModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLogActivity} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Activity Type
                </label>
                <select
                  value={actType}
                  onChange={(e) => setActType(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="reading">Reading / Theory</option>
                  <option value="coding">Coding / Building</option>
                  <option value="exercise">Milestone Exercise</option>
                  <option value="project_work">Portfolio Project Work</option>
                  <option value="review">System Architecture Review</option>
                  <option value="practice">LeetCode / Algorithmic Practice</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Duration (hours)
                </label>
                <input
                  type="number"
                  step="0.25"
                  min="0.25"
                  max="24"
                  value={actDuration}
                  onChange={(e) => setActDuration(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Skill Focus (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Python, Docker, PostgreSQL"
                  value={actSkill}
                  onChange={(e) => setActSkill(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Session Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Completed JWT token refresh middleware and added pytest tests."
                  value={actNotes}
                  onChange={(e) => setActNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowLogActivityModal(false)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary text-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoggingAct}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {isLoggingAct ? "Saving..." : "Log Activity"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: ADD RESOURCE BOOKMARK */}
      {showAddResourceModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">Add Custom Learning Resource</h3>
              <button
                onClick={() => setShowAddResourceModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddResource} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Skill Tag
                </label>
                <input
                  type="text"
                  placeholder="e.g. React, Redis, Go"
                  value={resSkill}
                  onChange={(e) => setResSkill(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Resource Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Distributed Systems Engineering Primer"
                  value={resTitle}
                  onChange={(e) => setResTitle(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Provider / Author
                </label>
                <input
                  type="text"
                  placeholder="e.g. MIT OpenCourseWare, Martin Fowler"
                  value={resProvider}
                  onChange={(e) => setResProvider(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Resource URL
                </label>
                <input
                  type="url"
                  placeholder="https://..."
                  value={resUrl}
                  onChange={(e) => setResUrl(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">
                    Cost Tier
                  </label>
                  <select
                    value={resCost}
                    onChange={(e) => setResCost(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="free">Free</option>
                    <option value="freemium">Freemium</option>
                    <option value="paid">Paid</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">
                    Difficulty
                  </label>
                  <select
                    value={resDifficulty}
                    onChange={(e) => setResDifficulty(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Description (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Notes on why this resource is useful..."
                  value={resDesc}
                  onChange={(e) => setResDesc(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddResourceModal(false)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary text-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingResource}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {isSavingResource ? "Saving..." : "Save Bookmark"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: EDIT PROJECT EVIDENCE */}
      {showProjectModal && projectToEdit && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">
                Update Project Portfolio Evidence
              </h3>
              <button
                onClick={() => setShowProjectModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveProject} className="space-y-4">
              <div>
                <span className="text-xs font-semibold text-muted-foreground block mb-1">
                  Project Title
                </span>
                <p className="text-sm font-bold text-foreground">{projectToEdit.title}</p>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Project Status
                </label>
                <select
                  value={editProjectStatus}
                  onChange={(e) => setEditProjectStatus(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="planning">Planning</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="abandoned">Abandoned</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  GitHub / GitLab Repository URL
                </label>
                <input
                  type="url"
                  placeholder="https://github.com/username/project"
                  value={editRepoUrl}
                  onChange={(e) => setEditRepoUrl(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Live Demo / Deployment URL (Optional)
                </label>
                <input
                  type="url"
                  placeholder="https://project.example.com"
                  value={editDemoUrl}
                  onChange={(e) => setEditDemoUrl(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Architecture Overview & Evidence Notes
                </label>
                <textarea
                  rows={4}
                  placeholder="Describe your database schema, async workers, API endpoints, rate limiting, and test coverage for your resume bullet points..."
                  value={editArchOverview}
                  onChange={(e) => setEditArchOverview(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-secondary/50 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowProjectModal(false)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary text-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingProject}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {isSavingProject ? "Saving..." : "Save Evidence"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
