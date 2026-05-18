#!/usr/bin/env python3
"""
Isaac Sim OceanSim WebSocket proxy + browser client.
Proxies between browser and Isaac Sim's native streaming WebSocket on port 48010.
The old streaming protocol sends JPEG frames as binary WebSocket messages.
"""
import asyncio
import aiohttp
from aiohttp import web
import json

ISAAC_WS_PORT = 48010

HTML = r"""<!DOCTYPE html>
<html>
<head>
  <title>Isaac Sim - OceanSim Stream</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #000; display: flex; flex-direction: column; align-items: center; height: 100vh; overflow: hidden; }
    #status { color: #0f0; font-family: monospace; font-size: 12px; padding: 4px 8px; width: 100%; background: #111; }
    #canvas { max-width: 100%; max-height: calc(100vh - 24px); cursor: crosshair; }
    #overlay { position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
                color: #fff; font-size: 24px; font-family: monospace; text-align: center;
                background: rgba(0,0,0,0.8); padding: 20px; border-radius: 8px; }
  </style>
</head>
<body>
  <div id="status">Connecting...</div>
  <canvas id="canvas" width="1920" height="1080"></canvas>
  <div id="overlay">Connecting to Isaac Sim...<br><small>OceanSim Underwater Robot Simulation</small></div>

<script>
const status = document.getElementById('status');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const overlay = document.getElementById('overlay');

let ws = null;
let frameCount = 0;
let lastFPS = 0;
let fpsTime = Date.now();
let connected = false;

function updateStatus(msg) {
  status.textContent = msg;
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = proto + '://' + location.host + '/ws';
  updateStatus('Connecting to ' + url + ' ...');
  ws = new WebSocket(url);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {
    connected = true;
    overlay.style.display = 'none';
    updateStatus('Connected — waiting for stream...');
    // Send stream request for old native streaming protocol
    try {
      ws.send(JSON.stringify({
        type: 'requestStream',
        width: canvas.width,
        height: canvas.height,
        fps: 30
      }));
    } catch(e) {}
  };

  ws.onmessage = (e) => {
    if (e.data instanceof ArrayBuffer) {
      // Binary frame — JPEG image
      const blob = new Blob([e.data], {type: 'image/jpeg'});
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width || canvas.width;
        canvas.height = img.height || canvas.height;
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        frameCount++;
        const now = Date.now();
        if (now - fpsTime > 1000) {
          lastFPS = Math.round(frameCount * 1000 / (now - fpsTime));
          frameCount = 0;
          fpsTime = now;
          updateStatus('Streaming — ' + lastFPS + ' FPS | ' + img.width + 'x' + img.height + ' | OceanSim');
        }
      };
      img.onerror = () => URL.revokeObjectURL(url);
      img.src = url;
    } else if (typeof e.data === 'string') {
      // Text message — JSON control
      try {
        const msg = JSON.parse(e.data);
        console.log('Server msg:', msg);
        if (msg.type === 'streamReady' || msg.type === 'ready') {
          updateStatus('Stream ready — waiting for frames...');
        }
      } catch(ex) {
        console.log('Raw text:', e.data.substring(0, 200));
      }
    }
  };

  ws.onclose = (e) => {
    connected = false;
    overlay.style.display = 'block';
    overlay.innerHTML = 'Disconnected (code ' + e.code + ')<br><small>Reconnecting in 3s...</small>';
    updateStatus('Disconnected — reconnecting...');
    setTimeout(connect, 3000);
  };

  ws.onerror = (e) => {
    updateStatus('WebSocket error — check proxy logs');
    console.error('WS error:', e);
  };
}

// Mouse events → send to server as JSON
canvas.addEventListener('mousemove', (e) => {
  if (!connected) return;
  const r = canvas.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width;
  const y = (e.clientY - r.top) / r.height;
  try { ws.send(JSON.stringify({type:'mouseMoved', normalizedX: x, normalizedY: y})); } catch(ex) {}
});

canvas.addEventListener('mousedown', (e) => {
  if (!connected) return;
  const r = canvas.getBoundingClientRect();
  try { ws.send(JSON.stringify({type:'mousePressed', button: e.button,
    normalizedX: (e.clientX - r.left)/r.width, normalizedY: (e.clientY - r.top)/r.height})); } catch(ex) {}
});

canvas.addEventListener('mouseup', (e) => {
  if (!connected) return;
  const r = canvas.getBoundingClientRect();
  try { ws.send(JSON.stringify({type:'mouseReleased', button: e.button,
    normalizedX: (e.clientX - r.left)/r.width, normalizedY: (e.clientY - r.top)/r.height})); } catch(ex) {}
});

canvas.addEventListener('wheel', (e) => {
  if (!connected) return;
  e.preventDefault();
  try { ws.send(JSON.stringify({type:'mouseScroll', delta: e.deltaY})); } catch(ex) {}
}, {passive: false});

document.addEventListener('keydown', (e) => {
  if (!connected) return;
  try { ws.send(JSON.stringify({type:'keyPressed', key: e.key, keyCode: e.keyCode})); } catch(ex) {}
});

document.addEventListener('keyup', (e) => {
  if (!connected) return;
  try { ws.send(JSON.stringify({type:'keyReleased', key: e.key, keyCode: e.keyCode})); } catch(ex) {}
});

connect();
</script>
</body>
</html>
"""


async def handle_http(request):
    return web.Response(content_type='text/html', text=HTML)


async def handle_ws(request):
    """Bidirectional WebSocket proxy between browser and Isaac Sim port 48010."""
    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)
    print(f'[proxy] Browser connected from {request.remote}')

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f'ws://127.0.0.1:{ISAAC_WS_PORT}',
                headers={'Sec-WebSocket-Protocol': 'livestream'},
                max_msg_size=0,
            ) as isaac_ws:
                print(f'[proxy] Connected to Isaac Sim on port {ISAAC_WS_PORT}')

                async def fwd_to_browser():
                    async for msg in isaac_ws:
                        if client_ws.closed:
                            break
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            await client_ws.send_bytes(msg.data)
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            print(f'[isaac→browser] {msg.data[:120]}')
                            await client_ws.send_str(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

                async def fwd_to_isaac():
                    async for msg in client_ws:
                        if isaac_ws.closed:
                            break
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            await isaac_ws.send_bytes(msg.data)
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            print(f'[browser→isaac] {msg.data[:120]}')
                            await isaac_ws.send_str(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

                await asyncio.gather(fwd_to_browser(), fwd_to_isaac())

    except aiohttp.ClientConnectorError as e:
        print(f'[proxy] Cannot connect to Isaac Sim port {ISAAC_WS_PORT}: {e}')
        await client_ws.send_str(json.dumps({
            'type': 'error',
            'message': f'Isaac Sim not ready on port {ISAAC_WS_PORT}: {e}'
        }))
    except Exception as e:
        print(f'[proxy] Error: {e}')

    print(f'[proxy] Browser disconnected')
    return client_ws


app = web.Application()
app.router.add_get('/', handle_http)
app.router.add_get('/ws', handle_ws)

if __name__ == '__main__':
    print(f'[proxy] Starting on port 8211, forwarding to Isaac Sim port {ISAAC_WS_PORT}')
    web.run_app(app, host='0.0.0.0', port=8211, access_log=None)
