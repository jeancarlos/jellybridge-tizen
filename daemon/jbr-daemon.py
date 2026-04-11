#!/usr/bin/env python3
"""
JellyBridge Input Daemon
- /key?k=<action>  — inject keyboard event into Jellyfin via xdotool
- /snapshot        — latest JPEG frame captured from X11 display
- /stream          — MJPEG stream (for desktop browsers; Tizen uses /snapshot)
- /health          — liveness check

Usage:
    python3 jbr-daemon.py

Install:
    sudo apt-get install -y xdotool ffmpeg
    sudo cp jbr-daemon.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now jbr-daemon
"""

import http.server
import urllib.parse
import subprocess
import os
import threading
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

# ─── Screen capture ───────────────────────────────────────────────────────────

_latest_frame = None
_frame_lock = threading.Lock()


def _capture_loop():
    """Run ffmpeg continuously, store the latest JPEG frame in memory."""
    global _latest_frame
    env = os.environ.copy()
    env['DISPLAY'] = DISPLAY
    env['XAUTHORITY'] = XAUTHORITY

    cmd = [
        'ffmpeg',
        '-f', 'x11grab', '-r', '60', '-i', DISPLAY,
        '-q:v', '2',       # JPEG quality (1=best, 31=worst)
        '-f', 'mjpeg', 'pipe:1',
    ]

    while True:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env
        )
        buf = b''
        try:
            while True:
                chunk = proc.stdout.read(32768)
                if not chunk:
                    break
                buf += chunk
                # Extract complete JPEG frames
                while True:
                    start = buf.find(b'\xff\xd8')
                    if start == -1:
                        break
                    end = buf.find(b'\xff\xd9', start + 2)
                    if end == -1:
                        break
                    frame = buf[start:end + 2]
                    buf = buf[end + 2:]
                    with _frame_lock:
                        _latest_frame = frame
        except Exception as exc:
            log.warning('capture error: %s', exc)
        finally:
            proc.terminate()


def start_capture():
    t = threading.Thread(target=_capture_loop, daemon=True, name='capture')
    t.start()


# ─── Key injection ────────────────────────────────────────────────────────────

def inject_key(key_name):
    env = os.environ.copy()
    env['DISPLAY'] = DISPLAY
    env['XAUTHORITY'] = XAUTHORITY
    # Target Jellyfin window directly by exact title
    subprocess.Popen(
        ['xdotool', 'search', '--name', 'Jellyfin Media Player',
         'key', '--clearmodifiers', '--', key_name],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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

        elif parsed.path == '/snapshot':
            with _frame_lock:
                frame = _latest_frame
            if frame:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(frame)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(frame)
            else:
                self._respond(503)  # not ready yet

        elif parsed.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type',
                             'multipart/x-mixed-replace; boundary=jbrframe')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            log.info('stream client connected')
            self._serve_stream()
            log.info('stream client disconnected')

        elif parsed.path == '/health':
            self._respond(200)
        else:
            self._respond(404)

    def _serve_stream(self):
        boundary = b'--jbrframe'
        last_frame = None
        try:
            while True:
                with _frame_lock:
                    frame = _latest_frame
                if frame is not None and frame is not last_frame:
                    last_frame = frame
                    msg = (
                        boundary + b'\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'
                        b'\r\n' + frame + b'\r\n'
                    )
                    self.wfile.write(msg)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

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
    start_capture()
    log.info('screen capture started  DISPLAY=%s', DISPLAY)
    server = ThreadedHTTPServer(('0.0.0.0', PORT), Handler)
    log.info('JellyBridge daemon listening on :%d', PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
