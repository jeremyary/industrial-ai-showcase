// This project was developed with assistance from AI tools.
import { readFile } from "node:fs/promises";
import { Agent } from "undici";

import type { FastifyInstance } from "fastify";

import type { AppConfig } from "./config.js";

interface KasStreamResponse {
  id: string;
  routes: Record<string, unknown>;
  status: { condition: string; status: boolean; message: string };
}

interface StartStreamBody {
  id?: string;
  version?: string;
  profile?: string;
}

export function registerStreamRoutes(fastify: FastifyInstance, config: AppConfig): void {
  const managerBase = config.kasManagerBaseUrl.replace(/\/$/, "");

  // Warm-pool state. Kept in memory on the backend pod — on restart we
  // rediscover by listing active sessions. A single warm session keeps an
  // Isaac Sim pod booted and the MDL/RTX caches hot so `Start` in the
  // Console attaches instantly instead of paying the 3-5 minute cold-boot
  // cost every time.
  let warmEnabled = process.env.KAS_WARM_POOL_ENABLED === "true";
  let warmSessionId: string | null = null;

  const createSession = async (): Promise<string | null> => {
    const resp = await fetch(`${managerBase}/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: config.kasDefaultAppId,
        version: config.kasDefaultAppVersion,
        profile: config.kasDefaultProfile,
      }),
    });
    if (!resp.ok) return null;
    const body = (await resp.json()) as KasStreamResponse;
    return body.id;
  };

  const deleteSession = async (id: string): Promise<void> => {
    await fetch(`${managerBase}/stream`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    }).catch(() => undefined);
  };

  const sessionExists = async (id: string): Promise<boolean> => {
    const resp = await fetch(`${managerBase}/stream/${encodeURIComponent(id)}`).catch(() => null);
    return !!resp && resp.ok;
  };

  // Best-effort reconciliation on startup — pick up any existing session
  // to avoid leaking a previously-created warm pod across backend restarts.
  const reconcileWarmOnStartup = async (): Promise<void> => {
    if (!warmEnabled) return;
    const listResp = await fetch(`${managerBase}/stream`).catch(() => null);
    if (!listResp || !listResp.ok) return;
    const body = (await listResp.json().catch(() => ({}))) as {
      items?: Array<{ id: string }>;
    };
    if (body.items?.length) {
      warmSessionId = body.items[0]?.id ?? null;
    } else {
      warmSessionId = await createSession();
    }
  };
  void reconcileWarmOnStartup();

  const routeHostFor = (sessionId: string): string =>
    config.kasIngressDomain
      ? `kas-${sessionId}-omni-streaming.${config.kasIngressDomain}`
      : "";

  const mjpegHostFor = (sessionId: string): string =>
    config.kasIngressDomain
      ? `mjpeg-${sessionId}-omni-streaming.${config.kasIngressDomain}`
      : "";

  // Looks up the Kit pod's cluster IP so the browser can pass it as
  // `mediaServer`/`mediaPort`. The NVIDIA streaming library then uses it
  // to substitute for the c=0.0.0.0 in Kit's SDP offer — that's the
  // target the browser will CreatePermission for on coturn so media
  // forwarded by Kit actually reaches the TURN allocation.
  let kubeDispatcher: Agent | null = null;
  const getKubeDispatcher = async (): Promise<Agent | null> => {
    if (kubeDispatcher) return kubeDispatcher;
    const ca = await readFile(
      "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
      "utf8",
    ).catch(() => "");
    if (!ca) return null;
    kubeDispatcher = new Agent({ connect: { ca } });
    return kubeDispatcher;
  };

  const kitPodIpFor = async (sessionId: string): Promise<string | null> => {
    const token = await readFile(
      "/var/run/secrets/kubernetes.io/serviceaccount/token",
      "utf8",
    ).catch(() => "");
    const dispatcher = await getKubeDispatcher();
    if (!token || !dispatcher) return null;
    const resp = await fetch(
      `https://kubernetes.default.svc/api/v1/namespaces/omni-streaming/pods?labelSelector=${encodeURIComponent(`sessionId=${sessionId}`)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        dispatcher,
      } as unknown as RequestInit,
    ).catch(() => null);
    if (!resp || !resp.ok) return null;
    const body = (await resp.json()) as {
      items?: Array<{ status?: { podIP?: string } }>;
    };
    return body.items?.[0]?.status?.podIP ?? null;
  };

  // Kit's livestream-rtc plugin corrupts its connection counter if you
  // hit it before the extension has finished loading (observed as
  // `NVST_CCE_DISCONNECTED when m_connectionCount 4294967295` at ~25s of
  // boot). A plain HTTP probe returns non-503 long before Kit is ready.
  //
  // The only reliable "Kit is ready to handle a real browser" signal:
  // complete a WebSocket upgrade AND receive the first peer_info frame
  // that Kit sends once signaling is live.
  const probeSignaling = async (host: string): Promise<boolean> => {
    if (!host) return false;
    return await new Promise((resolve) => {
      let decided = false;
      const settle = (v: boolean) => {
        if (decided) return;
        decided = true;
        try { ws.close(); } catch { /* ignore */ }
        resolve(v);
      };
      const timer = setTimeout(() => settle(false), 3500);
      let ws: WebSocket;
      try {
        ws = new WebSocket(
          `wss://${host}/sign_in?peer_id=probe&version=2`,
        );
      } catch {
        clearTimeout(timer);
        return settle(false);
      }
      ws.addEventListener("message", () => {
        clearTimeout(timer);
        settle(true);
      });
      ws.addEventListener("error", () => {
        clearTimeout(timer);
        settle(false);
      });
      ws.addEventListener("close", () => {
        clearTimeout(timer);
        settle(false);
      });
    });
  };

  fastify.post<{ Body: StartStreamBody }>(
    "/api/stream/start",
    async (request, reply) => {
      // If warm-pool is enabled and the warm session still exists, attach
      // to it instead of spawning a new one. Skips Kit's 3-5 minute boot.
      if (warmEnabled && warmSessionId && (await sessionExists(warmSessionId))) {
        const signalingHost = routeHostFor(warmSessionId);
        const [ready, podIp] = await Promise.all([
          probeSignaling(signalingHost),
          kitPodIpFor(warmSessionId),
        ]);
        return {
          id: warmSessionId,
          status: { condition: "ready", status: ready, message: "" },
          ready,
          signalingHost,
          signalingPort: 443,
          mediaHost: podIp ?? signalingHost,
          mediaPort: 47998,
          mjpegUrl: `https://${mjpegHostFor(warmSessionId)}/stream.mjpg`,
        };
      }
      const payload = {
        id: request.body?.id ?? config.kasDefaultAppId,
        version: request.body?.version ?? config.kasDefaultAppVersion,
        profile: request.body?.profile ?? config.kasDefaultProfile,
      };
      const upstream = await fetch(`${managerBase}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = (await upstream.json()) as KasStreamResponse | { detail: string };
      if (!upstream.ok) {
        reply.code(upstream.status).send(body);
        return;
      }
      const ks = body as KasStreamResponse;
      const signalingHost = routeHostFor(ks.id);
      const [ready, podIp] = await Promise.all([
        probeSignaling(signalingHost),
        kitPodIpFor(ks.id),
      ]);
      return {
        id: ks.id,
        status: ks.status,
        ready,
        signalingHost,
        signalingPort: 443,
        // Kit's pod IP (intra-cluster, reachable from coturn). The browser
        // creates a TURN permission for this address so Kit's UDP media
        // can flow back to the TURN allocation.
        mediaHost: podIp ?? signalingHost,
        mediaPort: 47998,
        mjpegUrl: `https://${mjpegHostFor(ks.id)}/stream.mjpg`,
      };
    },
  );

  fastify.get<{ Params: { id: string } }>(
    "/api/stream/:id",
    async (request, reply) => {
      const { id } = request.params;
      const upstream = await fetch(`${managerBase}/stream/${encodeURIComponent(id)}`);
      const body = (await upstream.json()) as KasStreamResponse | { detail: string };
      if (!upstream.ok) {
        reply.code(upstream.status).send(body);
        return;
      }
      const ks = body as KasStreamResponse;
      const signalingHost = routeHostFor(ks.id);
      const [ready, podIp] = await Promise.all([
        probeSignaling(signalingHost),
        kitPodIpFor(ks.id),
      ]);
      return {
        id: ks.id,
        status: ks.status,
        ready,
        signalingHost,
        signalingPort: 443,
        // Kit's pod IP (intra-cluster, reachable from coturn). The browser
        // creates a TURN permission for this address so Kit's UDP media
        // can flow back to the TURN allocation.
        mediaHost: podIp ?? signalingHost,
        mediaPort: 47998,
        mjpegUrl: `https://${mjpegHostFor(ks.id)}/stream.mjpg`,
      };
    },
  );

  fastify.get("/api/stream/warm", async () => ({
    enabled: warmEnabled,
    sessionId: warmSessionId,
  }));

  fastify.post<{ Body: { enabled?: boolean } }>(
    "/api/stream/warm",
    async (request) => {
      const enabled = request.body?.enabled === true;
      if (enabled && !warmEnabled) {
        warmEnabled = true;
        if (!warmSessionId || !(await sessionExists(warmSessionId))) {
          warmSessionId = await createSession();
        }
      } else if (!enabled && warmEnabled) {
        warmEnabled = false;
        if (warmSessionId) {
          await deleteSession(warmSessionId);
          warmSessionId = null;
        }
      }
      return { enabled: warmEnabled, sessionId: warmSessionId };
    },
  );

  fastify.get("/api/turn", async () => {
    if (!config.turnUrl) return { iceServers: [] };
    return {
      iceServers: [
        {
          urls: config.turnUrl,
          username: config.turnUsername,
          credential: config.turnCredential,
        },
      ],
    };
  });

  fastify.delete<{ Params: { id: string } }>(
    "/api/stream/:id",
    async (request, reply) => {
      const { id } = request.params;
      // If the caller is trying to end the warm session while warm-pool is
      // enabled, keep the pod alive so the next `Start` still attaches
      // instantly. The browser has already disconnected its WebRTC peer
      // by the time this hits; Kit itself is happy to accept a new peer.
      if (warmEnabled && warmSessionId === id) {
        reply.code(204).send();
        return;
      }
      const upstream = await fetch(`${managerBase}/stream`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      if (!upstream.ok) {
        const body = await upstream.text();
        reply.code(upstream.status).type(upstream.headers.get("content-type") ?? "text/plain").send(body);
        return;
      }
      reply.code(204).send();
    },
  );
}
