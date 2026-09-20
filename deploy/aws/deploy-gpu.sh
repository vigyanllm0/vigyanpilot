#!/bin/bash
# ════════════════════════════════════════════════════════════════════
# VigyanLLM — GPU Instance Deployment Script
# For g4dn.xlarge (4 vCPU, 16GB RAM, 1x T4 GPU)
# Run this ON THE NEW GPU INSTANCE, not the t3.micro
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

echo "═══════════════════════════════════════════════════════════════"
echo "  VigyanLLM GPU Deployment — g4dn.xlarge"
echo "═══════════════════════════════════════════════════════════════"

# Detect Python
PYTHON=$(command -v python3.14 || command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3 || echo "python3")
PYVER=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
echo "Using: $PYTHON ($PYVER)"

# ── System Setup ────────────────────────────────────────────────────────

echo ""
echo "[1/7] System updates..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-dev python3-pip git wget curl build-essential

# ── NVIDIA Drivers ──────────────────────────────────────────────────────

echo ""
echo "[2/7] Installing NVIDIA drivers..."
if ! command -v nvidia-smi &> /dev/null; then
    sudo apt-get install -y -qq ubuntu-drivers-common
    sudo ubuntu-drivers autoinstall
    echo "⚠ Reboot required after driver install: sudo reboot"
    echo "  Then re-run this script."
    exit 0
else
    echo "  NVIDIA drivers installed:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

# ── CUDA Toolkit ────────────────────────────────────────────────────────

echo ""
echo "[3/7] Checking CUDA..."
if [ -d /usr/local/cuda ]; then
    echo "  CUDA already installed"
else
    echo "  Installing CUDA toolkit..."
    wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    sudo dpkg -i cuda-keyring_1.1-1_all.deb
    sudo apt-get update -qq
    sudo apt-get install -y -qq cuda-toolkit-12-2
    rm cuda-keyring_1.1-1_all.deb
fi

export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

# ── Python Environment ──────────────────────────────────────────────────

echo ""
echo "[4/7] Setting up Python environment..."
VENV_DIR="/opt/vigyanllm/venv"
sudo mkdir -p /opt/vigyanllm && sudo chown $USER:$USER /opt/vigyanllm

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q

echo "  Installing PyTorch with CUDA..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 -q 2>&1 | tail -1

echo "  Installing transformers + ESMFold..."
pip install transformers huggingface_hub -q 2>&1 | tail -1

echo "  Installing AutoDock Vina..."
pip install vina -q 2>&1 | tail -1 || echo "  ⚠ Vina install failed — will use web fallback"

# ── Application Code ────────────────────────────────────────────────────

echo ""
echo "[5/7] Deploying application..."
DEPLOY_DIR="/opt/vigyanllm/vigyanpilot"
if [ ! -d "$DEPLOY_DIR" ]; then
    git clone https://github.com/vigyanllm0/vigyanpilot.git "$DEPLOY_DIR"
fi
cd "$DEPLOY_DIR"
git pull origin main
pip install -r requirements.txt -q 2>&1 | tail -1 || true
pip install gunicorn psutil -q

# ── Pre-download ESMFold Model ──────────────────────────────────────────

echo ""
echo "[6/7] Pre-downloading ESMFold model (~8.4GB)..."
python3 -c "
import torch
from transformers import AutoTokenizer, EsmForProteinFolding
print('Downloading ESMFold model...')
tok = AutoTokenizer.from_pretrained('facebook/esmfold_v1')
model = EsmForProteinFolding.from_pretrained('facebook/esmfold_v1')
if torch.cuda.is_available():
    model = model.cuda()
    print('Model on GPU:', next(model.parameters()).device)
else:
    print('WARNING: No GPU detected!')
print('Model ready')
" 2>/dev/null || echo "  ⚠ Model download will happen on first use"

# ── Systemd Service ─────────────────────────────────────────────────────

echo ""
echo "[7/7] Creating systemd service..."

sudo tee /etc/systemd/system/vigyanllm-gpu.service > /dev/null << 'EOF'
[Unit]
Description=VigyanLLM GPU Backend (g4dn.xlarge)
After=network.target

[Service]
Type=exec
User=ubuntu
WorkingDirectory=/opt/vigyanllm/vigyanpilot
Environment=CUDA_VISIBLE_DEVICES=0
Environment=ESM_DEVICE=cuda
Environment=DOCKING_GPU=1
Environment=PYTHONPATH=/opt/vigyanllm/vigyanpilot
ExecStart=/opt/vigyanllm/venv/bin/gunicorn \
    --workers 2 \
    --threads 4 \
    --bind 127.0.0.1:11437 \
    --timeout 300 \
    --keep-alive 5 \
    primerforge.primer_server:create_app()
Restart=always
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vigyanllm-gpu
sudo systemctl start vigyanllm-gpu

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Deployment complete!"
echo ""
echo "  Service: sudo systemctl status vigyanllm-gpu"
echo "  Logs:    sudo journalctl -u vigyanllm-gpu -f"
echo "  Port:    11437 (GPU backend)"
echo ""
echo "  ⚠ NEXT STEPS:"
echo "  1. Update nginx to proxy /api/docking/* to this GPU instance"
echo "  2. Update t3.micro memory check to allow proxying"
echo "  3. Copy this instance's IP to CloudFront origin"
echo ""
echo "  GPU:     $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'check nvidia-smi')"
echo "  CUDA:    $(nvcc --version 2>/dev/null | grep release || echo 'check /usr/local/cuda')"
echo "═══════════════════════════════════════════════════════════════"
