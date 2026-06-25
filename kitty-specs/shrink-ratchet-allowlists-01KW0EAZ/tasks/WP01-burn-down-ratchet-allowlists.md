---
work_package_id: WP01
title: Burn down the stale ratchet allowlists
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs:
- '2049'
planning_base_branch: feat/shrink-ratchet-allowlists
merge_target_branch: feat/shrink-ratchet-allowlists
branch_strategy: Planning artifacts for this mission were generated on feat/shrink-ratchet-allowlists. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/shrink-ratchet-allowlists unless the human explicitly redirects the landing branch.
created_at: '2026-06-26T00:00:00+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
agent: claude
history:
- date: '2026-06-26'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/synthesizer/write_pipeline.py
- src/specify_cli/compat/_adapters/version_checker.py
- src/specify_cli/compat/_adapters/gate.py
- src/specify_cli/compat/_adapters/detector.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_compat_shims.py
- tests/contract/test_example_round_trip.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here. This is a behavior-preserving *burn-down* (dead-code / dead-allowlist reduction) — randy-reducer's domain: remove the stale surface, keep behavior identical, prove it with the gates.

## ⚠️ Before you start: tracker assignment (DIR-003) + run via `uv run`

1. **DIR-003**: best-effort assign issue **#2049** to the HiC: `unset GITHUB_TOKEN && gh issue edit 2049 --repo Priivacy-ai/spec-kitty --add-assignee <HiC-handle>`. (Known limitation from the prior mission: `MOES-Media` can't be assigned upstream — if it errors, note it and continue.)
2. **Run all `spec-kitty`/`pytest`/`ruff`/`mypy` commands via `uv run …`** — the globally-installed `spec-kitty` lags local `main` and its commit path wrongly refuses to `main`.

## Objective

Burn down the evidence-backed stale architectural-ratchet allowlist entries across four categories, fix
the dead-symbol-gate parser bug (which un-blinds `write_pipeline.py`), retire 3 dead `compat/_adapters/*`
shim files, and correct the tracking-issue drift. Leave `tests/architectural/` and `tests/contract/`
green at the reduced baselines, with **no runtime behavior change** and `category_4` untouched.

Requirements basis: `docs/engineering_notes/2049-ratchet-burndown-audit.md` (squad-verified) + this
mission's `research.md` (re-confirmed live; line numbers drift — locate by symbol name).

## Constraints (from spec.md / research.md)

