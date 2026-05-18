#!/bin/bash
# OceanSim / Isaac Sim Launcher for RunPod
# Double-click this file (or run in Terminal) to set up and launch Isaac Sim.

SSH_OPTS="-i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=15 -t"
SSH_HOST="4gap2boopb73wx-64411108@ssh.runpod.io"
POD_ID="4gap2boopb73wx"

echo "==========================================="
echo " OceanSim Isaac Sim Launcher"
echo " Pod: $POD_ID (added_harlequin_macaw)"
echo " Image: nvcr.io/nvidia/isaac-sim:4.5.0"
echo "==========================================="
echo ""
echo "Connecting via SSH..."

# Capture setup script (single-quoted heredoc = no local expansion)
SETUP_SCRIPT=$(cat << 'INNER_EOF'

echo ""
echo "--- Step 1: Verify GPU environment ---"
echo "NVIDIA_DRIVER_CAPABILITIES: ${NVIDIA_DRIVER_CAPABILITIES:-not set}"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi not available"
ls /isaac-sim 2>/dev/null && echo "Isaac Sim found at /isaac-sim/" || echo "WARNING: /isaac-sim not found"

echo ""
echo "--- Step 2: Clone OceanSim to /workspace (if needed) ---"
if [ ! -d "/workspace/OceanSim" ]; then
    echo "Cloning OceanSim from GitHub..."
    cd /workspace
    git clone https://github.com/umfieldrobotics/OceanSim.git
    echo "OceanSim cloned successfully."
else
    echo "OceanSim already present at /workspace/OceanSim"
    cd /workspace/OceanSim && git pull --rebase 2>/dev/null || true
fi

echo ""
echo "--- Step 3: Find Isaac Sim extsUser directory ---"
if [ -d "/isaac-sim" ]; then
    EXTS_DIR="/isaac-sim/extsUser"
    LAUNCH_CMD="OMNI_KIT_ALLOW_ROOT=1 /isaac-sim/runheadless.webrtc.sh"
    echo "Using NGC container paths."
else
    EXTS_DIR="/usr/local/lib/python3.11/dist-packages/isaacsim/extsUser"
    LAUNCH_CMD="OMNI_KIT_ALLOW_ROOT=1 isaacsim --livestream webrtc"
    echo "Using pip-installed isaacsim paths."
fi

mkdir -p "$EXTS_DIR"
ln -sfn /workspace/OceanSim "$EXTS_DIR/OceanSim"
echo "Symlink OK: $EXTS_DIR/OceanSim -> /workspace/OceanSim"

echo ""
echo "--- Step 4: Create Vulkan ICD file (safety measure) ---"
mkdir -p /usr/share/vulkan/icd.d
if [ ! -f /usr/share/vulkan/icd.d/nvidia_icd.json ]; then
    python3 -c "
import json
data = {
    'file_format_version': '1.0.0',
    'ICD': {
        'library_path': 'libGLX_nvidia.so.0',
        'api_version': '1.3.260'
    }
}
with open('/usr/share/vulkan/icd.d/nvidia_icd.json', 'w') as f:
    json.dump(data, f, indent=4)
print('Vulkan ICD written.')
"
else
    echo "Vulkan ICD already exists."
fi

echo ""
echo "--- Step 5: Install tmux if needed ---"
which tmux >/dev/null 2>&1 && echo "tmux OK" || apt-get install -y tmux -q

echo ""
echo "--- Step 6: Launch Isaac Sim with WebRTC (port 8211) ---"
tmux kill-session -t isaacsim 2>/dev/null && echo "Killed previous isaacsim session" || true
tmux new-session -d -s isaacsim \
    "export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json; $LAUNCH_CMD 2>&1 | tee /tmp/isaacsim.log"
sleep 3
if tmux has-session -t isaacsim 2>/dev/null; then
    echo "Isaac Sim tmux session 'isaacsim' is running."
    echo ""
    echo "Early log output:"
    sleep 5
    tail -30 /tmp/isaacsim.log 2>/dev/null || echo "(log not yet available)"
else
    echo "ERROR: tmux session failed to start."
    exit 1
fi

echo ""
echo "==========================================="
echo " Isaac Sim is initializing! (~2-3 min)"
echo " WebRTC stream: https://4gap2boopb73wx-8211.proxy.runpod.net/"
echo " Monitor logs:  tail -f /tmp/isaacsim.log"
echo " Attach tmux:   tmux attach-session -t isaacsim"
echo "==========================================="

INNER_EOF
)

# Base64-encode the script and send it as a command argument
# This sidesteps stdin/heredoc issues with the RunPod SSH proxy
ENCODED=$(echo "$SETUP_SCRIPT" | base64 | tr -d '\n')
ssh $SSH_OPTS $SSH_HOST "echo '$ENCODED' | base64 -d | bash"

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "All steps completed."
    echo ""
    echo "Open Isaac Sim WebRTC stream in your browser:"
    echo "  https://4gap2boopb73wx-8211.proxy.runpod.net/"
    echo ""
    echo "Isaac Sim takes ~2-3 minutes to fully load after launching."
else
    echo "Setup encountered an error (exit code $EXIT_CODE). Check the output above."
fi

echo ""
echo "Press any key to close."
read -n 1
