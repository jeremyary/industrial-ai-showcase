// This project was developed with assistance from AI tools.

export type DemoPhase =
  | "idle"
  | "training-running"
  | "training-complete"
  | "promoted"
  | "anomaly-detected"
  | "rolled-back";

export type ArgoSyncStatus = "synced" | "syncing" | "reverting";

export type LineageNodeStatus = "completed" | "running" | "pending";

export interface AnomalyPoint {
  t: number;
  v: number;
}

interface FactoryState {
  policyVersion: string;
  argoSyncStatus: ArgoSyncStatus;
}

const BASELINE_VERSION = "vla-warehouse-v1.3";
const ANOMALY_RING_SIZE = 60;
const ARGO_TRANSITION_MS = 3000;

export class DemoState {
  phase: DemoPhase = "idle";
  factories: Record<string, FactoryState> = {
    "factory-a": { policyVersion: BASELINE_VERSION, argoSyncStatus: "synced" },
    "factory-b": { policyVersion: BASELINE_VERSION, argoSyncStatus: "synced" },
  };
  lineageStatuses: Record<string, LineageNodeStatus> = {
    dataset: "completed",
    pipeline: "completed",
    training: "completed",
    validation: "completed",
    model: "completed",
  };
  anomalyHistory: AnomalyPoint[] = [];

  private argoTimers: ReturnType<typeof setTimeout>[] = [];
  private promotedVersion: string = BASELINE_VERSION;

  promotePolicy(factory: string, version: string): void {
    const f = this.factories[factory];
    if (!f) return;
    this.promotedVersion = version;
    f.policyVersion = version;
    f.argoSyncStatus = "syncing";
    this.phase = "promoted";
    this.scheduleArgoSettle(factory, "synced");
  }

  advanceLineage(phase: string): void {
    if (phase === "training-running") {
      this.phase = "training-running";
      this.lineageStatuses = {
        dataset: "completed",
        pipeline: "running",
        training: "running",
        validation: "pending",
        model: "pending",
      };
    } else if (phase === "training-complete") {
      this.phase = "training-complete";
      this.lineageStatuses = {
        dataset: "completed",
        pipeline: "completed",
        training: "completed",
        validation: "completed",
        model: "completed",
      };
    }
  }

  recordAnomaly(robotId: string, score: number): void {
    this.anomalyHistory.push({ t: Date.now(), v: score });
    if (this.anomalyHistory.length > ANOMALY_RING_SIZE) {
      this.anomalyHistory.shift();
    }
    if (score >= 0.85) {
      this.triggerRollback(robotId);
    }
  }

  reset(): void {
    for (const timer of this.argoTimers) clearTimeout(timer);
    this.argoTimers = [];
    this.phase = "idle";
    this.promotedVersion = BASELINE_VERSION;
    for (const key of Object.keys(this.factories)) {
      this.factories[key] = {
        policyVersion: BASELINE_VERSION,
        argoSyncStatus: "synced",
      };
    }
    this.lineageStatuses = {
      dataset: "completed",
      pipeline: "completed",
      training: "completed",
      validation: "completed",
      model: "completed",
    };
    this.anomalyHistory = [];
  }

  private triggerRollback(robotId: string): void {
    this.phase = "anomaly-detected";
    const factory = robotId === "fl-08" ? "factory-b" : "factory-a";
    const f = this.factories[factory];
    if (!f) return;
    f.argoSyncStatus = "reverting";
    this.scheduleArgoSettle(factory, "synced", () => {
      f.policyVersion = BASELINE_VERSION;
      this.phase = "rolled-back";
    });
  }

  private scheduleArgoSettle(
    factory: string,
    targetStatus: ArgoSyncStatus,
    onSettle?: () => void,
  ): void {
    const timer = setTimeout(() => {
      const f = this.factories[factory];
      if (f) f.argoSyncStatus = targetStatus;
      onSettle?.();
    }, ARGO_TRANSITION_MS);
    this.argoTimers.push(timer);
  }
}
