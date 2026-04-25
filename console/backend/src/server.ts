// This project was developed with assistance from AI tools.
import Fastify from "fastify";
import fastifyCors from "@fastify/cors";

import { loadConfig } from "./config.js";
import { FleetStream, type FleetMessage } from "./kafkaStream.js";
import { registerStreamRoutes } from "./stream.js";
import { ArgoSync } from "./argoSync.js";

const config = loadConfig();
const fastify = Fastify({
  logger: { level: config.logLevel, name: "showcase-console" },
});
const log = fastify.log;
await fastify.register(fastifyCors, { origin: true });

const argoSync = new ArgoSync(config.githubToken, config.githubRepo, log);
log.info({ argoEnabled: argoSync.enabled }, "argo sync initialized");

const stream = new FleetStream(
  config.kafkaBootstrapServers,
  config.kafkaTopics,
  config.kafkaConsumerGroup,
  config.kafkaClientId,
  log,
);
stream.demoState.argoSync = argoSync;
stream.demoState.log = log;

fastify.get("/healthz", async () => ({ status: "ok" }));
fastify.get("/readyz", async () => ({ status: "ready" }));

fastify.get("/api/topology", async () => ({
  hub: {
    name: "Hub — factory operations",
    namespace: "fleet-ops",
    workloads: ["fleet-manager", "wms-stub", "camera-adapter", "fleet (kafka)"],
  },
  companion: {
    name: "Companion — robot edge",
    namespace: "robot-edge",
    workloads: ["mission-dispatcher", "openvla-server (host-native)"],
  },
  teasers: ["Retrain & promote", "Multi-site rollout", "Agentic operator"],
}));

fastify.get("/api/scenarios", async () => {
  const resp = await fetch(`${config.wmsStubBaseUrl}/scenarios`);
  return resp.json();
});

fastify.get<{ Params: { name: string } }>(
  "/api/scenarios/:name",
  async (request, reply) => {
    const { name } = request.params;
    const resp = await fetch(
      `${config.wmsStubBaseUrl}/scenarios/${encodeURIComponent(name)}`,
    );
    const body = await resp.text();
    reply.code(resp.status).type("application/json").send(body);
  },
);

fastify.post<{ Params: { action: string }; Body: Record<string, unknown> }>(
  "/api/action/:action",
  async (request, reply) => {
    const { action } = request.params;
    const resp = await fetch(
      `${config.wmsStubBaseUrl}/${encodeURIComponent(action)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request.body ?? {}),
      },
    );
    const body = await resp.text();
    reply.code(resp.status).type("application/json").send(body);
  },
);

fastify.get("/api/fleet", async () => {
  const telemetry = stream.getLatestTelemetry();
  const ds = stream.demoState;
  const fa = ds.factories["factory-a"];
  const fb = ds.factories["factory-b"];
  const d = config.clusterAppsDomain;
  const links = d
    ? {
        argoFleetManager: `https://openshift-gitops-server-openshift-gitops.${d}/applications/openshift-gitops/workloads-fleet-manager`,
        ocpFleetManager: `https://console-openshift-console.${d}/k8s/ns/fleet-ops/apps~v1~Deployment/fleet-manager`,
        rhoaiDashboard: `https://rhods-dashboard-redhat-ods-applications.${d}`,
        argoConsole: `https://openshift-gitops-server-openshift-gitops.${d}/applications/openshift-gitops/workloads-console`,
      }
    : null;
  return {
    demoPhase: ds.phase,
    anomalyHistory: ds.anomalyHistory,
    statusLog: ds.statusLog,
    links,
    factories: [
      {
        name: "Factory A",
        namespace: "robot-edge",
        policyVersion: fa?.policyVersion ?? telemetry["fl-07"]?.policyVersion ?? "vla-warehouse-v1.3",
        robotId: "fl-07",
        robotStatus: telemetry["fl-07"]?.robotStatus ?? "active",
        anomalyScore: telemetry["fl-07"]?.anomalyScore ?? 0.12,
        argoSyncStatus: fa?.argoSyncStatus ?? "synced",
        lastHeartbeat: telemetry["fl-07"]?.lastHeartbeat ?? new Date().toISOString(),
      },
      {
        name: "Factory B",
        namespace: "factory-b",
        policyVersion: fb?.policyVersion ?? telemetry["fl-08"]?.policyVersion ?? "vla-warehouse-v1.3",
        robotId: "fl-08",
        robotStatus: telemetry["fl-08"]?.robotStatus ?? "idle",
        anomalyScore: telemetry["fl-08"]?.anomalyScore ?? 0.03,
        argoSyncStatus: fb?.argoSyncStatus ?? "synced",
        lastHeartbeat: telemetry["fl-08"]?.lastHeartbeat ?? new Date().toISOString(),
      },
    ],
  };
});

