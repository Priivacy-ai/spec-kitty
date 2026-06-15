# Mission Review Report: tool-surface-contract-residuals-01KV4S5B

**Reviewer**: Claude (spec-kitty-mission-review skill, operator-directed)
**Date**: 2026-06-15
**Mission**: `tool-surface-contract-residuals-01KV4S5B` — ToolSurfaceContract Residual Closeout (mission #137)
**Baseline commit**: `a075bb36a3d0cf1b3a4e3b4a54a72584ae6eb17a` (pre-merge accept tip)
**HEAD at review**: `64d654f7198089ed06d982abd3692ac0cf05ddc8`
**WPs reviewed**: WP01..WP05 (all `done`)
**Event-log signals**: 5 forced transitions (documented lane-status `--force` from WP02/WP05 rejection cycles), 0 `ReviewerSelfApproval`.

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 pytest tests/contract/ -q`
- Exit code: 0
- Result: **PASS**
- Notes: 258 passed. Trailing `sync.server_auth_failure` line is a SaaS-auth warning (not logged in), not a test failure.

### Gate 2 — Architectural tests
- Command: `pytest tests/architectural/ -q`
- Exit code: non-zero
- Result: **FAIL — but pre-existing and out-of-scope (not mission-attributable)**
- Notes: Single failure `test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker`, violator `tests/specify_cli/cli/commands/test_context_info.py`. That file is **not in this mission's diff**, had **no `pytestmark` at the baseline commit** (`git show a075bb36a:…` → 0 hits), and was last touched by unrelated commit `31cb30c66`. 370 passed. All mission-touched test files carry markers (the new `test_agent_roster.py`/`test_manifest.py`/`test_projection.py`/`test_renderers.py` and the re-marked `test_docs.py`/`test_migration_compat.py` are clean). See OPEN-1.

### Gate 3 — Cross-repo E2E
- Command: (not run) `pytest spec-kitty-end-to-end-testing/scenarios/ -v`
- Result: **N/A — environmentally absent**
- Notes: The `spec-kitty-end-to-end-testing` repo is not checked out alongside this clone. This mission introduces **no cross-repo surface** (it is internal `tool_surface` finding-codes/manifest, `agent config` registry wiring, a CI-shard filter, a docs page, and a `paths.py` resolver scoping fix); no mission-claimed cross-repo behavior requires a new e2e scenario. No `mission-exception.md` is needed because the gate is not asserting a mission-introduced cross-repo claim.

### Gate 4 — Issue Matrix
- File: `kitty-specs/tool-surface-contract-residuals-01KV4S5B/issue-matrix.md`
- Rows: 7
- Empty / `unknown` verdicts: 0
- `deferred-with-followup` rows missing a follow-up handle: 0 (the single `#1945` deferred row names operator-owned epic closure + a readiness note delivered at accept)
- Result: **PASS**
- Notes: `#1940/#1941/#1942/#1944/#1965/#1948` → `fixed` (each cites the approved WP + commit); `#1945` → `deferred-with-followup` (operator-owned). No `in-mission` rows survived to `done`.

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | 4 profile finding codes emit at conditions | WP02 | `tool_surface/profiles/test_projection.py`, `test_renderers.py`, `providers/test_agent_profiles.py` | ADEQUATE — distinct emit sites in `projection.py` (171/203/226/239); live integration test asserts a code reaches `doctor tool-surfaces --json` via production caller `agent_profiles.py:211` | — |
| FR-002 | 8-field manifest provenance + legacy read | WP02 | `profiles/test_manifest.py` | ADEQUATE — 8-field round-trip + named legacy 6-field fixture via `raw.get` `_opt_str/_opt_int`; two-hash distinction both directions | — |
| FR-003 | registry-backed SKILL_ONLY/VALID agents | WP03 | `skills/test_agent_roster.py`, `cli/commands/test_agent_config.py` | ADEQUATE — single leaf `_agent_roster.py`, 3 live `src/` importers; monkeypatch-derivation test defeats coincidental-literal; config.py literal grep-proof deleted | — |
| FR-004 | "configured Claude w/ session presence" test | WP03 | `cli/commands/test_agent_config.py` | ADEQUATE — exercises real `SurfacePresenceIndex.build` path (present + absent), not a stub | — |
| FR-005 | docs-lint CI-collected fail-on-drift | WP04 | `tool_surface/test_docs.py` + `.github/workflows/ci-quality.yml` | ADEQUATE — `tool_surface/**` in the `core_misc` filter the `integration-tests-core-misc` `if:` reads; re-marked `integration`; discrimination test (registered→0, drift→`FINDING_UNREGISTERED_PATH`) | — |
| FR-006 | user-facing Tool-vs-Agent upgrade guide | WP05 | docs-lint + `3-2-page-inventory.yaml` + `toc.yml` | ADEQUATE — `docs/how-to/tool-surface-upgrade-and-repair.md` shipped (118 lines), TOC/inventory-discoverable, lint-clean | — |
| FR-007 | deterministic `..._error_schema_stable` | WP05 | `core/test_paths.py`, `cli/commands/test_doctor_skills.py` (+ `test_migration_compat.py`, fixed post-merge) | ADEQUATE — `SPECIFY_REPO_ROOT` authoritative when `env_path.exists()`; C-003 regression test green. See RISK-1 (the actual #1965 test in `test_migration_compat.py` was outside WP05 ownership and broke at merge; fixed) | RISK-1 |
| FR-008 | honest closure / issue-matrix terminal verdicts | WP01 + matrix | `issue-matrix.md` | ADEQUATE — Gate 4 PASS | — |

**Legend**: ADEQUATE = test constrains required behavior. No PARTIAL/MISSING/FALSE_POSITIVE chains found — the cycle-2 rejections specifically eliminated the two false-positive risks (WP02 dead `diagnose()`, WP05 uncommitted evidence).

---

## Drift Findings

### DRIFT-1: Leaked empty `test-feature-*` artifact committed into the squash merge
**Type**: NON-GOAL INVASION (hygiene / scope) · **Severity**: LOW
**Spec reference**: C-006 (not a bulk edit), NFR-003 (no `feature*` aliases — path token), general delivery hygiene
**Evidence**:
- `git diff a075bb36a..HEAD -- mutants/kitty-specs/test-feature-01KPN4R0/spec.md` → `new file mode 100644 … e69de29bb` (0 bytes)
- Introduced by squash commit `953cd6c74`; `mutants/` is **not** gitignored (`git check-ignore mutants/` → not ignored)

**Analysis**: An empty `test-feature-01KPN4R0/spec.md` under the `mutants/` mutation-testing scratch dir was an untracked file present in a lane worktree and got swept into the mission's squash merge. It is out-of-scope pollution on the delivery branch, matches the known E2E `test-feature-*` leak pattern, and its path carries the forbidden `feature*` token (the terminology guard does not scan `mutants/`, so it slipped through). No functional impact (empty file), but it should be removed and `mutants/` should be gitignored. Recommend a follow-up cleanup commit + `.gitignore` entry.

---

## Risk Findings

### RISK-1: An un-owned test pinning a touched source contract broke only at merge (resolved)
**Type**: CROSS-WP-INTEGRATION / ownership-scope · **Severity**: MEDIUM (resolved in-branch)
**Location**: `tests/specify_cli/tool_surface/integration/test_migration_compat.py::test_doctor_skills_json_error_schema_stable`
**Trigger condition**: WP05's correct `paths.py` change (existing `SPECIFY_REPO_ROOT` now authoritative) invalidated this test's old-contract assumption (`rc==2` via existing-dir override). The test was **not** in WP05's `owned_files`; WP05 fixed a same-named parallel copy in its owned `test_doctor_skills.py`. Per-WP review (owned-file scoped) never ran it; it failed only post-merge (`rc 0 != 2`).

**Analysis**: This is the systemic gap captured in **#1979** (filed). Remediated on-branch (`5a33f55be`): the error-envelope test now forces `locate_project_root → None` in-process, deterministically pinning the `not_in_project` envelope independent of filesystem walk-up (a leaked `/tmp/.kittify` made walk-up-based detection non-deterministic). Post-fix suite: 524 passed. No residual risk; recorded for the process-gap follow-up.

### RISK-2 (informational): merge preflight blocked on a reconstructed branch name
**Type**: tooling · **Severity**: LOW (worked around; ticketed)
**Location**: `src/specify_cli/cli/commands/merge.py:1147` (`_check_mission_branch`)
**Analysis**: Preflight reconstructs `kitty/mission-{slug}` (mid8-less) instead of reading `lanes_manifest.mission_branch`; blocked `spec-kitty merge` until a harmless alias branch was created. Not a mission-code defect (merge tooling). Filed as **#1978**.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `profiles/manifest.py` `_opt_str/_opt_int` | legacy 6-field entry missing new key | returns `None` | **None — intentional & documented** backward-read default (FR-002 requirement); not error-swallowing |
| `profiles/projection.py::render` | no renderer for tool / profile id not loaded | returns `None` | **None — intentional & documented** control flow (docstring); explicit sentinel, not `except: return ""` |

No genuine silent-failure (`except Exception: return ""`/`pass`) patterns found in mission-touched code.

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|----------------|
| `paths.py` env override now authoritative for any existing path | `core/paths.py:89-92` | path-resolution scope | Accepted — `env_path.exists()` guard retained; C-003 regression test proves real `.kittify/` projects resolve identically with/without the env var. `SPECIFY_REPO_ROOT` is a trusted operator/CI control, not untrusted input. No traversal/injection surface introduced. |

No subprocess/`shell=True`, network, or credential changes in this mission. No blocking security findings.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale
All eight FRs have closed, adequate spec→WP→test→code chains, verified on the merged tree: live callers exist for the new diagnostics (`diagnose()` at `agent_profiles.py:211`) and the new leaf module (`_agent_roster.py`, 3 `src/` importers) — no dead code; all four finding codes emit at distinct trigger sites; the docs-lint gate is genuinely CI-collected and drift-discriminating; the manifest reads legacy entries safely. The two false-positive risks that per-WP review would typically miss were caught and fixed by the cycle-2 rejections (WP02 dead `diagnose()`, WP05 uncommitted evidence) — the headline value of the hardened adversarial process. Contract gate (G1) and issue-matrix gate (G4) PASS. The only architectural-gate failure (G2) is a **pre-existing** marker violation in an untouched file (`test_context_info.py`), demonstrably not introduced by this mission and outside any touched surface — it does not force a mission FAIL. No CRITICAL/HIGH finding blocks release; the one MEDIUM (RISK-1) was already remediated on-branch and ticketed (#1979).

### Open items (non-blocking)
- **OPEN-1**: Pre-existing architectural-gate failure — `test_context_info.py` lacks a `pytestmark`. Not this mission's; recommend a one-line fix + (optionally) a ticket so the architectural suite is green for the next mission.
- **OPEN-2 (DRIFT-1)**: Remove the leaked empty `mutants/kitty-specs/test-feature-01KPN4R0/spec.md` and add `mutants/` to `.gitignore`.
- **OPEN-3 (RISK-2 / #1978)**: Merge-preflight `_check_mission_branch` should read `lanes_manifest.mission_branch` (ticketed under epic #1868).
- **OPEN-4 (RISK-1 / #1979)**: Ownership/review-scope gap — a WP can change a shared source surface whose contract is pinned by an un-owned test; surface impacted tests at finalize/merge (ticketed under epic #1931).
- **Note**: WP05's `project_resolver.py` (+27, #1971 4-caller evidence) and WP02's `model.py` (+25, `NativeAgentProfile` provenance fields) are out-of-`owned_files` edits — both documented with rationale and within ownership leeway; no action needed.

## Retrospective Reminder
The canonical post-merge sequence is **mission review → author/verify retrospective → surface findings**. The `retrospective.yaml` was authored at the runtime terminus and is present:
`kitty-specs/tool-surface-contract-residuals-01KV4S5B/retrospective.yaml` (185 lines, committed `64d654f71`).

Next, surface findings while the work is fresh:
- `spec-kitty retrospect summary` — cross-mission aggregation (read-only)
- `spec-kitty agent retrospect synthesize --mission 01KV4S5B` — inspect staged proposals (dry-run); add `--apply` to mutate
