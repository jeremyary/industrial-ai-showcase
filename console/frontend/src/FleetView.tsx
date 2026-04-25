// This project was developed with assistance from AI tools.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Label,
  ProgressStepper,
  ProgressStep,
  Spinner,
  Stack,
  StackItem,
} from "@patternfly/react-core";
import type {
  AnomalyPoint,
  ButtonDef,
  FactoryStatus,
  FleetMessage,
  FleetStatus,
  ScenarioDetail,
} from "./types.js";
import { executeAction, fetchFleetStatus, fetchScenarioDetail } from "./api.js";

const POLL_INTERVAL = 5000;

const DEMO_STEPS = [
  { id: "promote", label: "Promote v1.4", action: "promote-policy" },
  { id: "anomaly", label: "Trigger Anomaly", action: "trigger-anomaly" },
  { id: "reset", label: "Reset Demo", action: "reset-fleet-demo" },
];

function phaseToStepIndex(phase: string): number {
  if (phase === "promoted") return 1;
  if (phase === "anomaly-detected" || phase === "rolled-back") return 2;
  return 0;
}

function stepVariant(
  stepIdx: number,
  currentIdx: number,
): "success" | "info" | "pending" | "danger" {
  if (stepIdx < currentIdx) return "success";
  if (stepIdx === currentIdx) return "info";
  return "pending";
}

function statusColor(
  status: string,
): "green" | "blue" | "orange" | "red" | "grey" {
  if (status === "active") return "green";
  if (status === "idle") return "blue";
  if (status === "rerouting") return "orange";
  if (status === "reverting") return "red";
  if (status === "syncing") return "orange";
  if (status === "synced") return "green";
  return "grey";
}

function AnomalySparkline({ history }: { history: AnomalyPoint[] }) {
  if (history.length === 0) {
    return (
      <span style={{ fontSize: 12, color: "#6A6E73" }}>no data</span>
    );
  }

  const w = 120;
  const h = 24;
  const latest = history[history.length - 1].v;
  const points = history
    .map((p, i) => {
      const x = (i / Math.max(history.length - 1, 1)) * w;
      const y = h - p.v * h;
      return `${x},${y}`;
    })
    .join(" ");

  const color = latest >= 0.85 ? "#A30000" : latest >= 0.5 ? "#F0AB00" : "#3E8635";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <svg width={w} height={h} style={{ display: "block" }}>
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
        />
      </svg>
      <span style={{ fontSize: 12, color, fontWeight: 600 }}>
        {latest.toFixed(2)}
      </span>
    </div>
  );
}

function FactoryPanel({ factory }: { factory: FactoryStatus }) {
  const prevVersion = useRef(factory.policyVersion);
  const [pillClass, setPillClass] = useState("");

  useEffect(() => {
    if (prevVersion.current !== factory.policyVersion) {
      const cls =
        factory.policyVersion < prevVersion.current
          ? "showcase-policy-pill--reverting"
          : "showcase-policy-pill--promoting";
      setPillClass(cls);
      prevVersion.current = factory.policyVersion;
      const timer = setTimeout(() => setPillClass(""), 600);
      return () => clearTimeout(timer);
    }
  }, [factory.policyVersion]);

  const argoClass =
    factory.argoSyncStatus === "syncing" || factory.argoSyncStatus === "reverting"
      ? "showcase-argo-pulse"
      : "";

  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>
          {factory.name}
          <Label
            color={statusColor(factory.argoSyncStatus)}
            isCompact
            className={argoClass}
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
                <div style={{ fontSize: 13, color: "#6A6E73" }}>
                  Policy version
                </div>
                <div className={`showcase-policy-pill ${pillClass}`}>
                  {factory.policyVersion}
                </div>
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
            <AnomalySparkline history={[{ t: Date.now(), v: factory.anomalyScore }]} />
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
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const refresh = useCallback(() => {
    fetchFleetStatus().then(setFleet).catch(() => undefined);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    fetchScenarioDetail("fleet-demo").then(setScenario).catch(() => undefined);
  }, []);

  useEffect(() => {
    const hasFleetEvent = events.some(
      (e) => e.topic === "fleet.events" || e.topic === "fleet.telemetry",
    );
    if (hasFleetEvent) refresh();
  }, [events, refresh]);

  const onStepAction = useCallback(
    async (action: string) => {
      if (!scenario) return;
      const btn = scenario.buttons.find((b: ButtonDef) => b.action === action);
      if (!btn) return;
      setActionBusy(action);
      try {
        await executeAction(btn.action, btn.params);
        setTimeout(refresh, 500);
      } catch {
        // action failed — poll will show current state
      } finally {
        setActionBusy(null);
      }
    },
    [scenario, refresh],
  );

  const currentStepIdx = phaseToStepIndex(fleet?.demoPhase ?? "idle");

  return (
    <Stack hasGutter>
      <StackItem>
        <Card>
          <CardHeader>
            <CardTitle>Fleet Demo</CardTitle>
          </CardHeader>
          <CardBody>
            <ProgressStepper>
              {DEMO_STEPS.map((step, i) => (
                <ProgressStep
                  key={step.id}
                  id={step.id}
                  titleId={`step-${step.id}`}
                  variant={stepVariant(i, currentStepIdx)}
                  description={
                    i === currentStepIdx ? (
                      <Button
                        variant="link"
                        isInline
                        isLoading={actionBusy === step.action}
                        isDisabled={actionBusy !== null}
                        onClick={() => void onStepAction(step.action)}
                        style={{ fontSize: 13 }}
                      >
                        {step.label}
                      </Button>
                    ) : undefined
                  }
                >
                  {step.label}
                </ProgressStep>
              ))}
            </ProgressStepper>
          </CardBody>
        </Card>
      </StackItem>

      <StackItem>
        <Flex spaceItems={{ default: "spaceItemsLg" }}>
          {fleet?.factories.map((f) => (
            <FlexItem key={f.name} flex={{ default: "flex_1" }}>
              <FactoryPanel factory={f} />
            </FlexItem>
          )) ?? (
            <FlexItem>
              <Card>
                <CardBody>
                  <Spinner size="md" /> Loading fleet status...
                </CardBody>
              </Card>
            </FlexItem>
          )}
        </Flex>
      </StackItem>

      {fleet && fleet.anomalyHistory.length > 0 && (
        <StackItem>
          <Card>
            <CardHeader>
              <CardTitle>Anomaly History</CardTitle>
            </CardHeader>
            <CardBody>
              <AnomalySparkline history={fleet.anomalyHistory} />
            </CardBody>
          </Card>
        </StackItem>
      )}
    </Stack>
  );
}
