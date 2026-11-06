"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Bell,
  Briefcase,
  Calendar,
  Check,
  CheckCheck,
  Clock,
  ExternalLink,
  Layers,
  Sparkles,
  Tag,
  X,
} from "lucide-react";

import { NotificationItem, notificationsApi, NotificationType } from "@/lib/api";

const TYPE_CONFIG: Record<
  NotificationType,
  { label: string; icon: React.ElementType; color: string; bg: string }
> = {
  interview_reminder: {
    label: "Interview",
    icon: Calendar,
    color: "text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/20",
  },
  assessment_reminder: {
    label: "Assessment",
    icon: Tag,
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
  },
  application_deadline: {
    label: "Deadline",
    icon: AlertTriangle,
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
  },
  application_follow_up: {
    label: "Follow-up",
    icon: Clock,
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
  },
  job_freshness_update: {
    label: "Job Update",
    icon: Briefcase,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
  },
  task_completion: {
    label: "AI Studio",
    icon: Sparkles,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  system: {
    label: "System",
    icon: Layers,
    color: "text-slate-400",
    bg: "bg-slate-500/10 border-slate-500/20",
  },
};

export function NotificationBell() {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [latestNotifications, setLatestNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.unread_count);
    } catch {
      // Quiet fail if not logged in or during initial load
    }
  }, []);

  // Fetch latest notifications when opened
  const fetchLatest = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await notificationsApi.list({ limit: 5 });
      setLatestNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Poll unread count every 60 seconds (efficient, low overhead)
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 60000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleDropdown = () => {
    if (!isOpen) {
      fetchLatest();
    }
    setIsOpen(!isOpen);
  };

  const handleMarkAsRead = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await notificationsApi.markRead(id);
      setLatestNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error("Failed to mark as read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setLatestNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all read:", err);
    }
  };

  const handleNotificationClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await notificationsApi.markRead(notif.id);
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch {
        // Continue navigation
      }
    }
    setIsOpen(false);
    if (notif.action_url) {
      if (notif.action_url.startsWith("http")) {
        window.open(notif.action_url, "_blank", "noopener,noreferrer");
      } else {
        router.push(notif.action_url);
      }
    } else {
      router.push("/dashboard/notifications");
    }
  };

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={toggleDropdown}
        className="relative p-2 rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition"
        title="Notifications"
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 px-1.5 py-0.2 min-w-[1.2rem] h-[1.2rem] flex items-center justify-center text-[10px] font-bold rounded-full bg-primary text-primary-foreground animate-pulse shadow-sm">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl border border-border bg-card shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-1 duration-150 text-xs">
          {/* Header */}
          <div className="p-3 border-b border-border flex items-center justify-between bg-secondary/30">
            <div className="flex items-center gap-2">
              <span className="font-bold text-foreground">Notifications</span>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary border border-primary/20">
                  {unreadCount} unread
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition"
                title="Mark all as read"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          {/* Body */}
          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {isLoading ? (
              <div className="p-6 text-center text-muted-foreground">Loading...</div>
            ) : latestNotifications.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground">
                <Bell className="w-6 h-6 mx-auto mb-2 opacity-40" />
                <span>No notifications yet.</span>
              </div>
            ) : (
              latestNotifications.map((notif) => {
                const conf = TYPE_CONFIG[notif.notification_type] || TYPE_CONFIG.system;
                const IconComponent = conf.icon;

                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`p-3 hover:bg-secondary/40 transition cursor-pointer flex items-start gap-2.5 ${
                      !notif.is_read ? "bg-primary/5" : ""
                    }`}
                  >
                    <div
                      className={`p-1.5 rounded-lg border flex-shrink-0 mt-0.5 ${conf.bg} ${conf.color}`}
                    >
                      <IconComponent className="w-3.5 h-3.5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-foreground truncate block">
                          {notif.title}
                        </span>
                        {!notif.is_read && (
                          <span
                            className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0"
                            title="Unread"
                          />
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">
                        {notif.message}
                      </p>
                      <span className="text-[10px] text-muted-foreground/80 mt-1 block">
                        {new Date(notif.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}{" "}
                        &bull; {new Date(notif.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {!notif.is_read && (
                      <button
                        onClick={(e) => handleMarkAsRead(e, notif.id)}
                        className="p-1 rounded text-muted-foreground hover:text-foreground opacity-60 hover:opacity-100 transition flex-shrink-0"
                        title="Mark read"
                      >
                        <Check className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-2.5 border-t border-border bg-secondary/20 flex items-center justify-between text-[11px]">
            <Link
              href="/dashboard/notifications"
              onClick={() => setIsOpen(false)}
              className="text-primary hover:underline font-semibold flex items-center gap-1"
            >
              Open Notification Center &rarr;
            </Link>
            <button
              onClick={() => setIsOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

