---
name: refactor
description: "Scan a codebase (Go, Python, Terraform, Helm, GitHub Actions) for deepening opportunities: shallow modules whose interface is nearly as wide as their implementation. Present them as a visual HTML report, then brainstorm the one the user picks in design-only mode. Use when the user runs /refactor, asks for an architecture review, or wants to find refactors that make code easier to test and navigate."
disable-model-invocation: true
---

# Refactor

Surface architectural friction and propose **deepening opportunities**: refactors that turn shallow modules into deep ones. The aim is testability (fewer, higher seams for `/tdd`) and navigability (an agent or a newcomer finds the logic in one place).

This skill needs a live user: it ends in `/brainstorm`. In non-interactive contexts, write the report and stop.

It is read-only until the user confirms a design. No refactors, no `terraform`/`helm`/`kubectl` commands beyond reading files, and never open `.env` files, kubeconfigs, `*.tfstate` or Secret manifests.

## Vocabulary

Use these terms exactly in every candidate, in the report and in the brainstorm.

- **Module**: anything with an interface and an implementation. A Go package, a Python module, a Terraform module, a Helm chart, a reusable workflow or composite action.
- **Interface**: everything a caller must know to use the module: exported names, function parameters, Terraform `variable`s and `output`s, Helm `values.yaml` keys, workflow `inputs`/`outputs`/`secrets`.
- **Implementation**: what sits behind the interface.
- **Depth**: how much implementation a module hides per unit of interface. A **deep** module has a small interface over a lot of behaviour; a **shallow** one has an interface nearly as wide as its implementation.
- **Seam**: a place where you can observe or substitute behaviour without reaching inside, as in `/tdd`. Tests live at seams.
- **Adapter**: an implementation that plugs into a seam (real AWS client in prod, `moto` in tests).
- **Leverage**: how many callers one interface serves. One deep module, N call sites.
- **Locality**: how close together the code you change for one concept lives. Bugs concentrate where locality is high.

Don't drift to "component", "service" or "unit" when you mean module, to "API" or "signature" when you mean interface, or to "layer" or "wrapper" when you mean module.

Three principles:

- **The deletion test.** Imagine deleting the module and inlining it into its callers. If complexity *concentrates* (callers now repeat the same logic), the module earns its place. If it just *moves* (callers get one line longer), it's shallow.
- **The interface is the test surface.** Tests at the interface survive refactors of the implementation. If the only way to test something is to reach inside, the seam is in the wrong place.
- **One adapter is a hypothetical seam, two is a real one.** A Go interface with a single implementation and no test double, or a Terraform module with a single caller, is speculation until a second adapter or caller exists.

## Process

### 1. Scope

**YAGNI first.** Deepening a module pays off by making future changes to it easier, so weight the parts of the codebase that actually change. Decide *where* to look before you look:

- If the user named a direction (a package, a Terraform module, a workflow, a pain point), take it and skip the inference below.
- Otherwise, find the hot spots in recent history:

  ```sh
  git log --since=6.months --format= --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -30
  ```

  Let the paths that keep coming up pull your attention first. If changes are scattered with no clear hot spot, widen the window or the net.

