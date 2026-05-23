# OceanSim on Brev — Isaac Sim 5.0 with WebRTC streaming to macOS

A pragmatic, end-to-end setup guide. Targets:

- **Host:** NVIDIA Brev (UDP works, public IPv4, root access)
- **GPU:** RTX A6000 (confirmed in OceanSim test matrix; L40 / 4090 also fine)
- **Simulator:** Isaac Sim 5.0 built from source (required by OceanSim's docs)
- **Extension:** OceanSim (umfieldrobotics/OceanSim)
- **Client:** Isaac Sim WebRTC Streaming Client on macOS

---

## Why this stack (and why not RunPod)

OceanSim is an Isaac Sim 5.0 extension that has to be cloned into Isaac Sim's `extsUser` folder and loaded from the in-app Extensions browser. That means you need the GUI, which means WebRTC streaming, which means **UDP must be reachable** on the GPU host. RunPod blocks UDP and Isaac Sim 5.0 removed the TURN-over-TCP fallback that 4.2 had, so RunPod is a dead end for this workflow. Brev (NVIDIA's own GPU compute platform) gives you a real public IP with arbitrary UDP, which is exactly what the Omniverse streaming SDK expects.

---

## 0. Prereqs on your Mac

Install the Isaac Sim WebRTC Streaming Client for macOS now so it's ready when the pod is.

- Download from NVIDIA's Isaac Sim 5.0 Livestream Clients page:
  https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/manual_livestream_clients.html
- Drag the `.app` into `/Applications` and launch once so macOS approves it.

You'll also need an NVIDIA NGC account (free) if you want to fall back to the prebuilt container later; not strictly required for the source-build path below.

---

## 1. Launch a Brev instance

