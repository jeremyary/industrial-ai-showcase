# This project was developed with assistance from AI tools.
"""
End-to-end pipeline with Cosmos Transfer2.5 sim-to-real augmentation.

Extends the base Isaac training pipeline by adding Cosmos Transfer between
data generation and TFRecord conversion. Synthetic images are transformed
into photorealistic variations using depth, edge, and segmentation control
maps, doubling the effective training data.

Compile:  python pipelines/isaac_cosmos_pipeline.py
Submit:   upload pipelines/isaac_cosmos_pipeline.yaml via RHOAI dashboard or API
"""
from kfp import dsl, compiler
from kfp import kubernetes


# ---------------------------------------------------------------------------
# Step 1: Clone the SDG repo to a shared PVC
# ---------------------------------------------------------------------------
@dsl.container_component
def clone_sdg_repo():
    return dsl.ContainerSpec(
        image="alpine/git:latest",
        command=["/bin/sh", "-c"],
        args=[
            "if [ -d /workspace/sdg/palletjack_sdg ]; then "
            "echo 'SDG repo already cloned, skipping'; "
            "else "
            "rm -rf /workspace/sdg/lost+found && "
            "git clone --depth 1 "
            "https://github.com/NVIDIA-AI-IOT/synthetic_data_generation_training_workflow.git "
            "/workspace/sdg; "
            "fi"
        ],
    )


# ---------------------------------------------------------------------------
# Step 2: Generate synthetic data with Isaac Sim Replicator
# ---------------------------------------------------------------------------
@dsl.container_component
def generate_synthetic_data(
    num_frames: int,
    height: int,
    width: int,
    distractors: str,
):
    return dsl.ContainerSpec(
        image="nvcr.io/nvidia/isaac-sim:4.5.0",
        command=["/bin/bash"],
        args=[
            "-c",
            'echo "=== Isaac Sim Headless Datagen ===" && nvidia-smi && '
            "cd /workspace/sdg/palletjack_sdg && "
            "/isaac-sim/python.sh standalone_palletjack_sdg.py "
            '--headless True --height "$1" --width "$2" '
            '--num_frames "$3" --distractors "$4" '
            '--data_dir "/output/palletjack_data/$4" && '
            'echo "=== Datagen complete ===" && '
            'echo "RGB: $(ls /output/palletjack_data/$4/Camera/rgb/ | wc -l)" && '
            'echo "Labels: $(ls /output/palletjack_data/$4/Camera/object_detection/ | wc -l)"',
            "--",  # end of bash options
            height, width, num_frames, distractors,
        ],
    )


# ---------------------------------------------------------------------------
# Step 3: Prepare Cosmos Transfer control maps (no GPU)
# ---------------------------------------------------------------------------
@dsl.container_component
def prepare_control_maps(
    clip_length: int,
    height: int,
    width: int,
):
    return dsl.ContainerSpec(
        image="quay.io/jary/cosmos-prep:latest",
        command=["python", "/app/prepare_control_maps.py"],
        args=[
            "--input-dir", "/output/palletjack_data/warehouse/Camera",
            "--output-dir", "/output/cosmos_clips",
            "--clip-length", clip_length,
            "--height", height,
            "--width", width,
        ],
    )


