"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bell,
  Briefcase,
  Calendar,
  Check,
  CheckCheck,
  Clock,
  ExternalLink,
  Globe,
  Layers,
  Loader2,
  RefreshCw,
  Settings,
  Sparkles,
  Tag,
  Trash2,
  X,
} from "lucide-react";

import { useAuth } from "@/context/auth-context";
import {
  NotificationItem,
  notificationsApi,
  NotificationType,
  UserNotificationPreference,
} from "@/lib/api";

const TYPE_CONFIG: Record<
  NotificationType,
  { label: string; icon: React.ElementType; color: string; bg: string }
> = {
  interview_reminder: {
    label: "Interview Reminder",
    icon: Calendar,
    color: "text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/20",
  },
  assessment_reminder: {
    label: "Assessment Reminder",
    icon: Tag,
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
  },
  application_deadline: {
    label: "Application Deadline",
    icon: AlertTriangle,
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
  },
  application_follow_up: {
    label: "Application Follow-Up",
    icon: Clock,
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
  },
  job_freshness_update: {
    label: "Job Freshness Update",
    icon: Briefcase,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
  },
  task_completion: {
    label: "Task Completion",
    icon: Sparkles,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  system: {
    label: "System Notice",
    icon: Layers,
    color: "text-slate-400",
    bg: "bg-slate-500/10 border-slate-500/20",
  },
};

const STANDARD_TIMEZONES = [
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
  { value: "America/New_York", label: "Eastern Time (US / New York)" },
  { value: "America/Chicago", label: "Central Time (US / Chicago)" },
  { value: "America/Denver", label: "Mountain Time (US / Denver)" },
  { value: "America/Los_Angeles", label: "Pacific Time (US / Los Angeles)" },
  { value: "Europe/London", label: "London / GMT" },
  { value: "Europe/Paris", label: "Central Europe (Paris / Berlin)" },
  { value: "Asia/Dubai", label: "Gulf Standard Time (Dubai)" },
  { value: "Asia/Kolkata", label: "India Standard Time (IST / Kolkata)" },
  { value: "Asia/Singapore", label: "Singapore Standard Time (SGT)" },
  { value: "Asia/Tokyo", label: "Japan Standard Time (JST / Tokyo)" },
  { value: "Australia/Sydney", label: "Australian Eastern Time (Sydney)" },
];

export default function NotificationsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-12 text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Loading Notification Center...</p>
        </div>
      }
    >
      <NotificationsContent />
    </React.Suspense>
  );
}

