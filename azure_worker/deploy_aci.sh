#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# VigyanLLM Azure ACI Deploy Script
# ===================================
# Builds Docker image, pushes to ACR, deletes old ACI, creates new ACI.
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed
#   - Access to vigyanregistry01.azurecr.io
#
# Usage:
#   # CPU worker (24GB RAM, 4 vCPU) — default
#   bash azure_worker/deploy_aci.sh cpu
#
#   # GPU worker (V100, 24GB RAM, 4 vCPU)
#   bash azure_worker/deploy_aci.sh gpu
# ────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REGISTRY="vigyanregistry01.azurecr.io"
RG="VigyanComputeGroup"
API_BASE="${API_BASE_URL:-https://www.vigyanllm.in}"
DOCKING_DB="${DOCKING_DATABASE_URL:-}"

MODE="${1:-cpu}"

if [ "$MODE" = "gpu" ]; then
    IMAGE="$REGISTRY/vigyan-worker:gpu"
    DOCKERFILE="azure_worker/Dockerfile.gpu"
    CONTAINER_NAME="vigyan-worker-gpu"
    GPU_ARGS="--gpu count=1 sku=V100"
    echo "=== Deploying GPU worker ==="
else
    IMAGE="$REGISTRY/vigyan-worker:v6"
    DOCKERFILE="azure_worker/Dockerfile.azure"
    CONTAINER_NAME="vigyan-worker-cpu"
    GPU_ARGS=""
    echo "=== Deploying CPU worker (24GB, 4 vCPU) ==="
fi

# Step 1: Build
echo
echo "--- Step 1: Build ---"
docker build -t "$IMAGE" -f "$DOCKERFILE" .

# Step 2: Push to ACR
echo
echo "--- Step 2: Push to ACR ---"
az acr login --name vigyanregistry01 --expose-token 2>/dev/null || az acr login --name vigyanregistry01
docker push "$IMAGE"

# Get ACR credentials for ACI deployment (capture before stdin is used)
ACR_USERNAME="vigyanregistry01"
ACR_PASSWORD=$(az acr credential show -n vigyanregistry01 --query passwords[0].value -o tsv 2>/dev/null || echo "")

# Step 3: Delete old container
echo
echo "--- Step 3: Delete old container (if exists) ---"
az container delete --resource-group "$RG" --name "$CONTAINER_NAME" --yes 2>/dev/null || true

# Step 4: Create new ACI
echo
echo "--- Step 4: Create ACI (24GB RAM, 4 vCPU) ---"
az container create \
    --resource-group "$RG" \
    --name "$CONTAINER_NAME" \
    --image "$IMAGE" \
    --os-type Linux \
    --cpu 4 --memory 24 \
    $GPU_ARGS \
    --registry-login-server "$REGISTRY" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --environment-variables \
        API_BASE_URL="$API_BASE" \
        POLL_INTERVAL=10 \
        WORKER_MODE=daemon \
        DOCKING_DATABASE_URL="$DOCKING_DB" \
    --command-line "python /app/azure_worker/worker.py"

# Step 5: Verify
echo
echo "--- Step 5: Verify ---"
az container show --resource-group "$RG" --name "$CONTAINER_NAME" --query "{state:instanceView.currentState.state,fqdn:ipAddress.fqdn}" -o table

echo
echo "=== Deploy complete ==="
echo "Container: $CONTAINER_NAME"
echo "Image: $IMAGE"
echo "API: $API_BASE"
echo "Logs: az container logs --resource-group $RG --name $CONTAINER_NAME --follow"
