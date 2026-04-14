# PlexBridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert jellybridge-tizen (Jellyfin remote bridge) to PlexBridge — retarget to Plex HTPC, fix HDMI display bug, fix key injection, and rebrand.

**Architecture:** Same three-layer design: transparent Tizen app on Samsung TV captures remote keys → HTTP GET → Python daemon on jeanserver → xdotool injects keys into Plex HTPC window. Two bugs fixed as part of conversion: missing `tv.window` Tizen privilege (HDMI not showing) and wrong xdotool window search target (keys not reaching desktop).

**Tech Stack:** JavaScript (Tizen Web API 6.0), Python 3, xdotool, systemd, Tizen CLI (`tizen` tool).

---

## File Map

| File | Action | What changes |
|---|---|---|
| `icon.png` | Replace | Plex brand icon (converted from Downloads) |
| `config.xml` | Modify | New IDs, add `tv.window` privilege |
| `index.html` | Modify | Update `<title>` |
| `js/main.js` | Modify | Fix `tvwindow.show()` integer pixels |
| `deploy.sh` | Modify | New APP ID and wgt filename |
| `daemon/jbr-daemon.py` → `daemon/pbr-daemon.py` | Rename+modify | New window target, Plex key map, log prefix |
| `daemon/test_pbr_daemon.py` | Create | Unit + HTTP integration tests |
| `daemon/jbr-daemon.service` → `daemon/pbr-daemon.service` | Rename+modify | New description, updated ExecStart path |
| `README.md` | Modify | All JellyBridge references → PlexBridge |

---

## Task 1: Replace app icon

**Files:**
- Modify: `icon.png`

- [ ] **Step 1: Convert webp to png**

```bash
dwebp /home/jean/Downloads/plex-icon-filled-256.webp -o /home/jean/jellybridge-tizen/icon.png
```

If `dwebp` is not installed:
```bash
ffmpeg -i /home/jean/Downloads/plex-icon-filled-256.webp /home/jean/jellybridge-tizen/icon.png
```

- [ ] **Step 2: Verify output**

```bash
file /home/jean/jellybridge-tizen/icon.png
# Expected: PNG image data, 256 x 256
```

- [ ] **Step 3: Commit**

```bash
cd /home/jean/jellybridge-tizen
git add icon.png
git commit -m "chore: replace icon with Plex brand icon"
```

---

## Task 2: Rename and update daemon

**Files:**
- Rename: `daemon/jbr-daemon.py` → `daemon/pbr-daemon.py`

- [ ] **Step 1: Rename file**

```bash
cd /home/jean/jellybridge-tizen
git mv daemon/jbr-daemon.py daemon/pbr-daemon.py
```

- [ ] **Step 2: Replace full file content**

Replace the entire content of `daemon/pbr-daemon.py` with:

```python
#!/usr/bin/env python3
"""
PlexBridge Input Daemon
- /key?k=<action>  — inject keyboard event into Plex HTPC via xdotool
- /health          — liveness check
"""

import http.server
import urllib.parse
import subprocess
import os
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('pbr')

# Configuration
DISPLAY = os.environ.get('DISPLAY', ':0')
XAUTHORITY = os.environ.get('XAUTHORITY', os.path.expanduser('~/.Xauthority'))
PORT = 9000

# Action labels from Tizen app → xdotool key names
KEY_MAP = {
    'up':        'Up',
    'down':      'Down',
    'left':      'Left',
    'right':     'Right',
    'enter':     'Return',
    'back':      'Escape',
    'play':      'space',
    'pause':     'space',
    'playpause': 'space',
    'stop':      'Escape',   # Plex has no stop — returns to home
    'info':      'i',        # Plex HTPC: info overlay
    'red':       's',        # Plex HTPC: subtitle selection
    'green':     'a',        # Plex HTPC: audio track selection
    'yellow':    'period',   # Plex HTPC: next chapter
    'blue':      'comma',    # Plex HTPC: previous chapter
}

# ─── Key injection ────────────────────────────────────────────────────────────

_env = os.environ.copy()
_env['DISPLAY'] = DISPLAY
if os.path.exists(XAUTHORITY):
    _env['XAUTHORITY'] = XAUTHORITY

def inject_key(key_name):
    try:
        cmd = [
            'xdotool', 'search', '--name', 'Plex HTPC',
            'windowactivate', '--sync',
            'key', '--clearmodifiers', '--', key_name
        ]
        subprocess.Popen(
            cmd,
            env=_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log.error('Failed to inject key %s: %s', key_name, e)

# ─── HTTP handler ─────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/key':
            action = params.get('k', [None])[0]
            key = KEY_MAP.get(action) if action else None
            if key:
                inject_key(key)
                log.info('%s -> %s', action, key)
                self._respond(200)
            else:
                self._respond(400)

        elif parsed.path == '/health':
            self._respond(200)
        else:
            self._respond(404)

    def _respond(self, code):
        self.send_response(code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def log_message(self, *args):
        pass


class ThreadedHTTPServer(http.server.HTTPServer):
    """Each request handled in its own thread."""
    def process_request(self, request, client_address):
        t = threading.Thread(target=self._handle, args=(request, client_address))
        t.daemon = True
        t.start()

    def _handle(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


if __name__ == '__main__':
    log.info('PlexBridge daemon listening on :%d', PORT)
    server = ThreadedHTTPServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
```