function NotificationsContent() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  // State
  const [activeTab, setActiveTab] = useState<
    "all" | "unread" | "interviews" | "deadlines" | "preferences"
  >("all");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [preferences, setPreferences] = useState<UserNotificationPreference | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  // Auth Guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Load Data
  const loadData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const [listRes, prefRes] = await Promise.all([
        notificationsApi.list({ limit: 100 }),
        notificationsApi.getPreferences(),
      ]);
      setNotifications(listRes.items);
      setUnreadCount(listRes.unread_count);
      setPreferences(prefRes);
    } catch (err) {
      console.error("Failed to load notifications:", err);
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

  // Mark single as read
  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error("Failed to mark as read:", err);
    }
  };

  // Mark all as read
  const handleMarkAllAsRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
      );
      setUnreadCount(0);
      setFeedbackMsg("All notifications marked as read.");
      setTimeout(() => setFeedbackMsg(null), 3000);
    } catch (err) {
      console.error("Failed to mark all as read:", err);
    }
  };

  // Delete notification
  const handleDelete = async (id: string) => {
    try {
      await notificationsApi.delete(id);
      const target = notifications.find((n) => n.id === id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (target && !target.is_read) {
        setUnreadCount((c) => Math.max(0, c - 1));
      }
    } catch (err) {
      console.error("Failed to delete notification:", err);
    }
  };

  // Manual Trigger Reminder Scan
  const handleTriggerScan = async () => {
    setIsScanning(true);
    try {
      const res = await notificationsApi.processReminders();
      setFeedbackMsg(
        `Scanned reminders: ${res.reminders_created} new notification(s) generated.`
      );
      setTimeout(() => setFeedbackMsg(null), 4000);
      await loadData();
    } catch (err) {
      console.error("Error running reminder scan:", err);
      setFeedbackMsg("Failed to scan reminders.");
      setTimeout(() => setFeedbackMsg(null), 4000);
    } finally {
      setIsScanning(false);
    }
  };

  // Save Preferences
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preferences) return;

    try {
      const updated = await notificationsApi.updatePreferences({
        enable_in_app: preferences.enable_in_app,
        enable_interview_reminders: preferences.enable_interview_reminders,
        enable_assessment_reminders: preferences.enable_assessment_reminders,
        enable_follow_up_reminders: preferences.enable_follow_up_reminders,
        enable_deadline_reminders: preferences.enable_deadline_reminders,
        enable_job_freshness_updates: preferences.enable_job_freshness_updates,
        enable_task_completion_updates: preferences.enable_task_completion_updates,
        enable_system_notifications: preferences.enable_system_notifications,
        interview_reminder_24h: preferences.interview_reminder_24h,
        interview_reminder_1h: preferences.interview_reminder_1h,
        preferred_timezone: preferences.preferred_timezone,
      });
      setPreferences(updated);
      setFeedbackMsg("Notification preferences updated successfully.");
      setTimeout(() => setFeedbackMsg(null), 3500);
    } catch (err) {
      console.error("Failed to update preferences:", err);
      alert("Error saving preferences. Please check your settings.");
    }
  };

  // Filtered Notifications based on active tab
  const filteredNotifications = notifications.filter((notif) => {
    if (activeTab === "unread") return !notif.is_read;
    if (activeTab === "interviews")
      return (
        notif.notification_type === "interview_reminder" ||
        notif.notification_type === "assessment_reminder"
      );
    if (activeTab === "deadlines")
      return (
        notif.notification_type === "application_deadline" ||
        notif.notification_type === "application_follow_up"
      );
    return true;
  });

  if (authLoading || (!user && isLoading)) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Loading Notification Center...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition"
              title="Return to Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight">Notification Center</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium border border-primary/20">
                  Prompt 12
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Centralized reminders, deadline alerts & custom notification preferences
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleTriggerScan}
              disabled={isScanning}
              className="p-2 text-xs rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition flex items-center gap-1.5"
              title="Scan and evaluate upcoming reminders now"
            >
              <Clock className={`w-3.5 h-3.5 ${isScanning ? "animate-spin text-primary" : ""}`} />
              <span className="hidden sm:inline">
                {isScanning ? "Scanning..." : "Check Reminders"}
              </span>
            </button>

            <button
              onClick={loadData}
              disabled={isRefreshing}
              className="p-2 text-xs rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition flex items-center gap-1.5"
              title="Refresh notifications"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            {unreadCount > 0 && activeTab !== "preferences" && (
              <button
                onClick={handleMarkAllAsRead}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition flex items-center gap-1.5 shadow-sm"
              >
                <CheckCheck className="w-4 h-4" />
                <span>Mark All Read</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Feedback Alert */}
        {feedbackMsg && (
          <div className="p-3.5 rounded-xl border border-primary/30 bg-primary/10 text-primary text-xs flex items-center justify-between gap-3 animate-in fade-in">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 flex-shrink-0" />
              <span>{feedbackMsg}</span>
            </div>
            <button
              onClick={() => setFeedbackMsg(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-border flex items-center justify-between gap-2 overflow-x-auto">
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "all"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Bell className="w-3.5 h-3.5" />
              <span>All Notifications</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-secondary text-muted-foreground">
                {notifications.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("unread")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "unread"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Unread</span>
              {unreadCount > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-primary text-primary-foreground font-bold">
                  {unreadCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("interviews")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "interviews"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Interviews & Tests</span>
            </button>

            <button
              onClick={() => setActiveTab("deadlines")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "deadlines"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Deadlines & Follow-ups</span>
            </button>

            <button
              onClick={() => setActiveTab("preferences")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "preferences"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Settings className="w-3.5 h-3.5" />
              <span>Preferences</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Notifications List */}
        {activeTab !== "preferences" ? (
          <div className="space-y-3">
            {isLoading ? (
              <div className="p-12 text-center text-muted-foreground text-xs flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <span>Loading notifications...</span>
              </div>
            ) : filteredNotifications.length === 0 ? (
              <div className="p-12 text-center space-y-3 rounded-xl border border-border bg-card">
                <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mx-auto text-muted-foreground">
                  <Bell className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">No notifications found</h3>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  {activeTab === "unread"
                    ? "You are all caught up! No unread notifications."
                    : "No notifications match this category yet. Reminders are generated automatically based on your applications and interviews."}
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {filteredNotifications.map((notif) => {
                  const conf = TYPE_CONFIG[notif.notification_type] || TYPE_CONFIG.system;
                  const IconComp = conf.icon;

                  return (
                    <div
                      key={notif.id}
                      className={`p-4 rounded-xl border transition flex flex-col sm:flex-row items-start justify-between gap-3 ${
                        !notif.is_read
                          ? "border-primary/40 bg-card shadow-sm"
                          : "border-border bg-card/60 opacity-80"
                      }`}
                    >
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div
                          className={`p-2 rounded-lg border flex-shrink-0 mt-0.5 ${conf.bg} ${conf.color}`}
                        >
                          <IconComp className="w-4 h-4" />
                        </div>

                        <div className="space-y-1 flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${conf.bg} ${conf.color}`}
                            >
                              {conf.label}
                            </span>
                            {!notif.is_read && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-primary text-primary-foreground">
                                NEW
                              </span>
                            )}
                            <span className="text-[11px] text-muted-foreground">
                              {new Date(notif.created_at).toLocaleString([], {
                                dateStyle: "medium",
                                timeStyle: "short",
                              })}
                            </span>
                          </div>

                          <h3 className="text-sm font-bold text-foreground">{notif.title}</h3>
                          <p className="text-xs text-muted-foreground whitespace-pre-wrap">
                            {notif.message}
                          </p>

                          {notif.scheduled_for && (
                            <div className="text-[11px] text-muted-foreground/80 flex items-center gap-1 pt-0.5">
                              <Clock className="w-3 h-3 text-primary" />
                              <span>
                                Scheduled target:{" "}
                                {new Date(notif.scheduled_for).toLocaleString([], {
                                  dateStyle: "medium",
                                  timeStyle: "short",
                                })}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 self-end sm:self-center flex-shrink-0 text-xs">
                        {notif.action_url && (
                          <a
                            href={notif.action_url}
                            target={notif.action_url.startsWith("http") ? "_blank" : undefined}
                            rel={
                              notif.action_url.startsWith("http")
                                ? "noopener noreferrer"
                                : undefined
                            }
                            onClick={() => {
                              if (!notif.is_read) handleMarkAsRead(notif.id);
                            }}
                            className="px-2.5 py-1 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 transition flex items-center gap-1"
                          >
                            <span>Open</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}

                        {!notif.is_read ? (
                          <button
                            onClick={() => handleMarkAsRead(notif.id)}
                            className="p-1.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground transition"
                            title="Mark as read"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        ) : null}

                        <button
                          onClick={() => handleDelete(notif.id)}
                          className="p-1.5 rounded border border-destructive/20 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition"
                          title="Delete notification"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          /* Tab 2: User Preferences Form */
          <div className="max-w-2xl bg-card border border-border rounded-xl p-6 shadow-sm space-y-6 text-xs">
            <div>
              <h2 className="text-base font-bold text-foreground">Notification Preferences</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Customize automated reminder categories, scheduling intervals, and your preferred
                timezone.
              </p>
            </div>

            {preferences && (
              <form onSubmit={handleSavePreferences} className="space-y-5">
                {/* Master Switch */}
                <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 flex items-center justify-between gap-4">
                  <div>
                    <span className="font-bold text-foreground block text-sm">
                      In-App Notifications
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Enable or disable all in-app notifications and reminder alerts.
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.enable_in_app}
                    onChange={(e) =>
                      setPreferences({ ...preferences, enable_in_app: e.target.checked })
                    }
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                  />
                </div>

                {/* Preferred Timezone */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-foreground flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-primary" />
                    Preferred Display Timezone
                  </label>
                  <p className="text-[11px] text-muted-foreground">
                    Reminders will show formatted dates and event times localized to this timezone.
                  </p>
                  <select
                    value={preferences.preferred_timezone}
                    onChange={(e) =>
                      setPreferences({ ...preferences, preferred_timezone: e.target.value })
                    }
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {STANDARD_TIMEZONES.map((tz) => (
                      <option key={tz.value} value={tz.value}>
                        {tz.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Category Toggles */}
                <div className="space-y-3 pt-2 border-t border-border">
                  <h3 className="font-bold text-foreground uppercase tracking-wider text-[11px]">
                    Reminder Categories
                  </h3>

                  {/* Interview Reminders */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-foreground block">
                          Interview Reminders
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          Scheduled technical rounds, behavioral interviews, and managerial calls.
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.enable_interview_reminders}
                        onChange={(e) =>
                          setPreferences({
                            ...preferences,
                            enable_interview_reminders: e.target.checked,
                          })
                        }
                        className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                      />
                    </div>

                    {preferences.enable_interview_reminders && (
                      <div className="pl-3 pt-2 border-t border-border/50 flex flex-wrap gap-4 text-[11px]">
                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={preferences.interview_reminder_24h}
                            onChange={(e) =>
                              setPreferences({
                                ...preferences,
                                interview_reminder_24h: e.target.checked,
                              })
                            }
                            className="rounded border-border text-primary"
                          />
                          <span>24 hours prior</span>
                        </label>

                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={preferences.interview_reminder_1h}
                            onChange={(e) =>
                              setPreferences({
                                ...preferences,
                                interview_reminder_1h: e.target.checked,
                              })
                            }
                            className="rounded border-border text-primary"
                          />
                          <span>1 hour prior</span>
                        </label>
                      </div>
                    )}
                  </div>

                  {/* Assessment Reminders */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground block">
                        Assessment Reminders
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Coding assessments, take-home exercises, and technical challenges.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.enable_assessment_reminders}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          enable_assessment_reminders: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                    />
                  </div>

                  {/* Deadline Reminders */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground block">
                        Application Deadlines
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Alerts for job application submission deadlines expiring within 24 hours.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.enable_deadline_reminders}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          enable_deadline_reminders: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                    />
                  </div>

                  {/* Follow-up Reminders */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground block">
                        Application Follow-Ups
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Reminders when candidate follow-up with recruiter or company is due.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.enable_follow_up_reminders}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          enable_follow_up_reminders: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                    />
                  </div>

                  {/* Job Freshness Updates */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground block">
                        Job Freshness & Verification
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Status updates when saved jobs are verified, corroborated, or closed.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.enable_job_freshness_updates}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          enable_job_freshness_updates: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                    />
                  </div>

                  {/* AI & Task Completion */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground block">
                        Resume & AI Studio Tasks
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Notifications when resume parsing or AI intelligence analysis completes.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.enable_task_completion_updates}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          enable_task_completion_updates: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                    />
                  </div>

                  {/* System Announcements */}
                  <div className="p-3 rounded-lg border border-border bg-secondary/20 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground block">
                        System Notifications
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Important account security updates and platform notices.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.enable_system_notifications}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          enable_system_notifications: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded border-border text-primary cursor-pointer"
                    />
                  </div>
                </div>

                <div className="pt-3 border-t border-border flex justify-end">
                  <button
                    type="submit"
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition shadow-sm"
                  >
                    Save Preferences
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
