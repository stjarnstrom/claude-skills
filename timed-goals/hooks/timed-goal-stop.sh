#!/usr/bin/env bash
# Stop hook for the timed-goals plugin.
#
# Behavior (checked at the end of every turn):
#   time remaining     -> block: reflect and keep improving the work toward the goal
#   time's up          -> clear the goal, allow Claude to stop
#   no state / broken  -> allow stop (never trap the user)
#
# Output contract:
#   exit 0, no stdout                                  -> allow Claude to stop
#   exit 0, {"decision":"block","reason":"..."} stdout -> keep Claude working
#
# IMPORTANT: the remaining time is deliberately NOT told to Claude. Exposing a countdown
# makes Claude self-pace and treat 0s as a hard stop for *itself* — so near the deadline it
# keeps trying to wrap up while the hook keeps it going, burning the tail of the budget in a
# stop/continue loop. The hook is the sole timekeeper; Claude just keeps doing valuable work
# until it is stopped. (Users can still check the clock with `/timed-goal status`.)
#
# NOTE: requires CLAUDE_CODE_STOP_HOOK_BLOCK_CAP raised (e.g. 0) so the loop isn't capped at
# 8 blocks before the deadline.

STATE="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/timed-goal.state"
[ -f "$STATE" ] || exit 0

deadline=$(sed -n '3p' "$STATE")
goal=$(sed -n '5,$p' "$STATE")

# Bail out (allow stop) if the deadline is missing/garbage, so a bad file can't trap the session.
case "$deadline" in ''|*[!0-9]*) exit 0;; esac

now=$(date +%s)

# Time's up: consume the goal and allow a normal stop.
if [ "$now" -ge "$deadline" ]; then
  rm -f "$STATE"
  exit 0
fi

# Time remains: keep working. No countdown is exposed (see header note).
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\t'/\\t}"
  printf '"%s"' "$s"
}

reason="⏳ TIMED GOAL still in progress — keep working.
Goal: ${goal}

This is open-ended work with no finish line you need to hit. You will be stopped automatically when the time budget runs out, so do NOT try to wrap up, summarize, or stop on your own, and do not pace yourself toward a deadline.

Reflect, then take the work further:
- What is weakest or incomplete right now, and how can you strengthen it?
- How can you push this further toward the goal?
- What deserves focus next, and what would add the most value (tests, docs, edge cases, polish)?

Pick the single highest-value next improvement, implement it, and verify it works. Commit logically-grouped progress when it makes sense. Don't ask me questions — make reasonable decisions and keep going."

printf '{"decision":"block","reason":%s}\n' "$(json_escape "$reason")"
exit 0
