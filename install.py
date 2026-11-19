#!/usr/bin/env python3
"""Copy one skill from this repository into a target repository.

  python3 install.py handoff /path/to/your/repo
  python3 install.py handoff /path/to/your/repo --set WAKE_AGENT=researcher --set PEER_AGENT=gpu

Each skill folder has an install.json: the files to copy or append, and variables written as __NAME__ in those
files. Existing files that differ are left alone unless --force is given. Nothing is committed for you.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill", help="folder name under skills/")
    parser.add_argument("target", help="path of the repository to install into")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a variable")
    parser.add_argument("--force", action="store_true", help="overwrite existing files that differ")
    args = parser.parse_args()

    source, target = ROOT / "skills" / args.skill, Path(args.target).resolve()
    if not (source / "install.json").is_file():
        sys.exit(f"install: no such skill: {args.skill}")
    if not (target / ".git").exists():
        sys.exit(f"install: {target} is not the root of a git repository")
    manifest = json.loads((source / "install.json").read_text())
    variables = dict(manifest.get("variables", {}))
    for item in args.set:
        name, _, value = item.partition("=")
        if name not in variables or not value:
            sys.exit(f"install: --set takes one of {', '.join(variables)} as NAME=VALUE")
        variables[name] = value

    skipped = False
    for entry in manifest["files"]:
        text = (source / entry["from"]).read_text()
        for name, value in variables.items():
            text = text.replace(f"__{name}__", value)
        destination = target / entry["to"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        current = destination.read_text() if destination.exists() else None
        if entry.get("append"):
            if current is not None and entry["marker"] in current:
                print(f"  kept      {entry['to']} (already has this section)")
                continue
            joined = (current or "")
            joined += "" if not joined or joined.endswith("\n") else "\n"
            destination.write_text(joined + text)
            print(f"  appended  {entry['to']}")
        elif current is None or args.force:
            destination.write_text(text)
            print(f"  wrote     {entry['to']}")
        elif current == text:
            print(f"  kept      {entry['to']} (identical)")
        else:
            skipped = True
            print(f"  SKIPPED   {entry['to']} (exists and differs; pass --force to overwrite)")

    print("\nVariables: " + ", ".join(f"{k}={v}" for k, v in variables.items()))
    print(f"Next: review the changes in {target}, commit them, and follow skills/{args.skill}/README.md, 'Setup'.")
    sys.exit(1 if skipped else 0)


if __name__ == "__main__":
    main()
