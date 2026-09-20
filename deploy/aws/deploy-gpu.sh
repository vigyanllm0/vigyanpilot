#!/bin/bash
# ════════════════════════════════════════════════════════════════════
# VigyanLLM — GPU Instance Deployment Script
# For g4dn.xlarge (4 vCPU, 16GB RAM, 1x T4 GPU)
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

echo "═══════════════════════════════════════════════════════════════"
echo "  VigyanLLM GPU Deployment — g4dn.xlarge"
echo "═══════════════════════════════════════════════════════════════"

# ── System Setup ────────────────────────────────────────────────────────

echo ""
echo "[1/7] System updates..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3.11 python3.11-venv python3-pip git wget curl

# ── NVIDIA Drivers ──────────────────────────────────────────────────────

echo ""
echo "[2/7] Installing NVIDIA drivers..."
if ! command -v nvidia-smi &> /dev/null; then
    sudo apt-get install -y -qq nvidia-driver-535 nvidia-utils-535
    echo "⚠ Reboot required after driver install"
else
    echo "  NVIDIA drivers already installed"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

# ── CUDA Toolkit ────────────────────────────────────────────────────────

echo ""
echo "[3/7] Installing CUDA toolkit..."
if [ ! -d /usr/local/cuda ]; then
    wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    sudo dpkg -i cuda-keyring_1.1-1_all.deb
    sudo apt-get update -qq
    sudo apt-get install -y -qq cuda-toolkit-12-2
    rm cuda-keyring_1.1-1_all.deb
else
    echo "  CUDA already installed"
fi

export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

# ── Python Environment ──────────────────────────────────────────────────

echo ""
echo "[4/7] Setting up Python environment..."
cd /opt
sudo mkdir -p vigyanllm && sudo chown $USER:$USER vigyanllm
cd vigyanllm

if [ ! -d venv ]; then
    python3.11 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip -q
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 -q
pip install esm -q  # Meta's ESM-2 protein language model

# ── Application Code ────────────────────────────────────────────────────

echo ""
echo "[5/7] Deploying application..."
if [ ! -d vigyanpilot ]; then
    git clone https://github.com/vigyanllm0/vigyanpilot.git
fi
cd vigyanpilot
pip install -r requirements.txt -q
pip install gunicorn -q

# ── ESMFold Model Download ─────────────────────────────────────────────

echo ""
echo "[6/7] Pre-downloading ESMFold model..."
python3 -c "
import torch
from esm.pretrained import esmfold_v1
print('Downloading ESMFold model...')
model = esmfold_v1()
model = model.eval()
if torch.cuda.is_available():
    model = model.cuda()
print('Model ready:', next(model.parameters()).device)
torch.save(model.state_dict(), '/opt/vigyanllm/esmfold_v1.pt')
print('Model saved to /opt/vigyanllm/esmfold_v1.pt')
" 2>/dev/null || echo "  ⚠ Model download will happen on first use"

# ── Systemd Service ─────────────────────────────────────────────────────

echo ""
echo "[7/7] Creating systemd service..."

sudo tee /etc/systemd/system/vigyanllm.service > /dev/null << 'EOF'
[Unit]
Description=VigyanLLM Bioinformatics Platform
After=network.target

[Service]
Type=exec
User=ubuntu
WorkingDirectory=/opt/vigyanllm/vigyanpilot
Environment=CUDA_VISIBLE_DEVICES=0
Environment=ESM_DEVICE=cuda
Environment=DATABASE_URL=postgresql://vigyanllm:password@localhost:5432/vigyanllm
Environment=PYTHONPATH=/opt/vigyanllm/vigyanpilot
ExecStart=/opt/vigyanllm/venv/bin/gunicorn \
    --workers 2 \
    --threads 4 \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --keep-alive 5 \
    primerforge.primer_server:create_app()
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vigyanllm
sudo systemctl start vigyanllm

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Deployment complete!"
echo ""
echo "  Service: sudo systemctl status vigyanllm"
echo "  Logs:    sudo journalctl -u vigyanllm -f"
echo "  Port:    8000"
echo ""
echo "  GPU:     $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'check nvidia-smi')"
echo "  CUDA:    $(nvcc --version 2>/dev/null | grep release || echo 'check /usr/local/cuda')"
echo "═══════════════════════════════════════════════════════════════"
