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
