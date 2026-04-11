// JellyBridge — Samsung remote → jeanserver input bridge
//
// Architecture:
//   This Tizen app stays in the FOREGROUND so the TV OS delivers all remote
//   key events to it. jeanserver's HDMI output is shown via tvsourcemanager
//   + tizen.tvwindow, so the user sees Jellyfin while the app intercepts keys.

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

// ─── tvwindow ─────────────────────────────────────────────────────────────────
// Shows the HDMI source full-screen behind the transparent app DOM.
function showTVWindow() {
  try {
    tizen.tvwindow.show(
      function() { setStatus(''); },
      function(err) { setStatus('win err: ' + (err && err.message)); },
      ['0px', '0px', '1920px', '1080px'],
      'MAIN'
    );
  } catch (e) {
    setStatus('tvwindow: ' + e.message);
  }
}

// ─── Source switch → tvwindow ─────────────────────────────────────────────────
// Explicitly switches the TV to the configured HDMI port so tvwindow has
// content to render. Called once on init.
function showHDMI() {
  try {
    var sources = webapis.tvsourcemanager.getSourceList();
    var target = null;
    for (var i = 0; i < sources.length; i++) {
      if (sources[i].type === 'HDMI' && sources[i].number === CONFIG.hdmiPort) {
        target = sources[i];
        break;
      }
    }

    if (!target) {
      setStatus('HDMI ' + CONFIG.hdmiPort + ' not found');
      showTVWindow();
      return;
    }

    webapis.tvsourcemanager.setSource(
      target,
      function() {
        // Source is now active — show it in tvwindow
        setTimeout(showTVWindow, 300);
      },
      function(err) {
        setStatus('src: ' + (err && err.message));
        // Still try tvwindow with whatever source is active
        setTimeout(showTVWindow, 300);
      }
    );
  } catch (e) {
    // webapis.tvsourcemanager not available — fall back to tvwindow directly
    setStatus('src api: ' + e.message);
    setTimeout(showTVWindow, 300);
  }
}

// ─── Key event handler ────────────────────────────────────────────────────────
window.addEventListener('keydown', function(e) {
  var action = KEY_MAP[e.keyCode];
  if (!action) return;
  e.preventDefault();
  sendKey(action);
});

// ─── Init ─────────────────────────────────────────────────────────────────────
registerKeys();
showHDMI();
setStatus('JellyBridge');
