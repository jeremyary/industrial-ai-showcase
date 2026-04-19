# apps/mission-dispatcher

Companion-cluster deployment. Lives in `robot-edge` namespace on companion SNO.

## Why this isn't behind an ApplicationSet yet

Phase 1 applies this directly via `KUBECONFIG=~/.kube/companion.kubeconfig oc apply -k infrastructure/gitops/apps/mission-dispatcher/` during bootstrap. Phase 2 formalizes cross-cluster delivery via ACM ManifestWork (or Argo's managed-cluster delivery pattern already scaffolded in `infrastructure/gitops/apps/hub-acm/`).

## Kafka bootstrap URL

Companion reaches hub Kafka via the **external TLS-terminated route** on the hub (the hub Kafka CR's `tls` listener at `:9093`, exposed through an OpenShift Route). The `configmap.yaml` value is a placeholder; during companion apply:

```
HUB_KAFKA_ROUTE=$(oc get route fleet-kafka-bootstrap -n fleet-ops -o jsonpath='{.spec.host}')
oc --kubeconfig=~/.kube/companion.kubeconfig -n robot-edge create configmap mission-dispatcher-config \
  --from-literal=kafka.bootstrap.servers="${HUB_KAFKA_ROUTE}:443" \
  --from-literal=vla.endpoint.url="http://10.88.0.1:8000/act" \
  --dry-run=client -o yaml | oc --kubeconfig=~/.kube/companion.kubeconfig apply -f -
```

Phase 2 replaces direct cross-cluster Kafka access with **MirrorMaker2** — companion gets its own local broker cluster, and `fleet.missions` + `fleet.telemetry` are bidirectionally mirrored from the hub. That removes this route dependency.

## Host VLA endpoint

`vla.endpoint.url` points at the companion Fedora 43 host's podman-managed OpenVLA server per ADR-026. The default `http://10.88.0.1:8000/act` is the default podman CNI gateway IP reachable from pods; verify once the host VLA systemd unit is up and the firewalld rule permits the SNO CNI range to reach that port.
