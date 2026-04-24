// This project was developed with assistance from AI tools.
import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Label,
  Masthead,
  MastheadBrand,
  MastheadContent,
  MastheadMain,
  Page,
  PageSection,
  Spinner,
  Stack,
  StackItem,
  ToggleGroup,
  ToggleGroupItem,
} from "@patternfly/react-core";
import type { AudienceMode, ButtonDef, FleetMessage, ScenarioDetail, Topology } from "./types.js";
import { executeAction, fetchScenarioDetail, fetchScenarios, fetchTopology, subscribeEvents } from "./api.js";
import { StageCard } from "./Stage.js";

const MAX_EVENTS = 200;

export function App(){
  const [audience, setAudience] = useState<AudienceMode>("novice");
  const [topology, setTopology] = useState<Topology | null>(null);
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [events, setEvents] = useState<FleetMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [cameraState, setCameraState] = useState<string | null>(null);
  const [alertActive, setAlertActive] = useState(false);

  useEffect(() => {
    fetchTopology().then(setTopology).catch(() => undefined);
    fetchScenarios()
      .then((r) => {
        if (r.scenarios[0]) {
          fetchScenarioDetail(r.scenarios[0]).then(setScenario).catch(() => undefined);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeEvents((msg) => {
      setConnected(true);
      setEvents((prev) => [msg, ...prev].slice(0, MAX_EVENTS));

      if (msg.topic === "fleet.safety.alerts" && msg.payload && typeof msg.payload === "object") {
        const p = msg.payload as Record<string, unknown>;
        setAlertActive(p["obstructed"] === true);
      }

      if (
        msg.topic?.startsWith("warehouse.cameras.") &&
        msg.payload &&
        typeof msg.payload === "object" &&
        "state" in msg.payload
      ) {
        setCameraState(String((msg.payload as Record<string, unknown>).state));
      }
    });
    return unsubscribe;
  }, []);

  const onAction = useCallback(async (btn: ButtonDef) => {
    setActionBusy(btn.action);
    setLastResult(null);
    try {
      const result = await executeAction(btn.action, btn.params);
      const summary = result.trace_id
        ? `${btn.label}: ${result.status} (${String(result.trace_id).slice(0, 8)})`
        : `${btn.label}: ${result.status ?? "ok"}`;
      setLastResult(summary);

      if (btn.action === "drop-pallet") {
        setCameraState("obstructed");
      } else if (btn.action === "clear-pallet" || btn.action === "reset-scene") {
        setCameraState("empty");
      }
    } catch (e) {
      setLastResult(`${btn.label}: ${e instanceof Error ? e.message : "failed"}`);
    } finally {
      setActionBusy(null);
    }
  }, []);

  return (
    <Page
      masthead={
        <Masthead>
          <MastheadMain>
            <MastheadBrand>
              <strong>Physical AI Showcase</strong>
            </MastheadBrand>
          </MastheadMain>
          <MastheadContent>
            <ToggleGroup aria-label="audience mode">
              {(["novice", "evaluator", "expert"] as const).map((m) => (
                <ToggleGroupItem
                  key={m}
                  text={m}
                  buttonId={m}
                  isSelected={audience === m}
                  onChange={() => setAudience(m)}
                />
              ))}
            </ToggleGroup>
          </MastheadContent>
        </Masthead>
      }
    >
      <PageSection>
        <Flex spaceItems={{ default: "spaceItemsLg" }} alignItems={{ default: "alignItemsStretch" }}>
          <FlexItem
            flex={{ default: "flex_1" }}
            style={{ maxWidth: 320, minWidth: 260, alignSelf: "stretch" }}
          >
            <Stack hasGutter style={{ height: "100%" }}>
              <StackItem>
                <ScenarioPanel
                  scenario={scenario}
                  actionBusy={actionBusy}
                  lastResult={lastResult}
                  cameraState={cameraState}
                  alertActive={alertActive}
                  onAction={onAction}
                />
              </StackItem>
              <StackItem isFilled style={{ minHeight: 0, overflow: "hidden" }}>
                <EventsCard events={events} />
              </StackItem>
            </Stack>
          </FlexItem>
          <FlexItem flex={{ default: "flex_4" }}>
            <Stack hasGutter style={{ height: "100%" }}>
              <StackItem>
                <Flex spaceItems={{ default: "spaceItemsLg" }} alignItems={{ default: "alignItemsStretch" }}>
                  <FlexItem flex={{ default: "flex_1" }}>
                    <TopologyCard topology={topology} connected={connected} />
                  </FlexItem>
                  <FlexItem style={{ width: 458, flexShrink: 0 }}>
                    <CameraFeedCard cameraState={cameraState} />
                  </FlexItem>
                </Flex>
              </StackItem>
              <StackItem isFilled>
                <StageCard />
              </StackItem>
            </Stack>
          </FlexItem>
        </Flex>
      </PageSection>

      {audience !== "novice" && topology?.teasers.length ? (
        <PageSection>
          <Flex spaceItems={{ default: "spaceItemsSm" }}>
            {topology.teasers.map((t) => (
              <FlexItem key={t}>
                <Badge>{t}</Badge>
              </FlexItem>
            ))}
          </Flex>
        </PageSection>
      ) : null}
    </Page>
  );
}

function ScenarioPanel({
  scenario,
  actionBusy,
  lastResult,
  cameraState,
  alertActive,
  onAction,
}: {
  scenario: ScenarioDetail | null;
  actionBusy: string | null;
  lastResult: string | null;
  cameraState: string | null;
  alertActive: boolean;
  onAction: (btn: ButtonDef) => void;
}){
  if (!scenario) {
    return (
      <Card>
        <CardHeader><CardTitle>Drive the demo</CardTitle></CardHeader>
        <CardBody><Spinner size="md" /></CardBody>
      </Card>
    );
  }

  const buttonVariant = (action: string): "primary" | "danger" | "secondary" | "tertiary" => {
    if (action === "dispatch") return "primary";
    if (action === "drop-pallet") return "danger";
    if (action === "reset-scene") return "tertiary";
    return "secondary";
  };

  return (
    <Card>
      <CardHeader><CardTitle>Drive the demo</CardTitle></CardHeader>
      <CardBody>
        <Stack hasGutter>
          <StackItem>
            <Flex spaceItems={{ default: "spaceItemsSm" }} direction={{ default: "column" }}>
              {scenario.buttons.map((btn) => (
                <FlexItem key={btn.action}>
                  <Button
                    variant={buttonVariant(btn.action)}
                    isBlock
                    isLoading={actionBusy === btn.action}
                    isDisabled={actionBusy !== null}
                    onClick={() => onAction(btn)}
                  >
                    {btn.label}
                  </Button>
                </FlexItem>
              ))}
            </Flex>
          </StackItem>
          <StackItem>
            <Flex spaceItems={{ default: "spaceItemsSm" }}>
              <FlexItem>
                <Label color={cameraState === "obstructed" ? "orange" : "green"} isCompact>
                  camera: {cameraState ?? "unknown"}
                </Label>
              </FlexItem>
              {alertActive ? (
                <FlexItem>
                  <Label color="red" isCompact>obstruction detected</Label>
                </FlexItem>
              ) : null}
            </Flex>
          </StackItem>
          {lastResult ? (
            <StackItem>
              <Label color="blue" style={{ maxWidth: "100%" }}>{lastResult}</Label>
            </StackItem>
          ) : null}
        </Stack>
      </CardBody>
    </Card>
  );
}

function TopologyCard({ topology, connected }: { topology: Topology | null; connected: boolean }){
  return (
    <Card>
      <CardHeader>
        <CardTitle>Topology</CardTitle>
      </CardHeader>
      <CardBody>
        {topology === null ? (
          <Spinner size="md" />
        ) : (
          <Stack hasGutter>
            <StackItem>
              <ClusterPanel title={topology.hub.name} workloads={topology.hub.workloads} />
            </StackItem>
            <StackItem>
              <ClusterPanel title={topology.companion.name} workloads={topology.companion.workloads} />
            </StackItem>
            <StackItem>
              <Label color={connected ? "green" : "grey"}>
                events stream: {connected ? "live" : "waiting..."}
              </Label>
            </StackItem>
          </Stack>
        )}
      </CardBody>
    </Card>
  );
}

function ClusterPanel({ title, workloads }: { title: string; workloads: string[] }){
  return (
    <div>
      <strong>{title}</strong>
      <ul style={{ marginTop: 4 }}>
        {workloads.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
    </div>
  );
}

function CameraFeedCard({ cameraState }: { cameraState: string | null }){
  const [tick, setTick] = useState(0);
  useEffect(() => {
    setTick((t) => t + 1);
  }, [cameraState]);

  return (
    <Card isFullHeight>
      <CardHeader><CardTitle>Camera feed</CardTitle></CardHeader>
      <CardBody style={{ padding: 0 }}>
        <img
          src={`/api/camera/frame?t=${tick}`}
          alt={`Camera: ${cameraState ?? "unknown"}`}
          style={{ width: "100%", display: "block", borderRadius: "0 0 3px 3px" }}
        />
      </CardBody>
    </Card>
  );
}

function EventsCard({ events }: { events: FleetMessage[] }){
  return (
    <Card>
      <CardHeader>
        <CardTitle>Live fleet events</CardTitle>
      </CardHeader>
      <CardBody style={{ height: "100%", overflowY: "auto" }}>
        {events.length === 0 ? (
          <em>no events yet</em>
        ) : (
          <div>
            {events.map((m) => (
              <div key={`${m.topic}-${m.partition}-${m.offset}`} style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 4 }}>
                <Label color={topicColor(m.topic)} isCompact>
                  {m.topic}
                </Label>
                <span style={{ fontFamily: "monospace", fontSize: 12 }}>{extractKind(m)}</span>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function topicColor(topic: string): "blue" | "green" | "orange" | "purple" | "red" | "grey" {
  if (topic === "fleet.events") return "blue";
  if (topic === "fleet.missions") return "green";
  if (topic === "fleet.ops.events") return "orange";
  if (topic === "fleet.telemetry") return "purple";
  if (topic === "fleet.safety.alerts") return "red";
  return "grey";
}

function extractKind(m: FleetMessage): string {
  if (m.payload && typeof m.payload === "object") {
    const p = m.payload as Record<string, unknown>;
    if (typeof p["kind"] === "string") return p["kind"] as string;
    if (typeof p["event_class"] === "string") return p["event_class"] as string;
    if (typeof p["alert_type"] === "string") return p["alert_type"] as string;
    if (typeof p["robot_id"] === "string") return p["robot_id"] as string;
  }
  return "(payload)";
}
