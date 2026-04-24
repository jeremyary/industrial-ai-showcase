// This project was developed with assistance from AI tools.
import Fastify from "fastify";
import fastifyCors from "@fastify/cors";

import { loadConfig } from "./config.js";
import { FleetStream, type FleetMessage } from "./kafkaStream.js";
import { registerStreamRoutes } from "./stream.js";

const config = loadConfig();
const fastify = Fastify({
  logger: { level: config.logLevel, name: "showcase-console" },
});
const log = fastify.log;
await fastify.register(fastifyCors, { origin: true });

const stream = new FleetStream(
  config.kafkaBootstrapServers,
  config.kafkaTopics,
  config.kafkaConsumerGroup,
  config.kafkaClientId,
  log,
);

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
