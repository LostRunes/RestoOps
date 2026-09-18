"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useNotifications } from "@/hooks/use-notifications";
import {
  LayoutDashboard,
  Users,
  Megaphone,
  MessageSquare,
  Phone,
  FileText,
  ShoppingBag,
  Brain,
  Activity,
  Bell,
  Settings,
  UserCog,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Utensils,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { label: "Leads", href: "/leads", icon: Users },
  { label: "Campaigns", href: "/campaigns", icon: Megaphone },
  { label: "Conversations", href: "/conversations", icon: MessageSquare },
  { label: "Calls", href: "/calls", icon: Phone },
  { label: "Quotes", href: "/quotes", icon: FileText },
  { label: "Orders", href: "/orders", icon: ShoppingBag },
  { label: "AI Activity", href: "/ai/activity", icon: Brain },
  { label: "Background Jobs", href: "/jobs", icon: Activity },
  { label: "Notifications", href: "/notifications", icon: Bell, badgeKey: "unread" },
  { label: "Users", href: "/users", icon: UserCog },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { unreadCount } = useNotifications();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "relative flex flex-col h-screen bg-[#0d1322] border-r border-slate-800/80 transition-all duration-300 z-30 select-none",
        collapsed ? "w-20" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-800/80">
        <Link href="/dashboard" className="flex items-center gap-3 overflow-hidden">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 shrink-0">
            <Utensils className="w-5 h-5" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-slate-100 text-base tracking-tight leading-none">RestoOps</span>
              <span className="text-[10px] text-slate-400 font-mono mt-1">AI Dining Ops</span>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
          const hasBadge = item.badgeKey === "unread" && unreadCount > 0;

          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all group relative",
                isActive
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  isActive ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
                )}
              />
              {!collapsed && <span className="truncate">{item.label}</span>}

              {hasBadge && (
                <span
                  className={cn(
                    "ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500 text-white shrink-0 shadow-sm",
                    collapsed && "absolute top-2 right-2 px-1 py-0.5 text-[8px]"
                  )}
                >
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      {/* User Info & Logout */}
      <div className="p-3 border-t border-slate-800/80 bg-[#0a0f1b]/50">
        <div className={cn("flex items-center gap-3", collapsed ? "justify-center" : "justify-between")}>
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold text-slate-200 truncate">{user?.full_name || "User"}</span>
              <span className="text-[10px] text-slate-500 truncate">{user?.email || "owner@restoops.com"}</span>
            </div>
          )}
          <button
            onClick={logout}
            title="Logout"
            className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-950/30 transition-colors shrink-0"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
