// This project was developed with assistance from AI tools.
import type { FastifyInstance } from "fastify";
import type { AppConfig } from "./config.js";

export function registerStreamRoutes(fastify: FastifyInstance, config: AppConfig): void {
  fastify.get("/api/stream/mjpeg-url", async () => ({
    url: config.mjpegUrl,
  }));
}