fastify.get("/api/lineage", async () => {
  const ls = stream.demoState.lineageStatuses;
  return {
    nodes: [
      {
        id: "dataset",
        type: "dataset",
        label: "G1 Teleop Dataset",
        status: ls["dataset"] ?? "completed",
        metadata: {
          repo: "nvidia/PhysicalAI-Robotics-GR00T-Teleop-G1",
          episodes: "311",
          modality: "video + joint positions (43 DOF)",
        },
      },
      {
        id: "pipeline",
        type: "pipeline",
        label: "KFP Pipeline Run",
        status: ls["pipeline"] ?? "completed",
        metadata: {
          pipeline: "vla-finetune",
          dspa_namespace: "vla-training",
          steps: "data_prep → fine_tune → validate → register",
        },
      },
      {
        id: "training",
        type: "training",
        label: "GR00T N1.7-3B Fine-Tune",
        status: ls["training"] ?? "completed",
        metadata: {
          base_model: "nvidia/GR00T-N1.7-3B",
          embodiment: "UNITREE_G1",
          max_steps: "2000",
          batch_size: "64",
          gpu: "NVIDIA L40S",
          final_loss: "0.0342",
        },
      },
      {
        id: "validation",
        type: "validation",
        label: "ONNX Validation",
        status: ls["validation"] ?? "completed",
        metadata: {
          checks: "structure, inference, finite outputs, determinism",
          result: "PASSED",
        },
      },
      {
        id: "model",
        type: "model",
        label: "g1-vla-finetune v1",
        status: ls["model"] ?? "completed",
        metadata: {
          registry: "RHOAI Model Registry",
          format: "ONNX",
          uri: "s3://vla-training/vla-finetune/onnx",
          dataset_repo: "nvidia/PhysicalAI-Robotics-GR00T-Teleop-G1",
          base_model_repo: "nvidia/GR00T-N1.7-3B",
          training_steps: "2000",
          embodiment_tag: "UNITREE_G1",
        },
      },
    ],
    edges: [
      { source: "dataset", target: "pipeline" },
      { source: "pipeline", target: "training" },
      { source: "training", target: "validation" },
      { source: "validation", target: "model" },
    ],
  };
});

registerStreamRoutes(fastify, config);

fastify.get("/api/camera/frame", async (_request, reply) => {
  const frame = stream.getCameraFrame();
  if (!frame) {
    reply.code(503).send({ error: "no camera frame available" });
    return reply;
  }
  reply
    .header("Content-Type", "image/jpeg")
    .header("Cache-Control", "no-cache, no-store")
    .send(frame);
  return reply;
});

fastify.get("/api/events", async (_request, reply) => {
  reply.raw.setHeader("Content-Type", "text/event-stream");
  reply.raw.setHeader("Cache-Control", "no-cache, no-transform");
  reply.raw.setHeader("Connection", "keep-alive");
  reply.raw.setHeader("X-Accel-Buffering", "no");
  reply.raw.flushHeaders();
  // Disable Nagle's algorithm so each SSE event chunk flushes to the TCP
  // socket immediately. Without this, Node buffers small writes (~40ms+)
  // before sending — enough that a whole scenario's events bunch into
  // one batch delivered on completion.
  reply.raw.socket?.setNoDelay(true);

  let sseMsgCount = 0;
  const sseConnectTs = Date.now();
  log.info({ sseListeners: stream.listenerCount("message") + 1 }, "sse.client.connected");

  const onMessage = (msg: FleetMessage): void => {
    sseMsgCount++;
    reply.raw.write(`event: message\ndata: ${JSON.stringify(msg)}\n\n`);
  };
  const onClose = (): void => {
    const durationSec = ((Date.now() - sseConnectTs) / 1000).toFixed(0);
    log.info({ sseMsgCount, durationSec, sseListeners: stream.listenerCount("message") - 1 }, "sse.client.disconnected");
    stream.off("message", onMessage);
  };

  stream.on("message", onMessage);
  reply.raw.on("close", onClose);

  reply.raw.write(`event: hello\ndata: ${JSON.stringify({ topics: config.kafkaTopics })}\n\n`);
  const heartbeat = setInterval(() => {
    reply.raw.write(`event: ping\ndata: ${Date.now()}\n\n`);
  }, 15_000);
  reply.raw.on("close", () => clearInterval(heartbeat));

  return reply;
});

await stream.start();

const shutdown = async (signal: string): Promise<void> => {
  log.info({ signal }, "shutting down");
  await stream.stop();
  await fastify.close();
  process.exit(0);
};
process.on("SIGINT", () => void shutdown("SIGINT"));
process.on("SIGTERM", () => void shutdown("SIGTERM"));

await fastify.listen({ host: "0.0.0.0", port: config.port });
log.info({ port: config.port }, "showcase-console listening");
