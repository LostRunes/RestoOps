"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Conversation, Message } from "@/types";
import { formatRelativeTime } from "@/lib/utils";
import {
  MessageSquare,
  Search,
  Send,
  Mail,
  Phone,
  Bot,
  User,
  CheckCircle2,
  Sparkles,
  Loader2,
} from "lucide-react";
import { AIAnalysisPanel } from "@/components/conversations/ai-analysis-panel";
import { toast } from "sonner";

export default function ConversationsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const [search, setSearch] = useState("");

  const { data: conversations, isLoading: isLoadingConvs } = useQuery({
    queryKey: ["conversations", search],
    queryFn: async () => {
      const res = await api.get<{ items: Conversation[] }>("/conversations");
      return res.items || [];
    },
  });

  const activeConv = conversations?.find((c) => c.id === selectedId) || conversations?.[0];

  const { data: messages, isLoading: isLoadingMsgs } = useQuery({
    queryKey: ["messages", activeConv?.id],
    queryFn: async () => {
      if (!activeConv?.id) return [];
      const res = await api.get<{ items: Message[] }>(`/conversations/${activeConv.id}/messages`);
      return res.items || [];
    },
    enabled: !!activeConv?.id,
  });

  const sendMutation = useMutation({
    mutationFn: async () => {
      if (!activeConv?.id || !replyText.trim()) return;
      return api.post(`/conversations/${activeConv.id}/messages`, {
        content: replyText,
        channel: "EMAIL",
        sender_type: "AGENT",
      });
    },
    onSuccess: () => {
      setReplyText("");
      toast.success("Reply sent successfully");
      queryClient.invalidateQueries({ queryKey: ["messages", activeConv?.id] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to send reply"),
  });

  return (
    <div className="h-[calc(100vh-6.5rem)] flex rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-xl overflow-hidden">
      {/* Left Panel — Conversation List */}
      <div className="w-80 border-r border-slate-800 flex flex-col bg-[#0d1322]">
        <div className="p-3.5 border-b border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-indigo-400" /> Unified Inbox
            </h3>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations..."
              className="w-full bg-[#141c2e] border border-slate-800 rounded-lg pl-9 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-800/50">
          {isLoadingConvs ? (
            <div className="p-6 text-center text-xs text-slate-500">Loading inbox...</div>
          ) : !conversations || conversations.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">No active conversations.</div>
          ) : (
            conversations.map((conv) => {
              const isSelected = activeConv?.id === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => setSelectedId(conv.id)}
                  className={`p-3.5 cursor-pointer transition-colors ${
                    isSelected ? "bg-indigo-950/40 border-l-2 border-indigo-500" : "hover:bg-slate-800/30"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-slate-200 truncate">
                      {conv.lead?.company_name || conv.lead?.contact_name || `Lead #${conv.lead_id.slice(0, 6)}`}
                    </span>
                    <span className="text-[10px] text-slate-500">{formatRelativeTime(conv.last_message_at || conv.created_at)}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="truncate max-w-[160px]">{conv.lead?.email || "Customer Message"}</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {conv.channel}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Middle Panel — Thread & Composer */}
      <div className="flex-1 flex flex-col bg-[#090d16]">
        {/* Thread Header */}
        <div className="h-14 px-6 border-b border-slate-800 flex items-center justify-between bg-[#0d1322]">
          <div>
            <h3 className="text-xs font-bold text-slate-200">
              {activeConv?.lead?.company_name || activeConv?.lead?.contact_name || "Conversation Thread"}
            </h3>
            <p className="text-[10px] text-slate-400">{activeConv?.lead?.email}</p>
          </div>
        </div>

        {/* Messages Feed */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {isLoadingMsgs ? (
            <div className="text-center py-8 text-xs text-slate-500">Loading messages...</div>
          ) : !messages || messages.length === 0 ? (
            <div className="text-center py-12 text-xs text-slate-500">No messages in this thread yet.</div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.sender_type === "CUSTOMER";
              const isAI = msg.sender_type === "AI";
              return (
                <div key={msg.id} className={`flex gap-3 max-w-xl ${isUser ? "mr-auto" : "ml-auto flex-row-reverse"}`}>
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 ${
                      isUser
                        ? "bg-slate-800 text-slate-300"
                        : isAI
                        ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                        : "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                    }`}
                  >
                    {isUser ? <User className="w-3.5 h-3.5" /> : isAI ? <Bot className="w-3.5 h-3.5" /> : "AG"}
                  </div>
                  <div
                    className={`p-3.5 rounded-2xl text-xs space-y-1 ${
                      isUser
                        ? "bg-[#141c2e] text-slate-200 border border-slate-800"
                        : isAI
                        ? "bg-indigo-950/40 text-slate-200 border border-indigo-800/40"
                        : "bg-indigo-600 text-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4 text-[10px] opacity-70 mb-1">
                      <span className="font-semibold">{msg.sender_name || msg.sender_type}</span>
                      <span>{formatRelativeTime(msg.created_at)}</span>
                    </div>
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Message Composer */}
        <div className="p-4 border-t border-slate-800 bg-[#0d1322]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMutation.mutate();
            }}
            className="flex items-center gap-3"
          >
            <input
              type="text"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Type your response to customer..."
              className="flex-1 bg-[#141c2e] border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/60"
            />
            <button
              type="submit"
              disabled={!replyText.trim() || sendMutation.isPending}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50"
            >
              {sendMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Right Panel — Human in the Loop AI Panel */}
      {activeConv?.id && <AIAnalysisPanel conversationId={activeConv.id} />}
    </div>
  );
}
