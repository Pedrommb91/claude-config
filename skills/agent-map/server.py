#!/usr/bin/env python3
"""Live agent map: serves index.html and /api/agents built from Claude Code session transcripts.

Shows only live sessions (claude process still running) as trees:
main chat -> subagents (linked by the Agent tool call that spawned them) -> background tasks.

Usage: python3 server.py [--port 8765] [--projects DIR]
Read-only; binds to 127.0.0.1 only.
"""
import argparse
import json
import os
import re
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
ACTIVE_SECS = 20  # transcript touched this recently and not finished => running
BUSY_MAX_SECS = 1800  # unfinished agent in a busy session counts as running (it may sit in a long tool call)
NOTIFY_RE = re.compile(r"<tool-use-id>(toolu_\w+)</tool-use-id>.*?<status>(\w+)</status>", re.S)


def live_sessions() -> dict[str, dict]:
    """sessionId -> {status, name} for sessions whose claude process is still alive."""
    out = {}
    for f in (Path.home() / ".claude" / "sessions").glob("*.json"):
        try:
            d = json.loads(f.read_text())
            os.kill(int(d["pid"]), 0)
            out[d["sessionId"]] = {"status": d.get("status", "?"), "name": d.get("name", "")}
        except (ValueError, KeyError, OSError):
            continue  # unreadable file or dead process
    return out


