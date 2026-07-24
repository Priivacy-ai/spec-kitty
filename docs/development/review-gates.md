---
title: 'Review Gates: Pre-PR / Pre-Review Checklist'
description: The pre-PR/pre-review hygiene checklist contributors run locally — environment sync and test gates — so review focuses on substance, not avoidable environment drift.
doc_status: active
updated: '2026-07-07'
type: how-to
related:
- docs/development/local-overrides.md
---
# Review Gates: Pre-PR / Pre-Review Checklist

This page documents the small set of hygiene steps a contributor should run
locally before requesting review or opening a PR. The goal is to catch
trivial environment drift here, so the actual review focuses on the
substance of the change and not on confusing failures unrelated to it.

## Environment hygiene before review/PR

Run the documented sync command from the repository root **before**
running the test gates:

```bash
uv sync --frozen
```

### Why

The CLI consumes `spec-kitty-events` and `spec-kitty-tracker` from PyPI.
Compatibility ranges live in `pyproject.toml`; **exact pins** live in
`uv.lock`. If your installed copy of either shared package drifts away
from `uv.lock` (for example, after an ad-hoc `pip install` against a
sibling checkout, or after switching branches without re-syncing), the
review-gate test suite can fail in ways that look like real defects but
are actually pure environment drift.

### What `uv sync --frozen` does

It installs the **exact resolved versions from `uv.lock`** into your
active virtualenv without re-resolving the dependency graph. This is
the cheapest possible "snap me back to the lockfile" operation:

- It does not modify `pyproject.toml`.
- It does not modify `uv.lock`.
- It does not contact the resolver -- only the package index for the
  pinned wheels.

### When to run it

Run `uv sync --frozen` any time:

- You pull `main` (or any branch with new lock changes).
- You switch branches.
- You change `pyproject.toml` or `uv.lock`.
- You temporarily installed an editable / sibling-checkout copy of
  `spec-kitty-events` or `spec-kitty-tracker` for cross-package work
  (see [`local-overrides.md`](local-overrides.md) for the dev workflow).
- The drift detector fails (see below).

### Automated detection

The architectural test
[`tests/architectural/test_uv_lock_pin_drift.py`](../../tests/architectural/test_uv_lock_pin_drift.py)
detects drift between `uv.lock` and the installed versions of the
governed shared packages (`spec-kitty-events`, `spec-kitty-tracker`).

If that test fails, the failure message names every offending package
and prints the literal command to fix it:

```
uv.lock vs installed-package drift detected for governed shared packages:
  - spec-kitty-events: locked=4.1.0, installed=4.0.7
Run the documented pre-review/pre-PR sync command from the repository root:
  uv sync --frozen
```

That is the **only** documented sync command for this purpose. Do not
substitute `uv pip sync`, `uv pip install`, or any other variant -- they
either re-resolve the graph or skip the lockfile entirely, both of which
defeat the point.

## Typer/click version skew (`spec-kitty review` preflight)

`spec-kitty review` also checks that the active interpreter's `typer` and
`click` versions match the exact versions pinned in `uv.lock`. CI always
installs via `uv sync --frozen --all-extras`; a local `.venv` built without
`--frozen` can drift onto a newer release -- including a `typer>=0.26`
release that vendors `click` internally and stops re-exporting it (see the
TID251 Gap-5 ban in `pyproject.toml`) -- so local CLI-shard test runs can
silently diverge from CI without this check.

