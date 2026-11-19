
## Hand-off protocol

Agents that share this branch pass work with commit trailers; `scripts/handoff.py` reads and writes them.
Agents here: `__WAKE_AGENT__` and `__PEER_AGENT__`. The user decides direction.

- `Handoff-To: <agent>` on the commit that finishes a unit of work. Commits without it wake nobody.
- `Handoff-Ack: <sha>` on the commit that answers a hand-off. Until then it is pending.
- Always hand off with `python3 scripts/handoff.py send`. It also appends a line to `.handoff/to-<agent>.log`,
  which is what triggers the wake-up; a trailer typed by hand is listed by `pending` but wakes nobody.
- A file `PAUSE` at the repository root holds all pending hand-offs. Only the user adds or removes it.
- After examining a result, report to the user and stop. Hand new work to another agent only when the user
  assigned or approved it.

Check for work: `python3 scripts/handoff.py pending --as <your name>`. No output means nothing to do.
Full procedure: the `handoff` skill (`.claude/skills/handoff/SKILL.md`, `.agents/skills/handoff/SKILL.md`).

How each agent is woken:
- `__WAKE_AGENT__`: its session subscribes to the branch's draft pull request. The workflow
  `.github/workflows/handoff-notify.yml` comments there on each `Handoff-To: __WAKE_AGENT__`.
- `__PEER_AGENT__`: a watcher outside the agent (`python3 scripts/handoff.py watch --as __PEER_AGENT__ --run ...`)
  queues one message into its session for each new hand-off. Do not schedule the check inside the agent's chat:
  every firing would be a model turn.
