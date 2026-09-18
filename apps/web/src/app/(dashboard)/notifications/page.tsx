"use client";

import React, { useState } from "react";
import { useNotifications } from "@/hooks/use-notifications";
import { Bell, CheckCheck, Filter } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";

export default function NotificationsPage() {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const filtered = showUnreadOnly ? notifications.filter((n) => !n.read) : notifications;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Bell className="w-5 h-5 text-indigo-400" /> Notifications Center
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Real-time alert events from engine workflows</p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllAsRead()}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40 w-max"
          >
            <CheckCheck className="w-4 h-4" /> Mark All Read
          </button>
        )}
      </div>

      <div className="rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md divide-y divide-slate-800/50">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No notifications found.</div>
        ) : (
          filtered.map((n) => (
            <div
              key={n.id}
              onClick={() => !n.read && markAsRead(n.id)}
              className={`p-4 transition-colors cursor-pointer hover:bg-slate-800/30 ${!n.read ? "bg-indigo-950/20" : ""}`}
            >
              <div className="flex items-start justify-between gap-3 mb-1">
                <span className="font-semibold text-xs text-slate-200">{n.title}</span>
                <span className="text-[10px] text-slate-500 whitespace-nowrap">{formatRelativeTime(n.created_at)}</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{n.body}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
