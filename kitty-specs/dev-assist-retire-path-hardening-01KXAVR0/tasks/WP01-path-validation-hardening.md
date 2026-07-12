---
work_package_id: WP01
title: Path-validation security hardening
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-001
- C-001
tracker_refs:
- '2073'
planning_base_branch: feat/dev-assist-retire-path-hardening
merge_target_branch: feat/dev-assist-retire-path-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/dev-assist-retire-path-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dev-assist-retire-path-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dev-assist-retire-path-hardening-01KXAVR0
base_commit: 4e129fc35c2c4d8ee3b87208b14e6c2be7c9c237
created_at: '2026-07-12T11:03:32.843509+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Security hardening
shell_pid: "119196"
agent: "claude"
history:
- at: '2026-07-12T10:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-07-12T10:40:00Z'
  actor: claude
  action: Revised per post-tasks squad (Lens C security completeness) — symlink-test base, Windows-absolute + control-char rules, case-variant skip removal, over-rejection ordering, over-rejection tripwire, vector-count correction, runtime-wiring scoped out to the assets-trust doctrine (#2539/#2536).
agent_profile: python-pedro
authoritative_surface: tests/adversarial/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/mission.py
- tests/adversarial/test_path_validation.py
role: implementer
tags:
- security
task_type: implement
---

# WP01 — Path-validation security hardening

## Context

Phase-0 research (research.md R1) proved **all 17 malicious-path vectors are live**: `validate_deliverables_path` (`src/specify_cli/mission.py:618`) only checks a `kitty-specs` prefix, literal `research`, and a leading `/`. The adversarial tests mask this: each calls `pytest.xfail()` when the malicious path is *accepted*, so the suite is green while the holes are open.

**Scope decision (operator, 2026-07-12):** this WP **hardens the validator function** and de-masks its tests. It does **NOT** wire the validator into the runtime path — post-tasks review found `validate_deliverables_path` has **zero production callers** (the runtime path `get_deliverables_path` → `workflow_executor.py:566` never invokes it). Runtime enforcement is a path-containment/trust concern that overlaps the **ship-code-as-assets doctrine design (epic #2539, trust-surface #2536)** and must be designed there, not bolted on here. This WP therefore delivers **verified latent hardening**; FR-001/NFR-001 are scoped to the function, and the un-wired-in-runtime state is stated honestly in the spec and PR.

## Approach (ATDD red-first, C-001)

1. **T001 — strict red-first suite.** In `tests/adversarial/test_path_validation.py`:
   - Remove every `if is_valid: pytest.xfail(...)` guard so `assert not is_valid` runs strict (research R1: goes red).
   - Remove the `case_insensitive_fs` **skip** guard on `test_case_variants_rejected` and assert rejection **unconditionally** — the fix is in-code case-folding, so it must hold on any FS (else "8/8 red→green" is only 7/8 observable on Linux CI).
   - Give the 5 assertion-free tests real assertions. **Note (vector accounting):** only `test_project_root_rejected` (`./` → `.`) is a genuine malicious→rejected vector; `test_unicode_normalization_consistent` is a consistency guard (green today), and `test_valid_unicode_accepted` / `test_trailing_whitespace_handled` are positive cases. Do not count these three toward the "8 malicious vectors" tally.
2. **T002 — harden the validator.** Reject, with a specific message per class:
   - `..` components / any path that normalizes to escape the project root (check `..` on the **raw** input, before any resolve).
   - empty / whitespace-only (after strip) and slash-normalizing-to-empty.
   - **control characters** — null byte (`\x00`) and bidi/RTL overrides (`‪-‮`, `⁦-⁩`) — one control-char rejection rule covers both the null-byte and RTL-override tests.
   - `~` / home.
   - dot-only (`.`, `..`).
   - **absolute — POSIX AND Windows**: reject a leading `/`, a leading backslash, and a drive-letter form (`C:\`), checked on the **raw** input (POSIX `Path.is_absolute()` returns False for `C:\`, so an explicit backslash/drive rule is required).
   - **symlink containment**: resolve and confirm the resolved target stays within the project root and outside `kitty-specs/` — use `Path.relative_to` for containment, **not** `startswith` (which mis-fires on sibling prefixes like `kitty-specs-backup/`). Reference the canonical patterns `src/specify_cli/core/paths.py::assert_safe_path_segment` and the `relative_to` containment in `doctrine/sources/https_source.py:270`, and justify the separate implementation.
   - Ordering: run the raw-input checks (`..`, absolute, control-char, empty) FIRST; only then resolve-and-contain on a separate copy (`Path("docs/research/x").resolve()` is absolute by construction — never run the absolute check on the resolved path).
   - Make the `kitty-specs` containment check case-insensitive.
3. **T003 — preserve legitimate paths + fix the symlink test.**
   - The symlink test today builds the link under `tmp_path` but calls the SUT with a bare relative string resolved against CWD, so the link is never consulted. Give the test a real base — `monkeypatch.chdir(tmp_path)` (or pass a base/project_root) — so `Path.resolve()` actually sees the symlink.
   - Legitimate shapes MUST keep passing: `docs/research/<x>/`, `research-outputs/<x>/`, ordinary relative deliverables paths. Add positive cases in-file, and **run `tests/research/test_research_deliverables_unit.py` (L161-185) as the over-rejection tripwire** (its positive `assert is_valid` cases are the real regression guard; if the hardening trips it, a legitimate path was over-rejected). It is not owned by this WP — run it green; touch only with a recorded one-line rationale if genuinely required.
4. **T004 — anti-vacuity + green.** Prove the suite re-reds if any accepted-malicious-path is reintroduced (weaken the validator in a scratch check, confirm red, revert). Full `tests/adversarial/test_path_validation.py` green with 0 `xfail` and 0 unconditional `skip` (NFR-001); `tests/research/test_research_deliverables_unit.py` green.

## Acceptance

- Every malicious vector class rejected (traversal, empty/whitespace, dot-only, control-char incl. null + RTL, home, absolute POSIX **and** Windows, symlink, case-variant); 0 `xfail`, 0 skip-masks, 0 assertion-free tests in the file.
- No legitimate relative deliverables path regresses (`tests/research/test_research_deliverables_unit.py` green).
- Spec/PR state the validator is hardened but **not wired into runtime** (deferred to #2539/#2536).
- `ruff` + `mypy` clean on `src/specify_cli/mission.py`.

## Branch Strategy

Planning branch: `feat/dev-assist-retire-path-hardening`; final merge target the same (PR'd to `main` at close). Worktree per computed lane from `lanes.json`.

## Activity Log

- 2026-07-12T11:21:08Z – user – shell_pid=4168430 – Moved to for_review
- 2026-07-12T11:31:43Z – claude – shell_pid=119196 – Moved to for_review
- 2026-07-12T11:36:20Z – claude – shell_pid=119196 – LAND (review a09189b5): all vectors rejected, 44 green/0 xfail, anti-vacuity re-reds 11, ruff+mypy clean
