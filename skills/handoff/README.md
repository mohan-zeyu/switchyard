# handoff

Two (or more) agents share a branch. Typically one plans and examines results and another runs the long jobs.
Without this skill a person tells each agent when the other has pushed. With it:

```
researcher                     git branch                      executor
    |  send --to executor  -->  commit + "Handoff-To: executor"    |
    |                                                  woken; pending shows it
    |                                                  ... runs, commits progress (no trailer) ...
    |  <-- commit + "Handoff-To: researcher" + "Handoff-Ack: <sha>"  send --to researcher
woken, examines, acks
notifies the user, stops
```

To watch one round, see the animation in the [top-level README](../../README.md) or
[docs/demo](../../docs/demo/README.md).

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
python3 scripts/handoff.py watch --as codex --run '<command that wakes the agent>'
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
nothing waits.

## Setup

Install (see the top-level README), commit, push. Then give each agent a way to be woken. Pick one per agent.

| Agent runs as | Wake-up | Idle cost | Latency |
|---|---|---|---|
| Claude Code cloud session | Open a draft pull request for the branch and have the session subscribe to its activity. The installed workflow comments there on each hand-off to that agent. | none | seconds |
| Codex desktop app or CLI | The watcher (below), started by the agent after each `send`, queues one message into the same session. | none | the poll interval |
| Claude Code local session | `handoff.py wait --as <name>` as a background command inside the session, or the watcher with `claude -p --resume <session id> "$HANDOFF_MESSAGE"`. | none | the poll interval |
| Anything headless | The watcher with whatever command starts the agent. | none | the poll interval |

The workflow wakes one agent, `claude` by default. Choose another with
`install.py handoff <repo> --set WAKE_AGENT=<name>`.

Then tell each agent once: "Read the Hand-off protocol in AGENTS.md; your name is `<name>`."

### The watcher

Do not schedule the check inside the agent's chat: every firing is a model turn, almost always to find nothing.
`watch` is a plain process instead. It fetches the branch on an interval and runs your command once for each new
hand-off, so nothing but `git fetch` runs while nothing is pending.

The agent starts it itself. Put this in its instructions: right after every `send`, start the watcher as a
background job, then end the turn. For Codex:

```bash
python3 scripts/handoff.py watch --as codex --until-delivered --run 'codex queue --thread "$CODEX_THREAD_ID" --message "$HANDOFF_MESSAGE"'
```

- `codex queue --thread <id> --message <text>` queues a message for an existing Codex session, so the work
  lands in the same thread and keeps its context. A busy thread takes it when it is idle.
- Codex sets `CODEX_THREAD_ID` in the environment of the commands it runs, so nobody has to look the id up. That
  is in Codex's source, not in its documentation (November 2026): check `echo $CODEX_THREAD_ID` in your version.
- `--until-delivered` exits once the next hand-off has been delivered, so polling runs only while the agent is
  waiting. `--timeout <seconds>` also stops it after that long without one. A second watcher for the same agent
  in the same clone refuses to start.
- `$HANDOFF_MESSAGE` is a fixed instruction that names the commit and tells the agent to run `pending`. No text
  from the commit is passed to your command.
- Each hand-off is delivered once (the list is kept under `.git/`). A command that fails is tried again on the
  next pass. A `PAUSE` file holds deliveries.
- The watcher lives only while the thread stays loaded in the app. If the app is closed it is gone, so the
  instructions should also say: run `pending` once when the thread is reopened.
- Codex's default sandbox blocks this: it has no network, a read-only `.git` and no write access to
  `~/.codex`. The agent's sandbox must allow all three for `git fetch` and `codex queue` to work.

To run the watcher yourself instead (a terminal, tmux, or `--once` from cron or launchd), drop `--until-delivered`
and put the thread id in place of `$CODEX_THREAD_ID`; the app's "Copy chat deep link" shows it as
`codex://threads/<id>`.

## What has been verified

- `scripts/test_handoff.py` runs the whole cycle on throwaway repositories: addressee, ack, intermediate
  commits, merge when the remote moved, a conflicting merge, concurrent hand-offs, `PAUSE`, `wait`, `watch`,
  `announce`.
- On a Claude Code cloud session (November 2026): the workflow commented about 10 seconds after a hand-off push,
  and the comment woke the subscribed session about 3 seconds later. A push with no hand-off started no workflow
  run and woke nobody.
- A hand-off sent from a Codex desktop-app session woke the Claude Code cloud session, which acked it 45 seconds
  after the hand-off commit was made.
- Not yet observed by the authors: `watch` delivering into a Codex thread through `codex queue`. The command is
  documented by Codex; the watcher itself is covered by the tests.

## Limits

- Only one session can hold a pull request's subscription.
- Local wake-ups need the watcher running, the agent's app open and the machine awake.
- The workflow trusts everyone who can push to the branch. Pull-request comments are treated as untrusted: the
  skill tells the agent to act only on what `pending` reads from git.
- An agent woken unattended must be allowed to `git push`; check its sandbox settings.
- Run one wake-up mechanism per agent, or every hand-off is delivered twice.
- In shallow clones `pending` only sees the fetched history.
