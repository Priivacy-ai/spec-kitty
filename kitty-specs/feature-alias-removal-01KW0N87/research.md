# Research: Remove hidden --feature alias from user-facing CLI commands

**Mission**: `feature-alias-removal-01KW0N87`
**Phase**: Plan — Phase 0 Research
**Branch**: `feat/feature-alias-removal`
**Date**: 2026-06-26

---

## Summary

This document records the codebase audit performed during planning. All findings are derived from
`src/specify_cli/cli/commands/` in the clone at `/tmp/sk-1797/m1060-feature-alias-removal`.
No design decisions remain open; the spec is fully self-answering for this scope.

---

## Caller-Audit Evidence Table

### Table 1 — In-Scope Files: Option Site, resolve_selector Calls, Rename Targets

| File | `--feature` Typer Option site (file:line) | `resolve_selector` call(s) with `alias_flag="--feature"` (file:line) | Internal `feature`/`feature_slug` params/vars to rename |
|------|------------------------------------------|-----------------------------------------------------------------------|--------------------------------------------------------|
| `implement.py` | `:934` — `feature: Annotated[str\|None, typer.Option("--feature", hidden=True, ...)] = None` in `implement()` | **None** — uses `detect_feature_context()` / `resolve_mission_handle` directly | `feature` param in `implement()` :934; `feature` param in `_run_recover_mode()` :836; `feature_flag` param in `detect_feature_context()` :144; `raw_handle = mission_flag or feature_flag` :155; `_feature_number` at :851 and :999 |
| `merge.py` | `:412` — `feature: str = typer.Option(None, "--feature", hidden=True, ...)` in `merge()` | **None** — uses `(mission or feature or "").strip()` directly | `feature` param in `merge()` :412; `feature` param in `_resolve_slug_or_exit()` :231; `feature` param in `_dispatch_abort()` :277; `feature` param in `_dispatch_resume()` :328; `resolved_feature` local var in `merge()` :453+, in `_run_real_merge()` :350, and in `_dispatch_resume()` |
| `next_cmd.py` | `:71-74` — `feature: Annotated[str\|None, typer.Option("--feature", hidden=True, ...)] = None` in `next()` | `:333` — inside private helper `_resolve_mission_slug(mission, feature, repo_root)` | `feature` param in `next()` :71; `feature` param in `_resolve_mission_slug()` :331 |
| `research.py` | `:33-38` — `feature: str\|None = typer.Option(None, "--feature", hidden=True, ...)` in `research()` | `:67` — direct call, result unwrapped with `.canonical_value` | `feature` param in `research()` :33; StepTracker string key `"feature"` at :55, :65, :76, :115 (optional, cosmetic) |
| `context.py` | `:244` — `feature: Annotated[str\|None, typer.Option("--feature", hidden=True, ...)] = None` in `mission_resolve_command()` | `:269` — direct call, result unwrapped with `.canonical_value` | `feature` param in `mission_resolve_command()` :244 |
| `accept.py` | `:231-236` — `feature: str\|None = typer.Option(None, "--feature", hidden=True, ...)` in `accept()` | **None** — uses `raw_handle = mission or feature` then `resolve_mission_handle` | `feature` param in `accept()` :231; `feature_slug` param in `_spec_artifact_dirty_paths()` :43; `feature_slug` param in `_commit_residual_acceptance_artifacts()` :73 (local var throughout both functions) |
| `lifecycle.py` | `:169` — `feature: str\|None = typer.Option(None, "--feature", hidden=True, ...)` in `plan()`; `:258` — same pattern in `tasks()` | `:176` — in `plan()` inside `if mission is not None or feature is not None:` block; `:266` — in `tasks()` inside `if mission is not None or feature is not None:` block | `feature` param in `plan()` :169; `feature` param in `tasks()` :258; **positional** `feature: str = typer.Argument(...)` in `specify()` :126 (orchestrator ruling: rename → `mission`, metavar `FEATURE`→`MISSION`) |
| `mission_type.py` | `:207-210` — `feature: Annotated[str\|None, typer.Option("--feature", hidden=True, ...)] = None` in `current_cmd()` | `:246` — inside `if mission is None and feature is None:` `else:` branch | `feature` param in `current_cmd()` :207; `if mission is None and feature is None` at :217 and :239 |

---

### Table 2 — `resolve_selector` Callers Repo-Wide: In-Scope vs Out-of-Scope Classification

`resolve_selector` is defined at `src/specify_cli/cli/selector_resolution.py:123`.

