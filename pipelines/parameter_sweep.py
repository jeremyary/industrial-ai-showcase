# This project was developed with assistance from AI tools.
"""
Submit 5 parameter sweep runs sequentially to populate MLflow with
comparison data. Runs must be sequential because PVCs are RWO.

Usage:
    python pipelines/parameter_sweep.py

Requires:
    - oc login to the cluster
    - kfp SDK installed (pip install -r requirements.txt)
    - Pipeline compiled (python pipelines/isaac_training_pipeline.py)
"""
import argparse
import subprocess
import time

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import kfp


PIPELINE_FILE = "pipelines/isaac_training_pipeline.yaml"
EXPERIMENT_NAME = "palletjack-parameter-sweep"

SWEEP_CONFIGS = [
    {"name": "baseline",     "params": {"num_frames": 100, "epochs": 2, "batch_size": 4}},
    {"name": "more-frames",  "params": {"num_frames": 200, "epochs": 2, "batch_size": 4}},
    {"name": "larger-batch", "params": {"num_frames": 100, "epochs": 2, "batch_size": 8}},
    {"name": "more-epochs",  "params": {"num_frames": 100, "epochs": 4, "batch_size": 4}},
    {"name": "combined",     "params": {"num_frames": 200, "epochs": 4, "batch_size": 8}},
]


def get_dspa_host(namespace: str) -> str:
    """Discover the DSPA route from the cluster."""
    result = subprocess.check_output(
        ["oc", "get", "route", "-n", namespace, "-o",
         "jsonpath={.items[0].spec.host}"],
    ).decode().strip()
    return f"https://{result}"


def main():
    parser = argparse.ArgumentParser(description="Run parameter sweep")
    parser.add_argument(
        "-n", "--namespace", default="isaac-mlops-poc",
        help="Namespace where DSPA is deployed",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=30,
        help="Seconds between status checks (default: 30)",
    )
    args = parser.parse_args()

    token = subprocess.check_output(["oc", "whoami", "-t"]).decode().strip()
    host = get_dspa_host(args.namespace)
    print(f"DSPA endpoint: {host}")

    client = kfp.Client(host=host, existing_token=token, verify_ssl=False)

    for i, cfg in enumerate(SWEEP_CONFIGS):
        print(f"\n=== Run {i+1}/{len(SWEEP_CONFIGS)}: {cfg['name']} ===")
        print(f"  Params: {cfg['params']}")

        run = client.create_run_from_pipeline_package(
            pipeline_file=PIPELINE_FILE,
            arguments=cfg["params"],
            run_name=f"sweep-{cfg['name']}",
            experiment_name=EXPERIMENT_NAME,
        )
        print(f"  Run ID: {run.run_id}")
        print(f"  Waiting for completion...")

        while True:
            status = client.get_run(run.run_id)
            state = status.state
            if state in ("SUCCEEDED", "FAILED", "SKIPPED", "ERROR"):
                print(f"  Result: {state}")
                break
            time.sleep(args.poll_interval)
            print(f"  ... {state}")

    print("\nParameter sweep complete!")


if __name__ == "__main__":
    main()
