# Timed Goals

A [Claude Code](https://code.claude.com) plugin that turns a generic goal + a time budget
into an autonomous work session. Part of the
[Tromb plugin marketplace](../../README.md).

```
/timed-goal 90m harden the auth module so it's properly testable
```

Claude works toward the goal for the whole duration. At the end of **every turn**, while
time remains, it's prompted to **reflect** on its work — what to improve, how to take it
further, what to focus on — and then keep going. When the timer runs out, it's allowed to
stop.

## How it works

The engine is a **`Stop` hook**. Every time Claude tries to end its turn, the hook checks
the clock and either lets it stop or pushes it to keep going by returning:

```json
{ "decision": "block", "reason": "…reflect and keep improving…" }
```

A tiny state file (`.claude/timed-goal.state`, in the project you run it in) records the
goal and the deadline:

| Condition (at end of a turn) | Hook action |
|------------------------------|-------------|
| time remaining | **block** → "reflect on the work, then implement the highest-value improvement" |
| time's up | clear the goal, **allow stop** |
| no state / malformed | **allow stop** (normal Claude behavior) |

```
/timed-goal 90m <goal>
        │
        ▼
  ┌▶ end of a turn ──── time left? ──yes──▶ reflect + keep improving ──┐
  │       │                                                            │
  └───────┼────────────────────────────────────────────────────────-─┘
          │
         no (time's up) ──▶ allow stop   (or earlier: /timed-goal stop · Esc)
```

The deadline is a hard stop — the loop self-terminates when the timer expires. You can also
end it early with `/timed-goal stop` or `Esc`.

## Install

From the Tromb marketplace:
```
/plugin marketplace add tromb-dev/claude-plugins
/plugin install timed-goals@tromb
```

### Required one-time setup — raise the Stop-hook block cap

Claude Code overrides a `Stop` hook after **8 consecutive blocks without progress**, to stop
runaway loops. A long timed goal can creep toward that during quiet stretches, so give it
headroom. **The plugin can't set this for you** — Claude Code ignores `env` in a plugin's
settings (only `agent`/`subagentStatusLine` are honored) — so add it to a real settings file
(`~/.claude/settings.json` for all projects, or a project's `.claude/settings.json`) and
**restart Claude Code** (it's read at startup):

```json
{
  "env": {
    "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "30"
  }
}
```

- `30` is a comfortable backstop: during an active goal Claude makes progress each turn, so
  the counter resets and never reaches it — but if Claude ever gets genuinely stuck (30
  straight blocks with no progress) the run ends instead of looping forever.
- Want it to never auto-terminate before the deadline? Use a larger number, or `"0"` to
  disable the cap entirely.

> Rolling out to a team? Ship this env var together with the plugin via a committed
> `.claude/settings.json` — see [Team rollout](../../README.md#team-rollout-zero-touch).

## Usage

| Command | Effect |
|---------|--------|
| `/timed-goal 90m <goal>` | Start a 90-minute autonomous run toward `<goal>` |
| `/timed-goal 1h <goal>` | Hours (`h`), minutes (`m`, default), seconds (`s`) all work |
| `/timed-goal status` | Show time remaining without changing anything |
| `/timed-goal stop` | Clear the goal; Claude stops after the current step |
| `Esc` | Interrupt the current working turn immediately |

## Files

```
.claude-plugin/
  plugin.json          # plugin manifest
commands/
  timed-goal.md        # the /timed-goal command (parses args, starts the run)
scripts/
  timed-goal-init.sh   # writes/updates/clears the state file
hooks/
  hooks.json           # registers the Stop hook
  timed-goal-stop.sh   # the engine: reflect-and-continue vs allow-stop
```

## Notes & caveats

- **Continuous, not scheduled.** Unlike `/loop` (which sleeps between iterations), this
  keeps Claude in one continuous working session — right for "work for an hour," not "check
  something every hour."
- **No questions mid-run.** During the run Claude is told to make its own decisions and not
  stop to ask you, so it doesn't stall waiting for input.
- **Claude is not told the remaining time — on purpose.** Exposing a countdown makes Claude
  treat 0s as its own hard deadline, so near the end it tries to wrap up while the hook keeps
  it going, wasting the tail of the budget in a stop/continue loop. The hook is the sole
  timekeeper. (You can still check the clock yourself with `/timed-goal status`.)
- **Per-project state.** The state file lives in the current project's `.claude/`, so goals
  are scoped per project.
- **Self-recovering.** If the state file is missing or malformed, the hook allows a normal
  stop — a bad file can't trap your session.
