"use client";

import React, { useState, use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Quote, QuoteItem } from "@/types";
import { formatCurrency } from "@/lib/utils";
import { ArrowLeft, Save, Plus, Trash2, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export default function QuoteEditorClient({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const isNew = id === "new";

  const [leadId, setLeadId] = useState("");
  const [eventType, setEventType] = useState("Corporate Lunch");
  const [eventDate, setEventDate] = useState("2026-10-15");
  const [guestCount, setGuestCount] = useState(50);
  const [items, setItems] = useState<QuoteItem[]>([
    { name: "Artisanal Sandwich & Salad Platter", description: "Assorted gourmet wraps and seasonal sides", quantity: 50, unit_price: 18.5, total: 925 },
    { name: "Beverage Service", description: "Fresh juices, sparkling water, and artisanal coffee", quantity: 50, unit_price: 4.0, total: 200 },
  ]);
  const [taxRate, setTaxRate] = useState(0.08);
  const [deliveryFee, setDeliveryFee] = useState(50);

  const subtotal = items.reduce((sum, item) => sum + (item.quantity * item.unit_price || 0), 0);
  const tax = subtotal * taxRate;
  const total = subtotal + tax + deliveryFee;

  const { data: quote, isLoading } = useQuery({
    queryKey: ["quote", id],
    queryFn: async () => {
      if (isNew) return null;
      const res = await api.get<Quote>(`/quotes/${id}`);
      setLeadId(res.lead_id);
      setEventType(res.event_type || "");
      setGuestCount(res.guest_count || 50);
      if (res.items?.length > 0) setItems(res.items);
      return res;
    },
    enabled: !isNew,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        lead_id: leadId || "00000000-0000-0000-0000-000000000000",
        event_type: eventType,
        event_date: eventDate,
        guest_count: guestCount,
        items: items.map((i) => ({ ...i, total: i.quantity * i.unit_price })),
        subtotal,
        tax,
        delivery_fee: deliveryFee,
        total,
      };
      if (isNew) {
        return api.post<Quote>("/quotes", payload);
      } else {
        return api.patch<Quote>(`/quotes/${id}`, payload);
      }
    },
    onSuccess: () => {
      toast.success(isNew ? "Quote created" : "Quote updated");
      queryClient.invalidateQueries({ queryKey: ["quotes"] });
      router.push("/quotes");
    },
    onError: (err: any) => toast.error(err.message || "Failed to save quote"),
  });

  const addItem = () => {
    setItems([...items, { name: "Custom Menu Item", description: "", quantity: 1, unit_price: 15, total: 15 }]);
  };

  const removeItem = (idx: number) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-500 text-xs">Loading quote...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/quotes" className="p-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h2 className="text-xl font-bold text-slate-100">{isNew ? "Create Catering Quote" : `Quote ${quote?.quote_number}`}</h2>
            <p className="text-xs text-slate-400">Interactive line-item editor & auto calculations</p>
          </div>
        </div>

        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-indigo-950/40"
        >
          {saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Quote
        </button>
      </div>

      {/* Quote Event Details */}
      <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
        <h3 className="text-sm font-semibold text-slate-200">Event & Client Metadata</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Event Type</label>
            <input
              type="text"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200"
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Event Date</label>
            <input
              type="date"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200"
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Guest Count</label>
            <input
              type="number"
              value={guestCount}
              onChange={(e) => setGuestCount(parseInt(e.target.value) || 0)}
              className="w-full bg-[#141c2e] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200"
            />
          </div>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800/80 shadow-md space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-semibold text-slate-200">Menu Line Items</h3>
          <button
            onClick={addItem}
            className="px-3 py-1 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> Add Item
          </button>
        </div>

        <div className="space-y-3">
          {items.map((item, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-3 items-center bg-[#141c2e] p-3 rounded-xl border border-slate-800">
              <div className="col-span-5">
                <input
                  type="text"
                  value={item.name}
                  onChange={(e) => {
                    const copy = [...items];
                    copy[idx].name = e.target.value;
                    setItems(copy);
                  }}
                  placeholder="Item name"
                  className="w-full bg-[#0d1322] border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 font-semibold"
                />
              </div>
              <div className="col-span-2">
                <input
                  type="number"
                  value={item.quantity}
                  onChange={(e) => {
                    const copy = [...items];
                    copy[idx].quantity = parseFloat(e.target.value) || 0;
                    setItems(copy);
                  }}
                  className="w-full bg-[#0d1322] border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 text-center"
                />
              </div>
              <div className="col-span-2">
                <input
                  type="number"
                  value={item.unit_price}
                  onChange={(e) => {
                    const copy = [...items];
                    copy[idx].unit_price = parseFloat(e.target.value) || 0;
                    setItems(copy);
                  }}
                  className="w-full bg-[#0d1322] border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 text-right"
                />
              </div>
              <div className="col-span-2 text-right font-bold text-xs text-slate-200">
                {formatCurrency(item.quantity * item.unit_price)}
              </div>
              <div className="col-span-1 text-right">
                <button onClick={() => removeItem(idx)} className="text-slate-500 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Pricing Totals Breakdown */}
        <div className="pt-4 border-t border-slate-800 flex justify-end">
          <div className="w-64 space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Subtotal:</span>
              <span className="font-semibold text-slate-200">{formatCurrency(subtotal)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Tax (8%):</span>
              <span className="font-semibold text-slate-200">{formatCurrency(tax)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Delivery Fee:</span>
              <span className="font-semibold text-slate-200">{formatCurrency(deliveryFee)}</span>
            </div>
            <div className="flex justify-between pt-2 border-t border-slate-800 text-sm font-bold text-emerald-400">
              <span>Total Quote:</span>
              <span>{formatCurrency(total)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