- [ ] **Step 3: Verify syntax**

```bash
python3 -m py_compile daemon/pbr-daemon.py && echo "OK"
# Expected: OK
```

---

## Task 3: Write and run daemon tests

**Files:**
- Create: `daemon/test_pbr_daemon.py`

- [ ] **Step 1: Create test file**

```python
#!/usr/bin/env python3
"""Tests for pbr-daemon.py — runs without X11 or xdotool."""
import importlib.util
import os
import threading
import http.client
import time
import unittest
from unittest import mock

def _load_daemon():
    path = os.path.join(os.path.dirname(__file__), 'pbr-daemon.py')
    spec = importlib.util.spec_from_file_location('pbr_daemon', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

pbr = _load_daemon()

TEST_PORT = 19001  # avoids conflict with live daemon on 9000


class TestKeyMap(unittest.TestCase):
    def test_all_tizen_actions_present(self):
        required = {'up', 'down', 'left', 'right', 'enter', 'back',
                    'play', 'pause', 'playpause', 'stop', 'info',
                    'red', 'green', 'yellow', 'blue'}
        missing = required - set(pbr.KEY_MAP)
        self.assertEqual(missing, set(), f'Missing KEY_MAP entries: {missing}')

    def test_navigation_keys(self):
        self.assertEqual(pbr.KEY_MAP['up'], 'Up')
        self.assertEqual(pbr.KEY_MAP['down'], 'Down')
        self.assertEqual(pbr.KEY_MAP['left'], 'Left')
        self.assertEqual(pbr.KEY_MAP['right'], 'Right')
        self.assertEqual(pbr.KEY_MAP['enter'], 'Return')

    def test_back_and_stop_are_escape(self):
        self.assertEqual(pbr.KEY_MAP['back'], 'Escape')
        self.assertEqual(pbr.KEY_MAP['stop'], 'Escape')

    def test_plex_color_button_shortcuts(self):
        self.assertEqual(pbr.KEY_MAP['red'], 's')         # subtitles
        self.assertEqual(pbr.KEY_MAP['green'], 'a')       # audio
        self.assertEqual(pbr.KEY_MAP['yellow'], 'period') # next chapter
        self.assertEqual(pbr.KEY_MAP['blue'], 'comma')    # prev chapter


class TestHttpHandler(unittest.TestCase):
    def setUp(self):
        self.injected = []
        self._patcher = mock.patch.object(
            pbr, 'inject_key', side_effect=self.injected.append
        )
        self._patcher.start()
        self.server = pbr.ThreadedHTTPServer(('127.0.0.1', TEST_PORT), pbr.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.05)  # give server a moment to bind

    def tearDown(self):
        self.server.shutdown()
        self._patcher.stop()

    def _get(self, path):
        conn = http.client.HTTPConnection('127.0.0.1', TEST_PORT, timeout=2)
        conn.request('GET', path)
        resp = conn.getresponse()
        conn.close()
        return resp.status

    def test_health_returns_200(self):
        self.assertEqual(self._get('/health'), 200)

    def test_valid_key_returns_200_and_injects(self):
        status = self._get('/key?k=enter')
        time.sleep(0.05)  # wait for threaded handler
        self.assertEqual(status, 200)
        self.assertEqual(self.injected, ['Return'])

    def test_unknown_action_returns_400(self):
        status = self._get('/key?k=nonexistent')
        self.assertEqual(status, 400)
        self.assertEqual(self.injected, [])

    def test_missing_k_param_returns_400(self):
        self.assertEqual(self._get('/key'), 400)

    def test_unknown_path_returns_404(self):
        self.assertEqual(self._get('/unknown'), 404)

    def test_plex_subtitle_key_maps_correctly(self):
        self._get('/key?k=red')
        time.sleep(0.05)
        self.assertEqual(self.injected, ['s'])

    def test_plex_chapter_next_maps_correctly(self):
        self._get('/key?k=yellow')
        time.sleep(0.05)
        self.assertEqual(self.injected, ['period'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests — expect all pass**

```bash
cd /home/jean/jellybridge-tizen
python3 daemon/test_pbr_daemon.py -v
```

Expected output:
```
test_all_tizen_actions_present ... ok
test_back_and_stop_are_escape ... ok
test_health_returns_200 ... ok
test_missing_k_param_returns_400 ... ok
test_navigation_keys ... ok
test_plex_chapter_next_maps_correctly ... ok
test_plex_color_button_shortcuts ... ok
test_plex_subtitle_key_maps_correctly ... ok
test_unknown_action_returns_400 ... ok
test_unknown_path_returns_404 ... ok
test_valid_key_returns_200_and_injects ... ok
```

- [ ] **Step 3: Commit**

```bash
git add daemon/pbr-daemon.py daemon/test_pbr_daemon.py
git commit -m "feat: rename daemon to pbr, retarget to Plex HTPC, remap keys"
```

---

## Task 4: Rename and update service file

**Files:**
- Rename: `daemon/jbr-daemon.service` → `daemon/pbr-daemon.service`

- [ ] **Step 1: Rename file**

```bash
cd /home/jean/jellybridge-tizen
git mv daemon/jbr-daemon.service daemon/pbr-daemon.service
```

- [ ] **Step 2: Replace file content**

Full content of `daemon/pbr-daemon.service`:

```ini
[Unit]
Description=PlexBridge Input Daemon
After=network.target

