// This project was developed with assistance from AI tools.
import { useEffect, useState } from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Label,
  Spinner,
  Stack,
  StackItem,
} from "@patternfly/react-core";
import type { GovernanceStatus } from "./types.js";
import { fetchGovernance } from "./api.js";

function StatusDot({ ok }: { ok: boolean | null }) {
  const color = ok === true ? "#3E8635" : ok === false ? "#C9190B" : "#6A6E73";
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        backgroundColor: color,
        marginRight: 6,
        verticalAlign: "middle",
      }}
    />
  );
}

function relativeTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function ManagedClustersCard({ data }: { data: GovernanceStatus }) {
  if (data.managedClusters.length === 0) {
    return (
      <Card isFullHeight>
        <CardHeader><CardTitle>Managed Clusters</CardTitle></CardHeader>
        <CardBody>
          <span style={{ color: "#6A6E73", fontSize: 13 }}>No managed clusters found</span>
        </CardBody>
      </Card>
    );
  }
  return (
    <Card isFullHeight>
      <CardHeader><CardTitle>Managed Clusters</CardTitle></CardHeader>
      <CardBody>
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #E0E0E0", textAlign: "left" }}>
              <th style={{ padding: "6px 8px" }}>Cluster</th>
              <th style={{ padding: "6px 8px" }}>Role</th>
              <th style={{ padding: "6px 8px" }}>Available</th>
              <th style={{ padding: "6px 8px" }}>Joined</th>
              <th style={{ padding: "6px 8px" }}>Last Heartbeat</th>
            </tr>
          </thead>
          <tbody>
            {data.managedClusters.map((mc) => (
              <tr key={mc.name} style={{ borderBottom: "1px solid #F0F0F0" }}>
                <td style={{ padding: "6px 8px", fontWeight: 600 }}>{mc.name}</td>
                <td style={{ padding: "6px 8px" }}>{mc.role}</td>
                <td style={{ padding: "6px 8px" }}><StatusDot ok={mc.available} /></td>
                <td style={{ padding: "6px 8px" }}><StatusDot ok={mc.joined} /></td>
                <td style={{ padding: "6px 8px", color: "#6A6E73" }}>{relativeTime(mc.lastHeartbeat)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardBody>
    </Card>
  );
}

function PolicyFederationCard({ data }: { data: GovernanceStatus }) {
  if (data.policies.length === 0) {
    return (
      <Card isFullHeight>
        <CardHeader><CardTitle>Policy Federation</CardTitle></CardHeader>
        <CardBody>
          <span style={{ color: "#6A6E73", fontSize: 13 }}>No ACM policies found</span>
        </CardBody>
      </Card>
    );
  }
  const clusterNames = Array.from(
    new Set(data.policies.flatMap((p) => p.clusterCompliance.map((c) => c.cluster))),
  );
  return (
    <Card isFullHeight>
      <CardHeader><CardTitle>Policy Federation</CardTitle></CardHeader>
      <CardBody>
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #E0E0E0", textAlign: "left" }}>
              <th style={{ padding: "6px 8px" }}>Policy</th>
              <th style={{ padding: "6px 8px" }}>NIST Family</th>
              <th style={{ padding: "6px 8px" }}>Action</th>
              {clusterNames.map((cn) => (
                <th key={cn} style={{ padding: "6px 8px" }}>{cn}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.policies.map((p) => (
              <tr key={p.name} style={{ borderBottom: "1px solid #F0F0F0" }}>
                <td style={{ padding: "6px 8px", fontWeight: 600 }}>{p.displayName}</td>
                <td style={{ padding: "6px 8px", color: "#6A6E73" }}>{p.nistFamily}</td>
                <td style={{ padding: "6px 8px" }}>
                  <Label
                    color={p.remediationAction === "enforce" ? "blue" : "yellow"}
                    isCompact
                  >
                    {p.remediationAction}
                  </Label>
                </td>
                {clusterNames.map((cn) => {
                  const cc = p.clusterCompliance.find((c) => c.cluster === cn);
                  const compliant = cc?.compliant ?? null;
                  return (
                    <td key={cn} style={{ padding: "6px 8px" }}>
                      <StatusDot ok={compliant} />
                      <span style={{ fontSize: 12 }}>
                        {compliant === true ? "Compliant" : compliant === false ? "NonCompliant" : "Pending"}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </CardBody>
    </Card>
  );
}

function SecurityControlsCard({ data }: { data: GovernanceStatus }) {
  return (
    <Card>
      <CardBody>
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #E0E0E0", textAlign: "left" }}>
              <th style={{ padding: "6px 8px" }}>Control</th>
              <th style={{ padding: "6px 8px" }}>Scope</th>
              <th style={{ padding: "6px 8px" }}>Status</th>
              <th style={{ padding: "6px 8px" }}>Detail</th>
            </tr>
          </thead>
          <tbody>
            {data.securityControls.map((sc) => (
              <tr key={sc.name} style={{ borderBottom: "1px solid #F0F0F0" }}>
                <td style={{ padding: "6px 8px", fontWeight: 600 }}>{sc.name}</td>
                <td style={{ padding: "6px 8px", color: "#6A6E73" }}>{sc.scope}</td>
                <td style={{ padding: "6px 8px" }}>
                  {sc.status === "static" ? (
                    <span style={{ color: "#6A6E73" }}>—</span>
                  ) : (
                    <StatusDot ok={sc.status === "active"} />
                  )}
                </td>
                <td style={{ padding: "6px 8px", color: "#6A6E73" }}>{sc.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardBody>
    </Card>
  );
}

function SupplyChainCard({ data }: { data: GovernanceStatus }) {
  const steps = [
    { label: "Git Source", active: true },
    { label: "BuildConfig (UBI9)", active: true },
    { label: "Sigstore Sign", active: true },
    { label: "Registry", active: true },
    { label: "ClusterImagePolicy", active: true },
    { label: "Deploy", active: true },
  ];
  return (
    <Card>
      <CardHeader><CardTitle>Container Build Pipeline</CardTitle></CardHeader>
      <CardBody>
        <Stack hasGutter>
          <StackItem>
            <Flex alignItems={{ default: "alignItemsCenter" }} spaceItems={{ default: "spaceItemsNone" }}>
              {steps.map((step, i) => (
                <FlexItem key={step.label}>
                  <Flex alignItems={{ default: "alignItemsCenter" }} spaceItems={{ default: "spaceItemsNone" }}>
                    <FlexItem>
                      <div style={{
                        display: "inline-flex",
                        alignItems: "center",
                        padding: "6px 12px",
                        borderRadius: 4,
                        backgroundColor: step.active ? "#E7F1FA" : "#F0F0F0",
                        border: `1px solid ${step.active ? "#0066CC" : "#D2D2D2"}`,
                        fontSize: 12,
                        fontWeight: 600,
                        color: step.active ? "#0066CC" : "#6A6E73",
                      }}>
                        <StatusDot ok={step.active} />
                        {step.label}
                      </div>
                    </FlexItem>
                    {i < steps.length - 1 && (
                      <FlexItem>
                        <span style={{ margin: "0 4px", color: "#6A6E73" }}>→</span>
                      </FlexItem>
                    )}
                  </Flex>
                </FlexItem>
              ))}
            </Flex>
          </StackItem>
          <StackItem>
            <div style={{ fontSize: 13, color: "#6A6E73" }}>
              Base images: {data.supplyChain.baseImages.join(", ")} &nbsp;·&nbsp;
              Signing: {data.supplyChain.signingMethod} &nbsp;·&nbsp;
              Verification: {data.supplyChain.verificationPolicy}
            </div>
          </StackItem>
        </Stack>
      </CardBody>
    </Card>
  );
}

function StigComplianceCard({ data }: { data: GovernanceStatus }) {
  return (
    <Card>
      <CardHeader><CardTitle>STIG Compliance</CardTitle></CardHeader>
      <CardBody>
        <Stack hasGutter>
          <StackItem>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #E0E0E0", textAlign: "left" }}>
                  <th style={{ padding: "6px 8px" }}>Profile</th>
                  <th style={{ padding: "6px 8px" }}>Cluster</th>
                  <th style={{ padding: "6px 8px" }}>Schedule</th>
                  <th style={{ padding: "6px 8px" }}>Last Scan</th>
                  <th style={{ padding: "6px 8px" }}>Result</th>
                </tr>
              </thead>
              <tbody>
                {data.stigCompliance.map((s) => (
                  <tr key={s.profile} style={{ borderBottom: "1px solid #F0F0F0" }}>
                    <td style={{ padding: "6px 8px", fontFamily: "monospace", fontSize: 12 }}>{s.profile}</td>
                    <td style={{ padding: "6px 8px" }}>{s.cluster}</td>
                    <td style={{ padding: "6px 8px", color: "#6A6E73" }}>{s.schedule}</td>
                    <td style={{ padding: "6px 8px", color: "#6A6E73" }}>{s.lastScan ?? "—"}</td>
                    <td style={{ padding: "6px 8px" }}>
                      {s.pass !== null ? (
                        <span>
                          <span style={{ color: "#3E8635" }}>{s.pass} pass</span>
                          {" / "}
                          <span style={{ color: "#C9190B" }}>{s.fail} fail</span>
                          {" / "}
                          <span style={{ color: "#F0AB00" }}>{s.remediation} remediation</span>
                        </span>
                      ) : (
                        <span style={{ color: "#6A6E73" }}>Active (scan data on companion)</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </StackItem>
          <StackItem>
            <div style={{ fontSize: 12, color: "#6A6E73", fontStyle: "italic" }}>
              Auto-remediation disabled — remediations are reviewed and applied under human supervision
            </div>
          </StackItem>
        </Stack>
      </CardBody>
    </Card>
  );
}

function ObservabilityCard({ data }: { data: GovernanceStatus }) {
  return (
    <Card>
      <CardHeader><CardTitle>Observability Federation</CardTitle></CardHeader>
      <CardBody>
        <div style={{ fontSize: 13 }}>
          <StatusDot ok={data.observability.enabled} />
          Multi-cluster metrics: {data.observability.enabled ? "Active" : "Not deployed"}
          <span style={{ color: "#6A6E73", marginLeft: 16 }}>
            Retention: {data.observability.retentionRaw}
          </span>
        </div>
      </CardBody>
    </Card>
  );
}

export function PlatformGovernanceTab() {
  const [data, setData] = useState<GovernanceStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const d = await fetchGovernance();
        if (!cancelled) setData(d);
      } catch {
        // leave stale data on error
      }
    };
    void poll();
    const interval = setInterval(() => void poll(), 30_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (!data) {
    return <Spinner size="lg" />;
  }

  return (
    <Stack hasGutter>
      <StackItem>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>Multi-Cluster Federation</div>
        <Flex spaceItems={{ default: "spaceItemsLg" }} alignItems={{ default: "alignItemsStretch" }}>
          <FlexItem flex={{ default: "flex_1" }}>
            <ManagedClustersCard data={data} />
          </FlexItem>
          <FlexItem flex={{ default: "flex_2" }}>
            <PolicyFederationCard data={data} />
          </FlexItem>
        </Flex>
      </StackItem>

      <StackItem>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>Security Controls</div>
        <SecurityControlsCard data={data} />
      </StackItem>

      <StackItem>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>Supply Chain &amp; Compliance</div>
        <Stack hasGutter>
          <StackItem>
            <SupplyChainCard data={data} />
          </StackItem>
          <StackItem>
            <Flex spaceItems={{ default: "spaceItemsLg" }} alignItems={{ default: "alignItemsStretch" }}>
              <FlexItem flex={{ default: "flex_3" }}>
                <StigComplianceCard data={data} />
              </FlexItem>
              <FlexItem flex={{ default: "flex_1" }}>
                <ObservabilityCard data={data} />
              </FlexItem>
            </Flex>
          </StackItem>
        </Stack>
      </StackItem>
    </Stack>
  );
}