# ---------------------------------------------------------------------------
# Step 4: Deploy Cosmos Transfer NIM as a temporary pod (no GPU for launcher)
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=["kubernetes>=29.0.0"],
)
def deploy_cosmos_nim(
    namespace: str,
    gpu_product: str,
) -> str:
    """Deploy Cosmos Transfer2.5 NIM as a temporary pod and wait for health."""
    import time
    from kubernetes import client, config

    config.load_incluster_config()
    v1 = client.CoreV1Api()

    pod_name = "cosmos-transfer-nim"
    service_name = "cosmos-transfer-nim"

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            namespace=namespace,
            labels={"app": "cosmos-transfer-nim"},
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="nim",
                    image="nvcr.io/nim/nvidia/cosmos-transfer2.5-2b:1.0.0",
                    ports=[client.V1ContainerPort(container_port=8000)],
                    resources=client.V1ResourceRequirements(
                        limits={"nvidia.com/gpu": "1", "memory": "48Gi", "cpu": "8"},
                        requests={"nvidia.com/gpu": "1", "memory": "32Gi", "cpu": "4"},
                    ),
                    env=[
                        client.V1EnvVar(
                            name="NGC_API_KEY",
                            value_from=client.V1EnvVarSource(
                                secret_key_ref=client.V1SecretKeySelector(
                                    name="ngc-api-key",
                                    key="NGC_API_KEY",
                                ),
                            ),
                        ),
                        # Reduce PyTorch CUDA memory fragmentation during FP8 calibration.
                        # Without this, calibration OOMs on L40S due to ~5GB reserved-but-unused.
                        client.V1EnvVar(
                            name="PYTORCH_ALLOC_CONF",
                            value="expandable_segments:True",
                        ),
                    ],
                    volume_mounts=[
                        client.V1VolumeMount(
                            name="shm", mount_path="/dev/shm",
                        ),
                        # Cache built TRT engines so subsequent starts skip calibration
                        client.V1VolumeMount(
                            name="nim-cache", mount_path="/opt/nim/.cache",
                        ),
                    ],
                    readiness_probe=client.V1Probe(
                        http_get=client.V1HTTPGetAction(
                            path="/v1/health/ready", port=8000,
                        ),
                        initial_delay_seconds=30,
                        period_seconds=10,
                    ),
                ),
            ],
            volumes=[
                client.V1Volume(
                    name="shm",
                    empty_dir=client.V1EmptyDirVolumeSource(
                        medium="Memory", size_limit="32Gi",
                    ),
                ),
                client.V1Volume(
                    name="nim-cache",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name="nim-cache",
                    ),
                ),
            ],
            # NIM runs as UID 1000; fsGroup ensures PVC is group-writable
            security_context=client.V1PodSecurityContext(fs_group=1000),
            node_selector={"nvidia.com/gpu.product": gpu_product},
            tolerations=[
                client.V1Toleration(
                    key="nvidia.com/gpu", operator="Exists", effect="NoSchedule",
                ),
            ],
            image_pull_secrets=[
                client.V1LocalObjectReference(name="ngc-secret"),
            ],
            restart_policy="Never",
        ),
    )

    try:
        v1.delete_namespaced_pod(pod_name, namespace)
        print(f"Deleted existing pod {pod_name}, waiting for cleanup...")
        time.sleep(10)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise

    v1.create_namespaced_pod(namespace=namespace, body=pod)
    print(f"Created pod {pod_name}")

    svc = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=service_name,
            namespace=namespace,
            labels={"app": "cosmos-transfer-nim"},
        ),
        spec=client.V1ServiceSpec(
            selector={"app": "cosmos-transfer-nim"},
            ports=[client.V1ServicePort(port=8000, target_port=8000)],
        ),
    )
    try:
        v1.create_namespaced_service(namespace=namespace, body=svc)
        print(f"Created service {service_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print(f"Service {service_name} already exists")
        else:
            raise

    # NIM needs time for model download, TRT engine build, and warmup inference.
    # First startup on a new GPU type can take 15+ minutes.
    NIM_READINESS_TIMEOUT_ITER = 120
    NIM_POLL_INTERVAL_S = 10
    endpoint = f"http://{service_name}.{namespace}.svc:8000"
    print(f"Waiting for NIM to be ready at {endpoint}...")
    for i in range(NIM_READINESS_TIMEOUT_ITER):
        time.sleep(NIM_POLL_INTERVAL_S)
        try:
            pod_status = v1.read_namespaced_pod_status(pod_name, namespace)
            phase = pod_status.status.phase
            conditions = pod_status.status.conditions or []
            ready = any(
                c.type == "Ready" and c.status == "True" for c in conditions
            )
            if ready:
                print(f"NIM pod is ready after {(i + 1) * 10}s")
                return endpoint
            if phase == "Failed":
                raise RuntimeError(f"NIM pod failed: {pod_status.status}")
            print(f"  [{(i + 1) * 10}s] phase={phase}, ready={ready}")
        except client.exceptions.ApiException:
            print(f"  [{(i + 1) * 10}s] waiting for pod...")

    timeout_min = NIM_READINESS_TIMEOUT_ITER * NIM_POLL_INTERVAL_S // 60
    raise TimeoutError(f"Cosmos NIM pod did not become ready within {timeout_min} minutes")


# ---------------------------------------------------------------------------
# Step 5: Run Cosmos Transfer augmentation (no GPU — calls NIM API)
# ---------------------------------------------------------------------------
@dsl.container_component
def run_cosmos_augmentation(
    cosmos_endpoint: str,
    cosmos_prompt: str,
    edge_weight: float,
    depth_weight: float,
    seg_weight: float,
):
    return dsl.ContainerSpec(
        image="quay.io/jary/cosmos-prep:latest",
        command=["python", "/app/run_cosmos_augmentation.py"],
        args=[
            "--clips-dir", "/output/cosmos_clips",
            "--output-dir", "/output/cosmos_augmented/Camera",
            "--labels-dir", "/output/palletjack_data/warehouse/Camera/object_detection",
            "--endpoint", cosmos_endpoint,
            "--prompt", cosmos_prompt,
            "--edge-weight", edge_weight,
            "--depth-weight", depth_weight,
            "--seg-weight", seg_weight,
        ],
    )


# ---------------------------------------------------------------------------
# Step 6: Teardown Cosmos NIM pod (no GPU)
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=["kubernetes>=29.0.0"],
)
def teardown_cosmos_nim(
    namespace: str,
):
    """Delete the temporary Cosmos Transfer NIM pod and service."""
    from kubernetes import client, config

    config.load_incluster_config()
    v1 = client.CoreV1Api()

    for resource, delete_fn in [
        ("pod", lambda: v1.delete_namespaced_pod("cosmos-transfer-nim", namespace)),
        ("service", lambda: v1.delete_namespaced_service("cosmos-transfer-nim", namespace)),
    ]:
        try:
            delete_fn()
            print(f"Deleted {resource} cosmos-transfer-nim")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"{resource} cosmos-transfer-nim already deleted")
            else:
                raise