[Service]
Type=simple
User=jean
ExecStart=/usr/bin/python3 /home/jean/scripts/pbr-daemon.py
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/jean/.Xauthority

[Install]
WantedBy=multi-user.target
```

Note: ExecStart uses `~/scripts/pbr-daemon.py` — the deploy task copies the script there, decoupling the service from the repo directory name.

- [ ] **Step 3: Commit**

```bash
git add daemon/pbr-daemon.service
git commit -m "chore: rename service file to pbr-daemon"
```

---

## Task 5: Update Tizen app — config.xml

**Files:**
- Modify: `config.xml`

- [ ] **Step 1: Replace file content**

Full content of `config.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<widget xmlns="http://www.w3.org/ns/widgets" xmlns:tizen="http://tizen.org/ns/widgets"
  id="http://jeansouza.dev/plexbridge" version="1.0.0" viewmodes="maximized">
  <tizen:application id="PlxBridge0.PlexBridge" package="PlxBridge0" required_version="6.0"/>
  <content src="index.html"/>
  <feature name="http://tizen.org/feature/screen.size.all"/>
  <icon src="icon.png"/>
  <name>PlexBridge</name>
  <tizen:privilege name="http://tizen.org/privilege/internet"/>
  <tizen:privilege name="http://tizen.org/privilege/tv.inputdevice"/>
  <tizen:privilege name="http://tizen.org/privilege/tv.input"/>
  <tizen:privilege name="http://tizen.org/privilege/tv.window"/>
  <tizen:profile name="tv-samsung"/>
  <tizen:setting screen-orientation="landscape" context-menu="disable" background-support="enable"/>
