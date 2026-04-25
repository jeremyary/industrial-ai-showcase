// This project was developed with assistance from AI tools.
import type { ArgoSync } from "./argoSync.js";
import type { SimpleLogger } from "./kafkaStream.js";

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
const ARGO_POLL_MS = 2000;
const ARGO_FALLBACK_MS = 3000;

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

  private timers: ReturnType<typeof setTimeout>[] = [];
  private promotedVersion: string = BASELINE_VERSION;
  argoSync: ArgoSync | null = null;
  log: SimpleLogger | null = null;

  promotePolicy(factory: string, version: string): void {
    const f = this.factories[factory];
    if (!f) return;
    this.promotedVersion = version;
    f.policyVersion = version;
    f.argoSyncStatus = "syncing";
    this.phase = "promoted";

    if (this.argoSync?.enabled) {
      void this.realArgoPromote(factory, version);
    } else {
      this.scheduleSettle(factory, "synced");
    }
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
    for (const timer of this.timers) clearTimeout(timer);
    this.timers = [];
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

    if (this.argoSync?.enabled) {
      void this.argoSync.updatePolicyVersion(BASELINE_VERSION);
    }
  }

  private triggerRollback(robotId: string): void {
    this.phase = "anomaly-detected";
    const factory = robotId === "fl-08" ? "factory-b" : "factory-a";
    const f = this.factories[factory];
    if (!f) return;
    f.argoSyncStatus = "reverting";

    if (this.argoSync?.enabled) {
      void this.realArgoRollback(factory);
    } else {
      this.scheduleSettle(factory, "synced", () => {
        f.policyVersion = BASELINE_VERSION;
        this.phase = "rolled-back";
      });
    }
  }

  private async realArgoPromote(factory: string, version: string): Promise<void> {
    const ok = await this.argoSync!.updatePolicyVersion(version);
    if (!ok) {
      this.scheduleSettle(factory, "synced");
      return;
    }
    this.pollArgoUntilSynced(factory, () => {
      this.log?.info({ factory, version }, "argoSync: promotion sync complete");
    });
  }

  private async realArgoRollback(factory: string): Promise<void> {
    const f = this.factories[factory];
    const ok = await this.argoSync!.updatePolicyVersion(BASELINE_VERSION);
    if (!ok) {
      this.scheduleSettle(factory, "synced", () => {
        if (f) f.policyVersion = BASELINE_VERSION;
        this.phase = "rolled-back";
      });
      return;
    }
    this.pollArgoUntilSynced(factory, () => {
      if (f) f.policyVersion = BASELINE_VERSION;
      this.phase = "rolled-back";
      this.log?.info({ factory }, "argoSync: rollback sync complete");
    });
  }

  private pollArgoUntilSynced(factory: string, onDone: () => void): void {
    let attempts = 0;
    const maxAttempts = 60;
    const poll = (): void => {
      attempts++;
      void this.argoSync!.getArgoSyncStatus().then(({ syncStatus, healthStatus }) => {
        const f = this.factories[factory];
        if (syncStatus === "Synced" && healthStatus === "Healthy") {
          if (f) f.argoSyncStatus = "synced";
          onDone();
          return;
        }
        if (attempts >= maxAttempts) {
          this.log?.warn({ factory, syncStatus, healthStatus }, "argoSync: poll timeout — marking synced");
          if (f) f.argoSyncStatus = "synced";
          onDone();
          return;
        }
        const timer = setTimeout(poll, ARGO_POLL_MS);
        this.timers.push(timer);
      });
    };
    const timer = setTimeout(poll, ARGO_POLL_MS);
    this.timers.push(timer);
  }

  private scheduleSettle(
    factory: string,
    targetStatus: ArgoSyncStatus,
    onSettle?: () => void,
  ): void {
    const timer = setTimeout(() => {
      const f = this.factories[factory];
      if (f) f.argoSyncStatus = targetStatus;
      onSettle?.();
    }, ARGO_FALLBACK_MS);
    this.timers.push(timer);
  }
}
