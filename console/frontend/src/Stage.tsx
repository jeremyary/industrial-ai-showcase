// This project was developed with assistance from AI tools.
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";

interface TurnConfig {
  iceServers: RTCIceServer[];
}

async function fetchTurnConfig(): Promise<TurnConfig> {
  const resp = await fetch("/api/turn");
  if (!resp.ok) return { iceServers: [] };
  return (await resp.json()) as TurnConfig;
}

interface WarmState {
  enabled: boolean;
  sessionId: string | null;
}

async function fetchWarmState(): Promise<WarmState> {
  const resp = await fetch("/api/stream/warm");
  if (!resp.ok) return { enabled: false, sessionId: null };
  return (await resp.json()) as WarmState;
}

async function setWarmState(enabled: boolean): Promise<WarmState> {
  const resp = await fetch("/api/stream/warm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!resp.ok) throw new Error(`warm toggle failed: ${resp.status}`);
  return (await resp.json()) as WarmState;
}

// The NVIDIA streaming library doesn't expose an iceServers knob on
// DirectConfig, so we monkey-patch RTCPeerConnection at the window
// level. Every PC created after this runs uses TURN-TLS relay, which
// is how we punch WebRTC media through OpenShift Routes (Route passthrough
// terminates at coturn, coturn relays UDP to Kit intra-cluster).
//
// We also intercept setRemoteDescription to rewrite Kit's SDP: Kit is
// ice-lite and offers `c=IN IP4 0.0.0.0` with no a=candidate: lines, so
// the browser has no remote target to create a TURN permission for.
// Substituting Kit's actual pod IP lets the browser authorize that IP
// on coturn, which in turn lets Kit's UDP media reach the relay.
let kitPodIpGlobal = "";
export function setKitPodIp(ip: string): void {
  kitPodIpGlobal = ip;
}
function patchRtcPeerConnection(iceServers: RTCIceServer[]): void {
  const w = window as unknown as { RTCPeerConnection: typeof RTCPeerConnection };
  const Original = w.RTCPeerConnection;
  if ((Original as unknown as { __turnPatched?: boolean }).__turnPatched) return;
  const OriginalSetRemote = Original.prototype.setRemoteDescription;
  Original.prototype.setRemoteDescription = function (
    this: RTCPeerConnection,
    desc?: RTCSessionDescriptionInit | RTCSessionDescription,
  ): Promise<void> {
    const hasSdp = !!(desc && "sdp" in desc && desc.sdp);
    const hasPodIp = !!kitPodIpGlobal;
    // eslint-disable-next-line no-console
    console.log("[kas-stage] setRemoteDescription intercepted", {
      hasSdp,
      hasPodIp,
      kitPodIp: kitPodIpGlobal,
      type: desc && "type" in desc ? desc.type : undefined,
      sdpPreview: hasSdp ? (desc as RTCSessionDescriptionInit).sdp?.slice(0, 200) : undefined,
    });
    if (desc && "sdp" in desc && desc.sdp && kitPodIpGlobal) {
      let sdp = desc.sdp;
      // Kit is ICE-lite and emits no a=candidate: lines — modern browsers
      // only build remote ICE candidates from a=candidate:, so we synthesize
      // one per media section. The host address is Kit's pod IP (the browser
      // reaches it via TURN relay; coturn can dial the pod-internal IP
      // intra-cluster, and the browser's CreatePermission on that IP is
      // what finally authorizes the media flow).
      sdp = sdp.replace(/c=IN IP4 0\.0\.0\.0/g, `c=IN IP4 ${kitPodIpGlobal}`);
      sdp = sdp.replace(/m=(audio|video|application) (\d+) /g, (match) => match);
      // Inject candidate after each `a=mid:N` line once (prior to any existing
      // a=ice-* or a=setup lines at the media level — placement below mid: is
      // widely tolerated).
      const mediaSections = sdp.split(/\r?\nm=/);
      for (let i = 1; i < mediaSections.length; i++) {
        const section = mediaSections[i] ?? "";
        if (section.includes("a=candidate:")) continue;
        const portMatch = section.match(/^(\S+) (\d+) /);
        const port = portMatch?.[2] ?? "47998";
        const midMatch = section.match(/\r?\na=mid:[^\r\n]*/);
        if (!midMatch) continue;
        const candLines =
          `\r\na=candidate:0 1 UDP 2122260223 ${kitPodIpGlobal} ${port} typ host` +
          `\r\na=end-of-candidates`;
        mediaSections[i] = section.replace(midMatch[0], midMatch[0] + candLines);
      }
      const rewritten = mediaSections.join("\nm=");
      if (rewritten !== desc.sdp) {
        // eslint-disable-next-line no-console
        console.log("[kas-stage] rewrote SDP: c=→", kitPodIpGlobal, "+ a=candidate injected");
        desc = { ...desc, sdp: rewritten } as RTCSessionDescriptionInit;
      }
    }
    return (OriginalSetRemote as (
      this: RTCPeerConnection,
      description?: RTCSessionDescriptionInit | RTCSessionDescription,
    ) => Promise<void>).call(this, desc);
  };
  class Patched extends Original {
    constructor(config?: RTCConfiguration) {
      const merged = {
        ...(config ?? {}),
        iceServers: [...(config?.iceServers ?? []), ...iceServers],
        iceTransportPolicy: "relay" as RTCIceTransportPolicy,
      };
      // eslint-disable-next-line no-console
      console.log("[kas-stage] new RTCPeerConnection", {
        iceServers: merged.iceServers.map((s) => s.urls),
        iceTransportPolicy: merged.iceTransportPolicy,
      });
      super(merged);
    }
  }
  (Patched as unknown as { __turnPatched: boolean }).__turnPatched = true;
  w.RTCPeerConnection = Patched;
}
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Spinner,
  Switch,
} from "@patternfly/react-core";
import ExpandIcon from "@patternfly/react-icons/dist/esm/icons/expand-icon";
import CompressIcon from "@patternfly/react-icons/dist/esm/icons/compress-icon";

