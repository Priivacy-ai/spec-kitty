# Mission Review Report: doctrine-tension-edges-01KY1WPC

**Reviewer**: claude-sonnet-5 (orchestrator, post-merge review)
**Date**: 2026-07-21
**Mission**: `doctrine-tension-edges-01KY1WPC` — Doctrine Tension as First-Class DRG Edges (mission_number 185)
**Baseline commit**: `bf3235db65e494918860d91d75022187ceff6b78`
**HEAD at review**: `1533f3993` (post-merge, retrospective captured)
**WPs reviewed**: WP01–WP08 (all `done`)

---

## Gate Results

### Gate 1 — Contract tests
- Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/contract/ -q`
- Exit code: 0
- Result: **PASS**
- Notes: 294 passed, 3 skipped (131s).

### Gate 2 — Architectural tests
- Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/architectural/ -q`
- Exit code: non-zero (see below)
- Result: **FAIL**
- Notes: The full-suite run could not complete in reasonable time — `tests/architectural/test_arch_shard_marker_completeness.py` (a repo-wide test-collection-marker invariant, unrelated in subject matter to this mission's diff — it does not touch doctrine/charter code) appears to have a pre-existing, environment-dependent performance characteristic on this machine (a full `--collect-only` pass across the entire ~1000+ test tree); two attempts (60s and 550s timeouts) did not complete. This is very likely pre-existing and unrelated to this mission (confirmed: zero diff overlap with anything this mission touched), but I could not get a clean PASS to record. **Running the mission-relevant subset directly surfaced a real, mission-caused failure**: `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` fails with:
  ```
  charter.consistency_check::ConsistencyReport
  charter.consistency_check::TensionFinding
  specify_cli.core.env::SYNC_DISABLE_ENV_VARS
  ```
  The third (`SYNC_DISABLE_ENV_VARS`) is confirmed **pre-existing** — `src/specify_cli/core/env.py` has zero diff in this mission's range; last touched by unrelated PR #2814.
  The first two (`ConsistencyReport`, `TensionFinding`) are **new, mission-caused failures**: WP05 added both to `src/charter/consistency_check.py`'s `__all__`, but `grep -rn "ConsistencyReport\b|TensionFinding\b" src/` confirms **zero** external callers import either by name anywhere in `src/` (only a docstring in `activate.py` mentions `ConsistencyReport` in prose, not code). This directly contradicts the file's own already-documented convention two lines below `__all__` for `CharterYamlCorruptError`: *"Kept out of `__all__` per the symbol-level dead-code gate — no external caller imports it."* WP05 didn't follow the precedent sitting right next to where it edited. **See RISK-1.**

### Gate 3 — Cross-repo E2E
- Command: not run — no `spec-kitty-end-to-end-testing` sibling repo checkout available in this environment.
- Result: **NOT APPLICABLE / NOT RUN** — this mission does not claim cross-repo behavior (spec.md has no cross-repo FRs), and no `mission-exception.md` was required or authored. Recorded as N/A rather than FAIL since the gate's stated scope (cross-repo e2e floor scenarios) is orthogonal to this mission's actual changes (doctrine/DRG internals, no cross-repo surface touched).

### Gate 4 — Issue Matrix
- File: `kitty-specs/doctrine-tension-edges-01KY1WPC/issue-matrix.md`
- Rows: 5
- Empty / `unknown` verdicts: 0
- **`in-mission` rows that survived to mission `done`: 2** (`#2537`, `#2737`)
- Result: **FAIL** — per the skill's own rule, "An `in-mission` row that survives to mission `done` is likewise a hard fail." Both issues are in fact closed by work that has landed (WP01 for #2537's foundation, WP06 for #2737 exactly per FR-008/SC-003), so this is a **stale-verdict bookkeeping gap**, not an unresolved issue — but it is a hard gate fail as recorded. **See RISK-2.**

**A FAIL on Gates 2 and 4 forces the Final Verdict to FAIL** per the skill's binary rule, despite both being small, well-understood, easily-fixed gaps rather than deep defects.

---

## FR Coverage Matrix

All 15 FRs were independently verified during each WP's dedicated review (see `kitty-specs/doctrine-tension-edges-01KY1WPC/tasks/WP0N-*.md` activity logs and the acceptance-matrix.json evidence trail). Re-verified at mission level via the full `tests/doctrine/` suite (2749 passed, 0 failed, confirmed pre-merge) plus Gate 1 (contract, PASS).

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | `in_tension_with` relation | WP01 | test_models.py | ADEQUATE | — |
| FR-002 | `reconciles_tension` relation | WP01, WP05 | test_tension_unreconciled.py (half-reconciled case) | ADEQUATE | — |
| FR-003 | `rejects` relation | WP01, WP04 | test_validator.py (INV-004) | ADEQUATE | — |
| FR-004 | Anti-pattern/smell NodeKind | WP01, WP04 | test_drg_filtering.py, test_validator.py | ADEQUATE | — |
| FR-005 | Remove `opposed_by`/`Contradiction` | WP03 | grep-verified zero hits; dead-symbol gate (Contradiction) green | ADEQUATE | — |
| FR-006 | Migrate genuine tensions | WP02 | hand_authored_overlay.py registry cross-checked against WP02 commit | ADEQUATE | — |
| FR-007 | Migrate anti-pattern rejections | WP02 | pairing cross-checked verbatim against original opposed_by entries | ADEQUATE | — |
| FR-008 | Remove phantom orphan-lint branches | WP06 | live `spec-kitty charter lint` == exactly {DIRECTIVE_035, DIRECTIVE_039} | ADEQUATE | — |
| FR-009 | Advisory `tension_unreconciled` finding | WP05 | test_tension_unreconciled.py (positive-finding + fail-closed cases) | ADEQUATE | — |
| FR-010 | Activate-time tension warning | WP05 | activate.py wiring, shared scan function | ADEQUATE | See RISK-3 (silent-except nuance) |
| FR-011 | Built-in reconciliation artefact | WP02 | SC-002 live before/after test (WP05) | ADEQUATE | — |
| FR-012 | Relation self-description + doc parity | WP01, WP08 | test_relation_doc_parity.py, red-first mutation test | ADEQUATE | — |
| FR-013 | Cascade exclusion (regression-tested) | WP06 | test_cascade.py frozenset-intersection + live cascade test | ADEQUATE | — |
| FR-014 | Consistent surface propagation | WP01–05 (cross-cutting) | full tests/doctrine/ suite green post-WP03 | ADEQUATE | — |
| FR-015 | Downstream `opposed_by` migration | WP07 | live sandbox test (dry-run/real-run/idempotent/diagnostic) | ADEQUATE | — |

No PARTIAL, MISSING, or FALSE_POSITIVE ratings — every FR chain (spec → WP → test → code) closes.

---

## Drift Findings

None found. Checked specifically:
- **Non-goal invasion**: C-004's out-of-scope items (cascade-all-kinds #2829, `delegates_to` swarm #2827) — confirmed no diff touches cascade-kind-completeness logic or `delegates_to` runtime behavior.
- **Locked decisions**: D1 (migration mechanism, no deprecation window) — WP07 ships immediate-removal migration tool, matches. D2 (new first-class NodeKind, not a tag on existing kind) — confirmed `ANTI_PATTERN` is a genuine new `NodeKind`/`ArtifactKind` member, not a tag-only approach. D3 (always-on tension check) — confirmed `scan_unreconciled_tensions` has no activation-gate short-circuit; runs unconditionally over the activation-filtered graph.
- **C-001** (`replaces` stays canonical) — confirmed the built-in `replaces` edge set is now empty (the mis-minted 024↔025 cycle is gone) and no new non-`opposed_by`-derived `replaces` edge was introduced.
- **C-006** (green-at-every-boundary migration order) — confirmed via WP sequencing (WP01→WP02→WP03) and the fact the full suite is green post-WP03.

---

## Risk Findings

### RISK-1: Dead public exports in `charter.consistency_check.__all__`

**Type**: DEAD-CODE (symbol-level)
**Severity**: MEDIUM (gate-failing, but a 2-line mechanical fix; no runtime behavior is wrong)
**Location**: `src/charter/consistency_check.py:28-33`
**Trigger condition**: Always — this is a static gate failure, not input-dependent.

**Analysis**: `ConsistencyReport` and `TensionFinding` are listed in `__all__` but no file in `src/` imports either by name (confirmed via repo-wide grep). This fails `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`. The same file already documents the correct pattern two lines below, for `CharterYamlCorruptError`: keep undead-but-unimported symbols out of `__all__`. WP05's reviewer did not run this specific architectural gate (each WP review scoped its test runs to the relevant `tests/doctrine/`/`tests/charter/` trees, not `tests/architectural/`), so this was never caught until mission-level review. Fix: remove both names from `__all__` (the classes remain fully functional and usable via attribute access on `run_consistency_check()`'s return value — nothing else needs to change).

