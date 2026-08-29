---
work_package_id: WP04
title: Conftest de-mask + fixtures + CI opt-in
dependencies:
- WP01
requirement_refs:
- FR-010
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: tests/conftest.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/conftest.py
- .github/workflows/ci-quality.yml
- tests/auth/**
- tests/readiness/**
- tests/saas/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Make the suite's default posture **sync-off** so the WP05 `skipif` guards actually fire, while keeping the opt-in path fully exercisable — and add the CI opt-in job so the collection-completeness gate still selects every sync test file.

- **T011** — invert the conftest force-opt-in: `tests/conftest.py:223` `setdefault(ENABLE_SAAS_SYNC=1)` and the `:427` autouse, both to default-OFF.
- **T012** — add `sync_enabled` / `sync_disabled` fixtures; migrate the non-sync flag-consumers in `tests/auth`, `tests/readiness`, `tests/saas` onto `sync_enabled`.
- **T013** — add `env: SPEC_KITTY_ENABLE_SAAS_SYNC: "1"` to the `fast-tests-sync` CI step so collection-time opt-in works (a fixture is too late — the #3213 lesson).

## Context

Authoritative sources:

- **plan.md → BINDING** items 8 (collection-time opt-in MUST be a CI-job ENV var, not a fixture — #3213), 9 (~60 non-sync files read the flag via the autouse and get NO skipif — they must move onto the `sync_enabled` fixture or they silently change/red when the default flips; 20 use the `sync_module.` late-bind co-gate and must keep working — C-006).
- **plan.md → Architecture / decision 5** — de-masking rationale; the conftest currently forces the whole suite opt-in ON, which would make every `skipif` inert.
- **spec.md** — FR-010 (skip + de-mask conftest + fixtures + CI opt-in job), NFR-003 (completeness gate stays green), User Story 3.

**The #3213 lesson (BINDING item 8)**: collection-time `skipif` is evaluated at collection, before any fixture runs. So the opt-in that keeps sync tests selected under the CI job MUST be a process-level ENV var set on the CI step, NOT a pytest fixture. Fixtures run too late to affect collection.

**Owned-files boundary note**: this WP owns `tests/auth/**`, `tests/readiness/**`, `tests/saas/**` for the fixture migration. The broader ~60-file migration (clusters in `tests/cli/commands`, `tests/specify_cli/cli/commands/agent` + `/commands`, `architectural`, `docs`, `integration`, `e2e`) touches files this map does not assign to WP04. Handle those as **within-WP out-of-map edits with a one-line rationale each** (they are otherwise unowned and would silently red when the default flips); 20 of them use the `sync_module.` late-bind co-gate (C-006) and must keep working via the fixture. Do NOT edit files owned by other WPs.

## Per-Subtask Guidance

### T011 — Invert the conftest force-opt-in to default-off

**Steps**
1. `tests/conftest.py:223` — the `os.environ.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")` (or equivalent) that forces opt-in ON: invert to default-OFF (do not setdefault the flag on; ensure the default env has it unset/absent).
2. `tests/conftest.py:427` — the autouse fixture that currently forces the opt-in: invert so the default posture is sync-OFF. Preserve the ability to turn it on via the new fixtures (T012) and the CI env var (T013).

**Files**: `tests/conftest.py`.

**Validation**: after this change, collecting `tests/sync` with no env set should begin to show the tests as *runnable-but-would-fail* (until WP05 adds skipif) — the key proof is that the flag is no longer forced on. Confirm `SPEC_KITTY_ENABLE_SAAS_SYNC` is absent by default via a tiny probe test or by inspecting `os.environ` in a scratch check.

### T012 — Add `sync_enabled` / `sync_disabled` fixtures + migrate owned clusters

**Steps**
1. In `tests/conftest.py`, add two fixtures:
   - `sync_enabled` — sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (and clears any disable/minimal-import var) for the test, at call-time.
   - `sync_disabled` — ensures sync is inactive for the test.
   Both must preserve the `sync_module.<name>` late-bind seam (C-006) — set env, do not monkeypatch the predicate.
2. Migrate the non-sync flag-consumers in `tests/auth/**`, `tests/readiness/**`, `tests/saas/**` (per BINDING item 9's cluster counts: auth ~4, readiness ~2, saas ~2) onto the `sync_enabled` fixture so they keep working when the default flips. These read the flag but got NO skipif — without the fixture they silently change or red.
3. For the out-of-map clusters (see boundary note), apply the same `sync_enabled` migration with a one-line rationale per file. Keep the 20 `sync_module.` late-bind co-gate consumers working via the fixture.

**Files**: `tests/conftest.py`, `tests/auth/**`, `tests/readiness/**`, `tests/saas/**` (+ documented out-of-map edits).

**Validation**: `.venv/bin/python -m pytest tests/auth tests/readiness tests/saas -q` green under the new default-off posture (they pull `sync_enabled` where they need the flag). Spot-check one `sync_module.` co-gate consumer still passes.

### T013 — CI opt-in via env var on the sync step

**Steps**
1. In `.github/workflows/ci-quality.yml`, on the `fast-tests-sync` step (~:1135, within the job at ~:1108), add:
   ```yaml
   env:
     SPEC_KITTY_ENABLE_SAAS_SYNC: "1"
   ```
   This is the collection-time opt-in (BINDING item 8) — a fixture cannot do this.
2. Ensure any opt-in job/step has `if: github.event_name == 'push'` so the collection-completeness gate counts it (NFR-003 — every sync test file stays selected by a push-path job).

**Files**: `.github/workflows/ci-quality.yml`.

**Validation**: YAML lints/parses; the `fast-tests-sync` step carries the env var; the push-guard is present so completeness counts it. (CI itself validates on push — do not attempt a full local CI run.)

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP04` allocates the execution worktree from the computed lane in `lanes.json`.
- WP04 gates the test WPs (WP05 depends on WP04). After WP04, verify the suite default-off actually skips one sync module before the WP05 bulk rollout.

## Test Strategy

- **Test-first / red-first (DIR-034)**: this WP's "red" is behavioral — before T011, `SPEC_KITTY_ENABLE_SAAS_SYNC` is forced on; after, it is off by default. Confirm with a probe. The owned-cluster migration tests must stay green across the flip.
- **Critical ordering**: after WP04 lands, verify a single sync module skips on the default path (coordination point) before WP05 rolls out en masse.
- **ruff + mypy clean** for any Python touched (fixtures). YAML must be valid.
- **Targeted pytest only**; never the full suite. **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`; use the new `sync_enabled` fixture (or `SPEC_KITTY_ENABLE_SAAS_SYNC=1`) to exercise the opt-in path.
- Do NOT add skipif to sync test modules here — that is WP05. WP04 only flips the default and provides the fixtures + CI opt-in.

## Definition of Done

- Conftest `:223` setdefault and `:427` autouse inverted to default-OFF (**FR-010**).
- `sync_enabled` / `sync_disabled` fixtures added, preserving the late-bind seam (C-006); owned clusters (auth/readiness/saas) migrated; out-of-map consumers migrated with rationale (**FR-010**, BINDING item 9).
- `fast-tests-sync` CI step carries `SPEC_KITTY_ENABLE_SAAS_SYNC: "1"` with a push-guard so completeness counts it (**FR-010/NFR-003**, BINDING item 8).
- ruff + mypy clean; owned-cluster tests green under default-off.

## Risks

| Risk | Mitigation |
|------|------------|
| Using a fixture for collection-time opt-in (fails — #3213) | CI env var on the step, not a fixture (BINDING item 8). |
| ~60 non-sync flag-consumers silently red when default flips | Migrate them onto `sync_enabled`; 20 co-gate consumers kept working via the fixture (BINDING item 9). |
| Editing files owned by other WPs | Stay within owned globs; treat the rest as documented out-of-map edits with per-file rationale; never touch another WP's owned files. |
| Completeness gate drops sync files if opt-in job is PR-only | Push-guard (`github.event_name=='push'`) so it counts (NFR-003). |
| Fixture monkeypatches the predicate and breaks late-bind | Set env in the fixture, don't patch `sync_active` (C-006). |

## Reviewer Guidance

- Confirm the conftest no longer forces `SPEC_KITTY_ENABLE_SAAS_SYNC` on by default (both :223 and :427).
- Confirm `sync_enabled`/`sync_disabled` set env rather than patching the predicate (late-bind preserved).
- Confirm the CI opt-in is an env var on the step with a push-guard — not a fixture.
- Confirm out-of-map fixture edits each carry a one-line rationale and touch no other WP's owned files.
- Confirm no skipif was added to sync modules here (that is WP05).
