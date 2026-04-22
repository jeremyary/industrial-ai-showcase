# This project was developed with assistance from AI tools.
"""One-shot seeder: mirror the Phase-1 warehouse asset tree from the Isaac
asset CDN into our Nucleus.

Follows ADR-027: `small_warehouse_digital_twin.usd` + `Forklift_A01` +
pallet variants are fetched from the public Isaac Sim 6.0 asset CDN
(`omniverse-content-production` S3 bucket, us-west-2) and uploaded to
Nucleus preserving the Isaac-rooted path layout so scenes that reference
`Isaac/Environments/Digital_Twin_Warehouse/...` resolve unchanged.

Runtime: `nvcr.io/nvidia/isaac-sim:6.0.0-dev2` running headless via
`isaacsim.SimulationApp`. That bootstrap is required — `omni.client` pumps
its connection state machine through `omni.kit.async_engine`, which only
starts when the Kit runtime is initialized. Calling `omni.client.list()`
from bare `python.sh -c "..."` hangs because the async engine never runs
and the client's auth callback is never fired.

Once run, Nucleus becomes the authoritative source for Phase-1 assets and
the environment is air-gap-capable — no further CDN dependency at demo time.
"""

from __future__ import annotations

# Bootstrap Kit FIRST — before any omni.* import — so the async engine
# is running by the time omni.client is loaded. `headless=True` skips
# window/rendering; we only need the client + USD stack.
from isaacsim import SimulationApp  # noqa: E402
_app = SimulationApp({"headless": True})

import asyncio  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402


CDN_HOST = "https://omniverse-content-production.s3-us-west-2.amazonaws.com"
S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"

ISAAC_VERSION = os.environ.get("ISAAC_VERSION", "6.0")
ISAAC_PREFIX = f"Assets/Isaac/{ISAAC_VERSION}"

# Roots we explicitly seed. Relative to ISAAC_PREFIX.
SEED_ROOTS = [
    "Isaac/Environments/Digital_Twin_Warehouse",
    # Office MDL materials (../Office/Materials/ relative from warehouse USDs)
    "Isaac/Environments/Office/Materials",
    # Props referenced via ../../Props/ from warehouse scene (resolves to Isaac/Props/)
    "Isaac/Props",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Equipment/Forklifts/Forklift_A",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/Pallets",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/Cardboard_Boxes_on_Pallet",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/Cardboard_Boxes",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/Wood_Crate_on_Pallet",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/Wood_Crates",
    "NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Shipping/Materials",
    # Core NVIDIA MDL material library — relative ../../../NVIDIA/Materials/ from scene USDs
    "NVIDIA/Materials/Base",
    # ArchVis props referenced by warehouse fixtures (outlets, etc.)
    "NVIDIA/Assets/ArchVis/Residential/Decor/PowerOutlets",
]

LOCAL_STAGING = pathlib.Path(os.environ.get("LOCAL_STAGING", "/staging"))

NUCLEUS_HOST = os.environ.get("NUCLEUS_HOST", "nucleus.apps.jary-qs-0323.7w5j.p1.openshiftapps.com")
NUCLEUS_USER = os.environ.get("NUCLEUS_USER", "omniverse")
NUCLEUS_PASS = os.environ.get("NUCLEUS_PASS", "")
NUCLEUS_ROOT = os.environ.get("NUCLEUS_ROOT", "/Projects/showcase/assets")

# S3 keys are like "Assets/Isaac/6.0/NVIDIA/..."; strip that prefix so on
# Nucleus we end up with "<NUCLEUS_ROOT>/Isaac/6.0/NVIDIA/..." rather than
# a doubled "<NUCLEUS_ROOT>/Assets/Isaac/6.0/...".
STRIP_PREFIX = "Assets/"


