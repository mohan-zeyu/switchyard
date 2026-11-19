# handoff

Two (or more) agents share a branch. Typically one plans and examines results and another runs the long jobs.
Without this skill a person tells each agent when the other has pushed. With it:

```
researcher                     git branch                      executor
    |  send --to executor  -->  commit + "Handoff-To: executor"    |
    |                                                  pending / wait finds it
    |                                                  ... runs, commits progress (no trailer) ...
    |  <-- commit + "Handoff-To: researcher" + "Handoff-Ack: <sha>"  send --to researcher
woken, examines, acks
notifies the user, stops
```

## Protocol

| Trailer | Meaning |
|---|---|
| `Handoff-To: <agent>` | This commit finishes a unit of work; `<agent>` is next. |
| `Handoff-From: <agent>` | Who sent it. |
| `Handoff-Ack: <sha>` | This commit answers that hand-off. Until then it is pending. |
| `Handoff-Brief: <path>` | Optional: the file the receiver should read. |
| `Handoff-Status: <word>` | Optional: `done`, `interrupted`, `question`. |

Commits without trailers wake nobody. A `PAUSE` file at the repository root holds everything.

## Commands

```bash
python3 scripts/handoff.py pending --as codex
```

```bash
python3 scripts/handoff.py wait --as codex --interval 120
```

```bash
python3 scripts/handoff.py send --as claude --to codex --brief BRIEF.md -m "Subject" -m "Short instructions"
```

```bash
python3 scripts/handoff.py send --as codex --to claude --ack <sha> --status done -m "Report"
```

```bash
python3 scripts/handoff.py ack --as claude <sha>
```

`send` commits what you staged, pushes, and merges first if the remote moved. `pending` prints nothing when
nothing waits, so it is safe to run on a schedule.

## Setup

Install (see the top-level README), commit, push. Then give each agent a way to be woken. Pick one per agent.

| Agent runs as | Wake-up | Latency |
|---|---|---|
| Claude Code cloud session | Open a draft pull request for the branch and have the session subscribe to its activity. The installed workflow comments there on each hand-off to that agent. | seconds |
| Claude Code local session | Run `handoff.py wait --as <name>` as a background command; the session is re-invoked when it exits. | the poll interval |
| Codex desktop app or CLI | A recurring check that runs `handoff.py pending --as <name>` and ends quietly on no output. | the schedule |
| Anything headless | A loop or cron job around `pending` that starts the agent when it prints something. | the schedule |

The workflow wakes one agent, `claude` by default. Choose another with
`install.py handoff <repo> --set WAKE_AGENT=<name>`.

Then tell each agent once: "Read the Hand-off protocol in AGENTS.md; your name is `<name>`."

## What has been verified

- `scripts/test_handoff.py` runs the whole cycle on throwaway repositories: addressee, ack, intermediate
  commits, merge when the remote moved, a conflicting merge, concurrent hand-offs, `PAUSE`, `wait`, `announce`.
- On a Claude Code cloud session (November 2026): the workflow commented about 10 seconds after a hand-off push,
  and the comment woke the subscribed session about 3 seconds later. A push with no hand-off started no workflow
  run and woke nobody.
- Not yet observed end to end: a scheduled check inside the Codex desktop app picking up a hand-off.

## Limits

- Only one session can hold a pull request's subscription.
- Local wake-ups need the app or session open and the machine awake.
- The workflow trusts everyone who can push to the branch. Pull-request comments are treated as untrusted: the
  skill tells the agent to act only on what `pending` reads from git.
- A scheduled agent must be allowed to `git push` unattended; check its sandbox settings.
- In shallow clones `pending` only sees the fetched history.
