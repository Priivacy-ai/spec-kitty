# Pre-Spec Research Basis — #2009 + #2016 + one bounded merge.py extract

**Date:** 2026-06-18 · 4-agent profile-loaded squad (debugger-debbie / architect-alphonso / paula-patterns / python-pedro), all findings live-verified by the orchestrator against current HEAD. Raw data for the spec — nothing committed.

---

## Verdict in one line

All three items are **structurally coherent as one "governed-state-surface" mission**: #2016 (coord-read identity) and the chosen merge extract (baseline-commit state surface) are both *mission-state-surface ownership*; #2009 (charter freshness) is *read-vs-write-path discipline* on a second governed surface. Same anti-pattern family as epic #1868: *name proposes, authority disposes — adopt the one canonical seam, don't re-derive.*

---

## 1. #2016 — Orchestrator coord-read (ADOPTION GAP, live-red confirmed)

**Live evidence:** `test_issue_1615_1616_1617_1618.py::TestIssue1616OrchestratorApiCoordRead::test_coord_path_returned_when_coord_exists` is RED on HEAD (returns `None`, expects the coord dir). Fixture `mkdir`s an *empty* coord worktree dir — **no meta.json anywhere** (coord-only-with-tail-slug topology).

**Root cause** (`orchestrator_api/commands.py::_resolve_mission_dir`, ~:275-331): it reimplemented mid8 resolution with **only the strict tier-2 `resolve_mid8`**. On a coord-only fixture: `_read_primary_meta → (None, False)` → `resolve_mid8(slug, None)` declines → `""` → M5 fail-closed guard doesn't fire (`declares_coordination=False`) → `resolve_mission_read_path(root, slug, "")` skips the coord branch (`if mid8:`) → `None`.

**Divergence resolved (Alphonso vs Debbie):** Alphonso said "read the coord surface's own meta"; Debbie proved that is **not viable** — the coord worktree mission dir canonically carries no meta.json (`coordination_branch` lives in primary). Both agree on the **seam**: adopt the canonical `coordination/surface_resolver.py::_coord_mid8` 3-tier cascade (`meta.mid8` → `resolve_mid8(meta.mission_id)` → **`mid8_from_slug(slug)`**). The **operative tier for this topology is tier-3 `mid8_from_slug`** — verified live: `mid8_from_slug("my-feature-01KT3YBD") → "01KT3YBD"` composes the exact expected coord path; `resolve_mid8(…,None) → ""`.

**Fix surface:** route `_resolve_mission_dir`'s mid8 derivation through the one sanctioned `_coord_mid8`-style cascade ending in `mid8_from_slug` (removes the parallel strict-only reimplementation — directive-001 boundary). Preserve the M5 fail-closed raise for the genuinely-unresolvable case (no tail, no declared id). **Banned:** seeding a fake primary meta in the fixture; empty-mid8 seed; `[:8]` slice. Settle in spec: *coord-only-with-tail-slug is a supported topology.*

---

## 2. #2009 [2007/C2] — Charter status/sync/preflight coherence

C2 is a **cluster**, not just the DRG XOR. Live-verified facet inventory:

| Facet | HEAD status | Action |
|---|---|---|
| C2-a status write side-effects (`ensure_charter_bundle_fresh`/`generate_all` in read path) | **ALREADY FIXED** (`f892894e2`, read path pure) | verify-don't-redo; add a guard test |
| C2-b `charter status --json` traceback — non-JSON-safe `datetime` (`_status_collectors.py:73-77` `last_sync` → `status.py:74` `json.dumps` no `default=str`) | **STILL LIVE** (TypeError reproduced) | **FIX** (JSON-safe serialization) |
| C2-c `entity_pages: merged DRG not found` warning during status | no longer emitted from status; advisory `logger.warning` | verify no other read surface calls `generate_all`; keep non-blocking |
| C2-d hash unification (sync/status/freshness all → `charter.hasher.hash_content`) | **ALREADY UNIFIED** | add regression test asserting the 3 paths agree |
| C2-e `charter sync --json` `noop`-despite-stale → `--force` worked | needs live repro (likely stored-hash drift vs bundle `metadata.yaml`) | repro first, couple to C2-d test |
| C2-f DRG XOR `invalid` self-heals **only reactively** | **STILL LIVE** (structural) | **FIX** (structural — below) |

