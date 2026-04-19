// This project was developed with assistance from AI tools.
import Fastify from "fastify";
import fastifyCors from "@fastify/cors";

import { loadConfig } from "./config.js";
import { FleetStream, type FleetMessage } from "./kafkaStream.js";

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

fastify.post<{ Params: { name: string } }>(
  "/api/scenarios/:name/run",
  async (request, reply) => {
    const { name } = request.params;
    const resp = await fetch(`${config.wmsStubBaseUrl}/scenarios/${name}/run`, {
      method: "POST",
    });
    const body = await resp.text();
    reply.code(resp.status).type("application/json").send(body);
  },
);

fastify.get("/api/scenarios", async () => {
  const resp = await fetch(`${config.wmsStubBaseUrl}/scenarios`);
  return resp.json();
});

fastify.get("/api/events", async (_request, reply) => {
  reply.raw.setHeader("Content-Type", "text/event-stream");
  reply.raw.setHeader("Cache-Control", "no-cache, no-transform");
  reply.raw.setHeader("Connection", "keep-alive");
  reply.raw.setHeader("X-Accel-Buffering", "no");
  reply.raw.flushHeaders();

  const onMessage = (msg: FleetMessage): void => {
    reply.raw.write(`event: message\ndata: ${JSON.stringify(msg)}\n\n`);
  };
  const onClose = (): void => {
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
