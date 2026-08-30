---
work_package_id: WP08
title: Docs + CHANGELOG + doctor advisory copy
dependencies:
- WP03
- WP07
requirement_refs:
- FR-017
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: docs/
create_intent: []
execution_mode: code_change
owned_files:
- docs/api/environment-variables.md
- docs/api/cli-commands.md
- docs/operations/sync-daemon-orphan-cleanup.md
- docs/api/skills/spk-run-implement-review.md
- docs/plans/code-quality/sync-env-census.md
- CHANGELOG.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Living-documentation for the new opt-in default + breaking-change discoverability. Reword the docs that describe sync/daemon as running by default to the opt-in posture, fix the #2801 env in the implement-review skill doc, note the egress-consent ADR, add the CHANGELOG breaking-change note, and verify the doctor advisory copy (implemented in WP02) matches the docs.

- **T021** — reword sync-default-on → opt-in across the owned docs; fix `spk-run-implement-review.md:44-45`; update the sync-env-census companion; note the egress-consent ADR.
- **T022** — CHANGELOG breaking-change note; verify the WP02 doctor advisory copy matches.

## Context

Authoritative sources:

- **plan.md → BINDING** item 12 — the doc additions the `*sync*` glob missed: `docs/api/skills/spk-run-implement-review.md:44-45` (documents `SPEC_KITTY_SYNC_DISABLE` as the pre-review-gate disable — #2801 makes it wrong → `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`); `docs/plans/code-quality/sync-env-census.md` (companion to the env-census guard); the egress-consent ADR (filename lacks "sync" so the glob misses it).
- **spec.md** — FR-017 (living-documentation updates), FR-018 (CHANGELOG breaking-change note + doctor advisory), C-001/FR-016 (no new *sync* flag — the pre-review flag is a gate flag).
- **Terminology Canon** — "Mission" not "feature"; run the terminology guard before finishing.

**Ordering**: WP08 depends on WP03 (behavior settled) and WP07 (guards/goldens settled). Docs land last so they describe the final shipped behavior.

**Doc-by-doc intent** (owned files):

| Doc | Change | Source req |
|-----|--------|-----------|
| `docs/api/environment-variables.md` | `ENABLE_SAAS_SYNC` = opt-in; `SYNC_DISABLE`/`SYNC_MINIMAL_IMPORT` = force-off (disable wins); new `PRE_REVIEW_GATE_DISABLE` as a distinct gate flag; truth table | FR-017, FR-016 |
| `docs/api/cli-commands.md` | "runs by default" → "inactive by default; opt-in"; `sync` command still registered, no-ops when unarmed | FR-017, C-002 |
| `docs/operations/sync-daemon-orphan-cleanup.md` | no implicit spawn by default; keep orphaned-daemon cleanup hint | FR-017, FR-018 |
| `docs/api/skills/spk-run-implement-review.md:44-45` | `SPEC_KITTY_SYNC_DISABLE` → `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` for the pre-review gate | BINDING item 12 |
| `docs/plans/code-quality/sync-env-census.md` | companion to the WP07 env-census update (new literal) | BINDING item 12 |
| `CHANGELOG.md` | breaking-change note (sync opt-in) + folded #3470/#2801 | FR-018 |

**Doctor advisory copy**: the advisory string is IMPLEMENTED in WP02 (`sync_doctor_core.py`, FR-018 code half). WP08's job is to (a) document the opt-in posture and (b) VERIFY the advisory copy matches the docs — not to re-implement it. If the copy drifts, note it for a WP02 follow-up rather than editing `sync_doctor_core.py` (not owned here).

## Per-Subtask Guidance

### T021 — Reword docs to the opt-in posture

**Steps**
1. `docs/api/environment-variables.md` — document `SPEC_KITTY_ENABLE_SAAS_SYNC` as the opt-in-to-enable flag; `SPEC_KITTY_SYNC_DISABLE` / `SPEC_KITTY_SYNC_MINIMAL_IMPORT` as force-off (disable wins); add the new `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` as a distinct **gate** flag (not a sync flag — C-001/FR-016). Reflect the truth table (`sync_active = E AND NOT (D OR M)`).
2. `docs/api/cli-commands.md` — reword any "sync/daemon runs by default" language to "inactive by default; opt-in via `SPEC_KITTY_ENABLE_SAAS_SYNC=1`". The `sync` command stays registered; it reports inactive / no-ops when not armed (C-002).
3. `docs/operations/sync-daemon-orphan-cleanup.md` — reflect that implicit spawn no longer happens by default; add/keep the orphaned-daemon cleanup hint (deactivation does not kill a daemon from a prior opted-in session — spec Edge Cases).
4. `docs/api/skills/spk-run-implement-review.md:44-45` — replace `SPEC_KITTY_SYNC_DISABLE` with `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` for the pre-review-gate disable (#2801 makes the old text wrong).
5. `docs/plans/code-quality/sync-env-census.md` — update the companion to the env-census guard (WP07 T019 added `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` to the frozen set).
6. Note the **egress-consent ADR** — arming (`sync_active()`) is upstream of, and does not replace, per-project egress consent (C-007). Reference the ADR by name; the `*sync*` glob misses it because its filename lacks "sync".

**Files**: `docs/api/environment-variables.md`, `docs/api/cli-commands.md`, `docs/operations/sync-daemon-orphan-cleanup.md`, `docs/api/skills/spk-run-implement-review.md`, `docs/plans/code-quality/sync-env-census.md`.

> The FR-017 doc list is broader (sync-drain.md, manual-test-plan.md, known-friction-points.md, isolated-dev-environments.md, testing-flakiness.md, `docs/adr/3.x/*sync*`). Those outside the owned globs are handled as documented within-WP out-of-map edits with a one-line rationale each, OR flagged for a follow-up if they belong to another surface — do not silently leave a "runs by default" claim standing, and do not edit another WP's owned files.

**Validation**: `grep` the owned docs for "by default" / "runs" / "daemon starts" and confirm no stale sync-default-on claim remains; confirm `spk-run-implement-review.md:44-45` names the new gate flag.

### T022 — CHANGELOG + doctor advisory verification

**Steps**
1. `CHANGELOG.md` — add a **breaking-change** entry: sync is now opt-in via `SPEC_KITTY_ENABLE_SAAS_SYNC`; existing users who relied on default-on sync must set it. Mention the folded fixes (#3470 body-outbox traceback silenced; #2801 pre-review gate decoupled onto `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`). Follow the existing CHANGELOG format/section conventions.
2. Verify the WP02 doctor advisory copy (`sync_doctor_core.py`) matches the documented opt-in wording + orphaned-daemon cleanup hint. If it matches, note the verification; if it drifts, flag a WP02 follow-up (do not edit `sync_doctor_core.py` — not owned here).
3. Run the terminology guard mentally / actually: no forbidden terms ("feature"/"Feature" for the domain object; canonical "Mission").

**Files**: `CHANGELOG.md`.

**Validation**: `.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q` → green (no forbidden terms introduced by the docs/CHANGELOG). Confirm the CHANGELOG entry is under the right section and calls the change breaking.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP08` allocates the execution worktree from the computed lane in `lanes.json`.
- WP08 lands last (deps WP03, WP07) so docs describe the final behavior.

## Test Strategy

- Docs/CHANGELOG are prose — the binding gate is the **terminology guard** (`tests/architectural/test_no_legacy_terminology.py`), which some repo-wide checks run only in CI's `integration-tests-core-misc` job. Run it locally before finishing (≈0.1 s) — a forbidden-term regression otherwise passes local doctrine runs and only fails at CI.
- No code change here (doctor advisory is WP02) — so no ruff/mypy target beyond confirming nothing Python was touched.
- **Targeted pytest only** (the terminology guard). Never the full suite. **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`.
- Cross-check the doctor advisory copy against the docs by reading `sync_doctor_core.py` (read-only — not owned); do not edit it.

## Definition of Done

- Owned docs reworded to the opt-in default; `spk-run-implement-review.md:44-45` names `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`; sync-env-census companion updated; egress-consent ADR referenced (**FR-017**, BINDING item 12).
- CHANGELOG breaking-change note added (sync opt-in; existing users must set `SPEC_KITTY_ENABLE_SAAS_SYNC`) (**FR-018**).
- Doctor advisory copy verified to match the docs (or drift flagged for WP02) (**FR-018**).
- Terminology guard green (no forbidden terms).
- No stale "sync runs by default" claim left in the owned docs.

## Risks

| Risk | Mitigation |
|------|------------|
| Forbidden terminology slips into prose | Run `test_no_legacy_terminology.py` before finishing (CI-only otherwise). |
| Doc claims sync still runs by default somewhere | Grep the owned docs; handle out-of-map FR-017 files as documented edits or flag them — don't leave stale claims. |
| Editing `sync_doctor_core.py` (WP02-owned) | Verify copy read-only; flag drift for a WP02 follow-up, don't edit it. |
| Presenting the pre-review flag as a sync flag | Document it as a distinct gate flag (C-001/FR-016). |
| CHANGELOG entry not marked breaking | Explicitly label it breaking; explain the required opt-in for existing users. |

## Reviewer Guidance

- Confirm no owned doc still says sync/daemon runs by default; confirm the truth table / opt-in wording is present.
- Confirm `spk-run-implement-review.md:44-45` uses `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`, not `SPEC_KITTY_SYNC_DISABLE`.
- Confirm the CHANGELOG note is breaking and actionable (set `SPEC_KITTY_ENABLE_SAAS_SYNC`).
- Confirm the doctor advisory copy matches the docs (or a WP02 follow-up is flagged) and that `sync_doctor_core.py` is NOT in this WP's diff.
- Confirm the terminology guard passes.
