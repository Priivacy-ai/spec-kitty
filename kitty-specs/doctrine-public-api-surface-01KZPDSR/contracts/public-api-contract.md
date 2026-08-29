# Contract — Doctrine Public API Surface

This mission's "contract" is not an HTTP schema (C-003 — OpenAPI does not apply). It is a set
of **architectural invariants expressed as testable gates**. Each contract below names the
enforcing test and its acceptance condition, in ATDD red-first order.

## C1 — Doctrine public surface exists and is pinned

- **Gate**: `tests/architectural/test_doctrine_public_surface.py` (NEW) + `test_doctrine_wheel_closure.py` (UPDATE).
- **Given** `doctrine/api.py` with `__all__`, **then** importing `doctrine.api` exposes exactly the declared PUBLIC symbols, every one is importable and non-None, and the wheel-closure test pins this `__all__` (not just the manifest shape).
- **No-dead-symbol interaction**: charter facades re-export PUBLIC symbols **from `doctrine.api`** (so `from doctrine.api import X` gives the gate a live caller), and only genuinely caller-less wheel-only exports use `test_no_dead_symbols.py`'s `_SYMBOL_ALLOWLIST` with a tracker reference. Without the from-`doctrine.api` wiring, the gate degrades to blanket-allowlisting the whole surface. (FR-001)

## C2 — Facade identity (symbol-level)

- **Gate**: `tests/architectural/test_charter_facades_reexport_doctrine.py` (`_FACADE_TABLE` grows).
- **Given** each new/widened door (`charter.drg`+, `charter.mission_steps`+, `charter.missions`, `charter.model_routing`, `charter.assets`, glossary/spdd/pack_paths doors), **then** for every re-exported symbol `facade.SYMBOL is doctrine.SYMBOL` and `SYMBOL in facade.__all__`.
- **Symbol-level rule**: a facade entry re-exporting a whole submodule (not a leaf symbol) fails review even if identity holds. (FR-003, NFR-002)

## C3 — No direct doctrine reach-through from runtime

- **Gate**: `tests/architectural/test_runtime_charter_doctrine_boundary.py` — existing module-level ratchet (empty baseline) + NEW sibling lazy-import ratchet.
- **Given** any `*.py` under `src/specify_cli/` outside the enumerated management surface, **then** it contains no `from doctrine…` / `import doctrine…` with `ImportFrom.level == 0` at module level *or* inside a function body, excluding `if TYPE_CHECKING:` blocks.
- **Mechanism**: a **parent-tracking recursive descent** (not bare `ast.walk`, which loses the enclosing-block context needed to skip `TYPE_CHECKING` and to tell module-level from nested), tracking `(depth, under_TYPE_CHECKING)`. Fixtures must prove a `TYPE_CHECKING` doctrine import is NOT flagged and a nested-function one IS.
- **Baseline**: an only-shrink frozenset; a new violation (grow) fails, a stale entry (a migrated file still listed) fails. (FR-006, SC-003)
- **Known limit**: static AST does not see dynamic imports (`importlib.import_module("doctrine.x")`); zero exist today, but the "cannot silently regrow" claim is bounded to static imports.

## C4 — No first-party re-export laundering

- **Gate**: the same boundary test, laundering rule — **enforced SOURCE-side**.
- **Given** any `src/specify_cli/doctrine/*` module, **then** its `__all__` lists **no doctrine-origin symbol** (a name it imported `from doctrine…`). This is cleanly static and is the real fix for the conduit; a consumer-side check is rejected because `from specify_cli.doctrine.config import load_pack_registry` (laundered doctrine object) and `from specify_cli.doctrine.config import assert_pack_local_paths_exist` (genuine first-party) are byte-identical import syntax and cannot be distinguished by a single-file AST scan. The management surface stays inbound-only. (C-005, FR-004)

## C5 — Sole door not bypassed

- **Gate**: `tests/architectural/test_charter_sole_door_doctrine_service.py`.
- **Given** the whole tree, **then** zero unwrapped raw `doctrine.service.DoctrineService(...)` constructions exist outside `charter.activation.doctrine_service_builder`. `charter.activation.resolver.DoctrineService` (the wrapper) is never added to `_FACADE_TABLE`. (FR-005)

## C6 — Truly-internal paths stay hidden (negative)

- **Gate**: `tests/architectural/test_doctrine_public_surface.py` negative assertion.
- **Given** the truly-INTERNAL set (paths with no non-exempt consumer after IC-01 reconciliation), **then** none appears in `doctrine/api.py __all__` or any `charter.*` facade `__all__`. (FR-007)

## C7 — Behavior preservation (refactor lock)

- **Gate**: a golden-snapshot round-trip test seeded on the base commit.
- **Given** the FR-009 literal hoist and FR-010 complexity refactor, **then** `spec-kitty doctrine regenerate-graph` output is byte-identical to the base-commit golden snapshot; each extracted helper has its own passing focused test; ruff `C901`/Sonar `S3776` report every touched doctrine function ≤ 15. (FR-009, FR-010, NFR-003, C-006)

## C8 — Regression-delta + no-triage

- **Gate**: review + Sonar issue-history check (process gate, asserted in PR body).
- **Given** the branch vs merge-base, **then** no merge-base-green test is red on the branch (pre-existing reds classified per DIR-013), and zero doctrine CRITICAL Sonar issues were resolved via Won't-Fix/False-Positive during the mission window. (NFR-001, NFR-005, SC-004, SC-005)

### Contract → requirement traceability

| Contract | Requirements | Success criteria |
|---|---|---|
| C1 | FR-001, FR-008 | SC-002 |
| C2 | FR-003, NFR-002, C-002 | SC-005 |
| C3 | FR-006 | SC-001, SC-003 |
| C4 | FR-004, C-005 | SC-001 |
| C5 | FR-005 | SC-002 |
| C6 | FR-007 | SC-002 |
| C7 | FR-009, FR-010, FR-011, NFR-003, C-006 | SC-004, SC-005 |
| C8 | NFR-001, NFR-005 | SC-004, SC-005 |