If the repo has an `## Agent skills` block (see the `setup` skill's [notes.md](../setup/notes.md)), read the notes root's `Glossary.md` and the `Decisions/` that touch the area. If they don't exist, proceed silently.

### 2. Explore

Delegate the walk to the `context-scout` agent so the file reads stay out of the main session. Brief it narrowly: the hot-spot paths, the vocabulary and principles above, the friction questions below, the paths it must not open (secrets, state, kubeconfigs), and "return candidates as `files: problem` with `file:line` references, not file contents". For a large repo, split the hot spots across two or three scouts in one message.

Don't follow rigid heuristics; note where understanding hurts:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow**, with an interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts are untested, or hard to test through their current interface?

Shapes that are common in this stack:

- **Go**: an interface declared next to its only implementation (one adapter, hypothetical seam); a package per type with callers stitching four packages together; `utils`/`common` packages with no concept behind them.
- **Python**: thin client classes that forward every method to `boto3`; helpers split out of a function only so they can be unit-tested, while the orchestration that breaks stays untested.
- **Terraform**: a module wrapping a single resource whose `variable`s mirror the resource arguments one to one (the deletion test says inline it); or the opposite, the same five resources copy-pasted across environments with no module at all.
- **Helm**: `values.yaml` keys that map one to one onto template fields, so the chart hides nothing.
- **GitHub Actions**: reusable workflows or composite actions with as many `inputs` as steps; the same job block duplicated across workflows instead of one reusable workflow.

Apply the **deletion test** to anything you suspect is shallow. A "yes, complexity concentrates" is the signal you want.

### 3. Present candidates as an HTML report

Write a self-contained HTML file to `${TMPDIR:-/tmp}/architecture-review-<timestamp>.html` so nothing lands in the repo and each run gets a fresh file. Open it with `open <path>` and tell the user the absolute path.

The report uses **Tailwind via CDN** for layout and **Mermaid via CDN** for graph-shaped diagrams (call graphs, module dependencies, sequences), mixed with hand-built divs/SVG for the editorial visuals (mass diagrams, cross-sections). Each candidate gets a **before/after visualisation**. Be visual.

Each candidate is a card with:

- **Files**: the modules involved
- **Problem**: why the current shape causes friction
- **Solution**: plain-English description of what would change
- **Benefits**: in terms of locality and leverage, and how the tests would improve (which seam they'd move to)
- **Before / After diagram**: side by side, showing the shallowness and the deepening
- **Recommendation strength**: `Strong`, `Worth exploring` or `Speculative`, as a badge

End with a **Top recommendation**: which candidate you'd tackle first and why.

Use the glossary's vocabulary for the domain and the vocabulary above for the architecture. If the glossary defines "Deployment", say "the Deployment rollout module", not "the DeployHelper" and not "the deployment service".

**ADR conflicts**: if a candidate contradicts an existing decision in `Decisions/`, only surface it when the friction is real enough to reopen it, and mark it in the card: _"Contradicts Decisions/0007, but worth reopening because…"_. Don't list every refactor a decision rules out.

See [HTML-REPORT.md](HTML-REPORT.md) for the scaffold, diagram patterns and styling.

Don't propose interfaces yet. After the file is written, ask: **"Which of these would you like to explore?"** Then wait.

### 4. Brainstorm the chosen candidate

Invoke the `brainstorm` skill in **design-only mode**: the candidate card is the settled intent. Seed the design tree with these branches so the first round isn't asked from a blank page:

- **Constraints**: what can't change (exported names other repos import, Terraform resource addresses that would force `moved` blocks or recreation, workflow inputs callers depend on)
- **Dependencies**: which callers change, and in what order
- **Shape**: the deepened module's interface, as small as it can be
- **Behind the seam**: what moves into the implementation, and which adapters exist (in-process, local-substitutable like `testcontainers` or `moto`, or a true external that `/tdd` would mock)
- **Tests**: which existing tests survive at the new seam, and which ones tested internals and get deleted

Follow `brainstorm`'s rules: rounds with recommended answers, and nothing saved before the explicit yes. At its stop, alongside its own offers:

- **New or sharpened terms**: offer to add them to `Glossary.md`, including the name of the deepened module if it names a concept the glossary lacks.
- **Rejected candidate with a load-bearing reason**: offer an ADR: _"Want me to record this in Decisions/ so future architecture reviews don't re-suggest it?"_ Only when a future explorer would need the reason; skip ephemeral ones ("not worth it right now") and self-evident ones.
- **Next step**: `/spec` to write the refactor up, then `/issues` and `/implement`. For a small refactor, a Jira ticket via `/start-ticket` is enough.

**Designing it twice**: if the user wants alternative interfaces for the deepened module, spawn two or three `Plan` agents in one message, each with the same candidate and a different constraint (smallest possible interface; optimise for the most common caller; ports and adapters). Present the designs side by side and fold the chosen one back into the brainstorm. Only on request: it costs a few agents' worth of tokens.

## Red flags

- Exploring in the main session instead of delegating to `context-scout`
- Scanning the whole repo when the history shows clear hot spots
- A candidate that fails the deletion test, or one justified with "cleaner" or "easier to maintain" instead of locality and leverage
- Proposing interfaces in the report, before the user picks a candidate
- Editing code, or saving a glossary term or ADR, before `brainstorm`'s explicit yes
- Opening secrets, state files or kubeconfigs while exploring