import { MjpegCanvas } from "./MjpegCanvas.js";

import { AppStreamer, StreamType } from "@nvidia/omniverse-webrtc-streaming-library";

type PhaseState =
  | "idle"
  | "starting"
  | "waiting-pod"
  | "connecting"
  | "streaming"
  | "error";

interface StreamStartResponse {
  id: string;
  status: { condition: string; status: boolean; message: string };
  ready: boolean;
  signalingHost: string;
  signalingPort: number;
  mediaHost: string;
  mediaPort: number;
  mjpegUrl?: string;
}

async function startStream(): Promise<StreamStartResponse> {
  const resp = await fetch("/api/stream/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!resp.ok) throw new Error(`start failed: ${resp.status}`);
  return (await resp.json()) as StreamStartResponse;
}

async function pollUntilPodReady(sessionId: string, timeoutMs: number): Promise<StreamStartResponse> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const resp = await fetch(`/api/stream/${sessionId}`);
    if (resp.ok) {
      const data = (await resp.json()) as StreamStartResponse;
      if (data.ready) return data;
      const cond = data.status.condition?.toLowerCase();
      if (cond === "failed") throw new Error(`session ${sessionId} failed: ${data.status.message}`);
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  throw new Error(`timed out waiting for ${sessionId}`);
}

function destroyStream(sessionId: string): void {
  // Fire-and-forget; best effort cleanup.
  void fetch(`/api/stream/${sessionId}`, { method: "DELETE" });
}

// `fullKit` mode renders the interactive Kit WebRTC stream (current Ragnarok
// path — coturn, SDP rewriting, etc). `mjpeg` mode renders the simple
// viewport JPEG stream from viewport_mjpeg.py, which doesn't touch WebRTC
// at all. mjpeg is the default because it's reliable; fullKit is the
// power-user escape hatch opened in a separate tab via `?kit=1`.
type StageMode = "mjpeg" | "fullKit";

export function StageCard(): React.ReactElement {
  const mode: StageMode =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("kit") === "1"
      ? "fullKit"
      : "mjpeg";
  const [phase, setPhase] = useState<PhaseState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [session, setSession] = useState<StreamStartResponse | null>(null);
  const [warmEnabled, setWarmEnabled] = useState(false);
  const [warmBusy, setWarmBusy] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mjpegUrl, setMjpegUrl] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const stageFrameRef = useRef<HTMLDivElement | null>(null);
  const connectedRef = useRef(false);

  // MJPEG mode: on mount, call /api/stream/start (warm-pool returns the
  // already-booted session immediately). Once the session is ready, plug
  // its mjpegUrl into the <img> tag.
  useEffect(() => {
    if (mode !== "mjpeg") return;
    let cancelled = false;
    const attach = async (): Promise<void> => {
      try {
        const start = await startStream();
        if (cancelled) return;
        setSession(start);
        if (start.ready && start.mjpegUrl) {
          setMjpegUrl(start.mjpegUrl);
          setPhase("streaming");
          return;
        }
        setPhase("waiting-pod");
        const ready = await pollUntilPodReady(start.id, 600_000);
        if (cancelled) return;
        if (ready.mjpegUrl) {
          setMjpegUrl(ready.mjpegUrl);
          setPhase("streaming");
        }
      } catch (e) {
        if (!cancelled) {
          setErrorMsg(e instanceof Error ? e.message : String(e));
          setPhase("error");
        }
      }
    };
    void attach();
    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => {
    const onChange = (): void => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const onToggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void stageFrameRef.current?.requestFullscreen();
    }
  }, []);

  useEffect(() => {
    fetchWarmState()
      .then((s) => setWarmEnabled(s.enabled))
      .catch(() => undefined);
  }, []);

  const onToggleWarm = useCallback(async (checked: boolean) => {
    setWarmBusy(true);
    try {
      const s = await setWarmState(checked);
      setWarmEnabled(s.enabled);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setWarmBusy(false);
    }
  }, []);

  const onStart = useCallback(async () => {
    setErrorMsg(null);
    setPhase("starting");
    try {
      const turn = await fetchTurnConfig();
      if (turn.iceServers.length) patchRtcPeerConnection(turn.iceServers);
      const start = await startStream();
      setSession(start);
      setPhase("waiting-pod");
      const readySession = await pollUntilPodReady(start.id, 300_000);
      // mediaHost is Kit's actual pod IP (populated once the Kit pod is
      // scheduled); the setRemoteDescription interceptor uses it to
      // rewrite c=0.0.0.0 in Kit's SDP offer so the browser has a real
      // target to CreatePermission for on coturn.
      setKitPodIp(readySession.mediaHost);
      setPhase("connecting");
      await AppStreamer.connect({
        streamConfig: {
          videoElementId: "remote-video",
          audioElementId: "remote-audio",
          authenticate: false,
          maxReconnects: 10,
          signalingServer: start.signalingHost,
          signalingPort: start.signalingPort,
          mediaServer: start.mediaHost,
          mediaPort: start.mediaPort,
          backendUrl: `${window.location.origin}/api/stream`,
          sessionId: start.id,
          nativeTouchEvents: true,
          width: 1920,
          height: 1080,
          fps: 60,
          onStart: (msg) => {
            const status = String(msg?.status ?? "");
            // The library fires onStart on every reconnect attempt — status
            // is "warning" during retries, "success" only when a peer
            // connection is actually established.
            if (status === "success") setPhase("streaming");
            else if (status === "error") {
              setErrorMsg(String(msg?.info ?? "stream error"));
              setPhase("error");
            }
            // "warning" / "inProgress" → leave phase at "connecting"
          },
          onUpdate: () => undefined,
          onCustomEvent: () => undefined,
          onStop: () => setPhase("idle"),
          onTerminate: () => setPhase("idle"),
        },
        streamSource: StreamType.DIRECT,
      });
      connectedRef.current = true;
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setPhase("error");
    }
  }, []);

  const onStop = useCallback(() => {
    if (session) destroyStream(session.id);
    setSession(null);
    setPhase("idle");
    connectedRef.current = false;
  }, [session]);

  useEffect(() => {
    return () => {
      if (session) destroyStream(session.id);
    };
  }, [session]);

  const showVideo = phase === "connecting" || phase === "streaming";
  const openFullKit = useCallback(() => {
    window.open(`${window.location.origin}/?kit=1`, "_blank", "noopener");
  }, []);

  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>Stage</CardTitle>
      </CardHeader>
      <CardBody>
        <Flex direction={{ default: "column" }} spaceItems={{ default: "spaceItemsSm" }}>
          <FlexItem>
            <Flex spaceItems={{ default: "spaceItemsSm" }} alignItems={{ default: "alignItemsCenter" }}>
              {mode === "fullKit" ? (
                <>
                  <FlexItem>
                    <Button
                      variant="primary"
                      onClick={onStart}
                      isDisabled={phase !== "idle" && phase !== "error"}
                    >
                      Start Isaac Sim
                    </Button>
                  </FlexItem>
                  <FlexItem>
                    <Button variant="secondary" onClick={onStop} isDisabled={!session}>
                      Stop
                    </Button>
                  </FlexItem>
                  <FlexItem>
                    <PhaseBadge phase={phase} session={session?.id ?? null} />
                  </FlexItem>
                </>
              ) : (
                <>
                  <FlexItem>
                    <PhaseBadge phase={phase} session={session?.id ?? null} />
                  </FlexItem>
                  <FlexItem>
                    <Button variant="link" onClick={openFullKit}>
                      Open full Isaac Sim →
                    </Button>
                  </FlexItem>
                </>
              )}
              <FlexItem align={{ default: "alignRight" }}>
                <Flex spaceItems={{ default: "spaceItemsMd" }} alignItems={{ default: "alignItemsCenter" }}>
                  <FlexItem>
                    <Switch
                      id="warm-pool-toggle"
                      label="Keep Isaac Sim warm"
                      isChecked={warmEnabled}
                      onChange={(_e, checked) => void onToggleWarm(checked)}
                      isDisabled={warmBusy}
                    />
                  </FlexItem>
                  <FlexItem>
                    <Button
                      variant="plain"
                      aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
                      onClick={onToggleFullscreen}
                      icon={isFullscreen ? <CompressIcon /> : <ExpandIcon />}
                    />
                  </FlexItem>
                </Flex>
              </FlexItem>
            </Flex>
            {errorMsg ? (
              <div style={{ color: "#c9190b", marginTop: 6 }}>{errorMsg}</div>
            ) : null}
          </FlexItem>
          <FlexItem>
            <div
              ref={stageFrameRef}
              style={{
                height: isFullscreen ? "100vh" : "min(85vh, 1200px)",
                minHeight: 560,
                background: "linear-gradient(135deg, #1e1e1e, #3a3a3a)",
                color: "#ddd",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: isFullscreen ? 0 : 6,
                overflow: "hidden",
                position: "relative",
              }}
            >
              {mode === "mjpeg" ? (
                mjpegUrl ? (
                  <MjpegCanvas
                    src={mjpegUrl}
                    style={{ width: "100%", height: "100%", objectFit: "contain", background: "#000" }}
                  />
                ) : (
                  <PlaceholderContent phase={phase} />
                )
              ) : (
                <>
                  <video
                    id="remote-video"
                    ref={videoRef}
                    autoPlay
                    playsInline
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "contain",
                      display: showVideo ? "block" : "none",
                      background: "#000",
                    }}
                  />
                  <audio id="remote-audio" ref={audioRef} autoPlay style={{ display: "none" }} />
                  {!showVideo ? <PlaceholderContent phase={phase} /> : null}
                </>
              )}
            </div>
          </FlexItem>
        </Flex>
      </CardBody>
    </Card>
  );
}

function PhaseBadge({ phase, session }: { phase: PhaseState; session: string | null }): React.ReactElement {
  const label: Record<PhaseState, string> = {
    idle: "idle",
    starting: "requesting session",
    "waiting-pod": "Kit spawning",
    connecting: "connecting WebRTC",
    streaming: "streaming",
    error: "error",
  };
  return (
    <span style={{ fontSize: 12, color: "#666" }}>
      {label[phase]}
      {session ? ` · ${session.slice(0, 8)}` : ""}
    </span>
  );
}

function PlaceholderContent({ phase }: { phase: PhaseState }): React.ReactElement {
  if (phase === "starting" || phase === "waiting-pod") {
    return (
      <Flex direction={{ default: "column" }} alignItems={{ default: "alignItemsCenter" }}>
        <FlexItem>
          <Spinner />
        </FlexItem>
        <FlexItem>
          <span>
            {phase === "starting"
              ? "Asking the session manager…"
              : "Isaac Sim warm-up (Kit boot ~60–90s)…"}
          </span>
        </FlexItem>
      </Flex>
    );
  }
  return <span>Press Start to launch a warehouse simulation session.</span>;
}
