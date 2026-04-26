// This project was developed with assistance from AI tools.
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { AppStreamer, StreamType, LogLevel, StreamStatus } from "@nvidia/omniverse-webrtc-streaming-library";

interface WebRtcStreamProps {
  signalingServer: string;
  turn?: { urls: string; username: string; credential: string };
  style?: React.CSSProperties;
  onFirstFrame?: () => void;
}

export function WebRtcStream({ signalingServer, turn, style, onFirstFrame }: WebRtcStreamProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<string>("connecting");
  const firstFrameFired = useRef(false);

  useEffect(() => {
    if (!signalingServer) return;

    let terminated = false;

    // The NVIDIA library's configureStreamKitSettings (which injects TURN
    // into the internal ICE config) is NOT exported from the ESM bundle.
    // Monkey-patch RTCPeerConnection so every connection the library creates
    // includes our TURN relay server.  Restored on cleanup.
    const NativeRTCPeerConnection = window.RTCPeerConnection;
    if (turn) {
      const turnServer: RTCIceServer = {
        urls: turn.urls,
        username: turn.username,
        credential: turn.credential,
      };
      const Patched = function (this: RTCPeerConnection, config?: RTCConfiguration) {
        const patched: RTCConfiguration = { ...(config || {}) };
        patched.iceServers = [...(patched.iceServers || []), turnServer];
        patched.iceTransportPolicy = "relay";
        return new NativeRTCPeerConnection(patched);
      } as unknown as typeof RTCPeerConnection;
      Patched.prototype = NativeRTCPeerConnection.prototype;
      Object.setPrototypeOf(Patched, NativeRTCPeerConnection);
      window.RTCPeerConnection = Patched;
    }

    AppStreamer.connect({
      streamSource: StreamType.DIRECT,
      logLevel: LogLevel.DEBUG,
      streamConfig: {
        signalingServer,
        signalingPort: 443,
        forceWSS: true,
        videoElementId: "isaac-remote-video",
        audioElementId: "isaac-remote-audio",
        width: 1920,
        height: 1080,
        fps: 30,
        maxReconnects: 20,
        reconnectDelay: 3000,
        onStart: () => {
          if (terminated) return;
          setStatus("streaming");
          if (!firstFrameFired.current) {
            firstFrameFired.current = true;
            onFirstFrame?.();
          }
        },
        onStop: () => {
          if (terminated) return;
          setStatus("reconnecting");
        },
      },
    }).catch((err) => {
      if (!terminated) {
        console.error("[WebRtcStream] connect failed:", err);
        setStatus("error");
      }
    });

    return () => {
      terminated = true;
      window.RTCPeerConnection = NativeRTCPeerConnection;
      if (AppStreamer.streamStatus !== StreamStatus.none) {
        AppStreamer.terminate().catch(() => undefined);
      }
    };
  }, [signalingServer, turn, onFirstFrame]);

  return (
    <div ref={containerRef} tabIndex={0} style={{ ...style, position: "relative" }}>
      <video
        id="isaac-remote-video"
        autoPlay
        muted
        playsInline
        style={{ width: "100%", height: "100%", objectFit: "contain", background: "#1e1e1e" }}
      />
      <audio id="isaac-remote-audio" autoPlay muted playsInline style={{ display: "none" }} />
      {status !== "streaming" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#ccc",
            fontSize: 14,
            background: "rgba(30,30,30,0.85)",
            pointerEvents: "none",
          }}
        >
          {status === "error" ? "WebRTC connection failed" : "Connecting to Isaac Sim..."}
        </div>
      )}
    </div>
  );
}
