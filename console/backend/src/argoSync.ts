// This project was developed with assistance from AI tools.
import { readFileSync } from "node:fs";
import type { SimpleLogger } from "./kafkaStream.js";

const FLEET_MANAGER_DEPLOY_PATH =
  "infrastructure/gitops/apps/workloads/fleet-manager/deployment.yaml";
const ARGO_APP_NAME = "workloads-fleet-manager";
const ARGO_NAMESPACE = "openshift-gitops";

interface GitHubFileResponse {
  sha: string;
  content: string;
}

interface GitHubCommitResponse {
  commit: { html_url: string };
}

export class ArgoSync {
  private readonly k8sApiBase: string;
  private readonly k8sToken: string;

  constructor(
    private readonly githubToken: string,
    private readonly githubRepo: string,
    private readonly log: SimpleLogger,
  ) {
    this.k8sApiBase = "https://kubernetes.default.svc";
    try {
      this.k8sToken = readFileSync(
        "/var/run/secrets/kubernetes.io/serviceaccount/token",
        "utf-8",
      );
    } catch {
      this.k8sToken = "";
      this.log.warn({}, "argoSync: no SA token — k8s API calls will fail");
    }
  }

  get enabled(): boolean {
    return this.githubToken.length > 0;
  }

  async commitPolicyVersion(
    version: string,
  ): Promise<{ ok: boolean; commitUrl?: string }> {
    if (!this.enabled) return { ok: false };

    try {
      const file = await this.getFileFromGitHub(FLEET_MANAGER_DEPLOY_PATH);
      const content = Buffer.from(file.content, "base64").toString("utf-8");
      const updated = content.replace(
        /POLICY_VERSION\n(\s+)value:\s*\S+/,
        `POLICY_VERSION\n$1value: ${version}`,
      );

      if (updated === content) {
        this.log.info({ version }, "argoSync: POLICY_VERSION already set");
        return { ok: true };
      }

      const commitUrl = await this.putFileToGitHub(
        FLEET_MANAGER_DEPLOY_PATH,
        updated,
        file.sha,
        `chore: promote policy to ${version}`,
      );
      this.log.info({ version, commitUrl }, "argoSync: committed");
      return { ok: true, commitUrl };
    } catch (err) {
      this.log.error(
        { err: (err as Error).message },
        "argoSync: failed to commit policy version",
      );
      return { ok: false };
    }
  }

  async triggerSync(): Promise<boolean> {
    try {
      const body = JSON.stringify({
        operation: {
          initiatedBy: { username: "showcase-console" },
          sync: {
            syncOptions: ["CreateNamespace=true", "ServerSideApply=true"],
          },
        },
      });

      const resp = await fetch(
        `${this.k8sApiBase}/apis/argoproj.io/v1alpha1/namespaces/${ARGO_NAMESPACE}/applications/${ARGO_APP_NAME}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${this.k8sToken}`,
            "Content-Type": "application/merge-patch+json",
          },
          body,
        },
      );

      if (!resp.ok) {
        const text = await resp.text();
        this.log.warn(
          { status: resp.status, body: text.slice(0, 200) },
          "argoSync: sync trigger failed",
        );
        return false;
      }
      this.log.info({}, "argoSync: sync triggered");
      return true;
    } catch (err) {
      this.log.error(
        { err: (err as Error).message },
        "argoSync: sync trigger error",
      );
      return false;
    }
  }

  async getArgoSyncStatus(): Promise<{
    syncStatus: string;
    healthStatus: string;
    operationPhase: string;
  }> {
    try {
      const resp = await fetch(
        `${this.k8sApiBase}/apis/argoproj.io/v1alpha1/namespaces/${ARGO_NAMESPACE}/applications/${ARGO_APP_NAME}`,
        { headers: { Authorization: `Bearer ${this.k8sToken}` } },
      );

      if (!resp.ok) {
        const text = await resp.text();
        this.log.warn(
          { status: resp.status, body: text.slice(0, 200) },
          "argoSync: k8s API error",
        );
        return {
          syncStatus: "Unknown",
          healthStatus: "Unknown",
          operationPhase: "Unknown",
        };
      }

      const app = (await resp.json()) as {
        status?: {
          sync?: { status?: string };
          health?: { status?: string };
          operationState?: { phase?: string };
        };
      };
      return {
        syncStatus: app.status?.sync?.status ?? "Unknown",
        healthStatus: app.status?.health?.status ?? "Unknown",
        operationPhase: app.status?.operationState?.phase ?? "Unknown",
      };
    } catch (err) {
      this.log.error(
        { err: (err as Error).message },
        "argoSync: failed to get sync status",
      );
      return {
        syncStatus: "Unknown",
        healthStatus: "Unknown",
        operationPhase: "Unknown",
      };
    }
  }

  private async getFileFromGitHub(path: string): Promise<GitHubFileResponse> {
    const resp = await fetch(
      `https://api.github.com/repos/${this.githubRepo}/contents/${path}?ref=main`,
      {
        headers: {
          Authorization: `Bearer ${this.githubToken}`,
          Accept: "application/vnd.github.v3+json",
        },
      },
    );
    if (!resp.ok) {
      throw new Error(
        `GitHub GET ${path}: ${resp.status} ${await resp.text()}`,
      );
    }
    return (await resp.json()) as GitHubFileResponse;
  }

  private async putFileToGitHub(
    path: string,
    content: string,
    sha: string,
    message: string,
  ): Promise<string> {
    const resp = await fetch(
      `https://api.github.com/repos/${this.githubRepo}/contents/${path}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${this.githubToken}`,
          Accept: "application/vnd.github.v3+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          content: Buffer.from(content).toString("base64"),
          sha,
          branch: "main",
        }),
      },
    );
    if (!resp.ok) {
      throw new Error(
        `GitHub PUT ${path}: ${resp.status} ${await resp.text()}`,
      );
    }
    const data = (await resp.json()) as GitHubCommitResponse;
    return data.commit?.html_url ?? "";
  }
}
