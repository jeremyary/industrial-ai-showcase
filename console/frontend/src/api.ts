// This project was developed with assistance from AI tools.
import type { FleetMessage, ScenarioDetail, Topology } from "./types.js";

export async function fetchTopology(): Promise<Topology> {
  const resp = await fetch("/api/topology");
  if (!resp.ok) throw new Error(`topology fetch failed: ${resp.status}`);
  return (await resp.json()) as Topology;
}

export async function fetchScenarios(): Promise<{ scenarios: string[] }> {
  const resp = await fetch("/api/scenarios");
  if (!resp.ok) throw new Error(`scenarios fetch failed: ${resp.status}`);
  return (await resp.json()) as { scenarios: string[] };
}

export async function fetchScenarioDetail(name: string): Promise<ScenarioDetail> {
  const resp = await fetch(`/api/scenarios/${encodeURIComponent(name)}`);
  if (!resp.ok) throw new Error(`scenario detail fetch failed: ${resp.status}`);
  return (await resp.json()) as ScenarioDetail;
}

export async function executeAction(
  action: string,
  params?: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const resp = await fetch(`/api/action/${encodeURIComponent(action)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params ?? {}),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`action failed: ${resp.status} ${text}`);
  }
  return (await resp.json()) as Record<string, unknown>;
}

export function subscribeEvents(onMessage: (m: FleetMessage) => void): () => void {
  const es = new EventSource("/api/events");
  es.addEventListener("message", (evt) => {
    try {
      const parsed = JSON.parse(evt.data) as FleetMessage;
      onMessage(parsed);
    } catch {
      // ignore malformed payloads
    }
  });
  return () => es.close();
}
