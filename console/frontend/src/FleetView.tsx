// This project was developed with assistance from AI tools.
import { useCallback, useEffect, useState } from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Label,
  Stack,
  StackItem,
} from "@patternfly/react-core";
import type { FactoryStatus, FleetMessage, FleetStatus } from "./types.js";
import { fetchFleetStatus } from "./api.js";

const POLL_INTERVAL = 5000;

function statusColor(status: string): "green" | "blue" | "orange" | "red" | "grey" {
  if (status === "active") return "green";
  if (status === "idle") return "blue";
  if (status === "rerouting") return "orange";
  if (status === "reverting") return "red";
  if (status === "syncing") return "orange";
  if (status === "synced") return "green";
  return "grey";
}

function AnomalyBar({ score }: { score: number }) {
  const pct = Math.min(score * 100, 100);
  const color = score >= 0.85 ? "#A30000" : score >= 0.5 ? "#F0AB00" : "#3E8635";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          width: 120,
          height: 8,
          backgroundColor: "#E0E0E0",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            backgroundColor: color,
            borderRadius: 4,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span style={{ fontSize: 12, color: "#6A6E73" }}>{score.toFixed(2)}</span>
    </div>
  );
}

function FactoryPanel({ factory }: { factory: FactoryStatus }) {
  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>
          {factory.name}
          <Label
            color={statusColor(factory.argoSyncStatus)}
            isCompact
            style={{ marginLeft: 8 }}
          >
            {factory.argoSyncStatus}
          </Label>
        </CardTitle>
      </CardHeader>
      <CardBody>
        <Stack hasGutter>
          <StackItem>
            <Flex>
              <FlexItem>
                <div style={{ fontSize: 13, color: "#6A6E73" }}>Policy version</div>
                <div className="showcase-policy-pill">{factory.policyVersion}</div>
              </FlexItem>
              <FlexItem>
                <div style={{ fontSize: 13, color: "#6A6E73" }}>Robot</div>
                <div>
                  {factory.robotId}{" "}
                  <Label color={statusColor(factory.robotStatus)} isCompact>
                    {factory.robotStatus}
                  </Label>
                </div>
              </FlexItem>
            </Flex>
          </StackItem>

          <StackItem>
            <div style={{ fontSize: 13, color: "#6A6E73" }}>Anomaly score</div>
            <AnomalyBar score={factory.anomalyScore} />
          </StackItem>

          <StackItem>
            <div style={{ fontSize: 12, color: "#6A6E73" }}>
              Last heartbeat: {factory.lastHeartbeat || "—"}
            </div>
          </StackItem>
        </Stack>
      </CardBody>
    </Card>
  );
}

export function FleetView({ events }: { events: FleetMessage[] }) {
  const [fleet, setFleet] = useState<FleetStatus | null>(null);

  const refresh = useCallback(() => {
    fetchFleetStatus().then(setFleet).catch(() => undefined);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refresh]);

  const anomalyEvents = events.filter(
    (e) =>
      e.topic === "fleet.telemetry" &&
      e.payload &&
      typeof e.payload === "object" &&
      typeof (e.payload as Record<string, unknown>)["anomaly_score"] === "number" &&
      ((e.payload as Record<string, unknown>)["anomaly_score"] as number) >= 0.85,
  );

  return (
    <Stack hasGutter>
      <StackItem>
        <Flex spaceItems={{ default: "spaceItemsLg" }}>
          {fleet?.factories.map((f) => (
            <FlexItem key={f.name} flex={{ default: "flex_1" }}>
              <FactoryPanel factory={f} />
            </FlexItem>
          )) ?? (
            <FlexItem>
              <Card>
                <CardBody>Loading fleet status...</CardBody>
              </Card>
            </FlexItem>
          )}
        </Flex>
      </StackItem>

      {anomalyEvents.length > 0 && (
        <StackItem>
          <Card>
            <CardHeader>
              <CardTitle>
                <Label color="red" isCompact style={{ marginRight: 8 }}>ALERT</Label>
                Anomaly Events
              </CardTitle>
            </CardHeader>
            <CardBody>
              {anomalyEvents.slice(0, 5).map((e, i) => {
                const p = e.payload as Record<string, unknown>;
                return (
                  <div key={i} style={{ fontSize: 13, marginBottom: 4 }}>
                    Robot {String(p["robot_id"])} — anomaly score{" "}
                    {Number(p["anomaly_score"]).toFixed(2)} — {e.receivedAt}
                  </div>
                );
              })}
            </CardBody>
          </Card>
        </StackItem>
      )}
    </Stack>
  );
}
