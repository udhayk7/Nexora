"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Briefcase,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  ExternalLink,
  Filter,
  HelpCircle,
  Loader2,
  Mail,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  FollowUpDueItem,
  networkingApi,
  NetworkingActivityItem,
  NetworkingContactItem,
  NetworkingCRMOverview,
  OutreachMessageItem,
  RecruiterProfileItem,
} from "@/lib/api";

const MESSAGE_TYPES = [
  { id: "linkedin_connection", label: "LinkedIn Connection Note", desc: "Strictly ≤ 300 characters", channel: "linkedin" },
  { id: "recruiter_intro", label: "Recruiter Introduction", desc: "General outreach to talent team", channel: "email" },
  { id: "job_inquiry", label: "Specific Job Inquiry", desc: "Targeted to an active opening", channel: "email" },
  { id: "internship_inquiry", label: "Internship Inquiry", desc: "For university / entry candidates", channel: "email" },
  { id: "follow_up", label: "Polite Follow-up", desc: "Re-engage past inquiries (>5 days)", channel: "email" },
  { id: "interview_thank_you", label: "Interview Thank You", desc: "Post-interview appreciation note", channel: "email" },
  { id: "networking_email", label: "Professional Networking Email", desc: "Connecting with industry peers", channel: "email" },
];

const CRM_STATUSES = [
  { id: "all", label: "All Contacts" },
  { id: "saved", label: "Saved" },
  { id: "outreach_prepared", label: "Prepared" },
  { id: "contacted", label: "Contacted" },
  { id: "awaiting_response", label: "Awaiting Response" },
  { id: "responded", label: "Responded" },
  { id: "follow_up_required", label: "Follow-up Required" },
  { id: "connected", label: "Connected" },
  { id: "archived", label: "Archived" },
];

