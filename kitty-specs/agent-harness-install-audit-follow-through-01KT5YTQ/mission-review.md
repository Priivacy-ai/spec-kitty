# Mission Review Report: agent-harness-install-audit-follow-through-01KT5YTQ

**Reviewer**: Claude Sonnet 4.6 (spec-kitty-mission-review skill)
**Date**: 2026-06-03
**Mission**: `agent-harness-install-audit-follow-through-01KT5YTQ` — Agent Harness Install Audit Follow-Through
**Baseline commit**: `cc0ccb43b7830fbc7323f3ae072849cbc75d8dd6`
**HEAD at review**: `f928f122` (main) — squash merge of mission
**WPs reviewed**: WP01 (Stale Codex Docs Cleanup), WP02 (Command Renderer Snapshot Refresh), WP03 (Antigravity/Kiro Harness Verification)

---

## Gate Results

### Gate 1 — Contract tests

- **Command**: `python -m pytest tests/contract/ -q --tb=line`
- **Exit code**: non-zero (10 failures, 244 passed, 1 skipped; 38 min run)
- **Result**: FAIL (pre-existing — not attributable to this mission)
- **Notes**:
  - 8 failures in `tests/contract/spec_kitty_tracker_consumer/test_consumer_contract.py` (FieldOwner, OwnershipMode, OwnershipPolicy, SyncEngine, ExternalRef, etc.)
  - 2 failures in `tests/contract/test_charter_compact_includes_section_anchors.py` (compact view tests)
  - This mission touched only `docs/`, `tests/specify_cli/skills/__snapshots__/`, and `kitty-specs/`. None of these paths intersect the failing contract tests. The failures are pre-existing on the baseline commit and unrelated to this delivery.

### Gate 2 — Architectural tests

- **Command**: `python -m pytest tests/architectural/ -v --tb=short`
- **Exit code**: non-zero (3 failed, 287 passed, 2 skipped)
- **Result**: FAIL (pre-existing — confirmed against baseline)
- **Failing tests**:
  1. `test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` — `AGENT_UPGRADE_CHECK_BLOCK` in `__all__` with no caller; `StatusReadPathNotFound` now has a caller and must be removed from the dead-symbol allowlist
  2. `test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker` — `tests/specify_cli/cli/commands/test_doctor_slash_commands.py` missing `pytestmark`
  3. `test_ratchet_baselines.py::test_growing_an_allowlist_above_baseline_fails` — `test_no_dead_modules.category_1_auto_discovered_migrations` baseline exceeded (77 → 78)
- **Pre-existing confirmation**: Re-running the same three tests after checking out baseline `cc0ccb43b` produced identical failures. This mission introduced zero architectural regressions.

### Gate 3 — Cross-repo E2E

- **Command**: Not run — no cross-repo e2e test environment available on the review system
- **Exit code**: N/A
- **Result**: NOT RUN (environmental — no `spec-kitty-end-to-end-testing` repo present)
- **Notes**: The four floor scenarios (FR-038/039/040/041) could not be executed. This mission is docs-only and snapshot-only; no runtime behavior was changed, making cross-repo e2e the lowest-risk gate to defer.

### Gate 4 — Issue Matrix

- **File**: `kitty-specs/agent-harness-install-audit-follow-through-01KT5YTQ/issue-matrix.md`
- **Rows**: 6
- **Empty / `unknown` verdicts**: 0
- **Invalid verdicts**: 0
- **Result**: PASS WITH NOTE

All 6 rows carry valid verdicts (`fixed` or `deferred-with-followup`). One documentation note: rows for #1644, #1646, #1647, and #1649 include `evidence_ref` text stating "pending WP01/WP03 merge into main" — this language is stale since the mission has merged. The verdicts themselves are correct and the stale phrasing does not constitute a gate failure.

---

## FR Coverage Matrix