# ---------------------------------------------------------------------------
# Step 7: Merge original + augmented data (no GPU)
# ---------------------------------------------------------------------------
@dsl.container_component
def merge_datasets():
    return dsl.ContainerSpec(
        image="registry.access.redhat.com/ubi9/ubi:latest",
        command=["/bin/bash", "-c"],
        args=[
            "echo '=== Merging original + augmented data ===' && "
            "mkdir -p /output/palletjack_data_merged/warehouse/Camera/rgb && "
            "mkdir -p /output/palletjack_data_merged/warehouse/Camera/object_detection && "
            # Copy original data
            "cp /output/palletjack_data/warehouse/Camera/rgb/*.png "
            "   /output/palletjack_data_merged/warehouse/Camera/rgb/ && "
            "cp /output/palletjack_data/warehouse/Camera/object_detection/*.txt "
            "   /output/palletjack_data_merged/warehouse/Camera/object_detection/ && "
            "ORIG=$(ls /output/palletjack_data_merged/warehouse/Camera/rgb/ | wc -l) && "
            "echo \"Original images: $ORIG\" && "
            # Copy augmented data (if it exists)
            "if [ -d /output/cosmos_augmented/Camera/rgb ]; then "
            "  cp /output/cosmos_augmented/Camera/rgb/*.png "
            "     /output/palletjack_data_merged/warehouse/Camera/rgb/ 2>/dev/null; "
            "  cp /output/cosmos_augmented/Camera/object_detection/*.txt "
            "     /output/palletjack_data_merged/warehouse/Camera/object_detection/ 2>/dev/null; "
            "fi && "
            "TOTAL=$(ls /output/palletjack_data_merged/warehouse/Camera/rgb/ | wc -l) && "
            "AUG=$((TOTAL - ORIG)) && "
            "echo \"Augmented images: $AUG\" && "
            "echo \"Total merged: $TOTAL images\" && "
            "echo '=== Merge complete ==='"
        ],
    )


