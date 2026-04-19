# workloads/vla-serving-host/ansible

Provisions the host-native OpenVLA serving runtime on the companion Fedora 43 host.

Per ADR-026: VLA serving runs outside the companion's SNO cluster because AMD
consumer/APU hardware does not have first-class operator-managed device-plugin
coverage on OpenShift. The Fedora 43 host already has a working ROCm HIP stack
(llama.cpp + ollama using `libhipblas` / `librocblas` / `libamdhip64`); this
playbook adds a Quadlet-managed openvla-server container next to them.

## Run

```
cd workloads/vla-serving-host/ansible
ansible-playbook -i inventory.yml site.yml
```

## What it provisions

- `vla` system user (uid 1500) in `render` + `video` groups (for ROCm/DRM access).
- `/var/cache/vla-models` directory, writable by `vla`.
- `/etc/containers/systemd/openvla-server.container` Quadlet unit.
- firewalld rule opening TCP 8000 on the `trusted` zone (reachable from the SNO CNI range via the podman bridge).
- Systemd-managed `openvla-server.service` enabled + running.

## Assumed container image

`quay.io/redhat-physical-ai-reference/vla-serving-host:dev` — built separately from `workloads/vla-serving-host/container/Containerfile` (not written in Phase 1 yet; the podman image is built locally on the companion host for now — `podman build` command documented in `workloads/vla-serving-host/README.md`).

## Not-GitOps-managed

The Quadlet unit is reconciled by Ansible + systemd, not Argo CD. This is the honest trade-off named in ADR-026 — AMD consumer accelerators don't have a Kubernetes-native device-plugin path on OpenShift, so the serving runtime lives beside the OpenShift layer rather than inside it.