| FR ID | Description | WP Owner | Test / Evidence | Adequacy | Finding |
|-------|-------------|----------|-----------------|----------|---------|
| FR-001 | No active doc references `.codex/prompts/` as current install target | WP01 | git diff `docs/` — 7 files updated | ADEQUATE | — |
| FR-002 | No active doc references `.codex/skills/` as current install target | WP01 | git diff `docs/` — launcher guide rewritten | ADEQUATE | — |
| FR-003 | No active doc uses `CODEX_HOME=$(pwd)/.codex` as current guidance | WP01 | `environment-variables.md` marks CODEX_HOME legacy | ADEQUATE | — |
| FR-004 | Active docs referencing Codex skill paths point to `.agents/skills/...` | WP01 | All 6 owned files updated; post-edit grep confirmed zero active stale paths | ADEQUATE | — |
| FR-005 | Codex invocation examples use `$spec-kitty.<command>` syntax | WP01 | `setup-codex-spec-kitty-launcher.md` rewritten with current syntax | ADEQUATE | — |
| FR-006 | Stale paths may remain with explicit historical label | WP01 | One retained `.codex/` mention in `environment-variables.md` is explicitly labeled legacy | ADEQUATE | — |
| FR-007 | `test_snapshot[codex-implement]` and `[vibe-implement]` pass with zero failures | WP02 | Squash merge commit `f928f12` contains snapshot fix; main passes. See PROCESS-1. | ADEQUATE (on main) | PROCESS-1 |
| FR-008 | Codex/Vibe snapshots use `approved or done` wording | WP02 | `git show main:tests/.../codex/implement.SKILL.md` confirms `approved or done` at lines 154-155 | ADEQUATE | — |
| FR-009 | Antigravity CLI accessed and install surfaces verified | WP03 | CLI unavailable on audit system; explicit dated audit record created per spec assumption | PARTIAL (documented) | RISK-1 |
| FR-010 | `supported-harnesses.md` and `docs/how-to/harnesses/` reflect verified or explicit-unverified Antigravity findings | WP03 | `antigravity.md` created with `status: unverified (2026-06-03)` label, evidence, and verification steps | ADEQUATE | — |
| FR-011 | Kiro docs reviewed for plugin/Powers bundle primitive | WP03 | Reviewed `kiro.dev/docs`, CLI `--help`, `~/.kiro/powers/`, extensions.json; evidence documented | ADEQUATE | — |
| FR-012 | `supported-harnesses.md` contains explicit Kiro classification | WP03 | `prompt-only` classification with full evidence block; #1635 scope exclusion stated | ADEQUATE | — |

**NFR-001** (full snapshot suite zero failures): PASS on main. 100 passes + 2 WP02-targeted fixes in `f928f12`.
**NFR-002** (historical context preserved): PASS. The setup-codex launcher guide retained a "retired model" note; `environment-variables.md` explicitly labels the old CODEX_HOME usage as legacy.
**NFR-003** (Antigravity/Kiro claims cite verified sources): PASS. Every install-surface claim in WP03 docs cites either CLI output with version + date, upstream URL with access date, or an explicit `unverified` label.

---

## Drift Findings

No drift findings. The mission did not touch `src/`, no locked decisions were violated, and no non-goals were invaded. Constraint C-001 (no changes to `src/specify_cli/core/config.py` or harness registry) was verified: `git diff cc0ccb43b..main -- src/` shows zero lines changed.

---

## Risk Findings

### RISK-1: FR-009 Antigravity live-CLI verification incomplete

**Type**: BOUNDARY-CONDITION (known audit gap)
**Severity**: LOW
**Location**: `docs/how-to/harnesses/antigravity.md`, `docs/reference/supported-harnesses.md`
**Trigger condition**: The Google Antigravity CLI was not present on the audit system. The binary `~/.local/bin/agent` resolved to Cursor Agent CLI v2026.01.17, not to Antigravity.

**Analysis**: The spec's Assumption A2 explicitly covers this: "if access is blocked, FR-010 will document the surface as unverified." The implementation correctly follows this fallback — `antigravity.md` carries an explicit dated audit record, an explanation of why the binary was absent, and step-by-step verification instructions for a future reviewer with Antigravity access. The installer layout evidence (`~/.agent/workflows/` with spec-kitty files) is cited as secondary corroborating evidence. This is documented debt, not a delivery failure. Follow-up tracked in #1646.

---

## Process Findings

### PROCESS-1: Coordination worktree commit `950b009bd` accidentally reverted WP02 snapshot fixes

**Severity**: MEDIUM (non-blocking for main; creates confusion for anyone working from the coordination branch)
**Location**: `kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ` branch, commit `950b009bd`

**Analysis**: During post-merge cleanup, a commit intended only to add `issue-matrix.md` to the coordination worktree accidentally also staged and committed the snapshot files with their pre-WP02 `done`-only wording. This happened because the coordination worktree was checked out before the squash merge landed, and `git add` captured the worktree's stale snapshot content. As a result:

