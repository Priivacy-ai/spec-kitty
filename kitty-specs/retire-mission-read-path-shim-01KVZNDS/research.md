# Research: Retire mission_read_path Backcompat Shim

Phase 0 output. This mission has no open `[NEEDS CLARIFICATION]` markers; the research below
records the decisions and the investigation that de-risks the mechanical change.

## D-01 — External backcompat consumers: safe to delete

- **Decision**: Delete `src/specify_cli/mission_read_path.py` outright; do not keep a deprecated stub.
- **Rationale**: `specify_cli.mission_read_path` is an internal module path, not a documented public
  API. A repo-wide grep shows **zero `src/` importers** — every `src/` reference is a docstring or
  comment, not an `import`. The last production importer (`runtime/next/runtime_bridge.py`) was
  re-pointed to the canonical seam by mission 01KVJPEQ. External direct-importers of an internal
  module path are unsupported.
- **Alternatives considered**: (a) keep module + add `DeprecationWarning` — rejected: does not
  reverse the ratchet bump, perpetuates the dead module the issue exists to remove. (b) defer the
  decision to implementation behind a gate — rejected: the HiC confirmed "safe to delete" up front.

## D-02 — Repoint target: alias the PRIVATE canonical worker

- **Decision**: Re-point the importer to
  `from specify_cli.missions._read_path_resolver import _resolve_mission_read_path as resolve_mission_read_path`
  (and import `StatusReadPathNotFound` directly, since it is public).
- **Rationale**: The canonical module `specify_cli.missions._read_path_resolver` does **not** export
  a public symbol named `resolve_mission_read_path`. Mission 01KVJPEQ/WP01 privatized the worker to
  `_resolve_mission_read_path` and dropped it from `__all__`; the shim existed precisely to re-export
  it under the historical public name. Its signature
  `_resolve_mission_read_path(repo_root, mission_slug, mid8, *, require_exists=False, …)` matches the
  test's call sites exactly (`resolve_mission_read_path(tmp_path, slug, mid8, require_exists=True)`),
  so an import alias preserves the test bodies verbatim (NFR-003, C-002).
- **Error-contract names**: `StatusReadPathNotFound` and `STATUS_READ_PATH_NOT_FOUND_CODE` are
  defined in `_read_path_resolver.py`; `StatusReadPathNotFound` is in `__all__` and imports cleanly.
  The test only imports `StatusReadPathNotFound` (and `resolve_mission_read_path`), both reachable.
- **Alternatives considered**: (a) re-promote `_resolve_mission_read_path` to public / add to
  `__all__` — rejected: re-grows a symbol surface 01KVJPEQ deliberately shrank, and the dead-symbol
  gate would then demand justified cross-module callers. (b) refactor the test to call a public
  entry point (`resolve_handle_to_read_path`) — rejected: changes what is under test; these cases
  specifically exercise the low-level coord-worktree-first selection of the 3-arg worker.
- **Note on a non-importer reference**: `tests/architectural/test_single_mission_surface_resolver.py`
  contains a *string fixture* (`snippet = "… from specify_cli.missions._read_path_resolver import
  resolve_mission_read_path …"`) used to test a selection-bypass ratchet. It is injected source text,
  never executed as a real import, so it does not break. Left as-is.

## D-03 — Atomicity of the dead-module gate and ratchet

- **Decision**: Land the module delete, allowlist removals, and baseline decrement in the **same
  change**.
- **Rationale**: `test_no_dead_modules.py` fails if `"specify_cli.mission_read_path"` is removed from
  `_CATEGORY_4_BACKCOMPAT_SHIMS` while the module still exists (now an un-allowlisted dead module),
  and `test_ratchet_baselines.py` fails if `_baselines.yaml` declares 8 while the live frozenset
  still contains 9 entries (C-001). The set {delete module, drop both allowlist entries, set baseline
  = 8} is internally consistent only when applied together.
- **Alternatives considered**: splitting across commits — acceptable within one WP as long as the
  working tree is consistent at review time; the gate only needs to be green at the end.

## Investigation summary (importer census)

| Reference | Kind | Action |
|-----------|------|--------|
| `src/specify_cli/mission_read_path.py` | the shim module | DELETE |
| `tests/specify_cli/cli/commands/test_coord_reader_fixes.py` (7 sites) | real `from specify_cli.mission_read_path import …` | REPOINT to canonical, alias private worker |
| `tests/integration/test_cli_status_mediation.py` | imports from canonical `_read_path_resolver` already | NO CHANGE |
| `tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py` | asserts the *string* `resolve_mission_read_path` in production source | NO CHANGE |
| `tests/architectural/test_single_mission_surface_resolver.py` (line ~828) | string fixture, not a real import | NO CHANGE (tidy docstring at line ~100 only) |
| `tests/architectural/_baselines.yaml` | ratchet ledger | `category_4_backcompat_shims: 9 → 8` + justification |
| `tests/architectural/test_no_dead_modules.py` | `_CATEGORY_4_BACKCOMPAT_SHIMS` allowlist | DROP entry |
| `tests/architectural/test_no_dead_symbols.py` | `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` allowlist | DROP entry |

## Open risks

- **Off-by-one on the baseline.** After dropping the allowlist entry, recount the live frozenset and
  confirm it equals 8 before setting the baseline (C-001).
- **Private-import lint.** Importing `_resolve_mission_read_path` (underscore-prefixed) in a test may
  trip a "private member accessed" lint in some configs. Verify `ruff`/`mypy` stay green; if a rule
  fires, the canonical seam already intends this worker for in-repo use (the shim was its only public
  face), so a narrowly-scoped, justified suppression is acceptable per the charter's suppression
  policy — but confirm a real rule fires first rather than pre-emptively suppressing.
