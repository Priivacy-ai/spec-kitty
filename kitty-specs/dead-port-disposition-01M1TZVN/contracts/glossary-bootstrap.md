# Contract: Glossary Runner Registration — the Canonical Self-Bootstrap (WP02)

**Decision**: OD5 (a) (`01M1VAHKNXJTCMQNBQ350CWGEM`) · **Working assumption**: OD6 accept documented-but-unwired (deferred) · **Requirements**: FR-008, FR-009, FR-010, SC-004, SC-005

## 1. The contract (what the four sites must say)

- `kernel.glossary_runner` is a **registry** with `GlossaryRunnerProtocol`, `register()`, `get_runner()`, `clear_registry()` (test-only).
- **Nobody registers at import or startup.** The only production provider is the consumer itself: `charter.offering.missions.glossary_hook.execute_with_glossary` calls `get_runner()`; on `None` it does `import_module("glossary.attachment")`, which exposes `GlossaryAwarePrimitiveRunner`; the hook calls `register(GlossaryAwarePrimitiveRunner)` and retries `get_runner()` (`glossary_hook.py:127-137`).
- **Degradation rule**: the primitive runs without glossary checking only when `import_module("glossary.attachment")` raises `ImportError` (pure-doctrine environments). "No runner registered" is no longer a steady state in a full install.
- **Dependency diagram** (replaces `glossary_runner.py:3`): `doctrine → kernel.glossary_runner ← charter.offering.missions.glossary_hook (lazy provider) ← glossary.attachment`. `specify_cli` plays no role.

## 2. Site-by-site edits

| Site | Edit |
|---|---|
| `src/kernel/glossary_runner.py:1-40` | Rewrite the module docstring: registry purpose, the self-bootstrap contract (§1), the degradation rule, the corrected diagram; replace the "provider (specify_cli)" usage block `:24-29` with the hook's bootstrap snippet. No code change. |
| `src/kernel/__init__.py:38-42` | Replace the "`glossary` registers … at import time" sentence with the one-line contract. |
| `src/kernel/README.md:18` | Same one-line contract; mention `clear_registry()` stays test-only. |
| `src/charter/offering/missions/glossary_hook.py:16-19` | Replace "registered … by `specify_cli` at startup" with "self-bootstrapped below (see `_bootstrap_runner`/the `get_runner()` retry at `:127-137`)"; add the FR-020 `.. note::` (§4). Optionally extract the bootstrap into a named private helper `_ensure_runner_registered()` so the docstring can point at a function — code motion only, behaviour identical. |

## 3. Behaviour pin (FR-009) — `tests/doctrine/missions/test_glossary_hook.py`

```python
def test_execute_with_glossary_self_bootstraps_registry(monkeypatch) -> None:
    clear_registry()
    assert get_runner() is None
    execute_with_glossary(<any primitive>, <ctx with glossary_check enabled>)
    runner = get_runner()
    assert runner is not None and type(runner).__name__ == "GlossaryAwarePrimitiveRunner"

def test_execute_with_glossary_degrades_only_when_attachment_unimportable(monkeypatch) -> None:
    clear_registry()
    monkeypatch.setitem(sys.modules, "glossary.attachment", None)   # makes import_module raise ImportError
    result = execute_with_glossary(<primitive>, <ctx>)
    assert result == <direct primitive result> and get_runner() is None
```
Use the file's existing fixtures for the primitive/context shapes; keep `clear_registry()` teardown.

## 4. FR-020 enforcement-honesty note (FR-010, SC-005)

Module-docstring `.. note::` in `glossary_hook.py` (verbatim intent, adjust wording):

> **Enforcement honesty (FR-020).** This hook documents `glossary_check` as enabled by default, but as of mission `dead-port-disposition-01M1TZVN` (2026-09) `execute_with_glossary` has **zero production call sites** and no built-in step contract under `packs/` sets `glossary_check`. The default is therefore enforced nowhere in the live mission loop; the tests in `tests/doctrine/missions/test_glossary_hook.py` pin the contract, not live behaviour. Wiring the hook into the step executor is a separate feature decision (tracked on #1868), not implied by this note.

Tracker note (operator posts on #1868; text drafted in the WP02 design note): same content plus the SC-004 grep and the OD6 assumption.

## 5. Verification (SC-004)

```bash
grep -n "at import time\|at startup\|registers the concrete\|specify_cli.*register" src/kernel/glossary_runner.py src/kernel/__init__.py src/kernel/README.md src/charter/offering/missions/glossary_hook.py ; echo "expect: no registration-by-specify_cli/glossary phrasing"
.venv/bin/pytest tests/doctrine/missions/test_glossary_hook.py tests/doctrine -q
.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py tests/architectural/test_layer_rules.py -q
```
Optional tidy (US2-4): the three-link re-export chain is left alone — it touches escalated live-collision pins in `test_no_dead_symbols.py`.
