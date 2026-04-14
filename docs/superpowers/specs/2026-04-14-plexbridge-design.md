# PlexBridge Design

**Date:** 2026-04-14
**Status:** Approved

## Overview

Convert `jellybridge-tizen` to `plexbridge-tizen`: same Samsung TV remote → jeanserver input bridge architecture, retargeted from Jellyfin to Plex HTPC. Fix two existing bugs (HDMI not showing, keys not injected) as part of the conversion.

---

## Architecture

```
[Samsung One Remote]
    ↓ Bluetooth (paired to TV)
[Q70A — PlexBridge Tizen app — FOREGROUND]
    |— Shows: jeanserver HDMI output via tizen.tvwindow (full screen)
    |— Captures: remote key events
    |— Forwards: HTTP GET → jeanserver:9000/key?k=<action>
[jeanserver — pbr-daemon.py]
    |— Injects: keyboard events into X11 via xdotool
    ↓
[Plex HTPC — fullscreen on :0]
    ↓ HDMI
[Q70A screen — shown via tvwindow in the Tizen app]
```

No change to the three-layer structure. Approach: in-place rename of the existing repo.

---

## Changes

### 1. Tizen App — Branding

| Item | From | To |
|---|---|---|
| App name | JellyBridge | PlexBridge |
| Package ID | `JlyBridge0` | `PlxBridge0` |
| Application ID | `JlyBridge0.JellyBridge` | `PlxBridge0.PlexBridge` |
| Icon | `icon.png` (Jellyfin) | Plex icon (convert from `plex-icon-filled-256.webp`) |
| `<title>` in index.html | JellyBridge | PlexBridge |
| Widget ID | `http://jeansouza.dev/jellybridge` | `http://jeansouza.dev/plexbridge` |
| TizenBrew autolaunch entry | `JlyBridge0.JellyBridge` | `PlxBridge0.PlexBridge` |

Files: `config.xml`, `index.html`, `deploy.sh`

---

### 2. Bug Fix — HDMI Not Showing

**Root cause A:** `config.xml` missing `http://tizen.org/privilege/tv.window`. The `tizen.tvwindow` API fails silently without it.

**Root cause B:** `tizen.tvwindow.show()` called with string percentages `['0','0','100%','100%']`. Tizen API expects integer pixels.

**Fix:**
- Add privilege to `config.xml`
- Change show call to `[0, 0, 1920, 1080]`

---

### 3. Bug Fix — Keys Not Reaching Desktop

**Root cause:** `xdotool search --name 'Jellyfin'` finds no window when Plex HTPC is running.

**Fix:** Change search target in daemon from `'Jellyfin'` to `'Plex HTPC'`.

> If `'Plex HTPC'` doesn't match the actual window title, check with:
> `DISPLAY=:0 XAUTHORITY=~/.Xauthority xdotool search --name "." | xargs -I{} xdotool getwindowname {}`

---

### 4. Key Map

| Samsung Remote | Action sent | xdotool key | Notes |
|---|---|---|---|
| ▲ ▼ ◀ ▶ | up/down/left/right | Up/Down/Left/Right | unchanged |
| OK | enter | Return | unchanged |
| Back | back | Escape | unchanged |
| ▶ Play | play | space | unchanged |
| ⏸ Pause | pause | space | unchanged |
| ⏯ Play/Pause | playpause | space | unchanged |
| ⏹ Stop | stop | Escape | Plex has no stop — returns to home |
| ⓘ Info | info | i | Plex HTPC info overlay |
| Red | red | s | Subtitle track selection |
| Green | green | a | Audio track selection |
| Yellow | yellow | period | Next chapter (`.`) |
| Blue | blue | comma | Prev chapter (`,`) |

> Chapter keys (`.` and `,`) are best-guess defaults — adjust after testing if Plex HTPC uses different bindings.

---

### 5. Daemon Rename

| Item | From | To |
|---|---|---|
| Script | `jbr-daemon.py` | `pbr-daemon.py` |
| Service | `jbr-daemon.service` | `pbr-daemon.service` |
| Log prefix | `jbr` | `pbr` |
| Script description | JellyBridge Input Daemon | PlexBridge Input Daemon |

---

### 6. Deploy

Same pipeline as JellyBridge:
1. Convert icon: `cwebp`/`dwebp` or `ffmpeg` to convert `.webp` → `.png`
2. Deploy daemon: copy `pbr-daemon.py` + service to jeanserver, restart systemd unit
3. Package + deploy Tizen app: `./deploy.sh`
4. Update TizenBrew autolaunch to new app ID

---

## Files Changed

| File | Change |
|---|---|
| `config.xml` | Rename, new IDs, add `tv.window` privilege |
| `index.html` | Update title |
| `js/config.js` | No change needed |
| `js/main.js` | Fix `tvwindow.show()` pixel values |
| `icon.png` | Replace with Plex icon |
| `deploy.sh` | Update app ID and wgt filename |
| `daemon/jbr-daemon.py` → `daemon/pbr-daemon.py` | Rename, new window target, new key map |
| `daemon/jbr-daemon.service` → `daemon/pbr-daemon.service` | Rename references |
| `README.md` | Update all references |
