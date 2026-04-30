// This project was developed with assistance from AI tools.
import { readFile } from "node:fs/promises";
import { Agent } from "node:https";
import https from "node:https";

interface GovernanceData {
  managedClusters: {
    name: string;
    role: string;
    available: boolean;
    joined: boolean;
    lastHeartbeat: string;
  }[];
  policies: {
    name: string;
    displayName: string;
    nistFamily: string;
    remediationAction: "enforce" | "inform";
    clusterCompliance: {
      cluster: string;
      compliant: boolean | null;
    }[];
  }[];
  securityControls: {
    name: string;
    scope: string;
    status: "active" | "degraded" | "static";
    detail: string;
  }[];
  supplyChain: {
    baseImages: string[];
    signingMethod: string;
    verificationPolicy: string;
  };
  stigCompliance: {
    profile: string;
    cluster: string;
    schedule: string;
    lastScan: string | null;
    pass: number | null;
    fail: number | null;
    remediation: number | null;
  }[];
  observability: {
    enabled: boolean;
    retentionRaw: string;
    collectorHealthy: boolean | null;
  };
}

const CACHE_TTL_MS = 30_000;
let cachedData: GovernanceData | null = null;
let cacheTimestamp = 0;

async function k8sGet(path: string): Promise<unknown> {
  const token = (await readFile("/var/run/secrets/kubernetes.io/serviceaccount/token", "utf-8")).trim();
  const agent = new Agent({ rejectUnauthorized: false });
  const host = process.env.KUBERNETES_SERVICE_HOST ?? "kubernetes.default.svc";
  const port = process.env.KUBERNETES_SERVICE_PORT ?? "443";
  const url = `https://${host}:${port}${path}`;
  return new Promise((resolve, reject) => {
    const req = https.get(url, { headers: { Authorization: `Bearer ${token}` }, agent }, (res) => {
      let data = "";
      res.on("data", (chunk: Buffer) => { data += chunk.toString(); });
      res.on("end", () => {
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
          resolve(JSON.parse(data));
        } else {
          reject(new Error(`k8s ${path}: ${res.statusCode}`));
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(5000, () => { req.destroy(); reject(new Error("timeout")); });
  });
}

async function fetchManagedClusters(): Promise<GovernanceData["managedClusters"]> {
  try {
    const data = await k8sGet("/apis/cluster.open-cluster-management.io/v1/managedclusters") as {
      items?: Array<{
        metadata: { name: string; labels?: Record<string, string> };
        status?: { conditions?: Array<{ type: string; status: string; lastTransitionTime?: string }> };
      }>;
    };
    return (data.items ?? [])
      .filter((mc) => mc.metadata.name !== "local-cluster")
      .map((mc) => {
        const conds = mc.status?.conditions ?? [];
        const avail = conds.find((c) => c.type === "ManagedClusterConditionAvailable");
        const joined = conds.find((c) => c.type === "ManagedClusterJoined" || c.type === "HubAcceptedManagedCluster");
        return {
          name: mc.metadata.name,
          role: mc.metadata.labels?.["role"] ?? "spoke",
          available: avail?.status === "True",
          joined: joined?.status === "True",
          lastHeartbeat: avail?.status === "True" ? new Date().toISOString() : (avail?.lastTransitionTime ?? new Date().toISOString()),
        };
      });
  } catch {
    return [];
  }
}

async function fetchPolicies(): Promise<GovernanceData["policies"]> {
  const DISPLAY_NAMES: Record<string, { display: string; nist: string }> = {
    "companion-git-source-secret": { display: "Git Source Secret", nist: "CM — Configuration Mgmt" },
    "companion-network-baseline": { display: "Network Baseline", nist: "SC — System & Comms Protection" },
    "companion-rbac-enforcement": { display: "RBAC Enforcement", nist: "AC — Access Control" },
    "companion-compliance-scan": { display: "Compliance Scanning", nist: "AU — Audit & Accountability" },
  };
  try {
    const data = await k8sGet(
      "/apis/policy.open-cluster-management.io/v1/namespaces/open-cluster-management-global-set/policies",
    ) as {
      items?: Array<{
        metadata: { name: string };
        spec: { remediationAction?: string };
        status?: { status?: Array<{ clusternamespace: string; clustername: string; compliant?: string }> };
      }>;
    };
    return (data.items ?? [])
      .filter((p) => p.metadata.name.startsWith("companion-"))
      .map((p) => {
      const info = DISPLAY_NAMES[p.metadata.name] ?? { display: p.metadata.name, nist: "—" };
      return {
        name: p.metadata.name,
        displayName: info.display,
        nistFamily: info.nist,
        remediationAction: (p.spec.remediationAction as "enforce" | "inform") ?? "enforce",
        clusterCompliance: (p.status?.status ?? []).map((s) => ({
          cluster: s.clustername,
          compliant: s.compliant === "Compliant" ? true : s.compliant === "NonCompliant" ? false : null,
        })),
      };
    });
  } catch {
    return [];
  }
}

async function fetchSecurityControls(): Promise<GovernanceData["securityControls"]> {
  const controls: GovernanceData["securityControls"] = [];

  try {
    const vaultPods = await k8sGet("/api/v1/namespaces/vault/pods?labelSelector=app.kubernetes.io/name=vault") as {
      items?: Array<{ status?: { phase?: string } }>;
    };
    const healthy = (vaultPods.items ?? []).some((p) => p.status?.phase === "Running");
    controls.push({
      name: "Vault + VSO",
      scope: "Hub + Companion",
      status: healthy ? "active" : "degraded",
      detail: "KV v2, Kubernetes auth, hourly refresh",
    });
  } catch {
    controls.push({ name: "Vault + VSO", scope: "Hub + Companion", status: "static", detail: "KV v2, Kubernetes auth, hourly refresh" });
  }

  try {
    const apps = await k8sGet("/apis/argoproj.io/v1alpha1/namespaces/openshift-gitops/applications") as {
      items?: Array<unknown>;
    };
    const count = apps.items?.length ?? 0;
    controls.push({
      name: "Argo CD (GitOps)",
      scope: "Hub + Companion",
      status: "active",
      detail: `${count} Applications, drift detection on`,
    });
  } catch {
    controls.push({ name: "Argo CD (GitOps)", scope: "Hub + Companion", status: "static", detail: "Drift detection, PR-driven rollout" });
  }

  try {
    const nps = await k8sGet("/apis/networking.k8s.io/v1/networkpolicies") as {
      items?: Array<{ metadata: { namespace?: string } }>;
    };
    const count = nps.items?.length ?? 0;
    const namespaces = new Set((nps.items ?? []).map((n) => n.metadata.namespace));
    controls.push({
      name: "NetworkPolicies",
      scope: "Per-namespace",
      status: "active",
      detail: `${count} policies across ${namespaces.size} namespaces`,
    });
  } catch {
    controls.push({ name: "NetworkPolicies", scope: "Per-namespace", status: "static", detail: "Explicit ingress rules per workload" });
  }

  controls.push(
    { name: "Kafka TLS", scope: "Hub (3 listeners)", status: "static", detail: "plain / mTLS / external TLS-passthrough" },
    { name: "Istio mTLS", scope: "Nucleus namespace", status: "static", detail: "PeerAuthentication PERMISSIVE" },
    { name: "Per-workload ServiceAccounts", scope: "All namespaces", status: "static", detail: "No default SA usage" },
  );

  return controls;
}

async function fetchObservability(): Promise<GovernanceData["observability"]> {
  try {
    await k8sGet("/apis/observability.open-cluster-management.io/v1beta2/multiclusterobservabilities/observability");
    return { enabled: true, retentionRaw: "30d raw / 60d 5m / 90d 1h", collectorHealthy: null };
  } catch {
    return { enabled: false, retentionRaw: "—", collectorHealthy: null };
  }
}

async function buildGovernanceData(): Promise<GovernanceData> {
  const [managedClusters, policies, securityControls, observability] = await Promise.all([
    fetchManagedClusters(),
    fetchPolicies(),
    fetchSecurityControls(),
    fetchObservability(),
  ]);

  return {
    managedClusters,
    policies,
    securityControls,
    supplyChain: {
      baseImages: ["ubi9/python-312", "ubi9/nodejs-22"],
      signingMethod: "Sigstore keyless signing",
      verificationPolicy: "ClusterImagePolicy on companion (Red Hat release key)",
    },
    stigCompliance: [
      { profile: "ocp4-stig-v2r3", cluster: "companion", schedule: "Daily 06:00 UTC", lastScan: null, pass: null, fail: null, remediation: null },
      { profile: "ocp4-stig-node-v2r3", cluster: "companion", schedule: "Daily 06:00 UTC", lastScan: null, pass: null, fail: null, remediation: null },
      { profile: "rhcos4-stig-v2r3", cluster: "companion", schedule: "Daily 06:00 UTC", lastScan: null, pass: null, fail: null, remediation: null },
    ],
    observability,
  };
}

export async function getGovernanceStatus(): Promise<GovernanceData> {
  const now = Date.now();
  if (cachedData && now - cacheTimestamp < CACHE_TTL_MS) {
    return cachedData;
  }
  cachedData = await buildGovernanceData();
  cacheTimestamp = now;
  return cachedData;
}
