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
  DemoLinks,
  FactoryStatus,
  FleetMessage,
  FleetStatus,
  ScenarioDetail,
} from "./types.js";
import { executeAction, fetchFleetStatus, fetchScenarioDetail } from "./api.js";

const POLL_INTERVAL = 5000;

interface DemoStep {
  id: string;
  label: string;
  action: string;
  preText: string;
  activeText: string;
  doneText: string;
  linkKeys: (keyof DemoLinks)[];
  linkLabels: string[];
}

const DEMO_STEPS: DemoStep[] = [
  {
    id: "promote",
    label: "Promote v1.4",
    action: "promote-policy",
    preText: "Push the new VLA policy version to Factory A via GitOps.",
    activeText: "Argo CD is syncing the change to fleet-manager. This is a real GitOps deployment.",
    doneText: "Factory A is now running v1.4.",
    linkKeys: ["argoFleetManager", "ocpFleetManager"],
    linkLabels: ["Argo CD: fleet-manager", "OpenShift: fleet-manager pods"],
  },
  {
    id: "anomaly",
    label: "Trigger Anomaly",
    action: "trigger-anomaly",
    preText: "Inject a high anomaly score to test automatic rollback.",
    activeText: "Anomaly detected — auto-rollback reverting Factory A to v1.3.",
    doneText: "Factory A rolled back to v1.3 automatically.",
    linkKeys: ["argoFleetManager"],
    linkLabels: ["Argo CD: rollback sync"],
  },
  {
    id: "reset",
    label: "Reset Demo",
    action: "reset-fleet-demo",
    preText: "Return all systems to baseline.",
    activeText: "Resetting...",
    doneText: "Demo reset to baseline.",
    linkKeys: [],
    linkLabels: [],
  },
];

function phaseToStepIndex(phase: string): number {
  if (phase === "promoted") return 1;
  if (phase === "anomaly-detected" || phase === "rolled-back") return 2;
  return 0;
}

function isPhaseTransitioning(phase: string): boolean {
  return phase === "promoted" || phase === "anomaly-detected";
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

function ProofLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="showcase-proof-link"
    >
      {label} ↗
    </a>
  );
}

function StepDescription({
  step,
  isActive,
  isDone,
  isBusy,
  isTransitioning,
  links,
  onAction,
}: {
  step: DemoStep;
  isActive: boolean;
  isDone: boolean;
  isBusy: boolean;
  isTransitioning: boolean;
  links: DemoLinks | null;
  onAction: () => void;
}) {
  if (!isActive && !isDone) return null;

  if (isDone) {
    return (
      <div className="showcase-step-guidance">
        <span style={{ color: "#3E8635" }}>{step.doneText}</span>
      </div>
    );
  }

  const showLinks = isTransitioning && links && step.linkKeys.length > 0;

  return (
    <div className="showcase-step-guidance">
      <div style={{ marginBottom: 8 }}>
        {isTransitioning ? step.activeText : step.preText}
      </div>
      {!isTransitioning && (
        <Button
          variant="primary"
          size="sm"
          isLoading={isBusy}
          isDisabled={isBusy}
          onClick={onAction}
        >
          {step.label}
        </Button>
      )}
      {showLinks && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: "#6A6E73", marginBottom: 4 }}>
            Verify it's real:
          </div>
          <Flex spaceItems={{ default: "spaceItemsMd" }}>
            {step.linkKeys.map((key, i) => (
              <FlexItem key={key}>
                <ProofLink href={links[key]} label={step.linkLabels[i] ?? key} />
              </FlexItem>
            ))}
          </Flex>
        </div>
      )}
    </div>
  );
}

function AnomalyBar({ score }: { score: number }) {
  const pct = Math.min(score * 100, 100);
  const color =
    score >= 0.85 ? "#A30000" : score >= 0.5 ? "#F0AB00" : "#3E8635";
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

function AnomalySparkline({ history }: { history: AnomalyPoint[] }) {
  const w = 240;
  const h = 40;

  if (history.length === 0) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <svg width={w} height={h} style={{ display: "block" }}>
          <line
            x1={0}
            y1={h - 4}
            x2={w}
            y2={h - 4}
            stroke="#E0E0E0"
            strokeWidth={1}
          />
        </svg>
        <span style={{ fontSize: 12, color: "#6A6E73" }}>baseline</span>
      </div>
    );
  }

  const latest = history[history.length - 1]!.v;
  const points = history
    .map((p, i) => {
      const x = (i / Math.max(history.length - 1, 1)) * w;
      const y = h - p.v * h;
      return `${x},${y}`;
    })
    .join(" ");

  const color =
    latest >= 0.85 ? "#A30000" : latest >= 0.5 ? "#F0AB00" : "#3E8635";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <svg width={w} height={h} style={{ display: "block" }}>
        <line
          x1={0}
          y1={h - 4}
          x2={w}
          y2={h - 4}
          stroke="#E0E0E0"
          strokeWidth={1}
          strokeDasharray="4 4"
        />
        <polyline points={points} fill="none" stroke={color} strokeWidth={2} />
      </svg>
      <span style={{ fontSize: 13, color, fontWeight: 600 }}>
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
    factory.argoSyncStatus === "syncing" ||
    factory.argoSyncStatus === "reverting"
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

  const demoPhase = fleet?.demoPhase ?? "idle";
  const currentStepIdx = phaseToStepIndex(demoPhase);
  const transitioning = isPhaseTransitioning(demoPhase);

  return (
    <Stack hasGutter>
      <StackItem>
        <Card>
          <CardHeader>
            <CardTitle>Fleet Demo — Policy Promotion & Auto-Rollback</CardTitle>
          </CardHeader>
          <CardBody>
            <ProgressStepper>
              {DEMO_STEPS.map((step, i) => (
                <ProgressStep
                  key={step.id}
                  id={step.id}
                  titleId={`step-${step.id}`}
                  variant={stepVariant(i, currentStepIdx)}
                  isCurrent={i === currentStepIdx}
                  description={
                    <StepDescription
                      step={step}
                      isActive={i === currentStepIdx}
                      isDone={i < currentStepIdx}
                      isBusy={actionBusy === step.action}
                      isTransitioning={i === currentStepIdx && transitioning}
                      links={fleet?.links ?? null}
                      onAction={() => void onStepAction(step.action)}
                    />
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

      {fleet && (
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