**Warn-loud by default**: a divergence prints a `MISSION_REVIEW_ENV_SKEW`
warning (see
[`ERROR_CODES.md`](../../src/specify_cli/cli/commands/review/ERROR_CODES.md#env_skew))
and `spec-kitty review` proceeds.

**Fail-closed is opt-in**: set `SPEC_KITTY_ENV_SKEW_FAIL_CLOSED=1` to make
the preflight exit non-zero on divergence instead of warning. This is
intentionally opt-in -- a legitimately forward-compat dev loop (testing
against a newer `typer`/`click` ahead of the repo's pin bump) must not be
bricked by default.

Resolve a skew warning the same way as any other lock drift:

```bash
uv sync --frozen --all-extras
```

## Running the CI residual selection locally

CI runs an always-on `unit-contract-residual` job
(`.github/workflows/ci-quality.yml`) that selects tests marked `unit` or
`contract` which carry no other routed runnable marker -- the authoring-
taxonomy residual (mission `ci-suite-map-bind`, closes #2034). Previously
there was no way to run this exact selection locally before pushing, so a
marker-orphan failure only ever surfaced in CI.

Run it locally with:

```bash
spec-kitty review --check-residual
```

This skips the mission-scoped review gates and instead runs the CI
residual `-m` selection over `tests/` locally, exiting with pytest's return
code (`--mission` is not required for this flag). The `-m` expression is
**read live** from the `unit-contract-residual` job in
`.github/workflows/ci-quality.yml` at run time -- it is never hand-copied
into the CLI, so a future change to the CI selector is picked up
automatically on the next run with no risk of drift (NFR-002). The
`_test_env_check` marker parser is pinned to `_gate_coverage`'s parser by
`test_env_check_marker_parser_agrees_with_gate_coverage_live`, so the two
readers of that `-m` expression cannot silently diverge.

> **Note:** `--check-residual` runs the selection **serially** (plain
> `pytest -m ...`), not with CI's parallel `-n auto --dist loadfile`. It
> selects exactly the same tests as CI but takes longer to finish locally.

## Pre-review regression gate (`move-task --to for_review`)

When a work package moves to `for_review`, Spec Kitty runs a **doctrine-resolved**
transition gate. Rather than a hardcoded call into one repo-specific engine, the
hook resolves *which* named handlers the repo's active doctrine binds to the
current lane edge (`in_progress->for_review`), dispatches each, and aggregates
their verdicts (mission `doctrine-controlled-transition-gates`, epic #2535
half A). In the Spec-Kitty source tree the built-in `software-dev/review`
step-contract binds the `spec-kitty-pre-review` handler, which derives the CI
shards covering the WP's changed files and re-runs them — so a WP that broke a
shared contract pinned by a test *outside* its `owned_files` is caught at review
time instead of only at merge (#572, #1979). By default the gate is
**warn-only** -- it reports a new failure but the move still proceeds.

**How the impl is selected.** Activation, not repo shape, decides whether the
gate fires. A repo whose active doctrine binds no handler to the edge runs *no*
gate (a distinguishable `NO_COVERAGE` warn, never a silent skip); a repo that
activates a handler runs it. Toggling the binding's handler in doctrine flips
whether the gate fires with **no code change** between states.

**Fail-open and hard-stops.** Every handler *execution* error degrades to exactly
one visible unverified `NO_COVERAGE` warning — a faulting handler never removes
another's block from the computation. Exactly **two** hard-stops survive: a
terminal interruption (`TIMED_OUT`/`CANCELLED`) aborts the move with the
transition unapplied, and the opt-in `NEW_FAILURES` block (below) refuses the
move. Terminal is checked before the block. This is the closure of the
pre-review facet of #2534: a consumer repo never imports Spec-Kitty's internal
`_gate_coverage` authority, and even under *erroneous* activation of the
`spec-kitty-pre-review` handler the internal import is refused and degrades to a
`NO_COVERAGE` warn — the closure is structural, not configuration-dependent.

Configuration (`.kittify/config.yaml`, under `review:`):

- `review.fail_on_pre_review_regression` (bool, default `false`) -- opt in to
  **block** the move when the gate finds a new failure. `move-task --force`
  records an override and proceeds anyway.
- `review.test_command` -- selects which `ScopeSource` implementation the gate
  runs (`resolve_scope_source`, `scope_source.py`): when set, a portable
  `DeclaredCommandScopeSource` runs exactly this command; when unset --
  including in the Spec-Kitty source repo itself -- the gate falls back to the
  internal `GateCoverageScopeSource`, which derives its own scoped pytest
  invocation and ignores this key entirely. The block can only be *enforced*
  when a command is available (declared or derived); opting in to the block
  without one yields a loud warning (the gate cannot run a command it does not
  have).
- `review.pre_review_test_command` -- **deprecated** and aliased to
  `review.test_command`. A config that still sets it keeps working but earns a
  one-time deprecation warning; move the value to `review.test_command`.

> **Inherited limitation (#2741, P1 — inherited, NOT fixed by this mission).**
> The gate scopes off the WP worktree's *working-tree* diff rather than the WP
> commit range. The doctrine-controlled-transition-gates inversion is
> behaviour-preserving and therefore *preserves* this by design; it is tracked
> separately and must not be mistaken for a fix or flagged as a regression. Only
> the `for_review` pre-review facet of the repo-shape coupling is inverted here.

## PR draft and WIP-title conventions

A `WIP` or `[WIP]` prefix on your PR title marks the PR as author-declared
not-ready. The two draft-gated CI suites (`integration-tests-core-misc`,
`e2e-cross-cutting`) **skip** on a WIP-titled PR, but the `quality-gate`
aggregator's exemption is draft-*flag*-only -- not title-based -- so a
**non-draft** PR that still carries a WIP prefix is a contradiction the gate
rejects by design: requesting review while WIP-titled must not pass. To land,
either drop the `WIP` / `[WIP]` prefix from the title, or keep the PR in draft
until it is ready. (See the `DRAFT_GATED_JOBS` note in
[`.github/workflows/ci-quality.yml`](../../.github/workflows/ci-quality.yml).)

## Shippable doctrine: built-in doctrine must work in a consumer repo

**Built-in doctrine (anything under `src/doctrine/**/built-in/`) MUST be valid
and actionable in a consumer repository that has activated the pack but has NO
access to the spec-kitty source tree, CI, or tooling.** A doctrine pack is
installed/activated as a *pack* in an arbitrary customer repo — it does not ship
our `scripts/`, `.github/`, `src/`, or `tests/` directories, and never will.

When reviewing (or authoring) a directive, styleguide, tactic, procedure,
toolguide, or glossary pack, reject any of these:

- **A reference to a spec-kitty repo-local file as if the consumer has it** —
  e.g. naming `scripts/docs/<x>.py`, `.github/workflows/<y>.yml`,
  `src/specify_cli/...`, or a `tests/...` path as the enforcement mechanism or a
  resolvable artifact. The consumer repo has none of these. Mentioning our own
  CI or code-repo paths in shipped doctrine is an inconsistency waiting to
  happen (and, when the doctrine is activated in a customer repo, a dangling
  reference).
- **Consumer-facing logic (a lint, gate script, or other executable) that is
  not shipped as part of the pack.** The canonical way to ship executable logic
  or any blob to downstream repos is the **`asset` doctrine kind** (a sidecar
  `*.asset.yaml` manifest + the blob under the pack's `assets/` tree — see
  [`create-a-doctrine-artifact.md`](../doctrine/create-a-doctrine-artifact.md)
  and [`doctrine-kinds.md`](../doctrine/doctrine-kinds.md)). Do **not** force
  downstream customers to add executable scripts or CI to their own repos to
  satisfy our doctrine.

**Quick check:** `grep -rEn 'scripts/|\.github/|src/specify_cli|tests/' src/doctrine/*/built-in/`
should return nothing that a consumer is expected to *resolve or run*. Prose that
merely describes an internal practice ("maintained by periodic review") is fine;
a path presented as a live gate or resolvable artifact is not.

## See also

- [`local-overrides.md`](local-overrides.md) -- developer-only workflow
  for working across `spec-kitty-cli` / `spec-kitty-events` /
  `spec-kitty-tracker` checkouts without committing editable sources.
- [`tests/architectural/test_pyproject_shape.py`](../../tests/architectural/test_pyproject_shape.py)
  -- TOML-shape assertions for the shared-package boundary
  (compatibility ranges, no committed editable sources, etc.).
- The CI job `clean-install-verification` in
  `.github/workflows/ci-quality.yml` performs the equivalent
  fresh-venv check on every PR.