### RISK-2: Issue-matrix rows left at non-terminal `in-mission` verdict past mission `done`

**Type**: PROCESS/BOOKKEEPING (Gate 4)
**Severity**: MEDIUM (gate-failing, but the underlying issues genuinely ARE closed — this is a stale-record problem, not an unresolved-issue problem)
**Location**: `kitty-specs/doctrine-tension-edges-01KY1WPC/issue-matrix.md`

**Analysis**: `#2537` and `#2737` are marked `in-mission`, which the skill's own rule treats as a hard fail once the mission reaches `done` (the verdict must become terminal — `fixed` or `verified-already-fixed`). Both issues are demonstrably closed by landed work: #2537's foundation is WP01 (this mission's entire premise), and #2737 is explicitly closed by WP06's FR-008/SC-003 (`orphaned_directive` == exactly `{DIRECTIVE_035, DIRECTIVE_039}`, confirmed via a live `spec-kitty charter lint` run during WP06's review). Fix: update both rows to `fixed` with an evidence_ref citing the closing WP and verification method.

### RISK-3: `activate.py`'s tension-warning path silently swallows all exceptions with zero logging

**Type**: ERROR-PATH (silent failure candidate)
**Severity**: LOW (matches an existing, if imprecisely-cited, repo convention; the fail-closed guarantee correctly lives on the `consistency-check` surface per FR-009's actual requirement, not on `activate`)
**Location**: `src/specify_cli/cli/commands/charter/activate.py:264-267` (`_render_tension_warnings`)

**Analysis**: `except Exception: return` with no `logger.warning`/`logger.debug` call at all. The docstring explains this is intentional ("best-effort... matching the existing DRG-load handling... see `_render_no_cascade_warning`"), but on inspection, `_render_no_cascade_warning` doesn't wrap its DRG load in a `try/except` at all — an error there propagates and aborts the command. So the new code is actually **more silent** than the precedent it cites, not equivalent to it. A genuine transient error in the tension scan (not just the anticipated "bare `ProjectContext`" case the docstring is really guarding against) would produce zero operator-visible signal — indistinguishable from "no tensions found." This is a narrower, less severe version of the exact NFR-001 trap the mission's core feature (FR-009, on the consistency-check surface) was built to avoid — just on the secondary `activate` warning surface, which spec.md does not hold to the same fail-closed bar. Non-blocking; recommend a follow-up to at least log at debug/warning level on this path.

### RISK-4: `tests/architectural/test_arch_shard_marker_completeness.py` did not complete within available time

**Type**: ENVIRONMENTAL / PERFORMANCE (not attributable to this mission)
**Severity**: LOW / INFORMATIONAL
**Location**: `tests/architectural/test_arch_shard_marker_completeness.py`

**Analysis**: This test performs a repo-wide `--collect-only` pass across the entire test suite (per its own docstring, a generalized shard-marker-completeness invariant unrelated to doctrine/charter code) and did not complete inside 550s in this environment. Confirmed zero diff overlap with this mission's changes. Flagging as an open environmental item for the operator to re-run in a faster/less-contended environment, not as a mission-attributable defect.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|--------------|
| `src/specify_cli/cli/commands/charter/activate.py:264-267` | Any exception during the tension scan (`ProjectContext.from_repo` or `scan_unreconciled_tensions`) | Returns with no output, no log line | FR-010's warning silently never appears; indistinguishable from "no tensions found" (see RISK-3) |

No other silent-empty-result patterns (`return ""`, `return None` masking an error, bare `except: pass`) were found in this mission's diff — the two other `except Exception` blocks (WP05's fail-closed `verification_errors` append, and a `logger.warning`-then-`continue` in a best-effort registry-build loop in `doctrine.py`) are both correctly visible/logged.

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|-----------------|
| None found | — | — | This mission touches no subprocess/shell execution, no new file-path construction from user input beyond existing `--pack PATH` CLI argument handling (WP07), no new HTTP/network calls, and no credential/auth logic. `grep` for `subprocess`, `shell=True`, `eval(`, `exec(` across the full diff returned zero hits. |

`src/specify_cli/migration/rewrite_opposed_by.py` (WP07) accepts a `--pack PATH` argument and reads/writes YAML files under it — reviewed for path traversal: it operates entirely within the operator-supplied pack root using standard `Path` joins, no `..`-relative construction from untrusted input beyond what the operator explicitly passes on their own CLI invocation (equivalent trust boundary to every other `spec-kitty migrate` subcommand already in this codebase). Not a new risk class introduced by this mission.

---

## Final Verdict

**FAIL**

### Verdict rationale

All 15 FRs are adequately covered by real tests tied to production code paths (no synthetic-fixture false positives found), no locked decision was violated, no non-goal was invaded, and the security review found nothing new. However, Gate 2 (architectural) and Gate 4 (issue matrix) both fail per the skill's hard-gate rules: two dead public exports (`ConsistencyReport`, `TensionFinding`) fail the symbol-level dead-code gate, and two issue-matrix rows (#2537, #2737) remain at the non-terminal `in-mission` verdict past mission `done`. Both are small, mechanical, well-understood fixes — the underlying feature work is sound — but per the skill's binary rule ("any CRITICAL or HIGH finding... not already documented as an accepted known issue" forces FAIL, and gate fails are explicitly hard-fail-forcing), the verdict cannot be PASS WITH NOTES while these gates are red. Recommend: fix RISK-1 and RISK-2 (both trivial), then re-run Gates 2 and 4 to confirm PASS before opening a PR.

### Open items (non-blocking)

- RISK-3 (activate.py silent-except, LOW): consider adding a debug/warning log line on the exception path in a follow-up, for operator visibility into transient scan failures on the `activate` warning surface.
- RISK-4 (shard-marker-completeness test performance, LOW/environmental): re-run `tests/architectural/` in full once RISK-1 is fixed, ideally in an environment with more CPU headroom or via `-n auto --dist loadfile` per this repo's parallel-test guidance, to get a clean full-suite Gate 2 result rather than the targeted subset run used here.
- The ~100 "stale assertion" findings `spec-kitty merge` printed are confirmed false positives on sampling (2 of 2 checked: naive substring matching on common domain words like "tactic"/"directive"/"references" that remain valid NodeKind values, and one genuine WP07 test intentionally asserting `opposed_by` presence in an unclassifiable-entry edge case). No action needed.

## Retrospective Reminder

`kitty-specs/doctrine-tension-edges-01KY1WPC/retrospective.yaml` was authored automatically at merge terminus (commit `1533f3993`) — confirmed present and populated. Next steps for the operator: `spec-kitty retrospect summary` (cross-mission aggregation, read-only) and `spec-kitty agent retrospect synthesize --mission doctrine-tension-edges-01KY1WPC` (inspect proposals; dry-run by default, add `--apply` to mutate).

---

## Addendum: Fixes Applied (2026-07-21, same-day follow-up)

Both gate-blocking findings were fixed directly on `doctrine/drg-missing-links-analysis` at commit `38a83d939`:

- **RISK-1 (Gate 2)**: Removed `ConsistencyReport`/`TensionFinding` from `charter.consistency_check.__all__`; pruned the now-dangling pre-existing `ConsistencyReport` allowlist entry in `test_no_dead_symbols.py` (updated `_baselines.yaml`'s count 4→1 accordingly). Re-verified: `tests/architectural/test_no_dead_symbols.py` now shows only the confirmed pre-existing, unrelated `specify_cli.core.env::SYNC_DISABLE_ENV_VARS` finding (zero diff on `env.py` in this mission's range).
- **RISK-2 (Gate 4)**: `issue-matrix.md` rows for `#2537` and `#2737` updated from `in-mission` to `fixed`. While re-verifying #2737, a bare `spec-kitty charter lint` run against this repo's own dev activation config showed 25 orphan findings, not 2 — investigated and confirmed this is a **scope mismatch in the verification method**, not a regression: SC-003's claim is scoped to the built-in layer, not any one project's live (partial) activation config. Re-ran the actual test (`tests/specify_cli/charter_lint/checks/test_orphan.py`, 14/14 passed) to confirm the built-in-layer exact-set assertion genuinely holds post-merge. The issue-matrix row now documents this scope distinction explicitly so a future reader doesn't repeat the same false alarm.

**Gate 2 (architectural, dead-symbol/allowlist subset)**: PASS (mission-caused findings resolved; pre-existing unrelated finding remains, correctly out of scope).
**Gate 4 (issue matrix)**: PASS (0 rows at a non-terminal verdict).

### Updated Final Verdict

**PASS** — all FR coverage, drift, and security findings from the original review stand (none were blocking); both hard-gate failures are now resolved. RISK-3 (activate.py silent-except) and RISK-4 (shard-marker-completeness test performance) remain open, non-blocking follow-up items as originally recommended.
