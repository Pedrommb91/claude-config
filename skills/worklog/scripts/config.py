"""Local settings shared by the worklog, weeklog and start-ticket skills.

Values live in ~/.claude/worklog.config.json, which is git-ignored on purpose:
it holds organisation-specific details (ticket tracker URL, project folders, ...).
Create or edit it with `python3 ~/.claude/skills/worklog/scripts/setup.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "worklog.config.json"

# key -> (prompt shown by setup.py, default). All values are strings; empty means "off".
FIELDS: dict[str, tuple[str, str]] = {
    "ticket_url_base": (
        "Ticket URL base, the ticket ID is appended to it (e.g. https://jira.example.com/browse/). "
        "Empty = no ticket links:",
        "",
    ),
    "daily_ticket_id": (
        "Recurring weekday entry: ticket ID (e.g. PROJ-1). Empty = no recurring entry:",
        "",
    ),
    "daily_title": ("Recurring weekday entry: title (e.g. Team Daily):", ""),
    "daily_project": ("Recurring weekday entry: project name:", ""),
    "time_tool": (
        "Name of the time-tracking tool you copy entries into (used in the weekly page status):",
        "time tracker",
    ),
    "repos_roots": (
        "Folders that contain your git repos, comma-separated (used by /worklog backfill):",
        "",
    ),
    "vault_path": (
        "Obsidian vault folder that holds the Worklog/ notes (e.g. ~/Documents/Workbench):",
        "",
    ),
}


def load() -> dict[str, str]:
    """Return the saved settings merged over the defaults ({} values if the file is missing)."""
    values = {key: default for key, (_, default) in FIELDS.items()}
    try:
        saved = json.loads(CONFIG_PATH.read_text())
    except FileNotFoundError:
        return values
    values.update({k: str(v) for k, v in saved.items() if k in FIELDS})
    return values


def exists() -> bool:
    return CONFIG_PATH.is_file()


def save(values: dict[str, str]) -> None:
    CONFIG_PATH.write_text(
        json.dumps({k: values.get(k, "") for k in FIELDS}, indent=2, ensure_ascii=False) + "\n"
    )
    CONFIG_PATH.chmod(0o600)


def repos_roots(values: dict[str, str] | None = None) -> list[Path]:
    raw = (values or load())["repos_roots"]
    return [Path(p.strip()).expanduser() for p in raw.split(",") if p.strip()]