| Caller file | Call site (file:line) | `alias_flag` value | Classification | Action |
|-------------|----------------------|--------------------|----------------|--------|
| `research.py` | `:67` | `"--feature"` | **IN-SCOPE** | Remove call; replace with inline whitespace-normalization guard |
| `next_cmd.py` | `:333` | `"--feature"` | **IN-SCOPE** | Remove call inside `_resolve_mission_slug()`; inline guard |
| `context.py` | `:269` | `"--feature"` | **IN-SCOPE** | Remove call; inline guard |
| `lifecycle.py` | `:176` | `"--feature"` | **IN-SCOPE** (in `plan()`) | Remove call; inline guard |
| `lifecycle.py` | `:266` | `"--feature"` | **IN-SCOPE** (in `tasks()`) | Remove call; inline guard |
| `mission_type.py` | `:246` | `"--feature"` | **IN-SCOPE** (in `current_cmd()`) | Remove call; inline guard |
| `lifecycle.py` | `:136` | `"--mission"` | **OUT-OF-SCOPE** — aliases `--mission-type` → `--mission`; unrelated to `--feature` | **Untouched** |
| `charter/generate.py` | `:276` | `"--mission"` | **OUT-OF-SCOPE** — aliases `--mission-type` → `--mission` | **Untouched** |
| `charter/interview.py` | `:92` | `"--mission"` | **OUT-OF-SCOPE** — aliases `--mission-type` → `--mission` | **Untouched** |
| `agent/mission_create.py` | `:123` | `"--mission"` | **OUT-OF-SCOPE** — aliases `--mission-type` → `--mission` | **Untouched** |

**Key finding:** Every out-of-scope `resolve_selector` caller uses `alias_flag="--mission"` (aliasing `--mission-type`), NOT `"--feature"`. They are completely unrelated to this mission's change. `resolve_selector` itself is retained (C-005).

`materialize.py:64` and `verify.py:65` mention `resolve_selector()` in comments only — no live calls.

---

### Table 3 — `_legacy_aliases.py` Absence Audit

| Check | Result |
|-------|--------|
| `find src/ -name "_legacy_aliases.py"` | **File does not exist** — confirmed absent |
| `grep -rn "_legacy_aliases" src/` | No matches |

FR-005: confirmed absent at planning time. Implementation must re-confirm at WP execution time.

---

### Table 4 — Stored JSON `feature_slug` Keys (Immutable per C-003)

The following source locations READ `"feature_slug"` as a dict key from persisted artifacts
(`meta.json`, `status.events.jsonl`, `feature-runs.json`). These string constants MUST NOT be renamed.

| File | Usage |
|------|-------|
| `status/validate.py:91` | `if "mission_slug" not in event and "feature_slug" not in event:` |
| `status/models.py:253,308` | `data.get("mission_slug") or data.get("feature_slug", "")` |
| `status/store.py:269` | `raw.get("mission_slug") or raw.get("feature_slug") or ""` |
| `identity/aliases.py:21-22` | Back-compat alias enrichment from `feature_slug` → `mission_slug` |
| `charter_activate.py:197` | `meta.get("mission_slug") or meta.get("feature_slug")` |
| `retrospective/summary.py:198` | `meta.get("mission_slug") or meta.get("feature_slug")` |
| `migration/mission_state.py:241,248,251,1113` | Migration constants and legacy alias table |
| `upgrade/migrations/m_2_0_6_consistency_sweep.py:324` | Migration data field comparison |
| `audit/shape_registry.py:51,69,162` | Back-compat field in audit shape definitions |
| `audit/detectors.py:32` | Back-compat field in detector definitions |
| `sync/batch.py:106` | Field name in sync batch processor |
| `cli/commands/tracker.py:104` | `data.get("feature_slug") or data.get("slug")` |

These are all in files **outside the 8 in-scope files** and are reading persisted data schemas.
None of these will be touched by this mission.

The `feature_slug` parameter names in `accept.py`'s helpers (`_spec_artifact_dirty_paths`,
`_commit_residual_acceptance_artifacts`) are **Python variable names** (not JSON key strings) —
they are in scope for rename per FR-002 and Assumption 5.

---

## Design Decisions

### D-01 — Inline guard pattern (replaces resolve_selector alias branch)

**Decision**: After removing the `alias_value`/`alias_flag` arguments, replace each `resolve_selector` call
with a two-line inline guard:

```python
mission_norm = mission.strip() if isinstance(mission, str) else None
if not mission_norm:
    raise typer.BadParameter("--mission <slug> is required")
mission_slug = mission_norm
```

