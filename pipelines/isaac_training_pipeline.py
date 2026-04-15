# This project was developed with assistance from AI tools.
"""
End-to-end pipeline: Isaac Sim synthetic data generation → TAO training →
ONNX export → MLflow registration → KServe model serving.

Compile:  python pipelines/isaac_training_pipeline.py
Submit:   upload pipelines/isaac_training_pipeline.yaml via RHOAI dashboard or API
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
#
# Parameters are passed as positional args and referenced via $1..$4
# in the shell script. This is the standard KFP v2 pattern for
# container_component parameter passing on DSPA — set_env_variable
# does not resolve pipeline parameter channels (KFP issue #10111).
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
# Step 3: Convert KITTI annotations to TFRecords
# ---------------------------------------------------------------------------
@dsl.container_component
def convert_to_tfrecords():
    return dsl.ContainerSpec(
        image="nvcr.io/nvidia/tao/tao-toolkit:5.0.0-tf1.15.5",
        command=["/bin/bash", "-c"],
        args=[
            "echo '=== Converting KITTI to TFRecords ===' && "
            "mkdir -p /workspace/tfrecords/warehouse && "
            "detectnet_v2 dataset_convert "
            "-d /workspace/specs/tfrecords_warehouse.txt "
            "-o /workspace/tfrecords/warehouse/tfrecord && "
            "echo '=== Conversion complete ===' && "
            "ls -la /workspace/tfrecords/warehouse/"
        ],
    )


# ---------------------------------------------------------------------------
# Step 4: Train DetectNet_v2 via Kubeflow Trainer (TrainJob)
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
# Step 5: Export trained model to ONNX for serving
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
# Step 6: Evaluate results and register model in MLflow
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
    kfp_metrics: dsl.Output[dsl.Metrics],
) -> str:
    """Parse training status.json, log metrics/artifacts to MLflow, upload ONNX to S3, register model."""
    import json
    import os

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = mlflow_s3_endpoint
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ.get("MINIO_ACCESS_KEY", "minio")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ.get("MINIO_SECRET_KEY", "minio123")
    os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
    # RHOAI MLflow uses TLS + K8s workspace auth:
    # - Bearer token from ServiceAccount for authentication
    # - X-MLFLOW-WORKSPACE header (= pod namespace) for workspace context
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
    print(f"Epochs with metrics: {len(per_epoch_metrics)}")

    with mlflow.start_run() as run:
        mlflow.log_params({
            "num_frames": num_frames,
            "image_height": height,
            "image_width": width,
            "distractors": distractors,
            "epochs": epochs,
            "batch_size": batch_size,
            "architecture": "resnet18",
            "detector": "detectnet_v2",
        })

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
                pass  # already exists
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
        print(f"Result: {result}")
        print(f"MLflow run ID: {run.info.run_id}")

    # Upload ONNX to MinIO (KServe expects s3://<bucket>/<model-name>/<version>/model.onnx)
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
            },
        )
        print(f"RHOAI Model Registry: registered {rm.name} (format={model_fmt})")

    return result


# ---------------------------------------------------------------------------
# Step 7: Deploy model as a KServe InferenceService
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
    name="isaac-synth-train-serve",
    description=(
        "Synthetic data generation with Isaac Sim Replicator, "
        "model training with TAO DetectNet_v2, ONNX export, "
        "experiment tracking + model registration with MLflow, "
        "and deployment as a KServe InferenceService."
    ),
)
def isaac_training_pipeline(
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
    experiment_name: str = "palletjack-detectnet-v2",
    model_registry_url: str = "http://isaac-registry.rhoai-model-registries.svc.cluster.local",
    map_threshold: float = 0.0,
    serving_runtime: str = "ovms",
    s3_model_bucket: str = "models",
):
    # -- Step 1: Clone SDG repo to workspace PVC --
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

    # -- Step 3: Convert KITTI → TFRecords --
    convert_task = convert_to_tfrecords().after(datagen_task)
    _configure_pvc(convert_task, synthetic_data=True, specs=True, tfrecords=True)
    _configure_gpu(convert_task)
    kubernetes.set_image_pull_secrets(convert_task, ["ngc-secret"])

    # -- Step 4: Train DetectNet_v2 via TrainJob --
    train_task = train_detectnet(
        training_runtime=training_runtime,
    ).after(convert_task)

    # -- Step 5: Export trained model to ONNX (GPU) --
    export_task = export_to_onnx(
        encryption_key=encryption_key,
    ).after(train_task)
    _configure_pvc(export_task, model_artifacts=True)
    _configure_gpu(export_task)
    kubernetes.set_image_pull_secrets(export_task, ["ngc-secret"])

    # -- Step 6: Evaluate + register in MLflow + RHOAI Model Registry (no GPU) --
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
    ).after(export_task)
    _configure_pvc(eval_task, model_artifacts=True, specs=True)
    kubernetes.use_secret_as_env(
        eval_task, secret_name="minio-credentials",
        secret_key_to_env={
            "accesskey": "MINIO_ACCESS_KEY",
            "secretkey": "MINIO_SECRET_KEY",
        },
    )

    # -- Step 7: Deploy as KServe InferenceService (no GPU) --
    deploy_task = deploy_inference_service(
        model_name="palletjack-detectnet-v2",
        serving_runtime=serving_runtime,
        storage_uri=f"s3://{s3_model_bucket}/palletjack-detectnet-v2/",
        namespace="isaac-mlops-poc",
        gpu_product="NVIDIA-L40S",
    ).after(eval_task)


if __name__ == "__main__":
    compiler.Compiler().compile(
        isaac_training_pipeline, "pipelines/isaac_training_pipeline.yaml",
    )
    print("Compiled to pipelines/isaac_training_pipeline.yaml")