1. Sign in at https://brev.dev with your existing NVIDIA Developer / NGC account.
2. **New Instance → GPU**.
3. Configuration:
   - **GPU:** RTX A6000 (1×). L40, L40S, or 4090 also work; avoid V100/T4 — no RT cores.
   - **Image:** "Ubuntu 22.04 + CUDA 12.x" (Brev's default GPU image).
   - **Disk:** 200 GB minimum. Isaac Sim source + caches + OceanSim assets eat ~100 GB.
   - **Open Ports:** add **TCP 47995-48012, TCP 49000-49007, TCP 49100, UDP 47995-48012, UDP 49000-49007**. These are the Omniverse streaming SDK's signaling + media ranges.
4. Launch and wait ~2 min for it to come up green. Note the **public IP** — you'll need it later.
5. Click **Open in Browser → Terminal** (or SSH in with the key Brev provides).

---

## 2. Verify the GPU and base packages

```bash
nvidia-smi             # should show your A6000 and driver 535+
sudo apt-get update
sudo apt-get install -y git git-lfs build-essential cmake python3.10-venv \
                        libvulkan1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
                        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                        libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 \
                        libxkbcommon-x11-0 libegl1 libgl1 unzip
git lfs install
```

Vulkan is required — Isaac Sim's renderer won't start without `libvulkan1`.

---

## 3. Clone and build Isaac Sim 5.0 from source

OceanSim's installation docs explicitly say "For Isaac Sim 5.0, we build from their source code." Follow that exactly:

```bash
cd ~
git clone https://github.com/isaac-sim/IsaacSim.git isaacsim
cd isaacsim
git checkout v5.0.0       # pin to the release the OceanSim main branch tracks
./build.sh -r             # release build; takes 20–40 min on an A6000
```

The build produces a runtime tree under `~/isaacsim/_build/linux-x86_64/release/`. That directory is the equivalent of a workstation install — it contains `isaac-sim.sh`, `runheadless.sh`, and (critically) the `extsUser/` folder OceanSim wants.

---

## 4. Install OceanSim

```bash
cd ~/isaacsim/_build/linux-x86_64/release/extsUser
git clone https://github.com/umfieldrobotics/OceanSim.git
```

Download the OceanSim assets bundle from Google Drive:
https://drive.google.com/drive/folders/1qg4-Y_GMiybnLc1BFjx0DsWfR0AgeZzA?usp=sharing

Easiest path: install `gdown` and pull it directly into the pod (no need to bounce through your Mac).

```bash
pip install --user gdown
mkdir -p ~/OceanSim_assets
cd ~/OceanSim_assets
gdown --folder "https://drive.google.com/drive/folders/1qg4-Y_GMiybnLc1BFjx0DsWfR0AgeZzA"
```

Register the asset path so OceanSim knows where its USD files live:

```bash
cd ~/isaacsim/_build/linux-x86_64/release/extsUser/OceanSim
python3 config/register_asset_path.py ~/OceanSim_assets
```

---

## 5. Start Isaac Sim with WebRTC streaming

From the build directory:

```bash
cd ~/isaacsim/_build/linux-x86_64/release
./runheadless.sh
```

`runheadless.sh` boots Isaac Sim with rendering enabled but no local X display, and starts the WebRTC streaming server bound to all interfaces. Watch the log for two things:

- `WebRTC streaming server started on port 49100` (signaling)
- `Listening on UDP 47998` (media) — if this line never appears, your firewall is still blocking UDP; go back to step 1.4.

Leave this terminal running. Open a second SSH session for anything else.

---

## 6. Connect from macOS

1. Open **Isaac Sim WebRTC Streaming Client** on your Mac.
2. In the **Server** field, enter the Brev instance's **public IP** (no scheme, no port — e.g. `203.0.113.42`).
3. Click **Connect**. First connection takes ~10 seconds for ICE negotiation.
4. You should land in the empty Isaac Sim stage.

If you get a black screen with audio-only or it hangs at "connecting": almost always a UDP port issue on the Brev side. Double-check the open-ports list from step 1.4.

---

## 7. Activate OceanSim in the GUI

Inside the streamed Isaac Sim window:

1. **Window → Extensions**.
2. Top of the Extensions panel, **remove the `@feature` filter** that's there by default — OceanSim isn't tagged as a feature extension and won't show otherwise.
3. Search `OCEANSIM`, toggle it **On**, and check **Autoload** so you don't have to do this every session.
4. Close the Extensions window. OceanSim now appears as a top-level menu item — its sensors (camera, sonar, etc.) and environment modules are available from Python or via drag-into-stage.

---

## 8. Quick smoke test

In the Isaac Sim **Script Editor** (Window → Script Editor), run:

```python
import oceansim
print(oceansim.__version__)
# Spawn a default underwater scene
from oceansim.examples import load_default_scene
load_default_scene()
```

You should see the asset registry resolve, the underwater scene load, and ray-traced rendering kick in. If the assets fail to resolve, re-run `register_asset_path.py` — it writes a config file that 5.0 occasionally misses on first launch.

---

## Cost & shutdown reminders

- A6000 on Brev is roughly **$0.80–$1.20/hr**; an L40S is ~$1.50/hr.
- The source build is the slow part — **don't terminate the instance** when you're done, **stop** it. Stopped instances keep the disk (you pay storage only, ~$0.10/hr for 200 GB) and skip a 30-min rebuild next time.
- If you only need OceanSim occasionally, snapshot the disk and recreate from snapshot when needed.

---

## Troubleshooting cheatsheet

| Symptom | Likely cause | Fix |
|---|---|---|
| `runheadless.sh` exits with "Vulkan not found" | Missing system Vulkan loader | `sudo apt-get install -y libvulkan1` |
| WebRTC client connects but black screen | UDP port range not open | Reopen 47995-48012 UDP on Brev's firewall |
| OceanSim not visible in Extensions panel | `@feature` filter still applied | Clear the filter; re-search `OCEANSIM` |
| `gdown` fails with "Permission denied" | Google Drive rate limiting | Use a personal OAuth: `gdown --fuzzy --use-cookies <url>` |
| Renderer crashes on 4090 with `OptiX` errors | Driver too old | Brev image with driver ≥ 550 |
| Build fails mid-way with OOM | Default `make -j` too aggressive | `./build.sh -r -j 4` |

---

## Sources

- [Isaac Sim 5.0 — Container Installation](https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/install_container.html)
- [Isaac Sim 5.0 — Livestream Clients](https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/manual_livestream_clients.html)
- [Isaac Sim 5.0 + TCP-only TURN — NVIDIA dev forum (Oct 2025, confirms no TCP fallback in 5.0)](https://forums.developer.nvidia.com/t/isaac-sim-5-0-0-unable-to-configure-turn-server-for-webrtc-tcp-only-setup-no-udp-allowed/347641)
- [IsaacAutomator issue #37 — RunPod support / UDP blockers](https://github.com/isaac-sim/IsaacAutomator/issues/37)
- [OceanSim — installation docs](https://github.com/umfieldrobotics/OceanSim/blob/main/docs/subsections/installation.md)
- [OceanSim — GitHub repo](https://github.com/umfieldrobotics/OceanSim)
- [Brev — Isaac Launchable repo](https://github.com/isaac-sim/isaac-launchable)
- [RunPod — Expose ports docs (UDP not supported)](https://docs.runpod.io/pods/configuration/expose-ports)
