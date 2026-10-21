#!/usr/bin/env python3
"""Ask for the ticket details in native macOS dialogs and print them as JSON.

Usage: ticket_form.py [--id PROJ-123]

Exit codes: 0 = submitted (JSON on stdout), 1 = cancelled, 2 = dialogs unavailable.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Shared local settings (ticket URL base, ...); see worklog/scripts/config.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "worklog" / "scripts"))
import config  # noqa: E402

TICKET_URL_BASE = config.load()["ticket_url_base"]
TYPES = ["Feature", "Bug", "Chore", "Research"]
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")


class Cancelled(Exception):
    pass


def osa(script: str, *args: str) -> str:
    """Run an AppleScript `on run argv` handler; values are passed as argv, never interpolated."""
    proc = subprocess.run(
        ["osascript", "-e", script, *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        if "-128" in proc.stderr:  # user pressed Cancel
            raise Cancelled
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.rstrip("\n")


def text_dialog(prompt: str, default: str = "", multiline: bool = False) -> str:
    # A default answer with newlines makes macOS render a taller text field.
    if multiline and not default:
        default = "\n" * 8
    script = """
on run argv
    set r to display dialog (item 1 of argv) default answer (item 2 of argv) ¬
        with title "Start ticket" buttons {"Cancel", "Next"} default button "Next"
    return text returned of r
end run
"""
    return osa(script, prompt, default).strip()


def choose_type() -> str:
    script = """
on run argv
    set r to choose from list argv with title "Start ticket" ¬
        with prompt "Ticket type:" default items {item 1 of argv}
    if r is false then error number -128
    return item 1 of r
end run
"""
    return osa(script, *TYPES)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", default="", help="prefill the ticket ID")
    args = parser.parse_args()

    if sys.platform != "darwin" or not shutil.which("osascript"):
        print("dialogs unavailable: not macOS", file=sys.stderr)
        return 2

    try:
        ticket_id = args.id
        while True:
            ticket_id = text_dialog("Ticket ID (e.g. PROJ-123):", ticket_id).upper()
            if ID_RE.match(ticket_id):
                break
        title = ""
        while not title:
            title = text_dialog(f"{ticket_id} — title (exactly as in Jira):")
        description = text_dialog(
            f"{ticket_id} — description (paste it all, incl. acceptance criteria):",
            multiline=True,
        )
        ticket_type = choose_type()
        extra = text_dialog(
            "Optional: related links or context Jira doesn't have (leave empty to skip):",
            multiline=True,
        )
    except Cancelled:
        print("cancelled", file=sys.stderr)
        return 1
    except RuntimeError as err:
        print(f"dialogs unavailable: {err}", file=sys.stderr)
        return 2

    json.dump(
        {
            "id": ticket_id,
            "title": title,
            "description": description,
            "type": ticket_type,
            "extra": extra,
            "link": TICKET_URL_BASE + ticket_id if TICKET_URL_BASE else "",
        },
        sys.stdout,
        indent=2,
        ensure_ascii=False,
    )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
