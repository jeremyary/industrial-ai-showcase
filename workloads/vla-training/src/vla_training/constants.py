# This project was developed with assistance from AI tools.
"""Cluster-internal service URLs and pipeline defaults."""

S3_ENDPOINT = "http://minio.mlflow.svc:9000"
MLFLOW_TRACKING_URI = "https://mlflow.redhat-ods-applications.svc:8443"
MODEL_REGISTRY_ADDRESS = "http://model-registry.redhat-ods-applications.svc:8080"

PIPELINE_IMAGE = "image-registry.openshift-image-registry.svc:5000/vla-training/vla-training:latest"
GPU_LIMIT = 1
