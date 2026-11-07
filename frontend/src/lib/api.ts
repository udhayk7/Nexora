export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ParsedContact {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  links: string[];
}

export interface ParsedExperience {
  title?: string | null;
  company?: string | null;
  date_range?: string | null;
  bullets: string[];
}

export interface ParsedEducation {
  institution?: string | null;
  degree?: string | null;
  year?: string | null;
  details: string[];
}

export interface ResumeParsedProfile {
  contact: ParsedContact;
  summary?: string | null;
  skills: string[];
  experience: ParsedExperience[];
  education: ParsedEducation[];
  projects: string[];
  certifications: string[];
}

export interface ResumeVersionSummary {
  id: string;
  version_number: number;
  original_filename: string;
  file_type: string;
  file_size: number;
  parsing_status: "uploaded" | "processing" | "parsed" | "failed";
  error_summary?: string | null;
  created_at: string;
}

export interface ResumeVersionDetail extends ResumeVersionSummary {
  parsed_content?: ResumeParsedProfile | null;
  raw_text?: string | null;
}

export interface ResumeSummary {
  id: string;
  title: string;
  current_version_id?: string | null;
  current_version_number?: number | null;
  parsing_status: "uploaded" | "processing" | "parsed" | "failed";
  original_filename?: string | null;
  file_type?: string | null;
  file_size?: number | null;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface ResumeDetail {
  id: string;
  title: string;
  current_version_id?: string | null;
  current_version?: ResumeVersionDetail | null;
  versions: ResumeVersionSummary[];
  version_count: number;
  created_at: string;
  updated_at: string;
}

// AI Resume Intelligence Interfaces
export interface EvidenceItem {
  section: string;
  excerpt: string;
}

export interface CandidateProfile {
  summary: string;
  domains: string[];
  career_level_estimate: string;
  evidence: EvidenceItem[];
}

export interface SkillsAnalysis {
  categorized_skills: Record<string, string[]>;
  supported_skills: string[];
  unevidenced_skills: string[];
  evidence: EvidenceItem[];
}

export interface ExperienceEvidence {
  summary: string;
  measurable_outcomes: string[];
  vague_or_unsupported_claims: string[];
  evidence: EvidenceItem[];
}

export interface ResumeStrength {
  strength: string;
  evidence: EvidenceItem;
}

export interface ImprovementOpportunity {
  category: string;
  issue: string;
  suggestion: string;
  referenced_excerpt?: string | null;
}

export interface RoleSuitability {
  role_name: string;
  suitability_band: string;
  heuristic_score: number;
  confidence: string;
  strengths: string[];
  gaps: string[];
  evidence: EvidenceItem[];
  disclaimer: string;
}

export interface ActionableRecommendation {
  priority: "high" | "medium" | "low";
  title: string;
  issue: string;
  why_it_matters: string;
  suggested_action: string;
  referenced_evidence?: string | null;
}

export interface ResumeAnalysisResult {
  profile: CandidateProfile;
  skills: SkillsAnalysis;
  experience_evidence: ExperienceEvidence;
  strengths: ResumeStrength[];
  improvement_opportunities: ImprovementOpportunity[];
  role_suitability: RoleSuitability[];
  recommendations: ActionableRecommendation[];
}

export interface ResumeAnalysisSummary {
  id: string;
  resume_id: string;
  version_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  provider: string;
  model: string;
  career_level?: string | null;
  top_domains: string[];
  created_at: string;
  completed_at?: string | null;
}

export interface ResumeAnalysisDetail {
  id: string;
  resume_id: string;
  version_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  provider: string;
  model: string;
  result?: ResumeAnalysisResult | null;
  error_summary?: string | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  estimated_cost_usd?: number | null;
  created_at: string;
  completed_at?: string | null;
}

export type CompanyCategory =
  | "product_company"
  | "mnc"
  | "gcc"
  | "big_four"
  | "large_it_services"
  | "established_startup"
  | "other";

export type VerificationStatus =
  | "verified"
  | "corroborated"
  | "unverified"
  | "suspicious";

export type CompanySourceType =
  | "official_website"
  | "careers_page"
  | "public_directory"
  | "user_added"
  | "curated_dataset"
  | "other";

export interface CompanySource {
  id: string;
  company_id: string;
  source_name: string;
  source_type: CompanySourceType;
  source_url?: string | null;
  evidence_summary?: string | null;
  first_seen_at: string;
  last_checked_at: string;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;
  name: string;
  normalized_name: string;
  website_url?: string | null;
  normalized_domain?: string | null;
  category: CompanyCategory;
  headquarters_country?: string | null;
  headquarters_city?: string | null;
  operating_regions: string[];
  industry_tags: string[];
  technology_tags: string[];
  size_band?: string | null;
  careers_url?: string | null;
  description?: string | null;
  primary_source?: string | null;
  primary_source_url?: string | null;
  verification_status: VerificationStatus;
  verification_notes?: string | null;
  last_verified_at?: string | null;
  created_by_user_id?: string | null;
  is_global: boolean;
  is_merged: boolean;
  merged_into_company_id?: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  sources_count: number;
}

export interface CompanyDetail extends Company {
  sources: CompanySource[];
}

export interface CompanyListResponse {
  items: Company[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface CompanyDuplicateMatch {
  company: Company;
  confidence: "high" | "medium";
  reason: string;
}

export interface CompanyDuplicateCheckResponse {
  normalized_name: string;
  normalized_domain?: string | null;
  matches: CompanyDuplicateMatch[];
}

export type WorkArrangementType = "onsite" | "hybrid" | "remote" | "unspecified";
export type JobStatusType = "active" | "expired" | "closed" | "suspicious";
export type JobVerificationStatusType =
  | "verified"
  | "corroborated"
  | "unverified"
  | "expired"
  | "suspicious";
export type JobFreshnessType = "recent" | "due_for_review" | "stale" | "unknown";
export type JobVerificationType = "system" | "user";
export type JobEvidenceType =
  | "careers_page"
  | "permitted_api"
  | "announcement"
  | "user_evidence"
  | "other";
export type JobObservedStatusType = "active" | "closed" | "removed" | "expired" | "unknown";

export type JobSourceType =
  | "careers_page"
  | "official_api"
  | "permitted_feed"
  | "user_added"
  | "curated_record"
  | "other";

export interface JobSource {
  id: string;
  job_id: string;
  source_name: string;
  source_type: JobSourceType;
  source_url?: string | null;
  external_id?: string | null;
  evidence_summary?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface JobVerification {
  id: string;
  job_id: string;
  verifier_type: JobVerificationType;
  verifier_user_id?: string | null;
  evidence_type: JobEvidenceType;
  evidence_url?: string | null;
  evidence_summary?: string | null;
  observed_status: JobObservedStatusType;
  verification_outcome: JobVerificationStatusType;
  reason: string;
  checked_at: string;
  created_at: string;
  metadata_json?: Record<string, unknown>;
}

export interface JobRecheckResponse {
  job_id: string;
  recheck_status: "completed" | "manual_evidence_required" | "failed";
  observed_status: JobObservedStatusType;
  freshness: JobFreshnessType;
  status_code?: number | null;
  message: string;
  verification?: JobVerification | null;
}

export interface Job {
  id: string;
  title: string;
  normalized_title: string;
  description: string;
  company_id?: string | null;
  company_name?: string | null;
  employment_type?: string | null;
  seniority_level?: string | null;
  work_arrangement: WorkArrangementType;
  location_text?: string | null;
  city?: string | null;
  state_province?: string | null;
  country?: string | null;
  remote_eligibility_regions: string[];
  skills_tags: string[];
  role_family?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  job_url: string;
  application_url?: string | null;
  external_source_id?: string | null;
  canonical_url_hash?: string | null;
  source_published_at?: string | null;
  first_seen_at: string;
  last_seen_at: string;
  last_checked_at: string;
  freshness: JobFreshnessType;
  job_status: JobStatusType;
  verification_status: JobVerificationStatusType;
  verification_notes?: string | null;
  last_verified_at?: string | null;
  created_by_user_id?: string | null;
  is_global: boolean;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  sources_count: number;
  company?: Company | null;
}

export interface JobDetail extends Job {
  sources: JobSource[];
  verification_history: JobVerification[];
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface JobDuplicateMatch {
  job: Job;
  confidence: "high" | "medium";
  reason: string;
}

export interface JobDuplicateCheckResponse {
  matches: JobDuplicateMatch[];
}

export interface FeedIngestResult {
  feed_name: string;
  total_processed: number;
  created_count: number;
  updated_count: number;
  errors_count: number;
  errors: Array<{ record_index?: number; error: string }>;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let memoryAccessToken: string | null = null;

export function getAccessToken(): string | null {
  return memoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  memoryAccessToken = token;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const headers = new Headers(options.headers || {});
  // Only set application/json if body is not FormData
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (memoryAccessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${memoryAccessToken}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include", // Transmit HttpOnly refresh cookie
  });

  if (!response.ok) {
    let errorData: ApiError = {
      code: `HTTP_${response.status}`,
      message: response.statusText || "Request failed",
    };

    try {
      const json = await response.json();
      if (json && json.error) {
        errorData = json.error;
      }
    } catch {
      // Non-JSON response
    }

    throw errorData;
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export async function downloadFile(
  endpoint: string,
  defaultFilename = "resume-document"
): Promise<void> {
  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers();
  if (memoryAccessToken) {
    headers.set("Authorization", `Bearer ${memoryAccessToken}`);
  }

  const response = await fetch(url, {
    method: "GET",
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let errorMsg = "Download failed";
    try {
      const json = await response.json();
      if (json && json.error) {
        errorMsg = json.error.message || errorMsg;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = defaultFilename;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(blobUrl);
}

// ---------------------------------------------------------------------------
// Matching & Ranking Engine Types
// ---------------------------------------------------------------------------

export interface SignalEvidenceRef {
  section: string;
  excerpt: string;
}

export interface PositiveSignal {
  dimension: string;
  title: string;
  description: string;
  evidence?: SignalEvidenceRef | null;
}

export interface GapSignal {
  type: "missing" | "mismatch";
  dimension: string;
  title: string;
  description: string;
}

export type SalaryStatusType =
  | "matched"
  | "below_minimum"
  | "above_minimum"
  | "undisclosed"
  | "no_preference";

export interface ScoreBreakdown {
  skills_score: number;
  role_score: number;
  experience_score: number;
  location_score: number;
  salary_score?: number | null;
  salary_status: SalaryStatusType;
  trust_adjustment: number;
  trust_signals: Record<string, unknown>;
  weights_applied: Record<string, number>;
  raw_weighted_score: number;
  final_score: number;
  disclaimer: string;
}

export interface JobMatch {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string;
  version_id: string;
  analysis_id: string;
  engine_version: string;
  match_score: number;
  score_breakdown: ScoreBreakdown;
  positive_signals: PositiveSignal[];
  gap_signals: GapSignal[];
  is_saved: boolean;
  is_dismissed: boolean;
  created_at: string;
  updated_at: string;
  job?: Job | null;
}

export interface JobMatchListResponse {
  items: JobMatch[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface JobMatchRunRequest {
  resume_id?: string;
  version_id?: string;
  min_score_threshold?: number;
  limit?: number;
}

export interface JobMatchRunResult {
  matches_computed: number;
  matches_saved: number;
  resume_id: string;
  version_id: string;
  analysis_id: string;
  engine_version: string;
  message: string;
}

export interface UserMatchingPreference {
  id: string;
  user_id: string;
  target_role_families: string[];
  preferred_locations: string[];
  work_arrangement_preferences: string[];
  min_salary?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  seniority_preferences: string[];
  preferred_industries: string[];
  excluded_industries: string[];
  preferred_skills: string[];
  excluded_roles: string[];
  excluded_terms: string[];
  created_at?: string;
  updated_at?: string;
}

export interface UserMatchingPreferenceUpdate {
  target_role_families?: string[];
  preferred_locations?: string[];
  preferred_work_arrangements?: string[];
  min_salary?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  seniority_preferences?: string[];
  preferred_industries?: string[];
  excluded_industries?: string[];
  preferred_skills?: string[];
  excluded_roles?: string[];
  excluded_terms?: string[];
}

export interface JobMatchStateUpdate {
  is_saved?: boolean;
  is_dismissed?: boolean;
}

// ==========================================
// Resume Tailoring Studio Interfaces
// ==========================================

export interface SupportingEvidence {
  section: string;
  excerpt: string;
}

export interface JobRequirementAnalysis {
  relevant_skills: string[];
  relevant_experience: string[];
  missing_requirements: string[];
  keyword_opportunities: string[];
  improvement_opportunities: string[];
  summary_notes?: string | null;
}

export interface TailoringChange {
  id: string;
  session_id: string;
  section_name: string;
  change_type: string;
  original_content: string;
  proposed_content: string;
  user_content?: string | null;
  active_content: string;
  reason: string;
  supporting_evidence?: SupportingEvidence | null;
  related_job_requirement: string;
  confidence_level: string;
  status: "pending" | "accepted" | "rejected" | "modified";
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface TailoringSession {
  id: string;
  user_id: string;
  resume_id: string;
  version_id: string;
  job_id: string;
  status: string;
  job_analysis?: JobRequirementAnalysis | null;
  latex_content?: string | null;
  tailored_version_id?: string | null;
  provider?: string | null;
  model?: string | null;
  error_summary?: string | null;
  changes: TailoringChange[];
  job?: Job | null;
  resume_title?: string | null;
  parent_version_number?: number | null;
  created_at: string;
  updated_at: string;
}

export interface TailoringSessionSummary {
  id: string;
  resume_id: string;
  version_id: string;
  job_id: string;
  status: string;
  job_title: string;
  company_name: string;
  resume_title: string;
  tailored_version_id?: string | null;
  total_changes: number;
  accepted_changes: number;
  created_at: string;
  updated_at: string;
}

export interface CompilePDFResponse {
  success: boolean;
  compilation_engine: string;
  download_url?: string | null;
  error_log?: string | null;
  page_count: number;
  disclaimer: string;
}

export interface TailoredVersionResponse {
  id: string;
  resume_id: string;
  version_number: number;
  parent_version_id?: string | null;
  job_id?: string | null;
  tailoring_session_id?: string | null;
  is_tailored: boolean;
  title?: string | null;
  original_filename: string;
  file_type: string;
  file_size: number;
  parsing_status: string;
  latex_source?: string | null;
  pdf_storage_path?: string | null;
  tailoring_metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface JobMatchFilterParams {
  role_family?: string;
  location?: string;
  work_arrangement?: string;
  freshness?: string;
  verification_status?: string;
  min_score?: number;
  is_saved?: boolean;
  include_dismissed?: boolean;
  sort_by?: "score" | "date";
  page?: number;
  per_page?: number;
}

// ---------------------------------------------------------------------------
// Jobs API Client
// ---------------------------------------------------------------------------

export const jobsApi = {
  listJobs: (params?: { page?: number; page_size?: number; q?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("per_page", String(params.page_size));
    if (params?.q) q.append("q", params.q);
    const qs = q.toString();
    return apiClient<JobListResponse>(`/jobs${qs ? `?${qs}` : ""}`);
  },
  getJob: (id: string) => apiClient<JobDetail>(`/jobs/${id}`),
};

// ---------------------------------------------------------------------------
// Resume API Client
// ---------------------------------------------------------------------------

export const resumesApi = {
  listResumes: () => apiClient<ResumeSummary[]>("/resumes"),
  getResume: (id: string) => apiClient<ResumeDetail>(`/resumes/${id}`),
};

// ---------------------------------------------------------------------------
// Matching & Ranking API Client
// ---------------------------------------------------------------------------

export const matchingApi = {
  getPreferences: () =>
    apiClient<UserMatchingPreference>("/matches/preferences"),

  updatePreferences: (data: UserMatchingPreferenceUpdate) =>
    apiClient<UserMatchingPreference>("/matches/preferences", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  runMatches: (data?: JobMatchRunRequest) =>
    apiClient<JobMatchRunResult>("/matches/run", {
      method: "POST",
      body: JSON.stringify(data || {}),
    }),

  listMatches: (params?: JobMatchFilterParams) => {
    const query = new URLSearchParams();
    if (params) {
      if (params.role_family && params.role_family !== "all") {
        query.append("role_family", params.role_family);
      }
      if (params.location) {
        query.append("location", params.location);
      }
      if (params.work_arrangement && params.work_arrangement !== "all") {
        query.append("work_arrangement", params.work_arrangement);
      }
      if (params.freshness && params.freshness !== "all") {
        query.append("freshness", params.freshness);
      }
      if (params.verification_status && params.verification_status !== "all") {
        query.append("verification_status", params.verification_status);
      }
      if (params.min_score !== undefined) {
        query.append("min_score", params.min_score.toString());
      }
      if (params.is_saved !== undefined) {
        query.append("is_saved", String(params.is_saved));
      }
      if (params.include_dismissed !== undefined) {
        query.append("include_dismissed", String(params.include_dismissed));
      }
      if (params.sort_by) {
        query.append("sort_by", params.sort_by);
      }
      if (params.page) {
        query.append("page", params.page.toString());
      }
      if (params.per_page) {
        query.append("per_page", params.per_page.toString());
      }
    }
    const qStr = query.toString();
    return apiClient<JobMatchListResponse>(`/matches${qStr ? `?${qStr}` : ""}`);
  },

  getMatchDetail: (matchId: string) =>
    apiClient<JobMatch>(`/matches/${matchId}`),

  updateMatchState: (matchId: string, state: JobMatchStateUpdate) =>
    apiClient<JobMatch>(`/matches/${matchId}`, {
      method: "PATCH",
      body: JSON.stringify(state),
    }),
};

export async function fetchBlob(endpoint: string): Promise<Blob> {
  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers();
  if (memoryAccessToken) {
    headers.set("Authorization", `Bearer ${memoryAccessToken}`);
  }

  const response = await fetch(url, {
    method: "GET",
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch file: ${response.statusText}`);
  }

  return response.blob();
}

export const tailoringApi = {
  createSession: (data: { resume_id: string; version_id?: string; job_id: string }) =>
    apiClient<TailoringSession>("/tailoring/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listSessions: (skip = 0, limit = 50) =>
    apiClient<TailoringSessionSummary[]>(`/tailoring/sessions?skip=${skip}&limit=${limit}`),

  getSession: (sessionId: string) =>
    apiClient<TailoringSession>(`/tailoring/sessions/${sessionId}`),

  updateChangeStatus: (
    sessionId: string,
    changeId: string,
    data: { status: "pending" | "accepted" | "rejected" | "modified"; user_content?: string }
  ) =>
    apiClient<TailoringSession>(`/tailoring/sessions/${sessionId}/changes/${changeId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  batchUpdateChanges: (
    sessionId: string,
    action: "accept_all" | "reject_all" | "restore_original"
  ) =>
    apiClient<TailoringSession>(`/tailoring/sessions/${sessionId}/batch`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),

  updateContent: (sessionId: string, latexContent: string) =>
    apiClient<TailoringSession>(`/tailoring/sessions/${sessionId}/content`, {
      method: "PUT",
      body: JSON.stringify({ latex_content: latexContent }),
    }),

  compilePdf: (sessionId: string, latexContent?: string) =>
    apiClient<CompilePDFResponse>(`/tailoring/sessions/${sessionId}/compile`, {
      method: "POST",
      body: JSON.stringify({ latex_content: latexContent }),
    }),

  downloadPdf: (sessionId: string, filename = "tailored_resume.pdf") =>
    downloadFile(`/tailoring/sessions/${sessionId}/pdf`, filename),

  downloadLatex: (sessionId: string, filename = "tailored_resume.tex") =>
    downloadFile(`/tailoring/sessions/${sessionId}/latex`, filename),

  saveTailoredVersion: (
    sessionId: string,
    data: { title?: string; latex_content?: string }
  ) =>
    apiClient<TailoredVersionResponse>(`/tailoring/sessions/${sessionId}/save`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// Application Management Interfaces
export type ApplicationStatus =
  | "interested"
  | "preparing"
  | "applied"
  | "shortlisted"
  | "assessment"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export type ApplicationChannel =
  | "official_portal"
  | "email"
  | "referral"
  | "external_form"
  | "other";

export interface ApplicationStatusHistory {
  id: string;
  application_id: string;
  from_status?: ApplicationStatus | null;
  to_status: ApplicationStatus;
  note?: string | null;
  created_at: string;
}

export interface ApplicationActivity {
  id: string;
  application_id: string;
  user_id: string;
  activity_type:
    | "status_change"
    | "submission"
    | "note"
    | "interview"
    | "assessment"
    | "recruiter_contact"
    | "follow_up"
    | "other";
  title: string;
  description?: string | null;
  metadata_json?: Record<string, unknown> | null;
  occurred_at: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationInterview {
  id: string;
  application_id: string;
  user_id: string;
  round_number: number;
  interview_type: string;
  title: string;
  scheduled_at: string;
  duration_minutes: number;
  meeting_url?: string | null;
  interviewers: string[];
  preparation_notes?: string | null;
  feedback?: string | null;
  outcome?: "pending" | "passed" | "failed" | "cancelled" | "waived" | null;
  status: "scheduled" | "completed" | "cancelled" | "rescheduled";
  next_steps?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobApplicationSummary {
  id: string;
  user_id: string;
  job_id?: string | null;
  company_id?: string | null;
  title: string;
  company_name: string;
  status: ApplicationStatus;
  application_channel: ApplicationChannel;
  applied_at?: string | null;
  submission_confirmed: boolean;
  link_opened_at?: string | null;
  application_url?: string | null;
  deadline_at?: string | null;
  next_follow_up_at?: string | null;
  resume_id?: string | null;
  resume_version_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobApplicationDetail extends JobApplicationSummary {
  notes?: string | null;
  recruiter_name?: string | null;
  recruiter_email?: string | null;
  recruiter_phone?: string | null;
  recruiter_linkedin_url?: string | null;
  salary_offered?: number | null;
  currency?: string | null;
  location_workplace_type?: string | null;
  metadata_json?: Record<string, unknown> | null;
  status_history: ApplicationStatusHistory[];
  activities: ApplicationActivity[];
  interviews: ApplicationInterview[];
}

export interface JobApplicationListResponse {
  items: JobApplicationSummary[];
  total: number;
  skip: number;
  limit: number;
}

export interface UpcomingEvent {
  type: "deadline" | "follow_up" | "interview" | "assessment";
  title: string;
  date: string;
  application_id: string;
  meeting_url?: string;
}

export interface ApplicationAnalytics {
  total_applications: number;
  in_progress_count: number;
  interviews_scheduled_count: number;
  assessments_pending_count: number;
  offers_count: number;
  rejections_count: number;
  upcoming_deadlines_count: number;
  upcoming_follow_ups_count: number;
  status_distribution: Record<string, number>;
  channel_distribution: Record<string, number>;
  activity_trend: Array<{ week: string; count: number }>;
  upcoming_events: UpcomingEvent[];
}

export interface CreateApplicationPayload {
  title: string;
  company_name: string;
  job_id?: string | null;
  company_id?: string | null;
  status?: ApplicationStatus;
  application_channel?: ApplicationChannel;
  applied_at?: string | null;
  submission_confirmed?: boolean;
  application_url?: string | null;
  deadline_at?: string | null;
  next_follow_up_at?: string | null;
  notes?: string | null;
  resume_id?: string | null;
  resume_version_id?: string | null;
  recruiter_name?: string | null;
  recruiter_email?: string | null;
  recruiter_phone?: string | null;
  recruiter_linkedin_url?: string | null;
  salary_offered?: number | null;
  currency?: string | null;
  location_workplace_type?: string | null;
}

export interface UpdateApplicationPayload {
  title?: string;
  company_name?: string;
  status?: ApplicationStatus;
  application_channel?: ApplicationChannel;
  applied_at?: string | null;
  submission_confirmed?: boolean;
  application_url?: string | null;
  deadline_at?: string | null;
  next_follow_up_at?: string | null;
  notes?: string | null;
  resume_id?: string | null;
  resume_version_id?: string | null;
  recruiter_name?: string | null;
  recruiter_email?: string | null;
  recruiter_phone?: string | null;
  recruiter_linkedin_url?: string | null;
  salary_offered?: number | null;
  currency?: string | null;
  location_workplace_type?: string | null;
}

export interface CreateActivityPayload {
  activity_type:
    | "status_change"
    | "submission"
    | "note"
    | "interview"
    | "assessment"
    | "recruiter_contact"
    | "follow_up"
    | "other";
  title: string;
  description?: string;
  occurred_at?: string;
  metadata_json?: Record<string, unknown>;
}

export interface CreateInterviewPayload {
  round_number?: number;
  interview_type: string;
  title: string;
  scheduled_at: string;
  duration_minutes?: number;
  meeting_url?: string;
  interviewers?: string[];
  preparation_notes?: string;
  feedback?: string;
  outcome?: "pending" | "passed" | "failed" | "cancelled" | "waived";
  status?: "scheduled" | "completed" | "cancelled" | "rescheduled";
  next_steps?: string;
}

export interface UpdateInterviewPayload {
  round_number?: number;
  interview_type?: string;
  title?: string;
  scheduled_at?: string;
  duration_minutes?: number;
  meeting_url?: string;
  interviewers?: string[];
  preparation_notes?: string;
  feedback?: string;
  outcome?: "pending" | "passed" | "failed" | "cancelled" | "waived";
  status?: "scheduled" | "completed" | "cancelled" | "rescheduled";
  next_steps?: string;
}

export const applicationsApi = {
  getAnalytics: () => apiClient<ApplicationAnalytics>("/applications/analytics"),

  listApplications: (params?: {
    status?: ApplicationStatus;
    channel?: ApplicationChannel;
    search?: string;
    skip?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.channel) q.append("channel", params.channel);
    if (params?.search) q.append("search", params.search);
    if (params?.skip !== undefined) q.append("skip", String(params.skip));
    if (params?.limit !== undefined) q.append("limit", String(params.limit));
    const qs = q.toString();
    return apiClient<JobApplicationListResponse>(`/applications${qs ? `?${qs}` : ""}`);
  },

  getApplication: (id: string) => apiClient<JobApplicationDetail>(`/applications/${id}`),

  createApplication: (payload: CreateApplicationPayload) =>
    apiClient<JobApplicationDetail>("/applications", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateApplication: (id: string, payload: UpdateApplicationPayload) =>
    apiClient<JobApplicationDetail>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  updateStatus: (
    id: string,
    payload: {
      status: ApplicationStatus;
      note?: string;
      submission_confirmed?: boolean;
      applied_at?: string;
    }
  ) =>
    apiClient<JobApplicationDetail>(`/applications/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  markLinkOpened: (id: string) =>
    apiClient<JobApplicationSummary>(`/applications/${id}/open-link`, {
      method: "POST",
    }),

  deleteApplication: (id: string) =>
    apiClient<{ message: string }>(`/applications/${id}`, {
      method: "DELETE",
    }),

  createActivity: (applicationId: string, payload: CreateActivityPayload) =>
    apiClient<ApplicationActivity>(`/applications/${applicationId}/activities`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteActivity: (applicationId: string, activityId: string) =>
    apiClient<{ message: string }>(
      `/applications/${applicationId}/activities/${activityId}`,
      { method: "DELETE" }
    ),

  createInterview: (applicationId: string, payload: CreateInterviewPayload) =>
    apiClient<ApplicationInterview>(`/applications/${applicationId}/interviews`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateInterview: (
    applicationId: string,
    interviewId: string,
    payload: UpdateInterviewPayload
  ) =>
    apiClient<ApplicationInterview>(
      `/applications/${applicationId}/interviews/${interviewId}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      }
    ),

  deleteInterview: (applicationId: string, interviewId: string) =>
    apiClient<{ message: string }>(
      `/applications/${applicationId}/interviews/${interviewId}`,
      { method: "DELETE" }
    ),
};

// Notification & Reminder Interfaces
export type NotificationType =
  | "application_follow_up"
  | "interview_reminder"
  | "assessment_reminder"
  | "application_deadline"
  | "job_freshness_update"
  | "task_completion"
  | "system";

export interface NotificationItem {
  id: string;
  user_id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  entity_type?: string | null;
  entity_id?: string | null;
  action_url?: string | null;
  is_read: boolean;
  read_at?: string | null;
  scheduled_for?: string | null;
  delivery_status: string;
  idempotency_key?: string | null;
  metadata_json?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
  skip: number;
  limit: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkReadAllResponse {
  updated_count: number;
}

export interface UserNotificationPreference {
  id: string;
  user_id: string;
  enable_in_app: boolean;
  enable_interview_reminders: boolean;
  enable_assessment_reminders: boolean;
  enable_follow_up_reminders: boolean;
  enable_deadline_reminders: boolean;
  enable_job_freshness_updates: boolean;
  enable_task_completion_updates: boolean;
  enable_system_notifications: boolean;
  interview_reminder_24h: boolean;
  interview_reminder_1h: boolean;
  preferred_timezone: string;
  created_at: string;
  updated_at: string;
}

export interface UserNotificationPreferenceUpdate {
  enable_in_app?: boolean;
  enable_interview_reminders?: boolean;
  enable_assessment_reminders?: boolean;
  enable_follow_up_reminders?: boolean;
  enable_deadline_reminders?: boolean;
  enable_job_freshness_updates?: boolean;
  enable_task_completion_updates?: boolean;
  enable_system_notifications?: boolean;
  interview_reminder_24h?: boolean;
  interview_reminder_1h?: boolean;
  preferred_timezone?: string;
}

export interface ProcessRemindersResponse {
  reminders_created: number;
  scanned_interviews: number;
  scanned_applications: number;
}

export const notificationsApi = {
  list: (params?: {
    unread_only?: boolean;
    notification_type?: string;
    skip?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.unread_only) q.append("unread_only", "true");
    if (params?.notification_type && params.notification_type !== "all") {
      q.append("notification_type", params.notification_type);
    }
    if (params?.skip !== undefined) q.append("skip", String(params.skip));
    if (params?.limit !== undefined) q.append("limit", String(params.limit));
    const qs = q.toString();
    return apiClient<NotificationListResponse>(`/notifications${qs ? `?${qs}` : ""}`);
  },

  getUnreadCount: () => apiClient<UnreadCountResponse>("/notifications/unread-count"),

  markRead: (id: string) =>
    apiClient<NotificationItem>(`/notifications/${id}/read`, {
      method: "PATCH",
    }),

  markAllRead: () =>
    apiClient<MarkReadAllResponse>("/notifications/read-all", {
      method: "POST",
    }),

  delete: (id: string) =>
    apiClient<{ message: string }>(`/notifications/${id}`, {
      method: "DELETE",
    }),

  getPreferences: () =>
    apiClient<UserNotificationPreference>("/notifications/preferences"),

  updatePreferences: (data: UserNotificationPreferenceUpdate) =>
    apiClient<UserNotificationPreference>("/notifications/preferences", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  processReminders: () =>
    apiClient<ProcessRemindersResponse>("/notifications/process-reminders", {
      method: "POST",
    }),
};

// ============================================================================
// Automated Job Discovery Interfaces & API
// ============================================================================

export interface DiscoveryOverview {
  total_sources: number;
  total_active_sources: number;
  sources_scanned: number;
  new_jobs_discovered: number;
  updated_jobs: number;
  failed_source_scans: number;
  last_discovery_run: string | null;
  supported_adapters: {
    id: string;
    name: string;
    description: string;
    example_token: string;
    token_label: string;
  }[];
}

export interface DiscoverySource {
  id: string;
  company_id: string;
  company_name?: string | null;
  source_name: string;
  source_type: string;
  adapter_name?: string | null;
  source_url?: string | null;
  board_token?: string | null;
  is_enabled: boolean;
  scan_frequency_hours: number;
  last_successful_scan_at?: string | null;
  last_scan_status?: string | null;
  last_scan_message?: string | null;
  jobs_discovered_count: number;
  error_count: number;
  first_seen_at: string;
  last_checked_at: string;
  created_at: string;
  updated_at: string;
}

export interface DiscoverySourceListResponse {
  items: DiscoverySource[];
  total: number;
  skip: number;
  limit: number;
}

export interface DiscoverySourceCreateInput {
  company_id: string;
  source_name: string;
  source_type?: string;
  adapter_name: string;
  source_url?: string;
  board_token?: string;
  scan_frequency_hours?: number;
  is_enabled?: boolean;
}

export interface DiscoverySourceUpdateInput {
  source_name?: string;
  adapter_name?: string;
  source_url?: string;
  board_token?: string;
  scan_frequency_hours?: number;
  is_enabled?: boolean;
}

export interface DiscoverySourceTestRequest {
  adapter_name: string;
  source_url?: string;
  board_token?: string;
}

export interface DiscoverySourceTestResponse {
  is_success: boolean;
  message: string;
  jobs_detected: number;
  sample_jobs: {
    title: string;
    location?: string;
    role_family?: string;
    seniority?: string;
    skills?: string[];
    url: string;
  }[];
}

export interface DiscoveryScanResult {
  source_id: string;
  company_name: string;
  adapter_name: string;
  status: string;
  jobs_found: number;
  jobs_imported: number;
  jobs_updated: number;
  message: string;
  duration_seconds: number;
}

export interface DiscoveryBatchScanResult {
  sources_scanned: number;
  total_jobs_found: number;
  total_jobs_imported: number;
  total_jobs_updated: number;
  failed_sources: number;
  results: DiscoveryScanResult[];
}

export interface DiscoveryScanLogItem {
  id: string;
  company_source_id?: string | null;
  company_id?: string | null;
  company_name?: string | null;
  adapter_name: string;
  scan_type: string;
  status: string;
  jobs_found: number;
  jobs_imported: number;
  jobs_updated: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
  duration_seconds?: number | null;
}

export interface DiscoveryScanLogListResponse {
  items: DiscoveryScanLogItem[];
  total: number;
  skip: number;
  limit: number;
}

export const discoveryApi = {
  getOverview: () => apiClient<DiscoveryOverview>("/discovery/overview"),

  getAdapters: () =>
    apiClient<
      {
        id: string;
        name: string;
        description: string;
        example_token: string;
        token_label: string;
      }[]
    >("/discovery/adapters"),

  listSources: (params?: {
    company_id?: string;
    adapter_name?: string;
    is_enabled?: boolean;
    skip?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.company_id) q.append("company_id", params.company_id);
    if (params?.adapter_name) q.append("adapter_name", params.adapter_name);
    if (params?.is_enabled !== undefined) q.append("is_enabled", String(params.is_enabled));
    if (params?.skip !== undefined) q.append("skip", String(params.skip));
    if (params?.limit !== undefined) q.append("limit", String(params.limit));
    const qs = q.toString();
    return apiClient<DiscoverySourceListResponse>(`/discovery/sources${qs ? `?${qs}` : ""}`);
  },

  createSource: (data: DiscoverySourceCreateInput) =>
    apiClient<DiscoverySource>("/discovery/sources", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSource: (id: string, data: DiscoverySourceUpdateInput) =>
    apiClient<DiscoverySource>(`/discovery/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteSource: (id: string) =>
    apiClient<void>(`/discovery/sources/${id}`, {
      method: "DELETE",
    }),

  testSource: (data: DiscoverySourceTestRequest) =>
    apiClient<DiscoverySourceTestResponse>("/discovery/sources/test", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  scanSource: (id: string) =>
    apiClient<DiscoveryScanResult>(`/discovery/sources/${id}/scan`, {
      method: "POST",
    }),

  scanAll: (only_due: boolean = false) =>
    apiClient<DiscoveryBatchScanResult>(`/discovery/sources/scan-all?only_due=${only_due}`, {
      method: "POST",
    }),

  getLogs: (params?: {
    source_id?: string;
    company_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.source_id) q.append("source_id", params.source_id);
    if (params?.company_id) q.append("company_id", params.company_id);
    if (params?.skip !== undefined) q.append("skip", String(params.skip));
    if (params?.limit !== undefined) q.append("limit", String(params.limit));
    const qs = q.toString();
    return apiClient<DiscoveryScanLogListResponse>(`/discovery/logs${qs ? `?${qs}` : ""}`);
  },
};

// ---------------------------------------------------------------------------
// Recommendations & AI Job Intelligence Types
// ---------------------------------------------------------------------------

export interface JobIntelligence {
  id: string;
  job_id: string;
  content_hash: string;
  provider: string;
  model: string;
  status: string;
  error_message?: string | null;
  required_skills: string[];
  preferred_skills: string[];
  experience_requirements: {
    min_years?: number;
    max_years?: number | null;
    description?: string;
  };
  educational_qualifications: string[];
  responsibilities: string[];
  tools_and_frameworks: string[];
  seniority_level: string;
  work_arrangement: string;
  compensation_info?: {
    min?: number;
    max?: number;
    currency?: string;
    period?: string;
    disclosed?: boolean;
  } | null;
  application_requirements: string[];
  evidence_excerpts: Record<string, string>;
  is_deterministic_fallback: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIStrengthItem {
  title: string;
  description: string;
  evidence_resume?: string;
  evidence_job?: string;
}

export interface AISkillGapItem {
  skill: string;
  importance: "high" | "medium" | "low";
  reason: string;
  can_learn_on_job: boolean;
}

export interface AINextStepItem {
  step: string;
  action: string;
  priority: "high" | "medium" | "low";
}

export interface AIJobMatch {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string;
  resume_version_id: string;
  job_intelligence_id?: string | null;
  assessment_hash: string;
  compatibility_rating: "strong" | "moderate" | "growth_opportunity" | "poor";
  fit_score?: number | null;
  fit_summary: string;
  strengths: AIStrengthItem[];
  skill_gaps: AISkillGapItem[];
  experience_alignment: {
    seniority_fit?: string;
    candidate_seniority?: string;
    job_seniority?: string;
    reasoning?: string;
  };
  transferable_skills: string[];
  missing_requirements: string[];
  recommendation_rationale: string;
  next_steps: AINextStepItem[];
  evidence_citations: Array<{ title: string; evidence_resume?: string }>;
  provider: string;
  model: string;
  status: string;
  error_message?: string | null;
  is_deterministic_fallback: boolean;
  created_at: string;
}

export interface RecommendationExplanation {
  why_matches: {
    skills?: string[];
    experience?: string;
    projects?: string[];
    preference_alignment?: string;
  };
  potential_gaps: {
    missing_skills?: string[];
    experience_gaps?: string[];
    qualification_mismatches?: string[];
  };
  recommended_next_steps: string[];
}

export interface JobRecommendationItem {
  job_id: string;
  title: string;
  company_name: string;
  company_logo_url?: string | null;
  location_text?: string | null;
  work_arrangement: string;
  role_family?: string | null;
  seniority_level?: string | null;
  employment_type?: string | null;
  job_url: string;
  application_url?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  salary_disclosed: boolean;
  verification_status: string;
  freshness: string;
  deterministic_score: number;
  recommendation_score: number;
  score_breakdown: ScoreBreakdown;
  is_saved: boolean;
  is_dismissed: boolean;
  has_applied: boolean;
  ai_evaluated: boolean;
  ai_compatibility_rating?: string | null;
  ai_fit_score?: number | null;
  explanation: RecommendationExplanation;
  first_seen_at: string;
}

export interface RecommendationListResponse {
  items: JobRecommendationItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  active_resume_version_id?: string | null;
  active_resume_title?: string | null;
  stats: {
    top_score: number;
    total_count: number;
    ai_evaluated_count: number;
    verified_count: number;
  };
}

export interface RecommendationRefreshRequest {
  resume_version_id?: string;
  evaluate_top_ai?: boolean;
  max_ai_evaluations?: number;
}

export interface RecommendationRefreshResponse {
  message: string;
  recommendations_count: number;
  ai_evaluations_run: number;
}

export const recommendationsApi = {
  getRecommendations: (params?: {
    resume_version_id?: string;
    role_family?: string;
    location?: string;
    work_arrangement?: string;
    seniority?: string;
    verification_status?: string;
    min_score?: number;
    salary_disclosed_only?: boolean;
    include_applied?: boolean;
    search_query?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.resume_version_id) q.append("resume_version_id", params.resume_version_id);
    if (params?.role_family) q.append("role_family", params.role_family);
    if (params?.location) q.append("location", params.location);
    if (params?.work_arrangement) q.append("work_arrangement", params.work_arrangement);
    if (params?.seniority) q.append("seniority", params.seniority);
    if (params?.verification_status) q.append("verification_status", params.verification_status);
    if (params?.min_score !== undefined) q.append("min_score", String(params.min_score));
    if (params?.salary_disclosed_only) q.append("salary_disclosed_only", "true");
    if (params?.include_applied) q.append("include_applied", "true");
    if (params?.search_query) q.append("search_query", params.search_query);
    if (params?.sort_by) q.append("sort_by", params.sort_by);
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("page_size", String(params.page_size));
    const qs = q.toString();
    return apiClient<RecommendationListResponse>(`/recommendations${qs ? `?${qs}` : ""}`);
  },

  refreshRecommendations: (data: RecommendationRefreshRequest) =>
    apiClient<RecommendationRefreshResponse>("/recommendations/refresh", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  runAIMatch: (jobId: string, params?: { resume_version_id?: string; force_refresh?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.resume_version_id) q.append("resume_version_id", params.resume_version_id);
    if (params?.force_refresh) q.append("force_refresh", "true");
    const qs = q.toString();
    return apiClient<AIJobMatch>(`/recommendations/jobs/${jobId}/ai-match${qs ? `?${qs}` : ""}`, {
      method: "POST",
    });
  },

  getAIMatch: (jobId: string, resumeVersionId?: string) => {
    const qs = resumeVersionId ? `?resume_version_id=${resumeVersionId}` : "";
    return apiClient<AIJobMatch>(`/recommendations/jobs/${jobId}/ai-match${qs}`);
  },

  getJobIntelligence: (jobId: string) =>
    apiClient<JobIntelligence>(`/recommendations/jobs/${jobId}/intelligence`),

  analyzeJobIntelligence: (jobId: string, force_refresh: boolean = false) =>
    apiClient<JobIntelligence>(
      `/recommendations/jobs/${jobId}/intelligence?force_refresh=${force_refresh}`,
      {
        method: "POST",
      }
    ),

  updateJobState: (
    jobId: string,
    state: { is_saved?: boolean; is_dismissed?: boolean }
  ) =>
    apiClient<{ job_id: string; is_saved: boolean; is_dismissed: boolean }>(
      `/recommendations/jobs/${jobId}/state`,
      {
        method: "PATCH",
        body: JSON.stringify(state),
      }
    ),
};

export const matchesApi = matchingApi;

// ============================================================================
// Application Assistant & Gmail Integration Interfaces
// ============================================================================

export interface GoogleAuthUrlResponse {
  authorization_url: string;
  state: string;
}

export interface GmailConnectionStatus {
  is_connected: boolean;
  email: string | null;
  scopes: string[];
  connected_at: string | null;
  is_token_valid: boolean;
}

export interface ChecklistItem {
  id: string;
  label: string;
  completed: boolean;
  required: boolean;
  category: string;
  notes: string | null;
}

export interface ApplicationPreparation {
  id: string;
  user_id: string;
  job_id: string;
  application_id: string | null;
  resume_id: string | null;
  resume_version_id: string | null;
  checklist_status: "not_started" | "in_progress" | "ready_for_review" | "completed";
  checklist_items: ChecklistItem[];
  qa_answers: QAItem[];
  portal_opened_at: string | null;
  submission_confirmed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CoverLetter {
  id: string;
  user_id: string;
  job_id: string;
  preparation_id: string | null;
  resume_version_id: string | null;
  version_number: number;
  title: string;
  content: string;
  opening: string | null;
  body_paragraphs: string[];
  closing: string | null;
  skill_alignment: string[];
  experience_references: Array<{ name?: string; description?: string }>;
  user_instructions: string | null;
  is_approved: boolean;
  approved_at: string | null;
  pdf_path: string | null;
  provider: string | null;
  model: string | null;
  is_deterministic_fallback: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApplicationEmail {
  id: string;
  user_id: string;
  job_id: string | null;
  application_id: string | null;
  preparation_id: string | null;
  email_type: string;
  recipient_email: string | null;
  recipient_name: string | null;
  subject: string;
  body: string;
  status: "draft" | "approved" | "sent" | "failed";
  approval_confirmed_at: string | null;
  send_confirmed_at: string | null;
  sent_at: string | null;
  gmail_draft_id: string | null;
  gmail_message_id: string | null;
  gmail_thread_id: string | null;
  resume_version_id: string | null;
  include_resume_attachment: boolean;
  cover_letter_id: string | null;
  include_cover_letter_attachment: boolean;
  error_message: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface QAItem {
  question: string;
  answer: string;
  grounded_evidence: string[];
  confidence: string;
  missing_info: string | null;
}

export interface ApplicationQAResponse {
  job_id: string;
  preparation_id: string | null;
  resume_version_id: string | null;
  items: QAItem[];
}

export const googleIntegrationsApi = {
  getAuthUrl: () => apiClient<GoogleAuthUrlResponse>("/integrations/google/auth-url"),

  getStatus: () => apiClient<GmailConnectionStatus>("/integrations/google/status"),

  sendCallback: (code: string, state: string) =>
    apiClient<GmailConnectionStatus>("/integrations/google/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    }),

  disconnect: () =>
    apiClient<{ message: string }>("/integrations/google/disconnect", {
      method: "POST",
    }),
};

export const assistantApi = {
  getOrCreatePreparation: (
    jobId: string,
    applicationId?: string,
    resumeVersionId?: string
  ) =>
    apiClient<ApplicationPreparation>("/application-assistant/preparations", {
      method: "POST",
      body: JSON.stringify({
        job_id: jobId,
        application_id: applicationId || null,
        resume_version_id: resumeVersionId || null,
      }),
    }),

  getPreparation: (preparationId: string) =>
    apiClient<ApplicationPreparation>(
      `/application-assistant/preparations/${preparationId}`
    ),

  updateChecklistItem: (
    preparationId: string,
    itemId: string,
    completed: boolean,
    notes?: string
  ) =>
    apiClient<ApplicationPreparation>(
      `/application-assistant/preparations/${preparationId}/checklist`,
      {
        method: "PATCH",
        body: JSON.stringify({
          item_id: itemId,
          completed,
          notes: notes || null,
        }),
      }
    ),

  recordPortalOpened: (preparationId: string) =>
    apiClient<ApplicationPreparation>(
      `/application-assistant/preparations/${preparationId}/portal-opened`,
      {
        method: "POST",
      }
    ),

  confirmPortalSubmission: (data: {
    job_id: string;
    preparation_id?: string;
    application_id?: string;
    notes?: string;
  }) =>
    apiClient<ApplicationPreparation>(
      "/application-assistant/preparations/confirm-submission",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  generateCoverLetter: (data: {
    job_id: string;
    preparation_id?: string;
    resume_version_id?: string;
    user_instructions?: string;
  }) =>
    apiClient<CoverLetter>("/application-assistant/cover-letters/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getCoverLetter: (letterId: string) =>
    apiClient<CoverLetter>(`/application-assistant/cover-letters/${letterId}`),

  updateCoverLetter: (
    letterId: string,
    data: { title?: string; content?: string; is_approved?: boolean }
  ) =>
    apiClient<CoverLetter>(`/application-assistant/cover-letters/${letterId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  listCoverLettersForJob: (jobId: string) =>
    apiClient<CoverLetter[]>(`/application-assistant/jobs/${jobId}/cover-letters`),

  generateEmail: (data: {
    job_id?: string;
    application_id?: string;
    preparation_id?: string;
    resume_version_id?: string;
    cover_letter_id?: string;
    email_type: string;
    recipient_email?: string;
    recipient_name?: string;
    user_instructions?: string;
  }) =>
    apiClient<ApplicationEmail>("/application-assistant/emails/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getEmail: (emailId: string) =>
    apiClient<ApplicationEmail>(`/application-assistant/emails/${emailId}`),

  updateEmail: (
    emailId: string,
    data: {
      recipient_email?: string;
      recipient_name?: string;
      subject?: string;
      body?: string;
      include_resume_attachment?: boolean;
      resume_version_id?: string;
      include_cover_letter_attachment?: boolean;
      cover_letter_id?: string;
    }
  ) =>
    apiClient<ApplicationEmail>(`/application-assistant/emails/${emailId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  approveEmail: (emailId: string) =>
    apiClient<ApplicationEmail>(
      `/application-assistant/emails/${emailId}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ is_approved: true }),
      }
    ),

  createGmailDraft: (emailId: string) =>
    apiClient<ApplicationEmail>(
      `/application-assistant/emails/${emailId}/gmail-draft`,
      {
        method: "POST",
      }
    ),

  sendEmail: (emailId: string, confirmSend: boolean, idempotencyKey?: string) =>
    apiClient<ApplicationEmail>(`/application-assistant/emails/${emailId}/send`, {
      method: "POST",
      body: JSON.stringify({
        email_id: emailId,
        confirm_send: confirmSend,
        idempotency_key: idempotencyKey || null,
      }),
    }),

  listEmailsForJob: (jobId: string) =>
    apiClient<ApplicationEmail[]>(`/application-assistant/jobs/${jobId}/emails`),

  generateQA: (data: {
    job_id: string;
    preparation_id?: string;
    resume_version_id?: string;
    custom_questions?: string[];
  }) =>
    apiClient<ApplicationQAResponse>("/application-assistant/qa/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ============================================================================
// Interview Preparation & Coaching Interfaces & API
// ============================================================================

export interface InterviewSessionCreateRequest {
  job_id?: string;
  company_id?: string;
  application_id?: string;
  resume_version_id?: string;
  interview_round?: string;
  interview_type?: string;
  difficulty?: string;
  category?: string;
  question_count?: number;
  user_instructions?: string;
  selected_project_name?: string;
}

export interface InterviewSessionSummary {
  id: string;
  user_id: string;
  job_id?: string | null;
  job_title?: string | null;
  company_name?: string | null;
  interview_round: string;
  interview_type: string;
  difficulty: string;
  status: string;
  title: string;
  total_questions: number;
  completed_questions: number;
  average_score?: number | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface InterviewAnswerDetail {
  id: string;
  question_id: string;
  answer_text: string;
  submitted_code?: string | null;
  submitted_language?: string | null;
  word_count: number;
  time_spent_seconds?: number | null;
  submitted_at: string;
  evaluation?: InterviewEvaluationDetail | null;
}

export interface InterviewEvaluationDetail {
  id: string;
  question_id: string;
  overall_score: number;
  technical_correctness_score: number;
  relevance_score: number;
  completeness_score: number;
  clarity_score: number;
  approach_score: number;
  communication_score: number;
  strengths: string[];
  missing_points: string[];
  suggested_improvements: string[];
  stronger_answer_example?: string | null;
  evaluation_feedback?: string | null;
  evaluated_at: string;
  is_deterministic_fallback: boolean;
}

export interface InterviewQuestionDetail {
  id: string;
  session_id: string;
  question_order: number;
  category: string;
  difficulty: string;
  question_text: string;
  context_hint?: string | null;
  expected_points: string[];
  evaluation_criteria?: Record<string, any>;
  ideal_answer_outline?: string | null;
  project_name?: string | null;
  status: string;
  answer?: InterviewAnswerDetail | null;
  evaluation?: InterviewEvaluationDetail | null;
}

export interface InterviewSessionDetail {
  id: string;
  user_id: string;
  job_id?: string | null;
  company_id?: string | null;
  application_id?: string | null;
  resume_version_id?: string | null;
  title: string;
  interview_round: string;
  interview_type: string;
  difficulty: string;
  status: string;
  total_questions: number;
  completed_questions: number;
  average_score?: number | null;
  preparation_plan?: {
    technical_topics_to_revise?: { topic: string; rationale: string; suggested_focus: string[] }[];
    relevant_projects_to_explain?: { project_name: string; relevance_to_role: string; talking_points: string[] }[];
    internship_and_experience_talking_points?: string[];
    required_technical_skills?: string[];
    potential_skill_gaps?: { skill_or_requirement: string; status: string; mitigation_strategy: string }[];
    behavioral_preparation_topics?: { competency: string; prompt_theme: string; relevant_experience_anchor: string }[];
    company_and_role_context?: { company_name: string; role_title: string; workplace_type: string; key_focus_areas: string[] };
  } | null;
  questions: InterviewQuestionDetail[];
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface InterviewAnswerSubmitRequest {
  answer_text: string;
  submitted_code?: string;
  submitted_language?: string;
  time_spent_seconds?: number;
}

export interface InterviewAnswerSubmitResponse {
  answer: InterviewAnswerDetail;
  evaluation: InterviewEvaluationDetail;
  session_progress: {
    total_questions: number;
    completed_questions: number;
    average_score?: number | null;
    is_session_complete: boolean;
  };
}

export interface ProjectBreakdownResponse {
  project_name: string;
  overview_pitch: string;
  architecture_and_design: string;
  technical_implementation: string[];
  key_challenges_and_solutions: { challenge: string; solution: string }[];
  scalability_and_improvements: string[];
  candidate_contribution: string;
  practice_questions: string[];
  provider: string;
  model: string;
  is_fallback: boolean;
}

export interface InterviewNoteResponse {
  id: string;
  user_id: string;
  session_id?: string | null;
  application_id?: string | null;
  note_type: string;
  title: string;
  content: string;
  is_pinned: boolean;
  is_completed: boolean;
  checklist_items?: { id: string; text: string; done: boolean }[] | null;
  created_at: string;
  updated_at: string;
}

export interface InterviewNoteCreateRequest {
  title: string;
  content: string;
  note_type?: string;
  session_id?: string;
  application_id?: string;
  is_pinned?: boolean;
  is_completed?: boolean;
  checklist_items?: { id: string; text: string; done: boolean }[];
}

export interface InterviewNoteUpdateRequest {
  title?: string;
  content?: string;
  note_type?: string;
  is_pinned?: boolean;
  is_completed?: boolean;
  checklist_items?: { id: string; text: string; done: boolean }[];
}

export interface InterviewAnalyticsResponse {
  total_sessions_started?: number;
  total_sessions_completed?: number;
  total_sessions?: number;
  completed_sessions?: number;
  total_questions_attempted: number;
  overall_average_score: number;
  technical_average_score: number;
  behavioral_average_score: number;
  category_performance?: Record<string, number> | {
    category: string;
    questions_attempted: number;
    average_score: number;
  }[];
  difficulty_performance?: Record<string, number>;
  strong_areas: string[];
  weak_areas: string[];
  recommended_revision_topics: string[];
  score_trend?: {
    session_id: string;
    session_title: string;
    completed_at: string;
    average_score: number;
  }[];
  score_progression?: {
    session_id: string;
    title: string;
    score: number;
    date: string;
  }[];
}

export interface InterviewReminderCreateRequest {
  session_id?: string;
  application_id?: string;
  scheduled_at: string;
  reminder_type: string;
  custom_message?: string;
}

export const interviewPrepApi = {
  createSession: (data: InterviewSessionCreateRequest) =>
    apiClient<InterviewSessionDetail>("/interview-prep/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listSessions: (status?: string, limit: number = 50, offset: number = 0) => {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());
    return apiClient<InterviewSessionSummary[]>(`/interview-prep/sessions?${params.toString()}`);
  },

  getSession: (sessionId: string) =>
    apiClient<InterviewSessionDetail>(`/interview-prep/sessions/${sessionId}`),

  submitAnswer: (sessionId: string, questionId: string, data: InterviewAnswerSubmitRequest) =>
    apiClient<InterviewAnswerDetail>(
      `/interview-prep/sessions/${sessionId}/questions/${questionId}/answer`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  getProjectBreakdown: (projectName: string, jobId?: string, instructions?: string) =>
    apiClient<ProjectBreakdownResponse>("/interview-prep/project-breakdown", {
      method: "POST",
      body: JSON.stringify({
        project_name: projectName,
        job_id: jobId || null,
        user_instructions: instructions || null,
      }),
    }),

  listNotes: (noteType?: string, sessionId?: string, applicationId?: string) => {
    const params = new URLSearchParams();
    if (noteType) params.append("note_type", noteType);
    if (sessionId) params.append("session_id", sessionId);
    if (applicationId) params.append("application_id", applicationId);
    const qs = params.toString();
    return apiClient<InterviewNoteResponse[]>(`/interview-prep/notes${qs ? `?${qs}` : ""}`);
  },

  createNote: (data: InterviewNoteCreateRequest) =>
    apiClient<InterviewNoteResponse>("/interview-prep/notes", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateNote: (noteId: string, data: InterviewNoteUpdateRequest) =>
    apiClient<InterviewNoteResponse>(`/interview-prep/notes/${noteId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteNote: (noteId: string) =>
    apiClient<{ deleted: boolean; id: string }>(`/interview-prep/notes/${noteId}`, {
      method: "DELETE",
    }),

  getAnalytics: () => apiClient<InterviewAnalyticsResponse>("/interview-prep/analytics"),

  scheduleReminder: (data: InterviewReminderCreateRequest) =>
    apiClient<{ scheduled: boolean; notification_id: string; scheduled_at: string }>(
      "/interview-prep/reminders",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),
};

// ============================================================================
// Company Intelligence & Research Interfaces & API
// ============================================================================

export interface TechnologyItemSchema {
  name: string;
  category: string;
  evidence_strength: "confirmed" | "supported" | "inferred" | "unknown";
  evidence_source: string;
  context?: string | null;
}

export interface CompanyProductOrService {
  name: string;
  description: string;
  category?: string | null;
  evidence_source?: string | null;
}

export interface RecentDevelopmentItem {
  headline: string;
  summary: string;
  source_url?: string | null;
  date?: string | null;
}

export interface HiringSummarySchema {
  total_active_jobs: number;
  entry_level_jobs: number;
  internship_jobs: number;
  experienced_jobs: number;
  top_categories: Array<{ category: string; count: number }>;
  top_locations: string[];
  active_technologies: string[];
  stale_or_expired_jobs: number;
  last_job_posted_at?: string | null;
}

export interface CompanyIntelligenceResponse {
  id: string;
  company_id: string;
  company_name: string;
  overview?: string | null;
  industry_domain?: string | null;
  headquarters?: string | null;
  operating_locations: string[];
  website_url?: string | null;
  careers_url?: string | null;
  products_and_services: CompanyProductOrService[];
  technology_stack: TechnologyItemSchema[];
  size_band?: string | null;
  size_evidence?: string | null;
  funding_ownership_info?: string | null;
  recent_developments: RecentDevelopmentItem[];
  hiring_summary: HiringSummarySchema;
  last_researched_at?: string | null;
  is_stale: boolean;
  provenance_sources_count: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CompanyResearchSourceResponse {
  id: string;
  company_id: string;
  source_type: string;
  source_url: string;
  final_url?: string | null;
  title: string;
  content_snippet?: string | null;
  content_hash: string;
  retrieved_at: string;
  published_at?: string | null;
  is_verified: boolean;
  metadata_json: Record<string, unknown>;
}

export interface CompanyFitAssessmentResponse {
  company_id: string;
  company_name: string;
  fit_score: number;
  fit_level: "strong" | "moderate" | "developing";
  matching_skills: string[];
  missing_or_gap_skills: string[];
  role_alignment_summary: string;
  target_role_matches: Array<{
    job_id: string;
    title: string;
    seniority_level: string;
    location: string;
    job_status: string;
  }>;
  recommended_interview_focus: string[];
  fit_evidence: string[];
}

export interface CompanyResearchReportSection {
  key: string;
  title: string;
  content: string;
  bullet_points: string[];
}

export interface CompanyResearchReportResponse {
  id: string;
  company_id: string;
  company_name: string;
  user_id: string;
  report_title: string;
  sections: Record<string, CompanyResearchReportSection>;
  candidate_fit?: CompanyFitAssessmentResponse | null;
  source_evidence: Array<{
    source_id?: string;
    title: string;
    source_url: string;
    final_url?: string | null;
    source_type?: string;
    content_snippet?: string;
    content_hash?: string;
    is_verified?: boolean;
    retrieved_at?: string | null;
  }>;
  provider: string;
  model: string;
  is_cached: boolean;
  is_deterministic_fallback: boolean;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CompanyResearchGenerateRequest {
  force_refresh?: boolean;
  focus_areas?: string[] | null;
  resume_version_id?: string | null;
}

export const companyIntelligenceApi = {
  getIntelligence: (companyId: string, refresh = false) =>
    apiClient<CompanyIntelligenceResponse>(
      `/companies/${companyId}/intelligence${refresh ? "?refresh=true" : ""}`
    ),

  getTechnology: (companyId: string) =>
    apiClient<TechnologyItemSchema[]>(`/companies/${companyId}/technology`),

  getHiring: (companyId: string) =>
    apiClient<HiringSummarySchema>(`/companies/${companyId}/hiring`),

  getFit: (companyId: string, resumeVersionId?: string) => {
    const qs = resumeVersionId ? `?resume_version_id=${resumeVersionId}` : "";
    return apiClient<CompanyFitAssessmentResponse>(`/companies/${companyId}/fit${qs}`);
  },

  getSources: (companyId: string) =>
    apiClient<CompanyResearchSourceResponse[]>(`/companies/${companyId}/sources`),

  generateReport: (companyId: string, data: CompanyResearchGenerateRequest) =>
    apiClient<CompanyResearchReportResponse>(`/companies/${companyId}/research/generate`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listCompanyReports: (companyId: string) =>
    apiClient<CompanyResearchReportResponse[]>(`/companies/${companyId}/research/reports`),

  listAllReports: () =>
    apiClient<CompanyResearchReportResponse[]>("/company-intelligence/reports"),

  getReportDetail: (reportId: string) =>
    apiClient<CompanyResearchReportResponse>(`/company-intelligence/reports/${reportId}`),

  deleteReport: (reportId: string) =>
    apiClient<void>(`/company-intelligence/reports/${reportId}`, {
      method: "DELETE",
    }),
};

// ---------------------------------------------------------------------------
// Career Command Center Types & API (Prompt 18)
// ---------------------------------------------------------------------------

export interface CareerOverviewKPIs {
  total_discovered_jobs: number;
  active_verified_jobs: number;
  strong_job_matches: number;
  saved_opportunities: number;
  applications_in_progress: number;
  applications_submitted: number;
  interviews_scheduled: number;
  offers_received: number;
  resume_versions_created: number;
  interview_prep_sessions_completed: number;
  weekly_application_target: number;
  applications_this_week: number;
  target_progress_percentage: number;
  date_range: string;
}

export interface FunnelStageItem {
  stage_id: string;
  label: string;
  count: number;
  conversion_from_previous_percentage?: number | null;
  drop_off_count: number;
  drop_off_percentage: number;
}

export interface FunnelOutcomes {
  active: number;
  offered: number;
  rejected: number;
  withdrawn: number;
}

export interface CareerFunnelResponse {
  stages: FunnelStageItem[];
  outcomes: FunnelOutcomes;
  methodology_notes: string;
}

export interface DemonstratedSkillItem {
  skill: string;
  evidence_count: number;
  source_sections: string[];
  category?: string | null;
}

export interface RequestedSkillItem {
  skill: string;
  frequency: number;
  is_demonstrated_by_user: boolean;
}

export interface SkillGapItem {
  skill: string;
  market_demand_frequency: number;
  status: "missing_entirely" | "unevidenced_mention";
  recommendation: string;
}

export interface ProjectEvidenceItem {
  title: string;
  role_or_context: string;
  measurable_outcomes: string[];
  demonstrated_technologies: string[];
}

export interface InterviewPrepOverview {
  completed_sessions_count: number;
  evaluated_answers_count: number;
  average_overall_score?: number | null;
  rubric_averages: Record<string, number>;
  top_strengths: string[];
  areas_for_improvement: string[];
}

export interface TargetRoleAlignment {
  target_role_families: string[];
  average_match_score: number;
  alignment_tier: string;
}

export interface CareerReadinessResponse {
  readiness_score: number;
  readiness_score_formula: string;
  score_limitations: string;
  score_breakdown: Record<string, number>;
  demonstrated_skills: DemonstratedSkillItem[];
  frequently_requested_skills: RequestedSkillItem[];
  missing_or_underrepresented_skills: SkillGapItem[];
  project_and_internship_evidence: ProjectEvidenceItem[];
  interview_performance: InterviewPrepOverview;
  target_role_alignment: TargetRoleAlignment;
}

export interface NextActionItem {
  id: string;
  priority: "high" | "medium" | "low";
  action_type:
    | "prepare_interview"
    | "research_company"
    | "complete_prep"
    | "follow_up"
    | "tailor_resume"
    | "review_match"
    | "skill_gap";
  title: string;
  reason: string;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  navigation_url: string;
  metadata?: Record<string, any>;
}

export interface RecommendationsResponse {
  actions: NextActionItem[];
  total_actions: number;
}

export interface ActivityDataPoint {
  period: string;
  applications_created: number;
  applications_submitted: number;
  interviews_scheduled: number;
}

export interface CategoryCount {
  category: string;
  count: number;
  percentage: number;
}

export interface StatusCount {
  status: string;
  count: number;
  percentage: number;
}

export interface SkillFrequencyItem {
  skill: string;
  count: number;
}

export interface LocationCount {
  location: string;
  count: number;
}

export interface SavedVsAppliedComparison {
  saved_count: number;
  applied_count: number;
  ratio: number;
  insight: string;
}

export interface PerformanceAnalyticsResponse {
  date_range: string;
  weekly_activity: ActivityDataPoint[];
  monthly_activity: ActivityDataPoint[];
  applications_by_role_family: CategoryCount[];
  applications_by_company_category: CategoryCount[];
  interview_conversion_rate?: number | null;
  interview_sample_size: number;
  is_interview_sample_meaningful: boolean;
  offer_conversion_rate?: number | null;
  offer_sample_size: number;
  is_offer_sample_meaningful: boolean;
  application_status_distribution: StatusCount[];
  most_frequently_matched_skills: SkillFrequencyItem[];
  most_common_job_locations: LocationCount[];
  saved_vs_applied: SavedVsAppliedComparison;
}

export interface CareerGoalsResponse {
  target_role_families: string[];
  preferred_locations: string[];
  work_arrangement_preferences: string[];
  min_salary?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  preferred_company_categories: string[];
  priority_technical_skills: string[];
  weekly_application_target: number;
}

export interface CareerGoalsUpdate {
  target_role_families?: string[];
  preferred_locations?: string[];
  work_arrangement_preferences?: string[];
  min_salary?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  preferred_company_categories?: string[];
  priority_technical_skills?: string[];
  weekly_application_target?: number;
}

export const careerCommandCenterApi = {
  getOverview: (dateRange = "all") =>
    apiClient<CareerOverviewKPIs>(`/career-command-center/overview?date_range=${dateRange}`),

  getFunnel: () => apiClient<CareerFunnelResponse>("/career-command-center/funnel"),

  getReadiness: () => apiClient<CareerReadinessResponse>("/career-command-center/readiness"),

  getRecommendations: () =>
    apiClient<RecommendationsResponse>("/career-command-center/recommendations"),

  getAnalytics: (dateRange = "all") =>
    apiClient<PerformanceAnalyticsResponse>(
      `/career-command-center/analytics?date_range=${dateRange}`
    ),

  getGoals: () => apiClient<CareerGoalsResponse>("/career-command-center/goals"),

  updateGoals: (data: CareerGoalsUpdate) =>
    apiClient<CareerGoalsResponse>("/career-command-center/goals", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ============================================================================
// 23. LEARNING ROADMAPS & SKILL DEVELOPMENT TYPES & API (PROMPT 19)
// ============================================================================

export interface SkillItem {
  skill: string;
  category: string;
  priority_tier: "critical" | "high" | "medium" | "low";
  priority_score: number;
  market_demand_frequency: number;
  is_target_role_skill: boolean;
  is_interview_weakness: boolean;
  evidence_notes?: string | null;
}

export interface SkillGapAnalysisResponse {
  candidate_id: string;
  target_role: string;
  demonstrated_skills: SkillItem[];
  partially_demonstrated_skills: SkillItem[];
  missing_skills: SkillItem[];
  interview_weaknesses: SkillItem[];
  target_roles: string[];
  total_demonstrated: number;
  total_gaps: number;
  recommendation_summary: string;
}

export interface LearningResource {
  id: string;
  skill: string;
  title: string;
  provider: string;
  url: string;
  cost_tier: string;
  resource_type: string;
  difficulty: string;
  estimated_hours?: number | null;
  description?: string | null;
  is_verified: boolean;
  is_curated: boolean;
  is_bookmarked?: boolean;
  created_at?: string;
}

export interface PracticalExercise {
  title: string;
  instructions: string;
  estimated_minutes: number;
  completed: boolean;
}

export interface LearningMilestone {
  id: string;
  roadmap_id: string;
  title: string;
  stage: string;
  description?: string | null;
  learning_objectives: string[];
  practical_exercises: PracticalExercise[];
  status: string;
  estimated_hours: number;
  completed_hours: number;
  order_index: number;
  completion_notes?: string | null;
  completed_at?: string | null;
}

export interface RoadmapPrerequisite {
  topic: string;
  required: boolean;
  is_satisfied: boolean;
  evidence?: string | null;
}

export interface LearningRoadmap {
  id: string;
  title: string;
  target_role: string;
  description?: string | null;
  target_skills: string[];
  status: string;
  difficulty_level: string;
  total_estimated_hours: number;
  completed_hours: number;
  completion_percentage: number;
  prerequisites: RoadmapPrerequisite[];
  already_mastered_skills: string[];
  milestones: LearningMilestone[];
  created_at: string;
  updated_at?: string | null;
}

export interface LearningRoadmapSummary {
  id: string;
  title: string;
  target_role: string;
  target_skills: string[];
  status: string;
  difficulty_level: string;
  total_estimated_hours: number;
  completed_hours: number;
  completion_percentage: number;
  milestones_count: number;
  completed_milestones_count: number;
  created_at: string;
}

export interface SuggestedMilestone {
  title: string;
  description: string;
  estimated_hours: number;
}

export interface LearningProject {
  id: string;
  title: string;
  objective: string;
  summary?: string | null;
  target_skills: string[];
  functional_requirements: string[];
  tech_stack: string[];
  suggested_milestones: SuggestedMilestone[];
  expected_portfolio_outcome?: string | null;
  resume_bullet_sample?: string | null;
  status: string;
  repository_url?: string | null;
  live_demo_url?: string | null;
  architecture_overview?: string | null;
  is_portfolio_ready: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface LearningActivity {
  id: string;
  activity_type: string;
  skill?: string | null;
  duration_hours: number;
  notes?: string | null;
  logged_at: string;
}

export interface LearningAnalytics {
  total_hours_learned: number;
  weekly_hours_learned: number;
  active_roadmaps_count: number;
  completed_milestones_count: number;
  portfolio_projects_count: number;
  skills_in_progress: string[];
  hours_by_skill: Record<string, number>;
  recent_activities: LearningActivity[];
}

export const learningRoadmapsApi = {
  getSkillGaps: () =>
    apiClient<SkillGapAnalysisResponse>("/learning-roadmaps/skill-gaps"),

  getAnalytics: () =>
    apiClient<LearningAnalytics>("/learning-roadmaps/analytics"),

  listRoadmaps: (status?: string) =>
    apiClient<LearningRoadmapSummary[]>(
      `/learning-roadmaps${status ? `?status=${encodeURIComponent(status)}` : ""}`
    ),

  getRoadmap: (id: string) =>
    apiClient<LearningRoadmap>(`/learning-roadmaps/${id}`),

  createRoadmap: (data: {
    target_role: string;
    custom_skills?: string[];
    target_difficulty?: string;
    user_notes?: string;
  }) =>
    apiClient<LearningRoadmap>("/learning-roadmaps", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateRoadmapStatus: (id: string, status: string) =>
    apiClient<LearningRoadmap>(`/learning-roadmaps/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  deleteRoadmap: (id: string) =>
    apiClient<{ status: string; message: string }>(`/learning-roadmaps/${id}`, {
      method: "DELETE",
    }),

  updateMilestone: (
    id: string,
    data: {
      status?: string;
      completed_hours?: number;
      completion_notes?: string;
      practical_exercises?: PracticalExercise[];
    }
  ) =>
    apiClient<LearningMilestone>(`/learning-roadmaps/milestones/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  listResources: (params?: { skill?: string; difficulty?: string; cost_tier?: string }) => {
    const q = new URLSearchParams();
    if (params?.skill) q.set("skill", params.skill);
    if (params?.difficulty) q.set("difficulty", params.difficulty);
    if (params?.cost_tier) q.set("cost_tier", params.cost_tier);
    const qs = q.toString();
    return apiClient<LearningResource[]>(
      `/learning-roadmaps/resources/catalog${qs ? `?${qs}` : ""}`
    );
  },

  createCustomResource: (data: {
    skill: string;
    title: string;
    provider: string;
    url: string;
    cost_tier?: string;
    resource_type?: string;
    difficulty?: string;
    estimated_hours?: number;
    description?: string;
  }) =>
    apiClient<LearningResource>("/learning-roadmaps/resources/custom", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deleteCustomResource: (id: string) =>
    apiClient<{ status: string; message: string }>(
      `/learning-roadmaps/resources/custom/${id}`,
      { method: "DELETE" }
    ),

  logActivity: (data: {
    activity_type: string;
    duration_hours: number;
    skill?: string;
    notes?: string;
    milestone_id?: string;
    roadmap_id?: string;
  }) =>
    apiClient<LearningActivity>("/learning-roadmaps/activities", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listActivities: (limit = 20) =>
    apiClient<LearningActivity[]>(`/learning-roadmaps/activities?limit=${limit}`),

  getProjectRecommendations: (params?: { target_role?: string; missing_skills?: string }) => {
    const q = new URLSearchParams();
    if (params?.target_role) q.set("target_role", params.target_role);
    if (params?.missing_skills) q.set("missing_skills", params.missing_skills);
    const qs = q.toString();
    return apiClient<any[]>(
      `/learning-roadmaps/projects/recommendations${qs ? `?${qs}` : ""}`
    );
  },

  listProjects: (status?: string) =>
    apiClient<LearningProject[]>(
      `/learning-roadmaps/projects${status ? `?status=${encodeURIComponent(status)}` : ""}`
    ),

  createProject: (data: {
    title: string;
    objective: string;
    summary?: string;
    target_skills: string[];
    functional_requirements?: string[];
    tech_stack?: string[];
    suggested_milestones?: SuggestedMilestone[];
    expected_portfolio_outcome?: string;
    resume_bullet_sample?: string;
  }) =>
    apiClient<LearningProject>("/learning-roadmaps/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProject: (
    id: string,
    data: {
      status?: string;
      repository_url?: string;
      live_demo_url?: string;
      architecture_overview?: string;
      is_portfolio_ready?: boolean;
    }
  ) =>
    apiClient<LearningProject>(`/learning-roadmaps/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// ============================================================================
// 24. PORTFOLIO STUDIO & PROFESSIONAL SHOWCASE (PROMPT 20)
// ============================================================================

export interface PortfolioEducationItem {
  institution: string;
  degree: string;
  field_of_study?: string | null;
  start_year?: number | null;
  end_year?: number | null;
  highlights: string[];
}

export interface PortfolioWorkExperienceItem {
  company: string;
  role: string;
  location?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_current: boolean;
  description?: string | null;
  bullet_points: string[];
}

export interface PortfolioCertificationItem {
  name: string;
  issuer: string;
  issue_date?: string | null;
  url?: string | null;
  credential_id?: string | null;
}

export interface PortfolioAchievementItem {
  title: string;
  description: string;
  date?: string | null;
}

export interface PortfolioProfileData {
  full_name: string;
  headline: string;
  avatar_url?: string | null;
  summary: string;
  location: string;
  target_roles: string[];
  technical_skills: string[];
  contact_email?: string | null;
  phone?: string | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  website_url?: string | null;
  education: PortfolioEducationItem[];
  work_experience: PortfolioWorkExperienceItem[];
  certifications: PortfolioCertificationItem[];
  achievements: PortfolioAchievementItem[];
}

export interface PortfolioThemeConfig {
  accent_color: string;
  font_family: string;
  dark_mode: string;
  show_contact_form: boolean;
  show_view_counter: boolean;
}

export interface PortfolioSection {
  id: string;
  portfolio_id: string;
  section_type: string;
  title: string;
  is_visible: boolean;
  order_index: number;
  content_json?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface PortfolioProjectItem {
  id: string;
  portfolio_id: string;
  learning_project_id?: string | null;
  title: string;
  problem_statement?: string | null;
  description: string;
  tech_stack: string[];
  key_features: string[];
  architecture_overview?: string | null;
  candidate_contribution?: string | null;
  repository_url?: string | null;
  live_demo_url?: string | null;
  image_urls: string[];
  challenges?: string | null;
  outcomes?: string | null;
  status: string;
  is_featured: boolean;
  is_visible: boolean;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioVersionItem {
  id: string;
  version_number: number;
  change_summary?: string | null;
  created_at: string;
}

export interface PortfolioDetail {
  id: string;
  user_id: string;
  public_slug: string;
  title: string;
  headline?: string | null;
  is_published: boolean;
  published_at?: string | null;
  template_id: string;
  theme_config: PortfolioThemeConfig;
  profile_data: PortfolioProfileData;
  custom_css?: string | null;
  sections: PortfolioSection[];
  projects: PortfolioProjectItem[];
  versions_count: number;
  created_at: string;
  updated_at: string;
}

export interface PublicPortfolioDetail {
  public_slug: string;
  title: string;
  headline?: string | null;
  template_id: string;
  theme_config: PortfolioThemeConfig;
  profile_data: PortfolioProfileData;
  sections: PortfolioSection[];
  projects: PortfolioProjectItem[];
  published_at?: string | null;
}

export interface ViewTrendPoint {
  date: string;
  views: number;
}

export interface ProjectViewStat {
  project_id?: string | null;
  title: string;
  views: number;
}

export interface PortfolioAnalytics {
  total_views: number;
  project_views: number;
  downloads_count: number;
  views_by_date: ViewTrendPoint[];
  top_viewed_projects: ProjectViewStat[];
  referrers: Record<string, number>;
  devices: Record<string, number>;
}

export interface AIPortfolioAssistResult {
  suggested_content: string;
  explanation: string;
  bullet_points: string[];
  is_fallback: boolean;
  grounded_evidence: string[];
}

export const portfoliosApi = {
  getMyPortfolio: () =>
    apiClient<PortfolioDetail>("/portfolios/me"),

  updateProfile: (data: {
    title?: string;
    headline?: string;
    profile_data: PortfolioProfileData;
  }) =>
    apiClient<PortfolioDetail>("/portfolios/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  updateTheme: (data: {
    template_id?: string;
    theme_config: PortfolioThemeConfig;
    custom_css?: string;
  }) =>
    apiClient<PortfolioDetail>("/portfolios/theme", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  updateSlug: (public_slug: string) =>
    apiClient<PortfolioDetail>("/portfolios/slug", {
      method: "PUT",
      body: JSON.stringify({ public_slug }),
    }),

  reorderSections: (
    sections: { id: string; order_index: number; is_visible: boolean }[]
  ) =>
    apiClient<PortfolioSection[]>("/portfolios/sections", {
      method: "PUT",
      body: JSON.stringify({ sections }),
    }),

  updateSection: (
    sectionId: string,
    data: { title?: string; is_visible?: boolean; order_index?: number }
  ) =>
    apiClient<PortfolioSection>(`/portfolios/sections/${sectionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  createProject: (data: {
    learning_project_id?: string;
    title: string;
    problem_statement?: string;
    description: string;
    tech_stack?: string[];
    key_features?: string[];
    architecture_overview?: string;
    candidate_contribution?: string;
    repository_url?: string;
    live_demo_url?: string;
    image_urls?: string[];
    challenges?: string;
    outcomes?: string;
    status?: string;
    is_featured?: boolean;
    is_visible?: boolean;
    order_index?: number;
  }) =>
    apiClient<PortfolioProjectItem>("/portfolios/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProject: (
    projectId: string,
    data: Partial<{
      title: string;
      problem_statement: string;
      description: string;
      tech_stack: string[];
      key_features: string[];
      architecture_overview: string;
      candidate_contribution: string;
      repository_url: string;
      live_demo_url: string;
      image_urls: string[];
      challenges: string;
      outcomes: string;
      status: string;
      is_featured: boolean;
      is_visible: boolean;
      order_index: number;
    }>
  ) =>
    apiClient<PortfolioProjectItem>(`/portfolios/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteProject: (projectId: string) =>
    apiClient<{ status: string; message: string }>(
      `/portfolios/projects/${projectId}`,
      { method: "DELETE" }
    ),

  importLearningProject: (learningProjectId: string) =>
    apiClient<PortfolioProjectItem>(
      `/portfolios/projects/import-learning/${learningProjectId}`,
      { method: "POST" }
    ),

  importFromResume: () =>
    apiClient<PortfolioDetail>("/portfolios/import-resume", {
      method: "POST",
    }),

  publish: () =>
    apiClient<PortfolioDetail>("/portfolios/publish", {
      method: "POST",
    }),

  unpublish: () =>
    apiClient<PortfolioDetail>("/portfolios/unpublish", {
      method: "POST",
    }),

  createVersion: (change_summary?: string) =>
    apiClient<PortfolioVersionItem>("/portfolios/versions", {
      method: "POST",
      body: JSON.stringify({ change_summary }),
    }),

  listVersions: () =>
    apiClient<PortfolioVersionItem[]>("/portfolios/versions"),

  restoreVersion: (versionId: string) =>
    apiClient<PortfolioDetail>(`/portfolios/versions/${versionId}/restore`, {
      method: "POST",
    }),

  aiAssist: (data: {
    assist_type: string;
    current_text?: string;
    target_role?: string;
    project_title?: string;
    tech_stack?: string[];
    rough_notes?: string;
  }) =>
    apiClient<AIPortfolioAssistResult>("/portfolios/ai-assist", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getAnalytics: () =>
    apiClient<PortfolioAnalytics>("/portfolios/analytics"),

  getPublicPortfolio: (publicSlug: string) =>
    apiClient<PublicPortfolioDetail>(`/portfolios/public/${publicSlug}`),

  recordPublicEvent: (
    publicSlug: string,
    data: { event_type: string; project_id?: string; referrer?: string }
  ) =>
    apiClient<{ status: string }>(`/portfolios/public/${publicSlug}/event`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getPublicPdfUrl: (publicSlug: string) =>
    `${API_BASE}/api/v1/portfolios/public/${publicSlug}/export/pdf`,

  getPublicHtmlUrl: (publicSlug: string) =>
    `${API_BASE}/api/v1/portfolios/public/${publicSlug}/export/html`,
};

// ============================================================================
// Career Workflow & Automation Interfaces & API
// ============================================================================

export interface WorkflowRecommendedAction {
  action_type: string;
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  target_route: string;
  metadata?: Record<string, unknown>;
}

export interface CareerWorkflowStepSummary {
  id: string;
  step_number: number;
  step_name: string;
  status: string;
  input_payload?: Record<string, unknown>;
  output_payload?: Record<string, unknown>;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface CareerWorkflowRunSummary {
  id: string;
  workflow_type: string;
  status: "pending" | "running" | "paused_awaiting_input" | "completed" | "failed" | "cancelled";
  current_step?: string | null;
  progress_pct: number;
  error_message?: string | null;
  retry_count: number;
  step_data?: Record<string, unknown>;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  steps: CareerWorkflowStepSummary[];
}

export interface WorkflowDashboardData {
  profile_completion_pct: number;
  profile_missing_items: string[];
  new_opportunities_count: number;
  recommended_opportunities_count: number;
  jobs_requiring_review_count: number;
  applications_awaiting_approval_count: number;
  applications_submitted_count: number;
  incomplete_preparations_count: number;
  upcoming_interviews_count: number;
  recommended_next_actions: WorkflowRecommendedAction[];
  recent_workflow_runs: CareerWorkflowRunSummary[];
}

export interface OnboardingStartResult {
  workflow_run_id: string;
  status: string;
  extracted_roles: string[];
  extracted_skills: string[];
  extracted_experience_years?: number | null;
  extracted_education?: string | null;
  inferred_preferences: Record<string, unknown>;
  matching_jobs_count: number;
  top_matches: Array<{
    job_id: string;
    job_title: string;
    company_name: string;
    match_score: number;
  }>;
}

export interface OnboardingConfirmPayload {
  target_role_families: string[];
  preferred_locations: string[];
  work_arrangement_preferences: string[];
  min_salary?: number | null;
  salary_currency?: string;
  seniority: string;
}

export interface UnifiedOpportunityItem {
  job_id: string;
  title: string;
  company_name: string;
  company_id?: string | null;
  company_tier: string;
  location_text?: string | null;
  work_arrangement: string;
  seniority_level: string;
  is_entry_level: boolean;
  match_score?: number | null;
  match_reasons: string[];
  skill_gaps: string[];
  eligibility_concerns: string[];
  verification_status: string;
  source_provenance?: string | null;
  application_url?: string | null;
}

export interface UnifiedDiscoveryData {
  total_active_jobs: number;
  entry_level_count: number;
  priority_tier_count: number;
  opportunities: UnifiedOpportunityItem[];
}

export interface PreparationDetailData {
  preparation_id: string;
  job_id: string;
  job_title: string;
  company_name: string;
  application_id?: string | null;
  execution_status: string;
  execution_channel?: string | null;
  checklist_status: string;
  checklist_items: Array<{ item: string; done: boolean; notes?: string }>;
  job_intelligence?: {
    role_summary?: string;
    primary_responsibilities?: string[];
    must_have_skills?: string[];
    nice_to_have_skills?: string[];
    work_culture_signals?: string;
  } | null;
  compatibility_assessment?: {
    overall_score?: number;
    breakdown?: Record<string, unknown>;
    strengths?: string[];
    gaps?: string[];
  } | null;
  tailored_resume?: {
    version_id: string;
    version_number: number;
    filename?: string | null;
    is_tailored: boolean;
  } | null;
  cover_letter?: {
    id: string;
    version_number: number;
    content: string;
    is_approved: boolean;
    grounded_evidence: Array<Record<string, unknown>>;
  } | null;
  recruiter_email?: {
    id: string;
    subject: string;
    body_text: string;
    status: string;
    is_approved: boolean;
    recipient_email?: string | null;
  } | null;
  screening_qa_prep: Array<{ question: string; answer_outline: string; status: string }>;
  company_research?: {
    company_overview?: string;
    industry?: string;
    hiring_summary?: Record<string, unknown>;
    technologies_confirmed?: string[];
  } | null;
  interview_prep_starter?: {
    suggested_topics: string[];
    difficulty: string;
    mock_ready: boolean;
  } | null;
  portal_url?: string | null;
  can_apply: boolean;
}

export interface PortalOpenResult {
  portal_url: string;
  assisted_form_data: Record<string, string>;
  execution_status: string;
  opened_at: string;
}

export const careerWorkflowApi = {
  getDashboard: () =>
    apiClient<WorkflowDashboardData>("/career-workflow/dashboard"),

  startOnboarding: (resumeId?: string, preferencesOverride?: Record<string, unknown>) =>
    apiClient<OnboardingStartResult>("/career-workflow/onboarding/start", {
      method: "POST",
      body: JSON.stringify({
        resume_id: resumeId,
        preferences_override: preferencesOverride,
      }),
    }),

  confirmOnboarding: (data: OnboardingConfirmPayload) =>
    apiClient<{ status: string; message: string }>("/career-workflow/onboarding/confirm", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getDiscovery: (filterEntryLevel = true, prioritizeTiers = true, limit = 30) =>
    apiClient<UnifiedDiscoveryData>(
      `/career-workflow/discovery?filter_entry_level=${filterEntryLevel}&prioritize_tiers=${prioritizeTiers}&limit=${limit}`
    ),

  startPreparation: (jobId: string, resumeId?: string) =>
    apiClient<PreparationDetailData>("/career-workflow/preparation/start", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, resume_id: resumeId }),
    }),

  getPreparation: (jobId: string) =>
    apiClient<PreparationDetailData>(`/career-workflow/preparation/${jobId}`),

  approvePreparation: (
    jobId: string,
    channel: "official_portal" | "gmail" | "external_form",
    notes?: string
  ) =>
    apiClient<PreparationDetailData>(`/career-workflow/preparation/${jobId}/approve`, {
      method: "POST",
      body: JSON.stringify({ channel, notes }),
    }),

  openPortal: (jobId: string) =>
    apiClient<PortalOpenResult>(`/career-workflow/execution/portal-open/${jobId}`, {
      method: "POST",
    }),

  confirmPortalSubmission: (jobId: string, confirmationNotes?: string) =>
    apiClient<{ status: string; execution_status: string; message: string; confirmed_at: string }>(
      `/career-workflow/execution/portal-confirm/${jobId}`,
      {
        method: "POST",
        body: JSON.stringify({ confirmation_notes: confirmationNotes }),
      }
    ),

  executeGmail: (jobId: string, emailId: string, confirmSend = true) =>
    apiClient<{ status: string; execution_status: string; message: string; confirmed_at: string }>(
      `/career-workflow/execution/gmail-send/${jobId}`,
      {
        method: "POST",
        body: JSON.stringify({ email_id: emailId, confirm_send: confirmSend }),
      }
    ),

  withdraw: (jobId: string) =>
    apiClient<{ status: string; execution_status: string; message: string }>(
      `/career-workflow/execution/withdraw/${jobId}`,
      {
        method: "POST",
      }
    ),

  listRuns: () =>
    apiClient<CareerWorkflowRunSummary[]>("/career-workflow/runs"),

  cancelRun: (runId: string) =>
    apiClient<{ status: string; message: string }>(`/career-workflow/runs/${runId}/cancel`, {
      method: "POST",
    }),
};

// ============================================================================
// Professional Networking & Recruiter Intelligence (Prompt 22)
// ============================================================================

export interface RecruiterProfileItem {
  id: string;
  full_name: string;
  designation?: string | null;
  company_id?: string | null;
  company_name: string;
  recruitment_specialization: string;
  relevant_departments: string[];
  public_profile_url?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  associated_job_ids: string[];
  source_type: string;
  verification_status: "verified" | "unverified" | "inferred";
  is_verified: boolean;
  is_global: boolean;
  created_at: string;
  match_score?: number;
  match_reasons?: string[];
  why_recommended?: string | null;
  inferred_from?: string | null;
}

export interface RecruiterMatchExplanation {
  role_alignment_score: number;
  company_fit_score: number;
  skills_relevance_score: number;
  department_score: number;
  overall_score: number;
  match_reasons: string[];
  summary: string;
}

export interface RecruiterMatchItem {
  recruiter: RecruiterProfileItem;
  match_score: number;
  explanation: RecruiterMatchExplanation;
}

export interface RecruiterDiscoveryResponse {
  recruiters: RecruiterProfileItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface NetworkingActivityItem {
  id: string;
  relationship_id?: string | null;
  recruiter_id?: string | null;
  activity_type: string;
  title: string;
  description?: string | null;
  created_at: string;
}

export interface NetworkingContactItem {
  id: string;
  user_id: string;
  recruiter_id: string;
  company_id?: string | null;
  job_id?: string | null;
  application_id?: string | null;
  relationship_status: string;
  communication_channel: string;
  response_status: string;
  initial_contact_date?: string | null;
  last_contact_date?: string | null;
  next_follow_up_date?: string | null;
  networking_notes?: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  recruiter?: RecruiterProfileItem;
  recent_activities: NetworkingActivityItem[];
}

export interface NetworkingCRMOverview {
  saved_recruiters_count: number;
  companies_tracked_count: number;
  outreach_messages_count: number;
  pending_responses_count: number;
  follow_ups_due_count: number;
  status_distribution: Record<string, number>;
  recent_activities: NetworkingActivityItem[];
}

export interface OutreachMessageItem {
  id: string;
  user_id: string;
  recruiter_id: string;
  relationship_id?: string | null;
  job_id?: string | null;
  resume_version_id?: string | null;
  message_type: string;
  channel: string;
  tone: string;
  subject?: string | null;
  body: string;
  character_count: number;
  grounded_claims: string[];
  status: string;
  approval_confirmed_at?: string | null;
  sent_at?: string | null;
  sent_via_gmail: boolean;
  gmail_message_id?: string | null;
  created_at: string;
}

export interface FollowUpDueItem {
  relationship_id: string;
  recruiter_id: string;
  recruiter_name: string;
  company_name: string;
  relationship_status: string;
  last_contact_date?: string | null;
  next_follow_up_date?: string | null;
  days_since_last_contact: number;
  suggested_message_type: string;
  recommended_action: string;
}

export interface FollowUpDueResponse {
  total_due: number;
  items: FollowUpDueItem[];
}

export const networkingApi = {
  discoverRecruiters: (params?: {
    search?: string;
    company_id?: string;
    specialization?: string;
    verification_status?: string;
    skip?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.search) q.append("search", params.search);
    if (params?.company_id) q.append("company_id", params.company_id);
    if (params?.specialization) q.append("specialization", params.specialization);
    if (params?.verification_status) q.append("verification_status", params.verification_status);
    if (params?.skip !== undefined) q.append("skip", String(params.skip));
    if (params?.limit !== undefined) q.append("limit", String(params.limit));
    const qs = q.toString();
    return apiClient<RecruiterDiscoveryResponse>(`/networking/recruiters${qs ? `?${qs}` : ""}`);
  },

  createRecruiter: (payload: {
    full_name: string;
    designation?: string;
    company_name: string;
    company_id?: string;
    recruitment_specialization?: string;
    relevant_departments?: string[];
    public_profile_url?: string;
    contact_email?: string;
    contact_phone?: string;
    verification_status?: string;
  }) =>
    apiClient<RecruiterProfileItem>("/networking/recruiters", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getRecruiter: (id: string) => apiClient<RecruiterProfileItem>(`/networking/recruiters/${id}`),

  updateRecruiter: (
    id: string,
    payload: {
      designation?: string;
      recruitment_specialization?: string;
      relevant_departments?: string[];
      public_profile_url?: string;
      contact_email?: string;
      contact_phone?: string;
      verification_status?: string;
    }
  ) =>
    apiClient<RecruiterProfileItem>(`/networking/recruiters/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  discoverCompanyRecruiters: (companyId: string) =>
    apiClient<RecruiterProfileItem[]>(`/networking/recruiters/discover-company/${companyId}`, {
      method: "POST",
    }),

  getCRMOverview: () => apiClient<NetworkingCRMOverview>("/networking/crm/overview"),

  listCRMContacts: (params?: {
    status?: string;
    channel?: string;
    response_status?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.channel) q.append("channel", params.channel);
    if (params?.response_status) q.append("response_status", params.response_status);
    if (params?.search) q.append("search", params.search);
    if (params?.skip !== undefined) q.append("skip", String(params.skip));
    if (params?.limit !== undefined) q.append("limit", String(params.limit));
    const qs = q.toString();
    return apiClient<NetworkingContactItem[]>(`/networking/crm/contacts${qs ? `?${qs}` : ""}`);
  },

  addCRMContact: (payload: {
    recruiter_id: string;
    company_id?: string;
    job_id?: string;
    application_id?: string;
    relationship_status?: string;
    communication_channel?: string;
    next_follow_up_date?: string;
    networking_notes?: string;
    tags?: string[];
  }) =>
    apiClient<NetworkingContactItem>("/networking/crm/contacts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateCRMContact: (
    id: string,
    payload: {
      relationship_status?: string;
      communication_channel?: string;
      response_status?: string;
      next_follow_up_date?: string | null;
      networking_notes?: string;
      tags?: string[];
    }
  ) =>
    apiClient<NetworkingContactItem>(`/networking/crm/contacts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteCRMContact: (id: string) =>
    apiClient<{ status: string; message: string }>(`/networking/crm/contacts/${id}`, {
      method: "DELETE",
    }),

  generateOutreach: (payload: {
    recruiter_id: string;
    message_type: string;
    channel?: string;
    tone?: string;
    job_id?: string;
    resume_id?: string;
    custom_instructions?: string;
    enforce_linkedin_char_limit?: boolean;
  }) =>
    apiClient<OutreachMessageItem>("/networking/outreach/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  approveOutreach: (
    messageId: string,
    payload: {
      edited_subject?: string;
      edited_body: string;
    }
  ) =>
    apiClient<OutreachMessageItem>(`/networking/outreach/messages/${messageId}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  sendGmailOutreach: (
    messageId: string,
    payload: {
      confirm_send: boolean;
      attach_resume?: boolean;
    }
  ) =>
    apiClient<{
      status: string;
      gmail_message_id: string;
      sent_at: string;
      message: string;
    }>(`/networking/outreach/messages/${messageId}/send-gmail`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDueFollowups: () => apiClient<FollowUpDueResponse>("/networking/follow-ups/due"),
};

// ---------------------------------------------------------------------------
// Advanced AI Agent Orchestration & Copilot Interfaces
// ---------------------------------------------------------------------------

export interface AgentTraceStep {
  agent_name: string;
  operation: string;
  status: string;
  latency_ms: number;
  reasoning_summary: string;
  output_summary: Record<string, unknown>;
}

export interface ActionProposal {
  id: string;
  action_type: string;
  title: string;
  description: string;
  target_id?: string | null;
  target_type?: string | null;
  deep_link?: string | null;
  requires_approval: boolean;
  payload?: Record<string, unknown> | null;
}

export interface CopilotMessageItem {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string | null;
  agent_trace: AgentTraceStep[];
  action_proposals: ActionProposal[];
  token_usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    provider?: string;
    model?: string;
  } | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface CopilotSessionItem {
  id: string;
  title: string;
  session_type: string;
  is_active: boolean;
  message_count: number;
  context_summary?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CopilotSessionDetail {
  id: string;
  title: string;
  session_type: string;
  is_active: boolean;
  context_summary?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  messages: CopilotMessageItem[];
}

export interface AgentExecutionRecordItem {
  id: string;
  workflow_id: string;
  session_id?: string | null;
  agent_name: string;
  operation: string;
  status: string;
  latency_ms: number;
  tokens_used: number;
  provider: string;
  reasoning_summary?: string | null;
  requires_approval: boolean;
  approval_state?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  created_at: string;
}

export interface ApprovalActionResponse {
  record_id: string;
  status: string;
  approval_state: string;
  message: string;
}

export interface CandidateContextPreview {
  full_name: string;
  target_roles: string[];
  verified_skills: string[];
  career_readiness_score: number;
  active_applications_count: number;
  interviews_scheduled_count: number;
  portfolio_published: boolean;
  target_job_title?: string | null;
  target_company_name?: string | null;
}

export const copilotApi = {
  listSessions: (limit: number = 20) =>
    apiClient<CopilotSessionItem[]>(`/copilot/sessions?limit=${limit}`),

  createSession: (payload: { title?: string; session_type?: string }) =>
    apiClient<CopilotSessionItem>("/copilot/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string) =>
    apiClient<CopilotSessionDetail>(`/copilot/sessions/${sessionId}`),

  deleteSession: (sessionId: string) =>
    apiClient<{ status: string; id: string }>(`/copilot/sessions/${sessionId}`, {
      method: "DELETE",
    }),

  postMessage: (
    sessionId: string,
    payload: { content: string; target_job_id?: string; target_company_id?: string }
  ) =>
    apiClient<CopilotMessageItem>(`/copilot/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  executeQuickAction: (payload: {
    action: string;
    target_id?: string;
    parameters?: Record<string, unknown>;
  }) =>
    apiClient<CopilotMessageItem>("/copilot/actions/quick", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getWorkflowExecutions: (workflowId: string) =>
    apiClient<AgentExecutionRecordItem[]>(`/copilot/executions/${workflowId}`),

  handleApproval: (recordId: string, payload: { action: string; notes?: string }) =>
    apiClient<ApprovalActionResponse>(`/copilot/executions/${recordId}/approval`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getContextPreview: (targetJobId?: string, targetCompanyId?: string) => {
    const params = new URLSearchParams();
    if (targetJobId) params.append("target_job_id", targetJobId);
    if (targetCompanyId) params.append("target_company_id", targetCompanyId);
    const query = params.toString();
    return apiClient<CandidateContextPreview>(`/copilot/context${query ? `?${query}` : ""}`);
  },
};

// ---------------------------------------------------------------------------
// Production Integrations, Diagnostics & AI Usage Monitoring
// ---------------------------------------------------------------------------

export interface IntegrationServiceHealth {
  status: "connected" | "degraded" | "unconfigured" | "disconnected" | "error" | "operational" | string;
  service: string;
  is_configured?: boolean;
  provider?: string;
  model?: string;
  latency_ms?: number;
  message?: string;
  pool_size?: number;
  max_overflow?: number;
  active_connections?: number;
  connected_workers?: number;
  worker_names?: string[];
  broker_transport?: string;
  email?: string | null;
  scopes?: string[];
  is_client_configured?: boolean;
  is_connected?: boolean;
  connected_at?: string | null;
  last_used_at?: string | null;
}

export interface JobSourceAdapterInfo {
  name: string;
  type: string;
  auth_required: boolean;
  status: string;
  endpoint_pattern: string;
  rate_limit_policy: string;
  normalization: string;
  deduplication: string;
}

export interface IntegrationsHealthOverview {
  timestamp: string;
  environment: string;
  openai: IntegrationServiceHealth;
  gemini: IntegrationServiceHealth;
  postgres: IntegrationServiceHealth;
  redis: IntegrationServiceHealth;
  celery: IntegrationServiceHealth;
  gmail: IntegrationServiceHealth;
  job_sources: Record<string, JobSourceAdapterInfo>;
}

export interface AIUsageBreakdownItem {
  requests_count: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface AIUsageLogEntry {
  id: string;
  user_id?: string | null;
  provider: string;
  model: string;
  feature: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  request_status: string;
  latency_ms: number;
  cache_hit: boolean;
  created_at: string;
}

export interface AIUsageSummaryData {
  total_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
  daily_budget_usd: number;
  monthly_budget_usd: number;
  daily_spend_usd: number;
  monthly_spend_usd: number;
  daily_budget_percent: number;
  monthly_budget_percent: number;
  by_provider: Record<string, AIUsageBreakdownItem>;
  by_model: Record<string, AIUsageBreakdownItem>;
  by_feature: Record<string, AIUsageBreakdownItem>;
  recent_logs: AIUsageLogEntry[];
  disclaimer: string;
}

export interface JobSourcesResponse {
  timestamp: string;
  adapters: Record<string, JobSourceAdapterInfo>;
  compliance_notes: string;
}

export const integrationsApi = {
  getHealth: () => apiClient<IntegrationsHealthOverview>("/integrations/health"),
  testService: (service: string) =>
    apiClient<IntegrationServiceHealth>(`/integrations/test/${service}`, {
      method: "POST",
    }),
  getAIUsage: () => apiClient<AIUsageSummaryData>("/integrations/ai-usage"),
  getJobSources: () => apiClient<JobSourcesResponse>("/integrations/job-sources"),
};

