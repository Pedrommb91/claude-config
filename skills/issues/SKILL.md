---
name: issues
description: "Break a spec (or a plan, or the current conversation) into small, verifiable tracer-bullet issues with acceptance criteria, verification steps, size and blocking edges, publish them to the configured tracker as children of the spec issue, and write a plan note (checkpoints, risks, open questions) to the notes root. Use after /spec, or when work is too big to start in one go."
disable-model-invocation: true
---

# Issues

Break a spec into **issues**: tracer-bullet vertical slices, each small enough for one focused session, each with acceptance criteria, a verification step, a size, and the issues that **block** it. Then record what doesn't fit in issues (checkpoints, risks, open questions) in a plan note.

Read the repo's `## Agent skills` block for the tracker, notes root and labels (see the `setup` skill's [notes.md](../setup/notes.md)). If there's no block, tell the user to run `/setup`. Tracker operations are in `../setup/trackers/<github|gitlab|local>.md`; labels in [labels.md](../setup/labels.md).

**When NOT to use:** a single-file change with obvious scope, or a spec that already lists well-defined tasks.

## Process

### 1. Gather context

Work from the conversation. If the user passes a reference (a spec issue number or URL, a local spec path), fetch it with its full body and comments, and take the slug from its `spec:<slug>` label (or its directory, locally). If there's no spec, ask whether to run `/spec` first or work straight from the conversation (then there's no parent, and the user picks a slug for the plan note and label).

**Never overwrite an incomplete plan.** Check whether `<notes root>/Plans/<slug>.md` exists, or the tracker already has open issues labelled `spec:<slug>`:

- Same work being replanned (the user asked to revise or extend it) → update in place: edit existing issues, add new ones, close only what the user agrees is obsolete.
- Different work under the same slug → **stop and ask.** Those open issues may be mid-build in another session. Never bulk-close, delete or relabel another plan's open issues to make room.

### 2. Explore the codebase (read-only)

If you haven't already: read the notes root's `Glossary.md` and the `Decisions/` in the area, identify existing patterns and conventions, map dependencies between components, and note risks and unknowns. Issue titles and bodies use the glossary's vocabulary and respect the decisions. Find the repo's focused-test and build commands; every issue's Verification uses them.

Look for prefactoring that makes the work easier. "Make the change easy, then make the easy change."

**Write no code while planning.** The output is issues and a plan note, not implementation.

### 3. Draft vertical slices

Map the dependency graph (what must exist before what), then cut **tracer bullets** through it.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own and leaves the system working
- Each slice fits one focused session in a fresh context window
- Prefactoring goes first; then the **riskiest** slices, so the plan fails fast

</vertical-slice-rules>

Bad (horizontal): "Build the schema" → "Build all endpoints" → "Build all UI" → "Connect everything".
Good (vertical): "User can create an account" → "User can log in" → "User can create a task" → "User can view tasks".

Give each issue its **blocking edges**: the other issues that must complete before it can start. An issue with no blockers can start immediately. Block only on issues that genuinely gate it; spurious edges kill parallelism.

**Size** each issue:

| Size | Scope | Example |
| --- | --- | --- |
| XS | Single function or config change | Add a validation rule |
| S | One component or endpoint | Add a new API endpoint |
| M | One feature slice | Registration flow |
| L | Multi-component feature | Search with filtering and pagination |

**L or bigger → split it.** Also split when it would take more than one focused session, when you can't state its acceptance criteria in 3 or fewer bullets, when it touches two independent subsystems, or when its title has an "and" in it. Agents do best on S and M.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change (rename a column, retype a shared symbol) whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own issue blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in an issue blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify issue; green is promised only there.

**Checkpoints**: after every 2–3 issues, and at each phase boundary, a checkpoint: tests pass, build is clean, the core flow works end to end, human review before continuing. Checkpoints live in the plan note, not as issues.

**Parallelization**: mark which slices are safe to run in parallel (independent slices, tests for built features, docs), which must be sequential (migrations, shared state, dependency chains), and which need a contract defined first (slices sharing an API: define the contract, then parallelize).

