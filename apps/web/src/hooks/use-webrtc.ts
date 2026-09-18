"use client";

import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL } from "@/lib/constants";

export function useWebRTC(roomId?: string) {
  const [callState, setCallState] = useState<"IDLE" | "CONNECTING" | "CONNECTED" | "ENDED" | "FAILED">("IDLE");
  const [isMuted, setIsMuted] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  const startCall = async (targetRoomId: string) => {
    setCallState("CONNECTING");
    setDuration(0);

    try {
      // 1. Get microphone audio stream
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      localStreamRef.current = stream;

      // Set up AudioContext for volume visualization
      try {
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const updateVolume = () => {
          if (localStreamRef.current && audioCtx.state === "running") {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            setAudioLevel(Math.min(100, Math.round((sum / dataArray.length / 255) * 100 * 2.5)));
            requestAnimationFrame(updateVolume);
          }
        };
        updateVolume();
      } catch {}

      // 2. Setup RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }, { urls: "stun:stun1.l.google.com:19302" }],
      });
      peerConnectionRef.current = pc;

      // Add local audio tracks to PeerConnection
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));

      // Play remote audio stream when received
      pc.ontrack = (event) => {
        if (!remoteAudioRef.current) {
          const audio = new Audio();
          audio.autoplay = true;
          remoteAudioRef.current = audio;
        }
        remoteAudioRef.current.srcObject = event.streams[0];
      };

      pc.onicecandidate = (event) => {
        if (event.candidate && socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(
            JSON.stringify({
              type: "ice-candidate",
              candidate: event.candidate,
            })
          );
        }
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "connected") {
          setCallState("CONNECTED");
          startTimer();
        } else if (pc.connectionState === "disconnected" || pc.connectionState === "failed") {
          endCall();
        }
      };

      // 3. Setup WebSocket Signaling connection
      const token = localStorage.getItem("restoops_access_token");
      const wsUrl = `${WS_BASE_URL}/webrtc/${targetRoomId}?token=${encodeURIComponent(token || "")}`;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = async () => {
        // Create WebRTC Offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        ws.send(
          JSON.stringify({
            type: "offer",
            sdp: offer.sdp,
          })
        );
      };

      ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "answer" && pc) {
            await pc.setRemoteDescription(new RTCSessionDescription({ type: "answer", sdp: data.sdp }));
          } else if (data.type === "ice-candidate" && pc) {
            await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
          } else if (data.type === "call-ended") {
            endCall();
          }
        } catch {}
      };

      ws.onclose = () => {
        if (callState === "CONNECTED" || callState === "CONNECTING") {
          endCall();
        }
      };
    } catch (err) {
      console.error("Failed to start WebRTC call:", err);
      setCallState("FAILED");
    }
  };

  const startTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setDuration((prev) => prev + 1);
    }, 1000);
  };

  const toggleMute = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = !track.enabled;
      });
      setIsMuted((prev) => !prev);
    }
  };

  const endCall = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }

    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    if (socketRef.current) {
      if (socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: "call-ended" }));
      }
      socketRef.current.close();
      socketRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setCallState("ENDED");
    setAudioLevel(0);
  };

  useEffect(() => {
    if (roomId) {
      startCall(roomId);
    }
    return () => {
      endCall();
    };
  }, [roomId]);

  return {
    callState,
    isMuted,
    duration,
    audioLevel,
    startCall,
    endCall,
    toggleMute,
  };
}
