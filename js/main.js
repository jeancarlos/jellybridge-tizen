// JellyBridge — Samsung remote → jeanserver input bridge
//
// The app body is fully transparent. Tizen keeps the HDMI video layer 
// visible behind the transparent DOM. The app stays in the foreground, 
// capturing all remote key events and forwarding them via HTTP to jbr-daemon.py.

// ─── Keys that need explicit registration with the TV OS ─────────────────────
var REGISTER_KEYS = [
  'MediaPlay', 'MediaPause', 'MediaStop', 'MediaPlayPause',
  'ColorF0Red', 'ColorF1Green', 'ColorF2Yellow', 'ColorF3Blue',
  'Info', 'XF86Back', 'Return'
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

// ─── Input Switching ──────────────────────────────────────────────────────────
//
// Status messages are intentionally persistent here for diagnostics.
// Each step labels itself so we can see exactly where the API stops.
//
function switchToHDMI() {
  if (!tizen || !tizen.tvwindow) {
    setStatus('ERR: no tvwindow API');
    return;
  }

  setStatus('getSources...');
  tizen.tvwindow.getAvailableSources(function(sources) {
    var list = sources.map(function(s) {
      return s.type + (s.number !== undefined ? s.number : '');
    }).join(' ');
    setStatus('sources: ' + list);

    var target = null;
    for (var i = 0; i < sources.length; i++) {
      if (sources[i].type === 'HDMI' && sources[i].number === CONFIG.hdmiPort) {
        target = sources[i];
        break;
      }
    }
    if (!target) {
      setStatus('ERR: HDMI' + CONFIG.hdmiPort + ' not in: ' + list);
      return;
    }

    setStatus('setSource HDMI' + CONFIG.hdmiPort + '...');
    tizen.tvwindow.setSource(target, function() {
      setStatus('show...');
      // Brief delay after setSource — some Samsung firmware needs time
      // before the video layer accepts the show() call.
      setTimeout(function() {
        tizen.tvwindow.show(
          function() { setStatus('HDMI' + CONFIG.hdmiPort + ' OK'); },
          function(err) { setStatus('ERR show: ' + err.message); },
          ['0px', '0px', '1920px', '1080px'],
          'MAIN',
          'BEHIND'
        );
      }, 500);
    }, function(err) {
      setStatus('ERR setSource: ' + err.message);
    });
  }, function(err) {
    setStatus('ERR getSources: ' + err.message);
  });
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
  
  // Always prevent default for mapped keys to avoid TV system interference
  e.preventDefault();
  sendKey(action);
});

// ─── Init ─────────────────────────────────────────────────────────────────────
registerKeys();
switchToHDMI();
