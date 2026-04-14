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
            'xdotool', 'search', '--maxdepth', '10', '--name', 'Plex HTPC',
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
