# companion-install

One-time install of the self-managed OpenShift companion cluster per ADR-017. Source material lives here so rebuilds from scratch are reproducible.

## Target shape

- **Host**: Fedora 43 on GMKTec Evo-X2 (AMD Ryzen AI Max+ 395, 32 threads, 124 GiB RAM, 1.9 TB NVMe).
- **Topology**: Single-Node OpenShift in a KVM VM on the Fedora host. VM network: macvtap on `eno1` (direct LAN attach).
- **Version**: OCP 4.21.5 — matches the hub per Session 09 plan D3.
- **Cluster name / baseDomain**: `companion` / `lab.local` → `api.companion.lab.local`, `*.apps.companion.lab.local`.
- **Node IP**: static `10.0.0.80` (nmstate in agent-config).
- **FIPS mode**: `fips: true`, day-1-only. Per ADR-017 the companion is where the FIPS demo lives. The Fedora install host is not itself in FIPS mode, so ISO rendering sets `OPENSHIFT_INSTALL_SKIP_HOSTCRYPT_VALIDATION=1` to skip the installer's host-crypt gate (the static `openshift-install` binary enforces it; the FIPS-capable variant from the `openshift-install-rhel9` tarball would not). The cluster itself comes up genuinely FIPS-enabled (`fips=1` on the RHCOS kernel cmdline, FIPS-validated crypto in the payload); only ignition-bootstrap key generation was off a non-FIPS host, which leaves `install.openshift.io/hostcrypt-check-bypassed=true` on the cluster. Immaterial for demonstrating posture; material for a formal CNSA audit.

## Prerequisites

1. Fedora host with libvirt/QEMU:
   ```bash
   sudo dnf install -y @virtualization nmstate
   sudo systemctl enable --now libvirtd
   sudo usermod -aG libvirt,kvm $USER
   echo 'export LIBVIRT_DEFAULT_URI=qemu:///system' >> ~/.bashrc
   ```
   Fresh shell after the group change. `virt-host-validate qemu` should show no fatals.

2. Red Hat pull secret at `~/companion-install/pull-secret.txt` (download from `console.redhat.com/openshift/install/pull-secret`).

3. Your own SSH public key at `~/.ssh/id_ed25519.pub` (or equivalent). Used as the `core` user's authorized key on the SNO node. The template carries a `__SSH_KEY__` placeholder; the render step substitutes it.

## Install

```bash
cd ~/companion-install
# Download installer + oc client (pinned to hub version)
curl -sLO https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/4.21.5/openshift-install-linux-4.21.5.tar.gz
curl -sLO https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/4.21.5/openshift-client-linux-4.21.5.tar.gz
tar xzf openshift-install-linux-4.21.5.tar.gz openshift-install
tar xzf openshift-client-linux-4.21.5.tar.gz oc
sudo mv oc /usr/local/bin/

# Render install-config.yaml from the template (substitutes pull secret + SSH key)
mkdir -p config
PS=$(jq -c . pull-secret.txt | sed 's|[/&]|\\&|g')
KEY=$(cat ~/.ssh/id_ed25519.pub | sed 's|[/&]|\\&|g')
sed -e "s/__PULL_SECRET__/$PS/" -e "s|__SSH_KEY__|$KEY|" install-config.template.yaml > config/install-config.yaml
cp agent-config.yaml config/

# Generate the ISO (consumes both YAMLs). The env var bypasses the static
# installer's host-FIPS check — see "FIPS mode" note at top of file.
OPENSHIFT_INSTALL_SKIP_HOSTCRYPT_VALIDATION=1 ./openshift-install agent create image --dir config

# Stage ISO in libvirt's pool for SELinux labelling
sudo install -m 0644 -o qemu -g qemu config/agent.x86_64.iso /var/lib/libvirt/images/companion-agent.iso

# Create + boot the VM
bash virt-install.sh
```

## Post-install

```bash
# Install completes in ~45 min. Watch progress from the Fedora host:
./openshift-install agent wait-for bootstrap-complete --dir config
./openshift-install agent wait-for install-complete --dir config

# Kubeconfig lands in config/auth/kubeconfig + config/auth/kubeadmin-password.
# Copy kubeconfig to your workstation:
scp daddo@<host>:~/companion-install/config/auth/kubeconfig ~/.kube/companion.kubeconfig
```

On your workstation, add to `/etc/hosts`:
```
10.0.0.80 api.companion.lab.local
10.0.0.80 oauth-openshift.apps.companion.lab.local
10.0.0.80 console-openshift-console.apps.companion.lab.local
```

Verify:
```bash
KUBECONFIG=~/.kube/companion.kubeconfig oc --insecure-skip-tls-verify get nodes
```

(`--insecure-skip-tls-verify` needed because the cluster cert is for `api.companion.lab.local` but the kubeconfig's server URL was re-pointed. Session 10 captures the proper pattern.)

## What's NOT in this directory

- `pull-secret.txt` — never committed.
- Generated `agent.x86_64.iso` — 1.4 GB, regenerated from templates.
- `config/auth/` — rendered kubeconfigs; workstation copy only.
