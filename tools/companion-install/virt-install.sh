#!/usr/bin/env bash
# Boot the companion SNO VM. Assumes:
#   - ISO at /var/lib/libvirt/images/companion-agent.iso (staged from config/).
#   - libvirt + LIBVIRT_DEFAULT_URI=qemu:///system available.
# Idempotent: destroys + undefines any prior 'companion' domain first.
set -euo pipefail

name=companion
mem_mb=65536          # 64 GiB
vcpus=16
disk_gb=250
iso=/var/lib/libvirt/images/companion-agent.iso
disk=/var/lib/libvirt/images/companion-disk.qcow2
mac=52:54:00:0c:01:01  # matches agent-config.yaml
host_iface=eno1        # macvtap source on the Fedora host

if sudo virsh list --all --name | grep -qx "$name"; then
  sudo virsh destroy "$name" 2>/dev/null || true
  sudo virsh undefine --nvram "$name" 2>/dev/null || true
fi
sudo rm -f "$disk"

sudo virt-install \
  --connect qemu:///system \
  --name "$name" \
  --memory "$mem_mb" \
  --vcpus "$vcpus" \
  --cpu host-passthrough \
  --disk path="$disk",size="$disk_gb",format=qcow2,bus=virtio \
  --cdrom "$iso" \
  --network type=direct,source="$host_iface",source_mode=bridge,model=virtio,mac="$mac" \
  --os-variant rhel9.4 \
  --graphics none \
  --boot uefi \
  --noautoconsole
