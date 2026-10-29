---
name: spec
description: "Turn the current conversation into a spec and publish it to the configured tracker as a parent issue labelled `spec` + `spec:<slug>`, which /issues then breaks into child issues. No interview, just synthesis of what's already been discussed (run /brainstorm first if the intent isn't settled)."
disable-model-invocation: true
---

# Spec

Take the current conversation and codebase understanding and produce a spec. Do NOT interview the user; synthesize what you already know. If the conversation hasn't settled what's being built, for whom and what's out of scope, say so and suggest `/brainstorm` instead of guessing.

Read the repo's `## Agent skills` block for the tracker, notes root and labels (see the `setup` skill's [notes.md](../setup/notes.md) for how to find it). If there's no block, tell the user to run `/setup`. Tracker operations are in `../setup/trackers/<github|gitlab|local>.md`; labels in [labels.md](../setup/labels.md).

## Process

1. **Explore.** Understand the current state of the code if you haven't already. Read the notes root's `Glossary.md` and the `Decisions/` in the area you're touching; use the glossary's vocabulary throughout, and flag any decision the spec contradicts. If a confirmed brainstorm note exists for this topic (`<notes root>/Brainstorms/`), use its Outcome / Success / Out of scope as the backbone.

2. **Pick the seams.** Sketch the seams at which the feature will be tested. Prefer existing seams to new ones, and the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better; the ideal number is one. Check with the user that the seams match their expectations.

3. **Pick the slug.** A short kebab-case name for the spec (`csv-export`, `oidc-deploy-role`). It becomes the `spec:<slug>` label and the `Plans/<slug>.md` note, so check the tracker doesn't already have that label for a different spec. Confirm it with the user alongside the seams.

4. **Write and publish** the spec using the template below:
   - **GitHub / GitLab**: create the `spec:<slug>` label (`spec::<slug>` on GitLab) if missing, then create the spec issue titled `Spec: <title>` with labels `spec`, `spec:<slug>` and `enhancement`. **No state label**: the spec is the parent container for the issues `/issues` will create, not agent work itself.
   - **Local**: write `<notes root>/Issues/<slug>/spec.md` with the header lines from the local tracker doc.

5. **Hand off.** Give the user the spec reference and suggest `/issues <ref>` to break it down. Don't start that in the same turn.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested, and at which seams
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

## Issues

_Filled in by `/issues`._

</spec-template>
