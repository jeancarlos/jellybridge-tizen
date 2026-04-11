// JellyBridge — Samsung remote → jeanserver input bridge
//
// The app body is fully transparent. When launched while HDMI 2 is active,
// Tizen keeps the HDMI video layer visible behind the transparent DOM.
// The app stays in the foreground, capturing all remote key events and
// forwarding them via HTTP to jbr-daemon.py on jeanserver.

// ─── Keys that need explicit registration with the TV OS ─────────────────────
var REGISTER_KEYS = [
  'MediaPlay', 'MediaPause', 'MediaStop', 'MediaPlayPause',
  'ColorF0Red', 'ColorF1Green', 'ColorF2Yellow', 'ColorF3Blue',
  'Info', 'XF86Back'
];

// ─── Samsung remote keyCode → action label ────────────────────────────────────
var KEY_MAP = {
  38:    'up',
  40:    'down',
  37:    'left',
  39:    'right',
  13:    'enter',
  10009: 'back',
  415:   'play',
  19:    'pause',
  413:   'stop',
  10252: 'playpause',
  457:   'info',
  403:   'red',
  404:   'green',
  405:   'yellow',
  406:   'blue'
};

// ─── State ────────────────────────────────────────────────────────────────────
var lastSent = 0;
var statusEl = document.getElementById('status');
var screenEl = document.getElementById('screen');

// ─── Helpers ──────────────────────────────────────────────────────────────────
function setStatus(msg) {
  statusEl.textContent = msg;
}

function sendKey(action) {
  var now = Date.now();
  if (now - lastSent < CONFIG.debounce) return;
  lastSent = now;

  var xhr = new XMLHttpRequest();
  xhr.timeout = CONFIG.timeout;
  xhr.open('GET', CONFIG.serverUrl + '/key?k=' + action, true);
  xhr.onload    = function() { setStatus(''); };
  xhr.onerror   = function() { setStatus('jeanserver unreachable'); };
  xhr.ontimeout = function() { setStatus('timeout'); };
  xhr.send();
}

// ─── Key registration ─────────────────────────────────────────────────────────
function registerKeys() {
  try {
    var supported = tizen.tvinputdevice.getSupportedKeys();
    var names = supported.map(function(k) { return k.name; });
    REGISTER_KEYS.forEach(function(name) {
      if (names.indexOf(name) !== -1) {
        tizen.tvinputdevice.registerKey(name);
      }
    });
  } catch (e) {
    setStatus('key reg: ' + e.message);
  }
}

// ─── Key event handler ────────────────────────────────────────────────────────
window.addEventListener('keydown', function(e) {
  var action = KEY_MAP[e.keyCode];
  if (!action) return;
  e.preventDefault();
  sendKey(action);
});

// ─── Screen polling ───────────────────────────────────────────────────────────
function startStream() {
  var snapshotUrl = CONFIG.serverUrl + '/snapshot';
  var frameCount = 0;

  screenEl.onload = function() {
    frameCount++;
    if (frameCount === 1) setStatus('');  // clear "Connecting..." on first frame
    // Load next frame immediately after current one renders
    screenEl.src = snapshotUrl + '?t=' + Date.now();
  };
  screenEl.onerror = function() {
    setStatus('stream error — retrying');
    setTimeout(function() {
      screenEl.src = snapshotUrl + '?t=' + Date.now();
    }, 1000);
  };

  setStatus('Connecting to jeanserver...');
  screenEl.src = snapshotUrl + '?t=' + Date.now();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
registerKeys();
startStream();
