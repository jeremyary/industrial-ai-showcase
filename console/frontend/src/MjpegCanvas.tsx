// This project was developed with assistance from AI tools.
//
// Consumes a multipart/x-mixed-replace MJPEG stream via `fetch()` +
// ReadableStream and draws each JPEG frame to a <canvas>. Doing the parse
// in JS (rather than letting the browser handle it via <img>) dodges
// Firefox's quiet behavior of periodically cycling long-running MJPEG
// streams attached to <img>, which manifests as ~2 second blackouts every
// 60–90 seconds. The stream itself and the server are untouched — just the
// consumer changes.
//
// Wire format our viewport_mjpeg.py server emits per frame:
//   --frame\r\n
//   Content-Type: image/jpeg\r\n
//   Content-Length: <N>\r\n
//   \r\n
//   <N bytes of JPEG>
//   \r\n
//
// We rely on Content-Length to avoid searching for the boundary inside
// JPEG payload bytes (which can contain `--frame` or any byte pattern).

import type React from "react";
import { useEffect, useRef } from "react";

interface MjpegCanvasProps {
  src: string;
  style?: React.CSSProperties;
  // Called the first time a frame successfully renders — caller can use
  // it to hide a placeholder.
  onFirstFrame?: () => void;
}

// Search for a byte sequence in a Uint8Array. Returns index or -1.
function indexOfBytes(haystack: Uint8Array, needle: Uint8Array, from = 0): number {
  const end = haystack.length - needle.length;
  outer: for (let i = from; i <= end; i++) {
    for (let j = 0; j < needle.length; j++) {
      if (haystack[i + j] !== needle[j]) continue outer;
    }
    return i;
  }
  return -1;
}

const BOUNDARY = new TextEncoder().encode("--frame");
const DOUBLE_CRLF = new TextEncoder().encode("\r\n\r\n");

export function MjpegCanvas({ src, style, onFirstFrame }: MjpegCanvasProps): React.ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    let firstFrameFired = false;

    const draw = (bitmap: ImageBitmap): void => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      // Match canvas resolution to the incoming frame exactly — otherwise
      // the browser scales every repaint and CPU use climbs.
      if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(bitmap, 0, 0);
      bitmap.close();
      if (!firstFrameFired) {
        firstFrameFired = true;
        onFirstFrame?.();
      }
    };

    const run = async (): Promise<void> => {
      while (!cancelled) {
        try {
          const resp = await fetch(src, { cache: "no-store", credentials: "omit" });
          if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);
          reader = resp.body.getReader();
          let buffer = new Uint8Array(0);
          while (!cancelled) {
            const { value, done } = await reader.read();
            if (done) break;
            if (value) {
              const merged = new Uint8Array(buffer.length + value.length);
              merged.set(buffer, 0);
              merged.set(value, buffer.length);
              buffer = merged;
            }
            // Parse as many complete frames from the buffer as possible.
            while (!cancelled) {
              const boundaryAt = indexOfBytes(buffer, BOUNDARY);
              if (boundaryAt < 0) break;
              // Find end-of-headers after boundary.
              const headerEnd = indexOfBytes(buffer, DOUBLE_CRLF, boundaryAt);
              if (headerEnd < 0) break;
              const headerText = new TextDecoder("ascii").decode(
                buffer.subarray(boundaryAt, headerEnd),
              );
              const lengthMatch = /Content-Length:\s*(\d+)/i.exec(headerText);
              if (!lengthMatch) {
                // Corrupted / unexpected — resync past this boundary.
                buffer = buffer.subarray(boundaryAt + BOUNDARY.length);
                continue;
              }
              const frameLen = parseInt(lengthMatch[1]!, 10);
              const frameStart = headerEnd + DOUBLE_CRLF.length;
              const frameEnd = frameStart + frameLen;
              if (buffer.length < frameEnd) break; // need more bytes
              const jpegBytes = buffer.subarray(frameStart, frameEnd);
              try {
                const bitmap = await createImageBitmap(new Blob([jpegBytes], { type: "image/jpeg" }));
                if (!cancelled) draw(bitmap);
              } catch {
                // Partial/corrupted JPEG — skip this frame.
              }
              // Advance past trailing CRLF of this frame (if present).
              let consumeTo = frameEnd;
              if (buffer[consumeTo] === 0x0d && buffer[consumeTo + 1] === 0x0a) {
                consumeTo += 2;
              }
              buffer = buffer.subarray(consumeTo);
            }
          }
        } catch {
          // network blip or server-initiated close; fall through to reconnect
        } finally {
          reader?.cancel().catch(() => undefined);
          reader = null;
        }
        if (cancelled) break;
        // Brief backoff before reconnecting so we don't hammer a down server.
        await new Promise((r) => setTimeout(r, 500));
      }
    };

    void run();
    return () => {
      cancelled = true;
      reader?.cancel().catch(() => undefined);
    };
  }, [src, onFirstFrame]);

  return <canvas ref={canvasRef} style={style} />;
}
