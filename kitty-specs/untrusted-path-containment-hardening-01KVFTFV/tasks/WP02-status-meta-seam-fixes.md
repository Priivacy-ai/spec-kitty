---
work_package_id: WP02
title: status/ + meta.json seam fixes (IC-01 + IC-05)
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-007
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: automation/sonar-security-20260619
merge_target_branch: automation/sonar-security-20260619
branch_strategy: Planning artifacts for this mission were generated on automation/sonar-security-20260619. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into automation/sonar-security-20260619 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1254993"
history:
- at: '2026-06-19T12:26:42Z'
  actor: claude
  note: WP authored from plan IC-01 + IC-05 (FR-002/FR-007/FR-008/FR-009).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/status/store.py
- src/specify_cli/status/views.py
- src/specify_cli/status/lifecycle.py
- src/specify_cli/mission_metadata.py
- tests/status/test_store.py
- tests/status/test_derived_view_slug_traversal.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile before anything else: run `/ad-hoc-profile-load python-pedro`
(or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it),
and acknowledge its initialization declaration.

## Objective

Close the two highest-severity residuals of the untrusted-slug class on the
`status/` + identity surface:
1. **IC-01 / FR-002**: `store.py._SlugResolver.resolve` uses segment-grammar only,
   so a valid-label slug naming a **symlink directory** under `kitty-specs/` escapes.
   Add `resolve()`-containment.
2. **IC-05 / FR-009**: `views.py` (`_stale_check_slug`→`resolve_mission_identity`) and
   the `lifecycle.py` empty-slug fallback read `meta.json`'s `mission_slug`
   **unvalidated** and `mkdir` under `derived_dir / <slug>` — a **live write-path
   traversal** after #2036 (the reducer seam covers only the event slug, and a hostile
   event slug downgraded to `""` actively triggers this `meta.json` fallback). Sanitize
   at the single `mission_metadata` chokepoint.

Must not regress the #2036 baseline (FR-007). Reuse the canonical seam (C-002); fail
closed (C-004).

## Context (verified against code on this branch)

- `src/specify_cli/core/paths.py`: `assert_safe_path_segment(value)` (raises), `safe_mission_slug(slug, fallback)` (fail-closed, never raises).
- `src/specify_cli/core/utils.py`: `ensure_within_any(path, roots)` — `resolve(strict=False)` + containment, raises `ValueError` on escape.
- `store.py._SlugResolver.resolve` (~line 165-187): grammar-guarded then `.exists()`/`read_text()` on `self._mission_specs_root / mission_slug / "meta.json"` — NO containment.
- `mission_metadata.py:225`: `resolved_slug = str(meta.get("mission_slug") or meta.get("slug") or feature_dir.name)` — the single unsanitized source feeding `views.py:_stale_check_slug` (~240/264) and `lifecycle.py` (~341/426-427).
- `progress.py` (~216) is already safe (uses `snapshot.mission_slug or feature_dir.name`).

## Subtasks

