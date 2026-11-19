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
nothing waits. `wait` and `watch` run until a hand-off arrives; they have no time limit unless you pass
`--timeout <seconds>`, and they fetch every 120 and 300 seconds (`--interval`).

## Setup

1. Install (see the top-level README), commit, push.
2. Tell each agent once: "Read the Hand-off protocol in AGENTS.md; your name is `<name>`."
3. Give each agent one way to be woken, from the sections below. Use one per agent, or every hand-off is
   delivered twice.

Do not schedule the check inside an agent's chat. Every firing is a model turn, almost always to find nothing.
Each mechanism below costs nothing while the agent waits, except where noted.

### Claude Code, cloud session

Open a draft pull request for the branch and have the session subscribe to its activity. The installed workflow
comments there on each hand-off, and the comment wakes the session within seconds.

The workflow announces hand-offs for one agent, `claude` by default. Choose another with
`install.py handoff <repo> --set WAKE_AGENT=<name>`. Only one session can hold a pull request's subscription.

### Claude Code, local session

Right after every `send`, the agent runs this as a background command and ends its turn. The command exits when
a hand-off arrives, which re-invokes the session.

```bash
python3 scripts/handoff.py wait --as claude
```

### Codex, desktop app or CLI

A background job that finishes does not wake a Codex session, so the agent uses `watch`: a plain process that
runs a command once for each new hand-off. Right after every `send`, the agent starts this as a background
terminal and ends its turn.

```bash
python3 scripts/handoff.py watch --as codex --until-delivered --run 'codex queue --thread "$CODEX_THREAD_ID" --message "$HANDOFF_MESSAGE"'
```

- `codex queue` queues a message for an existing Codex session, so the work lands in the same thread and keeps
  its context. A busy thread takes it when it is idle.
- Codex sets `CODEX_THREAD_ID` in the environment of the commands it runs, so nobody has to look the id up. That
  is in Codex's source, not in its documentation (November 2026): check `echo $CODEX_THREAD_ID` in your version.
- `--until-delivered` exits once the next hand-off has been delivered, so polling runs only while the agent
  waits. A second watcher for the same agent in the same clone refuses to start.
- `$HANDOFF_MESSAGE` is a fixed instruction that names the commit and tells the agent to run `pending`. No text
  from the commit is passed to your command.
- Each hand-off is delivered once (the list is kept under `.git/`). A command that fails is tried again on the
  next pass.
- The watcher lives only while the thread stays loaded in the app. The agent's instructions should also say:
  run `pending` once when the thread is reopened.
- Codex's default sandbox blocks this: it has no network, a read-only `.git` and no write access to
  `~/.codex`. The agent's sandbox must allow all three.

### Codex, cloud

Create a monitoring task in the ChatGPT web UI: trigger GitHub, your repository, the pull request's number, an
event that includes comments, and a prompt that tells the agent to run `pending`. The agent cannot create this
task itself. The task wakes the same session.

It fires on every matching pull-request event, hand-off or not, and each firing is a cloud run. The workflow
comments only for the agent it was installed for, so to wake Codex cloud install with
`--set WAKE_AGENT=<its name>`.

### Anything else

Run `watch` yourself (a terminal, tmux, or `--once` from cron or launchd) with whatever command starts or
messages the agent.

## Status

Observed in November 2026, unless marked otherwise.

| Agent | Sending | Being woken |
|---|---|---|
| Claude Code, cloud | Observed | Observed: the workflow commented about 10 s after the push, and the session woke about 3 s later. A push with no hand-off woke nobody. |
| Claude Code, local | Same tool | Not yet run in a real session. `wait` is covered by the tests. |
| Codex, desktop app | Observed: Claude acked 45 s after the commit | Not yet observed. `watch` is covered by the tests; `codex queue` is documented by Codex. |
| Codex, cloud | Observed twice, pushed through ChatGPT's GitHub integration | Observed once by the user who ran the test: the workflow's comment fired the monitoring task in the same session. |

`scripts/test_handoff.py` runs the whole cycle on throwaway repositories: addressee, ack, intermediate commits,
merge when the remote moved, a conflicting merge, concurrent hand-offs, `PAUSE`, `wait`, `watch`, `announce`.

## Limits

- `PAUSE` holds hand-offs back but stops nothing: waiters keep polling, and agents woken through the pull
  request are still woken and find nothing.
- Local wake-ups need the agent's app or session open and the machine awake.
- The workflow trusts everyone who can push to the branch. Pull-request comments are treated as untrusted: the
  skill tells the agent to act only on what `pending` reads from git.
- An agent woken unattended must be allowed to `git push`; check its sandbox settings.
- In shallow clones `pending` only sees the fetched history.
