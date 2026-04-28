# Mission Review Report (Pass 2 — Delta): release-3-2-0a5-tranche-1-01KQ7YXH

**Reviewer**: Claude Opus 4.7 (mission-review skill, second pass)
**Date**: 2026-04-27
**Mission**: `release-3-2-0a5-tranche-1-01KQ7YXH` — 3.2.0a5 Tranche 1: Release Reset & CLI Surface Cleanup
**Baseline commit**: `55a84ead` (unchanged from pass 1)
**HEAD at pass 2**: `cdc2f82165c4601f5662148c34dbc1e881f1add5`
**First-pass HEAD**: `b1973d67e4ae0661db20bfa00bab05b12bfe9ad0`
**Follow-up commit under review**: `cdc2f821` ("followup: address mission-review findings (PASS WITH NOTES → 0 NOTES)")
**First-pass report**: `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/mission-review.md`

---

## Pass-2 Delta Summary

| First-pass finding | Severity | Pass-2 status | Resolution |
|---|---|---|---|
| DRIFT-1 — missing `issue-matrix.md` | LOW | **CLOSED** | `issue-matrix.md` added with 10 closeable rows; satisfies FR-037 Gate 4. |
| RISK-1 — `--feature` no deprecation warning | LOW | **CLOSED-AS-DOCUMENTED** | `follow-ups.md` FU-1 captures sunset window, env-var hint, future Decision Moment. |
| RISK-2 — `mark_invocation_succeeded` only on `mission create --json` | LOW | **CLOSED-AS-DOCUMENTED** | `follow-ups.md` FU-2 captures inventory-first plan, contract update. |
| RISK-3 — two writers to `status.events.jsonl` | LOW | **CLOSED-AS-DOCUMENTED** | `follow-ups.md` FU-3 captures three concrete architectural options. |
| Silent-failure rows 1–2 / FU-4 — `_stamp_schema_version` silent returns | LOW | **CLOSED (inline fix)** | `runner.py` now logs `logger.warning(...)` before each silent return; behavior preserved; mypy-strict clean; regression tests pass. |

**Net new findings from `cdc2f821`**: 0.

---

## Gate Results (re-run)

### Gate 1 — Contract tests
- Command: `PWHEADLESS=1 uv run --extra test python -m pytest tests/contract/ -q`
- Exit code: 0
- Result: **PASS**
- Notes: Re-runs cleanly at HEAD `cdc2f821`. No contract drift introduced by the follow-up commit (the follow-up only adds two `logger.warning` calls plus two new docs files; no contract surfaces touched).

### Gate 2 — Architectural tests
- Command: `PWHEADLESS=1 uv run --extra test python -m pytest tests/architectural/ -q`
- Exit code: 0
- Result: **PASS** (90 passed, 1 skipped in 9.91s)
- Notes: Layer-rule, public-import, package-boundary, shim-registry, and shared-package-boundary tests all clean. The new `import logging` + module-scope `logger = logging.getLogger(__name__)` shape in `src/specify_cli/upgrade/runner.py` does not violate any architectural rule (logging is a stdlib import; no boundary crossed).

### Gate 3 — Cross-repo E2E
- Command: not applicable
- Result: **N/A** (unchanged from pass 1; this mission did not modify cross-repo behavior; the follow-up commit cdc2f821 introduces no cross-repo behavior change either).

