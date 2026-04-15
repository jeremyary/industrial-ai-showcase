-include .env
export

CENTRAL_NS    ?= ai-showcase-central
MLOPS_NS      ?= ai-showcase-mlops
FACTORY_SITES ?= ai-showcase-factory-a
REGISTRY      ?= quay.io/jary
IMAGE_TAG     ?= latest

HELM := helm
SITES := $(FACTORY_SITES)

.PHONY: deploy deploy-platform deploy-factory deploy-mlops undeploy undeploy-platform undeploy-factory undeploy-mlops status build push lint template

## deploy: Deploy platform + all factory sites + mlops
deploy:
	@$(MAKE) deploy-platform
	@for site in $(SITES); do \
		$(MAKE) deploy-factory SITE=$$site; \
	done
	@$(MAKE) deploy-mlops

## deploy-platform: Deploy central platform chart (creates namespace + NGC secret)
deploy-platform:
	@test -n "$(NGC_API_KEY)" || (echo "ERROR: NGC_API_KEY not set in .env"; exit 1)
	@oc new-project $(CENTRAL_NS) --skip-config-write 2>/dev/null || true
	@oc create secret docker-registry ngc-pull-secret \
		--docker-server=nvcr.io \
		--docker-username='$$oauthtoken' \
		--docker-password=$(NGC_API_KEY) \
		-n $(CENTRAL_NS) --dry-run=client -o yaml | oc apply -f -
	$(HELM) upgrade --install platform charts/platform \
		-n $(CENTRAL_NS) \
		-f values/central.yaml \
		--create-namespace

## deploy-factory: Deploy a single factory site (SITE=ai-showcase-factory-a)
deploy-factory:
	@test -n "$(SITE)" || (echo "ERROR: set SITE=ai-showcase-factory-a|ai-showcase-factory-b"; exit 1)
	@test -n "$(NGC_API_KEY)" || (echo "ERROR: NGC_API_KEY not set in .env"; exit 1)
	@test -n "$(HF_TOKEN)" || (echo "ERROR: HF_TOKEN not set in .env — see .env.example for instructions"; exit 1)
	@oc new-project $(SITE) --skip-config-write 2>/dev/null || true
	@oc create secret docker-registry ngc-pull-secret \
		--docker-server=nvcr.io \
		--docker-username='$$oauthtoken' \
		--docker-password=$(NGC_API_KEY) \
		-n $(SITE) --dry-run=client -o yaml | oc apply -f -
	@oc create secret generic hf-token \
		--from-literal=token=$(HF_TOKEN) \
		-n $(SITE) --dry-run=client -o yaml | oc apply -f -
	@oc create secret generic ngc-api-key \
		--from-literal=NGC_API_KEY=$(NGC_API_KEY) \
		-n $(SITE) --dry-run=client -o yaml | oc apply -f -
	$(HELM) upgrade --install $(SITE) charts/factory \
		-n $(SITE) \
		-f values/$(SITE).yaml \
		--create-namespace

