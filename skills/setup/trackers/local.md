# Tracker: local markdown

Issues and specs live as markdown files under `<notes root>/Issues/` (the notes root comes from the `## Agent skills` block, so for a vault user they live in the vault, for anyone else in the repo). No labels: roles are lines in the file.

## Conventions

- One spec per directory: `<notes root>/Issues/<slug>/`
- The spec is `<notes root>/Issues/<slug>/spec.md`, with `Type: spec` and `Category: enhancement` near the top (no `Status:` role: it's a container).
- Child issues are one file each: `<notes root>/Issues/<slug>/<NN>-<issue-slug>.md`, numbered from `01` in dependency order. Never a single combined file.
- Standalone issues (not part of a spec) go in `<notes root>/Issues/_inbox/<NN>-<issue-slug>.md`.
- Near the top of each issue: `Category:` (`bug` / `enhancement`), `Status:` (a triage role from labels.md), and `Blocked by:` (`NN, NN` or `None`).
- Comments and conversation history append under a `## Comments` heading at the bottom.
- Closing: set `Status: done` (implemented) or `Status: wontfix`, with a closing note under `## Comments`.

## Specs and their issues

- **Child of the spec**: being in the spec's directory is the link.
- **Blocking edge**: the `Blocked by:` line. An issue is unblocked when every file it lists is `done`.
- **Frontier**: files in `Issues/<slug>/` with `Status: ready-for-agent` whose blockers are all `done`; lowest number first.

## Skill verbs

- "Publish to the tracker" → write the file (creating the directory if needed).
- "Fetch the issue" → read the file at the referenced path; the user normally passes the path or `<slug>/<NN>`.
