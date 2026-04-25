// This project was developed with assistance from AI tools.
import type { ArgoSync } from "./argoSync.js";
import type { SimpleLogger } from "./kafkaStream.js";

export type DemoPhase =
  | "idle"
  | "training-running"
  | "training-complete"
  | "promoting"
  | "promoted"
  | "anomaly-detected"
  | "rolling-back"
  | "rolled-back";

export type ArgoSyncStatus = "synced" | "syncing" | "reverting";

export type LineageNodeStatus = "completed" | "running" | "pending";

export interface AnomalyPoint {
  t: number;
  v: number;
}

export interface StatusLogEntry {
  ts: number;
  message: string;
}

interface FactoryState {
  policyVersion: string;
  argoSyncStatus: ArgoSyncStatus;
}

const BASELINE_VERSION = "vla-warehouse-v1.3";
const ANOMALY_RING_SIZE = 60;
const ARGO_POLL_MS = 3000;
const ARGO_FALLBACK_MS = 4000;

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
  statusLog: StatusLogEntry[] = [];

  private timers: ReturnType<typeof setTimeout>[] = [];
  private promotedVersion: string = BASELINE_VERSION;
  argoSync: ArgoSync | null = null;
  log: SimpleLogger | null = null;

  private addLog(message: string): void {
    this.statusLog.push({ ts: Date.now(), message });
    if (this.statusLog.length > 20) this.statusLog.shift();
  }

  promotePolicy(factory: string, version: string): void {
    const f = this.factories[factory];
    if (!f) return;
    this.promotedVersion = version;
    this.phase = "promoting";
    f.argoSyncStatus = "syncing";
    this.statusLog = [];
    this.addLog(`Starting promotion of ${factory} to ${version}`);

    if (this.argoSync?.enabled) {
      void this.realArgoPromote(factory, version);
    } else {
      this.addLog("Argo CD not configured — simulating sync");
      this.scheduleSettle(factory, "synced", () => {
        f.policyVersion = version;
        this.phase = "promoted";
        this.addLog("Simulated sync complete");
      });
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
    this.statusLog = [];

    if (this.argoSync?.enabled) {
      void this.realArgoReset();
    }
  }

  private triggerRollback(robotId: string): void {
    this.phase = "anomaly-detected";
    const factory = robotId === "fl-08" ? "factory-b" : "factory-a";
    const f = this.factories[factory];
    if (!f) return;
    this.addLog(`Anomaly detected on ${robotId} — initiating rollback`);

    setTimeout(() => {
      this.phase = "rolling-back";
      f.argoSyncStatus = "reverting";
      this.addLog(`Rolling back ${factory} to ${BASELINE_VERSION}`);

      if (this.argoSync?.enabled) {
        void this.realArgoRollback(factory);
      } else {
        this.scheduleSettle(factory, "synced", () => {
          f.policyVersion = BASELINE_VERSION;
          this.phase = "rolled-back";
          this.addLog("Simulated rollback complete");
        });
      }
    }, 2000);
  }

  private async realArgoPromote(
    factory: string,
    version: string,
  ): Promise<void> {
    const f = this.factories[factory];

    this.addLog("Committing policy version change to Git…");
    const result = await this.argoSync!.commitPolicyVersion(version);
    if (!result.ok) {
      this.addLog("Git commit failed — falling back to simulated sync");
      this.scheduleSettle(factory, "synced", () => {
        if (f) f.policyVersion = version;
        this.phase = "promoted";
      });
      return;
    }
    if (result.commitUrl) {
      this.addLog(`Committed → ${result.commitUrl}`);
    } else {
      this.addLog("Policy version already at target in Git");
    }

    this.addLog("Triggering Argo CD sync…");
    const synced = await this.argoSync!.triggerSync();
    if (!synced) {
      this.addLog("Argo sync trigger failed — will poll for natural sync");
    } else {
      this.addLog("Argo CD sync triggered — waiting for completion");
    }

    this.pollArgoUntilSynced(factory, () => {
      if (f) {
        f.policyVersion = version;
        f.argoSyncStatus = "synced";
      }
      this.phase = "promoted";
      this.addLog("Argo CD sync complete — promotion finished");
      this.log?.info({ factory, version }, "argoSync: promotion complete");
    });
  }

  private async realArgoRollback(factory: string): Promise<void> {
    const f = this.factories[factory];

    this.addLog("Committing rollback to Git…");
    const result = await this.argoSync!.commitPolicyVersion(BASELINE_VERSION);
    if (!result.ok) {
      this.addLog("Git commit failed — simulating rollback");
      this.scheduleSettle(factory, "synced", () => {
        if (f) {
          f.policyVersion = BASELINE_VERSION;
          f.argoSyncStatus = "synced";
        }
        this.phase = "rolled-back";
      });
      return;
    }
    if (result.commitUrl) {
      this.addLog(`Rollback committed → ${result.commitUrl}`);
    }

    this.addLog("Triggering Argo CD sync for rollback…");
    const synced = await this.argoSync!.triggerSync();
    if (!synced) {
      this.addLog("Argo sync trigger failed — will poll for natural sync");
    } else {
      this.addLog("Argo CD sync triggered — waiting for rollback");
    }

    this.pollArgoUntilSynced(factory, () => {
      if (f) {
        f.policyVersion = BASELINE_VERSION;
        f.argoSyncStatus = "synced";
      }
      this.phase = "rolled-back";
      this.addLog("Rollback sync complete");
      this.log?.info({ factory }, "argoSync: rollback complete");
    });
  }

  private async realArgoReset(): Promise<void> {
    const result = await this.argoSync!.commitPolicyVersion(BASELINE_VERSION);
    if (result.ok) {
      await this.argoSync!.triggerSync();
    }
  }

  private pollArgoUntilSynced(factory: string, onDone: () => void): void {
    let attempts = 0;
    const maxAttempts = 60;
    const poll = (): void => {
      attempts++;
      void this.argoSync!.getArgoSyncStatus().then(
        ({ syncStatus, healthStatus, operationPhase }) => {
          const f = this.factories[factory];
          if (attempts % 3 === 1) {
            this.addLog(
              `Argo: sync=${syncStatus} health=${healthStatus} op=${operationPhase}`,
            );
          }
          if (syncStatus === "Synced" && healthStatus === "Healthy") {
            onDone();
            return;
          }
          if (
            operationPhase === "Succeeded" &&
            syncStatus === "Synced"
          ) {
            onDone();
            return;
          }
          if (attempts >= maxAttempts) {
            this.log?.warn(
              { factory, syncStatus, healthStatus },
              "argoSync: poll timeout",
            );
            this.addLog("Argo poll timed out — marking complete");
            if (f) f.argoSyncStatus = "synced";
            onDone();
            return;
          }
          const timer = setTimeout(poll, ARGO_POLL_MS);
          this.timers.push(timer);
        },
      );
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
