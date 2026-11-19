# switchyard

Git-native hand-offs between coding agents.

Skills and workflows that let different coding agents (Claude Code, Codex, or anything that can run a script)
work on one repository without a person carrying messages between them. Everything travels through git, so it
works across machines, vendors, cloud and local sessions.

![One hand-off round: claude commits a brief with "Handoff-To: codex"; codex's recurring check finds it, pushes progress commits that wake nobody, then sends the report back; a workflow comments on the draft pull request, which wakes claude; claude checks the result, acks, notifies the user once and stops.](docs/demo/handoff-demo.gif)

One round of the [`handoff`](skills/handoff/README.md) skill. Every command and its output come from a real run on
throwaway repositories. [MP4 version](docs/demo/handoff-demo.mp4).

## Skills

| Skill | What it does |
|---|---|
| [`handoff`](skills/handoff/README.md) | One agent finishes a unit of work and names who is next in a commit trailer. The other agent is woken, does its part, and answers the same way. The user is notified when a result needs their eyes. |

## Install a skill into your repository

```bash
git clone https://github.com/mohan-zeyu/switchyard
```

```bash
python3 switchyard/install.py handoff /path/to/your/repo
```

The installer copies the skill's files, prints what it wrote, and commits nothing. Review, commit, then follow
the skill's README for the one-time setup. Python 3.8+ and git; no other dependencies.

## Design rules

- **Git is the only channel.** State lives in commits, so it survives restarts and needs no server.
- **Explicit signals.** An agent is woken by a hand-off, never by an ordinary push.
- **The user decides direction.** Agents carry work across; they do not chain rounds on their own.
- **Plain files.** A skill is a `SKILL.md` in the open Agent Skills format plus small standard-library scripts.

## Licence

MIT. See [LICENSE](LICENSE).
