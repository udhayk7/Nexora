"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Calendar,
  CheckCircle2,
  Clock,
  Cpu,
  Download,
  ExternalLink,
  FileDown,
  Github,
  Globe,
  GraduationCap,
  Layers,
  Linkedin,
  Mail,
  MapPin,
  Share2,
  Sparkles,
  Terminal,
  Trophy,
} from "lucide-react";
import {
  portfoliosApi,
  PublicPortfolioDetail,
  PortfolioProjectItem,
  PortfolioWorkExperienceItem,
  PortfolioEducationItem,
  PortfolioCertificationItem,
  PortfolioAchievementItem,
} from "@/lib/api";

export default function PublicPortfolioPage() {
  const params = useParams();
  const slug = (params?.public_slug as string) || "";

  const [portfolio, setPortfolio] = useState<PublicPortfolioDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!slug) return;
    let isMounted = true;
    setLoading(true);

    portfoliosApi
      .getPublicPortfolio(slug)
      .then((data) => {
        if (isMounted) {
          setPortfolio(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(
            err?.message || "This portfolio is currently private or does not exist."
          );
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [slug]);

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleProjectInteraction = (projectId: string) => {
    if (!slug) return;
    portfoliosApi
      .recordPublicEvent(slug, {
        event_type: "project_view",
        project_id: projectId,
      })
      .catch(() => {});
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground p-6">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground font-medium">Loading portfolio...</p>
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground p-6 text-center">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4 text-muted-foreground">
          <Globe className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold mb-2">Portfolio Unavailable</h1>
        <p className="text-muted-foreground max-w-md mb-6 text-sm">
          {error || "This portfolio is not publicly accessible at this time."}
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Return to Nexora
        </Link>
      </div>
    );
  }

  const { template_id, theme_config, profile_data, sections, projects } = portfolio;
  const accentColor = theme_config?.accent_color || "#2563eb";
  const fontFamily = theme_config?.font_family || "Inter";
  const isDarkMode = theme_config?.dark_mode === "dark";

  // Filter sections by is_visible and sort by order_index
  const sortedSections = [...(sections || [])]
    .filter((s) => s.is_visible)
    .sort((a, b) => a.order_index - b.order_index);

  const visibleProjects = (projects || []).filter((p) => p.is_visible);

  return (
    <div
      className={`min-h-screen transition-colors duration-200 ${
        isDarkMode ? "bg-slate-950 text-slate-100" : "bg-slate-50 text-slate-900"
      }`}
      style={{ fontFamily }}
    >
      {/* Top Floating Action Bar */}
      <header
        className={`sticky top-0 z-40 backdrop-blur-md border-b transition-colors ${
          isDarkMode
            ? "bg-slate-950/80 border-slate-800"
            : "bg-white/80 border-slate-200"
        }`}
      >
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: accentColor }}
            />
            <span className="font-semibold text-sm tracking-tight">
              {profile_data?.full_name || portfolio.title || "Portfolio"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleShare}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                isDarkMode
                  ? "border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-200"
                  : "border-slate-200 bg-white hover:bg-slate-100 text-slate-700"
              }`}
            >
              <Share2 className="w-3.5 h-3.5" />
              {copied ? "Link Copied!" : "Share"}
            </button>

            <a
              href={portfoliosApi.getPublicPdfUrl(slug)}
              download
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-white transition-opacity hover:opacity-90 shadow-sm"
              style={{ backgroundColor: accentColor }}
            >
              <Download className="w-3.5 h-3.5" />
              Download PDF
            </a>

            <a
              href={portfoliosApi.getPublicHtmlUrl(slug)}
              download
              className={`hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                isDarkMode
                  ? "border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300"
                  : "border-slate-200 bg-white hover:bg-slate-100 text-slate-700"
              }`}
            >
              <FileDown className="w-3.5 h-3.5" />
              Offline HTML
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="max-w-5xl mx-auto px-6 py-12 space-y-16">
        {sortedSections.map((section) => {
          switch (section.section_type) {
            case "hero":
              return (
                <HeroSection
                  key={section.id}
                  profile={profile_data}
                  headline={portfolio.headline || undefined}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            case "about":
              return (
                <AboutSection
                  key={section.id}
                  title={section.title || "About Me"}
                  summary={profile_data?.summary}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            case "skills":
              return (
                <SkillsSection
                  key={section.id}
                  title={section.title || "Technical Capabilities"}
                  skills={profile_data?.technical_skills || []}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            case "projects":
              return (
                <ProjectsSection
                  key={section.id}
                  title={section.title || "Featured Projects"}
                  projects={visibleProjects}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                  onInteract={handleProjectInteraction}
                />
              );
            case "experience":
              return (
                <ExperienceSection
                  key={section.id}
                  title={section.title || "Experience"}
                  experience={profile_data?.work_experience || []}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            case "education":
              return (
                <EducationSection
                  key={section.id}
                  title={section.title || "Education"}
                  education={profile_data?.education || []}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            case "certifications":
              return (
                <CertificationsSection
                  key={section.id}
                  title={section.title || "Certifications & Achievements"}
                  certifications={profile_data?.certifications || []}
                  achievements={profile_data?.achievements || []}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            case "contact":
              return (
                <ContactSection
                  key={section.id}
                  title={section.title || "Contact & Links"}
                  profile={profile_data}
                  templateId={template_id}
                  accentColor={accentColor}
                  isDarkMode={isDarkMode}
                />
              );
            default:
              return null;
          }
        })}
      </main>

      {/* Footer */}
      <footer
        className={`mt-24 border-t py-8 text-center text-xs transition-colors ${
          isDarkMode
            ? "border-slate-800 bg-slate-950/40 text-slate-500"
            : "border-slate-200 bg-white/40 text-slate-400"
        }`}
      >
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© {new Date().getFullYear()} {profile_data?.full_name || "Professional Portfolio"}. All rights reserved.</p>
          <div className="flex items-center gap-1.5">
            <span>Verified with</span>
            <Link
              href="/"
              className="font-medium hover:underline flex items-center gap-1"
              style={{ color: accentColor }}
            >
              <Sparkles className="w-3.5 h-3.5" /> Nexora Career Navigator
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Sub-components for Sections
// -----------------------------------------------------------------------------

function HeroSection({
  profile,
  headline,
  templateId,
  accentColor,
  isDarkMode,
}: {
  profile?: PublicPortfolioDetail["profile_data"];
  headline?: string;
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  const isDev = templateId === "developer";
  const isAi = templateId === "ai_tech";

  return (
    <section className="pt-4 pb-2">
      {isDev && (
        <div
          className={`inline-flex items-center gap-2 px-3 py-1 rounded-md text-xs font-mono mb-4 border ${
            isDarkMode
              ? "bg-slate-900 border-slate-800 text-emerald-400"
              : "bg-slate-100 border-slate-200 text-emerald-600"
          }`}
        >
          <Terminal className="w-3.5 h-3.5" /> ~/portfolio/root.sh
        </div>
      )}

      {isAi && (
        <div
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium mb-4"
          style={{
            backgroundColor: `${accentColor}15`,
            color: accentColor,
            border: `1px solid ${accentColor}30`,
          }}
        >
          <Cpu className="w-3.5 h-3.5" /> AI Systems & Engineering Showcase
        </div>
      )}

      <div className="flex flex-col-reverse sm:flex-row items-start justify-between gap-6">
        <div className="space-y-3 flex-1">
          <h1
            className={`text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight ${
              isDev ? "font-mono" : ""
            }`}
          >
            {profile?.full_name || "Professional Engineer"}
          </h1>

          <p
            className={`text-lg sm:text-xl font-medium ${
              isDarkMode ? "text-slate-300" : "text-slate-600"
            }`}
          >
            {headline || profile?.headline || "Software Engineer & Technologist"}
          </p>

          <div className="flex flex-wrap items-center gap-4 text-xs pt-1">
            {profile?.location && (
              <span
                className={`inline-flex items-center gap-1.5 ${
                  isDarkMode ? "text-slate-400" : "text-slate-500"
                }`}
              >
                <MapPin className="w-3.5 h-3.5" />
                {profile.location}
              </span>
            )}

            {profile?.contact_email && (
              <a
                href={`mailto:${profile.contact_email}`}
                className="inline-flex items-center gap-1.5 hover:underline"
                style={{ color: accentColor }}
              >
                <Mail className="w-3.5 h-3.5" />
                {profile.contact_email}
              </a>
            )}

            {profile?.github_url && (
              <a
                href={profile.github_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 hover:underline font-mono"
                style={{ color: accentColor }}
              >
                <Github className="w-3.5 h-3.5" />
                GitHub
              </a>
            )}

            {profile?.linkedin_url && (
              <a
                href={profile.linkedin_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 hover:underline"
                style={{ color: accentColor }}
              >
                <Linkedin className="w-3.5 h-3.5" />
                LinkedIn
              </a>
            )}

            {profile?.website_url && (
              <a
                href={profile.website_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 hover:underline"
                style={{ color: accentColor }}
              >
                <Globe className="w-3.5 h-3.5" />
                Website
              </a>
            )}
          </div>

          {profile?.target_roles && profile.target_roles.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-2">
              <span
                className={`text-xs font-semibold mr-1 uppercase tracking-wider ${
                  isDarkMode ? "text-slate-400" : "text-slate-500"
                }`}
              >
                Target Roles:
              </span>
              {profile.target_roles.map((r, i) => (
                <span
                  key={i}
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    isDarkMode
                      ? "bg-slate-800 text-slate-300"
                      : "bg-slate-200/80 text-slate-800"
                  }`}
                >
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>

        {profile?.avatar_url && (
          <div
            className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden border-2 shadow-sm flex-shrink-0"
            style={{ borderColor: accentColor }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={profile.avatar_url}
              alt={profile.full_name || "Profile Photo"}
              className="w-full h-full object-cover"
            />
          </div>
        )}
      </div>
    </section>
  );
}

