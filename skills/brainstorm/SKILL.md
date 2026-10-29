---
name: brainstorm
description: "Interview the user until you understand what they actually want, then grill the design tree until every decision is settled. Phase 1 extracts intent one question at a time (hypothesis + confidence, a guess with every question, an explicit-yes restate); phase 2 walks the remaining design decisions in rounds with recommended answers. Use when an ask is underspecified ('build me X' without who/why/success), before /spec, or on 'brainstorm', 'grill me', 'interview me', 'stress-test this', 'are we sure?'. Also runs in design-only mode from /triage."
---

# Brainstorm

What people ask for and what they actually want are different things. The cheapest moment to find that gap is before any spec, plan or code exists. This skill closes it in two phases, then stops:

1. **Intent**: what does the user actually want? One question at a time until you can predict their answers.
2. **Design**: which decisions does that want imply? Grilled in rounds until nothing is silently assumed.

**Design-only mode** skips phase 1. Use it when called from `/triage` (the issue already carries the intent), or when the user says the intent is settled ("I know what I want, grill the design"). Say which mode you're in at the start.

**When NOT to use:** unambiguous, self-contained asks (rename, typo); pure information requests; mechanical work; when the user explicitly wants speed over verification.

This skill needs a live user. In non-interactive contexts (CI, `/loop`, scheduled runs), don't run it: flag the underspecified ask as a blocker instead of guessing.

**Facts are your job, decisions are the user's.** When a question needs a fact from the environment (code, config, tools, docs), look it up, or dispatch a sub-agent for anything bigger than a couple of reads. Never ask the user what you could find out. Don't block on a running lookup: only the questions downstream of it wait.

If the repo has an `## Agent skills` block (see the `setup` skill's [notes.md](../setup/notes.md)), read the notes root's `Glossary.md`, `Decisions/` and `Brainstorms/` on the topic first, so you don't re-ask what's settled and you use the project's vocabulary.

## Phase 1: Intent

### Hypothesize, with a confidence number

Before asking anything, write your best one-sentence read of what the user wants and an honest confidence:

```
HYPOTHESIS: You want a way to answer "how are we doing?" in standup, and "dashboard" was the convention that came to mind.
CONFIDENCE: ~30% (missing: who it's for, what "metrics" means here, what success looks like)
```

Below ~70%, always say on the same line what's missing. Update the hypothesis and number as answers come in, so the user sees it move.

### One question at a time, each with a guess

```
Q:     <one focused question>
GUESS: <your answer for them, with the reasoning that produced it>
```

Then wait. One at a time because the next question usually depends on this answer, and because the user can only react to a hypothesis that isn't buried in a list. The guess is there because reacting to a wrong guess is faster than answering from scratch. The risk is a polite user agreeing to be agreeable: be visibly willing to be wrong, and now and then guess in a direction you expect them to push back on.

Aim at the four things an underspecified ask is missing: **who** it's for, **why** (and why now), what **success** looks like, and the binding **constraint**.

### Listen for "want vs. should want"

Watch for answers that sound like what a thoughtful answer should be rather than what the user wants: best-practice talk ("scalable", "clean", "robust", "modern") with no specifics, deference to convention ("the standard way"), "I should probably…", "good practice says…". When you hear them, ask:

> _"If you didn't have to justify this to anyone, what would you actually want?"_

### Stop test

You're done with phase 1 when you can answer yes to: **can I predict the user's reaction to the next three questions I'd ask?** If after several questions your confidence isn't rising, stop and say so: "I've asked N questions and still can't predict your answers. Something foundational is missing. Want to step back?"

### Restate, and get an explicit yes

```
Here's what I now think you want:

- Outcome:      <one line>
- User:         <who benefits>
- Why now:      <what changed>
- Success:      <how we'll know it worked>
- Constraint:   <the binding limit>
- Out of scope: <what we're explicitly not doing>

Yes / no / refine?
```

Use their words. "Out of scope" is mandatory: half of misalignment is silent disagreement about what's not being built.

The gate is an explicit **yes**. Not yes: "whatever you think" (delegation: re-ask as a choice between two concrete options), "sounds good" or "sure, let's go" (ask "anything you'd refine?"), silence followed by "ok let's start" (ask whether you've missed something). On a correction, fold it in and restate.

## Phase 2: Design

Map the decisions the confirmed intent implies as a **design tree**: every decision branches into the decisions that hang off it. If the tree is trivial (nothing a reasonable person would decide differently), say so and skip to the stop.

Work it in **rounds**. The **frontier** is every decision whose prerequisites are settled: the questions you can ask now without guessing at answers you haven't heard. Ask the whole frontier in one round, numbered, each with your recommended answer, worded so "yes" accepts the recommendation:

```
❓ **Q1** - **<question title>**: <question body, with the options and trade-offs when they genuinely branch>

➡️ <your recommended answer>

---

❓ **Q2** - …
```

Then wait. Each round's answers reshape the tree: recompute the frontier and ask the next round. A question that depends on another still open in this round belongs to a later round.

The same honesty rules apply: probe buzzword answers, and treat "whatever you think" as a request for your recommendation to be stated as a concrete choice, not as a decision.

Phase 2 is done when the frontier is empty: every branch visited, nothing silently assumed. Summarise the shared understanding (the intent restate, if phase 1 ran, plus the decisions) and get an explicit yes on it.

## Stop: deliver, offer, hand back

When the user confirms:

1. **Deliver** the confirmed outcome: the restate and the settled decisions.
2. **Offer** (each only on an explicit yes; never save before the user has confirmed the content):
   - Save it to `<notes root>/Brainstorms/<topic>.md`, or, with no `## Agent skills` block, to `~/Documents/Workbench/Brainstorms/<topic>.md` or a path the user gives. Frontmatter: `type: brainstorm`, `date`, `status: confirmed`.
   - Record **decisions** that are hard to reverse, surprising to a newcomer, or the result of a real trade-off as ADRs in `<notes root>/Decisions/NNNN-<slug>.md` (format in [notes.md](../setup/notes.md)). Most decisions don't qualify; say which ones do and why.
   - Add new or sharpened **terms** to `<notes root>/Glossary.md` (term, one-line definition, synonyms to avoid).
   - Next step: `/spec` to write it up as a spec, or back to `/triage` in design-only mode.
3. **Stop the turn.** Don't invoke tools or start downstream work in the same turn as the confirmation; hand control back.

In design-only mode from `/triage`, skip the Brainstorms save (the outcome goes into the triage comment or agent brief) but still offer decisions and terms.

## Red flags

- Phase 1: two or more questions in one message, or a question without a guess
- A confidence below ~70% with no reason attached, or no visible movement after three questions
- Accepting "whatever you think", "sounds good" or a buzzword answer as terminal
- Asking the user a fact you could have looked up
- Phase 2: asking a question whose prerequisite is still open in the same round
- A restate without an Out of scope line
- Producing a spec, plan or issue, or saving a note, before the explicit yes
- Starting downstream work in the confirmation turn
