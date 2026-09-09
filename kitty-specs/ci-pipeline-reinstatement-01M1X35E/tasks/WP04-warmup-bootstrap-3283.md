---
work_package_id: WP04
title: Warmup / bootstrap
dependencies: []
requirement_refs:
- FR-003
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: .github/actions/warmup/action.yml
create_intent:
- .github/actions/warmup/action.yml
- tests/release/test_warmup_action.py
execution_mode: code_change
owned_files:
- .github/actions/warmup/action.yml
- tests/release/test_warmup_action.py
role: implementer
tags: []
tracker_refs:
- '#3283'
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (FOUNDATION F3),
`research.md` D2 (warmup env decision), `data-model.md` E8 (warmup env artefact), and
the charter §"Shared-Package pinned-rev" + DIR-051 (SHA-pinned actions).

## Objective

The canonical `pytest -n auto` cannot bootstrap on a fresh checkout — a venv-lock
timeout (#3283) poisons every job. This WP builds a **shared warmup / test-env-creation
composite action** that resolves dependencies + builds the editable environment
**once** and publishes it as a **cache-keyed reusable artefact**, so downstream shards
reuse it without re-running the install. Two resolution modes (research D2):

- **PR mode**: a **pinned `spec_kitty_events` rev** — deterministic, cache-hit,
  charter pinned-rev aligned (no moving branch ref).
- **Nightly/full mode**: **latest mainline** — to catch upstream drift early.

Cache via `actions/cache` keyed on `hash(uv.lock + resolved events rev)` (research D2:
NOT a bare `upload-artifact`, which conflates cache semantics). All actions SHA-pinned
(DIR-051).

## Subtask guidance

### T018 — Red-first: `test_warmup_action.py` pins the contract (SEPARATE first commit)

As your **first commit**, author `tests/release/test_warmup_action.py` asserting the
composite action's observable contract against the on-disk `action.yml`:

- inputs include a `mode` (`pr`|`full`) and the resolution behavior differs (pinned
  rev vs latest mainline);
- the cache key is derived from `uv.lock` + the resolved events rev;
- every `uses:` is pinned to a full commit SHA (DIR-051);
- the composite performs the editable install exactly once and exposes the built env
  for reuse.

Run against base and confirm red for the right reason (`action.yml` absent). Load the
YAML lazily/in-test so the file collects.

### T019 — Author the warmup composite

Create `.github/actions/warmup/action.yml` (`runs.using: composite`): checkout →
`astral-sh/setup-uv` (SHA-pinned) → resolve deps → editable install once. Keep steps
pinned and reviewed (no arbitrary `postinstall`; DIR-051 deny-by-default lifecycle).

### T020 — PR mode: pinned rev + cache

Implement PR-mode resolution against a **pinned** `spec_kitty_events` rev (charter
Shared-Package pinned-rev policy — no moving branch ref). Wire `actions/cache`
(SHA-pinned) keyed on `hash(uv.lock + resolved events rev)`; a cache hit skips the
rebuild. Deterministic per (lockfile, rev) — the E8 invariant.

### T021 — Nightly/full mode: latest mainline + mode threading

Implement `mode: full` resolving the **latest** `spec_kitty_events` mainline (upstream
drift signal). Thread the `mode` input through the composite so callers (WP09
module-tests, WP13 nightly) select behavior. Document the PR↔full split in the action's
inputs description.

### T022 — Prove #3283 elimination

Demonstrate (in the test + a short note in the action doc) that one pre-warm publishes
the reusable env and downstream consumption reuses it **without re-running the
install** — the mechanism that dissolves the venv-lock cascade. The test asserts the
single-build-then-reuse contract; the runtime proof lands when WP09 consumes it.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP04`.
- No dependencies — this WP is decoupled and can land early in FOUNDATION.
- Commit order: **T018 red-first FIRST**, then T019–T022.

## Definition of Done

- T018 red on base (evidence captured), green on final.
- `.github/actions/warmup/action.yml` is a composite that builds the env once, caches
  on `hash(uv.lock + events rev)`, supports `pr` (pinned) / `full` (latest) modes, and
  is fully SHA-pinned — each of these is an **assertion in `test_warmup_action.py`**
  (cache-key derivation, pr/full behavior divergence, every `uses:` full-SHA), verified
  by running that test, not eyeballed off the YAML.
- `#3283` is addressed: `test_warmup_action.py` asserts the single-build-then-reuse
  contract (objective, machine-checked).
- **Targeted test surface** (the test that gates this DoD): `pytest tests/release/test_warmup_action.py -q`.

## Risks

- **Ticket assignment (DIR-012)**: assign #3283 to the HiC before/as you begin.
- **Cache-key drift**: an over-broad key never hits (slow) or an under-broad key serves
  a stale env (wrong). Key strictly on `uv.lock` + resolved rev per E8.
- **Supply chain (DIR-051)**: pin every action to a full SHA, not a moving tag; record
  versions. First-party `actions/*` + `astral-sh` are canonical publishers.
- **Runtime proof deferred**: the true #3283 kill is evidenced when WP09 consumes the
  env in a real run — note this handoff; do not over-claim runtime success from the
  static contract test alone.

## Reviewer guidance

- Verify T018 red-on-base for the right reason (missing `action.yml`).
- Confirm every `uses:` is a full commit SHA.
- Confirm the cache key and the pr/full mode split match research D2 and E8.
- Confirm no bare `upload-artifact` is used where cache semantics are required.
