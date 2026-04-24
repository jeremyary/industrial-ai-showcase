// This project was developed with assistance from AI tools.
import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [cameraTick, setCameraTick] = useState(0);
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
      setConnected((prev) => {
        if (!prev) console.log("[console] events stream: live");
        return true;
      });

      if (msg.topic === "fleet.safety.alerts" && msg.payload && typeof msg.payload === "object") {
        const p = msg.payload as Record<string, unknown>;
        const obstructed = p["obstructed"] === true;
        console.log("[console] safety alert:", obstructed ? "obstruction detected" : "clear");
        setAlertActive(obstructed);
      }

      if (msg.topic?.startsWith("warehouse.cameras.")) {
        setCameraTick((t) => t + 1);
        return;
      }

      if (extractKind(msg)) {
        setEvents((prev) => [msg, ...prev].slice(0, MAX_EVENTS));
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
      console.log("[console] action result:", summary);
      setLastResult(summary);
    } catch (e) {
      const err = `${btn.label}: ${e instanceof Error ? e.message : "failed"}`;
      console.log("[console] action error:", err);
      setLastResult(err);
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
                    <CameraFeedCard cameraTick={cameraTick} />
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
  alertActive,
  onAction,
}: {
  scenario: ScenarioDetail | null;
  actionBusy: string | null;
  lastResult: string | null;
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

  const buttonVariant = (action: string): "primary" | "danger" | "tertiary" | "secondary" => {
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
        </Stack>
      </CardBody>
    </Card>
  );
}

function TopologyCard({ topology, connected }: { topology: Topology | null; connected: boolean }){
  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>Topology</CardTitle>
      </CardHeader>
      <CardBody>
        {topology === null ? (
          <Spinner size="md" />
        ) : (
          <Flex spaceItems={{ default: "spaceItemsLg" }}>
            <FlexItem flex={{ default: "flex_1" }}>
              <div className="showcase-cluster showcase-cluster--hub">
                <div className="showcase-cluster-title">{topology.hub.name}</div>
                <ul className="showcase-cluster-workloads">
                  {topology.hub.workloads.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            </FlexItem>
            <FlexItem flex={{ default: "flex_1" }}>
              <div className="showcase-cluster showcase-cluster--companion">
                <div className="showcase-cluster-title">{topology.companion.name}</div>
                <ul className="showcase-cluster-workloads">
                  {topology.companion.workloads.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            </FlexItem>
          </Flex>
        )}
      </CardBody>
    </Card>
  );
}

function CameraFeedCard({ cameraTick }: { cameraTick: number }){
  return (
    <Card isFullHeight>
      <CardHeader><CardTitle>Camera Reasoning</CardTitle></CardHeader>
      <CardBody className="showcase-camera-body">
        <img
          src={`/api/camera/frame?t=${cameraTick}`}
          alt="Camera feed"
        />
      </CardBody>
    </Card>
  );
}

interface CollapsedEvent {
  topic: string;
  kind: string;
  count: number;
  key: string;
}

function collapseEvents(events: FleetMessage[]): CollapsedEvent[] {
  const result: CollapsedEvent[] = [];
  for (const m of events) {
    const kind = extractKind(m);
    const prev = result[result.length - 1];
    if (prev && prev.topic === m.topic && prev.kind === kind) {
      prev.count++;
    } else {
      result.push({ topic: m.topic, kind, count: 1, key: `${m.topic}-${m.partition}-${m.offset}` });
    }
  }
  return result;
}

function EventsCard({ events }: { events: FleetMessage[] }){
  const collapsed = useMemo(() => collapseEvents(events), [events]);
  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>Live fleet events</CardTitle>
      </CardHeader>
      <CardBody className="showcase-events-body">
        {events.length === 0 ? (
          <span className="showcase-event-kind" style={{ padding: "8px 16px" }}>no events yet</span>
        ) : (
          collapsed.map((evt) => (
            <div key={evt.key} className="showcase-event-row">
              <Label color={topicColor(evt.topic)} isCompact>{evt.topic}</Label>
              <span className="showcase-event-kind">{evt.kind}</span>
              {evt.count > 1 ? (
                <Badge isRead>{evt.count}</Badge>
              ) : null}
            </div>
          ))
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

    if (typeof p["kind"] === "string") {
      const k = p["kind"] as string;
      if (k === "vla.call.failed") return "";
      if (k === "vla.call.started") return "querying VLA";
      return k;
    }

    if (typeof p["event_class"] === "string") return p["event_class"] as string;
    if (typeof p["alert_type"] === "string") return p["alert_type"] as string;

    if (m.topic === "fleet.safety.alerts") {
      return p["obstructed"] === true ? "obstruction" : "clear";
    }

    if (typeof p["robot_id"] === "string") return p["robot_id"] as string;
  }
  return "(payload)";
}