### 4. Quiz the user

Present the breakdown as a numbered list, in dependency order. For each issue:

- **Title** and **size**
- **Blocked by**: which other issues (if any)
- **What it delivers**: the end-to-end behaviour it makes work

Then the checkpoints, the top risks, and the open questions. Ask:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each issue only depend on issues that genuinely gate it?
- Should any issues be merged or split?

Iterate until the user approves.

### 5. Publish

Publish in dependency order (blockers first) so blocking edges can reference real identifiers.

- **GitHub / GitLab**: one issue per slice, labels `spec:<slug>` (`spec::<slug>` on GitLab), a category (normally `enhancement`), and `ready-for-agent` unless told otherwise (they're agent-grabbable by construction; use `ready-for-human` for a slice that needs judgment calls, external access or manual testing, and say why in the body). Attach each as a sub-issue of the spec issue, and set blocking edges natively where the tracker supports it (see the tracker doc).
- **Local**: one file per issue under `<notes root>/Issues/<slug>/`, numbered from `01` in dependency order, using the local template below.

Then:

- Update the spec issue's `## Issues` section with the ordered list of children (edit the body; don't close or otherwise modify the spec issue).
- Write the plan note `<notes root>/Plans/<slug>.md` from the template below.

Work the **frontier**: any issue whose blockers are all done. For a purely linear chain that's top to bottom.

<issue-template>

## Parent

Spec: #<spec> (omit when there's no spec)

## What to build

The end-to-end behaviour this issue makes work, from the user's perspective, not a layer-by-layer implementation list.

## Acceptance criteria

- [ ] Specific, testable condition
- [ ] Specific, testable condition

## Verification

- [ ] Tests pass: `<repo's focused-test command>`
- [ ] Build succeeds: `<repo's build command>`
- [ ] Manual check: <what to look at>

## Size

S | M (with one line on why, if not obvious)

## Blocked by

- #<n> <title>, or "None (can start immediately)". Omit when blockers were set as native edges.

</issue-template>

<local-issue-template>

# <NN>: <Issue title>

Category: enhancement
Status: ready-for-agent
Blocked by: <NN, NN> | None
Size: S | M

## What to build

…

## Acceptance criteria

- [ ] …

## Verification

- [ ] …

</local-issue-template>

<plan-template>

```markdown
---
type: plan
spec: <spec URL or path>
status: active
created: YYYY-MM-DD
---

# Plan: <Feature>

## Overview
One paragraph: what we're building and why (link the spec).

## Architecture decisions
- Decision and rationale (link `Decisions/NNNN` when one exists)

## Issues
### Phase 1: <name>
1. [#12 Title](https://…/issues/12) (S)
2. [#13 Title](https://…/issues/13) (M), blocked by #12

#### Checkpoint: <name>
- [ ] Tests pass, build clean
- [ ] Core flow works end to end
- [ ] Human review before Phase 2

### Phase 2: …

## Parallelization
- Safe in parallel: …
- Sequential: …
- Needs a contract first: …

## Risks and mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

## Open questions
- …
```

</plan-template>

In every form, avoid specific file paths or code snippets: they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts.

## Red flags

- An issue that says "implement the feature" with no acceptance criteria, or no verification step
- An L-or-bigger issue, or a title with "and" in it
- Horizontal slices (all schema, then all API, then all UI)
- No checkpoints between phases, or dependency order not considered
- Closing, overwriting or relabelling another plan's open issues to make room
- Putting tasks in both the tracker and a markdown checklist (the plan note indexes the issues, it doesn't duplicate them)

## Before you finish

- [ ] Every issue has acceptance criteria (≤3–4), a verification step and a size of S or M (XS fine)
- [ ] Blocking edges are set and ordered correctly; riskiest slices are early
- [ ] Every issue is a child of the spec and carries `spec:<slug>`; the spec's `## Issues` list is updated
- [ ] The plan note exists with checkpoints, risks and open questions
- [ ] No pre-existing incomplete plan was overwritten without explicit confirmation
- [ ] The user approved the breakdown before anything was published
