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
        self.server.server_close()
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