def ts(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def describe_tool(inp: dict, name: str) -> str:
    hint = inp.get("description") or inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
    return f"{name} {str(hint)[:120]}".strip()


_scan_cache: dict[Path, tuple] = {}


def scan(path: Path) -> dict:
    """Parse one transcript (main or subagent), cached by mtime/size."""
    st = path.stat()
    hit = _scan_cache.get(path)
    if hit and hit[0] == (st.st_mtime, st.st_size):
        return hit[1]
    r = {
        "first": 0.0, "last": 0.0, "model": "", "tokens": 0, "lastTool": "", "lastText": "",
        "finished": False, "toolCalls": 0, "prompt": "",
        "spawned": {},     # Agent tool_use id -> description (subagents launched from here)
        "bg": [],          # background Bash launched from here: {id, label}
        "notified": {},    # tool_use id -> status, from task notifications delivered here
        "goal": None, "branch": "", "prs": {},
    }
    for line in path.read_bytes().splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        t = ts(rec.get("timestamp", ""))
        if t:
            r["first"] = r["first"] or t
            r["last"] = t
        r["branch"] = rec.get("gitBranch", r["branch"])
        if b"task-notification" in line:
            for tid, status in NOTIFY_RE.findall(line.decode("utf-8", "replace")):
                r["notified"][tid] = status
        att = rec.get("attachment") or {}
        if att.get("type") == "goal_status":
            r["goal"] = {"condition": att.get("condition", ""), "met": bool(att.get("met"))}
        if rec.get("type") == "pr-link":
            r["prs"][rec["prNumber"]] = rec.get("prUrl", "")
        msg = rec.get("message") or {}
        if rec.get("type") == "user":
            if not r["prompt"] and rec.get("isSidechain"):
                r["prompt"] = text_of(msg.get("content"))[:600]
            r["finished"] = False
        elif rec.get("type") == "assistant":
            r["model"] = msg.get("model", r["model"])
            u = msg.get("usage") or {}
            r["tokens"] = sum(u.get(k, 0) or 0 for k in
                              ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
            blocks = msg.get("content") if isinstance(msg.get("content"), list) else []
            has_tool = False
            for b in blocks:
                if b.get("type") == "tool_use":
                    has_tool = True
                    r["toolCalls"] += 1
                    inp = b.get("input") or {}
                    r["lastTool"] = describe_tool(inp, b.get("name", "?"))
                    if b.get("name") in ("Agent", "Task"):
                        r["spawned"][b["id"]] = inp.get("description", "")
                    if inp.get("run_in_background"):
                        # one-line command without the PATH boilerplate the agents prepend
                        cmd = re.sub(r"^export PATH=\S+\s*", "", " ".join(str(inp.get("command", "")).split()))
                        r["bg"].append({"id": b["id"], "label": inp.get("description") or cmd[:200]})
                elif b.get("type") == "text" and b.get("text", "").strip():
                    r["lastText"] = b["text"].strip()[:300]
            r["finished"] = msg.get("stop_reason") == "end_turn" and not has_tool
    r["prs"] = [{"number": n, "url": u} for n, u in r["prs"].items()]
    _scan_cache[path] = ((st.st_mtime, st.st_size), r)
    return r


def agent_status(r: dict, mtime: float, now: float, session_status: str) -> str:
    if r["finished"]:
        return "done"
    age = now - mtime
    if age <= ACTIVE_SECS or (session_status == "busy" and age <= BUSY_MAX_SECS):
        return "running"
    return "idle"  # never reported end_turn: stopped, or waiting with the session idle


def build(projects: Path) -> dict:
    now = time.time()
    sessions = []
    for sid, sess in live_sessions().items():
        main = next(projects.glob(f"*/{sid}.jsonl"), None)
        if main is None:
            continue  # session started but nothing written yet
        m = scan(main)
        sub = main.with_suffix("") / "subagents"
        files = sorted(sub.glob("agent-*.jsonl")) if sub.exists() else []

        # every transcript in the session: "main" plus one per subagent
        scans = {"main": m}
        agents = []
        for f in files:
            aid = f.stem.removeprefix("agent-")
            meta = {}
            try:
                meta = json.loads(f.with_suffix(".meta.json").read_text())
            except (OSError, ValueError):
                pass
            r = scan(f)
            scans[aid] = r
            agents.append({
                "id": aid,
                "type": meta.get("agentType", "?"),
                "description": meta.get("description", ""),
                "toolUseId": meta.get("toolUseId", ""),
                "background": meta.get("requestShape") == "background",
                "status": agent_status(r, f.stat().st_mtime, now, sess["status"]),
                "model": r["model"], "tokens": r["tokens"], "toolCalls": r["toolCalls"],
                "lastTool": r["lastTool"], "lastText": r["lastText"], "prompt": r["prompt"],
                "started": r["first"], "updated": r["last"] or f.stat().st_mtime,
            })

        # parent = whichever transcript issued the Agent call with our toolUseId
        spawner = {tid: owner for owner, r in scans.items() for tid in r["spawned"]}
        notified = {tid: st for r in scans.values() for tid, st in r["notified"].items()}
        for a in agents:
            a["parent"] = spawner.get(a["toolUseId"], "main")
        tasks = []
        for owner, r in scans.items():
            for t in r["bg"]:
                status = notified.get(t["id"], "running" if sess["status"] == "busy" else "unknown")
                tasks.append({"id": t["id"], "owner": owner, "label": t["label"], "status": status})

        sessions.append({
            "id": sid,
            "project": main.parent.name.replace("-Users-pedrobarreiro-", "~/").replace("-", "/"),
            "name": sess["name"],
            "status": sess["status"],
            "goal": m["goal"], "branch": m["branch"], "prs": m["prs"],
            "model": m["model"], "tokens": m["tokens"], "lastTool": m["lastTool"],
            "started": m["first"], "updated": m["last"],
            "agents": sorted(agents, key=lambda a: a["started"]),
            "tasks": tasks,
        })
    sessions.sort(key=lambda s: (s["status"] != "busy", -s["updated"]))
    return {"now": now, "sessions": sessions}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--projects", type=Path, default=Path.home() / ".claude" / "projects")
    args = ap.parse_args()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/agents"):
                body, ctype = json.dumps(build(args.projects)).encode(), "application/json"
            elif self.path in ("/", "/index.html"):
                body, ctype = (HERE / "index.html").read_bytes(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    print(f"agent map: http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), H).serve_forever()


if __name__ == "__main__":
    main()