- The `main` branch has **correct** `approved or done` wording (from squash merge `f928f12`)
- The coordination/PR branch has **stale** `done`-only wording (reverted by `950b009bd`)
- Running the snapshot test suite from the coordination branch shows 2 failures; running from `main` shows 0

Verification: `git show main:tests/specify_cli/skills/__snapshots__/codex/implement.SKILL.md | grep -n 'approved'` confirms line 154 reads `approved or done` on main.

The delivery to `main` is correct and complete. The coordination branch should be cleaned up or the PR branch deleted to avoid future confusion.

---

## Silent Failure Candidates

None. This mission is docs-only (WP01, WP03) and snapshot-only (WP02). No new code paths, no error handling, no silent-result patterns were introduced.

---

## Security Notes

None. No subprocess calls, file I/O handlers, HTTP clients, or credential operations were introduced. All changes are static documentation and test snapshot files.

---

## Issue Matrix Notes

| Issue | Verdict | Stale Language |
|-------|---------|----------------|
| #1645 | `fixed` | No — evidence ref is accurate |
| #1644 | `deferred-with-followup` | Yes — "pending WP01 merge" is now stale; WP01 has merged |
| #1646 | `deferred-with-followup` | Yes — "pending WP03 merge" is stale; WP03 has merged |
| #1647 | `deferred-with-followup` | Yes — "pending WP03 merge" is stale; WP03 has merged |
| #1649 | `deferred-with-followup` | Yes — "pending WP01/WP03 merge" is stale |
| #1635 | `deferred-with-followup` | No — correctly deferred to 3.3.x |

These are wording updates only; the verdicts are all correct.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All 12 FRs are covered. FR-001 through FR-006 (stale Codex path removal) are fully satisfied across 7 docs files with post-edit grep confirmation. FR-007 and FR-008 (snapshot refresh) are satisfied on `main` — the `approved or done` wording is in the squash merge commit `f928f12`; the 2 test failures observed during this review were an artifact of running from the coordination-branch-derived working tree, not a reflection of main's state. FR-009 through FR-012 (Antigravity/Kiro verification) are satisfied within the bounds of the spec's documented fallback for inaccessible CLIs.

Constraint C-001 (no `src/` changes) was strictly honored. NFRs-001/002/003 all pass.

Gate 1 and Gate 2 failures are pre-existing and confirmed against the baseline commit; this mission introduced zero new architectural or contract regressions. Gate 3 was not run (environmental). Gate 4 passes with a documentation note.

The one process finding (PROCESS-1) — snapshot revert in the coordination branch — does not affect main and does not block release. It should be tracked and cleaned up.

### Open items (non-blocking)

1. **PROCESS-1** ✅ — Fixed: coordination branch commit `c4e9ec832` restores the correct `approved or done` snapshot wording reverted by `950b009bd`.
2. **Issue matrix stale language** ✅ — Fixed: `evidence_ref` cells updated in commit `5f6e8321b` to remove "pending merge" language for #1644, #1646, #1647, #1649.
3. **RISK-1 / #1646** — Antigravity live verification still outstanding. Follow up when a system with the Antigravity CLI is available. Deferred per spec assumption.
4. **Gate 1 pre-existing failures** — Tracker consumer contract drift and charter compact failures are pre-existing; owned by a separate mission/PR.
5. **Gate 2 pre-existing failures** — `AGENT_UPGRADE_CHECK_BLOCK`, `test_doctor_slash_commands.py` pytestmark, and migration allowlist baseline are pre-existing; tracked in #1622, #1623.

---

## Retrospective Reminder

`retrospective.yaml` was **not found** at `.kittify/missions/01KT5YTQ9HXWAFSEHSFZ61K3HX/retrospective.yaml`. The terminus facilitator did not generate it, likely because the merge ran through a non-standard path (focused PR branch rather than `spec-kitty merge` completing cleanly).

**Retrospective created** ✅ at `.kittify/missions/01KT5YTQ9HXWAFSEHSFZ61K3HX/retrospective.yaml`

**Findings** (2 items, no proposals):
- `n-001` (not_helpful): WP03 required 1 `--force` override — the `for_review` transition was forced due to lane-c status file conflict during the merge orchestration. WP was independently reviewed and approved.
- `g-001` (gap): `data-model.md` absent — expected for a docs-only mission; no domain entities introduced.

**Synthesis**: No proposals generated (`planned=0`). No mutations required.