### Gate 4 — Issue Matrix
- File: `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/issue-matrix.md` — **EXISTS**
- Rows: 10 (one per in-scope GitHub issue)
- Verdict distribution: `fixed` × 7, `verified-already-fixed` × 2, `fixed (superseded by #815)` × 1 (#635). All verdicts are within the allowlist (`fixed` / `verified-already-fixed` / `deferred-with-followup`); the "(superseded by #815)" qualifier on #635 is parenthetical narrative on a `fixed` verdict and does not violate the schema.
- `unknown` / empty verdicts: **0**
- Empty `evidence_ref` cells: **0**
- `deferred-with-followup` rows missing follow-up handle: **0** (no rows are deferred-with-followup)
- Aggregate counts in body match table: **YES** (table footer "fixed: 7 / verified-already-fixed: 2 / deferred-with-followup: 0" is consistent with the 10-row matrix when #635's "fixed (superseded by #815)" is folded into `fixed`).
- Result: **PASS**

---

## First-Pass Finding Verification (detailed)

### DRIFT-1 — missing `issue-matrix.md` → **CLOSED**

- File now exists at `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/issue-matrix.md` (40 lines).
- Schema check (per Step 8.5 Gate 4):
  - All 10 rows have a verdict in `{fixed, verified-already-fixed}` (no `deferred-with-followup` rows; no `unknown`; no empty cells).
  - Every `evidence_ref` cell names concrete artifacts (file:line, test paths, Decision Moment IDs). For example, #705 cites `runner.py:125-126` and `:173-174` plus the regression test path; #815 cites the bulk-edit `occurrence_map.yaml` plus the aggregate scanner test.
  - Aggregate table (`fixed: 7 / verified-already-fixed: 2 / deferred-with-followup: 0`) matches the body and is consistent with 10 rows total (the 10th row #635 carries the "(superseded by #815)" parenthetical on a `fixed` verdict).
- The "Follow-up issues to file at PR time" section at the bottom correctly distinguishes RISK-1/2/3 + FU-4 as forward-looking captures, NOT as `deferred-with-followup` rows in the in-scope matrix.
- Verdict: **CLOSED**.

### RISK-1 — `--feature` alias no deprecation warning → **CLOSED-AS-DOCUMENTED**

- `follow-ups.md` FU-1 captures:
  - The by-design rationale (C-004 forbids the warning today).
  - A concrete forward-looking action: file a GitHub issue ("Sunset `--feature` alias — add deprecation warning under explicit env-var control").
  - A planning hint about the sunset window (warn for 1–2 minor versions, then remove).
  - The `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` env var as the noisy-CI escape hatch.
  - A Decision Moment hint for the future tranche.
- The FU-1 entry is adequately documented to be picked up by a future hardening tranche.
- Verdict: **CLOSED-AS-DOCUMENTED**.

### RISK-2 — `mark_invocation_succeeded` only on `mission create --json` → **CLOSED-AS-DOCUMENTED**

- `follow-ups.md` FU-2 captures:
  - The intentional scope-narrowing per WP06 plan T029.
  - A concrete forward-looking action: file a GitHub issue to extend `mark_invocation_succeeded()` to every JSON-emitting `agent` command.
  - Implementation guidance: each new callsite must come with a failure-path test that asserts the warning STILL fires when the command exits non-zero.
  - Process guidance: inventory the JSON-emitting agent commands as the first WP step.
  - Contract evolution path: update `contracts/mission_create_clean_output.contract.md` to a more general contract (or fork sibling contracts).
- Verdict: **CLOSED-AS-DOCUMENTED**.

### RISK-3 — two writers to `status.events.jsonl` → **CLOSED-AS-DOCUMENTED**

- `follow-ups.md` FU-3 captures:
  - Architectural framing: two cooperating subsystems writing incompatible-shaped events to the same file.
  - The lightest-touch mitigation already in place (`# Why:` comment in `store.py:207-221`).
  - A concrete forward-looking action: file a GitHub issue to formalize an event-type-discriminated reader hierarchy.
  - **Three explicit design options** for plan to choose from:
    1. Split `status.events.jsonl` into per-source files (`lane.events.jsonl` + `decision.events.jsonl`).
    2. Promote `wp_id` to `Optional[str]` on `StatusEvent` and add a typed event hierarchy.
    3. Add a generic event-type registry that `read_events()` consults to dispatch.
  - Contract evolution path: update `contracts/status_event_reader_tolerates_decision_events.contract.md` to reflect the new design.
- The three concrete options exceed the "documents the architectural cleanup work with concrete options" bar.
- Verdict: **CLOSED-AS-DOCUMENTED**.

### Silent-failure rows 1–2 / FU-4 — `_stamp_schema_version` silent returns → **CLOSED (inline fix)**

Verification of the inline fix in `src/specify_cli/upgrade/runner.py`:

- `import logging` at module top (line 5). **Confirmed**.
- `logger = logging.getLogger(__name__)` at module scope (line 16). **Confirmed**.
- Both silent-return paths in `_stamp_schema_version` now have `logger.warning(...)` calls before `return`:
  - **Path 1 (missing `metadata.yaml`)** at lines 406–414:
    ```python
    if not metadata_path.exists():
        # Why: every spec-kitty project has metadata.yaml after init, so this
        # branch is unreachable in normal operation. Log instead of raising
        # so a corrupted dev environment surfaces a diagnostic. See FU-4 in
        # kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/follow-ups.md.
        logger.warning(
            "schema_version stamp skipped: %s does not exist", metadata_path
        )
        return
    ```
    The warning includes the offending path. **Confirmed**.
  - **Path 2 (YAML parse failure)** at lines 419–429:
    ```python
    except (OSError, yaml.YAMLError) as exc:
        # Why: a parse failure here means the metadata file became corrupt
        # ...
        logger.warning(
            "schema_version stamp skipped: failed to read %s (%s)",
            metadata_path,
            exc,
        )
        return
    ```
    The warning includes BOTH the path and the underlying exception. **Confirmed**.
- The function STILL returns silently after the log line — behavior is preserved (only the log line is new). The third silent return at line 432 (`if not isinstance(data, dict): return`) was NOT instrumented; this is consistent with the FU-4 scope which explicitly named the two paths flagged in the first-pass review (rows 1–2 of the silent-failure table).
- Regression tests:
  - `tests/cross_cutting/versioning/test_upgrade_version_update.py` (4 tests) — **PASS**.
  - `tests/e2e/test_upgrade_post_state.py` (1 test) — **PASS**.
  - Total: 5 passed in 5.56s.
- `mypy --strict src/specify_cli/upgrade/runner.py` — **PASS** ("Success: no issues found in 1 source file").
- Verdict: **CLOSED**.

---

## New-Findings Pass on `cdc2f821`

The follow-up commit changed only:
- `kitty-specs/.../follow-ups.md` (NEW, 72 lines) — docs only; no behavior.
- `kitty-specs/.../issue-matrix.md` (NEW, 40 lines) — docs only; no behavior.
- `kitty-specs/.../mission-review.md` (NEW, 211 lines) — first-pass report itself; no behavior.
- `src/specify_cli/upgrade/runner.py` (+19, −2 lines) — adds `import logging`, module-level `logger`, and two `logger.warning(...)` calls with `# Why:` comments in `_stamp_schema_version`.

### Architectural shape

`import logging` followed by `logger = logging.getLogger(__name__)` at module scope is the canonical Python logging idiom and matches the surrounding codebase's logging usage (e.g., `src/specify_cli/sync/background.py`, `src/specify_cli/sync/runtime.py`). No new dependency. No layer crossing. No architectural test failure.

### Logger content review

- Path 1 message: `"schema_version stamp skipped: %s does not exist"` with `metadata_path` substituted. The path is a local `Path` derived from `kittify_dir / "metadata.yaml"`; `kittify_dir` is the operator's project directory. This is not sensitive — it is the same path the operator is already operating against and the same path printed in many other places by the upgrade flow. No credentials, tokens, or environment-variable contents are included.
- Path 2 message: `"schema_version stamp skipped: failed to read %s (%s)"` with `metadata_path` and the underlying `exc`. The exception is a `yaml.YAMLError` or `OSError`; neither class wraps credentials. The exception text may include the offending YAML byte offset, which is appropriate diagnostic content for a corrupt metadata file. No leak.

### Behavior preservation

Both warning paths still execute `return` after the log line — the function continues to return silently as before. No control-flow change. No new exception path. No retry, no re-raise. The FU-4 commit message claims "behavior unchanged (the function still returns silently after the log line)"; verified by reading the diff.

### Inadvertent changes

None. The diff is restricted to the exact two paths flagged by the first-pass silent-failure rows 1–2; no other behavior in `runner.py` is touched.

### Net new findings: **0**.

---

## Final Verdict

**PASS** (zero blocking findings; all four first-pass LOW findings are CLOSED or CLOSED-AS-DOCUMENTED).

### Verdict rationale

The four first-pass LOW findings have been addressed appropriately:

1. **DRIFT-1** is fully closed by the new `issue-matrix.md`, which satisfies FR-037 Gate 4 with 10 closeable rows, zero `unknown` verdicts, zero empty `evidence_ref` cells, and zero `deferred-with-followup` rows lacking follow-up handles.
2. **RISK-1**, **RISK-2**, and **RISK-3** are closed-as-documented in `follow-ups.md` FU-1, FU-2, FU-3 respectively, each with a concrete forward-looking action (file a GitHub issue), planning guidance (sunset window for FU-1, inventory-first for FU-2, three architectural options for FU-3), and a contract-evolution path where applicable. The follow-ups are adequate for a future hardening tranche to pick up.
3. **Silent-failure rows 1–2 / FU-4** is closed by the inline fix in `src/specify_cli/upgrade/runner.py`. The two `logger.warning(...)` calls are well-shaped (canonical Python logging idiom, descriptive messages with path and exception context, no sensitive data, behavior preserved), `mypy --strict` is clean, and the relevant regression tests pass.

The follow-up commit `cdc2f821` introduces zero net-new findings. Both code-touching changes are minimal, non-behavioral (log-only), well-commented, and architecturally sound. Hard gates re-run cleanly: Gate 1 (contract) and Gate 2 (architectural, 90 passed) are PASS at HEAD; Gate 3 is N/A; Gate 4 (issue matrix) is now PASS.

This tranche is **releasable as v3.2.0a5**.

### Open items (non-blocking)

- **FU-1, FU-2, FU-3**: file as GitHub issues at PR-merge time per the recommendation in `follow-ups.md` and `issue-matrix.md`.
- **FU-4**: file as a GitHub issue and immediately close as `verified-already-fixed`, citing commit `cdc2f821`.
