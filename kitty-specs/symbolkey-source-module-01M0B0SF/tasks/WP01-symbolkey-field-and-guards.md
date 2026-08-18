---
work_package_id: WP01
title: SymbolKey source_module field + G1–G6 non-goal guards
dependencies: []
requirement_refs:
- C-001
- C-002
- FR-001
- NFR-001
planning_base_branch: remediation/symbolkey-source-module-3552
merge_target_branch: remediation/symbolkey-source-module-3552
branch_strategy: Planning artifacts for this mission were generated on remediation/symbolkey-source-module-3552. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/symbolkey-source-module-3552 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-08-18T18:20:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/_symbol_key.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/_symbol_key.py
- tests/unit/test_symbol_key.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). ATDD; `mypy --strict` + zero new suppressions; complexity ≤ 15; realistic test data.

## Objective

Add an optional, **non-hashing** `source_module` field to `SymbolKey` and pin the six
non-goal guards (G1–G6) that keep it out of identity. This is the foundation WP — after it,
the field exists and is provably inert with respect to equality/hash/`body_hash`/`key_tier`/`as_tuple()`.
It must be **green on its own commit**: adding a defaulted field + guard tests changes nothing else.

Closes toward #3552. Non-goals (C-001, C-002): the field MUST NOT enter `body_hash`/`key_tier`,
and MUST NOT escalate content-tier to collision-tier (relocation-tolerance D-1 preserved).

## Context

- `SymbolKey` is a `@dataclass(frozen=True)` in `tests/architectural/_symbol_key.py` (~L91).
  Its `__eq__`/`__hash__` derive from every *comparing* field `(bare_name, body_hash, module_path)`.
- The gate's exemption is `final_key in allowlist` (full-tuple membership), where resolver-minted
  keys carry **no** provenance and allowlist entries **will** carry `source_module`. So the field
  MUST be non-comparing or every provenance-bearing entry stops matching its resolver key and the
  whole allowlist false-reds (critical risk R1).
- `as_tuple()` (~L107) branches on `module_path` only; `key_tier` (~L509) and `classify_collisions`
  (~L484) read the live collision index and `module_path` — never provenance.
- Guard contract: `contracts/non-goal-invariants.md` (G1–G6 verbatim).

## Subtasks

### T001 — Add the field
In `_symbol_key.py`: add `from dataclasses import field` (if not already imported) and add to `SymbolKey`:
```python
source_module: str | None = field(default=None, compare=False)
```
Reword the class docstring to describe it as provenance-only machine identity, excluded from identity by `compare=False`. Do **not** touch `body_hash`, `key_tier`, `as_tuple`, or `classify_collisions`.

### T002 — G6 keystone guard (in `tests/unit/test_symbol_key.py`)
```python
import dataclasses
def test_source_module_is_non_comparing():
    f = {fld.name: fld for fld in dataclasses.fields(SymbolKey)}["source_module"]
    assert f.compare is False
```
This fails the instant someone flips the field to comparing (closes R1).

### T003 — G1/G2 equality + hash + frozenset membership
Two keys equal in `(bare_name, body_hash[, module_path])` but differing in `source_module` (incl. `None` vs set) compare **equal**, hash-equal, and are mutual `frozenset` members. Add a case modelling `final_key in allowlist`: a `source_module=None` resolver key is `in frozenset({SymbolKey("Foo","h", source_module="pkg.mod")})`.

### T004 — G3/G4 tier + tuple
- G3: `SymbolKey("Foo","h", source_module="pkg.mod")` is still `is_content_tier`; `key_tier(...)` returns it **unescalated** (no `module_path` minted from provenance). Use realistic corpus inputs.
- G4: `.as_tuple()` returns `("Foo","h")` (content) / `("Foo","m","h")` (collision) — provenance excluded in both branches.

### T005 — G5 body_hash + resolver key
`body_hash` is identical with/without `source_module`; a resolver-minted key for a still-dead symbol has `source_module is None`; adding a provenance peer does not change any other key's `body_hash`.

### T006 — Verify
```bash
uv run ruff check tests/architectural/_symbol_key.py tests/unit/test_symbol_key.py
uv run mypy --strict tests/architectural/_symbol_key.py
PWHEADLESS=1 uv run pytest tests/unit/test_symbol_key.py -q
```
All clean/green. Then a quick sanity that the dead-symbol gate is unaffected:
`PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py -q` (green — nothing changed yet).

## Branch Strategy

Planning base and merge target are both `remediation/symbolkey-source-module-3552`. Execution worktrees are allocated per computed lane from `lanes.json`; this WP has no dependencies and branches from the mission base.

## Definition of Done

- `source_module: str | None = field(default=None, compare=False)` present; docstring updated.
- G1–G6 present and green (keystone G6 included).
- ruff + mypy --strict clean; `test_no_dead_symbols` still green (no behavior change).

## Reviewer guidance

Confirm the field is `compare=False` (not just defaulted), that `as_tuple`/`body_hash`/`key_tier` are untouched, and that G6 actually fails if `compare=False` is removed (ask the implementer to demonstrate, or verify by inspection).