# ---------------------------------------------------------------------------
# Step 8: Convert KITTI annotations to TFRecords
# ---------------------------------------------------------------------------
@dsl.container_component
def convert_to_tfrecords():
    return dsl.ContainerSpec(
        image="nvcr.io/nvidia/tao/tao-toolkit:5.0.0-tf1.15.5",
        command=["/bin/bash", "-c"],
        args=[
            "echo '=== Converting KITTI to TFRecords (merged data) ===' && "
            "mkdir -p /workspace/tfrecords/warehouse && "
            "detectnet_v2 dataset_convert "
            "-d /workspace/specs/tfrecords_warehouse_merged.txt "
            "-o /workspace/tfrecords/warehouse/tfrecord && "
            "echo '=== Conversion complete ===' && "
            "ls -la /workspace/tfrecords/warehouse/"
        ],
    )


# ---------------------------------------------------------------------------
# Step 9: Train DetectNet_v2 via Kubeflow Trainer (TrainJob)
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=["kubeflow==0.4.0"],
)
def train_detectnet(
    training_runtime: str,
):
    """Launch TAO DetectNet_v2 training as a TrainJob and wait for completion."""
    from kubeflow.trainer import TrainerClient

    client = TrainerClient()

    job_name = client.train(runtime=training_runtime)
    print(f"Created TrainJob {job_name}")

    print("Waiting for TrainJob to complete...")
    client.wait_for_job_status(
        name=job_name,
        status={"Complete"},
        timeout=3600,
        polling_interval=10,
    )
    print(f"TrainJob {job_name} completed successfully")


# ---------------------------------------------------------------------------
# Step 10a: Export trained model to ONNX for serving
# ---------------------------------------------------------------------------
@dsl.container_component
def export_to_onnx(encryption_key: str):
    return dsl.ContainerSpec(
        image="nvcr.io/nvidia/tao/tao-toolkit:5.0.0-tf1.15.5",
        command=["/bin/bash", "-c"],
        args=[
            "echo '=== TAO DetectNet_v2 Export to ONNX ===' && "
            "nvidia-smi && "
            "detectnet_v2 export "
            '-m /workspace/output/resnet18_palletjack/weights/model.hdf5 '
            '-o /workspace/output/resnet18_palletjack/weights/model.onnx '
            '-k "$1" '
            "--data_type fp32 && "
            "echo '=== Export complete ===' && "
            "ls -la /workspace/output/resnet18_palletjack/weights/model.onnx",
            "--",
            encryption_key,
        ],
    )


