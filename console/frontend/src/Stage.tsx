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

interface StreamConfig {
  signalingServer: string;
  turn: { urls: string; username: string; credential: string } | null;
  mjpegUrl: string;
}

async function fetchStreamConfig(): Promise<StreamConfig> {
  const resp = await fetch("/api/stream/config");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as StreamConfig;
}

export function StageCard(): React.ReactElement {
  const [config, setConfig] = useState<StreamConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const stageFrameRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchStreamConfig()
      .then(setConfig)
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
          <FlexItem><CardTitle>Digital Twin</CardTitle></FlexItem>
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
      <CardBody className="showcase-stage-body">
        <div
          ref={stageFrameRef}
          className="showcase-stage-viewport"
          style={{
            height: isFullscreen ? "100vh" : undefined,
            aspectRatio: isFullscreen ? undefined : "16 / 9",
            color: "#ddd",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
          }}
        >
          {config?.mjpegUrl ? (
            <MjpegCanvas
              src={config.mjpegUrl}
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
