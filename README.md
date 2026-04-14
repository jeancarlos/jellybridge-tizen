# PlexBridge

Samsung remote → Plex HTPC control bridge for the Q70A + jeanserver HTPC setup.

```
[Samsung One Remote]
    ↓ Bluetooth (stays paired to TV)
[Q70A — PlexBridge Tizen app — FOREGROUND]
    |— Shows: jeanserver HDMI output via tizen.tvwindow (full screen)
    |— Captures: nav key events (arrows, Enter, Back, Play/Pause)
    |— Forwards: HTTP GET → jeanserver:9000/key?k=<action>
[jeanserver — pbr-daemon.py]
    |— Injects: keyboard events into X11 via xdotool
    ↓
[Plex HTPC — TV mode, reacts to arrow/enter/esc/space/s/a/./,]
    ↓ HDMI-0
[Q70A screen — shown via tvwindow in the Tizen app]
```

The Tizen app stays in the foreground (solving the "background key capture" limitation),
while embedding jeanserver's HDMI output via `tizen.tvwindow` so the user sees Plex HTPC.

---

## Requirements

- Samsung Q70A TV (Tizen 6.0+)
- jeanserver with `xdotool` installed
- Same build pipeline and certificates as `aerial-tizen`

---

## Setup

### 1. Install daemon dependencies on jeanserver

```bash
ssh jean@jeanserver
sudo apt-get install -y xdotool
```

### 2. Deploy daemon to jeanserver

```bash
ssh jean@jeanserver
cp ~/plexbridge-tizen/daemon/pbr-daemon.py ~/scripts/pbr-daemon.py
sudo cp ~/plexbridge-tizen/daemon/pbr-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pbr-daemon
```

### 3. Configure HDMI port

Edit `js/config.js` and set `hdmiPort` to the HDMI port number where jeanserver
is connected on the Samsung TV (check TV remote → Source).

### 4. Setup Tizen toolchain

```bash
./setup.sh
```

Uses the same profile/certificates as `aerial-tizen` (AerialProfile).

### 5. Deploy to TV

```bash
./deploy.sh
```

---

## Key Mapping

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

---

## Auto-launch

Configure via TizenBrew autolaunch (already installed on the TV):

```
TizenBrew → Module settings → Autolaunch → Add PlxBridge0.PlexBridge
```

Remove old entry JlyBridge0.JellyBridge if present.

---

## Daemon health check

```bash
curl http://192.168.1.200:9000/health
# → HTTP 200
```

---

## Running tests

```bash
python3 daemon/test_pbr_daemon.py -v
```
