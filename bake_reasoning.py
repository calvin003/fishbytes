#!/usr/bin/env python3
"""
FishBytes — bake Claude reasoning + next-move per ROV keyframe.

Reads keyframes.json (in this same folder), calls the Anthropic API per
keyframe with an inspection-mission system prompt, and writes baked.json
alongside it. The Cognition demo on index.html fetches baked.json at load
and uses that data if reachable; otherwise it falls back to the static
inline data baked into the page.

USAGE
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 bake_reasoning.py

After it runs, redeploy your site (or refresh locally if you're serving it).
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib import request as urlreq
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).parent
KEYFRAMES = ROOT / "keyframes.json"
OUT = ROOT / "baked.json"

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    sys.exit("ANTHROPIC_API_KEY env var is required. Export it and re-run.")

MODEL = os.environ.get("FISHBYTES_MODEL", "claude-sonnet-4-5")
URL = "https://api.anthropic.com/v1/messages"

SYSTEM = """You are the on-board reasoning module of an underwater inspection ROV.

You receive structured scene state at each decision tick: telemetry, detected
objects with positions, a short context summary, and the mission objective.
You output two things in JSON:

1. `reasoning`: 1-2 short sentences (max ~35 words) explaining your assessment
   of the scene and what the priority is *right now*. Be specific, terse, and
   inspection-focused. Reference what you actually see. No fluff.

2. `command`: a single discrete motor command in the form:
   `thrust X.X m/s · yaw ±Y° · pitch ±Z° · standoff S.S m`
   Omit fields that don't change. Add a leading verb-phrase like
   "hold and document", "advance", "yaw to clear", "egress" etc.

Respond with ONLY a JSON object, no preamble. Schema:
{"reasoning": "...", "command": "..."}"""


def call_claude(user_payload: dict) -> dict:
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 400,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": json.dumps(user_payload, indent=2)}],
    }).encode("utf-8")
    req = urlreq.Request(URL, data=body, method="POST", headers={
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    with urlreq.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read())
    text = out["content"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    return json.loads(text)


def main():
    data = json.loads(KEYFRAMES.read_text())
    out_frames = []
    for i, kf in enumerate(data["keyframes"]):
        payload = {
            "mission":   data["mission"],
            "platform":  data["platform_telemetry"],
            "tick":      kf["t"],
            "label":     kf["label"],
            "telemetry": kf["telemetry"],
            "detections": kf["boxes"],
            "context":   kf["context_summary"],
        }
        for attempt in range(3):
            try:
                result = call_claude(payload)
                break
            except HTTPError as e:
                print(f"[{i+1}/{len(data['keyframes'])}] HTTP {e.code}: {e.read()[:200]}", file=sys.stderr)
                if attempt == 2: raise
                time.sleep(2 ** attempt)
            except (URLError, json.JSONDecodeError, KeyError) as e:
                print(f"[{i+1}/{len(data['keyframes'])}] {type(e).__name__}: {e}", file=sys.stderr)
                if attempt == 2: raise
                time.sleep(2 ** attempt)
        out_frames.append({**kf, "reasoning": result["reasoning"], "command": result["command"]})
        print(f"[{i+1}/{len(data['keyframes'])}] t={kf['t']}s {kf['label']}")
        print(f"    reasoning: {result['reasoning']}")
        print(f"    command:   {result['command']}")

    OUT.write_text(json.dumps({**data, "keyframes": out_frames, "baked_with": MODEL}, indent=2))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
