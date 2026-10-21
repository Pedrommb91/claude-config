#!/usr/bin/env python3
"""Create or update the local worklog config (~/.claude/worklog.config.json).

Usage:
  setup.py                  ask for each value (macOS dialogs, or the terminal elsewhere)
  setup.py --get            print the saved config as JSON; exit 3 if none exists yet
  setup.py --set key=value  set values without prompting (repeatable)

Exit codes: 0 = ok, 1 = cancelled, 3 = no config yet (--get only).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

import config


class Cancelled(Exception):
    pass


def ask_dialog(prompt: str, default: str) -> str:
    script = """
on run argv
    set r to display dialog (item 1 of argv) default answer (item 2 of argv) ¬
        with title "Worklog setup" buttons {"Cancel", "Next"} default button "Next"
    return text returned of r
end run
"""
    proc = subprocess.run(["osascript", "-e", script, prompt, default], capture_output=True, text=True)
    if proc.returncode != 0:
        if "-128" in proc.stderr:
            raise Cancelled
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.rstrip("\n").strip()


def ask_terminal(prompt: str, default: str) -> str:
    try:
        answer = input(f"{prompt} [{default}] " if default else f"{prompt} ")
    except (EOFError, KeyboardInterrupt):
        raise Cancelled
    return answer.strip() or default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--get", action="store_true")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()

    if args.get:
        if not config.exists():
            print("no config yet: run setup.py", file=sys.stderr)
            return 3
        json.dump(config.load(), sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    values = config.load()

    if args.set:
        for item in args.set:
            key, sep, value = item.partition("=")
            if not sep or key not in config.FIELDS:
                parser.error(f"unknown or malformed setting {item!r}; keys: {', '.join(config.FIELDS)}")
            values[key] = value.strip()
        config.save(values)
        print(f"saved {config.CONFIG_PATH}")
        return 0

    use_dialogs = sys.platform == "darwin" and shutil.which("osascript")
    ask = ask_dialog if use_dialogs else ask_terminal
    try:
        for key, (prompt, _) in config.FIELDS.items():
            values[key] = ask(prompt, values[key])
    except Cancelled:
        print("cancelled, nothing saved", file=sys.stderr)
        return 1
    config.save(values)
    print(f"saved {config.CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
