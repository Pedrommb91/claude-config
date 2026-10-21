---
name: agent-map
description: Open the live Agent Map in the browser, a real-time tree of every live Claude Code session across all projects (main chat with its /goal, subagents, background tasks). Use when the user runs /agent-map or asks to see, open, stop or check the agent map / running agents dashboard.
disable-model-invocation: true
---

Run the bundled launcher and report its one-line result. Do nothing else.

- `/agent-map` or `/agent-map start`: `bash ~/.claude/skills/agent-map/agent-map.sh start` (starts the server if needed, opens the browser).
- `/agent-map stop`: `bash ~/.claude/skills/agent-map/agent-map.sh stop`.
- `/agent-map status`: `bash ~/.claude/skills/agent-map/agent-map.sh status`.

The server is project-independent: it reads all of `~/.claude/projects` and `~/.claude/sessions`, read-only, bound to 127.0.0.1 (port 8765, override with `AGENT_MAP_PORT`). On `FAILED`, show the log tail it prints and stop.