**XOR `invalid` structural model:** `built_in_only=true ∧ project graph.yaml present` → `computer.py:345-357` returns terminal `invalid`; preflight `_PASS_STATES` (runner.py:60) excludes it → **blocks** preflight/implement. Reachable via interrupted synthesize, or a git checkout/merge/stash-pop restoring a stale graph.yaml (manifest+graph have independent git lifecycles). Self-heal lives at two disjoint sites (`computer.py:350` text + `_fresh_doctrine.py:119` unlink) and only fires on next `synthesize`; preflight auto-refresh skips dirty trees so `invalid` surfaces unresolved.

**Structural fix (make `invalid` unreachable, not self-healing):** the manifest is declared authority (#083 model). A graph.yaml the manifest disowns is **residue, not contradiction** → treat `built_in_only ∧ graph present` as a **read-time normalization**: reader authoritatively reports `built_in_only` + emits a non-blocking "stale graph residue" diagnostic, instead of terminal `invalid`. Pair with a **producer-side guarantee**: consolidate the two parallel unlink sites (`apply_post_condition` + `_fresh_doctrine.py:119`) into one shared helper any `built_in_only`-writer calls. Net: `invalid` block becomes impossible to reach; dup unlink collapses to one seam. (Same emit-don't-block / one-canonical-seam pattern as #2016.)

**Scope note:** #2009 stays charter-runtime layering hygiene — **orthogonal to the read-path SSOT** (#2007 item 4 keeps charter freshness separate from the naming rider). No new resolver; status stays a read-only consumer; **banned:** status calling `sync --force` internally or owning a second hash computation.

---

## 3. Bounded merge.py extract — RECOMMEND: Cluster F (baseline-commit state surface)

**Alphonso + Paula independently converged on the same cut.**

| | |
|---|---|
| **Functions** | `BaselineMergeCommitError` (~180), `_record_baseline_merge_commit` (~1678), `_recorded_baseline_from_working_meta` (~1756), `_read_committed_meta_json` (~1768), `_assert_baseline_merge_commit_on_target` (~1803) |
| **Target** | new `src/specify_cli/merge/baseline.py`; re-export `record_baseline_merge_commit` / `assert_baseline_merge_commit_on_target` / `BaselineMergeCommitError` via `merge/__init__.py` |
| **LOC** | ~204 (3460 → ~3256) |
| **Coupling** | **Lowest in the file** — zero `console`, zero `typer.Exit`; deps only `load_meta`/`write_meta`/`run_command`/`json`/`logger`. No cycle (`merge/` never imports `cli.commands.merge`). |
| **Test net** | already imported by name in 6+ suites (`tests/specify_cli/merge/test_1827_baseline_regression.py`, `tests/merge/test_merge_done_recording.py`, …) — import-redirect only, behavior-preserving |
| **Thematic fit** | `baseline_merge_commit` is a `meta.json` mission-state-surface field consumed by `review --mode post-merge` (`review/_mode.py`). Extracting gives the writer a named home facing the existing reader — coherent with #2009/#2016's governed-state-surface theme. |

**Fallback (only if PO wants max CC reduction over theme):** Cluster E mission_number bake (~354 LOC) — bigger win but widens the mission's theme and touches worktree lifecycle/global-lock. **Rejected for this mission.**

**Explicitly NOT this mission (Pedro's "mandatory" mega-split):** `_run_lane_based_merge[_locked]` (S3776 164/129) is the eventual `merge/executor.py` decomposition — high-risk, far beyond a *bounded* extract. The baseline extract trims a few calls out of `_locked` but does not (and should not try to) collapse those mega-functions here.

---

## 4. Sonar / boy-scout (python-pedro) — FOLD-NOW only what the edits disturb

**FOLD-NOW (on the edit path):**
- `merge.py` S1192 `"meta.json"` ×6 → hoist `META_JSON` constant **in the moved baseline.py code**.
- `orchestrator_api/commands.py` `_fail()` (~:221) typed `-> None` but always raises → retype `-> NoReturn`; that makes the two `raise # unreachable` lines (S5747 at :367/:370) provably dead/deletable. Clean typing fix on the **#2016 touch file**.
- `merge.py:845` `S2083` **BLOCKER** — this is the *canonical-seams branch's own* path-trust guard (`assert_safe_path_segment` + `ensure_within_any` IS the mitigation). **Code is correct → resolve as Sonar UI hotspot review with rationale in the PR body, NOT a code change.**

**ADJACENT-OPTIONAL (fold if the file is already open):**
- `charter_runtime/freshness/computer.py` S1192 `"spec-kitty charter sync"` ×6 / `"spec-kitty charter synthesize"` ×4 → hoist constants **if #2009 edits computer.py** (it will).
- `_fresh_doctrine.py:96` / `merge/state.py:146` `.kittify` literal → check `core.paths` for an existing canonical constant before adding a local one.
- `computer.py:324` `_compute_synthesized_drg` S3776=22 → only refactor if the #2009 change lands in that function (it does — fold a small helper extraction).

**OUT-OF-SCOPE (defer):** the merge mega-functions S3776, `merge/conflict_resolver.py`/`workspace.py`/`ordering.py` sibling cosmetics, `commands.py:175` load-bearing `except SystemExit: raise`. All present `# noqa`/`# type: ignore` are justified/load-bearing — **do not strip.**

---

## Proposed scope envelope (3 goals)

- **Goal A (#2016):** adopt the `_coord_mid8` cascade in `_resolve_mission_dir`; turn the red regression green with a topology-true coord-only fixture; preserve M5 fail-closed. + FOLD `_fail -> NoReturn` (S5747).
- **Goal B (#2009):** (B1) JSON-safe `charter status` serialization [C2-b live]; (B2) structural XOR downgrade `invalid`→read-time-normalization + consolidate dup unlink to one helper [C2-f live]; (B3) regression tests pinning hash-unification [C2-d] + status side-effect-free [C2-a]; (B4) live-repro C2-e then fix-or-document. + FOLD charter literal constants.
- **Goal C (extract):** relocate Cluster F → `merge/baseline.py`, behavior-preserving, re-export for back-compat. + FOLD `META_JSON` constant.

**Discipline (binding):** TDD-first; live-repro before "fixed" (C2-e especially); topology-true fixtures (full 26-char ULID, real coord paths); behavior-preserving for the extract (pure relocation + import redirect); structural-not-reactive for #2009; ruff+mypy clean ≤15 no suppressions; no version prescription. Advances epic #1868. Tickets: #2009 (C2), #2016, + the bounded-extract noted under the merge-decomposition theme.

---

## 5. Goal D (FOLD-IN, operator-flagged) — green main: the un-masked architectural gate is RED

**Live evidence:** CI Quality run **27736269610** on `upstream/main` @ `9f98d89fe` (the canonical-seams merge) — `integration-tests-core-misc (architectural)` shard FAILED. Reproduced locally. Root cause is **self-inflicted by design**: canonical-seams shipped FR-007 (un-mask the architectural gate) + FR-008 (re-key ratchets). FR-007 only takes effect *after* merge, so the mission's own gate could not catch offenders introduced/exposed in the same merge. First post-merge main run goes red. Failure cluster:

| Failing test | Nature | Fix |
|---|---|---|
| `test_pytest_marker_correctness.py::test_subprocess_git_users_must_carry_git_repo_marker` | **REAL, mechanical** — canonical-seams' new `tests/specify_cli/missions/test_read_path_resolver_validation.py` invokes git via subprocess but lacks `git_repo` marker | add `git_repo` to its `pytestmark` |
| `…::test_fast_marker_must_not_apply_to_subprocess_users` | **REAL, mechanical** — same file carries `fast` but uses subprocess | drop `pytest.mark.fast` |
| `test_no_worktree_name_guess.py::{test_allow_list_entries_are_real_and_benign, test_name_compose_offenders_match_pinned_baseline, test_shortid_allow_list_entries_are_real}` | FR-008 re-keyed ratchets — composite keys/baselines stale against the exact main tree (env-sensitive: CI py3.12+installed+parallel vs local py3.11 editable) | reconcile the AST/qualname baselines to main; verify under CI conditions |
| `test_no_worktree_name_guess.py::test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils` | **mission-diff-scoped** NFR-001 test — self-referential to the canonical-seams diff; flags `status/{emit,lifecycle_events,store,work_package_lifecycle}.py` | this test should be **neutralized/removed post-merge** — it pins a one-time mission diff, not a durable invariant; it does not belong on main |

**Thematic fit:** Goal D is the **same guard-capability theme as canonical-seams Goal C** — gate-coherence/ratchet hygiene. It belongs in this mission. **Lesson (memory-worthy):** a gate-un-masking change cannot self-validate; pair every FR-007-style un-mask with a *pre-merge* full-architectural dry-run on the mission branch, and never ship a mission-diff-scoped assertion to main.

**Sequencing tension:** main is RED now. The mechanical half (markers + neutralize the mission-scoped NFR test) is a ~10-line hotfix that greens main immediately; the ratchet-baseline reconcile needs CI-condition reproduction. Decision for operator: fast green-main hotfix PR first, vs fold the whole repair into mission WP01.