- **C-001**: every `_baselines.yaml` decrement MUST equal the live frozenset/file-list size after the edit. Re-count.
- **C-002**: every `_baselines.yaml` edit MUST carry a `# justification:` comment naming #2049 + the evidence.
- **C-003**: file deletions + their allowlist removals land together (gate must be green at each commit).
- **C-005**: do NOT touch `category_4_backcompat_shims` (owned by #2048 / PR #2152). It will read `9` here — leave it.

## Subtasks

### T001 — FR-006: fix `_extract_all_literal` + unit test

**Purpose**: Un-blind the dead-symbol gate to modules whose first top-level node is a non-`__all__`
annotated assignment.

**Steps**:
1. In `tests/architectural/test_no_dead_symbols.py`, find `def _extract_all_literal` (≈line 910). The
   bug: the `elif isinstance(node, ast.AnnAssign):` branch sets `value` only when the target is
   `__all__`; otherwise `value` stays `None` and the next `if value is None: return frozenset()`
   (≈line 938) fires — returning an empty `__all__` for the WHOLE module.
2. Fix: in the `AnnAssign` branch, when the target is NOT `__all__`, `continue` to the next node. Only
   reach `if value is None: return frozenset()` for an `__all__` AnnAssign declared without a value
   (`__all__: list[str]`). Preserve the existing `ast.Assign` and dynamic-`__all__` (`return None`) behavior.
3. Add a focused unit test (same file or a sibling) that builds a module AST whose first top-level node
   is a non-`__all__` `AnnAssign` (e.g. `_X: int = 1`) followed by a real `__all__ = ["foo"]`, and
   asserts `_extract_all_literal` returns `frozenset({"foo"})` (it returns `frozenset()` today).

**Validation**:
- [ ] New unit test passes; demonstrates the module's `__all__` is now seen.

### T002 — FR-006 cascade: trim `write_pipeline.__all__`

**Purpose**: After T001, the gate inspects `src/charter/synthesizer/write_pipeline.py`'s `__all__`
(`promote, stage_and_validate, compute_written_artifacts, StagedArtifact`). Only `stage_and_validate`
has a real cross-module `from`-import caller; the other 3 would be flagged dead. Resolve by demoting the
uncalled ones to unexported internals (the established `merge.*`-seam burn-down pattern) — NOT by adding
allowlist entries.

**Steps**:
1. **Verify first** (do not skip): (a) `grep -rn "from charter.synthesizer.write_pipeline import \*" src/ tests/` → expect none; (b) for each of `promote`, `compute_written_artifacts`, `StagedArtifact`, `grep -rn "from .*write_pipeline import" src/` and confirm none import that name (module-style `write_pipeline.promote()` does NOT count). `stage_and_validate` HAS a real importer (`src/specify_cli/cli/commands/charter/_synthesis.py`) — keep it.
2. Trim `__all__` in `write_pipeline.py` to the live-caller set: `__all__ = ["stage_and_validate"]`. Leave the symbol *definitions* intact (they stay importable via explicit `from ... import` and module-style calls — `__all__` only governs `import *`).
3. If step 1 reveals any of the 3 DOES have a real `from`-import caller, keep that one in `__all__` (it's live) and demote only the truly-uncalled ones.

**Validation**:
- [ ] No star-import of `write_pipeline` exists.
- [ ] `write_pipeline.__all__` lists only symbols with a real cross-module `from`-import caller; the module retains a non-empty `__all__` (passes `test_all_declarations_required`).

### T003 — FR-001: shrink `category_a_slice_f_deferred` to 9

**Steps**:
1. In `tests/architectural/test_no_dead_symbols.py`, remove the two entries
   `"charter.synthesizer.write_pipeline::StagedArtifact"` and `"…write_pipeline::promote"` from the
   slice-F deferred frozenset (locate by the `::` entries; the variable backs `category_a_slice_f_deferred`).
2. In `tests/architectural/_baselines.yaml`, set `category_a_slice_f_deferred: 9` with a `# justification:`
   comment. **Re-count** the live frozenset after removal — the audit found a 12-declared / 11-live drift,
   so removing 2 lands at 9; confirm the live size equals 9.

**Validation**:
- [ ] Live frozenset size == declared 9; the 2 entries gone.

### T004 — FR-002: shrink `category_b_grandfathered_legacy` to 284

**Steps**:
1. Remove `"specify_cli.cli.commands.charter.activate::charter_activate_app"` and
   `"…charter.deactivate::charter_deactivate_app"` from the grandfathered-legacy frozenset
   (`test_no_dead_symbols.py`). (Both symbols were deleted by a prior charter-app refactor; `tests/specify_cli/test_charter_activate_cli.py` asserts their absence.)
2. Set `_baselines.yaml` `category_b_grandfathered_legacy: 284` with a `# justification:` comment; confirm live size == 284.

**Validation**:
- [ ] Live frozenset size == 284; the 2 entries gone.

### T005 — FR-004: retire the 3 pure-shim adapter files

**Purpose**: Delete dead adapters (zero functional importers; real consumers import the canonical modules
directly) and drop their TWO paired baselines to 0.

**Steps**:
1. **Verify**: `grep -rn "compat._adapters" src/ tests/ | grep import` — confirm no functional `from specify_cli.compat._adapters.* import` in `src/` (only architectural-allowlist references should exist).
2. `git rm src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py`.
3. Remove their entries from **all four** surfaces (C-003):
   - `_ADAPTER_FILES` in `tests/architectural/test_compat_shims.py`
   - the `category_5` adapter entries in `tests/architectural/test_no_dead_modules.py`
   - the adapter dead-symbol entries in `tests/architectural/test_no_dead_symbols.py`
   - `_baselines.yaml`: `pure_shim_files: 0` AND `category_5_wp_in_flight_adapters: 0` (both pin the same 3 files), each with a `# justification:` comment.

**Validation**:
- [ ] 3 files deleted; `grep -rn "compat._adapters" src/` empty; `pure_shim_files` and `category_5_wp_in_flight_adapters` both 0; live sizes match.

### T006 — FR-003: shrink `legacy_contract_allowlist` to 151

**Steps**:
1. Confirm the path is gone: `test ! -d kitty-specs/033-github-observability-event-metadata`.
2. In `tests/contract/test_example_round_trip.py`, remove the entry
   `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` from
   `legacy_contract_allowlist` (note: this allowlist is in `tests/contract/`, NOT architectural).
3. Set `_baselines.yaml` `legacy_contract_allowlist: 151` with a `# justification:` comment; confirm live size == 151.

**Validation**:
- [ ] Dangling entry gone; live size == 151.

### T007 — FR-005: post issue/doc corrections

**Steps**:
1. `unset GITHUB_TOKEN && gh issue comment 2049 --repo Priivacy-ai/spec-kitty --body "<corrections>"` noting: `legacy_contract_allowlist` lives in `tests/contract/test_example_round_trip.py` (issue said architectural); live counts are `category_7_grandfathered_orphans=7` (issue said 6) and `category_b_grandfathered_legacy=286` (issue said 271).
2. If the `gh comment` fails (auth), record the corrections in the PR body instead and note it.

**Validation**:
- [ ] Corrections posted to #2049 (or captured in the PR body with a note).

### T008 — Verify everything green

**Steps**:
1. `PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_compat_shims.py tests/contract/test_example_round_trip.py -q`
2. `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`
3. Diff-scoped lint: `git diff --name-only --diff-filter=AMR HEAD | rg '\.py$'` then `uv run ruff check <those files>` (exit 0).
4. `uv run mypy src/charter/synthesizer/write_pipeline.py`.
5. Confirm the 5 reduced baselines and that `category_4_backcompat_shims` is unchanged.

**Validation**:
- [ ] All listed gates pass; every edited baseline == its live size; `category_4` untouched.
- [ ] `ruff` + `mypy` clean on the diff. (Ignore local-env `python -m ruff` tid251 failures + the order-flaky `test_pytest_marker_convention` — env artifacts, verify on CI.)

## Branch Strategy

- **Planning base branch**: `feat/shrink-ratchet-allowlists`.
- **Final merge target**: `feat/shrink-ratchet-allowlists`, which merges to `main` via a PR (cross-fork: push to `fork`, `gh pr create --repo Priivacy-ai/spec-kitty --head MOES-Media:feat/shrink-ratchet-allowlists`). Do not push to `origin/main`.
- Execution worktrees are allocated per computed lane from `lanes.json`. Enter the workspace `spec-kitty agent action implement WP01` resolves — do not reconstruct paths.

## Definition of Done

- `_baselines.yaml`: `category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`; `category_4_backcompat_shims` unchanged; every edit has a `# justification:` comment and matches its live size.
- `_extract_all_literal` fixed + unit-tested; `write_pipeline.__all__` trimmed to live-caller symbols.
- 3 `compat/_adapters/*` files deleted; no functional importers remain.
- Dangling `legacy_contract` entry removed; #2049 corrections posted.
- `pytest tests/architectural/ tests/contract/`, `ruff`, `mypy` all green.

## Risks & Reviewer Guidance

- **FR-006 cascade (the key risk)**: Reviewer — confirm the parser fix un-blinds `write_pipeline`, that `__all__` was trimmed (not that new allowlist entries were added), and that each demoted symbol genuinely has no `from`-import caller / no star-import. Watch for `compute_written_artifacts` (the audit didn't list it).
- **C-001 off-by-one**: Reviewer — for each of the 5 baselines, confirm declared == live frozenset/file-list size (`test_ratchet_baselines.py` is the oracle).
- **C-003 atomicity**: Reviewer — confirm all 4 pure-shim surfaces moved together and no dead-module gate flags an un-allowlisted file.
- **C-005**: Reviewer — confirm `category_4_backcompat_shims` is NOT in the diff.
- **No production behavior change (NFR-002)**: the only `src/` edits are the 3 file deletions + the `write_pipeline.__all__` line; symbol definitions and call sites are untouched.
