"use client";

import React, { useState } from "react";
import { Phone, Mic, MicOff, PhoneOff, Volume2, Globe, Radio, X } from "lucide-react";
import { useWebRTC } from "@/hooks/use-webrtc";
import { api } from "@/lib/api-client";
import { toast } from "sonner";

interface CallDialogProps {
  isOpen: boolean;
  onClose: () => void;
  leadId?: string;
  phoneNumber?: string;
}

export function CallDialog({ isOpen, onClose, leadId, phoneNumber = "+18005550199" }: CallDialogProps) {
  const [provider, setProvider] = useState<"WEBRTC" | "EXOTEL">("WEBRTC");
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const { callState, isMuted, duration, audioLevel, startCall, endCall, toggleMute } = useWebRTC(activeRoomId || undefined);

  if (!isOpen) return null;

  const handleInitiate = async () => {
    if (provider === "EXOTEL") {
      try {
        await api.post("/calls", { lead_id: leadId, provider: "EXOTEL", to_phone: phoneNumber });
        toast.success("Phone call triggered via Exotel!");
        onClose();
      } catch (err: any) {
        toast.error(err.message || "Failed to trigger phone call");
      }
    } else {
      const mockRoom = `room-${Date.now()}`;
      setActiveRoomId(mockRoom);
    }
  };

  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-[#0f172a] border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6 relative text-center">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
        >
          <X className="w-4 h-4" />
        </button>

        {!activeRoomId ? (
          <div className="space-y-5">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mx-auto mb-3">
                <Phone className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-100">Initiate Communication Call</h3>
              <p className="text-xs text-slate-400 mt-1">Select channel provider for lead intake</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setProvider("WEBRTC")}
                className={`p-4 rounded-2xl border text-left transition-all space-y-2 ${
                  provider === "WEBRTC"
                    ? "bg-indigo-950/40 border-indigo-500 text-slate-100 shadow-md shadow-indigo-950/40"
                    : "bg-[#141c2e] border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <Globe className="w-5 h-5 text-indigo-400" />
                <div>
                  <div className="text-xs font-bold">Browser WebRTC</div>
                  <div className="text-[10px] opacity-70">Real-time IP Audio</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setProvider("EXOTEL")}
                className={`p-4 rounded-2xl border text-left transition-all space-y-2 ${
                  provider === "EXOTEL"
                    ? "bg-indigo-950/40 border-indigo-500 text-slate-100 shadow-md shadow-indigo-950/40"
                    : "bg-[#141c2e] border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <Radio className="w-5 h-5 text-indigo-400" />
                <div>
                  <div className="text-xs font-bold">Exotel Telephony</div>
                  <div className="text-[10px] opacity-70">PSTN Phone Call</div>
                </div>
              </button>
            </div>

            <button
              onClick={handleInitiate}
              className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-950/50"
            >
              <Phone className="w-4 h-4" /> Start Call Now
            </button>
          </div>
        ) : (
          /* Active WebRTC Call UI */
          <div className="space-y-6 py-4">
            <div className="w-20 h-20 rounded-full bg-indigo-600/20 border-2 border-indigo-500/50 text-indigo-300 flex items-center justify-center mx-auto shadow-xl relative">
              <Phone className="w-8 h-8 animate-pulse" />
              {callState === "CONNECTED" && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-500 ring-4 ring-[#0f172a]" />
              )}
            </div>

            <div>
              <h4 className="text-base font-bold text-slate-100">Catering Client Call</h4>
              <p className="text-xs text-indigo-400 font-mono mt-1 font-semibold">{callState}</p>
              <div className="text-2xl font-bold font-mono text-slate-200 mt-2">{formatTimer(duration)}</div>
            </div>

            {/* Audio Waveform Indicator */}
            <div className="h-8 flex items-center justify-center gap-1.5 px-6">
              {[40, 70, 30, 90, 60, 100, 50, 80, 20].map((h, i) => (
                <div
                  key={i}
                  className="w-1.5 bg-indigo-500 rounded-full transition-all duration-75"
                  style={{
                    height: callState === "CONNECTED" ? `${Math.max(10, (audioLevel * h) / 100)}px` : "8px",
                    opacity: callState === "CONNECTED" ? 1 : 0.3,
                  }}
                />
              ))}
            </div>

            {/* Call Controls */}
            <div className="flex items-center justify-center gap-4 pt-4 border-t border-slate-800">
              <button
                onClick={toggleMute}
                className={`p-3.5 rounded-2xl border transition-colors ${
                  isMuted ? "bg-red-950/50 border-red-800 text-red-300" : "bg-slate-800 border-slate-700 text-slate-300"
                }`}
              >
                {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>

              <button
                onClick={() => {
                  endCall();
                  setActiveRoomId(null);
                  onClose();
                }}
                className="p-4 rounded-2xl bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-950/50 transition-colors"
              >
                <PhoneOff className="w-6 h-6" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
