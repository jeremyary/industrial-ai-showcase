// This project was developed with assistance from AI tools.
import { useEffect, useState } from "react";
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Flex,
  FlexItem,
  Label,
  Stack,
  StackItem,
} from "@patternfly/react-core";
import type { LineageGraph, LineageNode } from "./types.js";
import { fetchLineage } from "./api.js";

function nodeColor(type: LineageNode["type"]): string {
  const colors: Record<string, string> = {
    dataset: "#0066CC",
    pipeline: "#6A6E73",
    training: "#3E8635",
    validation: "#F0AB00",
    model: "#EE0000",
    synthetic: "#8A4FBF",
  };
  return colors[type] ?? "#6A6E73";
}

function statusLabel(status: LineageNode["status"]): "green" | "blue" | "orange" | "red" {
  if (status === "completed") return "green";
  if (status === "running") return "blue";
  if (status === "pending") return "orange";
  return "red";
}

function NodeCard({ node, isSelected, onSelect }: {
  node: LineageNode;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`showcase-lineage-node ${isSelected ? "selected" : ""}`}
      style={{ borderLeftColor: nodeColor(node.type) }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontWeight: 600 }}>{node.label}</span>
        <Label color={statusLabel(node.status)} isCompact>{node.status}</Label>
      </div>
      <div style={{ fontSize: 12, color: "#6A6E73" }}>{node.type}</div>
    </div>
  );
}

function NodeDetail({ node }: { node: LineageNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{node.label}</CardTitle>
      </CardHeader>
      <CardBody>
        <DescriptionList isCompact>
          <DescriptionListGroup>
            <DescriptionListTerm>Type</DescriptionListTerm>
            <DescriptionListDescription>{node.type}</DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup>
            <DescriptionListTerm>Status</DescriptionListTerm>
            <DescriptionListDescription>
              <Label color={statusLabel(node.status)} isCompact>{node.status}</Label>
            </DescriptionListDescription>
          </DescriptionListGroup>
          {Object.entries(node.metadata).map(([key, value]) => (
            <DescriptionListGroup key={key}>
              <DescriptionListTerm>{key}</DescriptionListTerm>
              <DescriptionListDescription style={{ wordBreak: "break-all" }}>
                {value}
              </DescriptionListDescription>
            </DescriptionListGroup>
          ))}
        </DescriptionList>
      </CardBody>
    </Card>
  );
}

export function LineageView() {
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    fetchLineage().then(setGraph).catch(() => undefined);
  }, []);

  const selectedNode = graph?.nodes.find((n) => n.id === selectedId) ?? null;

  return (
    <Flex spaceItems={{ default: "spaceItemsLg" }} alignItems={{ default: "alignItemsStretch" }}>
      <FlexItem flex={{ default: "flex_3" }}>
        <Card isFullHeight>
          <CardHeader>
            <CardTitle>Pipeline Lineage — Data → Model</CardTitle>
          </CardHeader>
          <CardBody>
            {!graph ? (
              <div style={{ color: "#6A6E73" }}>Loading lineage...</div>
            ) : (
              <div className="showcase-lineage-graph">
                <Flex spaceItems={{ default: "spaceItemsMd" }} alignItems={{ default: "alignItemsCenter" }}>
                  {graph.nodes.map((node, i) => (
                    <FlexItem key={node.id}>
                      <Flex alignItems={{ default: "alignItemsCenter" }} spaceItems={{ default: "spaceItemsSm" }}>
                        <FlexItem>
                          <NodeCard
                            node={node}
                            isSelected={selectedId === node.id}
                            onSelect={() => setSelectedId(node.id)}
                          />
                        </FlexItem>
                        {i < graph.nodes.length - 1 && (
                          <FlexItem>
                            <span style={{ color: "#6A6E73", fontSize: 18 }}>→</span>
                          </FlexItem>
                        )}
                      </Flex>
                    </FlexItem>
                  ))}
                </Flex>

                <Stack hasGutter style={{ marginTop: 24 }}>
                  <StackItem>
                    <div style={{ fontSize: 13, color: "#6A6E73", fontStyle: "italic" }}>
                      Every piece of this chain is traceable — from training data to deployed model.
                      Click a node to inspect its metadata.
                    </div>
                  </StackItem>
                </Stack>
              </div>
            )}
          </CardBody>
        </Card>
      </FlexItem>

      <FlexItem flex={{ default: "flex_1" }} style={{ minWidth: 300 }}>
        {selectedNode ? (
          <NodeDetail node={selectedNode} />
        ) : (
          <Card isFullHeight>
            <CardHeader><CardTitle>Details</CardTitle></CardHeader>
            <CardBody>
              <div style={{ color: "#6A6E73" }}>Select a node to view details</div>
            </CardBody>
          </Card>
        )}
      </FlexItem>
    </Flex>
  );
}
