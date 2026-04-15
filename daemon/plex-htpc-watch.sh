#!/usr/bin/env bash
# plex-htpc-watch.sh — run Plex HTPC and restart it when it exits
# Intended to run inside a detached screen session:
#   screen -dmS plex /path/to/plex-htpc-watch.sh

export DISPLAY=:0
export XAUTHORITY=/run/user/1000/gdm/Xauthority

while true; do
    flatpak run tv.plex.PlexHTPC
    sleep 2
done
