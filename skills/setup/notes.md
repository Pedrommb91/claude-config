# Notes root

The **notes root** is the folder named on the `**Notes root:**` line of the repo's `## Agent skills` block. For an Obsidian user it's a project folder in the vault (e.g. `~/Documents/Workbench/<Project>/`); for anyone else it's an in-repo folder (e.g. `docs/`). Skills never hardcode a path: they read the block.

## Finding the block

Look for `## Agent skills` in `AGENTS.md`, then `AGENTS.local.md` (both may be imported through `CLAUDE.md` / `CLAUDE.local.md`, so it may already be in context). If neither has it, stop and tell the user to run `/setup`.

## Layout

```
<notes root>/
├── <Project>.md          hub note (vault only), frontmatter type: dev_project
├── Plans/<slug>.md       /issues plan notes: spec link, ordered issue index, checkpoints, risks
├── Decisions/NNNN-<slug>.md   ADRs
├── Glossary.md           domain vocabulary
├── Out of scope/<concept>.md  rejected enhancements (/triage)
├── Brainstorms/<topic>.md     confirmed intent and design outcomes (/brainstorm)
├── Issues/<slug>/        local tracker only (see trackers/local.md)
└── Memory/               cross-session notes; not managed by these skills
```

Create a folder only when writing its first file. Monorepo: keep one project folder, and put context-scoped glossary and decisions under `<Context>/Glossary.md` and `<Context>/Decisions/`; the root `Glossary.md` then lists the contexts.

Vault notes are read outside the repo and outside GitHub, so link issues by full URL (`https://github.com/owner/repo/issues/42`), not bare `#42`. Obsidian wikilinks (`[[Glossary]]`) are fine between notes in the same project folder.

## Before exploring, read these

- `<notes root>/Glossary.md` (and the per-context glossaries relevant to the topic)
- `<notes root>/Decisions/`: the ADRs that touch the area you're about to work in

If they don't exist, **proceed silently**. Don't flag their absence or suggest creating them upfront; `/brainstorm` writes them lazily when terms or decisions actually get resolved.

## Use the glossary's vocabulary

When your output names a domain concept (issue title, spec, hypothesis, test name), use the term as the glossary defines it. Don't drift to synonyms it explicitly avoids. A concept missing from the glossary is a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/brainstorm` to record).

## Flag ADR conflicts

If your output contradicts an existing decision, surface it rather than silently overriding:

> _Contradicts Decisions/0007 (event-sourced orders), but worth reopening because…_

## ADR format

```markdown
# NNNN: <Decision title>

**Status:** accepted | superseded by NNNN
**Date:** YYYY-MM-DD

## Context
What forced the decision.

## Decision
What we chose.

## Consequences
What gets easier, what gets harder, what we gave up.
```

Number sequentially from `0001`. Only record decisions that are hard to reverse, surprising to a newcomer, or the outcome of a real trade-off.
