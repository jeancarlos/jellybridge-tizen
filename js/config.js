// JellyBridge configuration — edit to match your setup
var CONFIG = {
  // jeanserver IP on the TV subnet (br1 bridge at 192.168.1.200)
  serverUrl: 'http://192.168.1.200:9000',

  // HDMI port on the Samsung TV where jeanserver is connected (1, 2, 3 or 4)
  hdmiPort: 2,

  // Minimum ms between key sends (debounce for held keys)
  debounce: 120,

  // HTTP request timeout in ms
  timeout: 250
};
