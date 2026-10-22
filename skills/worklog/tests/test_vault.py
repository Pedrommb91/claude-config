"""Tests for vault.py. The fixture vault follows _schema.md with made-up data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import vault as v

TICKET_A = "acme-10 - Fix the pipeline"
TICKET_B = "acme-9 - Rotate keys"
TICKET_C = "side-quest"


def note(path: Path, front: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front.strip()}\n---\n{body}", encoding="utf-8")


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    wl = tmp_path / "Worklog"
    note(
        wl / "Projects" / "ACME.md",
        "type: project\nrepos:\n  - acme/infra\n  - acme/infra-modules\n"
        "ticket_prefix: ACME\nstatus: Active\ndescription: Acme things",
    )
    note(
        wl / "Projects" / "Side.md",
        "type: project\nrepos:\n  - acme/infra-modules\nstatus: Active",
    )
    note(
        wl / "Tickets" / "ACME" / f"{TICKET_A}.md",
        'type: ticket\ntitle: "Fix the pipeline"\nticket_id: ACME-10\nkey: acme-10\n'
        'project: "[[ACME]]"\nstatus: In progress\nticket_type: Bug\nrepos:\n  - acme/infra\n'
        'branch: fix/ACME-10\nlinks: []\nlast_session: 2026-10-05',
        "\n## Goal / Why\n\nBecause.\n",
    )
    note(
        wl / "Tickets" / "ACME" / f"{TICKET_B}.md",
        'type: ticket\ntitle: "Rotate keys"\nticket_id: ACME-9\nkey: acme-9\n'
        'project: "[[ACME]]"\nstatus: Done\nticket_type: Chore\nrepos: []\nlinks: []',
    )
    note(
        wl / "Tickets" / "Side" / f"{TICKET_C}.md",
        'type: ticket\ntitle: "Side quest"\nkey: side-quest\nproject: "[[Side]]"\n'
        "status: In progress\nticket_type: Research\nrepos: []\nlinks: []",
    )
    # a subpage in a ticket folder must not count as a ticket
    note(
        wl / "Tickets" / "ACME" / TICKET_A / "Notes.md",
        f'type: ticket_note\ntitle: Notes\nticket: "[[{TICKET_A}]]"',
    )
    sess = [
        ("2026-10-05", "acme-10", TICKET_A, "ACME", "Looked at the failing job"),
        ("2026-10-06", "acme-9", TICKET_B, "ACME", "Rotated the keys"),
        ("2026-10-06", "acme-10", TICKET_A, "ACME", "Fixed the cache key"),
        ("2026-10-06", "side-quest", TICKET_C, "Side", "Tried a thing"),
        ("2026-10-13", "acme-10", TICKET_A, "ACME", "Out of range"),
    ]
    for day, key, ticket, project, summary in sess:
        note(
            wl / "Sessions" / f"{day} {key}.md",
            f'type: session\ndate: {day}\nticket: "[[{ticket}]]"\nproject: "[[{project}]]"\n'
            f"summary: {json.dumps(summary)}",
        )
    note(
        wl / "Weeks" / "2026-W41.md",
        'type: week\ntitle: "2026-W41 · 5 Oct – 11 Oct"\nweek_start: 2026-10-05\nstatus: Draft',
        "\n## Mon 5 Oct\n",
    )
    return tmp_path


def run(vault: Path, capsys: pytest.CaptureFixture[str], *argv: str) -> dict:
    assert v.main(["--vault", str(vault), *argv]) == 0
    return json.loads(capsys.readouterr().out)


def test_parse_note_subset():
    fm, body = v.parse_note(
        '---\ntype: ticket\ntitle: "[X] a: b"\nrepos:\n  - o/r\n  - o/s\nlinks: []\n---\n\nbody\n'
    )
    assert fm == {"type": "ticket", "title": "[X] a: b", "repos": ["o/r", "o/s"], "links": []}
    assert body == "\nbody\n"


def test_yaml_str_quotes_what_needs_it():
    assert v.yaml_str("plain words") == "plain words"
    assert v.yaml_str("[[VDS]]") == '"[[VDS]]"'
    assert v.yaml_str("yes") == '"yes"'


def test_find_project_matches_whole_entries_case_insensitively(vault, capsys):
    out = run(vault, capsys, "find-project", "--repo", "ACME/Infra")
    assert [m["name"] for m in out["matches"]] == ["ACME"]  # not infra-modules


def test_find_project_shared_repo_returns_all(vault, capsys):
    out = run(vault, capsys, "find-project", "--repo", "acme/infra-modules")
    assert [m["name"] for m in out["matches"]] == ["ACME", "Side"]


def test_find_project_no_match(vault, capsys):
    assert run(vault, capsys, "find-project", "--repo", "x/y") == {"matches": []}


def test_find_ticket_by_id_then_key(vault, capsys):
    out = run(vault, capsys, "find-ticket", "--project", "ACME", "--id", "acme-10")
    assert out["match"]["file"] == TICKET_A
    assert out["match"]["label"] == "[ACME-10] Fix the pipeline"
    out = run(vault, capsys, "find-ticket", "--project", "ACME", "--id", "ACME-99", "--key", "acme-9")
    assert out["match"]["file"] == TICKET_B


def test_find_ticket_is_scoped_to_project_and_label_without_id(vault, capsys):
    assert run(vault, capsys, "find-ticket", "--project", "Side", "--key", "acme-10")["match"] is None
    out = run(vault, capsys, "find-ticket", "--project", "Side", "--key", "side-quest")
    assert out["match"]["label"] == "Side quest"


def test_find_ticket_duplicate_is_an_error(vault, capsys):
    dup = vault / "Worklog" / "Tickets" / "ACME" / "acme-10 - Copy.md"
    dup.write_text((vault / "Worklog" / "Tickets" / "ACME" / f"{TICKET_A}.md").read_text())
    assert v.main(["--vault", str(vault), "find-ticket", "--project", "ACME", "--key", "acme-10"]) == 1
    assert "duplicate" in capsys.readouterr().err


def test_list_tickets_filters_status(vault, capsys):
    out = run(vault, capsys, "list-tickets", "--project", "ACME", "--status", "In progress")
    assert [t["key"] for t in out["tickets"]] == ["acme-10"]


def test_sessions_range_and_order(vault, capsys):
    out = run(vault, capsys, "sessions", "--from", "2026-10-05", "--to", "2026-10-11")
    got = [(s["date"], s["label"]) for s in out["sessions"]]
    assert got == [
        ("2026-10-05", "[ACME-10] Fix the pipeline"),
        ("2026-10-06", "[ACME-9] Rotate keys"),  # numeric order: 9 before 10
        ("2026-10-06", "[ACME-10] Fix the pipeline"),
        ("2026-10-06", "Side quest"),
    ]


def test_sessions_label_follows_current_ticket_fields(vault, capsys):
    path = vault / "Worklog" / "Tickets" / "ACME" / f"{TICKET_B}.md"
    path.write_text(path.read_text().replace("ticket_id: ACME-9", "ticket_id: ACME-11"))
    out = run(vault, capsys, "sessions", "--from", "2026-10-06", "--to", "2026-10-06")
    assert "[ACME-11] Rotate keys" in [s["label"] for s in out["sessions"]]


def test_sessions_orphan_falls_back_to_file_name(vault, capsys):
    note(
        vault / "Worklog" / "Sessions" / "2026-10-07 ghost.md",
        'type: session\ndate: 2026-10-07\nticket: "[[gone]]"\nproject: "[[ACME]]"\nsummary: x',
    )
    out = run(vault, capsys, "sessions", "--from", "2026-10-07", "--to", "2026-10-07")
    assert out["sessions"][0]["ticket_found"] is False
    assert out["sessions"][0]["label"] == "2026-10-07 ghost"


def test_upsert_creates_session_matching_schema(vault, capsys):
    out = run(
        vault, capsys, "upsert-session", "--project", "ACME", "--key", "acme-9",
        "--date", "2026-10-07", "--summary", "Checked: audit log",
    )
    assert out["action"] == "created"
    text = Path(out["path"]).read_text()
    assert Path(out["path"]).name == "2026-10-07 acme-9.md"
    assert text == (
        "---\ntype: session\ndate: 2026-10-07\n"
        f'ticket: "[[{TICKET_B}]]"\nproject: "[[ACME]]"\nsummary: "Checked: audit log"\n---\n'
    )
    # ticket B had no last_session: it is added
    assert "last_session: 2026-10-07\n---\n" in (
        vault / "Worklog" / "Tickets" / "ACME" / f"{TICKET_B}.md"
    ).read_text()


def test_upsert_merges_second_log_same_day(vault, capsys):
    args = ["upsert-session", "--project", "ACME", "--key", "acme-10", "--date", "2026-10-06"]
    out = run(vault, capsys, *args, "--summary", "Added a retry")
    assert out["action"] == "merged"
    assert out["summary"] == "Fixed the cache key; added a retry"
    # same text again is a no-op, not a duplicate
    assert run(vault, capsys, *args, "--summary", "Added a retry")["action"] == "unchanged"
    assert len(list((vault / "Worklog" / "Sessions").glob("2026-10-06 acme-10*"))) == 1


def test_upsert_merge_over_limit_is_rejected(vault):
    argv = ["--vault", str(vault), "upsert-session", "--project", "ACME", "--key", "acme-10",
            "--date", "2026-10-06", "--summary", "x" * 150]
    assert v.main(argv) == 1


def test_upsert_summary_over_limit_is_rejected(vault):
    argv = ["--vault", str(vault), "upsert-session", "--project", "ACME", "--key", "acme-10",
            "--date", "2026-10-20", "--summary", "x" * 121]
    assert v.main(argv) == 1
    assert not (vault / "Worklog" / "Sessions" / "2026-10-20 acme-10.md").exists()


def test_upsert_last_session_only_moves_forward(vault, capsys):
    ticket = vault / "Worklog" / "Tickets" / "ACME" / f"{TICKET_A}.md"
    out = run(vault, capsys, "upsert-session", "--project", "ACME", "--id", "ACME-10",
              "--date", "2026-10-01", "--summary", "Backfilled day")
    assert out["last_session_updated"] is False
    assert "last_session: 2026-10-05" in ticket.read_text()
    out = run(vault, capsys, "upsert-session", "--project", "ACME", "--id", "ACME-10",
              "--date", "2026-10-09", "--summary", "Later day")
    assert out["last_session_updated"] is True
    text = ticket.read_text()
    assert "last_session: 2026-10-09" in text and text.endswith("Because.\n")


def test_upsert_unknown_ticket_is_an_error(vault, capsys):
    argv = ["--vault", str(vault), "upsert-session", "--project", "ACME", "--key", "nope",
            "--date", "2026-10-06", "--summary", "x"]
    assert v.main(argv) == 1
    assert "not found" in capsys.readouterr().err


def test_find_week_existing_and_new(vault, capsys):
    out = run(vault, capsys, "find-week", "--week", "2026-W41")
    assert out["exists"] and out["status"] == "Draft"
    assert out["title"] == "2026-W41 · 5 Oct – 11 Oct"
    out = run(vault, capsys, "find-week", "--date", "2026-10-01")
    assert out["week"] == "2026-W40" and out["week_start"] == "2026-09-28"
    assert out["title"] == "2026-W40 · 28 Sep – 4 Oct"
    assert out["exists"] is False


def test_vault_from_config(tmp_path, monkeypatch, capsys):
    (tmp_path / "Worklog" / "Projects").mkdir(parents=True)
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"vault_path": str(tmp_path)}))
    monkeypatch.setattr(v, "CONFIG_PATH", cfg)
    assert v.main(["find-project", "--repo", "a/b"]) == 0
    monkeypatch.setattr(v, "CONFIG_PATH", tmp_path / "missing.json")
    assert v.main(["find-project", "--repo", "a/b"]) == 1
