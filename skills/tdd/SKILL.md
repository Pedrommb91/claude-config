---
name: tdd
description: "Test-driven development in Go and Python: agree the seams under test with the user, then run vertical red → green slices (one failing test, one minimal implementation) with `go test -run` / `pytest -k`. Covers what a good test is, where tests go, when to mock (system boundaries only), and the anti-patterns. Use when the user wants to build a feature or fix a bug test-first, mentions TDD or red-green-refactor, asks for integration tests, or picks up an issue from /issues that should be driven by tests."
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle: consult them before and during the loop, not after.

Before exploring, read the repo's `## Agent skills` block for the notes root (see the `setup` skill's [notes.md](../setup/notes.md)), then `<notes root>/Glossary.md` and the `Decisions/` ADRs in the area you're touching, so test names and interface vocabulary match the project's domain language. If they don't exist, proceed silently.

Follow the repo's existing test conventions over anything here: test layout, runner, helpers, fixtures, assertion library (`testify` or stdlib, plain `assert` or a helper).

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: `TestCheckout_ConfirmsValidCart` or `test_checkout_confirms_valid_cart` tells you exactly what capability exists, and it survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

- **Go**: the exported API of a package, tested from an external `_test` package (`package orders_test`) so the test can only see what callers see. An HTTP handler via `httptest`; a CLI via its `run(args, stdout, stderr) error` entry point.
- **Python**: the module's public functions and classes (no leading underscore); a FastAPI/Flask app via its test client; a CLI via its `main(argv)`.
- **Infra code**: a Terraform module via `terraform test` (`.tftest.hcl`, `command = plan` for fast checks); a Helm chart via `helm template` output; a K8s manifest via `kubectl apply --dry-run=server` against a confirmed context. Ask before anything that would create real resources.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything, so agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?" Give each proposed seam a one-line note on what it catches and what it misses. If the shape of the interface itself is unsettled (what to export, where the boundary belongs), settle it with `/brainstorm` first rather than inside the loop.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests unexported functions or `_private` helpers, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (`assert total(items) == sum(i.price for i in items)`, a golden file regenerated from the code under test, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, the spec.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than caller-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead: one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you. A table-driven test grows one row per cycle; it is not written up front.

## Rules of the loop

- **Red before green.** Write the failing test first, run it, and see it fail for the right reason (an assertion, not a compile error or import error) before writing code. Then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Run narrowly, then widely.** Each cycle runs just the new test (`go test ./pkg/orders -run 'TestCheckout$'`, `pytest tests/test_orders.py -k checkout`), and keeps output small. At the end of the loop run the repo's full checks (`go build ./...`, `go vet ./...`, `go test ./...`; or `ruff check`, `pytest`) and report the results. Add `-race` when the slice touched goroutines.
- **No sleeps, no real clocks, no network.** Inject time and randomness; use `t.TempDir()` / `tmp_path` for the file system. A flaky test is a failed slice.
- **Bug fixes start with the reproducing test.** The first red is the bug itself, at the seam where the user saw it.
- **Refactoring is not part of the loop.** It belongs to the review stage (`/review`, `/simplify`), not the red → green implementation cycle.