### T006 — store.py resolve()-containment (FR-002)
- In `_SlugResolver.resolve`, after the existing segment-grammar gate and before/around the `read_text`, validate the composed `meta_path` with `ensure_within_any(meta_path, roots=[self._mission_specs_root])`. **`roots` is keyword-only** — the positional form `ensure_within_any(meta_path, [root])` raises `TypeError` and the containment silently never runs (a no-op disguised as a fix). Use the `roots=` keyword (matches `merge.py:823,844`).
- **Fail closed (C-004)**: on `ValueError`, return `None` (skip), log at most one WARNING per distinct slug (reuse the existing cache so a repeated bad slug doesn't re-warn — NFR-004). Do NOT raise.
- Keep cyclomatic complexity ≤ 15 (extract a small helper if needed).

### T007 — store.py symlink-escape + symlinked-root tests (FR-008)
- **Negative (escape)**: plant a symlink dir under the specs root whose target is outside it, with a `meta.json` behind it; assert `resolve()` returns `None` and does not read the escaped file. Mutation-verify: neutralize the new containment → test FAILS.
- **Positive (symlinked root — macOS hazard, research Decision 6)**: place the specs root itself under a symlinked path and assert a LEGITIMATE slug RESOLVES (no false reject). This guards NFR-003. Pass the un-resolved logical root to `ensure_within_any`. **MUST run on ALL platforms (incl. Linux CI)** — construct the symlink explicitly inside `tmp_path` (a symlinked dir → real specs root); do NOT `@pytest.mark.skipif` on platform and do NOT `pytest.skip` in the body (a skipped test ships the false-reject regression undetected). Assert `path.is_symlink()` on the planted link so a no-op test that omits the symlink fails.

### T008 — mission_metadata safe_mission_slug chokepoint (FR-009)
- In `resolve_mission_identity` (mission_metadata.py:225), route the resolved slug through `safe_mission_slug(meta.get("mission_slug") or meta.get("slug"), feature_dir.name)` so a hostile `meta.json` slug fails closed to the trusted `feature_dir.name`. This single change covers BOTH `views.py` and `lifecycle.py` consumers.
- **Pass-through positive test (un-fakeable)**: assert that for a LEGITIMATE `meta.json mission_slug`, `resolve_mission_identity().mission_slug` returns the slug **unchanged** (proving `safe_mission_slug` is a pass-through for valid input, not a blanket downgrade that would corrupt display). Mutation: a valid slug must NOT be replaced by `feature_dir.name`.

### T009 — meta.json write-path negative test (FR-009)
- In `tests/status/test_derived_view_slug_traversal.py`, add a case: hostile `meta.json` `mission_slug = "../../../../evil"` + empty event-log slug → drive `generate_lifecycle_json` and `materialize_if_stale`/`write_derived_views`; assert NO `mkdir`/write outside `derived_dir`, output under `feature_dir.name`. Mutation-verify: revert T008 → test FAILS (escaped dir created).

### T010 — route any WP01-flagged reachable status/ sink
- From WP01's inventory, if any `status/` sink is marked `routed-through-seam (TODO)` beyond store.py/views.py/lifecycle.py, route it through the seam here. If none, record that in the WP history.

### T011 — gates + no-regression (FR-007)
- `ruff check` + `mypy` clean on all touched files (no new `# noqa`/`# type: ignore`).
- `PWHEADLESS=1 python -m pytest tests/status/ tests/specify_cli/cli/commands/test_merge.py -p no:cacheprovider -q` — all green; confirms the #2036 baseline (reducer seam, progress.py) still holds.

## Branch Strategy

Planning/base + merge target: `automation/sonar-security-20260619` (rides PR #2036; flattened). Execution worktree allocated per `lanes.json` lane at implement time.

## Definition of Done

- [ ] store.py applies `resolve()`-containment, fail-closed to `None` (FR-002, C-004).
- [ ] symlink-escape negative AND symlinked-root positive tests pass, both mutation-verified (FR-008, NFR-003).
- [ ] `mission_metadata.resolve_mission_identity` routes the slug through `safe_mission_slug` (FR-009).
- [ ] meta.json + empty-event-slug write-path negative test passes, mutation-verified.
- [ ] ruff + mypy clean; full status/merge suite green; #2036 baseline not regressed (FR-007).
- [ ] At most one WARNING per distinct rejected slug (NFR-004).

## Risks / Reviewer guidance

- **macOS false-reject risk** (the key one): the symlinked-root positive test MUST prove a legitimate slug is accepted under a symlinked root — verify the test would catch a guard that passes a pre-resolved root.
- **Reviewer**: run the two mutation checks yourself (neutralize containment → escape test fails; revert the mission_metadata change → meta.json write test fails). Confirm `progress.py` is untouched and still safe.

## Activity Log

- 2026-06-19T13:15:01Z – claude:opus:python-pedro:implementer – shell_pid=1218199 – Assigned agent via action command
- 2026-06-19T13:27:03Z – claude:opus:python-pedro:implementer – shell_pid=1218199 – store.py containment (roots= kw) + meta.json chokepoint; symlink-escape + symlinked-root + meta.json-bypass tests all mutation-verified; mypy --strict clean; #2036 baseline green; --force used: flattened-mission kitty-specs-on-lane guard false-positive (lane is based on automation/sonar-security-20260619 which carries kitty-specs)
- 2026-06-19T13:27:42Z – claude:opus:python-pedro:implementer – shell_pid=1218199 – Reconcile lane→primary desync (flattened mission); WP02 impl complete lane-b b6e3fabd2 (mypy --strict 0, 730 tests, 3 mutations bit)
- 2026-06-19T13:27:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1254993 – Started review via action command
- 2026-06-19T13:32:38Z – user – shell_pid=1254993 – Review passed (reviewer-renata, independent mutation-verified). FR-002: store.py resolve() calls ensure_within_any(meta_path, roots=[root]) keyword roots= (kw-only confirmed), fail-closed None, cached. Mutation force _is_contained=True: symlink-escape test FAILED (attacker mission_id returned), symlinked-root positive still PASSED; reverted clean. FR-009: resolve_mission_identity routes meta slug via safe_mission_slug(raw, feature_dir.name). Mutation raw slug: both generate_lifecycle_json + materialize_if_stale hostile-meta tests FAILED with a REAL escaped 'evil' dir created outside derived_dir (asserts no-mkdir-outside), pass-through positive PASSED; reverted clean. NFR-003 symlinked-root test runs unconditionally (no skip), asserts is_symlink(). FR-007: progress.py/reducer.py untouched, 730 status+merge tests passed. Gates: mypy --strict exit 0, ruff+C901 clean, no new noqa/type-ignore. Scope: exactly 4 files; resolve <=15. --force: known flattened-mission kitty-specs-on-lane guard false-positive (lane based on automation/sonar-security-20260619 carrying kitty-specs; #2036 in-mission), same override the implementer used.
- 2026-06-19T13:33:35Z – user – shell_pid=1254993 – Reconcile lane→primary desync; reviewer-renata APPROVED WP02 (FR-002+FR-009 mutations independently bit, mypy --strict 0, 730 tests). #2036 in-mission.
