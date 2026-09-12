# Phase 0 Research: Charter Preflight Missing-Charter Advisory Mode

No `[NEEDS CLARIFICATION]` markers remain in `spec.md` — all scope questions were resolved during discovery and planning (see `decisions/` for the recorded decision moments). This document consolidates the design decisions made from direct source inspection rather than open unknowns.

## Pre-merge adversarial correction (2026-08-16)

The first squad review proved two earlier conclusions below were incomplete. This correction is authoritative where they conflict:

- Canonical freshness state alone decides pass/block. `_is_optional_missing_charter_stack()` must pass first (`charter_source=missing`, `synced_bundle=missing`, `synthesized_drg in {missing,built_in_only}`). Only then may a direct `charter.md` existence probe select fresh-vs-legacy advisory copy. It cannot exempt stale, invalid, or other partial residue.
- The two warning presentations are not separate behavioral exemption predicates. Identical canonical states must have identical `passed` and `blocked_reason` values regardless of `charter.md` presence.
- A warning stored only in `CharterPreflightResult.warnings` is not visible. The shared mutation hook emits passed advisories to stderr, and the dashboard command persists/renders them. The prior claim that dashboard needed no code change is superseded.
- The legacy remediation must be executable in a project with no saved interview: `spec-kitty charter generate --no-from-interview`.
- Wrapper-level delivery matters: advancing/query and human/JSON `next` paths must all preserve advisories on stderr. Hook-only tests do not prove that contract.
- `CHARTER_MD` remains canonical but its `charter.bundle` import must be lazy; eager import executes `charter.__init__` and adds ~1.1s to the `next` startup path. A fresh-process <500ms regression test pins this boundary.

Red-first consumer, stale-residue, wording, and dashboard tests were committed separately before the remediation implementation.

## Decision: Detect the legacy-bundle shape via direct `charter.md` file existence, not via `freshness/computer.py`

**Rationale**: `compute_freshness()` (`charter_runtime/freshness/computer.py`) is explicitly documented as a pure observer of `charter.yaml`-derived state — its module docstring states `charter.md` "is a curated, never-resolving prose companion... and is not consulted here." Teaching it to consult `charter.md` would violate that documented boundary and widen a module whose docstring explicitly promises NFR-001 latency (no extra I/O) as a pure observer. The legacy-bundle predicate instead lives in `runner.py` (which already has `repo_root` in scope) and does one additional `Path.exists()` check — matching NFR-001's "at most one additional filesystem existence check" constraint.

**Alternatives considered**:
- Add a `charter_md_present` field to `CharterFreshness`/`FreshnessSubState`: rejected — touches a dataclass consumed by `spec-kitty charter status --json` (a documented contract surface, `contracts/charter-status-json.md`), which is out of scope for a bug fix and would require a contract-doc update for an unrelated consumer.
- Detect legacy bundle by adding a fourth "layer" check: rejected — the three-layer check list (`charter_source`, `synced_bundle`, `synthesized_drg`) is iterated generically elsewhere (`_derive_blocked_reason`, `_LAYER_ORDER`); a fourth entry would need to be excluded from those generic loops to avoid changing blocked-reason formatting for every other failure case — more invasive than a standalone predicate function.

## Historical decision superseded: Keep the two predicates mutually exclusive by construction

**Rationale**: `_is_optional_missing_charter_fresh_project()` requires exact equality on all three layer states being `"missing"`. `_is_legacy_charter_bundle()` requires `charter.md` to exist on disk — which is definitionally impossible in the fresh-project shape (a truly fresh project has no `.kittify/charter/` contents at all, per Story 1's Given clause). No repo state can satisfy both predicates simultaneously, so evaluation order between them is not a source of ambiguity, but the implementation should still check fresh-project first (existing behavior, unchanged) then legacy-bundle second, to keep the diff purely additive.

**Alternatives considered**: A single merged predicate with a mode return value — rejected as it would touch the existing, already-tested `_is_optional_missing_charter_fresh_project()` implementation instead of leaving it untouched (smallest-viable-diff, DIRECTIVE_024).

## Decision: Two distinct warning message constants, not one parameterized message

**Rationale**: FR-003 requires the legacy-bundle warning to be "visibly different from and more detailed than" the fresh-project warning. The existing `_FRESH_PROJECT_MISSING_CHARTER_WARNING` is a module-level string constant consumed via `CharterPreflightResult.warnings`. A second constant (e.g. `_LEGACY_BUNDLE_MISSING_CHARTER_WARNING`) keeps both messages independently editable and greppable, consistent with the existing single-constant pattern.

## Historical decision superseded: Dashboard reuses the same predicate/message pair (in scope per decision `01M05RT3Q6HZYY4BCV9YS8JZAC`)

**Rationale**: `run_preflight_for_dashboard()` already calls `run_charter_preflight(..., allow_missing_charter=True, ...)`. Once `run_charter_preflight()` itself gains the legacy-bundle branch (IC-01), the dashboard gets the more detailed warning for free — no dashboard-specific code change is needed beyond what IC-01/IC-02 already produce, since the flag is already `True` there. This confirms IC-03 is low-risk: it is largely a verification/test task (prove the dashboard already benefits) rather than a new code change, once IC-01 lands.

## Supply-Chain Security & Adversarial Evidence

**Not applicable.** This mission adds no new dependency in any ecosystem (npm/pip/etc.) — it is a pure internal-logic change inside `src/specify_cli/charter_runtime/preflight/`. Per the plan command's Supply-Chain section, this is recorded explicitly (not silently skipped): no dependency decision was made, so no adversarial-evidence pass is required.

## Domain rule / invariant confirmation

- **Invariant preserved**: A genuinely broken canonical state (invalid YAML, stale synthesis, partial residue) fails closed even when `charter.md` exists. Confirmed by `test_charter_md_never_exempts_stale_or_invalid_residue`; one canonical predicate runs before the display-only warning selector.
- **No state mutation on the exempted paths**: Confirmed via `hook.py:55-101` (`run_preflight_or_abort`) — the advisory branches return `passed=True` before any worktree allocation or `.kittify/` write occurs downstream in `next_cmd.py` / the implement command, so FR-001/FR-002 introduce no new state-mutation ordering risk.
