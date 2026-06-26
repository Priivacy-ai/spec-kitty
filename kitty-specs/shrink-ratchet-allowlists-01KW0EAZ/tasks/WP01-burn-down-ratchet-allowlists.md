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
agent: claude
shell_pid: "452836"
history:
- date: '2026-06-26'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
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

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here. This is a behavior-preserving *burn-down* — remove the stale allowlist surface, keep behavior identical, prove it with the gates.

## ⚠️ SCOPE GUARDRAIL — FR-006 is DEFERRED to #2158

This WP delivers the **clean allowlist shrink only**. Do **NOT** fix the `_extract_all_literal` parser
bug and do **NOT** modify `src/charter/synthesizer/write_pipeline.py`. A prior attempt fixed the parser,
which un-blinded ~57 modules / ~117 pre-existing dead symbols and **grew** `category_b` 286→392 (the
opposite of this mission's goal). That work is now its own issue **#2158**. If, during your edits, the
dead-symbol gate suddenly flags many new dead symbols, STOP — you've touched the parser; revert that.

## ⚠️ Before you start

1. **Reset the lane to base** to discard the prior (rejected) parser-fix attempt: from the lane worktree run `git log --oneline -3`, then `git reset --hard <the "chore: Start WP01 implementation" commit>` so the rejected `feat(WP01)` parser commit is gone and the tree matches the mission base.
2. **DIR-003**: best-effort `unset GITHUB_TOKEN && gh issue edit 2049 --repo Priivacy-ai/spec-kitty --add-assignee MOES-Media` (known to fail upstream — note + continue).
3. **Run all `spec-kitty`/`pytest`/`ruff`/`mypy` via `uv run …`** (installed `spec-kitty` lags local `main`).

## Objective

Remove ~7 evidence-backed stale allowlist entries across four categories and retire 3 dead
`compat/_adapters/*` shim files. Leave `tests/architectural/` and `tests/contract/` green at the reduced
baselines, with **no runtime behavior change**, **no net allowlist growth**, and the parser /
`write_pipeline.py` / `category_4` untouched.

Requirements basis: `docs/engineering_notes/2049-ratchet-burndown-audit.md` (squad-verified) + this
mission's `research.md` (line numbers drift — locate by symbol name).

## Constraints

- **C-001**: every `_baselines.yaml` decrement MUST equal the live frozenset/file-list size after the edit. Re-count.
- **C-002**: every `_baselines.yaml` edit MUST carry a `# justification:` comment naming #2049.
- **C-003**: file deletions + their allowlist removals land together (gate green at each commit).
- **C-005**: do NOT touch `category_4_backcompat_shims` (reads `9`; leave it).

## Subtasks

### T001 — FR-001: shrink `category_a_slice_f_deferred` to 9

**Steps**:
1. In `tests/architectural/test_no_dead_symbols.py`, remove the two entries
   `"charter.synthesizer.write_pipeline::StagedArtifact"` and `"…write_pipeline::promote"` from the
   slice-F deferred frozenset (the variable backing `category_a_slice_f_deferred`). These are inert — the
   gate is blind to `write_pipeline` (parser unfixed) — so removal cannot make the gate fail.
2. In `_baselines.yaml`, set `category_a_slice_f_deferred: 9` with a `# justification:` comment. The live
   frozenset is 11 (declared was a stale 12); removing 2 lands at **9**. Re-count to confirm live == 9.

**Validation**: live frozenset size == 9; the 2 entries gone.

### T002 — FR-002: shrink `category_b_grandfathered_legacy` to 284

**Steps**:
1. Remove `"specify_cli.cli.commands.charter.activate::charter_activate_app"` and
   `"…charter.deactivate::charter_deactivate_app"` from the grandfathered-legacy frozenset
   (`test_no_dead_symbols.py`). (Both symbols were deleted by a prior charter-app refactor; `tests/specify_cli/test_charter_activate_cli.py` asserts their absence.)
2. Set `_baselines.yaml` `category_b_grandfathered_legacy: 284` with a `# justification:` comment. Confirm live == 284. **Do NOT add any other entries** (without the parser fix, none surface).

**Validation**: live frozenset size == 284; only those 2 entries removed.

### T003 — FR-004: retire the 3 pure-shim adapter files

**Steps**:
1. **Verify**: `grep -rn "compat._adapters" src/ | grep import` — confirm no functional `from specify_cli.compat._adapters.* import` in `src/`.
2. `git rm src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py`.
3. Remove their entries from **all four** surfaces (C-003): `_ADAPTER_FILES` (`test_compat_shims.py`), the `category_5` adapter entries (`test_no_dead_modules.py`), the adapter dead-symbol entries (`test_no_dead_symbols.py`), and `_baselines.yaml`: `pure_shim_files: 0` AND `category_5_wp_in_flight_adapters: 0` (both pin the same 3 files), each with a `# justification:` comment.

**Validation**: 3 files deleted; `grep -rn "compat._adapters" src/` empty; both baselines 0; live sizes match.

### T004 — FR-003: shrink `legacy_contract_allowlist` to 151

**Steps**:
1. Confirm absent: `test ! -d kitty-specs/033-github-observability-event-metadata`.
2. In `tests/contract/test_example_round_trip.py`, remove the entry
   `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` from
   `legacy_contract_allowlist` (note: this allowlist is in `tests/contract/`, NOT architectural).
3. Set `_baselines.yaml` `legacy_contract_allowlist: 151` with a `# justification:` comment. Confirm live == 151.

**Validation**: dangling entry gone; live == 151.

### T005 — FR-005: issue/doc corrections

**Steps**:
1. A corrections comment was already posted to #2049 (issuecomment-4804994494). Confirm it (or post if missing) and add a one-line note that the `_extract_all_literal` parser fix moved to **#2158**:
   `unset GITHUB_TOKEN && gh issue comment 2049 --repo Priivacy-ai/spec-kitty --body "Parser fix (FR-006) split out to #2158; this mission delivers the clean allowlist shrink only."`

**Validation**: #2049 reflects the corrections + the #2158 split (or captured in the PR body with a note).

### T006 — Verify everything green + net SHRINK

**Steps**:
1. `PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_compat_shims.py tests/contract/test_example_round_trip.py -q`
2. `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`
3. Diff-scoped lint: `git diff --name-only --diff-filter=AMR HEAD | rg '\.py$'` then `uv run ruff check <those files>` (exit 0).
4. `uv run mypy` on any changed `.py` (best-effort; ignore pre-existing errors unchanged by the diff).
5. Confirm the 5 reduced baselines; `category_4` unchanged; **`git diff` of `test_no_dead_symbols.py` is a NET REMOVAL** (entries deleted, not 100+ added — if it grew, the parser was touched: revert).

**Validation**:
- [ ] Gates pass; every edited baseline == its live size; `category_4` untouched.
- [ ] `test_no_dead_symbols.py` diff is a net shrink (no mass additions).
- [ ] `ruff`/`mypy` clean on the diff. (Ignore local-env `python -m ruff` tid251 failures + the order-flaky `test_pytest_marker_convention` — env artifacts, verify on CI; the 2 `test_example_round_trip MISSING_FRONTMATTER` failures for OTHER missions' contracts are pre-existing and unrelated.)

## Branch Strategy

- **Planning base branch**: `feat/shrink-ratchet-allowlists`.
- **Final merge target**: `feat/shrink-ratchet-allowlists`, which merges to `main` via a cross-fork PR (push to `fork`, `gh pr create --repo Priivacy-ai/spec-kitty --head MOES-Media:feat/shrink-ratchet-allowlists`). Do not push to `origin/main`.
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Definition of Done

- `_baselines.yaml`: `category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`; `category_4_backcompat_shims` unchanged; each edit has a `# justification:` and matches its live size.
- 3 `compat/_adapters/*` files deleted; no functional importers remain.
- Dangling `legacy_contract` entry removed; #2049 corrections + #2158 split noted.
- `pytest tests/architectural/ tests/contract/`, `ruff`, `mypy` all green; `test_no_dead_symbols.py` diff is a net shrink.
- Parser / `write_pipeline.py` / `category_4` NOT touched.

## Risks & Reviewer Guidance

- **Scope guardrail (the key check)**: Reviewer — confirm `_extract_all_literal` and `src/charter/synthesizer/write_pipeline.py` are NOT in the diff, and that `test_no_dead_symbols.py` shows a NET REMOVAL (the prior attempt added 100+ entries — that must be gone).
- **C-001 off-by-one**: Reviewer — for each of the 5 baselines, confirm declared == live size (`test_ratchet_baselines.py` is the oracle).
- **C-003 atomicity**: all 4 pure-shim surfaces moved together; no dead-module gate flags an un-allowlisted file.
- **C-005**: `category_4_backcompat_shims` NOT in the diff.
- **NFR-002**: the only `src/` edits are the 3 file deletions.