export default function NetworkingPage() {
  const { user, isLoading: authLoading } = useAuth();

  // Active Main Tab
  const [activeTab, setActiveTab] = useState<"discovery" | "crm" | "outreach" | "timeline">("discovery");

  // CRM Overview Data
  const [crmOverview, setCrmOverview] = useState<NetworkingCRMOverview | null>(null);
  const [dueFollowups, setDueFollowups] = useState<FollowUpDueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  // Tab 1: Discovery State
  const [recruiters, setRecruiters] = useState<RecruiterProfileItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [specializationFilter, setSpecializationFilter] = useState("");
  const [verificationFilter, setVerificationFilter] = useState("");
  const [discoveryLoading, setDiscoveryLoading] = useState(false);

  // Tab 2: CRM Contacts State
  const [crmContacts, setCrmContacts] = useState<NetworkingContactItem[]>([]);
  const [crmStatusFilter, setCrmStatusFilter] = useState("all");
  const [crmLoading, setCrmLoading] = useState(false);
  const [selectedContactForNotes, setSelectedContactForNotes] = useState<NetworkingContactItem | null>(null);
  const [editNotesText, setEditNotesText] = useState("");

  // Tab 3: Outreach Studio State
  const [selectedRecruiterForOutreach, setSelectedRecruiterForOutreach] = useState<RecruiterProfileItem | null>(null);
  const [selectedMessageType, setSelectedMessageType] = useState("linkedin_connection");
  const [selectedChannel, setSelectedChannel] = useState("linkedin");
  const [selectedTone, setSelectedTone] = useState("professional");
  const [customInstructions, setCustomInstructions] = useState("");
  const [outreachDraft, setOutreachDraft] = useState<OutreachMessageItem | null>(null);
  const [generatingOutreach, setGeneratingOutreach] = useState(false);
  const [editedSubject, setEditedSubject] = useState("");
  const [editedBody, setEditedBody] = useState("");
  const [approvingOutreach, setApprovingOutreach] = useState(false);
  const [copiedNote, setCopiedNote] = useState(false);

  // Gmail Send Modal State
  const [showGmailModal, setShowGmailModal] = useState(false);
  const [confirmSendChecked, setConfirmSendChecked] = useState(false);
  const [attachResumeChecked, setAttachResumeChecked] = useState(true);
  const [sendingGmail, setSendingGmail] = useState(false);

  // Add Recruiter Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [addFullName, setAddFullName] = useState("");
  const [addDesignation, setAddDesignation] = useState("");
  const [addCompanyName, setAddCompanyName] = useState("");
  const [addSpecialization, setAddSpecialization] = useState("Technical Recruitment");
  const [addDepartments, setAddDepartments] = useState("Engineering, Product");
  const [addProfileUrl, setAddProfileUrl] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addPhone, setAddPhone] = useState("");
  const [addVerificationStatus, setAddVerificationStatus] = useState("unverified");
  const [addingRecruiter, setAddingRecruiter] = useState(false);

  const showToast = (type: "success" | "error" | "info", text: string) => {
    setToastMessage({ type, text });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  // Load Primary Data
  const loadOverviewAndFollowups = useCallback(async () => {
    try {
      const [overviewData, followupsData] = await Promise.all([
        networkingApi.getCRMOverview(),
        networkingApi.getDueFollowups(),
      ]);
      setCrmOverview(overviewData);
      setDueFollowups(followupsData.items || []);
    } catch (err: unknown) {
      console.error("Failed to load networking overview", err);
    }
  }, []);

  const loadDiscovery = useCallback(async () => {
    setDiscoveryLoading(true);
    try {
      const res = await networkingApi.discoverRecruiters({
        search: searchQuery || undefined,
        specialization: specializationFilter || undefined,
        verification_status: verificationFilter || undefined,
        limit: 30,
      });
      setRecruiters(res.recruiters || []);
    } catch (err: unknown) {
      console.error("Failed to discover recruiters", err);
      showToast("error", "Failed to load recruiters.");
    } finally {
      setDiscoveryLoading(false);
    }
  }, [searchQuery, specializationFilter, verificationFilter]);

  const loadCrmContacts = useCallback(async () => {
    setCrmLoading(true);
    try {
      const res = await networkingApi.listCRMContacts({
        status: crmStatusFilter === "all" ? undefined : crmStatusFilter,
        limit: 50,
      });
      setCrmContacts(res || []);
    } catch (err: unknown) {
      console.error("Failed to list CRM contacts", err);
      showToast("error", "Failed to load CRM contacts.");
    } finally {
      setCrmLoading(false);
    }
  }, [crmStatusFilter]);

  useEffect(() => {
    if (!authLoading && user) {
      setLoading(true);
      Promise.all([loadOverviewAndFollowups(), loadDiscovery(), loadCrmContacts()]).finally(() => {
        setLoading(false);
      });
    }
  }, [authLoading, user, loadOverviewAndFollowups, loadDiscovery, loadCrmContacts]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadOverviewAndFollowups(), loadDiscovery(), loadCrmContacts()]);
    setRefreshing(false);
    showToast("info", "Networking data refreshed.");
  };

  // Add to CRM action
  const handleSaveToCRM = async (recruiter: RecruiterProfileItem) => {
    try {
      await networkingApi.addCRMContact({
        recruiter_id: recruiter.id,
        relationship_status: "saved",
        networking_notes: `Saved from Recruiter Intelligence directory (${recruiter.company_name})`,
      });
      showToast("success", `Saved ${recruiter.full_name} to your Networking CRM.`);
      loadOverviewAndFollowups();
      loadCrmContacts();
    } catch (err: unknown) {
      showToast("error", "Failed to save recruiter to CRM.");
    }
  };

  // Select Recruiter for Outreach
  const handleStartOutreach = (recruiter: RecruiterProfileItem) => {
    setSelectedRecruiterForOutreach(recruiter);
    setActiveTab("outreach");
    setOutreachDraft(null);
  };

  // Generate Outreach Draft
  const handleGenerateOutreach = async () => {
    if (!selectedRecruiterForOutreach) {
      showToast("error", "Please select a recruiter first.");
      return;
    }
    setGeneratingOutreach(true);
    try {
      const res = await networkingApi.generateOutreach({
        recruiter_id: selectedRecruiterForOutreach.id,
        message_type: selectedMessageType,
        channel: selectedChannel,
        tone: selectedTone,
        custom_instructions: customInstructions || undefined,
        enforce_linkedin_char_limit: selectedMessageType === "linkedin_connection",
      });
      setOutreachDraft(res);
      setEditedSubject(res.subject || "");
      setEditedBody(res.body);
      showToast("success", "Outreach draft generated successfully.");
      loadOverviewAndFollowups();
    } catch (err: unknown) {
      showToast("error", "Failed to generate outreach message.");
    } finally {
      setGeneratingOutreach(false);
    }
  };

  // Approve Outreach Draft
  const handleApproveOutreach = async () => {
    if (!outreachDraft) return;
    setApprovingOutreach(true);
    try {
      const res = await networkingApi.approveOutreach(outreachDraft.id, {
        edited_subject: editedSubject || undefined,
        edited_body: editedBody,
      });
      setOutreachDraft(res);
      showToast("success", "Outreach message approved! You may now dispatch or copy.");
      loadOverviewAndFollowups();
      loadCrmContacts();
    } catch (err: unknown) {
      showToast("error", "Failed to approve outreach draft.");
    } finally {
      setApprovingOutreach(false);
    }
  };

  // Copy Note to Clipboard
  const handleCopyNote = () => {
    if (!editedBody) return;
    navigator.clipboard.writeText(editedBody);
    setCopiedNote(true);
    setTimeout(() => setCopiedNote(false), 2500);
    showToast("success", "Copied outreach note to clipboard!");
  };

  // Dispatch via Gmail
  const handleSendGmail = async () => {
    if (!outreachDraft) return;
    if (!confirmSendChecked) {
      showToast("error", "Please explicitly check the confirmation box.");
      return;
    }
    setSendingGmail(true);
    try {
      const res = await networkingApi.sendGmailOutreach(outreachDraft.id, {
        confirm_send: true,
        attach_resume: attachResumeChecked,
      });
      showToast("success", res.message || "Email successfully sent via Gmail!");
      setShowGmailModal(false);
      setConfirmSendChecked(false);
      loadOverviewAndFollowups();
      loadCrmContacts();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send email via Gmail.";
      showToast("error", msg);
    } finally {
      setSendingGmail(false);
    }
  };

  // Add Recruiter Submission
  const handleAddRecruiterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addFullName.trim() || !addCompanyName.trim()) {
      showToast("error", "Name and Company Name are required.");
      return;
    }
    setAddingRecruiter(true);
    try {
      const depts = addDepartments
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await networkingApi.createRecruiter({
        full_name: addFullName.trim(),
        designation: addDesignation.trim() || undefined,
        company_name: addCompanyName.trim(),
        recruitment_specialization: addSpecialization.trim() || undefined,
        relevant_departments: depts,
        public_profile_url: addProfileUrl.trim() || undefined,
        contact_email: addEmail.trim() || undefined,
        contact_phone: addPhone.trim() || undefined,
        verification_status: addVerificationStatus,
      });
      showToast("success", `Added ${addFullName} to Recruiter Intelligence.`);
      setShowAddModal(false);
      // Reset form
      setAddFullName("");
      setAddDesignation("");
      setAddCompanyName("");
      setAddProfileUrl("");
      setAddEmail("");
      setAddPhone("");
      loadDiscovery();
      loadOverviewAndFollowups();
    } catch (err: unknown) {
      showToast("error", "Failed to add recruiter profile.");
    } finally {
      setAddingRecruiter(false);
    }
  };

  // Update CRM status
  const handleUpdateContactStatus = async (contactId: string, newStatus: string) => {
    try {
      await networkingApi.updateCRMContact(contactId, {
        relationship_status: newStatus,
      });
      showToast("success", `Relationship updated to ${newStatus}.`);
      loadCrmContacts();
      loadOverviewAndFollowups();
    } catch (err: unknown) {
      showToast("error", "Failed to update contact status.");
    }
  };

  // Save notes modal
  const handleSaveNotes = async () => {
    if (!selectedContactForNotes) return;
    try {
      await networkingApi.updateCRMContact(selectedContactForNotes.id, {
        networking_notes: editNotesText,
      });
      showToast("success", "Networking notes saved.");
      setSelectedContactForNotes(null);
      loadCrmContacts();
    } catch (err: unknown) {
      showToast("error", "Failed to save notes.");
    }
  };

  // Delete CRM Contact
  const handleDeleteContact = async (contactId: string) => {
    if (!confirm("Are you sure you want to remove this contact from your CRM?")) return;
    try {
      await networkingApi.deleteCRMContact(contactId);
      showToast("info", "Contact removed from CRM.");
      loadCrmContacts();
      loadOverviewAndFollowups();
    } catch (err: unknown) {
      showToast("error", "Failed to remove contact.");
    }
  };

  if (authLoading || loading) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center p-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
        <p className="text-sm text-muted-foreground">Loading Recruiter Intelligence & Networking CRM...</p>
      </main>
    );
  }

  const charCount = editedBody.length;
  const isLinkedIn = selectedMessageType === "linkedin_connection";
  const isOverLimit = isLinkedIn && charCount > 300;

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg border text-sm animate-in fade-in slide-in-from-top-2 ${
            toastMessage.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
              : toastMessage.type === "error"
              ? "bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400"
              : "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400"
          }`}
        >
          {toastMessage.type === "success" && <CheckCircle2 className="w-4 h-4 shrink-0" />}
          {toastMessage.type === "error" && <AlertCircle className="w-4 h-4 shrink-0" />}
          {toastMessage.type === "info" && <HelpCircle className="w-4 h-4 shrink-0" />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border mb-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 mb-2">
            <Users className="w-3.5 h-3.5" /> Professional Networking & Recruiter Intelligence
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Recruiter Discovery & Networking CRM</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Discover verified tech recruiters, cultivate relationships, and craft AI outreach grounded in verified resume facts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> Add Recruiter
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-primary" : "text-muted-foreground"}`} />
            Refresh
          </button>
        </div>
      </header>

      {/* Follow-up Intelligence Banner (when contacts are overdue) */}
      {dueFollowups.length > 0 && (
        <section className="mb-6 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                Follow-up Due: {dueFollowups.length} Outreach Relationship{dueFollowups.length > 1 ? "s" : ""}
              </h3>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-0.5">
                Nexora detected contacts waiting for follow-up without response (&gt;5 days or scheduled follow-up passed).
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {dueFollowups.slice(0, 3).map((item) => (
                  <div
                    key={item.relationship_id}
                    className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-background/80 border border-amber-500/20 text-xs text-foreground shadow-xs"
                  >
                    <span className="font-semibold">{item.recruiter_name}</span>
                    <span className="text-muted-foreground">({item.company_name})</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-700 dark:text-amber-300 font-medium">
                      {item.days_since_last_contact}d ago
                    </span>
                    <button
                      onClick={() => {
                        const rec = recruiters.find((r) => r.id === item.recruiter_id);
                        if (rec) {
                          handleStartOutreach(rec);
                          setSelectedMessageType("follow_up");
                        } else {
                          setActiveTab("crm");
                        }
                      }}
                      className="ml-1 text-primary hover:underline font-medium inline-flex items-center gap-0.5"
                    >
                      Follow Up <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Overview KPI Cards */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-muted-foreground">Saved Recruiters</span>
            <Users className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          </div>
          <p className="text-2xl font-bold tracking-tight">{crmOverview?.saved_recruiters_count || 0}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-muted-foreground">Companies Tracked</span>
            <Building2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p className="text-2xl font-bold tracking-tight">{crmOverview?.companies_tracked_count || 0}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-muted-foreground">Outreach Messages</span>
            <Send className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <p className="text-2xl font-bold tracking-tight">{crmOverview?.outreach_messages_count || 0}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-muted-foreground">Pending Responses</span>
            <MessageSquare className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <p className="text-2xl font-bold tracking-tight">{crmOverview?.pending_responses_count || 0}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-muted-foreground">Follow-ups Due</span>
            <Clock className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          </div>
          <p className="text-2xl font-bold tracking-tight">{crmOverview?.follow_ups_due_count || 0}</p>
        </div>
      </section>

      {/* Main Workspace Tabs */}
      <div className="flex items-center gap-2 border-b border-border mb-6">
        <button
          onClick={() => setActiveTab("discovery")}
          className={`pb-3 px-3 text-sm font-medium border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "discovery"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Search className="w-4 h-4" /> Recruiter Discovery
        </button>
        <button
          onClick={() => setActiveTab("crm")}
          className={`pb-3 px-3 text-sm font-medium border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "crm"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCheck className="w-4 h-4" /> Networking CRM ({crmContacts.length})
        </button>
        <button
          onClick={() => setActiveTab("outreach")}
          className={`pb-3 px-3 text-sm font-medium border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "outreach"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sparkles className="w-4 h-4" /> AI Outreach Studio
        </button>
        <button
          onClick={() => setActiveTab("timeline")}
          className={`pb-3 px-3 text-sm font-medium border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "timeline"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Calendar className="w-4 h-4" /> Activity Timeline
        </button>
      </div>

      {/* TAB 1: RECRUITER DISCOVERY */}
      {activeTab === "discovery" && (
        <section className="space-y-6">
          {/* Search & Filters */}
          <div className="p-4 rounded-xl border border-border bg-card flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search recruiters by name, company, specialization, or role..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadDiscovery()}
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={specializationFilter}
                onChange={(e) => {
                  setSpecializationFilter(e.target.value);
                  loadDiscovery();
                }}
                className="px-3 py-2 text-sm rounded-lg border border-border bg-background"
              >
                <option value="">All Specializations</option>
                <option value="Technical Recruitment">Technical Recruitment</option>
                <option value="Campus & University Recruitment">Campus & University</option>
                <option value="Leadership & Executive Hiring">Leadership & Executive</option>
                <option value="Full-Cycle Recruitment">Full-Cycle Recruitment</option>
              </select>

              <select
                value={verificationFilter}
                onChange={(e) => {
                  setVerificationFilter(e.target.value);
                  loadDiscovery();
                }}
                className="px-3 py-2 text-sm rounded-lg border border-border bg-background"
              >
                <option value="">All Verification</option>
                <option value="verified">Verified Only</option>
                <option value="inferred">Inferred Only</option>
                <option value="unverified">Unverified</option>
              </select>

              <button
                onClick={loadDiscovery}
                className="px-3.5 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Search
              </button>
            </div>
          </div>

          {/* Recruiter Cards Grid */}
          {discoveryLoading ? (
            <div className="py-12 text-center">
              <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">Discovering recruiters and computing match scores...</p>
            </div>
          ) : recruiters.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-border">
              <Users className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <h3 className="text-sm font-semibold">No recruiters found</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Try adjusting your search criteria or manually add a recruiter using the button above.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recruiters.map((rec) => {
                const matchScore = rec.match_score || 75;
                const isSaved = crmContacts.some((c) => c.recruiter_id === rec.id);

                return (
                  <div
                    key={rec.id}
                    className="p-5 rounded-xl border border-border bg-card hover:border-primary/40 transition-all flex flex-col justify-between shadow-xs"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <h3 className="text-base font-semibold text-foreground">{rec.full_name}</h3>
                          <p className="text-xs text-muted-foreground">{rec.designation || "Recruiter"}</p>
                        </div>

                        {/* Match Score Badge */}
                        <div
                          className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                            matchScore >= 85
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                              : matchScore >= 70
                              ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
                              : "bg-secondary text-muted-foreground"
                          }`}
                        >
                          {Math.round(matchScore)}% Match
                        </div>
                      </div>

                      <div className="flex items-center gap-2 mb-3">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-secondary text-foreground">
                          <Building2 className="w-3 h-3 text-muted-foreground" />
                          {rec.company_name}
                        </span>

                        {/* Verification Status */}
                        {rec.verification_status === "verified" ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                            <ShieldCheck className="w-3.5 h-3.5" /> Verified
                          </span>
                        ) : rec.verification_status === "inferred" ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                            <HelpCircle className="w-3.5 h-3.5" /> Inferred
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                            <AlertCircle className="w-3.5 h-3.5" /> Unverified
                          </span>
                        )}
                      </div>

                      {/* Why Recommended / Match Reasons */}
                      {rec.match_reasons && rec.match_reasons.length > 0 && (
                        <div className="mb-3 space-y-1">
                          <p className="text-[11px] font-medium text-muted-foreground">Why Recommended:</p>
                          <div className="flex flex-wrap gap-1">
                            {rec.match_reasons.slice(0, 2).map((reason, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded text-[11px] bg-secondary/80 text-foreground border border-border"
                              >
                                {reason}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Specialization & Departments */}
                      <div className="text-xs text-muted-foreground space-y-1 mb-4">
                        <p>
                          <span className="font-medium text-foreground">Focus:</span>{" "}
                          {rec.recruitment_specialization || "General Tech"}
                        </p>
                        {rec.relevant_departments && rec.relevant_departments.length > 0 && (
                          <p>
                            <span className="font-medium text-foreground">Teams:</span>{" "}
                            {rec.relevant_departments.slice(0, 3).join(", ")}
                          </p>
                        )}
                        {rec.contact_email ? (
                          <p className="text-emerald-600 dark:text-emerald-400 truncate">
                            <span className="font-medium">Email:</span> {rec.contact_email}
                          </p>
                        ) : (
                          <p className="text-muted-foreground text-[11px] italic">
                            No public email available (Inferred from company directory)
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-3 border-t border-border flex items-center justify-between gap-2">
                      {rec.public_profile_url && (
                        <a
                          href={rec.public_profile_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                        >
                          Profile <ExternalLink className="w-3 h-3" />
                        </a>
                      )}

                      <div className="flex items-center gap-2 ml-auto">
                        <button
                          onClick={() => handleSaveToCRM(rec)}
                          disabled={isSaved}
                          className={`px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                            isSaved
                              ? "bg-secondary text-muted-foreground cursor-default"
                              : "border border-border bg-background hover:bg-secondary text-foreground"
                          }`}
                        >
                          {isSaved ? "Saved in CRM" : "Save to CRM"}
                        </button>
                        <button
                          onClick={() => handleStartOutreach(rec)}
                          className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center gap-1"
                        >
                          <Sparkles className="w-3 h-3" /> Draft Outreach
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB 2: NETWORKING CRM */}
      {activeTab === "crm" && (
        <section className="space-y-6">
          {/* Status Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-border">
            {CRM_STATUSES.map((st) => (
              <button
                key={st.id}
                onClick={() => setCrmStatusFilter(st.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  crmStatusFilter === st.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-secondary/60 text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          {/* CRM Contacts List */}
          {crmLoading ? (
            <div className="py-12 text-center">
              <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">Loading CRM relationships...</p>
            </div>
          ) : crmContacts.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-border">
              <UserCheck className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <h3 className="text-sm font-semibold">No contacts in this view</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Save recruiters from the Discovery tab or add contacts manually to build your networking pipeline.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {crmContacts.map((contact) => {
                const rec = contact.recruiter;
                return (
                  <div
                    key={contact.id}
                    className="p-4 rounded-xl border border-border bg-card flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-sm font-semibold text-foreground">
                          {rec ? rec.full_name : "Recruiter"}
                        </h4>
                        <span className="text-xs text-muted-foreground">
                          at {rec ? rec.company_name : "Company"}
                        </span>
                        {rec?.verification_status === "verified" && (
                          <span title="Verified Recruiter">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mt-1">
                        <span>
                          Channel: <strong className="text-foreground capitalize">{contact.communication_channel || "LinkedIn"}</strong>
                        </span>
                        <span>•</span>
                        <span>
                          Response: <strong className="text-foreground capitalize">{contact.response_status || "Pending"}</strong>
                        </span>
                        {contact.last_contact_date && (
                          <>
                            <span>•</span>
                            <span>
                              Last Contact: {new Date(contact.last_contact_date).toLocaleDateString()}
                            </span>
                          </>
                        )}
                        {contact.next_follow_up_date && (
                          <>
                            <span>•</span>
                            <span className="text-amber-600 dark:text-amber-400 font-medium">
                              Follow-up: {new Date(contact.next_follow_up_date).toLocaleDateString()}
                            </span>
                          </>
                        )}
                      </div>

                      {contact.networking_notes && (
                        <p className="text-xs text-foreground/80 bg-secondary/50 p-2 rounded-md mt-2 italic">
                          &ldquo;{contact.networking_notes}&rdquo;
                        </p>
                      )}
                    </div>

                    {/* Status Changer & Quick Actions */}
                    <div className="flex flex-wrap items-center gap-2 shrink-0">
                      <select
                        value={contact.relationship_status}
                        onChange={(e) => handleUpdateContactStatus(contact.id, e.target.value)}
                        className="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-background"
                      >
                        <option value="saved">Saved</option>
                        <option value="outreach_prepared">Outreach Prepared</option>
                        <option value="contacted">Contacted</option>
                        <option value="awaiting_response">Awaiting Response</option>
                        <option value="responded">Responded</option>
                        <option value="follow_up_required">Follow-up Required</option>
                        <option value="connected">Connected</option>
                        <option value="archived">Archived</option>
                      </select>

                      <button
                        onClick={() => {
                          setSelectedContactForNotes(contact);
                          setEditNotesText(contact.networking_notes || "");
                        }}
                        className="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary text-foreground"
                      >
                        Notes
                      </button>

                      {rec && (
                        <button
                          onClick={() => handleStartOutreach(rec)}
                          className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center gap-1"
                        >
                          <Sparkles className="w-3 h-3" /> Draft
                        </button>
                      )}

                      <button
                        onClick={() => handleDeleteContact(contact.id)}
                        className="p-1.5 text-muted-foreground hover:text-destructive transition-colors rounded-lg hover:bg-secondary"
                        title="Remove contact"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB 3: AI OUTREACH STUDIO */}
      {activeTab === "outreach" && (
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Form: Generator Settings */}
          <div className="lg:col-span-5 p-5 rounded-xl border border-border bg-card space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border">
              <Sparkles className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold">Configure Outreach Message</h2>
            </div>

            {/* Recruiter Selector */}
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Target Recruiter</label>
              <select
                value={selectedRecruiterForOutreach?.id || ""}
                onChange={(e) => {
                  const rec = recruiters.find((r) => r.id === e.target.value);
                  setSelectedRecruiterForOutreach(rec || null);
                }}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
              >
                <option value="">Select a recruiter...</option>
                {recruiters.map((rec) => (
                  <option key={rec.id} value={rec.id}>
                    {rec.full_name} ({rec.company_name} – {rec.designation || "Recruiter"})
                  </option>
                ))}
              </select>
            </div>

            {/* Message Type Selector */}
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Message Type</label>
              <div className="space-y-1.5">
                {MESSAGE_TYPES.map((t) => (
                  <label
                    key={t.id}
                    className={`flex items-start gap-2.5 p-2 rounded-lg border cursor-pointer text-xs transition-colors ${
                      selectedMessageType === t.id
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-border bg-background text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <input
                      type="radio"
                      name="messageType"
                      checked={selectedMessageType === t.id}
                      onChange={() => {
                        setSelectedMessageType(t.id);
                        setSelectedChannel(t.channel);
                      }}
                      className="mt-0.5 text-primary"
                    />
                    <div>
                      <span className="font-semibold text-foreground block">{t.label}</span>
                      <span className="text-[11px] text-muted-foreground">{t.desc}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Outreach Channel & Tone */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">Channel</label>
                <select
                  value={selectedChannel}
                  onChange={(e) => setSelectedChannel(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background"
                >
                  <option value="linkedin">LinkedIn</option>
                  <option value="email">Email</option>
                  <option value="portal_message">Portal</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground mb-1">Tone</label>
                <select
                  value={selectedTone}
                  onChange={(e) => setSelectedTone(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background"
                >
                  <option value="professional">Professional</option>
                  <option value="enthusiastic">Enthusiastic</option>
                  <option value="concise">Concise</option>
                  <option value="formal">Formal</option>
                </select>
              </div>
            </div>

            {/* Custom Instructions */}
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Custom Focus / Instructions (Optional)
              </label>
              <textarea
                rows={2}
                placeholder="e.g., Highlight experience with distributed systems or mention my recent open-source contribution..."
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <button
              onClick={handleGenerateOutreach}
              disabled={generatingOutreach || !selectedRecruiterForOutreach}
              className="w-full py-2.5 px-4 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              {generatingOutreach ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Grounding Resume & Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" /> Generate Personalized Draft
                </>
              )}
            </button>
          </div>

          {/* Right Editor: Draft, Grounded Claims & Dispatch */}
          <div className="lg:col-span-7 p-5 rounded-xl border border-border bg-card flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border mb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-semibold">Outreach Workspace & Approval Gate</h3>
                </div>

                {/* Character Counter with LinkedIn Warning */}
                <div
                  className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${
                    isOverLimit
                      ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
                      : isLinkedIn
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                      : "bg-secondary text-muted-foreground"
                  }`}
                >
                  {charCount} {isLinkedIn ? "/ 300 chars" : "chars"}
                </div>
              </div>

              {/* Subject (for email) */}
              {selectedChannel === "email" && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Subject Line</label>
                  <input
                    type="text"
                    value={editedSubject}
                    onChange={(e) => setEditedSubject(e.target.value)}
                    placeholder="Subject line will appear here..."
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              )}

              {/* Message Body Editor */}
              <div className="mb-3">
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Message Content (Editable)
                </label>
                <textarea
                  rows={10}
                  value={editedBody}
                  onChange={(e) => setEditedBody(e.target.value)}
                  placeholder="Draft your personalized message or generate one using the form on the left..."
                  className="w-full p-3 text-sm font-sans rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 leading-relaxed"
                />
              </div>

              {/* Grounded Claims Evidence */}
              {outreachDraft?.grounded_claims && outreachDraft.grounded_claims.length > 0 && (
                <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 mb-3">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 mb-1">
                    <ShieldCheck className="w-3.5 h-3.5" /> Factual Grounding Verification
                  </div>
                  <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-0.5">
                    {outreachDraft.grounded_claims.map((claim, idx) => (
                      <li key={idx}>{claim}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* LinkedIn character limit notice */}
              {isOverLimit && (
                <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>
                    LinkedIn connection notes cannot exceed 300 characters. Please edit the text to reduce length.
                  </span>
                </div>
              )}
            </div>

            {/* Candidate Approval & Dispatch Actions */}
            <div className="pt-3 border-t border-border flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleApproveOutreach}
                  disabled={approvingOutreach || !editedBody.trim() || isOverLimit}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors inline-flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  {approvingOutreach ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  {outreachDraft?.status === "approved" ? "Approved ✓" : "Approve Draft"}
                </button>

                <button
                  onClick={handleCopyNote}
                  disabled={!editedBody.trim()}
                  className="px-3 py-2 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary transition-colors inline-flex items-center gap-1.5"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copiedNote ? "Copied!" : "Copy Note"}
                </button>
              </div>

              {/* Email Send Button (if channel is email) */}
              {selectedChannel === "email" && (
                <button
                  onClick={() => setShowGmailModal(true)}
                  disabled={outreachDraft?.status !== "approved" || !selectedRecruiterForOutreach?.contact_email}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                  title={
                    !selectedRecruiterForOutreach?.contact_email
                      ? "Recruiter has no verified email address. Nexora forbids email guessing."
                      : outreachDraft?.status !== "approved"
                      ? "Candidate approval is required before sending."
                      : "Send via Gmail"
                  }
                >
                  <Mail className="w-3.5 h-3.5" /> Send via Gmail
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {/* TAB 4: ACTIVITY TIMELINE */}
      {activeTab === "timeline" && (
        <section className="space-y-4">
          <div className="p-4 rounded-xl border border-border bg-card">
            <h3 className="text-sm font-semibold mb-3">Networking Interaction History</h3>
            {crmOverview?.recent_activities && crmOverview.recent_activities.length > 0 ? (
              <div className="space-y-3">
                {crmOverview.recent_activities.map((act) => (
                  <div key={act.id} className="flex items-start gap-3 p-3 rounded-lg bg-secondary/30 border border-border text-xs">
                    <Clock className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-foreground">{act.title}</span>
                        <span className="text-[11px] text-muted-foreground">
                          {new Date(act.created_at).toLocaleString()}
                        </span>
                      </div>
                      {act.description && <p className="text-muted-foreground mt-0.5">{act.description}</p>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                No recent networking activities logged yet. Interactions, approved drafts, and sent messages will appear here.
              </p>
            )}
          </div>
        </section>
      )}

      {/* MODAL 1: ADD RECRUITER */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
          <div className="w-full max-w-lg p-6 rounded-xl border border-border bg-card shadow-xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-border mb-4">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-primary" />
                <h3 className="text-base font-semibold">Add Recruiter Profile</h3>
              </div>
              <button onClick={() => setShowAddModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddRecruiterSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Sarah Jenkins"
                  value={addFullName}
                  onChange={(e) => setAddFullName(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    Company <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Stripe"
                    value={addCompanyName}
                    onChange={(e) => setAddCompanyName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Designation</label>
                  <input
                    type="text"
                    placeholder="e.g., Senior Technical Recruiter"
                    value={addDesignation}
                    onChange={(e) => setAddDesignation(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Specialization</label>
                  <select
                    value={addSpecialization}
                    onChange={(e) => setAddSpecialization(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background"
                  >
                    <option value="Technical Recruitment">Technical Recruitment</option>
                    <option value="Campus & University Recruitment">Campus & University</option>
                    <option value="Leadership & Executive Hiring">Leadership & Executive</option>
                    <option value="Full-Cycle Recruitment">Full-Cycle Recruitment</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Departments</label>
                  <input
                    type="text"
                    placeholder="Engineering, Product, Infrastructure"
                    value={addDepartments}
                    onChange={(e) => setAddDepartments(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground mb-1">Public Profile URL</label>
                <input
                  type="url"
                  placeholder="https://linkedin.com/in/recruiter-profile"
                  value={addProfileUrl}
                  onChange={(e) => setAddProfileUrl(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Contact Email</label>
                  <input
                    type="email"
                    placeholder="name@company.com"
                    value={addEmail}
                    onChange={(e) => setAddEmail(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Verification Status</label>
                  <select
                    value={addVerificationStatus}
                    onChange={(e) => setAddVerificationStatus(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background"
                  >
                    <option value="unverified">Unverified (Candidate Added)</option>
                    <option value="verified">Verified Contact</option>
                    <option value="inferred">Inferred</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3.5 py-2 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingRecruiter}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center gap-1.5"
                >
                  {addingRecruiter && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Save Recruiter Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: GMAIL CONFIRM SEND */}
      {showGmailModal && selectedRecruiterForOutreach && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
          <div className="w-full max-w-lg p-6 rounded-xl border border-border bg-card shadow-xl animate-in fade-in zoom-in-95 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-primary" />
                <h3 className="text-base font-semibold">Confirm Gmail Outreach Dispatch</h3>
              </div>
              <button onClick={() => setShowGmailModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-lg bg-secondary/50 text-xs space-y-1">
              <p>
                <span className="font-semibold text-foreground">Recipient:</span>{" "}
                {selectedRecruiterForOutreach.contact_email}
              </p>
              <p>
                <span className="font-semibold text-foreground">Subject:</span> {editedSubject}
              </p>
            </div>

            <div className="space-y-2 text-xs">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={attachResumeChecked}
                  onChange={(e) => setAttachResumeChecked(e.target.checked)}
                  className="text-primary rounded"
                />
                <span className="text-foreground">Attach verified candidate resume PDF</span>
              </label>

              <label className="flex items-start gap-2 cursor-pointer p-2 rounded-lg border border-amber-500/20 bg-amber-500/5">
                <input
                  type="checkbox"
                  checked={confirmSendChecked}
                  onChange={(e) => setConfirmSendChecked(e.target.checked)}
                  className="mt-0.5 text-primary rounded"
                />
                <span className="text-xs text-amber-800 dark:text-amber-300">
                  <strong>Explicit Candidate Confirmation:</strong> I have reviewed and approved this outreach email, and
                  authorize Nexora to dispatch it immediately via my connected Gmail account.
                </span>
              </label>
            </div>

            <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowGmailModal(false)}
                className="px-3.5 py-2 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSendGmail}
                disabled={sendingGmail || !confirmSendChecked}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {sendingGmail ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                Confirm & Send Email
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: NOTES EDITOR */}
      {selectedContactForNotes && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
          <div className="w-full max-w-md p-6 rounded-xl border border-border bg-card shadow-xl animate-in fade-in zoom-in-95 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="text-sm font-semibold">
                Networking Notes: {selectedContactForNotes.recruiter?.full_name}
              </h3>
              <button
                onClick={() => setSelectedContactForNotes(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <textarea
              rows={5}
              placeholder="Record notes on interactions, career fair conversations, interview insights..."
              value={editNotesText}
              onChange={(e) => setEditNotesText(e.target.value)}
              className="w-full p-3 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <button
                onClick={() => setSelectedContactForNotes(null)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveNotes}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
              >
                Save Notes
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
