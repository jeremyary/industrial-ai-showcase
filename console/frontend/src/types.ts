// This project was developed with assistance from AI tools.
export type AudienceMode = "novice" | "evaluator" | "expert";

export interface Topology {
  hub: { name: string; namespace: string; workloads: string[] };
  companion: { name: string; namespace: string; workloads: string[] };
  teasers: string[];
}

export interface FleetMessage {
  receivedAt: string;
  topic: string;
  partition: number;
  offset: string;
  key: string | null;
  payload: Record<string, unknown> | string | null;
}

export interface ButtonDef {
  label: string;
  action: string;
  params: Record<string, string>;
}

export interface ScenarioDetail {
  name: string;
  buttons: ButtonDef[];
}

export type ViewName = "stage" | "architecture" | "fleet" | "lineage";

export interface FactoryStatus {
  name: string;
  namespace: string;
  policyVersion: string;
  robotId: string;
  robotStatus: "active" | "idle" | "rerouting";
  anomalyScore: number;
  argoSyncStatus: "synced" | "syncing" | "reverting";
  lastHeartbeat: string;
}

export interface AnomalyPoint {
  t: number;
  v: number;
}

export interface DemoLinks {
  argoFleetManager: string;
  ocpFleetManager: string;
  rhoaiDashboard: string;
  argoConsole: string;
}

export interface StatusLogEntry {
  ts: number;
  message: string;
}

export interface FleetStatus {
  demoPhase: string;
  anomalyHistory: AnomalyPoint[];
  statusLog: StatusLogEntry[];
  links: DemoLinks | null;
  factories: FactoryStatus[];
}

export interface LineageNode {
  id: string;
  type: "dataset" | "pipeline" | "training" | "validation" | "model" | "synthetic";
  label: string;
  status: "completed" | "running" | "failed" | "pending";
  metadata: Record<string, string>;
}

export interface LineageEdge {
  source: string;
  target: string;
}

export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
}
