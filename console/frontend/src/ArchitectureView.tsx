// This project was developed with assistance from AI tools.
import { useEffect, useState } from "react";
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
import type { Topology } from "./types.js";
import { fetchTopology } from "./api.js";

const PURDUE_LEVELS = [
  {
    level: 4,
    label: "Level 4 — Enterprise / Hub",
    color: "#0066CC",
    components: [
      { name: "Fleet Manager", ns: "fleet-ops", role: "Mission planning + MES consumption" },
      { name: "Obstruction Detector", ns: "fleet-ops", role: "Camera frame analysis via Cosmos Reason" },
      { name: "Cosmos Reason 2-8B", ns: "cosmos", role: "Visual reasoning (vLLM on L40S)" },
      { name: "MLflow + MinIO", ns: "mlflow", role: "Experiment tracking + artifact storage" },
      { name: "DSPA Pipeline", ns: "vla-training", role: "VLA fine-tuning orchestration" },
      { name: "Model Registry", ns: "redhat-ods-applications", role: "Model versioning + lineage" },
      { name: "Showcase Console", ns: "fleet-ops", role: "Operations dashboard" },
      { name: "Argo CD", ns: "openshift-gitops", role: "GitOps reconciliation" },
    ],
  },
  {
    level: 3,
    label: "Level 3 — Site Operations / MES",
    color: "#3E8635",
    components: [
      { name: "MES-Stub", ns: "fleet-ops", role: "SAP PP/DS-shaped order emitter" },
      { name: "WMS-Stub", ns: "fleet-ops", role: "Scenario driver + demo control" },
      { name: "AMQ Streams (Kafka)", ns: "fleet-ops", role: "Event backbone" },
    ],
  },
  {
    level: 2,
    label: "Level 2 — HMI / SCADA",
    color: "#F0AB00",
    components: [
      { name: "PLC Gateway VM", ns: "factory-floor", role: "KubeVirt — OPC-UA server (brownfield)" },
    ],
  },
  {
    level: 1,
    label: "Level 1 — Field Devices / Robot Edge",
    color: "#A30000",
    components: [
      { name: "Mission Dispatcher (A)", ns: "robot-edge", role: "Waypoint planner + VLA caller" },
      { name: "Fake Camera (A)", ns: "warehouse-edge", role: "Photorealistic warehouse frames" },
      { name: "Mission Dispatcher (B)", ns: "factory-b", role: "Idle telemetry heartbeat" },
      { name: "Fake Camera (B)", ns: "factory-b", role: "Factory B camera feed" },
    ],
  },
];

export function ArchitectureView() {
  const [topology, setTopology] = useState<Topology | null>(null);

  useEffect(() => {
    fetchTopology().then(setTopology).catch(() => undefined);
  }, []);

  return (
    <Stack hasGutter>
      <StackItem>
        <Card>
          <CardHeader>
            <CardTitle>System Architecture — Purdue Model Overlay</CardTitle>
          </CardHeader>
          <CardBody>
            <Stack hasGutter>
              {PURDUE_LEVELS.map((level) => (
                <StackItem key={level.level}>
                  <div
                    style={{
                      borderLeft: `4px solid ${level.color}`,
                      paddingLeft: 16,
                      marginBottom: 8,
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: 8, color: level.color }}>
                      {level.label}
                    </div>
                    <Flex
                      spaceItems={{ default: "spaceItemsSm" }}
                      flexWrap={{ default: "wrap" }}
                    >
                      {level.components.map((c) => (
                        <FlexItem key={c.name}>
                          <div className="showcase-arch-component">
                            <div style={{ fontWeight: 600 }}>{c.name}</div>
                            <div style={{ fontSize: 12, color: "#6A6E73" }}>{c.ns}</div>
                            <div style={{ fontSize: 12, color: "#6A6E73" }}>{c.role}</div>
                          </div>
                        </FlexItem>
                      ))}
                    </Flex>
                  </div>
                </StackItem>
              ))}
            </Stack>
          </CardBody>
        </Card>
      </StackItem>

      <StackItem>
        <Flex spaceItems={{ default: "spaceItemsLg" }}>
          <FlexItem flex={{ default: "flex_1" }}>
            <Card isFullHeight>
              <CardHeader><CardTitle>KubeVirt VM</CardTitle></CardHeader>
              <CardBody>
                <Stack hasGutter>
                  <StackItem>
                    <Label color="purple" isCompact>companion cluster</Label>
                    {" "}plc-gateway-01
                  </StackItem>
                  <StackItem>
                    <div style={{ fontSize: 13, color: "#6A6E73" }}>
                      Namespace: factory-floor
                    </div>
                    <div style={{ fontSize: 13, color: "#6A6E73" }}>
                      OPC-UA server on port 4840
                    </div>
                    <div style={{ fontSize: 13, color: "#6A6E73" }}>
                      Fedora 40 — containerDisk + cloud-init
                    </div>
                  </StackItem>
                  <StackItem>
                    <div style={{ fontSize: 12, color: "#6A6E73", fontStyle: "italic" }}>
                      OpenShift Virtualization runs legacy PLC/HMI gateways alongside container workloads
                    </div>
                  </StackItem>
                </Stack>
              </CardBody>
            </Card>
          </FlexItem>

          <FlexItem flex={{ default: "flex_1" }}>
            <Card isFullHeight>
              <CardHeader><CardTitle>MES Order Flow</CardTitle></CardHeader>
              <CardBody>
                <Stack hasGutter>
                  <StackItem>
                    <Label color="blue" isCompact>mes.orders</Label>
                    {" → Fleet Manager → "}
                    <Label color="green" isCompact>fleet.missions</Label>
                  </StackItem>
                  <StackItem>
                    <div style={{ fontSize: 13, color: "#6A6E73" }}>
                      SAP PP/DS-shaped production orders translated into robot missions
                    </div>
                  </StackItem>
                </Stack>
              </CardBody>
            </Card>
          </FlexItem>

          <FlexItem flex={{ default: "flex_1" }}>
            <Card isFullHeight>
              <CardHeader><CardTitle>Air-Gap Path</CardTitle></CardHeader>
              <CardBody>
                <Stack hasGutter>
                  <StackItem>
                    <div style={{ fontSize: 13, color: "#6A6E73" }}>
                      Mirror registry → OCI artifacts → disconnected install
                    </div>
                    <div style={{ fontSize: 13, color: "#6A6E73" }}>
                      Every dependency mirrorable; no live internet at runtime
                    </div>
                  </StackItem>
                </Stack>
              </CardBody>
            </Card>
          </FlexItem>
        </Flex>
      </StackItem>
    </Stack>
  );
}
