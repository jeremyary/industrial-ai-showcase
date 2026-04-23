// This project was developed with assistance from AI tools.
//
// HLS video player for the Isaac Sim viewport stream. The viewport
// capture pipeline on Isaac Sim encodes frames with NVENC (GPU H.264)
// and serves HLS segments. This component plays them via hls.js for
// smooth, hardware-decoded video in the browser.

import type React from "react";
import { useEffect, useRef } from "react";
import Hls from "hls.js";

interface MjpegCanvasProps {
  src: string;
  style?: React.CSSProperties;
  onFirstFrame?: () => void;
}

const DIAG_PREFIX = "[hls_diag]";
const DIAG_INTERVAL_MS = 10_000;

function logDiag(...args: unknown[]): void {
  console.log(DIAG_PREFIX, new Date().toISOString(), ...args);
}

function getBufferedInfo(video: HTMLVideoElement): { bufferedSec: number; bufferedRanges: string } {
  const buf = video.buffered;
  const ranges: string[] = [];
  let total = 0;
  for (let i = 0; i < buf.length; i++) {
    const s = buf.start(i);
    const e = buf.end(i);
    ranges.push(`${s.toFixed(2)}-${e.toFixed(2)}`);
    total += e - s;
  }
  return { bufferedSec: total, bufferedRanges: ranges.join(", ") || "none" };
}

export function MjpegCanvas({ src, style, onFirstFrame }: MjpegCanvasProps): React.ReactElement {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const hlsUrl = src
      .replace(/\/stream\.mjpg$/, "/hls/stream.m3u8")
      .replace(/\/stream$/, "/hls/stream.m3u8")
      .replace(/\/frame\.jpg$/, "/hls/stream.m3u8");

    logDiag("init", { hlsUrl, hlsSupported: Hls.isSupported() });

    let firedFirst = false;
    const onPlaying = (): void => {
      logDiag("EVENT playing", { currentTime: video.currentTime, readyState: video.readyState });
      if (!firedFirst) {
        firedFirst = true;
        onFirstFrame?.();
      }
    };
    video.addEventListener("playing", onPlaying);

    const onWaiting = (): void => {
      const { bufferedSec, bufferedRanges } = getBufferedInfo(video);
      logDiag("EVENT waiting (stall)", {
        currentTime: video.currentTime,
        readyState: video.readyState,
        paused: video.paused,
        bufferedSec,
        bufferedRanges,
      });
    };
    video.addEventListener("waiting", onWaiting);

    const onStalled = (): void => {
      logDiag("EVENT stalled", { currentTime: video.currentTime, readyState: video.readyState });
    };
    video.addEventListener("stalled", onStalled);

    const onError = (): void => {
      const err = video.error;
      logDiag("EVENT error", { code: err?.code, message: err?.message });
    };
    video.addEventListener("error", onError);

    const onPause = (): void => {
      logDiag("EVENT pause", { currentTime: video.currentTime });
    };
    video.addEventListener("pause", onPause);

    let diagTimer: ReturnType<typeof setInterval> | null = null;
    let fragLoadCount = 0;
    let fragBufferedCount = 0;
    let levelLoadCount = 0;
    let hlsErrorCount = 0;

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 4,
        liveMaxLatencyDurationCount: 8,
        liveDurationInfinity: true,
        lowLatencyMode: false,
        enableWorker: true,
        backBufferLength: 0,
      });

      hls.on(Hls.Events.FRAG_LOADED, (_event, data) => {
        fragLoadCount++;
        if (fragLoadCount <= 3 || fragLoadCount % 50 === 0) {
          logDiag("FRAG_LOADED", {
            sn: data.frag.sn,
            duration: data.frag.duration?.toFixed(2),
            loadTimeMs: data.frag.stats?.loading
              ? (data.frag.stats.loading.end - data.frag.stats.loading.start).toFixed(0)
              : "?",
            totalLoaded: fragLoadCount,
          });
        }
      });

      hls.on(Hls.Events.FRAG_BUFFERED, (_event, data) => {
        fragBufferedCount++;
        if (fragBufferedCount <= 3 || fragBufferedCount % 50 === 0) {
          const { bufferedSec } = getBufferedInfo(video);
          logDiag("FRAG_BUFFERED", {
            sn: data.frag.sn,
            bufferedSec: bufferedSec.toFixed(2),
            totalBuffered: fragBufferedCount,
          });
        }
      });

      hls.on(Hls.Events.LEVEL_LOADED, (_event, data) => {
        levelLoadCount++;
        logDiag("LEVEL_LOADED", {
          fragments: data.details.fragments.length,
          live: data.details.live,
          targetduration: data.details.targetduration,
          totalduration: data.details.totalduration?.toFixed(2),
          totalLoaded: levelLoadCount,
        });
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        hlsErrorCount++;
        logDiag("HLS ERROR", {
          type: data.type,
          details: data.details,
          fatal: data.fatal,
          reason: data.reason,
          totalErrors: hlsErrorCount,
        });
        if (data.fatal) {
          logDiag("FATAL error — attempting recovery", { type: data.type });
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            hls.startLoad();
          } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            hls.recoverMediaError();
          }
        }
      });

      hls.on(Hls.Events.BUFFER_APPENDING, () => {
        // high frequency — only log at trace level
      });

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        logDiag("MANIFEST_PARSED — starting playback");
        void video.play().catch(() => undefined);
      });

      diagTimer = setInterval(() => {
        const { bufferedSec, bufferedRanges } = getBufferedInfo(video);
        const latency = hls.latency ?? -1;
        const targetLatency = hls.targetLatency ?? -1;
        const drift = hls.drift ?? 0;
        const liveSyncPosition = hls.liveSyncPosition ?? -1;
        logDiag("PERIODIC", {
          currentTime: video.currentTime.toFixed(2),
          readyState: video.readyState,
          paused: video.paused,
          playbackRate: video.playbackRate,
          bufferedSec: bufferedSec.toFixed(2),
          bufferedRanges,
          latency: latency.toFixed(2),
          targetLatency: targetLatency.toFixed(2),
          drift: drift.toFixed(4),
          liveSyncPosition: liveSyncPosition.toFixed(2),
          fragLoaded: fragLoadCount,
          fragBuffered: fragBufferedCount,
          levelLoaded: levelLoadCount,
          errors: hlsErrorCount,
        });
      }, DIAG_INTERVAL_MS);

      hls.loadSource(hlsUrl);
      hls.attachMedia(video);

      return () => {
        video.removeEventListener("playing", onPlaying);
        video.removeEventListener("waiting", onWaiting);
        video.removeEventListener("stalled", onStalled);
        video.removeEventListener("error", onError);
        video.removeEventListener("pause", onPause);
        if (diagTimer) clearInterval(diagTimer);
        logDiag("cleanup — destroying hls instance");
        hls.destroy();
      };
    }

    // Safari supports HLS natively.
    video.src = hlsUrl;
    void video.play().catch(() => undefined);
    return () => {
      video.removeEventListener("playing", onPlaying);
      video.removeEventListener("waiting", onWaiting);
      video.removeEventListener("stalled", onStalled);
      video.removeEventListener("error", onError);
      video.removeEventListener("pause", onPause);
      if (diagTimer) clearInterval(diagTimer);
      video.src = "";
    };
  }, [src, onFirstFrame]);

  return (
    <video
      ref={videoRef}
      autoPlay
      muted
      playsInline
      style={{ ...style, objectFit: "contain", background: "#1e1e1e" }}
    />
  );
}
