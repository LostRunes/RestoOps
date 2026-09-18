"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { useNotifications } from "@/hooks/use-notifications";
import { useAuth } from "@/hooks/use-auth";
import { Search, Bell, CheckCheck, User as UserIcon, Sparkles } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";
import Link from "next/link";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard Overview",
  "/leads": "Leads Directory",
  "/campaigns": "Marketing Campaigns",
  "/conversations": "Unified Inbox",
  "/calls": "Call Center & WebRTC",
  "/quotes": "Quotes & Catering",
  "/orders": "Orders & Revenue",
  "/ai/activity": "AI Agents & Audit Log",
  "/jobs": "Background Processing Jobs",
  "/notifications": "Notifications Center",
  "/users": "Team Management",
  "/settings": "Organization Settings",
};

export function Topbar() {
  const pathname = usePathname() || "/dashboard";
  const { user } = useAuth();
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const [showNotifications, setShowNotifications] = useState(false);

  const getTitle = () => {
    for (const [path, title] of Object.entries(PAGE_TITLES)) {
      if (pathname === path || (path !== "/dashboard" && pathname.startsWith(path))) {
        return title;
      }
    }
    return "Dashboard";
  };

  return (
    <header className="h-16 bg-[#0d1322]/80 border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-20 backdrop-blur-md">
      {/* Dynamic Page Title */}
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-slate-100 tracking-tight">{getTitle()}</h1>
        <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          Live Engine
        </span>
      </div>

      {/* Right Tools */}
      <div className="flex items-center gap-4">
        {/* Quick Search Input */}
        <div className="relative hidden md:block w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search leads, quotes..."
            className="w-full bg-[#141c2e] border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>

        {/* Real-Time Notification Bell Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 transition-colors"
            title="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 rounded-full bg-indigo-500 ring-2 ring-[#0d1322] animate-pulse" />
            )}
          </button>

          {/* Notification Menu */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-[#0f172a] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="p-3.5 border-b border-slate-800 flex items-center justify-between bg-[#141c2e]">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-200">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-indigo-600/30 text-indigo-300 border border-indigo-500/30">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={() => markAllAsRead()}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition-colors"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/50">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">No notifications yet</div>
                ) : (
                  notifications.slice(0, 10).map((n) => (
                    <div
                      key={n.id}
                      onClick={() => !n.read && markAsRead(n.id)}
                      className={`p-3.5 text-xs transition-colors cursor-pointer hover:bg-slate-800/40 ${
                        !n.read ? "bg-indigo-950/20" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className="font-semibold text-slate-200">{n.title}</span>
                        <span className="text-[10px] text-slate-500 whitespace-nowrap">
                          {formatRelativeTime(n.created_at)}
                        </span>
                      </div>
                      <p className="text-slate-400 leading-relaxed">{n.body}</p>
                    </div>
                  ))
                )}
              </div>

              <div className="p-2.5 border-t border-slate-800 text-center bg-[#141c2e]">
                <Link
                  href="/notifications"
                  onClick={() => setShowNotifications(false)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  View all notifications →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User Profile Avatar Pill */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 flex items-center justify-center font-bold text-xs">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <UserIcon className="w-4 h-4" />}
          </div>
          <span className="hidden sm:inline-block text-xs font-medium text-slate-300">{user?.full_name || "User"}</span>
        </div>
      </div>
    </header>
  );
}
