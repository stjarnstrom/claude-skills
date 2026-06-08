#!/usr/bin/env bash
# Initialize / manage a timed goal. Writes a tiny state file the Stop hook reads.
#
# State file layout (.claude/timed-goal.state), one field per line:
#   1: duration_seconds
#   2: started_at (epoch)
#   3: deadline (epoch)
#   4: phase            (working | reflect)
#   5+: goal text       (may span multiple lines)
#
# Usage:
#   timed-goal-init.sh <90m|1h|30m|90s> <goal...>
#   timed-goal-init.sh status
#   timed-goal-init.sh stop

STATE_DIR="${CLAUDE_PROJECT_DIR:-$PWD}/.claude"
STATE="$STATE_DIR/timed-goal.state"

human() { printf '%dm %ds' $(( $1 / 60 )) $(( $1 % 60 )); }

usage='Usage: /timed-goal <90m|1h|30m> <goal>   |   /timed-goal status   |   /timed-goal stop'

cmd="${1:-}"
case "$cmd" in
  stop)
    rm -f "$STATE"
    echo "🛑 Timed goal cleared. Stop after this message — take no further action."
    exit 0
    ;;
  status)
    if [ ! -f "$STATE" ]; then echo "ℹ️ No active timed goal."; exit 0; fi
    deadline=$(sed -n '3p' "$STATE"); phase=$(sed -n '4p' "$STATE"); goal=$(sed -n '5,$p' "$STATE")
    now=$(date +%s); rem=$(( deadline - now )); [ "$rem" -lt 0 ] && rem=0
    echo "📊 STATUS — phase=${phase}, $(human "$rem") remaining."
    echo "Goal: ${goal}"
    exit 0
    ;;
  "")
    echo "$usage"
    exit 0
    ;;
esac

dur_raw="$cmd"; shift; goal="$*"
if [ -z "$goal" ]; then echo "$usage"; exit 0; fi

num="${dur_raw//[!0-9]/}"; unit="${dur_raw//[0-9]/}"
if [ -z "$num" ]; then echo "⚠️ Could not parse duration '${dur_raw}'. Try 90m, 1h, or 30m."; exit 0; fi
case "$unit" in
  h|H)     secs=$(( num * 3600 ));;
  s|S)     secs=$num;;
  m|M|"")  secs=$(( num * 60 ));;
  *)       secs=$(( num * 60 ));;
esac

now=$(date +%s); deadline=$(( now + secs ))
mkdir -p "$STATE_DIR"
printf '%s\n%s\n%s\n%s\n%s\n' "$secs" "$now" "$deadline" "working" "$goal" > "$STATE"

echo "✅ TIMED GOAL STARTED — $(human "$secs") on the clock."
echo "Goal: ${goal}"
