---
description: Set a timed goal — work autonomously toward a goal for a fixed duration, then reflect and auto-continue.
argument-hint: "<90m|1h|30m> <goal>   |   status   |   stop"
allowed-tools: Bash, Read, Edit, Write, MultiEdit, Grep, Glob, NotebookEdit, WebFetch
---

!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/timed-goal-init.sh" $ARGUMENTS`

---

The line above is the output of initializing your timed goal.

- If it shows **usage**, a **status report**, or says the goal was **cleared/stopped**, simply relay that line to me and then STOP. Take no further action.
- Otherwise a timed working block is now **ACTIVE**. Begin immediately:
  - Work autonomously toward the goal. Repeatedly pick the single highest-value next increment, implement it, and verify it works.
  - Do not ask me questions during the run — make sensible decisions and keep moving.
  - Don't time your work to the clock or wrap up early. You'll be stopped automatically when the budget runs out — until then there's always more to do, so just keep doing the next valuable thing.
  - Commit logically-grouped progress when it makes sense.
  - At the end of each turn a Stop hook checks the clock: while time remains it prompts you to reflect and keep improving the work; when the timer expires it lets you stop. To end early I'll type `/timed-goal stop` or press Esc.

Start now.
