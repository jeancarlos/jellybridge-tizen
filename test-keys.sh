#!/usr/bin/env bash
# PlexBridge key tester — sends each remote action to the daemon and shows the result.
# Usage: ./test-keys.sh [--auto [DELAY_SECONDS]]
#   --auto        send all keys automatically with a 2s delay (default)
#   --auto 3      send all keys automatically with a 3s delay
#   (no flag)     interactive: press Enter to send each key

SERVER="${PBRT_SERVER:-http://192.168.1.200:9000}"
DELAY="${2:-2}"

# action → description of expected Plex HTPC effect
declare -A EFFECTS=(
  [up]="navigate up"
  [down]="navigate down"
  [left]="navigate left"
  [right]="navigate right"
  [enter]="select / confirm"
  [back]="go back (Escape)"
  [play]="play"
  [pause]="pause"
  [playpause]="toggle play/pause"
  [stop]="return to home (Escape)"
  [info]="info overlay (i)"
  [red]="subtitle selection (s)"
  [green]="audio track selection (a)"
  [yellow]="next chapter (.)"
  [blue]="previous chapter (,)"
)

KEYS=(up down left right enter back play pause playpause stop info red green yellow blue)

send_key() {
  local action="$1"
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER}/key?k=${action}" --max-time 2)
  if [[ "$http_code" == "200" ]]; then
    echo "  → sent  (HTTP 200)"
  elif [[ "$http_code" == "000" ]]; then
    echo "  → ERROR: daemon unreachable at ${SERVER}"
  else
    echo "  → ERROR: HTTP ${http_code}"
  fi
}

echo ""
echo "PlexBridge Key Tester"
echo "Server: ${SERVER}"
echo "─────────────────────────────────────────"

# Quick health check
health=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER}/health" --max-time 2)
if [[ "$health" != "200" ]]; then
  echo "ERROR: daemon not responding at ${SERVER} (health returned ${health})"
  echo "Is pbr-daemon running on jeanserver?"
  exit 1
fi
echo "Daemon: OK"
echo ""

if [[ "$1" == "--auto" ]]; then
  echo "Auto mode — ${DELAY}s between keys. Ctrl+C to stop."
  echo ""
  for action in "${KEYS[@]}"; do
    effect="${EFFECTS[$action]}"
    printf "%-12s  %s\n" "[$action]" "$effect"
    send_key "$action"
    sleep "$DELAY"
  done
else
  echo "Interactive mode — press Enter to send each key, Ctrl+C to stop."
  echo ""
  for action in "${KEYS[@]}"; do
    effect="${EFFECTS[$action]}"
    printf "%-12s  %s  [Enter to send] " "[$action]" "$effect"
    read -r
    send_key "$action"
  done
fi

echo ""
echo "Done."
