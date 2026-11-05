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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

