// This project was developed with assistance from AI tools.
import { useEffect, useMemo, useState } from "react";
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
  Select,
  SelectOption,
  MenuToggle,
  type MenuToggleElement,
  Spinner,
  Stack,
  StackItem,
  ToggleGroup,
  ToggleGroupItem,
} from "@patternfly/react-core";
import type { AudienceMode, FleetMessage, Topology } from "./types.js";
import { fetchScenarios, fetchTopology, runScenario, subscribeEvents } from "./api.js";

const MAX_EVENTS = 200;

export function App(){
  const [audience, setAudience] = useState<AudienceMode>("novice");
  const [topology, setTopology] = useState<Topology | null>(null);
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [scenarioSelection, setScenarioSelection] = useState<string | null>(null);
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const [lastTraceId, setLastTraceId] = useState<string | null>(null);
  const [events, setEvents] = useState<FleetMessage[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    fetchTopology().then(setTopology).catch(() => undefined);
    fetchScenarios()
      .then((r) => {
        setScenarios(r.scenarios);
        setScenarioSelection(r.scenarios[0] ?? null);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeEvents((msg) => {
      setConnected(true);
      setEvents((prev) => [msg, ...prev].slice(0, MAX_EVENTS));
    });
    return unsubscribe;
  }, []);

  const onRun = async () => {
    if (!scenarioSelection) return;
    try {
      const result = await runScenario(scenarioSelection);
      setLastTraceId(result.trace_id);
    } catch {
      setLastTraceId("run failed");
    }
  };

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
          <FlexItem flex={{ default: "flex_1" }}>
            <TopologyCard topology={topology} connected={connected} />
          </FlexItem>
          <FlexItem flex={{ default: "flex_2" }}>
            <StageCard />
          </FlexItem>
          <FlexItem flex={{ default: "flex_2" }}>
            <EventsCard events={events} />
          </FlexItem>
        </Flex>
      </PageSection>

      <PageSection>
        <Card>
          <CardHeader>
            <CardTitle>Drive the demo</CardTitle>
          </CardHeader>
          <CardBody>
            <Flex spaceItems={{ default: "spaceItemsMd" }} alignItems={{ default: "alignItemsCenter" }}>
              <FlexItem>
                <Select
                  id="scenario-select"
                  isOpen={scenarioOpen}
                  selected={scenarioSelection}
                  onSelect={(_e, v) => {
                    setScenarioSelection(String(v));
                    setScenarioOpen(false);
                  }}
                  toggle={(ref: React.Ref<MenuToggleElement>) => (
                    <MenuToggle
                      ref={ref}
                      onClick={() => setScenarioOpen((o) => !o)}
                      isExpanded={scenarioOpen}
                    >
                      {scenarioSelection ?? "choose a scenario"}
                    </MenuToggle>
                  )}
                >
                  {scenarios.map((s) => (
                    <SelectOption key={s} value={s}>
                      {s}
                    </SelectOption>
                  ))}
                </Select>
              </FlexItem>
              <FlexItem>
                <Button variant="primary" onClick={onRun} isDisabled={!scenarioSelection}>
                  Fire scenario
                </Button>
              </FlexItem>
              {lastTraceId ? (
                <FlexItem>
                  <Label color="blue">trace_id: {lastTraceId}</Label>
                </FlexItem>
              ) : null}
            </Flex>
          </CardBody>
        </Card>
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
          <Stack hasGutter>
            <StackItem>
              <ClusterPanel title={topology.hub.name} workloads={topology.hub.workloads} />
            </StackItem>
            <StackItem>
              <ClusterPanel title={topology.companion.name} workloads={topology.companion.workloads} />
            </StackItem>
            <StackItem>
              <Label color={connected ? "green" : "grey"}>
                events stream: {connected ? "live" : "waiting…"}
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

function StageCard(){
  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>Stage</CardTitle>
      </CardHeader>
      <CardBody>
        <div
          style={{
            aspectRatio: "16/9",
            background: "linear-gradient(135deg, #1e1e1e, #3a3a3a)",
            color: "#ddd",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 6,
          }}
        >
          <span>Kit App Streaming viewport — lands in Phase 1 tail (Isaac Sim + Kit).</span>
        </div>
      </CardBody>
    </Card>
  );
}

function EventsCard({ events }: { events: FleetMessage[] }){
  const grouped = useMemo(() => groupByTrace(events), [events]);
  return (
    <Card isFullHeight>
      <CardHeader>
        <CardTitle>Live fleet events</CardTitle>
      </CardHeader>
      <CardBody style={{ maxHeight: "60vh", overflowY: "auto" }}>
        {events.length === 0 ? (
          <em>no events yet — fire a scenario</em>
        ) : (
          <Stack hasGutter>
            {grouped.map(({ traceId, messages }) => (
              <StackItem key={traceId}>
                <Card>
                  <CardHeader>
                    <CardTitle>
                      <code>{traceId}</code>
                    </CardTitle>
                  </CardHeader>
                  <CardBody>
                    {messages.map((m) => (
                      <EventLine key={`${m.topic}-${m.partition}-${m.offset}`} message={m} />
                    ))}
                  </CardBody>
                </Card>
              </StackItem>
            ))}
          </Stack>
        )}
      </CardBody>
    </Card>
  );
}

function groupByTrace(events: FleetMessage[]): { traceId: string; messages: FleetMessage[] }[] {
  const byTrace = new Map<string, FleetMessage[]>();
  for (const m of events) {
    const traceId = extractTraceId(m) ?? "(no trace)";
    const bucket = byTrace.get(traceId) ?? [];
    bucket.push(m);
    byTrace.set(traceId, bucket);
  }
  return Array.from(byTrace.entries()).map(([traceId, messages]) => ({ traceId, messages }));
}

function extractTraceId(m: FleetMessage): string | null {
  if (m.payload && typeof m.payload === "object" && "trace_id" in m.payload) {
    const t = (m.payload as Record<string, unknown>)["trace_id"];
    return typeof t === "string" ? t : null;
  }
  return null;
}

function EventLine({ message }: { message: FleetMessage }){
  const kind = extractKind(message);
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 4 }}>
      <Label color={topicColor(message.topic)} isCompact>
        {message.topic}
      </Label>
      <span style={{ fontFamily: "monospace", fontSize: 12 }}>{kind}</span>
    </div>
  );
}

function topicColor(topic: string): "blue" | "green" | "orange" | "purple" | "grey" {
  switch (topic) {
    case "fleet.events":
      return "blue";
    case "fleet.missions":
      return "green";
    case "fleet.ops.events":
      return "orange";
    case "fleet.telemetry":
      return "purple";
    default:
      return "grey";
  }
}

function extractKind(m: FleetMessage): string {
  if (m.payload && typeof m.payload === "object") {
    const p = m.payload as Record<string, unknown>;
    if (typeof p["kind"] === "string") return p["kind"] as string;
    if (typeof p["event_class"] === "string") return p["event_class"] as string;
    if (typeof p["robot_id"] === "string") return `telemetry ${p["robot_id"] as string}`;
  }
  return "(payload)";
}
