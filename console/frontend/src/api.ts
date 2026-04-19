// This project was developed with assistance from AI tools.
import type { FleetMessage, Topology } from "./types.js";

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

export async function runScenario(name: string): Promise<{ trace_id: string; status: string; scenario: string }> {
  const resp = await fetch(`/api/scenarios/${encodeURIComponent(name)}/run`, {
    method: "POST",
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`run failed: ${resp.status} ${text}`);
  }
  return (await resp.json()) as { trace_id: string; status: string; scenario: string };
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