def s3_list(prefix: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    token: str | None = None
    while True:
        q = f"list-type=2&prefix={urllib.parse.quote(prefix, safe='/')}"
        if token:
            q += f"&continuation-token={urllib.parse.quote(token, safe='')}"
        with urllib.request.urlopen(f"{CDN_HOST}/?{q}", timeout=30) as resp:
            root = ET.fromstring(resp.read())
        for obj in root.findall(S3_NS + "Contents"):
            key = obj.find(S3_NS + "Key").text
            size = int(obj.find(S3_NS + "Size").text)
            keys.append((key, size))
        is_truncated = root.findtext(S3_NS + "IsTruncated") == "true"
        if not is_truncated:
            break
        token = root.findtext(S3_NS + "NextContinuationToken")
    return keys


def download(key: str, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{CDN_HOST}/{urllib.parse.quote(key, safe='/')}"
    with urllib.request.urlopen(url, timeout=300) as src, out_path.open("wb") as dst:
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            dst.write(chunk)


def enumerate_and_download() -> tuple[list[str], int]:
    downloaded: list[str] = []
    total_bytes = 0
    for root in SEED_ROOTS:
        prefix = f"{ISAAC_PREFIX}/{root}/"
        print(f"[listing] {prefix}", flush=True)
        entries = s3_list(prefix)
        print(f"[listing] {prefix}: {len(entries)} objects", flush=True)
        for key, size in entries:
            if not key or key.endswith("/"):
                continue
            local = LOCAL_STAGING / key
            if local.exists() and local.stat().st_size == size:
                continue
            download(key, local)
            downloaded.append(key)
            total_bytes += size
            if len(downloaded) % 50 == 0:
                print(f"  [download] {len(downloaded)} files, {total_bytes / 1e6:.1f} MB", flush=True)
    return downloaded, total_bytes


def walk_deps() -> set[str]:
    """Enumerate asset paths referenced by every USD under staging.

    Relative paths that resolve inside LOCAL_STAGING but don't exist locally
    are flagged so the operator can add their parent prefix to SEED_ROOTS.
    Non-fatal if pxr is unavailable — we rely on Isaac Sim load-time diag.
    """
    try:
        from pxr import Sdf
    except ImportError as e:
        print(f"  [skip] pxr not importable, skipping USD dep walk: {e}", flush=True)
        return set()

    missing: set[str] = set()
    usd_suffixes = (".usd", ".usda", ".usdc", ".usdz")
    for p in LOCAL_STAGING.rglob("*"):
        if not p.is_file() or not p.name.lower().endswith(usd_suffixes):
            continue
        try:
            layer = Sdf.Layer.FindOrOpen(str(p))
        except Exception as e:
            print(f"  [warn] open failed: {p}: {e}", flush=True)
            continue
        if layer is None:
            continue
        try:
            deps = layer.GetCompositionAssetDependencies()
        except AttributeError:
            deps = list(layer.externalReferences)
        for ref in deps:
            if ref.startswith(("http://", "https://", "omniverse://")):
                continue
            resolved = (p.parent / ref).resolve() if not ref.startswith("/") else pathlib.Path(ref).resolve()
            try:
                rel = resolved.relative_to(LOCAL_STAGING)
            except ValueError:
                continue
            if not resolved.exists():
                missing.add(str(rel))
    return missing


def _auth_callback(url: str):
    return (NUCLEUS_USER, NUCLEUS_PASS)


async def upload_tree() -> int:
    import omni.client

    # Hold the subscription for the lifetime of the uploads.
    _sub = omni.client.register_authentication_callback(_auth_callback)  # noqa: F841
    base = f"omniverse://{NUCLEUS_HOST}{NUCLEUS_ROOT}"
    # Ensure root folder exists.
    r = await omni.client.create_folder_async(base)
    if r not in (omni.client.Result.OK, omni.client.Result.ERROR_ALREADY_EXISTS):
        print(f"  [nucleus] create_folder {base}: {r}", flush=True)

    failures = 0
    count = 0
    for p in sorted(LOCAL_STAGING.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(LOCAL_STAGING).as_posix()
        if STRIP_PREFIX and rel.startswith(STRIP_PREFIX):
            rel = rel[len(STRIP_PREFIX):]
        target = f"{base}/{rel}"
        result = await omni.client.copy_async(
            str(p), target, behavior=omni.client.CopyBehavior.OVERWRITE
        )
        if result != omni.client.Result.OK:
            print(f"  [FAIL] {rel} -> {target}: {result}", flush=True)
            failures += 1
        count += 1
        if count % 50 == 0:
            print(f"  [upload] {count} files", flush=True)
    print(f"[upload] total {count} files, {failures} failures", flush=True)
    return failures


def main() -> int:
    LOCAL_STAGING.mkdir(parents=True, exist_ok=True)

    print(f"== stage 1: enumerate + download from CDN ==", flush=True)
    files, total = enumerate_and_download()
    print(f"[download] complete: {len(files)} files, {total / 1e9:.2f} GB staged at {LOCAL_STAGING}", flush=True)

    print(f"== stage 2: walk USD deps for missing refs ==", flush=True)
    missing = walk_deps()
    if missing:
        print(f"[deps] {len(missing)} USD-referenced paths not staged:", flush=True)
        for m in sorted(missing):
            print(f"  {m}", flush=True)
        print("[deps] add their parent prefixes to SEED_ROOTS and re-run.", flush=True)
        # Don't fail — some refs are intentionally remote or optional.
    else:
        print("[deps] all USD refs resolved inside staging", flush=True)

    print(f"== stage 3: upload to Nucleus ==", flush=True)
    failures = asyncio.run(upload_tree())
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        _app.close()
    sys.exit(rc)
