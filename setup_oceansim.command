#!/bin/bash
# OceanSim Setup Script - clean non-interactive version
# Double-click to run setup and launch Isaac Sim with WebRTC

SSH_OPTS="-i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=30 -T"
SSH_HOST="4gap2boopb73wx-64411108@ssh.runpod.io"

echo "==========================================="
echo " OceanSim Setup"
echo "==========================================="
echo ""
echo "Connecting to pod (non-interactive)..."

SETUP=$(cat << 'INNER_EOF'
set -x

echo "=== Checking environment ==="
nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "nvidia-smi not found"
ls /isaac-sim 2>/dev/null && echo "Isaac Sim found" || echo "WARNING: /isaac-sim missing"

echo "=== Cloning OceanSim ==="
if [ ! -d "/workspace/OceanSim" ]; then
    cd /workspace && git clone https://github.com/umfieldrobotics/OceanSim.git
    echo "Cloned OK"
else
    echo "OceanSim already present"
    cd /workspace/OceanSim && git pull --rebase 2>/dev/null || true
fi

echo "=== Creating symlink ==="
mkdir -p /isaac-sim/extsUser
ln -sfn /workspace/OceanSim /isaac-sim/extsUser/OceanSim
ls -la /isaac-sim/extsUser/OceanSim

echo "=== Vulkan ICD ==="
mkdir -p /usr/share/vulkan/icd.d
python3 -c "
import json, sys
d={'file_format_version':'1.0.0','ICD':{'library_path':'libGLX_nvidia.so.0','api_version':'1.3.260'}}
json.dump(d, open('/usr/share/vulkan/icd.d/nvidia_icd.json','w'), indent=2)
print('Vulkan ICD written')
"

echo "=== Installing tmux ==="
which tmux >/dev/null 2>&1 && echo "tmux OK" || apt-get install -y tmux -q

echo "=== Launching Isaac Sim WebRTC ==="
tmux kill-session -t isaacsim 2>/dev/null && echo "Killed old session" || true
tmux new-session -d -s isaacsim \
    "export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json; OMNI_KIT_ALLOW_ROOT=1 /isaac-sim/runheadless.webrtc.sh 2>&1 | tee /tmp/isaacsim.log"
sleep 2
tmux has-session -t isaacsim 2>/dev/null && echo "tmux session RUNNING" || echo "ERROR: tmux session failed"
echo "=== DONE ==="
echo "WebRTC URL: https://4gap2boopb73wx-8211.proxy.runpod.net/"
INNER_EOF
)

ENCODED=$(printf '%s' "$SETUP" | base64 | tr -d '\n')
echo "Sending setup script..."
ssh $SSH_OPTS $SSH_HOST "echo '$ENCODED' | base64 -d | bash -s" 2>&1

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "==========================================="
    echo " Setup complete!"
    echo " Isaac Sim is loading (~2-3 min)"
    echo " WebRTC: https://4gap2boopb73wx-8211.proxy.runpod.net/"
    echo "==========================================="
else
    echo "Setup failed (exit $EXIT_CODE)"
fi

echo ""
echo "Press any key to close."
read -n 1
