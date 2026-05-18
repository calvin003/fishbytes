#!/bin/bash
# OceanSim Status Checker

SSH_OPTS="-i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=15"
SSH_HOST="johdubtd9bzmv3-64411548@ssh.runpod.io"

echo "==========================================="
echo " OceanSim Status Check"
echo "==========================================="
echo ""

ssh $SSH_OPTS $SSH_HOST 'bash -s' << 'ENDSCRIPT'

echo "--- tmux session ---"
tmux has-session -t isaacsim 2>/dev/null && echo "STATUS: RUNNING" || echo "STATUS: NOT RUNNING"

echo ""
echo "--- Port 8211 listener ---"
ss -tlnp 2>/dev/null | grep 8211 || netstat -tlnp 2>/dev/null | grep 8211 || echo "Nothing listening on 8211 yet"

echo ""
echo "--- Last 80 lines of Isaac Sim log ---"
tail -80 /tmp/isaacsim.log 2>/dev/null || echo "Log not found at /tmp/isaacsim.log"

echo ""
echo "--- GPU status ---"
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi not available"

ENDSCRIPT

echo ""
echo "Press any key to close."
read -n 1
