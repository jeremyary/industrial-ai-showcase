// This project was developed with assistance from AI tools.
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Spinner,
} from "@patternfly/react-core";
import ExpandIcon from "@patternfly/react-icons/dist/esm/icons/expand-icon";
import CompressIcon from "@patternfly/react-icons/dist/esm/icons/compress-icon";

import { MjpegCanvas } from "./MjpegCanvas.js";

async function fetchMjpegUrl(): Promise<string> {
  const resp = await fetch("/api/stream/mjpeg-url");
  if (!resp.ok) return "";
  const body = (await resp.json()) as { url?: string };
  return body.url ?? "";
}

export function StageCard(): React.ReactElement {
  const [mjpegUrl, setMjpegUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const stageFrameRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchMjpegUrl()
      .then((url) => {
        if (url) setMjpegUrl(url);
        else setError("MJPEG_URL not configured on backend");
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

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

  return (
    <Card isFullHeight>
      <CardHeader>
        <Flex alignItems={{ default: "alignItemsCenter" }}>
          <FlexItem><CardTitle>Stage</CardTitle></FlexItem>
          <FlexItem align={{ default: "alignRight" }}>
            <Button
              variant="plain"
              aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              onClick={onToggleFullscreen}
              icon={isFullscreen ? <CompressIcon /> : <ExpandIcon />}
            />
          </FlexItem>
        </Flex>
      </CardHeader>
      <CardBody>
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
          {mjpegUrl ? (
            <MjpegCanvas
              src={mjpegUrl}
              style={{ width: "100%", height: "100%", objectFit: "contain", background: "#000" }}
            />
          ) : error ? (
            <span style={{ color: "#c9190b" }}>{error}</span>
          ) : (
            <Flex direction={{ default: "column" }} alignItems={{ default: "alignItemsCenter" }}>
              <FlexItem><Spinner /></FlexItem>
              <FlexItem><span>Connecting to Isaac Sim viewport...</span></FlexItem>
            </Flex>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
