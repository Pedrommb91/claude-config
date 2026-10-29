---
name: setup
description: "Configure a repo for the planning skills (/brainstorm, /spec, /issues, /triage): pick the issue tracker (GitHub, GitLab or local), the notes root (an Obsidian vault project folder or an in-repo folder), and the triage labels, then write the `## Agent skills` block to AGENTS.md. Run once per repo before first use of the other skills, or again to change tracker or notes root."
disable-model-invocation: true
---

# Setup

Write the per-repo configuration the planning skills read:

- **Tracker**: where issues live (GitHub, GitLab, or local markdown files under the notes root)
- **Notes root**: where plans, decisions, glossary, out-of-scope records and brainstorms live (an Obsidian vault project folder, or an in-repo folder for people without a vault)
- **Labels**: the strings used for the triage roles and spec grouping

All of it lands in one `## Agent skills` block. No `docs/agents/` files: the how-to for each tracker lives in this skill's folder and is shared by every repo.

This is a prompt-driven skill, not a script. Explore, present what you found, confirm, then write.

## Reference docs

- [trackers/github.md](trackers/github.md), [trackers/gitlab.md](trackers/gitlab.md), [trackers/local.md](trackers/local.md): tracker operations
- [notes.md](notes.md): notes-root layout and the rules every skill follows when reading it
- [labels.md](labels.md): the label vocabulary

## Process

### 1. Explore

Read whatever exists; don't assume:

- `git remote -v`: GitHub, GitLab (`gitlab.com` or self-hosted), or no remote?
- `AGENTS.md`, `AGENTS.local.md`, `CLAUDE.md`, `CLAUDE.local.md` at the repo root. Does any already hold an `## Agent skills` block? Does `CLAUDE.md` import `@AGENTS.md`?
- Leftovers from the old setup: `docs/agents/`, `GLOSSARY.md`, `GLOSSARY-MAP.md`, `docs/adr/`, `.out-of-scope/`, `.scratch/`, `tasks/plan.md`. Note them; step 5 offers to migrate them.
- The default vault `~/Documents/Workbench`: does it exist? Is there already a project folder whose hub note has `repo:` matching this remote (grep the `repo:` frontmatter of `*/<name>.md` hub notes)?
- Monorepo signals (`pnpm-workspace.yaml`, `go.work`, a `workspaces` field, populated `packages/*` or `services/*`). Absent in almost every repo.

### 2. Ask, one section at a time

Summarise what's present and missing, then take the sections in order. Lead each with the recommended answer so the user can accept it in a word. Skip a section when exploration already settled it (an existing block being updated keeps its answers unless the user wants to change them).

**A. Tracker.** Recommend from the remote: GitHub remote → GitHub, GitLab remote → GitLab, no remote → local.

- **GitHub**: GitHub Issues via `gh`
- **GitLab**: GitLab Issues via `glab`
- **Local**: one markdown file per issue under `<notes root>/Issues/`
- **Other** (Jira, Linear, …): ask for a one-paragraph description of the workflow and record it as prose in the block

**B. Notes root.**

- **Obsidian vault** (recommended when `~/Documents/Workbench` exists): `<vault>/<Project>/`. Confirm the vault path (default `~/Documents/Workbench`) and the project folder name (default: an existing folder matched in step 1, else the repo name in PascalCase).
- **In-repo**: `docs/` (or a folder the user names) for people without a vault.

Monorepo: one project folder, with per-context subfolders for `Glossary.md` and `Decisions/` (see [notes.md](notes.md)). Only raise this when step 1 found monorepo signals.

**C. Personal or shared repo.** Decides where the block lives:

- **Personal** (recommended when the remote owner is the user's own account): block goes in `AGENTS.md`, committed.
- **Shared** (client, team or company repo): block goes in `AGENTS.local.md`, which is added to `.git/info/exclude` and imported from `CLAUDE.local.md` (`@AGENTS.local.md`). Nothing personal is committed.

**D. Labels.** Ask exactly one question: "Keep the default labels?" (recommended: **yes**, see [labels.md](labels.md)). Only on **no**, usually because the tracker already uses other names, collect the overrides so skills apply existing labels instead of creating duplicates. Skip for the local tracker.

The "PRs as a request surface" flag defaults to **no**. Write it, don't raise it.

### 3. Confirm

Show the user, before writing anything:

- The `## Agent skills` block and the file it goes in
- Any `CLAUDE.md` / `CLAUDE.local.md` import line being added, and the `.git/info/exclude` entry for a shared repo
- The hub note to create, if the notes root is a new vault folder
- The labels that will be created on the tracker

Let them edit.

### 4. Write

**The block** (update in place if one exists; never append a duplicate, never touch surrounding sections):

```markdown
## Agent skills

Read by /brainstorm, /spec, /issues and /triage.

- **Tracker:** GitHub (`owner/repo`)
- **Notes root:** `~/Documents/Workbench/<Project>` (Obsidian vault `~/Documents/Workbench`)
- **Labels:** defaults
- **PRs as a request surface:** no
```

Variants: `**Tracker:** GitLab (`group/project`)`, `**Tracker:** local (`<notes root>/Issues/`)`, `**Tracker:** other: <description>`; `**Notes root:** `docs/` (in-repo)`; `**Labels:** defaults, except `needs-triage` → `bug:triage``.

**Files:**

- Personal: write the block into `AGENTS.md` (create it if missing). If `CLAUDE.md` exists and doesn't already import it, add `@AGENTS.md` near the top.
- Shared: write the block into `AGENTS.local.md`, append `AGENTS.local.md` to `.git/info/exclude` (and `CLAUDE.local.md` if that is new and not already ignored), and make sure `CLAUDE.local.md` contains `@AGENTS.local.md`.

**Notes root:**

- Vault: if the project folder doesn't exist, create it with a hub note `<Project>/<Project>.md`:

  ```markdown
  ---
  type: dev_project
  repo: <owner/repo or "local">
  local_path: <repo path, with ~ for $HOME>
  status: Active
  description: <one line>
  ---

  # <Project>

  Dev notes for <repo link>. Issues live in <tracker>; this folder holds plans, decisions, glossary and other notes that don't belong in the repo.
  ```

  Don't create the subfolders: each skill creates its folder the first time it writes there.
- In-repo: create nothing yet.

**Labels** (GitHub / GitLab only): create each label from [labels.md](labels.md) the tracker lacks (`gh label create` / `glab label create`), using the colours listed there. Don't touch existing labels. Per-spec `spec:<slug>` labels are created later by `/spec`.

### 5. Migrate leftovers (only if step 1 found any)

Offer, once, to move old-convention files into the notes root: `GLOSSARY.md` → `Glossary.md`, `docs/adr/*` → `Decisions/`, `.out-of-scope/*` → `Out of scope/`, `tasks/plan.md` → `Plans/`, and to remove `docs/agents/` plus the old `## Agent skills` block contents. Only on an explicit yes; deleting repo files is the user's commit to make, so leave the deletions unstaged.

### 6. Done

Tell the user which skills now read the block, and that they can edit the block directly later. Re-running `/setup` is only needed to switch tracker or notes root.
