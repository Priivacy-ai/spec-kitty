# Mission Specification: Governed-State-Surface Coherence

**Mission ID:** 01KVCGQCTNN5K5YD2YEZ8F2DA6 · **mid8:** 01KVCGQC
**Branch:** `feat/governed-state-surface-coherence` → PR → `main`
**Mission type:** software-dev · **Epic:** #1868 (bind authority to type/owner — "name proposes, authority disposes")
**Created:** 2026-06-18

---

## Overview / Context

Three independent subsystems each own a **governed-state surface** — a piece of state that a canonical seam already knows how to resolve authoritatively — yet each re-derives that state by hand, divergently from the canonical authority. The drift produces two observable failure classes:

1. **Wrong-surface reads.** The orchestrator's mission-directory resolver reimplements mission-identity (`mid8`) derivation with only a partial cascade, so a mission that exists *only* as a coordination worktree resolves to nothing (`None`) instead of its real status surface (#2016, live-red regression test confirmed).
2. **Blocking false-positives.** The charter freshness computer treats a recoverable stale-artifact condition (a disowned `graph.yaml` residue) as a terminal `invalid` state that blocks preflight/implement, and self-heals only reactively on the next `synthesize`; a sibling read path (`charter status --json`) crashes on a non-JSON-safe value (#2009 / #2007-C2, live-reproduced).

A fourth, related surface is the **merge-baseline recording** logic: a cohesive ~200-LOC "record and verify the post-merge baseline commit" unit buried inside a 3 460-LOC command module. It is the lowest-coupling, most test-anchored extraction candidate and is thematically the same *mission-state-surface ownership* concern as #2016 — so this mission also relocates it to a named module (behavior-preserving).

Finally, the architectural CI gate went **red on `main`** the moment a prior mission (canonical-seams #2024) un-masked it: the un-masking only takes effect *after* merge, so the gate could not catch offenders introduced in its own merge. This mission repairs that gate **first** (WP01) so the rest of the work lands on a green base.

This mission **binds each surface to its existing canonical authority** (no new resolvers, no new shadow paths), makes the freshness false-positive structurally unreachable, extracts the merge-baseline unit, and restores a green architectural gate. It advances epic #1868: adopt the one canonical seam; do not re-derive.

Grounded in a 4-agent profile-loaded pre-spec research squad, all findings live-verified — see `research/00-prespec-synthesis.md`.

## Domain Language

| Canonical term | Meaning | Avoid |
|---|---|---|
| **Governed-state surface** | State whose authoritative resolution is owned by a single canonical seam (identity, freshness, baseline). | "the data" |
| **Coord-only-with-tail-slug topology** | A mission present only as a coordination worktree (no primary `meta.json`), whose canonical `<slug>-<mid8>` directory name embeds the disambiguator. A **supported** topology. | "broken mission", "orphan" |
| **`_coord_mid8` cascade** | The canonical 3-tier mid8 resolution: `meta.mid8` → `resolve_mid8(meta.mission_id)` → `mid8_from_slug(slug)`, fail-closed if all exhausted. | ad-hoc `[:8]` slice |
| **Stale graph residue** | A project `graph.yaml` present while the synthesis manifest declares `built_in_only=true`; the manifest disowns it → it is residue, not a contradiction. | "invalid state" |
| **Read-time normalization** | A reader authoritatively reporting the declared state and emitting a non-blocking diagnostic for residue, rather than returning a terminal blocking error. | "self-heal", "auto-fix" |
| **Mission-diff-scoped test** | A test that pins a one-time mission's diff (not a durable invariant); must not persist on `main`. | "regression test" |

## User Scenarios & Testing

**Primary actor:** an automation/orchestrator agent (and operators) reading mission status and running charter/merge workflows.

1. **Coord-only status read (#2016).** *Trigger:* the orchestrator resolves the status directory for a mission that exists only as a coordination worktree. *Today:* returns `None` → the caller flattens to `MISSION_NOT_FOUND` or reads stale primary. *Desired:* returns the coordination status directory by adopting the canonical mid8 cascade; a genuinely-unresolvable handle still fails closed with the typed read-path error.
2. **Charter status JSON (#2009 C2-b).** *Trigger:* `charter status --json` on a project whose bundle `metadata.yaml` carries an unquoted ISO datetime. *Today:* `TypeError: Object of type datetime is not JSON serializable` traceback. *Desired:* valid JSON output (serialized safely), no traceback.
3. **Charter preflight with stale graph residue (#2009 C2-f).** *Trigger:* preflight/implement on a worktree where the manifest says `built_in_only=true` but a stray `graph.yaml` remains (e.g. after a branch checkout). *Today:* terminal `invalid` blocks preflight; recovery requires a manual `synthesize` (and auto-refresh skips dirty trees). *Desired:* preflight passes, reporting `built_in_only` with a non-blocking "stale graph residue" diagnostic.
4. **Merge baseline ownership (extract).** *Trigger:* a maintainer reads/edits the post-merge baseline record/verify logic. *Today:* it is buried in a 3 460-LOC command file. *Desired:* it lives in a named `merge/baseline.py`; all existing call sites and tests bind unchanged.
5. **Green architectural gate (Goal D).** *Trigger:* CI runs the full `tests/architectural/**` shard on `main`. *Today:* red (marker violation + a mission-diff-scoped test that escaped + stale ratchet baselines). *Desired:* green under real CI conditions.

**Main exception / edge:** for #2016, a handle with no declared identity **and** no canonical tail must still fail closed (not fabricate a path). For #2009, the residue downgrade must apply **only** when the manifest authoritatively declares `built_in_only` (the manifest is the authority); a genuine synthesized-DRG inconsistency outside that declaration is not downgraded.

## Functional Requirements

### Goal A — #2016 orchestrator coord-read (adoption gap)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `orchestrator_api/commands.py::_resolve_mission_dir` MUST resolve `mid8` through the canonical coord-aware cascade (`meta.mid8` → `resolve_mid8(meta.mission_id)` → `mid8_from_slug(slug)`) used by `coordination/surface_resolver.py::_coord_mid8`, so a coord-only-with-tail-slug mission resolves to its coordination status directory. | Draft |
| FR-002 | The orchestrator MUST consolidate onto the one sanctioned mid8 cascade — the parallel strict-only `resolve_mid8`-only reimplementation MUST be removed (no second identity-derivation path remains in the orchestrator). | Draft |
| FR-003 | The fail-closed behavior MUST be preserved for a genuinely-unresolvable handle (no declared identity AND no canonical `<slug>-<mid8>` tail): the resolver raises the typed read-path error rather than fabricating a path or reading a stale primary surface. | Draft |
| FR-004 | (Fold-now) `orchestrator_api/commands.py::_fail` MUST be retyped to `NoReturn`; the two now-provably-dead `raise # unreachable` lines flagged by Sonar S5747 MUST be deleted. | Draft |

### Goal B — #2009 charter status/sync/preflight coherence

| ID | Requirement | Status |
|----|-------------|--------|
| FR-005 | `charter status --json` MUST produce valid JSON when the bundle `metadata.yaml` carries a non-JSON-safe value (e.g. an unquoted ISO datetime parsed to a `datetime`); the read path MUST serialize safely (no traceback). | Draft |
| FR-006 | The charter freshness computer MUST treat `built_in_only=true` ∧ a present project `graph.yaml` as **read-time residue**: it reports the authoritative `built_in_only` state and emits a non-blocking "stale graph residue" diagnostic, instead of returning the terminal `invalid` state that excludes preflight pass. The blocking `invalid` branch for this specific condition becomes unreachable. | Draft |
| FR-007 | The two parallel `graph.yaml` unlink sites (`charter/synthesizer/project_drg.py::apply_post_condition` and `cli/commands/charter/_fresh_doctrine.py`) MUST be consolidated into ONE shared helper that any `built_in_only`-writer calls (eliminating the duplicated unlink). | Draft |
| FR-008 | Regression tests MUST pin the already-landed C2 fixes against re-drift: (a) the `charter status` read path is side-effect-free (no `ensure_charter_bundle_fresh` / `generate_all` call); (b) the freshness hash is unified — `sync`, `status`, and the freshness computer agree via the one `charter.hasher.hash_content` path. | Draft |
| FR-009 | The `charter sync --json` "noop-despite-stale" report (C2-e) MUST be reproduced live before any code change; if reproduced, fix the stored-hash drift (couple to FR-008's unification test); if not reproducible, document the closed/non-reproducible verdict with evidence. | Draft |

### Goal C — one bounded merge.py extract (behavior-preserving)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-010 | The `baseline_merge_commit` record/verify cluster (`BaselineMergeCommitError`, `_record_baseline_merge_commit`, `_recorded_baseline_from_working_meta`, `_read_committed_meta_json`, `_assert_baseline_merge_commit_on_target`) MUST be relocated from `cli/commands/merge.py` to a new `src/specify_cli/merge/baseline.py`, re-exporting `record_baseline_merge_commit`, `assert_baseline_merge_commit_on_target`, and `BaselineMergeCommitError` (via `merge/__init__.py`) so existing call sites and the 6+ baseline test suites bind unchanged. The move is pure relocation + import redirect — no logic change. | Draft |

### Goal D — green main: repair the un-masked architectural gate (WP01)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-011 | `tests/specify_cli/missions/test_read_path_resolver_validation.py` MUST carry correct pytest markers: add `git_repo` (it invokes git via subprocess) and remove `fast` — satisfying `test_pytest_marker_correctness` Rules 1 & 2. | Draft |
| FR-012 | `tests/architectural/test_no_worktree_name_guess.py::test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils` — a mission-diff-scoped assertion that pins the canonical-seams one-time diff, not a durable invariant — MUST be removed/neutralized so it does not fail on `main`. | Draft |
| FR-013 | The FR-008-era re-keyed ratchet baselines in `tests/architectural/test_no_worktree_name_guess.py` (`test_allow_list_entries_are_real_and_benign`, `test_name_compose_offenders_match_pinned_baseline`, `test_shortid_allow_list_entries_are_real`) MUST be reconciled to the current `main` tree and verified GREEN under real CI conditions (Python 3.12 + installed package + parallel), not merely local. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure |
|----|-------------|---------------------|
| NFR-001 | Goal C is behavior-preserving. | No trusted-root, topology, rollback, or logic change; the baseline functions' observable behavior and public names are identical; all pre-existing baseline tests pass unchanged. |
| NFR-002 | Fixes are proven by live repro, not static reading. | A failing-first (red) test exists for each live defect (FR-001, FR-005, FR-006) before its fix; FR-009 requires a live repro attempt with recorded outcome. |
| NFR-003 | Goal D fixes are verified under real CI conditions. | The architectural shard is observed GREEN on CI (Python 3.12 + installed + `-n auto --dist loadfile`), not only local Python 3.11 editable. |
| NFR-004 | Code-health gates hold. | `ruff` + `mypy` clean on new/touched code; cyclomatic/cognitive complexity ≤ 15; zero new `# noqa` / `# type: ignore` / Sonar suppressions. |
| NFR-005 | Topology-true, realistic fixtures. | #2016 fixtures use full 26-char ULIDs and real coord-worktree paths; no short/fabricated slugs; no fake-primary-meta shortcut. |
| NFR-006 | Charter status stays a read-only consumer. | The `status` path invokes no mutator (`ensure_charter_bundle_fresh`, `generate_all`, `sync`) and computes no second freshness hash. |

## Constraints

| ID | Constraint |
|----|------------|
| C-001 | NON-GOAL: do NOT seed a fake primary `meta.json` in the #2016 regression fixture — the coord-only-with-tail-slug topology is real and must be exercised as-is. |
| C-002 | NON-GOAL: the `_run_lane_based_merge[_locked]` mega-function split (Sonar S3776 164/129) is the eventual `merge/executor.py` decomposition — explicitly OUT of scope here. The Cluster E `mission_number` bake extraction is also out of scope (widens theme). |
| C-003 | NON-GOAL: #2009 stays charter-runtime layering hygiene, orthogonal to the read-path SSOT (#2007 item 4). No new resolver; `status` MUST NOT call `sync --force` internally or own a second hash computation. |
| C-004 | `cli/commands/merge.py` Sonar S2083 BLOCKER (~:845) is the canonical-seams branch's own path-trust guard (`assert_safe_path_segment` + `ensure_within_any` IS the mitigation). It is correct code → resolve as a Sonar UI hotspot review with rationale in the PR body, NOT a code change. The PR body MUST call this out. |
| C-005 | No version prescription (patch/minor numbers are a PO/release-time call). |
| C-006 | Present `# noqa` / `# type: ignore` in touched files are justified/load-bearing — do NOT strip them. |
| C-007 | Operator decision: Goal D (green main) lands as WP01; the rest of the mission builds on the greened base. Main stays red until WP01 merges (accepted: one mission, one PR trail). |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | The #2016 regression test `test_coord_path_returned_when_coord_exists` passes with a topology-true coord-only fixture (no fake primary meta), and `test_none_returned_when_mission_not_found` still passes (fail-closed preserved). |
| SC-002 | `charter status --json` returns valid JSON (exit 0, parseable) on a project whose `metadata.yaml` has an unquoted datetime — no traceback. |
| SC-003 | A fixture with `built_in_only=true` + a stray `graph.yaml` yields preflight PASS reporting `built_in_only` plus a non-blocking residue diagnostic; no terminal `invalid`. |
| SC-004 | `record_baseline_merge_commit` / `assert_baseline_merge_commit_on_target` / `BaselineMergeCommitError` are importable from both `specify_cli.merge` and the legacy `merge.py` surface; all pre-existing baseline test suites pass unchanged. |
| SC-005 | The CI `integration-tests-core-misc (architectural)` shard is GREEN on the mission branch under real CI conditions. |
| SC-006 | `ruff` + `mypy` clean, complexity ≤ 15, zero new suppressions, across all touched code. |
| SC-007 | Every addressed GitHub issue has an `issue-matrix.md` verdict and a tracker claim/comment naming this mission. |

## Key Entities

- **Mission identity** (`mission_id` / `mid8` / `mission_slug`) — resolved via the `_coord_mid8` cascade.
- **Charter freshness state** (`fresh` / `built_in_only` / `skipped` / `invalid`) — `invalid` becomes unreachable for the residue condition.
- **Synthesis manifest** (`built_in_only` flag) — the declared authority over `graph.yaml` presence.
- **Baseline merge commit record** (`meta.json.baseline_merge_commit`) — written by merge, read by `review --mode post-merge`.

## Assumptions

- The canonical `_coord_mid8` cascade (incl. its `mid8_from_slug` tier-3) is the sanctioned, already-shipped resolution authority; adopting it is the intended consolidation, not a new mechanism.
- C2-a (status side-effects) and C2-d (hash unification) already landed in-tree (commit `f892894e2`); this mission pins them with tests rather than re-implementing.
- The architectural-shard divergence between local (py3.11 editable) and CI (py3.12 installed parallel) is environmental; FR-013 reconciliation is validated on CI.

## Out of Scope / Non-Goals

- Re-routing the ~143 path-composition callers or unifying the two read primitives (that is the read-path-adoption / naming-rider work).
- The merge mega-function decomposition and the `mission_number` extraction (C-002).
- Any change to what the architectural guards *assert* (Goal D is guard-mechanism only).
- Forcing HTTPS on / otherwise altering the loopback-safe and path-trust hotspots (C-004).

## Issue Matrix (tracker linkage)

| Issue | Goal | Parent / Epic | Planned verdict |
|-------|------|---------------|-----------------|
| #2016 | A — orchestrator coord-read | native sub-issue of #1868 ✅ | in-mission → fixed |
| #2009 | B — charter coherence | child of #2007 ✅ | in-mission → fixed (C2-e: live-repro → fixed or verified-non-reproducible) |
| #2027 | C — merge baseline extract | child of NEW epic #2026 ("merge.py god-module decomposition", under #1797) ✅ | in-mission → fixed |
| #2025 | D — green main | native sub-issue of #1931 ✅ (NEW; sibling residual to CLOSED #2023) | in-mission → fixed |

**Goal C tracker home (resolved 2026-06-18):** new epic **#2026** "merge.py god-module decomposition" (wired under #1797 codebase-sanitization, sibling to the doctor.py #1623 effort) with slice-1 child **#2027** for this baseline extract. The eventual mega-function split is a future slice under #2026 (out of scope here, C-002).

DO NOT use #1796 (CLOSED) or #1479 (META-TRACKER) as parents.