**Rationale**: `typer.BadParameter` produces exit code 2 natively (satisfying SC-003), formats a
clean user-facing message ("Error: Invalid value for '--mission': …"), and requires no new imports.
The `isinstance(str)` guard replicates `_normalize_selector`'s OptionInfo-sentinel protection
(the PR #1985 adversarial finding that caused `TypeError`). Two lines; complexity-neutral (NFR-003).

**Rejected alternative**: Passing `alias_value=None` to `resolve_selector` — leaves dead arguments in
place and makes the alias-free path non-obvious. Spec FR-006 says "prefer inlining the simplified guard."

**Rejected alternative**: Calling `require_explicit_feature()` directly — it raises `ValueError`,
not `typer.BadParameter`, requiring an extra wrapping `except ValueError` block.

### D-02 — Exit code standardization on no-selector

**Decision**: Standardize all 8 commands to exit code 2 on no-selector (SC-003).

**Where this changes existing behavior**:
- `accept.py:279` currently raises `typer.Exit(1)` — updated to `typer.Exit(2)` (or `typer.BadParameter`).
- `merge.py:503` currently raises `typer.Exit(1)` — updated to `typer.Exit(2)`.
- `research.py` currently converts `BadParameter` to `typer.Exit(1)` — the new inline guard raises
  `BadParameter` and lets Typer handle it naturally (exit 2).

### D-03 — resolve_selector import cleanup

**Decision**: Remove `from specify_cli.cli.selector_resolution import resolve_selector` imports from the
6 files that no longer call it: `research.py`, `next_cmd.py`, `context.py`, `lifecycle.py` (if lifecycle's
`specify()` resolveSelector for `--mission-type` branch still needs it — see below), `mission_type.py`.

**Special case — lifecycle.py**: `lifecycle.py` still has `resolve_selector` in `specify()` at line 136
(aliasing `--mission-type`). The import stays. Only the `alias_flag="--feature"` call sites are removed.

### D-04 — SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION env var

**Decision**: After this mission the env var becomes inert (no `--feature` warnings emitted anywhere in
the 8 commands). Update `docs/reference/environment-variables.md` to note it is now unused. Do NOT
delete the env var check from `selector_resolution.py` itself — that would be a change to an out-of-scope
file. The variable is simply never triggered by the in-scope commands post-cleanup.

### D-05 — lifecycle.specify positional `feature` → `mission` rename (orchestrator ruling)

**Decision**: Rename positional param `feature` → `mission` in `lifecycle.specify()`.
CLI invocation is unchanged: `spec-kitty lifecycle specify my-mission-name` still works.
The help metavar changes from `FEATURE` to `MISSION` (Typer auto-derives from param name).
Call `_slugify_feature_input(mission)` after rename. The function `_slugify_feature_input` itself
is not renamed (it has param `value: str`, not `feature`).

**Rationale**: Orchestrator ruling to remove the last `feature` positional in the lifecycle surface.

### D-06 — Existing tests that assert merge keeps --feature

**Decision**: Update `tests/contract/test_feature_alias_scope.py` — flip the three merge-specific
assertions: `test_merge_still_accepts_feature_alias` → now asserts exit 2 / "No such option";
`test_merge_feature_and_mission_both_accepted` → now asserts `--feature` is rejected, `--mission` works;
`test_merge_feature_alias_is_hidden_in_cli_introspection` → now asserts merge has NO `--feature` param.

These tests were written for the previous mission's scope (where merge was "out of scope"). This mission
brings merge in scope. NFR-001 requires test updates, not deletions.

---

## Findings on Existing Test Infrastructure

| Test file | Current behavior | After this mission |
|-----------|-----------------|-------------------|
| `tests/contract/test_terminology_guards.py` | `INSCOPE_FEATURE_FREE_FILES` has 10 files | Extend to 18 (add the 8 new files) |
| `tests/contract/test_feature_alias_scope.py` | Asserts merge/next/implement still have `--feature` | Update: merge/next/implement are now also removed; flip assertions for merge; update INSCOPE list |
| `tests/specify_cli/cli/test_no_visible_feature_alias.py` | `test_every_feature_flag_is_hidden` passes vacuously | Add `test_zero_feature_flags_exist` asserting 0 `--feature` params CLI-wide |
| `tests/integration/test_legacy_feature_alias.py` | `test_no_unhidden_feature_typer_options_in_commands_tree` passes | Still passes (no `--feature` options at all) |
