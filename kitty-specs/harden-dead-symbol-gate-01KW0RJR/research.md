# Research: Harden the Dead-Symbol Gate (#2158)

Phase 0 research. Two opus research agents: one mapped the gate internals, one designed per-pattern
detection. Headline: **strategy A is right, but only 4 of the 6 patterns should be detection-fixed
in-gate — the other 2 must be dispositions (DEMOTE/allowlist), because in-gate detection of them would
mask real dead code.**

## Gate architecture (confirmed)

`tests/architectural/test_no_dead_symbols.py` (1125 lines) is ONE test, pure-AST (no greps):
- `_extract_all_literal` (L910–948) — parses each module's `__all__`. **The bug** (L929–938): an `elif ast.AnnAssign` branch that, for a non-`__all__` annotated module constant appearing before `__all__`, leaves `value=None` and hits `if value is None: return frozenset()` → silently empties that module's `__all__`. **Blast radius: 57 modules** invisible.
- `_walk_modules` (L951–977) — parses each src file ONCE; returns `decls` (module→`__all__`), `path_to_dotted`, and **`path_to_tree` — a cached whole-src AST corpus**. This is the load-bearing reuse asset: new detectors `ast.walk` these cached trees with zero new I/O.
- `_imports_by_target` (L980–1007) — the ONLY caller rule today: walks `ast.ImportFrom`, records `per_symbol[target]={names}` + `star_targets`. Plain `import X` and `tests/` are deliberately ignored.
- `_symbol_has_caller` (L1010–1048) — the **extension point**; returns True on a direct/parent/submodule `from-import` match. New rules OR in here (or widen `_imports_by_target`).

## D-01 — The parser fix and the detectors MUST land together

Simulating the one-line `_extract_all_literal` fix surfaces **119 new offenders** — these ARE the "~107 live symbols." So: fix-only → gate goes red with 119 false positives; detectors-only → gate stays blind to 57 modules. One PR, both changes. (Confirms the #2158 framing.)

## D-02 — The no-false-negative invariant (NFR-001 / C-001)

**Every proof-of-life must bind to a RESOLVED declaring module, never a bare name.** A dead `foo` in module X is rescued only when `bar.foo` is found where `bar` provably resolves (via the file's own import table) to X. This single rule is what keeps every detector from masking dead code. Belt-and-suspenders: keep the existing stale-allowlist reverse check (L1093–1099) so over-broad rules self-surface in review.

## D-03 — Per-pattern dispositions (THE refinement to FR-002)

| Pattern | Verdict | Rule (anchored to resolved module) | Masking risk |
|---------|---------|-----------------------------------|--------------|
| **(a) module-style `alias.symbol`** | **IN-GATE** | Build alias map per tree (`ast.Import`/`ImportFrom asname`); walk `ast.Attribute` where `.value` is a known alias; resolve alias→module; record `(module, attr)`. | Low |
| **(c) Typer `app.command()(mod.fn)`** | **IN-GATE — FREE** | It's an `ast.Attribute` arg; (a)'s walk already visits it. No separate rule. | Low |
| **(d-getattr) `getattr(mod,"name")`** | **IN-GATE** | `Call` to `getattr`, `args[1]` str Constant, resolve `args[0]` via alias map. | Low |
| **(b) lazy `__getattr__` facade** | **IN-GATE** | Module has `def __getattr__`; collect static dict-literal `(submodule, "name")` tuples; mark the submodule's canonical symbol live. | Low |
| **(e) return-type/annotation flow** | **DISPOSITION (allowlist/DEMOTE)** | A *global* annotation-name rule is HIGH masking risk (any file's annotation rescues an unrelated dead symbol). Anchored annotation = a `from-import` the gate already counts. Same-module-only-returned publics (`PolicyMetadata`, `ActiveWPResolution`, `WorkspaceResolutionError`) → DEMOTE or justified allowlist. | **High if in-gate** |
| **(f) test-only** | **DISPOSITION (DEMOTE)** | Counting `tests/` callers as "alive" defeats the gate's founding premise (a symbol exercised only by its own tests is runtime-dead). Introduce a DEMOTE disposition (drop from `__all__`, keep def — still test-importable as a module attr). | **High by definition if in-gate** |
| **(d-register-arg) `register(1, fn)`** | **DISPOSITION or tightened** | "name passed as any call arg" is loose (a stray `Name` load rescues dead code). Either restrict to a known-registrar allowlist (`_register_migration`, `register_safety`, `app.command`) or DEMOTE/allowlist. | Medium-high if loose |

**So FR-002 narrows to:** implement in-gate detection for **(a)+(c)+(d-getattr)+(b)** — these absorb the bulk of the 119-wave with negligible masking risk. **(e)**, **(f)**, and **(d-register-arg)** are handled by the existing FR-003/FR-004 dispositions (delete/DEMOTE) or justified allowlist — NOT new in-gate rules.

## D-04 — Add a DEMOTE disposition as a first-class concept

The current allowlist (esp. category-C) is over-used to paper over "test-only / annotation-only, not dead" symbols, accumulating as permanent ratchet debt. A clean **DEMOTE** (drop from `__all__`, keep def) lets those leave the public surface instead of growing the allowlist. This is the right home for the FR-004 set AND for residual (e)/(f) symbols.

## D-05 — Implementation order (cheapest→highest coverage)

1. Fix `_extract_all_literal` (1-line `continue`) — prerequisite.
2. (a) module-attribute resolver (subsumes (c)).
3. (d-getattr) — small add on (a)'s alias map.
4. (b) `__getattr__` facade — rescues 13 `sync::*` in one rule.
5. Apply DEMOTE/delete to the residue (FR-003/FR-004 + any (e)/(f)/(d-register) leftover).
6. Allowlist-as-deferred only the irreducible (auth.transport trio, FR-006).

After 1–4, the 119-wave drops to a small residue (private seam helpers, annotation-only publics) handled by step 5.

## D-06 — Secondary finding: the symbol-gate baselines are documentary-only

`tests/architectural/_baselines.yaml` has a `test_no_dead_symbols:` section, but `test_ratchet_baselines.py` does NOT enforce it (only `test_no_dead_modules` per-category + a hardcoded single-baselines list). So `category_a/b` symbol counts are NOT a live ratchet — they're documentary (matches the #2049 squad finding). NFR-003 ("no net growth") is therefore measured by *entry count in the frozensets*, not by a ratchet-test failure. Optional stretch: wire the symbol-gate section into `test_ratchet_baselines` so it becomes a real ratchet — flag as a possible FR or explicit out-of-scope.

## Open questions / risks for plan

1. **FR-002 scope** is now 4 in-gate patterns (a/b/c/d-getattr), not 6 — confirm and update the spec. (e)/(f)/(d-register) → dispositions.
2. **(d-register-arg)**: tighten to a known-registrar set, or DEMOTE the few affected symbols (`migrate_v1_to_v2`, predicates)? Plan should pick.
3. **Symbol-gate ratchet** (D-06): make it enforced (stretch FR) or leave documentary (note in spec)?
4. **Test corpus for the detectors**: each new rule needs a focused unit test (synthetic module exercising the pattern) PLUS the NFR-001 no-false-negative test (a synthetic dead symbol still flagged).
