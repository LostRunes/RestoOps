"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { Notification, JobProgress } from "@/types";
import { WebSocketManager } from "@/lib/websocket";
import { useAuth } from "./auth-provider";
import { toast } from "sonner";
import { api } from "@/lib/api-client";

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  jobProgress: Record<string, JobProgress>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  refetchNotifications: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [jobProgress, setJobProgress] = useState<Record<string, JobProgress>>({});

  const fetchUnreadCount = async () => {
    try {
      const data = await api.get<{ unread_count: number }>("/notifications/unread-count");
      setUnreadCount(data.unread_count);
    } catch {}
  };

  const fetchNotifications = async () => {
    try {
      const data = await api.get<{ items: Notification[] }>("/notifications", { limit: 20 });
      setNotifications(data.items || []);
    } catch {}
  };

  useEffect(() => {
    if (!isAuthenticated) return;

    fetchUnreadCount();
    fetchNotifications();

    const ws = new WebSocketManager("/notifications");
    ws.connect();

    const unsubscribeMessage = ws.on("notification", (event) => {
      if (event.notification) {
        const notif: Notification = event.notification;
        setNotifications((prev) => [notif, ...prev.slice(0, 49)]);
        setUnreadCount((prev) => prev + 1);

        toast(notif.title, {
          description: notif.body,
        });
      }
    });

    const unsubscribeUnread = ws.on("unread_count", (event) => {
      if (typeof event.count === "number") {
        setUnreadCount(event.count);
      }
    });

    const unsubscribeJob = ws.on("job_progress", (event) => {
      if (event.job_id) {
        setJobProgress((prev) => ({
          ...prev,
          [event.job_id]: {
            job_id: event.job_id,
            job_type: event.job_type || "TASK",
            status: event.status || "RUNNING",
            total: event.total || 0,
            processed: event.processed || 0,
            percentage: event.percentage || 0,
            details: event.details,
          },
        }));

        if (event.percentage === 100 || event.status === "COMPLETED") {
          toast.success(`Job Completed`, {
            description: `${event.job_type || "Task"} has completed successfully.`,
          });
        }
      }
    });

    return () => {
      unsubscribeMessage();
      unsubscribeUnread();
      unsubscribeJob();
      ws.disconnect();
    };
  }, [isAuthenticated, user?.id]);

  const markAsRead = async (id: string) => {
    try {
      await api.post(`/notifications/${id}/read`);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {}
  };

  const markAllAsRead = async () => {
    try {
      await api.post("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
      toast.success("All notifications marked as read");
    } catch {}
  };

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        jobProgress,
        markAsRead,
        markAllAsRead,
        refetchNotifications: fetchNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}