## deploy-mlops: Deploy MLOps chart (pipelines, training, serving)
deploy-mlops:
	@test -n "$(NGC_API_KEY)" || (echo "ERROR: NGC_API_KEY not set in .env"; exit 1)
	@test -n "$(MINIO_PASSWORD)" || (echo "ERROR: MINIO_PASSWORD not set in .env"; exit 1)
	@test -n "$(REGISTRY_DB_PASSWORD)" || (echo "ERROR: REGISTRY_DB_PASSWORD not set in .env"; exit 1)
	@oc new-project $(MLOPS_NS) --skip-config-write 2>/dev/null || true
	@oc create secret docker-registry ngc-pull-secret \
		--docker-server=nvcr.io \
		--docker-username='$$oauthtoken' \
		--docker-password=$(NGC_API_KEY) \
		-n $(MLOPS_NS) --dry-run=client -o yaml | oc apply -f -
	@oc create secret generic ngc-api-key \
		--from-literal=NGC_API_KEY=$(NGC_API_KEY) \
		-n $(MLOPS_NS) --dry-run=client -o yaml | oc apply -f -
	$(HELM) upgrade --install mlops charts/mlops \
		-n $(MLOPS_NS) \
		--set minio.credentials.password=$(MINIO_PASSWORD) \
		--set modelRegistry.database.password=$(REGISTRY_DB_PASSWORD) \
		--create-namespace
	@echo "Linking NGC pull secret to pipeline ServiceAccount..."
	@for i in $$(seq 1 24); do \
		if oc secrets link pipeline-runner-isaac-pipelines ngc-pull-secret \
			--for=pull -n $(MLOPS_NS) 2>/dev/null; then \
			echo "  Pull secret linked to pipeline SA"; \
			break; \
		fi; \
		if [ $$i -eq 24 ]; then \
			echo "  WARN: Could not link pull secret — run 'make deploy-mlops' again after DSPA creates the SA"; \
			break; \
		fi; \
		echo "  Waiting for DSPA to create pipeline SA ($$i/24)..."; \
		sleep 5; \
	done

## undeploy: Tear down everything
undeploy:
	@$(MAKE) undeploy-mlops
	@for site in $(SITES); do \
		$(HELM) uninstall $$site -n $$site --ignore-not-found || true; \
		oc delete project $$site --ignore-not-found || true; \
	done
	@$(MAKE) undeploy-platform

## undeploy-platform: Remove platform chart
undeploy-platform:
	$(HELM) uninstall platform -n $(CENTRAL_NS) --ignore-not-found || true
	oc delete project $(CENTRAL_NS) --ignore-not-found || true

## undeploy-factory: Remove a single factory site (SITE=ai-showcase-factory-a)
undeploy-factory:
	@test -n "$(SITE)" || (echo "ERROR: set SITE=ai-showcase-factory-a|ai-showcase-factory-b"; exit 1)
	$(HELM) uninstall $(SITE) -n $(SITE) --ignore-not-found || true
	oc delete project $(SITE) --ignore-not-found || true

## undeploy-mlops: Remove MLOps chart
undeploy-mlops:
	$(HELM) uninstall mlops -n $(MLOPS_NS) --ignore-not-found || true
	oc delete project $(MLOPS_NS) --ignore-not-found || true

## status: Show pod/service status across all namespaces
status:
	@echo "=== $(CENTRAL_NS) ==="
	@oc get pods,svc,routes -n $(CENTRAL_NS) 2>/dev/null || true
	@for site in $(SITES); do \
		echo ""; \
		echo "=== $$site ==="; \
		oc get pods,svc,routes -n $$site 2>/dev/null || true; \
	done
	@echo ""
	@echo "=== $(MLOPS_NS) ==="
	@oc get pods,svc -n $(MLOPS_NS) 2>/dev/null || true

## build: Build custom container images (camera-feed, dashboard)
build:
	podman build -t $(REGISTRY)/camera-feed:$(IMAGE_TAG) images/camera-feed/
	podman build -t $(REGISTRY)/dashboard:$(IMAGE_TAG) images/dashboard/
	podman build -t $(REGISTRY)/inference-sidecar:$(IMAGE_TAG) images/inference-sidecar/

## push: Push custom images to registry
push:
	podman push $(REGISTRY)/camera-feed:$(IMAGE_TAG)
	podman push $(REGISTRY)/dashboard:$(IMAGE_TAG)
	podman push $(REGISTRY)/inference-sidecar:$(IMAGE_TAG)

## lint: Helm lint all charts
lint:
	$(HELM) lint charts/platform -f values/central.yaml
	@for site in $(SITES); do \
		$(HELM) lint charts/factory -f values/$$site.yaml; \
	done
	$(HELM) lint charts/mlops

## template: Dry-run render all charts
template:
	$(HELM) template platform charts/platform -f values/central.yaml
	@for site in $(SITES); do \
		$(HELM) template $$site charts/factory -f values/$$site.yaml; \
	done
	$(HELM) template mlops charts/mlops
