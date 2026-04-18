#!/usr/bin/env bash
# Capture companion cluster state into markdown-ready sections.
# Usage:
#   export KUBECONFIG=~/.kube/companion.kubeconfig
#   tools/companion-install/capture-baseline.sh > /tmp/companion-baseline.txt
#
# Re-runnable. Flag any drift when re-run after material changes.
set -uo pipefail

OC="oc --insecure-skip-tls-verify=true"

hdr() { printf "\n=== %s ===\n" "$*"; }

hdr "1. Cluster identity + version"
$OC version 2>&1 | head -4
$OC get clusterversion -o jsonpath='{.items[0].status.desired.image}{"\n"}'
$OC get infrastructure cluster -o jsonpath='status.platform={.status.platform} name={.status.infrastructureName}{"\n"}'

hdr "2. Access verification"
$OC whoami
$OC auth can-i '*' '*' --all-namespaces
# Try oc debug node — should work on companion (unlike OSD hub)
first_node=$($OC get nodes -o jsonpath='{.items[0].metadata.name}')
echo "oc debug node/$first_node (first 3 lines):"
timeout 15s $OC debug node/"$first_node" --quiet=true -- chroot /host echo "host reachable via debug" 2>&1 | head -3 || echo "debug node failed"

hdr "3. Node inventory"
$OC get nodes -o wide
echo ""
echo "Node resource capacity:"
$OC get nodes -o json 2>/dev/null | jq -r '.items[] | {name:.metadata.name, capacity:.status.capacity, allocatable:.status.allocatable}'

hdr "4. GPU inventory"
gpu_nodes=$($OC get nodes -l nvidia.com/gpu.present=true --no-headers 2>/dev/null | wc -l)
echo "nvidia.com/gpu.present=true node count: $gpu_nodes"
if [ "$gpu_nodes" -gt 0 ]; then
  $OC get nodes -l nvidia.com/gpu.present=true -o json | jq '.items[] | {name:.metadata.name, product:.metadata.labels."nvidia.com/gpu.product"}'
fi

hdr "5. NVIDIA GPU Operator"
$OC get clusterpolicy -A 2>&1 | head -3

hdr "6. NFD"
$OC get subscriptions.operators.coreos.com -A 2>/dev/null | grep -i nfd || echo "not installed"
$OC get nodefeature -A 2>&1 | head -3

hdr "7. RHOAI"
$OC get datasciencecluster -A 2>&1 | head -3

hdr "8. OpenShift Virtualization"
$OC get packagemanifests -n openshift-marketplace kubevirt-hyperconverged -o jsonpath='catalog={.status.catalogSource} defaultChannel={.status.defaultChannel}{"\n"}' 2>&1
$OC get csv -A 2>&1 | grep -iE "kubevirt|openshift-virtualization" | head -3 || echo "no kubevirt csv installed"
echo ""
echo "nested virt on node (requires debug node):"
timeout 15s $OC debug node/"$first_node" --quiet=true -- chroot /host grep -Eo 'svm|vmx' /proc/cpuinfo 2>/dev/null | sort -u | head -3 || echo "debug node unavailable or no virt extensions"

hdr "9. Built-in Sigstore admission"
$OC get crd clusterimagepolicies.config.openshift.io -o jsonpath='{.metadata.name}{"\n"}' 2>&1 | head -2
$OC get clusterimagepolicy.config.openshift.io 2>&1

hdr "9b. FIPS state"
# fips=1 must be present on the RHCOS kernel cmdline
$OC get nodes -o jsonpath='{range .items[*]}{.metadata.name}: {.status.nodeInfo.kernelVersion}{"\n"}{end}'
echo "kernel cmdline fips flag (via debug node):"
timeout 20s $OC debug node/"$first_node" --quiet=true -- chroot /host cat /proc/cmdline 2>/dev/null | tr ' ' '\n' | grep -i fips || echo "  fips= flag not found on cmdline"
echo "host fips_enabled:"
timeout 20s $OC debug node/"$first_node" --quiet=true -- chroot /host cat /proc/sys/crypto/fips_enabled 2>/dev/null || echo "  unavailable"
# FIPS install-host-crypt bypass annotation — should be present because the
# ISO was rendered on a non-FIPS Fedora host (see ADR-017 amendment).
echo "hostcrypt-check-bypassed annotation on ClusterVersion:"
$OC get clusterversion version -o jsonpath='{.metadata.annotations.install\.openshift\.io/hostcrypt-check-bypassed}{"\n"}' 2>&1

hdr "10. Installed operators (Subscription-based)"
$OC get subscriptions.operators.coreos.com -A 2>&1
echo ""
echo "All CSVs (operator installs):"
$OC get csv -A -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase --no-headers 2>&1 | sort -u

hdr "11. Catalog sources"
$OC get catalogsource -n openshift-marketplace -o custom-columns=NAME:.metadata.name,DISPLAY:.spec.displayName,STATUS:.status.connectionState.lastObservedState 2>&1

hdr "12. Network"
$OC get network.config cluster -o jsonpath='{.spec}{"\n"}' 2>&1 | jq . 2>/dev/null | head -20

hdr "13. StorageClasses"
$OC get storageclass 2>&1

hdr "14. ClusterOperator rollup"
$OC get co 2>&1
echo ""
echo "Any CO not Available=True OR Progressing=True OR Degraded=True:"
$OC get co --no-headers 2>&1 | awk '$3 != "True" || $4 != "False" || $5 != "False"'

hdr "DONE"
