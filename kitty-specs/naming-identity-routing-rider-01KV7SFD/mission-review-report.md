# Mission Review Report — Naming/Identity Routing Rider (`01KV7SFD`)

**Reviewer:** senior post-merge mission reviewer (spec-kitty-mission-review discipline)
**Date:** 2026-06-16
**Mission branch:** `feat/naming-rider-3-2-1` (squash-merged; 7 WPs done)
**Baseline:** `e17572a8abb70a9e84164ca0425b8a174b69c546` (`meta.json.baseline_merge_commit`)
**Squash commit:** `f617d857a` (`feat(kitty/mission-naming-identity-routing-rider-01KV7SFD): squash merge of mission`)
**Verdict:** **PASS-WITH-NOTES** (one HIGH test-hygiene defect; routing core sound)

---

## 1. Coverage map

`git diff <baseline>..HEAD --stat` (scoped to `src/` + `tests/` + `src/doctrine/`): 32 files, +2176/−91.

| Concern | Files | WP |
|---------|-------|----|
| Seam SSOT entrypoint (demote `mid8`→`_mid8`) | `lanes/branch_naming.py` | WP01 |
| Ratchet (AST short-id detector + bypass rule) | `tests/architectural/test_no_worktree_name_guess.py` (+369) | WP02 |
| Contract-sensitive routes | `status/aggregate.py`, `dashboard/scanner.py`, `doctor.py`, `implement.py`, `worktree_allocator.py` | WP03 |
| Direct + 5 missed routes | `sparse_checkout.py`, `apply.py`, `mission_resolver.py`, `retrospective_terminus.py`, `resolution.py`, `agent/mission.py`, `agent/workflow.py`, `mission_type.py`, `retrospective/generator.py` | WP04 |
| #2000 compose-routing | `core/mission_creation.py`, `core/worktree.py` | WP05 |
| #1888 verify + #1971-tail test | `tests/.../test_validation_existence.py`, `test_locate_project_root_convergence.py` | WP06 |
| #2007 Focus A drift guard | `src/doctrine/skills/*`, `src/doctrine/missions/.../plan/prompt.md`, `test_docs_cli_reference_parity.py`, `scripts/docs/_typer_walker.py` | WP07 |
| Routed cross-WP find (status write) | `coordination/status_transition.py` | WP01 |

---

## 2. Gate Results

| Gate | Command | Exit | Result |
|------|---------|------|--------|
| 1 — Contract | `pytest tests/contract/ -q` | 0 | **PASS** (268 passed) |
| 2 — Architectural | `pytest tests/architectural/ -q` | non-zero | **FAIL** (3 failed, 382 passed) — see breakdown |
| 3 — Cross-repo E2E | sibling `spec-kitty-end-to-end-testing` | n/a | **EXCEPTION** (repo not present locally; environmental, not a code defect — not counted against verdict) |
| 4 — Issue Matrix | read `issue-matrix.md` | n/a | **PASS** (all 21 rows terminal; deferred rows name follow-ups) |

### Gate 2 failure triage (critical — 2 of 3 are mission-caused)

