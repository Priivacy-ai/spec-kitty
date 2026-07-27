# Mission Specification: Harden the Dead-Symbol Gate

**Mission**: `harden-dead-symbol-gate-01KW0RJR`
**Type**: software-dev
**Status**: Draft
**Source**: [GitHub issue #2158](https://github.com/Priivacy-ai/spec-kitty/issues/2158) — split from #2049
**Requirements basis**: `docs/engineering_notes/2158-dead-symbol-classification.md` — a 4-agent classification of the 119 symbols the parser fix surfaces.

## Purpose

The architectural dead-symbol gate (`tests/architectural/test_no_dead_symbols.py`) flags an `__all__`
symbol as dead when it has no cross-module caller. It has two limitations: (1) a parser bug
(`_extract_all_literal`) that blinds it to the public symbols of ~57 modules, and (2) caller detection
that only recognizes `from X import Y` — missing module-style attribute access, lazy `__getattr__`
package re-exports, Typer/click command registration, dynamic registry/`getattr` dispatch, and
return-type/annotation flow. Fixing only the parser surfaces ~107 **live-but-invisible** symbols and
tempts a mass-allowlist that would *grow* the ratchet #2049 works to shrink. This mission fixes the
parser **and** enhances caller detection so those ~107 are correctly recognized as live (no allowlist
growth), cleans up the handful of genuinely-dead symbols, and closes a latent security gap.

## Domain Language

| Term | Meaning |
|------|---------|
| **Dead-symbol gate** | `tests/architectural/test_no_dead_symbols.py` — fails when an `__all__` symbol has no detected caller. |
| **Caller detection** | The gate's logic for deciding whether a symbol is referenced. Today: only `from <module> import <symbol>` in `src/`. |
| **False positive** | A symbol the gate flags "dead" that is actually reachable via a pattern the gate can't see (module-style call, lazy re-export, Typer registration, registry, return-type flow, test-only). |
| **DEMOTE** | Remove a symbol from its module's `__all__` while keeping its definition — it stops being a "public" symbol the gate tracks, without deleting code. |
| **SHRINK ratchet** | `tests/architectural/_baselines.yaml`; category counts may only decrease (#2049 / Slice F C-004). |

## User Scenarios & Testing

### Primary scenario
**Actor:** Maintainer running the architectural suite after this mission.
**Trigger:** `pytest tests/architectural/` on the feature branch.
**Success outcome:** The dead-symbol gate now inspects the previously-hidden ~57 modules, correctly
recognizes the ~107 live-but-gate-blind symbols as live (no new allowlist entries for them), the gate
suite is green, and `category_a`/`category_b` baselines do **not** grow (they hold or shrink).

### Acceptance scenarios
1. **Given** the parser fix and caller-detection enhancement, **when** the gate runs, **then** none of the ~107 live symbols (module-called, lazy-reexport, Typer-registered, registry-dispatched, return-flow, test-only) is flagged dead, and no allowlist entry was added for them.
2. **Given** a deliberately-dead test symbol (in `__all__`, zero callers of any kind), **when** the gate runs, **then** it is STILL flagged — proving the enhancement did not weaken the gate (no false negatives).
3. **Given** the `BANNED_FLAGS` security check is wired, **when** an orchestrator-api policy envelope includes a banned flag (e.g. `--yolo`), **then** `parse_and_validate_policy` rejects it.
4. **Given** the cleanup, **when** the gate runs, **then** `sync.owner::_daemon_root` is gone and the ~7 demoted symbols are absent from their `__all__` — with no net ratchet growth.

### Edge cases
- The enhancement must be **precise**: it must not treat *any* string match of a symbol name as a caller (that would mask real dead code). Detection patterns must be structurally grounded (AST or anchored regex), and the no-false-negative regression test (scenario 2) is the guard.
- Baseline numbers (`category_a`/`category_b`) depend on whether #2049 (#2159) and #2048 (#2152) have merged — the implementer re-confirms live counts at implement time.
- The `auth.transport` trio is genuinely dead but deferred (pending the SaaS migration wave) — it is allowlisted-as-deferred with a justification, NOT detection-fixed.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Fix `_extract_all_literal` in `tests/architectural/test_no_dead_symbols.py` so a top-level non-`__all__` `AnnAssign` `continue`s instead of early-returning `frozenset()`; add a focused unit test (a module whose first top-level node is a non-`__all__` AnnAssign followed by a real `__all__`). | Pending |
| FR-002 | Enhance the gate's caller detection (in `tests/architectural/test_no_dead_symbols.py`, reusing the cached `path_to_tree` AST corpus) to recognize **four** legitimate reference patterns the `from X import Y` check misses, each anchored to a RESOLVED declaring module (never a bare name — C-001): **(a)** module-style attribute access (`alias.symbol`, resolving the import alias), **(b)** lazy `__getattr__` package re-export facades (e.g. `sync/__init__.py`'s static `(submodule, "name")` map), **(c)** Typer/click command registration (`app.command()(mod.fn)` — a free sub-case of (a)), **(d-getattr)** `getattr(mod, "literal")` dispatch. These absorb the bulk of the surfaced-symbol wave with no allowlist entries. **Per research D-03, return-type/annotation flow (e), test-only references (f), and the loose `register(1, fn)` arg form are NOT detection-fixed in-gate** (a global annotation-name or any-call-arg rule would mask real dead code, and counting `tests/` callers defeats the gate's purpose) — those residual symbols are handled by FR-003/FR-004 (delete/DEMOTE) or a justified allowlist. | Pending |
| FR-003 | DELETE the genuinely-dead re-export `specify_cli.sync.owner::_daemon_root` (callers use `daemon._daemon_root()` directly); remove it from `owner.py`'s import block and `__all__`. | Pending |
| FR-004 | DEMOTE the following from their module `__all__` (keep definitions): `auth.transport::reset_user_facing_dedup`, `sync.owner::check_daemon_owner_match`, `compat.safety_modes::_ORCHESTRATOR_API_UNSAFE_SUBCOMMANDS`, `compat.safety_modes::SafetyPredicate` (redundant re-export; canonical in `compat.safety`), `legacy_detector::LEGACY_LANE_DIRS`, `readiness.upgrade_ux::PromptCallback`, `readiness.upgrade_ux::UpgradeUxOutcome`. Re-confirm each is not externally imported before demoting. | Pending |
| FR-005 | Wire the latent security check: `parse_and_validate_policy` in `specify_cli/orchestrator_api/envelope.py` must reject any `dangerous_flags` entry that is a member of `BANNED_FLAGS` (currently defined but never enforced); add a test that a banned flag (e.g. `--yolo`) is rejected. | Pending |
| FR-006 | Allowlist-as-deferred the `auth.transport` trio (`get_client`, `get_async_client`, `reset_clients`) — genuinely dead now but the documented target of the next SaaS migration wave (`saas_client.py`). Add a single justified allowlist entry (or keep their existing category) referencing the deferral; do NOT detection-fix or delete them. | Pending |
| FR-007 | Net result: the gate inspects the previously-hidden ~57 modules with the enhanced detection, and `category_a_slice_f_deferred` / `category_b_grandfathered_legacy` baselines show NO net growth versus the pre-mission base (the ~107 live symbols add zero entries; only the deferred auth trio + any irreducibly-dead symbol may add a justified entry). Any residual genuinely-dead symbol is handled by delete/demote/justified-allowlist — never bulk-allowlist. | Pending |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The enhancement must not weaken the gate (no false negatives). | A regression test asserts a synthetic genuinely-dead `__all__` symbol IS still flagged after the enhancement (acceptance scenario 2). | Pending |
| NFR-002 | The full architectural + contract suites pass. | `pytest tests/architectural/ tests/contract/` exits 0 (excluding the documented pre-existing env/order-flake failures). | Pending |
| NFR-003 | No net ratchet growth beyond the single deferred auth-trio entry. | Post-mission `category_a_slice_f_deferred` + `category_b_grandfathered_legacy` frozenset entry counts ≤ pre-mission base + the one deferred auth-trio allowlist entry (FR-006) — measured by **direct frozenset entry-count** (the `test_no_dead_symbols` baseline section in `_baselines.yaml` is documentary-only per research D-06, NOT enforced by `test_ratchet_baselines.py`). | Pending |
| NFR-004 | No unintended runtime behavior change. | The only production behavior change is the `BANNED_FLAGS` enforcement (FR-005); the 1 delete + 7 demotes do not alter call behavior (defs retained; demotes only affect `import *`). `ruff`/`mypy` clean on the diff. | Pending |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Caller-detection patterns MUST be structurally grounded (AST or boundary-anchored), not bare substring matches — a too-loose matcher would silently mask real dead code (this is the gate's whole purpose). | Active |
| C-002 | `_baselines.yaml` edits MUST carry a `# justification:` comment and the declared count MUST equal the live frozenset size (C-001 of #2049 still applies). | Active |
| C-003 | Re-confirm live baseline counts at implement time — they depend on whether #2049 (#2159) and #2048 (#2152) have merged into the base. | Active |
| C-004 | Per-symbol dispositions follow `docs/engineering_notes/2158-dead-symbol-classification.md`; the implementer re-verifies each genuinely-dead/demote symbol against the live tree (callers can change as other missions land) before acting. | Active |

## Success Criteria

1. The gate inspects the ~57 previously-hidden modules; the ~107 classified-live symbols are recognized as live with **zero** new allowlist entries.
2. A no-false-negative regression test passes (a synthetic dead symbol is still flagged).
3. `sync.owner::_daemon_root` deleted; the ~7 demotes applied; the `BANNED_FLAGS` check wired + tested; the auth trio allowlisted-as-deferred.
4. `category_a`/`category_b` baselines show no net growth vs base; `pytest tests/architectural/ tests/contract/` green; `ruff`/`mypy` clean.
5. The PR closes #2158.

## Key Entities

- **`test_no_dead_symbols.py`** — the gate: holds `_extract_all_literal` (FR-001) and the caller-detection logic (`_imports_by_target` / `_symbol_has_caller` or equivalent) to enhance (FR-002).
- **`_baselines.yaml`** — ratchet ledger; must show no net growth (NFR-003).
- **`orchestrator_api/envelope.py`** — `parse_and_validate_policy` + `BANNED_FLAGS` (FR-005).
- **The disposition table** — `docs/engineering_notes/2158-dead-symbol-classification.md`: per-symbol classification + evidence.

## Assumptions

- The squad classification (2026-06-26) holds at implement time; the implementer re-confirms each delete/demote/allowlist symbol against the live tree (C-004).
- Enhancing caller detection to recognize the six patterns is sufficient to clear the ~107 false positives; if a handful resist precise detection, they are handled individually (demote or justified-allowlist), not bulk-allowlisted.

## Out of Scope

- The broader `category_b_grandfathered_legacy` / `legacy_contract` full burn-down (separate follow-on missions, per #2049).
- `category_4_backcompat_shims` (#2048 / #2152).
- Refactoring or wiring the genuinely-dead `auth.transport` trio into the SaaS path — that belongs to the future SaaS migration wave (this mission only defers it).