# ---------------------------------------------------------------------------
# Step 10b: Evaluate results and register model in MLflow
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=["mlflow>=3.5.0", "boto3>=1.34.0", "model-registry>=0.3.0"],
)
def evaluate_and_register(
    mlflow_tracking_uri: str,
    mlflow_s3_endpoint: str,
    experiment_name: str,
    model_registry_url: str,
    s3_model_bucket: str,
    num_frames: int,
    height: int,
    width: int,
    distractors: str,
    epochs: int,
    batch_size: int,
    map_threshold: float,
    cosmos_augmented: bool,
    cosmos_prompt: str,
    kfp_metrics: dsl.Output[dsl.Metrics],
) -> str:
    """Parse training status.json, log metrics/artifacts to MLflow, upload ONNX to S3, register model."""
    import json
    import os

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = mlflow_s3_endpoint
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get("MINIO_ACCESS_KEY", "minio")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get("MINIO_SECRET_KEY", "minio123")
    os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
    sa_token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    sa_ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    if os.path.exists(sa_token_path):
        with open(sa_token_path) as f:
            os.environ["MLFLOW_TRACKING_TOKEN"] = f.read().strip()
    workspace = "default"
    if os.path.exists(sa_ns_path):
        with open(sa_ns_path) as f:
            workspace = f.read().strip()

    import mlflow
    from mlflow.tracking.request_header.registry import _request_header_provider_registry

    class _WorkspaceHeaderProvider:
        """Injects X-MLFLOW-WORKSPACE header for RHOAI MLflow K8s auth."""
        def in_context(self):
            return True
        def request_headers(self):
            return {"X-MLFLOW-WORKSPACE": workspace}

    _request_header_provider_registry.register(_WorkspaceHeaderProvider)

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)

    # TAO writes cumulative NDJSON to status.json; extract the last SUCCESS session
    status_file = "/workspace/output/resnet18_palletjack/status.json"
    with open(status_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    last_success_idx = None
    for i in range(len(entries) - 1, -1, -1):
        if entries[i].get("status") == "SUCCESS":
            last_success_idx = i
            break

    session_start_idx = 0
    if last_success_idx is not None:
        for i in range(last_success_idx, -1, -1):
            if entries[i].get("status") == "STARTED":
                session_start_idx = i
                break
        session = entries[session_start_idx:last_success_idx + 1]
    else:
        session = entries

    final_map = 0.0
    final_loss = 0.0
    model_size_mb = 0.0
    param_count_m = 0.0
    per_epoch_metrics = []

    for entry in session:
        kpi = entry.get("kpi", {})
        graphical = entry.get("graphical", {})
        epoch = entry.get("epoch")

        if "mean average precision" in kpi:
            final_map = kpi["mean average precision"]
        if "loss" in graphical:
            final_loss = graphical["loss"]
        if "size" in kpi:
            model_size_mb = kpi["size"]
        if "param_count" in kpi:
            param_count_m = kpi["param_count"]

        if epoch is not None and "loss" in graphical:
            per_epoch_metrics.append({
                "epoch": epoch,
                "loss": graphical["loss"],
                "learning_rate": graphical.get("learning_rate", ""),
                "map": kpi.get("mean average precision", 0.0),
                "val_cost": kpi.get("validation cost", 0.0),
            })

    model_path = "/workspace/output/resnet18_palletjack/weights/model.hdf5"
    onnx_path = "/workspace/output/resnet18_palletjack/weights/model.onnx"
    model_exists = os.path.exists(model_path)
    onnx_exists = os.path.exists(onnx_path)

    print(f"Final mAP: {final_map}")
    print(f"Final loss: {final_loss}")
    print(f"Model size: {model_size_mb:.1f} MB")
    print(f"Model exists: {model_exists}")
    print(f"ONNX exists: {onnx_exists}")
    print(f"mAP threshold: {map_threshold}")
    print(f"Cosmos augmented: {cosmos_augmented}")

    with mlflow.start_run() as run:
        params = {
            "num_frames": num_frames,
            "image_height": height,
            "image_width": width,
            "distractors": distractors,
            "epochs": epochs,
            "batch_size": batch_size,
            "architecture": "resnet18",
            "detector": "detectnet_v2",
            "cosmos_augmented": cosmos_augmented,
        }
        if cosmos_augmented:
            params["cosmos_prompt"] = cosmos_prompt
        mlflow.log_params(params)

        mlflow.log_metrics({
            "final_map": final_map,
            "final_loss": final_loss,
            "model_size_mb": model_size_mb,
            "param_count_millions": param_count_m,
        })

        kfp_metrics.log_metric("final_map", final_map)
        kfp_metrics.log_metric("final_loss", final_loss)
        kfp_metrics.log_metric("model_size_mb", model_size_mb)
        kfp_metrics.log_metric("param_count_millions", param_count_m)
        kfp_metrics.log_metric("cosmos_augmented", 1.0 if cosmos_augmented else 0.0)

        for em in per_epoch_metrics:
            mlflow.log_metrics(
                {"epoch_loss": em["loss"], "epoch_map": em["map"],
                 "epoch_val_cost": em["val_cost"]},
                step=em["epoch"],
            )

        mlflow.log_artifact(status_file, artifact_path="training_output")

        spec_file = "/workspace/specs/training_resnet18.txt"
        if os.path.exists(spec_file):
            mlflow.log_artifact(spec_file, artifact_path="specs")

        if model_exists and final_map >= map_threshold:
            mlflow.log_artifact(model_path, artifact_path="model")
            if onnx_exists:
                mlflow.log_artifact(onnx_path, artifact_path="model")
            client = mlflow.MlflowClient()
            try:
                client.create_registered_model("palletjack-detectnet-v2")
            except mlflow.exceptions.MlflowException:
                pass
            client.create_model_version(
                name="palletjack-detectnet-v2",
                source=f"runs:/{run.info.run_id}/model",
                run_id=run.info.run_id,
            )
            result = f"REGISTERED (mAP={final_map:.4f} >= {map_threshold})"
        elif model_exists:
            mlflow.log_artifact(model_path, artifact_path="model")
            if onnx_exists:
                mlflow.log_artifact(onnx_path, artifact_path="model")
            result = f"LOGGED_ONLY (mAP={final_map:.4f} < {map_threshold})"
        else:
            result = "NO_MODEL (model file not found)"

        mlflow.set_tag("result", result)
        if cosmos_augmented:
            mlflow.set_tag("augmentation", "cosmos-transfer-2.5")
        print(f"Result: {result}")
        print(f"MLflow run ID: {run.info.run_id}")

    s3_model_uri = ""
    if onnx_exists:
        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=mlflow_s3_endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        s3_key = "palletjack-detectnet-v2/1/model.onnx"
        s3.upload_file(onnx_path, s3_model_bucket, s3_key)
        s3_model_uri = f"s3://{s3_model_bucket}/palletjack-detectnet-v2/1/"
        print(f"Uploaded ONNX to {s3_model_uri}")

    if model_exists and final_map >= map_threshold:
        from model_registry import ModelRegistry

        registry = ModelRegistry(
            server_address=model_registry_url,
            port=8080,
            author="isaac-pipeline",
            is_secure=False,
        )
        model_uri = s3_model_uri if s3_model_uri else f"runs:/{run.info.run_id}/model"
        model_fmt = "onnx" if onnx_exists else "hdf5"
        rm = registry.register_model(
            "palletjack-detectnet-v2",
            model_uri,
            model_format_name=model_fmt,
            model_format_version="1",
            version=run.info.run_id[:8],
            description=(
                f"DetectNet_v2 ResNet-18 palletjack detector. "
                f"mAP={final_map:.4f}, loss={final_loss:.6f}, "
                f"{num_frames} frames, {epochs} epochs."
                f"{' Cosmos Transfer augmented.' if cosmos_augmented else ''}"
            ),
            metadata={
                "mlflow_run_id": run.info.run_id,
                "final_map": final_map,
                "final_loss": final_loss,
                "model_size_mb": model_size_mb,
                "num_frames": num_frames,
                "epochs": epochs,
                "batch_size": batch_size,
                "distractors": distractors,
                "cosmos_augmented": cosmos_augmented,
            },
        )
        print(f"RHOAI Model Registry: registered {rm.name} (format={model_fmt})")

    return result


# ---------------------------------------------------------------------------
# Step 10c: Deploy model as a KServe InferenceService
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=["kubernetes>=29.0.0"],
)
def deploy_inference_service(
    model_name: str,
    serving_runtime: str,
    storage_uri: str,
    namespace: str,
    gpu_product: str,
):
    """Create or update a KServe InferenceService for the trained model."""
    from kubernetes import client, config

    config.load_incluster_config()
    api = client.CustomObjectsApi()

    isvc = {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": model_name,
            "namespace": namespace,
            "annotations": {
                "serving.kserve.io/deploymentMode": "RawDeployment",
            },
        },
        "spec": {
            "predictor": {
                "model": {
                    "modelFormat": {"name": "onnx"},
                    "runtime": f"{serving_runtime}-runtime",
                    "storageUri": storage_uri,
                },
                "serviceAccountName": "model-serving",
            },
        },
    }

    if serving_runtime == "triton":
        isvc["spec"]["predictor"]["nodeSelector"] = {
            "nvidia.com/gpu.product": gpu_product,
        }
        isvc["spec"]["predictor"]["tolerations"] = [
            {"key": "nvidia.com/gpu", "operator": "Exists", "effect": "NoSchedule"},
        ]

    try:
        api.get_namespaced_custom_object(
            group="serving.kserve.io",
            version="v1beta1",
            namespace=namespace,
            plural="inferenceservices",
            name=model_name,
        )
        api.patch_namespaced_custom_object(
            group="serving.kserve.io",
            version="v1beta1",
            namespace=namespace,
            plural="inferenceservices",
            name=model_name,
            body=isvc,
        )
        print(f"Updated InferenceService {model_name}")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            api.create_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=namespace,
                plural="inferenceservices",
                body=isvc,
            )
            print(f"Created InferenceService {model_name}")
        else:
            raise

    print(f"InferenceService {model_name} deployed with runtime {serving_runtime}-runtime")
    print(f"Model source: {storage_uri}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _configure_gpu(task):
    """Standard GPU scheduling for NVIDIA containers on OpenShift."""
    task.set_accelerator_type("nvidia.com/gpu")
    task.set_accelerator_limit("1")
    task.set_memory_limit("32Gi")
    task.set_cpu_limit("8")
    task.set_memory_request("16Gi")
    task.set_cpu_request("4")
    kubernetes.add_node_selector(task, "nvidia.com/gpu.product", "NVIDIA-L40S")
    kubernetes.add_toleration(
        task, key="nvidia.com/gpu", operator="Exists", effect="NoSchedule",
    )


def _configure_pvc(
    task,
    workspace=False,
    output=False,
    synthetic_data=False,
    synthetic_data_merged=False,
    model_artifacts=False,
    specs=False,
    tfrecords=False,
    pretrained=False,
):
    """Mount standard PVCs and volumes for pipeline tasks."""
    if workspace:
        kubernetes.mount_pvc(
            task, pvc_name="workspace-data", mount_path="/workspace/sdg",
        )
    if output:
        kubernetes.mount_pvc(
            task, pvc_name="synthetic-data", mount_path="/output",
        )
    if synthetic_data:
        kubernetes.mount_pvc(
            task, pvc_name="synthetic-data", mount_path="/workspace/data",
        )
    if synthetic_data_merged:
        # Mount the same PVC but at a path where the merged data lives.
        # The TFRecord spec points at /workspace/data/palletjack_data_merged/...
        kubernetes.mount_pvc(
            task, pvc_name="synthetic-data", mount_path="/workspace/data",
        )
    if model_artifacts:
        kubernetes.mount_pvc(
            task, pvc_name="model-artifacts", mount_path="/workspace/output",
        )
    if specs:
        kubernetes.use_config_map_as_volume(
            task, config_map_name="tao-specs", mount_path="/workspace/specs",
        )
    if tfrecords:
        kubernetes.mount_pvc(
            task, pvc_name="tfrecords", mount_path="/workspace/tfrecords",
        )
    if pretrained:
        kubernetes.empty_dir_mount(
            task, volume_name="pretrained", mount_path="/workspace/pretrained",
        )


# ---------------------------------------------------------------------------
# Pipeline definition
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name="isaac-cosmos-synth-train-serve",
    description=(
        "Synthetic data generation with Isaac Sim Replicator, "
        "Cosmos Transfer2.5 sim-to-real augmentation, "
        "model training with TAO DetectNet_v2, ONNX export, "
        "experiment tracking + model registration with MLflow, "
        "and deployment as a KServe InferenceService."
    ),
)
def isaac_cosmos_pipeline(
    num_frames: int = 100,
    height: int = 544,
    width: int = 960,
    distractors: str = "warehouse",
    epochs: int = 2,
    batch_size: int = 4,
    training_runtime: str = "tao-detectnet",
    encryption_key: str = "tao_key",
    mlflow_tracking_uri: str = "https://mlflow.redhat-ods-applications.svc:8443",
    mlflow_s3_endpoint: str = "http://minio.isaac-mlops-poc.svc:9000",
    experiment_name: str = "palletjack-cosmos-augmented",
    model_registry_url: str = "http://isaac-registry.rhoai-model-registries.svc.cluster.local",
    map_threshold: float = 0.0,
    serving_runtime: str = "ovms",
    s3_model_bucket: str = "models",
    # Cosmos Transfer parameters
    cosmos_clip_length: int = 25,
    cosmos_prompt: str = "Industrial warehouse, bright overhead fluorescent lighting, concrete floor",
    cosmos_edge_weight: float = 1.0,
    cosmos_depth_weight: float = 0.25,
    cosmos_seg_weight: float = 0.25,
):
    # -- Step 1: Clone SDG repo --
    clone_task = clone_sdg_repo()
    _configure_pvc(clone_task, workspace=True)

    # -- Step 2: Isaac Sim datagen (GPU) --
    datagen_task = generate_synthetic_data(
        num_frames=num_frames,
        height=height,
        width=width,
        distractors=distractors,
    ).after(clone_task)
    datagen_task.set_env_variable("ACCEPT_EULA", "Y")
    datagen_task.set_env_variable("PRIVACY_CONSENT", "Y")
    _configure_pvc(datagen_task, workspace=True, output=True)
    _configure_gpu(datagen_task)
    kubernetes.set_image_pull_secrets(datagen_task, ["ngc-secret"])
    for name, path in [
        ("cache", "/isaac-sim/kit/cache"),
        ("glcache", "/root/.cache/nvidia/GLCache"),
        ("computecache", "/root/.nv/ComputeCache"),
        ("omniverse", "/.nvidia-omniverse"),
    ]:
        kubernetes.empty_dir_mount(datagen_task, volume_name=name, mount_path=path)

    # -- Step 3: Prepare Cosmos control maps (no GPU) --
    prep_task = prepare_control_maps(
        clip_length=cosmos_clip_length,
        height=height,
        width=width,
    ).after(datagen_task)
    _configure_pvc(prep_task, output=True)

    # -- Step 4: Deploy Cosmos Transfer NIM (no GPU for launcher) --
    deploy_nim_task = deploy_cosmos_nim(
        namespace="isaac-mlops-poc",
        gpu_product="NVIDIA-H100-80GB-HBM3",
    ).after(prep_task)

    # -- Step 5: Run Cosmos augmentation (no GPU — calls NIM API) --
    augment_task = run_cosmos_augmentation(
        cosmos_endpoint=deploy_nim_task.output,
        cosmos_prompt=cosmos_prompt,
        edge_weight=cosmos_edge_weight,
        depth_weight=cosmos_depth_weight,
        seg_weight=cosmos_seg_weight,
    ).after(deploy_nim_task)
    _configure_pvc(augment_task, output=True)

    # -- Step 6: Teardown Cosmos NIM (free GPU for training) --
    teardown_task = teardown_cosmos_nim(
        namespace="isaac-mlops-poc",
    ).after(augment_task)

    # -- Step 7: Merge original + augmented data (no GPU) --
    merge_task = merge_datasets().after(teardown_task)
    _configure_pvc(merge_task, output=True)

    # -- Step 8: Convert KITTI → TFRecords (reads merged data) --
    convert_task = convert_to_tfrecords().after(merge_task)
    _configure_pvc(convert_task, synthetic_data_merged=True, specs=True, tfrecords=True)
    _configure_gpu(convert_task)
    kubernetes.set_image_pull_secrets(convert_task, ["ngc-secret"])

    # -- Step 9: Train DetectNet_v2 via TrainJob --
    train_task = train_detectnet(
        training_runtime=training_runtime,
    ).after(convert_task)

    # -- Step 10a: Export to ONNX (GPU) --
    export_task = export_to_onnx(
        encryption_key=encryption_key,
    ).after(train_task)
    _configure_pvc(export_task, model_artifacts=True)
    _configure_gpu(export_task)
    kubernetes.set_image_pull_secrets(export_task, ["ngc-secret"])

    # -- Step 10b: Evaluate + register (no GPU) --
    eval_task = evaluate_and_register(
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_s3_endpoint=mlflow_s3_endpoint,
        experiment_name=experiment_name,
        model_registry_url=model_registry_url,
        s3_model_bucket=s3_model_bucket,
        num_frames=num_frames,
        height=height,
        width=width,
        distractors=distractors,
        epochs=epochs,
        batch_size=batch_size,
        map_threshold=map_threshold,
        cosmos_augmented=True,
        cosmos_prompt=cosmos_prompt,
    ).after(export_task)
    _configure_pvc(eval_task, model_artifacts=True, specs=True)
    kubernetes.use_secret_as_env(
        eval_task, secret_name="minio-credentials",
        secret_key_to_env={
            "accesskey": "MINIO_ACCESS_KEY",
            "secretkey": "MINIO_SECRET_KEY",
        },
    )

    # -- Step 10c: Deploy as KServe InferenceService (no GPU) --
    deploy_task = deploy_inference_service(
        model_name="palletjack-detectnet-v2",
        serving_runtime=serving_runtime,
        storage_uri=f"s3://{s3_model_bucket}/palletjack-detectnet-v2/",
        namespace="isaac-mlops-poc",
        gpu_product="NVIDIA-L40S",
    ).after(eval_task)


if __name__ == "__main__":
    compiler.Compiler().compile(
        isaac_cosmos_pipeline, "pipelines/isaac_cosmos_pipeline.yaml",
    )
    print("Compiled to pipelines/isaac_cosmos_pipeline.yaml")
