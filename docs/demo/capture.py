#!/usr/bin/env python3
"""Run one real hand-off round on throwaway repositories and record every command and its output.

A bare remote plus two clones, "claude" and "codex", as in skills/handoff/scripts/test_handoff.py. Each command is
run exactly as written in STEPS (through bash, in that agent's clone) and its real stdout/stderr is saved to
transcript.js, which demo.html reads. Nothing in the animation's terminals is typed by hand.

  python3 docs/demo/capture.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent.parent / "skills" / "handoff" / "scripts" / "handoff.py"
BRANCH = "sweep"

# Commit dates are pinned to one value, so the date lines in `pending` output imply no durations.
DATE = "2026-11-19T09:00:00+00:00"
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C",
       "GIT_AUTHOR_DATE": DATE, "GIT_COMMITTER_DATE": DATE}
for key in ("HANDOFF_AGENT", "HANDOFF_BRANCH"):
    ENV.pop(key, None)

BRIEF = """# Brief: learning-rate sweep

Train the small model at lr 1e-4, 3e-4 and 1e-3, one run each.
Commit results.csv after every run. Report which lr is best.
Stop and ask if a run diverges.
"""
REPORT = """# Report: learning-rate sweep

Best: lr 3e-4 (lowest val_loss in results.csv).
No run diverged.
"""


def sh(cwd, command, who):
    env = {**ENV, "GIT_AUTHOR_NAME": who, "GIT_AUTHOR_EMAIL": f"{who}@example.invalid",
           "GIT_COMMITTER_NAME": who, "GIT_COMMITTER_EMAIL": f"{who}@example.invalid"}
    proc = subprocess.run(["bash", "-c", command], cwd=cwd, env=env, text=True, capture_output=True)
    if proc.returncode:
        sys.exit(f"capture: {command!r} failed in {who}:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout + proc.stderr


def main():
    log = []  # [{"id", "who", "cmd", "out"}]

    def step(key, who, command):
        out = sh(clones[who], command, who)
        log.append({"id": key, "who": who, "cmd": command, "out": out})
        return out

    def quiet(who, command):  # set-up and file writing; not shown in the animation
        return sh(clones[who], command, who).strip()

    with tempfile.TemporaryDirectory() as tmp:
        remote = os.path.join(tmp, "remote.git")
        clones = {"claude": os.path.join(tmp, "claude"), "codex": os.path.join(tmp, "codex")}
        sh(tmp, f"git init -q --bare -b {BRANCH} {remote} && git clone -q {remote} claude", "claude")
        os.makedirs(os.path.join(clones["claude"], "scripts"))
        Path(clones["claude"], "scripts", "handoff.py").write_text(TOOL.read_text())
        Path(clones["claude"], ".gitattributes").write_text(".handoff/*.log merge=union\n")
        quiet("claude", f"git checkout -q -b {BRANCH} && git add -A && git commit -q -m Start && git push -q -u origin {BRANCH}")
        sh(tmp, f"git clone -q {remote} codex", "codex")

        # Before anything is sent, codex's recurring check prints nothing.
        step("codex_idle", "codex", "python3 scripts/handoff.py pending --as codex")

        # 1. claude writes a brief and hands it to codex.
        Path(clones["claude"], "BRIEF.md").write_text(BRIEF)
        step("claude_add", "claude", "git add BRIEF.md")
        step("claude_send", "claude",
             'python3 scripts/handoff.py send --as claude --to codex --brief BRIEF.md '
             '-m "Brief: learning-rate sweep" -m "Run the three settings in BRIEF.md."')
        brief = quiet("claude", "git rev-parse HEAD")
        step("brief_msg", "claude", "git log -1 --format=%B")

        # 2. codex's next check finds it; codex works and pushes progress with no trailer.
        step("codex_pending", "codex", "python3 scripts/handoff.py pending --as codex")
        quiet("codex", f"git merge -q --ff-only origin/{BRANCH}")
        rows = ["lr,val_loss", "1e-4,2.31", "3e-4,2.12", "1e-3,2.47"]
        progress = []
        for n in (1, 2, 3):
            Path(clones["codex"], "results.csv").write_text("\n".join(rows[: n + 1]) + "\n")
            quiet("codex", "git add results.csv")
            step(f"codex_commit{n}", "codex", f'git commit -m "Record run {n} of 3"')
            step(f"codex_push{n}", "codex", "git push -q")
            progress.append(quiet("codex", "git rev-parse HEAD"))
        before_report = progress[-1]
        # A progress push wakes nobody: nothing is pending for claude, and announce finds no hand-off in it.
        step("claude_idle", "claude", "python3 scripts/handoff.py pending --as claude")
        quiet("claude", f"git fetch -q origin")
        silent = sh(clones["claude"], f"python3 scripts/handoff.py announce --to claude --before {brief} --after {before_report}", "claude")
        assert silent == "", silent

        # 3. codex reports and acks the brief.
        Path(clones["codex"], "REPORT.md").write_text(REPORT)
        step("codex_add", "codex", "git add REPORT.md")
        step("codex_send", "codex",
             f'python3 scripts/handoff.py send --as codex --to claude --ack {brief[:7]} --status done '
             f'-m "Report: learning-rate sweep" -m "Best lr 3e-4. Evidence in results.csv."')
        report = quiet("codex", "git rev-parse HEAD")

        # 4. The workflow's announce step: the real pull-request comment body for that push.
        quiet("claude", "git fetch -q origin")
        comment = sh(clones["claude"], f"python3 scripts/handoff.py announce --to claude --before {before_report} --after {report}", "claude")

        # 5. claude is woken, reads what waits, checks the evidence, acks, stops.
        step("claude_pending", "claude", "python3 scripts/handoff.py pending --as claude")
        quiet("claude", f"git merge -q --ff-only origin/{BRANCH}")
        step("claude_check", "claude", "cat results.csv")
        step("claude_ack", "claude", f'python3 scripts/handoff.py ack --as claude {report[:7]} -m "Checked against results.csv."')
        step("claude_clear", "claude", "python3 scripts/handoff.py pending --as claude")
        ack = quiet("claude", "git rev-parse HEAD")
        graph = quiet("claude", f"git log --reverse --format=%h%x09%s origin/{BRANCH}")

    data = {"branch": BRANCH, "brief": brief, "report": report, "ack": ack, "progress": progress,
            "comment": comment, "graph": [line.split("\t", 1) for line in graph.splitlines()],
            "steps": {s["id"]: s for s in log}}
    (HERE / "transcript.js").write_text("// Written by capture.py from a real run. Do not edit by hand.\n"
                                        "window.TRANSCRIPT = " + json.dumps(data, indent=1) + ";\n")
    print(f"wrote {HERE / 'transcript.js'}")


if __name__ == "__main__":
    main()