</widget>
```

Key changes from original:
- `id`: `jellybridge` → `plexbridge`
- `tizen:application id`: `JlyBridge0.JellyBridge` → `PlxBridge0.PlexBridge`
- `package`: `JlyBridge0` → `PlxBridge0`
- `<name>`: `JellyBridge` → `PlexBridge`
- Added: `<tizen:privilege name="http://tizen.org/privilege/tv.window"/>` ← **this was the HDMI bug**

- [ ] **Step 2: Commit**

```bash
git add config.xml
git commit -m "fix: add tv.window privilege, rename Tizen app to PlexBridge"
```

---

## Task 6: Update index.html

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Update title tag**

In `index.html`, change line 5:
```html
  <title>JellyBridge</title>
```
to:
```html
  <title>PlexBridge</title>
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "chore: update title to PlexBridge"
```

---

## Task 7: Fix HDMI display in main.js

**Files:**
- Modify: `js/main.js`

- [ ] **Step 1: Fix tvwindow.show() parameters**

In `js/main.js`, change line 71:
```javascript
                tizen.tvwindow.show(['0', '0', '100%', '100%'], 'BEHIND', function() {
```
to:
```javascript
                tizen.tvwindow.show([0, 0, 1920, 1080], 'BEHIND', function() {
```

The Tizen `tvwindow.show()` API expects integer pixel values, not string percentages. Using strings silently fails.

- [ ] **Step 2: Commit**

```bash
git add js/main.js
git commit -m "fix: pass integer pixels to tvwindow.show() — fixes HDMI not displaying"
```

---

## Task 8: Update deploy.sh

**Files:**
- Modify: `deploy.sh`

- [ ] **Step 1: Update APP variable and wgt filename**

In `deploy.sh`, change:
```bash
APP="JlyBridge0.JellyBridge"
```
to:
```bash
APP="PlxBridge0.PlexBridge"
```

And change:
```bash
cp "$DIR/JellyBridge.wgt" /tmp/jellybridge.wgt
```
to:
```bash
cp "$DIR/PlexBridge.wgt" /tmp/plexbridge.wgt
```

And change:
```bash
tizen install -n jellybridge.wgt -t "$TV_NAME" -- /tmp
```
to:
```bash
tizen install -n plexbridge.wgt -t "$TV_NAME" -- /tmp
```

- [ ] **Step 2: Commit**

```bash
git add deploy.sh
git commit -m "chore: update deploy.sh for PlexBridge app ID"
```

---

## Task 9: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Bulk rename JellyBridge → PlexBridge references**

```bash
cd /home/jean/jellybridge-tizen
sed -i \
  -e 's/JellyBridge/PlexBridge/g' \
  -e 's/jellybridge/plexbridge/g' \
  -e 's/JlyBridge0\.JellyBridge/PlxBridge0.PlexBridge/g' \
  -e 's/jbr-daemon/pbr-daemon/g' \
  README.md
```

- [ ] **Step 2: Update key mapping table**

In `README.md`, replace the Key Mapping table section. Find the block starting with `| Samsung Remote | Action sent | Jellyfin effect |` and replace it with:

```
| Samsung Remote | Action sent | Plex HTPC effect |
|---|---|---|
| ▲ ▼ ◀ ▶ | up/down/left/right | Navigate |
| OK | enter | Select |
| Back | back | Go back (Escape) |
| ⏯ | playpause | Play / Pause |
| ▶ Play | play | Play |
| ⏸ Pause | pause | Pause |
| ⏹ Stop | stop | Back to home (Escape) |
| ⓘ Info | info | Info overlay (i) |
| Red | red | Subtitle selection (s) |
| Green | green | Audio track selection (a) |
| Yellow | yellow | Next chapter (.) |
| Blue | blue | Previous chapter (,) |
| Volume ▲▼, Power | *(not captured)* | Native TV behavior |
```

- [ ] **Step 3: Update architecture diagram target line**

In `README.md`, change the Jellyfin Media Player line in the diagram:
```
[Jellyfin Media Player — TV mode, reacts to arrow/enter/esc/space]
```
to:
```
[Plex HTPC — TV mode, reacts to arrow/enter/esc/space/s/a/./,]
```

- [ ] **Step 4: Update TizenBrew autolaunch section**

In `README.md`, change the autolaunch command from:
```
TizenBrew → Module settings → Autolaunch → Add JlyBridg0.JellyBridge
```
to:
```
TizenBrew → Module settings → Autolaunch → Add PlxBridge0.PlexBridge
```
Add a note: `Remove old entry JlyBridge0.JellyBridge if present.`

- [ ] **Step 5: Add testing section**

Append to the end of `README.md`:

```
## Running tests

    python3 daemon/test_pbr_daemon.py -v
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: update README for PlexBridge"
```

---

## Task 10: Deploy daemon to jeanserver

Run these commands from your local machine.

- [ ] **Step 1: Stop and disable the old jbr-daemon service**

```bash
ssh jean@jeanserver 'sudo systemctl stop jbr-daemon; sudo systemctl disable jbr-daemon'
```

Expected: no error (or "Unit jbr-daemon.service not loaded" if it was never started — that's fine).

- [ ] **Step 2: Copy new daemon script**

```bash
scp /home/jean/jellybridge-tizen/daemon/pbr-daemon.py jean@jeanserver:~/scripts/pbr-daemon.py
```

- [ ] **Step 3: Copy and install new service file**

```bash
scp /home/jean/jellybridge-tizen/daemon/pbr-daemon.service jean@jeanserver:/tmp/pbr-daemon.service
ssh jean@jeanserver 'sudo cp /tmp/pbr-daemon.service /etc/systemd/system/pbr-daemon.service && sudo systemctl daemon-reload && sudo systemctl enable --now pbr-daemon'
```

- [ ] **Step 4: Verify daemon is running**

```bash
ssh jean@jeanserver 'sudo systemctl status pbr-daemon --no-pager'
```

Expected: `Active: active (running)`

- [ ] **Step 5: Verify health endpoint responds**

```bash
curl http://192.168.1.200:9000/health
```

Expected: HTTP 200 (curl exits 0, no error output)

- [ ] **Step 6: Test key injection manually**

Open Plex HTPC on jeanserver so it's visible. Then:

```bash
curl "http://192.168.1.200:9000/key?k=up"
```

Expected: focus moves up in Plex HTPC. If Plex HTPC isn't focused or the window name doesn't match, check:

```bash
ssh jean@jeanserver 'DISPLAY=:0 XAUTHORITY=~/.Xauthority xdotool search --name "." | xargs -I{} xdotool getwindowname {} 2>/dev/null'
```

If the window title isn't `Plex HTPC`, update line 57 of `daemon/pbr-daemon.py` with the correct name and re-deploy.

---

## Task 11: Deploy Tizen app to TV

- [ ] **Step 1: Ensure TV is on and connected to the dev machine**

```bash
cd /home/jean/jellybridge-tizen
cat .env
```

Verify `TV_NAME` in `.env` matches your TV (check with `tizen devices`).

- [ ] **Step 2: Run deploy script**

```bash
./deploy.sh
```

Expected output:
```
==> Packaging...
==> Installing...
==> Launching...
==> Done!
```

- [ ] **Step 3: Verify HDMI shows jeanserver output**

On the TV, PlexBridge should launch and immediately switch to HDMI and show the jeanserver desktop. The status line should briefly show `HDMI 2 active` then clear.

If HDMI still doesn't show, check TV source list:
- TV remote → Source → confirm which port number jeanserver is on
- Update `hdmiPort` in `js/config.js` if needed and redeploy

- [ ] **Step 4: Update TizenBrew autolaunch**

On the TV:
```
TizenBrew → Module settings → Autolaunch
→ Remove: JlyBridge0.JellyBridge  (if present)
→ Add: PlxBridge0.PlexBridge
```

- [ ] **Step 5: Final key test**

With PlexBridge running and Plex HTPC visible:
- Arrow keys → navigate Plex
- OK → select
- Back → go back
- Red → subtitle menu opens
- Green → audio track menu opens
- Yellow → moves to next chapter
- Blue → moves to previous chapter
