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

export function MjpegCanvas({ src, style, onFirstFrame }: MjpegCanvasProps): React.ReactElement {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const hlsUrl = src
      .replace(/\/stream\.mjpg$/, "/hls/stream.m3u8")
      .replace(/\/stream$/, "/hls/stream.m3u8")
      .replace(/\/frame\.jpg$/, "/hls/stream.m3u8");

    let firedFirst = false;
    const onPlaying = (): void => {
      if (!firedFirst) {
        firedFirst = true;
        onFirstFrame?.();
      }
    };
    video.addEventListener("playing", onPlaying);

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 1,
        liveMaxLatencyDurationCount: 3,
        liveDurationInfinity: true,
        lowLatencyMode: true,
        enableWorker: true,
        backBufferLength: 0,
      });
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        void video.play().catch(() => undefined);
      });
      return () => {
        video.removeEventListener("playing", onPlaying);
        hls.destroy();
      };
    }

    // Safari supports HLS natively.
    video.src = hlsUrl;
    void video.play().catch(() => undefined);
    return () => {
      video.removeEventListener("playing", onPlaying);
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
