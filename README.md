# claude-config

Versioned Claude Code configuration. The repo lives directly in `~/.claude`
and a whitelist `.gitignore` tracks only the stable parts:

| Path | What |
|---|---|
| `CLAUDE.md` | Global instructions |
| `settings.json` | Permissions, model, attribution |
| `agents/` | Custom subagents |
| `skills/` | Custom skills |

Everything else (sessions, `worklog.config.json`, projects/memory, caches, telemetry, plugins,
credentials, `skills/synced`, `skills/.trash`) is ignored.

## Commit identity

This repo is public. `.githooks/pre-push` rejects pushes containing commits whose author or committer
email is not a GitHub noreply address. Enable it once per clone:

```sh
git -C ~/.claude config core.hooksPath .githooks
```

## Credits

The planning skills are adapted from
[mattpocock/skills](https://github.com/mattpocock/skills) by Matt Pocock, reworked to keep
plans, decisions and glossary in an Obsidian vault (or any notes folder) instead of the repo:

- `triage` (from `triage`)
- `setup` (from `setup-matt-pocock-skills`)
- `spec` (from `to-spec`)
- `issues` (from `to-tickets`, merged with `planning-and-task-breakdown`)
- `brainstorm` (from `grilling`, merged with `interview-me`)

`planning-and-task-breakdown` and `interview-me` come from
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) by Addy Osmani.

All credit for the originals goes to their authors; check the upstream repos for
the current versions and license terms.

## Worklog setup (per machine)

The `worklog`, `weeklog` and `start-ticket` skills need a few organisation-specific values
(ticket URL base, recurring daily entry, time-tracking tool name, folders with your repos).
They are **not** in this repo: they live in `~/.claude/worklog.config.json`, which is
git-ignored. The skills ask for them on first use; to create or edit the file yourself:

```sh
python3 ~/.claude/skills/worklog/scripts/setup.py          # prompts for each value
python3 ~/.claude/skills/worklog/scripts/setup.py --get    # show current values
python3 ~/.claude/skills/worklog/scripts/setup.py --set time_tool="My tool"
```

## Restore on a new machine

```sh
# 1. Install Claude Code and run it once so ~/.claude exists, then quit.
# 2. Clone into the existing directory:
cd ~/.claude
git init -b main
git remote add origin git@github.com:Pedrommb91/claude-config.git
git fetch origin
git checkout -f main   # -f overwrites the freshly generated defaults
```

Then run the worklog setup above.

## Notes

- Put machine-specific or sensitive settings in `settings.local.json` (ignored).
- Plugins and MCP connectors are not versioned; reinstall/authorize them per machine.
- Before committing, check `git status` — the whitelist should keep it short.