| Failing test | Origin | Detail |
|---|---|---|
| `test_ci_quality_path_filters::test_core_misc_shards_plus_e2e_owner_cover_legacy_selection` | **MISSION-CAUSED (HIGH)** | Collection error: `tests/specify_cli/core/test_2000_compose_routing.py` imports the deleted public `mid8` symbol → `ImportError: cannot import name 'mid8'`. See Finding H-1. |
| `test_pytest_marker_convention::test_every_test_file_declares_a_pytestmark_marker` | **MISSION-CAUSED (MEDIUM)** | 3 new mission test files declare no `pytestmark` (CI marker profiles skip them silently). See Finding M-1. |
| `test_pytest_marker_correctness::test_subprocess_git_users_must_carry_git_repo_marker` | **PRE-EXISTING** | Sole violator `tests/specify_cli/cli/commands/test_implement_base_ref.py` — untouched by this mission, last modified in `fcf9be595` (#2001, predates baseline). NOT a regression. |

**Known pre-existing (NOT counted):** `test_coord_reader_fixes.py::...test_returns_coord_path_when_coord_exists` fails identically on baseline (`#2007` read-path bug, deferred to #2010). Confirmed: test file untouched by mission.

---

## 3. FR Coverage Matrix

Testing discipline verified: byte-parity assertions use **frozen HEAD-captured literals** (e.g. `test_mid8_contract_sensitive_routing.py`, `test_branch_naming_ssot_entrypoint.py`), not `resolve_mid8(x)==resolve_mid8(x)` tautologies. Verification-by-deletion: shadow `def _mid8` in `retrospective_terminus.py` genuinely deleted.

| FR | Spec→WP→Test→Code | Status |
|----|-------------------|--------|
| FR-001 | Route bare mid8 derivations (~15 sites) → WP03/WP04 → `test_mid8_contract_sensitive_routing.py`, `test_mid8_direct_routing.py`, `test_mid8_caller_routing.py` → all 15 sites routed to `resolve_mid8` | **ADEQUATE** |
| FR-002 | No ExecutionContext-held re-derivation → WP04 → `test_mid8_direct_routing.py::test_identity_fragment_rejects_inconsistent_mid8` (constructs real fragment) | **ADEQUATE** (verification; 0 sites found, as inventoried) |
| FR-003 | Dashboard `scanner.py:438` via `resolve_mid8(...) or None` → WP03 → dashboard tests pass; `None` registry contract preserved in diff | **ADEQUATE** |
| FR-004 | New AST short-id detector + shrinking allow-list → WP02 → `test_no_worktree_name_guess.py` (self-test plants all 5 shapes; `invocation_id[:8]` not tripped) | **ADEQUATE** |
| FR-005 | #2000 composes via `mission_dir_name`/`worktree_dir_name` → WP05 → **`test_2000_compose_routing.py` DOES NOT RUN (import error)** | **PARTIAL** — code is byte-equal (verified manually, §4), but the byte-parity proof test never executes. See H-1. |
| FR-006 | #1971-tail convergence + split-brain-disproving test → WP06 → `test_locate_project_root_convergence.py` (297 lines; divergent-input Path equality under 3 conditions) | **ADEQUATE** |
| FR-007 | #1888 existence check → WP06 → `test_validation_existence.py` (5 phantom-path tests pass on HEAD, `validate_glob_matches`, no code change) | **ADEQUATE** (verify-and-close: fix pre-landed in `991162c0a`) |
| FR-008 | Byte-parity contract preservation per routed site → WP03 → each route carries `or None`/`or mission_id[:8]`/`else ""` + per-site rationale comment | **ADEQUATE** |
| FR-009 | Delete dead shadow implementations → WP01/WP04 → `retrospective_terminus.py` `def _mid8` deleted; `mid8` dropped from `__all__`; status_transition pre-derivation removed | **ADEQUATE** |
| FR-010 | `resolve_mid8` sole public mid8 door; demote `mid8`→`_mid8` → WP01 → `test_branch_naming_ssot_entrypoint.py` (250 lines; one-shot warning + reset seam preserved) | **ADEQUATE** |
| FR-011 | Repoint 15 drifted SOURCE refs → WP07 → SKILL.md + plan/prompt.md edited; SOURCE-only (no agent copies in diff) | **ADEQUATE** |
| FR-012 | Command-snippet CI guard, 3 finding codes, empty-frozenset ratchet → WP07 → `test_docs_cli_reference_parity.py` (empty frozenset, self-tests pass) | **PARTIAL** — only `unregistered-path` implemented; `unknown-flag` and `internal-as-public` NOT present. See Finding M-2. |
| FR-013 | Repoint `worktree repair` hint → `doctor workspaces --fix`; document implement/review JSON contract → WP07 | **ADEQUATE** (hint repointed; #1891 documented, code-add deferred per scope) |

---

## 4. Cross-WP Verifications (the 5 the operator wanted confirmed)

| # | Check | Result |
|---|-------|--------|
| 1 | **F-1 closed** — zero importers of public `mid8` | **CONFIRMED.** `git grep "branch_naming import"` (multi-line expanded): only `_mid8`/`resolve_mid8`/`resolve_transaction_mid8`/`mid8_from_slug` remain. `mid8` dropped from `__all__` (line 42–54); `def _mid8` is private (line 122). The WP01-found `coordination/status_transition.py` importer is clean: the `_seam_mid8` pre-derivation was **removed** and the value left `None` for `resolve_transaction_mid8` to derive (cascade `meta.mid8 → mission_id[:8]`) — **byte-equal**, a read-side route, **no #1900 coord-write-side creep**. |
| 2 | **Ratchet passes without over-allow-listing** | **CONFIRMED.** `test_no_worktree_name_guess.py` passes. Short-id allow-list = exactly **2 `doctor.py` tolerance entries** (`:3073`, `:3165`) + **2 seam homes** (`branch_naming.py`, `mission_runtime/context.py` in `_SHORTID_HOME_FILES`) + **`invocation_id[:8]` by name** (`_SHORTID_NAMED_EXCLUSIONS`). Pinned accounting comment (lines 573–579): 7 raw matches = 5 homes + 2 allow-listed = **0 unaccounted consumers**. No hidden missed routes. |
| 3 | **Byte-parity held (worktree.py:367)** | **CONFIRMED.** The `-` literal "removed" from `worktree.py` is a **false positive**: the inline `f"{strip_numeric_prefix(slug)}-{mid8(mission_id)}"` moved into `mission_dir_name(slug, mid8=resolve_mid8("", mission_id=...))`. `mission_dir_name` composes `strip_numeric_prefix(slug)+"-"+mid8`; `resolve_mid8("", mission_id=X)` == old `mid8(X)` for `len(X)>=8`. Output unchanged. The lanes/worktree/workspace test areas (329 tests) pass. |
| 4 | **#1888 verify-and-close** | **CONFIRMED.** `ownership/validation.py` is **UNCHANGED** in the diff (verify-and-close = no code change; fix pre-landed `991162c0a`). Only the new `test_validation_existence.py` was added. |
| 5 | **WP07 SOURCE-only** | **CONFIRMED.** No generated agent copies (`.claude/`, `.codex/`, `.github/`, …) in the diff. Only `src/doctrine/skills/*`, `src/doctrine/missions/.../plan/prompt.md`, and the test/script files. |

---

## 5. Drift Findings

- **No non-goal invasion.** The mission did NOT stray into deferred classes: `coordination/status_transition.py` is the only coordination-package file touched, and its change is the byte-equal read-side route (no #1900 write-side ratchet, no #1832 read-path, no #1716 topology, no #1619 builder-hardening). The `feature_dir.parent.parent` repo-root class is untouched and named in the ratchet honesty note.
- **All diff confined to** `src/`, `tests/`, `src/doctrine/`, `kitty-specs/`. NFR-004 (bounded conflict surface) holds.

## 6. Risk Findings

- **H-1 (HIGH) — WP05 byte-parity test never executes.** `tests/specify_cli/core/test_2000_compose_routing.py:23` imports the deleted public `mid8`, so the module raises `ImportError` at collection. The #2000 compose-routing byte-parity proof (FR-005/NFR-001) is **dead on the merged tree** — it has not run since WP01's demotion landed (ordering artefact: WP05 authored against the pre-demotion seam, never re-collected post-WP01). This also breaks the `test_ci_quality_path_filters` architectural gate. The underlying production code IS byte-equal (verified manually, §4 check 3), so this is a test-hygiene/CI-integrity defect, not a behavioral regression — but the verification-by-deletion proof for #2000 is currently absent. **Fix:** change the import to `_mid8` (and the body's `mid8(...)` calls) or recompute literals; re-collect. *Note: the test body also re-calls `mid8(_MISSION_ID)` to compute its "frozen" RHS (lines 70/121), which is a tautology-adjacent pattern the anti-gaming discipline warns against — worth tightening when repairing.*
- **M-1 (MEDIUM) — 3 new test files lack `pytestmark`.** `test_branch_naming_ssot_entrypoint.py`, `test_mid8_contract_sensitive_routing.py`, `test_mid8_direct_routing.py` carry no marker → CI's marker-based profiles silently skip them. They pass when run directly (329 green), but CI coverage of WP01/WP03/WP04 routing is not guaranteed. Fails `test_pytest_marker_convention`.
- **M-2 (MEDIUM) — FR-012 finding-code scope reduced.** Spec FR-012 lists three codes (`unregistered-path`, `unknown-flag`, `internal-as-public`); implementation emits only `unregistered-path`. Flag-level and internal-as-public detection are absent. Consistent with WP07's "path-level validation first" risk note, but the spec text was not amended — the guard catches unregistered command paths only, not bad flags or internal-surface leakage.

## 7. Silent Failure Candidates

**None found.** Every routed site preserves its prior `""`/`None`/short-id contract with an explicit `or None` / `or mission_id[:8]` / `else ""` and a per-site rationale comment. `resolve_mid8` declines to `""` (never raises), and each call site converts that to its required sentinel deliberately. `retrospective/generator.py` correctly preserved selector prefix-comparison semantics (computed-canonical-then-compare) rather than naively routing. No empty/effect-free exception handlers introduced; the `doctor.py` dead `try/except ValueError` was consciously removed.

## 8. Security Notes

Surface is internal (mid8 derivation, doctrine SOURCE prose, CI guard). No new external input, network, auth, or filesystem-write surface. `_typer_walker.walk()` reuse is read-only introspection of the registered Typer app. No security concerns.

## 9. Dead-Code Check

No new function without a live caller. The command-snippet guard helpers (`_extract_command_path`, `_is_registered_path`, `_doctrine_source_snippets`, `_chop_at_shell_stop`) all have live test callers (`test_doctrine_source_snippets_are_registered`, `test_guard_rejects_planted_nonexistent_command`, `test_guard_accepts_valid_bool_auto_negation`). The `retrospective_terminus.py` `def _mid8` shadow was deleted (FR-009).

---

## Final Verdict: **PASS-WITH-NOTES**

**Rationale.** The routing core is sound, honest, and severable. All 5 operator cross-WP checks are confirmed: F-1 closed with a byte-equal status_transition route (no coord-write creep); the ratchet passes with a minimal, non-over-allow-listed allow-list (0 unaccounted consumers); worktree.py byte-parity holds (the `-` move is a false positive); #1888 is genuinely verify-and-close (unchanged); WP07 is SOURCE-only. Contract gate green (268). Issue matrix fully terminalized. No silent-failure, no drift into deferred classes, no dead code, no security surface.

The verdict is held below clean PASS by **H-1**: the WP05 byte-parity test is uncollectable on the merged tree (imports the deleted public `mid8`), which (a) means the #2000 verification-by-deletion proof does not actually run and (b) red-lights the `test_ci_quality_path_filters` architectural gate. The production code is byte-equal (manually verified), so this is a CI-integrity / test-hygiene defect rather than a behavioral regression — but it is a real broken link in the FR-005 trace and a broken architectural gate, which is why this is PASS-WITH-NOTES rather than PASS.

### Open items (follow-up, non-blocking for behavior; blocking for green CI)
1. **H-1:** Repair `tests/specify_cli/core/test_2000_compose_routing.py` — import `_mid8` (not `mid8`), recompute the frozen literals as true HEAD-captured constants (not re-calls), re-collect. Restores both the FR-005 proof and the `test_ci_quality_path_filters` gate.
2. **M-1:** Add `pytestmark` to the 3 new routing test files (`test_branch_naming_ssot_entrypoint.py`, `test_mid8_contract_sensitive_routing.py`, `test_mid8_direct_routing.py`).
3. **M-2:** Either implement the `unknown-flag` / `internal-as-public` finding codes (FR-012) or amend the spec to record the path-level-only scope as the delivered contract.
4. Pre-existing (not this mission): `test_implement_base_ref.py` missing `git_repo` marker (`test_pytest_marker_correctness`); `test_coord_reader_fixes` #2007 read-path failure (deferred to #2010).

### Retrospective reminder
The H-1 / M-1 cluster is a recurring **post-reorder collection-drift** signature: when the dependency graph is flipped (route-WPs before the demotion-WP, per the F-1 fix in `POST-TASKS-SYNTHESIS.md`), a test authored against the *pre-demotion* public symbol survives the squash merge uncollected because no full-suite re-collection ran after WP01 de-exported `mid8`. A mission-level "collect-all after the last ownership-shifting WP" gate (or simply running the full architectural suite pre-accept) would have caught both H-1 and M-1 before merge.
