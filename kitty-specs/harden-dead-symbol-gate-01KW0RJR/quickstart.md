# Quickstart / Verification: Harden the Dead-Symbol Gate

No API contracts (no `contracts/` dir) — internal architectural-test hardening. Run everything via
`uv run` (installed `spec-kitty`/tooling lags local `main`).

## Preconditions
- On `feat/harden-dead-symbol-gate` (or its lane worktree).
- Per DIR-003, best-effort assign #2158 to the HiC.
- Re-confirm live `category_a`/`category_b` frozenset sizes vs the base (depends on #2159/#2048 merge state, C-003).

## The change (per research D-05 order)
1. **FR-001** — fix `_extract_all_literal` (`tests/architectural/test_no_dead_symbols.py` ~L938): `continue` for non-`__all__` `AnnAssign` instead of `return frozenset()`. Add a unit test.
2. **FR-002 detectors** (same file, anchored to a resolved module via the per-tree alias map):
   - (a) module-style `alias.symbol` (subsumes (c) Typer registration)
   - (d-getattr) `getattr(mod, "name")`
   - (b) `__getattr__` facade static `(submodule, "name")` map
   Each detector ships a focused unit test. **Land the parser fix + all detectors in one commit** (D-01).
3. **NFR-001** — add the no-false-negative regression test (synthetic dead `__all__` symbol still flagged).
4. **FR-003/FR-004 dispositions** — delete `sync.owner::_daemon_root`; DEMOTE from `__all__`: the FR-004 set + register-arg symbols (`migrate_v1_to_v2`, `_orchestrator_api_predicate`, `_mission_state_predicate`) + any residual annotation-only/test-only. Verify no external `from`-import / star-import per symbol before demoting (C-004).
5. **FR-006** — add ONE justified allowlist-as-deferred entry for the `auth.transport` trio (SaaS migration wave).
6. **FR-005** — in `orchestrator_api/envelope.py`, make `parse_and_validate_policy` reject any `dangerous_flags` ∈ `BANNED_FLAGS`; add a `--yolo`-rejected test.
7. **`_baselines.yaml`** — reflect the net (no growth) with `# justification:` comments (C-002).

## Verification commands
```bash
# 1. The gate itself — green, with the previously-hidden 57 modules now inspected:
PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py -q

# 2. The detectors' unit tests + the no-false-negative guard:
PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py -k "detector or no_false_negative or extract_all" -q

# 3. The security fix:
PWHEADLESS=1 uv run pytest tests/agent/test_envelope_unit.py -q   # (+ the new --yolo-rejected case)

# 4. No net allowlist growth — count the frozensets vs base:
uv run python -c "import tests.architectural.test_no_dead_symbols as g; print('A', len(g._CATEGORY_A_SLICE_F_DEFERRED), 'B', len(g._CATEGORY_B_GRANDFATHERED_LEGACY))"

# 5. Full suites + lint/type:
PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q
uv run ruff check .
uv run mypy src/specify_cli/orchestrator_api/envelope.py
```

## Pass criteria (→ Success Criteria)
- `test_no_dead_symbols.py` green; the ~119 surfaced symbols are recognized live with ZERO new allowlist entries (only the deferred auth trio adds one). (SC-1, FR-002, FR-007)
- The no-false-negative regression test passes (synthetic dead symbol still flagged). (SC-2, NFR-001)
- `_daemon_root` deleted; demotes applied; `BANNED_FLAGS` enforced + tested; auth trio allowlisted-deferred. (SC-3)
- `category_a`/`category_b` frozenset counts ≤ base; `pytest tests/architectural/ tests/contract/` green; `ruff`/`mypy` clean. (SC-4, NFR-002/003/004)

## Note on CI vs local
Local `python -m ruff` (tid251) + order-flaky `test_pytest_marker_convention` + other missions' `MISSING_FRONTMATTER` are pre-existing env/unrelated failures — verify on CI, don't chase locally.
