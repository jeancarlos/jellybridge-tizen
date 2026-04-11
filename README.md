# JellyBridge

Samsung remote → Jellyfin Media Player control bridge for the Q70A + jeanserver HTPC setup.

```
[Samsung One Remote]
    ↓ Bluetooth (stays paired to TV)
[Q70A — JellyBridge Tizen app — FOREGROUND]
    |— Shows: jeanserver HDMI output via tizen.tvwindow (full screen)
    |— Captures: nav key events (arrows, Enter, Back, Play/Pause)
    |— Forwards: HTTP GET → jeanserver:9000/key?k=<action>
[jeanserver — jbr-daemon.py]
    |— Injects: keyboard events into X11 via xdotool
    ↓
[Jellyfin Media Player — TV mode, reacts to arrow/enter/esc/space]
    ↓ HDMI-0
[Q70A screen — shown via tvwindow in the Tizen app]
```

The Tizen app stays in the foreground (solving the "background key capture" limitation),
while embedding jeanserver's HDMI output via `tizen.tvwindow` so the user sees Jellyfin.

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
cp ~/jellybridge-tizen/daemon/jbr-daemon.py ~/scripts/jbr-daemon.py
sudo cp ~/jellybridge-tizen/daemon/jbr-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jbr-daemon
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

| Samsung Remote | Action sent | Jellyfin effect |
|---|---|---|
| ▲ ▼ ◀ ▶ | up/down/left/right | Navigate |
| OK | enter | Select |
| Back | back | Go back (Escape) |
| ⏯ | playpause | Play / Pause |
| ▶ Play | play | Play |
| ⏸ Pause | pause | Pause |
| ⏹ Stop | stop | Stop playback |
| ⓘ Info | info | Info overlay |
| Volume ▲▼, Power | *(not captured)* | Native TV behavior |

---

## Auto-launch

Configure via TizenBrew autolaunch (already installed on the TV):

```
TizenBrew → Module settings → Autolaunch → Add JlyBridg0.JellyBridge
```

---

## Daemon health check

```bash
curl http://192.168.1.200:9000/health
# → HTTP 200
```