function AboutSection({
  title,
  summary,
  templateId,
  accentColor,
  isDarkMode,
}: {
  title: string;
  summary?: string;
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  if (!summary) return null;
  const isDev = templateId === "developer";

  return (
    <section className="space-y-4">
      <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
      <div
        className={`p-6 rounded-xl border leading-relaxed text-sm sm:text-base ${
          isDarkMode
            ? "bg-slate-900/60 border-slate-800 text-slate-300"
            : "bg-white border-slate-200 text-slate-700 shadow-sm"
        }`}
      >
        <p className="whitespace-pre-line">{summary}</p>
      </div>
    </section>
  );
}

function SkillsSection({
  title,
  skills,
  templateId,
  accentColor,
  isDarkMode,
}: {
  title: string;
  skills: string[];
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  if (!skills || skills.length === 0) return null;
  const isDev = templateId === "developer";

  return (
    <section className="space-y-4">
      <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
      <div className="flex flex-wrap gap-2">
        {skills.map((skill, index) => (
          <span
            key={index}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              isDev ? "font-mono" : ""
            } ${
              isDarkMode
                ? "bg-slate-900/80 border-slate-800 text-slate-200 hover:border-slate-700"
                : "bg-white border-slate-200 text-slate-800 hover:border-slate-300 shadow-sm"
            }`}
          >
            {skill}
          </span>
        ))}
      </div>
    </section>
  );
}

function ProjectsSection({
  title,
  projects,
  templateId,
  accentColor,
  isDarkMode,
  onInteract,
}: {
  title: string;
  projects: PortfolioProjectItem[];
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
  onInteract: (projectId: string) => void;
}) {
  if (!projects || projects.length === 0) return null;
  const isDev = templateId === "developer";
  const isAi = templateId === "ai_tech";

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
        <span
          className={`text-xs font-medium ${
            isDarkMode ? "text-slate-400" : "text-slate-500"
          }`}
        >
          {projects.length} verified {projects.length === 1 ? "work" : "works"}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {projects.map((project) => (
          <article
            key={project.id}
            onClick={() => onInteract(project.id)}
            className={`rounded-xl border p-6 flex flex-col justify-between transition-all hover:shadow-md ${
              isDarkMode
                ? "bg-slate-900/50 border-slate-800 hover:border-slate-700"
                : "bg-white border-slate-200 hover:border-slate-300 shadow-sm"
            } ${
              isAi
                ? "relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-0.5 before:bg-gradient-to-r before:from-transparent before:via-primary before:to-transparent"
                : ""
            }`}
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <h3
                  className={`text-base font-bold tracking-tight ${
                    isDev ? "font-mono" : ""
                  }`}
                >
                  {project.title}
                </h3>

                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold flex-shrink-0 ${
                    project.status === "completed"
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  }`}
                >
                  {project.status === "completed" ? (
                    <>
                      <CheckCircle2 className="w-3 h-3" /> Completed
                    </>
                  ) : (
                    <>
                      <Clock className="w-3 h-3" /> In Progress
                    </>
                  )}
                </span>
              </div>

              {project.candidate_contribution && (
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Role / Contribution: {project.candidate_contribution}
                </p>
              )}

              {project.problem_statement && (
                <div className="text-xs">
                  <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">
                    Problem
                  </span>
                  <p className="line-clamp-2 text-slate-600 dark:text-slate-300">
                    {project.problem_statement}
                  </p>
                </div>
              )}

              {project.description && (
                <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300 line-clamp-3">
                  {project.description}
                </p>
              )}

              {project.architecture_overview && (
                <div
                  className={`p-3 rounded-lg text-xs border ${
                    isDarkMode
                      ? "bg-slate-950/60 border-slate-800/80 text-slate-300"
                      : "bg-slate-50 border-slate-200/80 text-slate-700"
                  }`}
                >
                  <span className="font-semibold block mb-1 flex items-center gap-1.5 text-primary">
                    <Layers className="w-3.5 h-3.5" /> Architecture
                  </span>
                  <p className="line-clamp-2 font-mono text-[11px]">
                    {project.architecture_overview}
                  </p>
                </div>
              )}

              {project.outcomes && (
                <div className="text-xs">
                  <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 mb-1">
                    <Trophy className="w-3 h-3" /> Measurable Impact
                  </span>
                  <p className="text-slate-600 dark:text-slate-300 line-clamp-2">
                    {project.outcomes}
                  </p>
                </div>
              )}

              {/* Tech Stack Pills */}
              {project.tech_stack && project.tech_stack.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-2">
                  {project.tech_stack.map((t, idx) => (
                    <span
                      key={idx}
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium ${
                        isDarkMode
                          ? "bg-slate-800 text-slate-300"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Action Links */}
            <div className="flex items-center gap-3 pt-5 mt-4 border-t border-slate-200 dark:border-slate-800 text-xs">
              {project.repository_url && (
                <a
                  href={project.repository_url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => onInteract(project.id)}
                  className="inline-flex items-center gap-1 font-medium hover:underline font-mono"
                  style={{ color: accentColor }}
                >
                  <Github className="w-3.5 h-3.5" /> Repository
                </a>
              )}

              {project.live_demo_url && (
                <a
                  href={project.live_demo_url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => onInteract(project.id)}
                  className="inline-flex items-center gap-1 font-medium hover:underline"
                  style={{ color: accentColor }}
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Live Demo
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ExperienceSection({
  title,
  experience,
  templateId,
  accentColor,
  isDarkMode,
}: {
  title: string;
  experience: PortfolioWorkExperienceItem[];
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  if (!experience || experience.length === 0) return null;
  const isDev = templateId === "developer";

  return (
    <section className="space-y-6">
      <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
      <div className="space-y-6">
        {experience.map((exp, idx) => (
          <div
            key={idx}
            className={`p-6 rounded-xl border relative pl-6 transition-all ${
              isDarkMode
                ? "bg-slate-900/50 border-slate-800"
                : "bg-white border-slate-200 shadow-sm"
            }`}
          >
            <div
              className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl"
              style={{ backgroundColor: accentColor }}
            />
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
              <h3 className="text-base font-bold text-foreground">
                {exp.role || "Role"}
              </h3>
              {(exp.start_date || exp.end_date) && (
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {exp.start_date || ""}
                  {exp.end_date ? ` - ${exp.end_date}` : exp.is_current ? " - Present" : ""}
                </span>
              )}
            </div>

            <p className="text-xs font-semibold text-primary mb-3">
              {exp.company}
              {exp.location ? ` • ${exp.location}` : ""}
            </p>

            {exp.bullet_points && exp.bullet_points.length > 0 && (
              <ul className="space-y-1.5 text-xs sm:text-sm text-slate-600 dark:text-slate-300">
                {exp.bullet_points.map((b, bIdx) => (
                  <li key={bIdx} className="flex items-start gap-2">
                    <span
                      className="mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: accentColor }}
                    />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function EducationSection({
  title,
  education,
  templateId,
  accentColor,
  isDarkMode,
}: {
  title: string;
  education: PortfolioEducationItem[];
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  if (!education || education.length === 0) return null;
  const isDev = templateId === "developer";

  return (
    <section className="space-y-4">
      <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {education.map((edu, idx) => (
          <div
            key={idx}
            className={`p-5 rounded-xl border ${
              isDarkMode
                ? "bg-slate-900/50 border-slate-800"
                : "bg-white border-slate-200 shadow-sm"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <GraduationCap className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-bold text-foreground">
                {edu.degree}
              </h3>
            </div>
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
              {edu.institution}
              {edu.end_year ? ` • ${edu.end_year}` : edu.start_year ? ` • ${edu.start_year}` : ""}
            </p>
            {edu.highlights && edu.highlights.length > 0 && (
              <p className="text-xs text-slate-600 dark:text-slate-300">
                {edu.highlights.join(" • ")}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function CertificationsSection({
  title,
  certifications,
  achievements,
  templateId,
  accentColor,
  isDarkMode,
}: {
  title: string;
  certifications: PortfolioCertificationItem[];
  achievements: PortfolioAchievementItem[];
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  if (
    (!certifications || certifications.length === 0) &&
    (!achievements || achievements.length === 0)
  ) {
    return null;
  }
  const isDev = templateId === "developer";

  return (
    <section className="space-y-4">
      <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {certifications && certifications.length > 0 && (
          <div
            className={`p-5 rounded-xl border ${
              isDarkMode
                ? "bg-slate-900/50 border-slate-800"
                : "bg-white border-slate-200 shadow-sm"
            }`}
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3 text-slate-500 dark:text-slate-400">
              Certifications
            </h4>
            <ul className="space-y-2 text-xs">
              {certifications.map((cert, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                  <span>
                    <strong className="font-semibold">{cert.name}</strong>
                    {cert.issuer ? ` (${cert.issuer})` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {achievements && achievements.length > 0 && (
          <div
            className={`p-5 rounded-xl border ${
              isDarkMode
                ? "bg-slate-900/50 border-slate-800"
                : "bg-white border-slate-200 shadow-sm"
            }`}
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3 text-slate-500 dark:text-slate-400">
              Key Achievements
            </h4>
            <ul className="space-y-2 text-xs">
              {achievements.map((ach, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <Trophy className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                  <span>
                    <strong className="font-semibold">{ach.title}:</strong>{" "}
                    {ach.description}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function ContactSection({
  title,
  profile,
  templateId,
  accentColor,
  isDarkMode,
}: {
  title: string;
  profile?: PublicPortfolioDetail["profile_data"];
  templateId: string;
  accentColor: string;
  isDarkMode: boolean;
}) {
  const isDev = templateId === "developer";

  return (
    <section className="space-y-4">
      <SectionHeading title={title} accentColor={accentColor} isDev={isDev} />
      <div
        className={`p-8 rounded-2xl border text-center space-y-4 ${
          isDarkMode
            ? "bg-slate-900/50 border-slate-800"
            : "bg-white border-slate-200 shadow-sm"
        }`}
      >
        <h3 className="text-xl font-bold tracking-tight">Let&apos;s Connect</h3>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
          Interested in discussing engineering opportunities, collaboration, or code architecture? Reach out directly.
        </p>

        <div className="flex flex-wrap justify-center gap-3 pt-2">
          {profile?.contact_email && (
            <a
              href={`mailto:${profile.contact_email}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90 shadow-sm"
              style={{ backgroundColor: accentColor }}
            >
              <Mail className="w-4 h-4" /> Send Email
            </a>
          )}

          {profile?.linkedin_url && (
            <a
              href={profile.linkedin_url}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium border transition-colors ${
                isDarkMode
                  ? "border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-200"
                  : "border-slate-200 bg-white hover:bg-slate-100 text-slate-700"
              }`}
            >
              <Linkedin className="w-4 h-4" /> Connect on LinkedIn
            </a>
          )}

          {profile?.github_url && (
            <a
              href={profile.github_url}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium border transition-colors ${
                isDarkMode
                  ? "border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-200"
                  : "border-slate-200 bg-white hover:bg-slate-100 text-slate-700"
              }`}
            >
              <Github className="w-4 h-4" /> View GitHub Profile
            </a>
          )}
        </div>
      </div>
    </section>
  );
}

function SectionHeading({
  title,
  accentColor,
  isDev,
}: {
  title: string;
  accentColor: string;
  isDev: boolean;
}) {
  return (
    <div className="flex items-center gap-2 pb-1 border-b border-slate-200 dark:border-slate-800">
      <div
        className="w-1.5 h-5 rounded-full"
        style={{ backgroundColor: accentColor }}
      />
      <h2
        className={`text-lg sm:text-xl font-bold tracking-tight ${
          isDev ? "font-mono" : ""
        }`}
      >
        {isDev ? `<${title} />` : title}
      </h2>
    </div>
  );
}
