#!/usr/bin/env python3
"""
JellyBridge Input Daemon
Receives key actions from the Samsung TV Tizen app via HTTP and injects
keyboard events into X11 (DISPLAY=:0) using xdotool, so Jellyfin Media
Player responds as if the user pressed keys on a physical keyboard.

Usage:
    python3 jbr-daemon.py

Install:
    sudo apt-get install -y xdotool
    sudo cp jbr-daemon.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now jbr-daemon
"""

import http.server
import urllib.parse
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('jbr')

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
    'stop':      'x',        # Jellyfin: stop playback
    'info':      'i',        # Jellyfin: show info overlay
    'red':       'F1',
    'green':     'F2',
    'yellow':    'F3',
    'blue':      'F4',
}


def inject_key(key_name):
    env = os.environ.copy()
    env['DISPLAY'] = DISPLAY
    env['XAUTHORITY'] = XAUTHORITY
    subprocess.Popen(
        ['xdotool', 'key', '--clearmodifiers', '--', key_name],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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
        pass  # suppress default per-request logging


if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    log.info('JellyBridge daemon listening on :%d  DISPLAY=%s', PORT, DISPLAY)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
