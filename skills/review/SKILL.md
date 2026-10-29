---
name: review
description: "Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's coding standards and the baseline?) and Spec (does it implement what the originating issue/spec asked for?). Runs each axis in a parallel `reviewer` sub-agent and reports them side by side. Use when the user runs /review, wants to review a branch, a PR, or work-in-progress changes, or asks to \"review since X\"."
---

# Review

Two-axis review of the diff between `HEAD` and a fixed point:

- **Standards**: does the code conform to the repo's documented standards and the [baseline](baseline.md)?
- **Spec**: does the code faithfully implement the originating issue or spec?

Each axis runs in its own `reviewer` sub-agent with a fresh context, so neither pollutes the other. You orchestrate from the main session; sub-agents can't spawn sub-agents, so this skill never runs inside one.

## Process

### 1. Pin the fixed point

Use what the user gave (SHA, branch, tag, `HEAD~5`, a PR number). Default to the repo's default branch. For a PR number, use `gh pr view <n> --json baseRefName,headRefName` and review `origin/<base>...<head>`.

Confirm `git rev-parse <fixed-point>` resolves and `git diff --stat <fixed-point>...HEAD` is non-empty. A bad ref or empty diff fails here, not inside two sub-agents.

Record:
- Diff command: `git diff <fixed-point>...HEAD` (three-dot, against the merge-base).
- Commit list: `git log <fixed-point>..HEAD --oneline`.

### 2. Find the spec

Read the repo's `## Agent skills` block for the tracker and notes root (see the `setup` skill's [notes.md](../setup/notes.md)). Look, in order:

1. Issue refs in commit messages or the branch name (`#123`, `Closes #45`, `PROJ-123`). GitHub: `gh issue view <n> --json title,body,comments`. If that issue is a child of a spec, fetch the parent `Spec: <title>` issue too (label `spec:<slug>`).
2. A path or ref the user passed.
3. Local tracker: `<notes root>/Issues/<slug>/spec.md` matching the branch or feature; also `<notes root>/Brainstorms/` and `Plans/`.
4. Otherwise ask the user. If there is none, skip the Spec axis and say so in the report.

Jira isn't connected: for a `PROJ-123` ref with no spec found, ask the user to paste the ticket description.

### 3. Find the standards

List every file that documents how code is written here: `CODING_STANDARDS.md`, `CONTRIBUTING.md`, `docs/` style guides. If the repo has no `CODING_STANDARDS.md` and its standards live in `AGENTS.md`/`CLAUDE.md`, pass those files and note it in the report as a `/retro` candidate.

Note the guardrails that already run (`.pre-commit-config.yaml`, linter configs, `.github/workflows/`), so the reviewer skips what tooling enforces.

### 4. Spawn both reviewers in parallel

Issue both `reviewer` calls in one message, in the foreground. Each prompt contains:

- The axis: `standards` or `spec`.
- The diff command and commit list.
- **Standards**: the standards files from step 3, the guardrails that already run, and the baseline path `~/.claude/skills/review/baseline.md`.
- **Spec**: the spec contents (paste them; the reviewer has no tracker access) or its path.

### 5. Aggregate

Present the reports under `## Standards` and `## Spec`, verbatim or lightly cleaned. Keep the axes separate: no merging, no reranking across them.

End with one line: each axis's verdict, its Critical/Required counts, and the worst issue within each axis.

Then offer to fix the Critical and Required findings. Leave Optional and Nit to the user. For correctness bugs beyond the spec (races, off-by-ones), suggest the built-in `/code-review`.

## Why two axes

Code that follows every standard can implement the wrong thing (**Standards pass, Spec fail**), and code that does exactly what the issue asked can break the project's conventions (**Spec pass, Standards fail**). Separate reports stop one axis from masking the other.
