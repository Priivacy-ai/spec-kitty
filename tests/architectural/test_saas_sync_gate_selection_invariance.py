"""#3213 — the SaaS-sync feature flag is a single collection-time authority.

Import-time ``@pytest.mark.skipif(not os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC"))``
gates are evaluated at *collection*. If any test
module sets that flag at import via its own module-level
``os.environ.setdefault(...)``, the gate's decision depends on whether that
module happens to be collected in the current selection — so the SAME node
skips under ``pytest tests/regression`` but runs under ``pytest tests/ -m
regression``. That selection-dependence is the #3213 defect.

The cure has two halves. First, ``tests/conftest.py``'s ``pytest_configure`` is
the single collection-wide authority for the flag's posture — no test module may
re-introduce a per-module write. Second (mission sync-deactivate-by-default,
WP04/FR-010) the DEFAULT collection posture is now sync-**OFF**: ``pytest_configure``
deliberately does NOT set ``SPEC_KITTY_ENABLE_SAAS_SYNC``, so the WP05
collection-time skipif gates actually fire on a bare push. Opt-in is a
process-level env var set BEFORE collection by the ``fast-tests-sync`` CI job
(the #3213 lesson: a fixture runs too late for ``skipif``). These guards pin the
combined contract:

1. the flag is NOT *forced on* at collection time by default (default-off), and
   its collection-time value — unset by default, ``"1"`` only under the sanctioned
   opt-in job — agrees with :func:`sync_active`;
2. the opt-in path (flag set, no disable var) deterministically flips
   ``sync_active()`` on; unsetting it flips it off;
3. NO test module re-introduces a module-level write of the flag (which would
   restore the selection-dependence).

Whatever the collection-time posture, every import-time SaaS-sync gate makes the
same skip/run decision under ``pytest tests/regression`` and ``pytest tests/ -m
regression`` — the selection-invariance the #3213 fix bought is preserved; only
the default *value* flipped from forced-on to off (#3799). (Historically the
forced-on default re-exposed the then-open #2782 P0 red under ``pytest
tests/regression``; #2782 has since been resolved and its reproduction retired.)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.unit]

_FLAG = "SPEC_KITTY_ENABLE_SAAS_SYNC"
_TESTS_ROOT = Path(__file__).resolve().parents[1]
#: The single sanctioned authority that sets the flag collection-wide: the ROOT
#: tests/conftest.py only. A NESTED conftest.py writing the flag would apply to
#: its subtree alone -- reintroducing the exact selection-dependence this guards
#: against -- so it is NOT exempt.
_ALLOWED_RELPATHS = {Path("conftest.py")}


#: The sync-disable escape hatches ``sync_active()`` also honours; unset by the
#: opt-in arm so the flip is governed by the enable flag alone.
_SYNC_DISABLE_VARS = ("SPEC_KITTY_SYNC_DISABLE", "SPEC_KITTY_SYNC_MINIMAL_IMPORT")


def test_flag_is_not_forced_on_at_collection_time() -> None:
    """Default-off contract (WP04/FR-010, #3799): ``pytest_configure`` no longer
    *forces* the enable flag on collection-wide.

    The collection-time value is either unset (the default push posture, so the
    WP05 skipif gates fire) or ``"1"`` (the sanctioned ``fast-tests-sync`` opt-in
    job, set once process-wide). Both are honest; a hard-coded ``== "1"`` would
    fight the default push path and a hard-coded ``is None`` would fight the
    opt-in job — so this pins the value against :func:`sync_active`, whichever
    posture the collection ran under.
    """
    import os

    from specify_cli.core.saas_sync_config import sync_active

    flag = os.environ.get(_FLAG)
    if flag is None:
        assert sync_active() is False, (
            f"{_FLAG} is unset at collection (the WP04 default-off posture), so "
            "sync_active() must read False — the import-time skipif gates fire."
        )
    else:
        assert flag == "1", (
            f"the only sanctioned collection-time value of {_FLAG} is '1', set "
            "once process-wide by the fast-tests-sync opt-in CI job; a stray "
            f"other value ({flag!r}) means an ad-hoc write leaked in."
        )


def test_opt_in_flips_sync_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """The opt-in path deterministically arms ``sync_active()``; unset disarms it.

    Proves the flip directly (call-time env control) rather than relying on the
    ambient collection posture, so the contract holds identically under the
    default push path and the opt-in CI job.
    """
    from specify_cli.core.saas_sync_config import sync_active

    for var in _SYNC_DISABLE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv(_FLAG, "1")
    assert sync_active() is True, "flag set + no disable var must arm sync_active()"
    monkeypatch.delenv(_FLAG, raising=False)
    assert sync_active() is False, "clearing the flag must disarm sync_active()"


def _module_level_flag_writers() -> list[str]:
    """Test files that write ``SPEC_KITTY_ENABLE_SAAS_SYNC`` at module scope.

    AST-based (not a text grep) so comments and string literals mentioning the
    flag do not count — only real module-level ``os.environ[...] = ...`` /
    ``os.environ.setdefault(...)`` statements do.
    """
    offenders: list[str] = []
    for path in _TESTS_ROOT.rglob("*.py"):
        if path.relative_to(_TESTS_ROOT) in _ALLOWED_RELPATHS:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:  # module scope only — nested (in-test) writes are fine
            if _statement_writes_flag(node):
                offenders.append(str(path.relative_to(_TESTS_ROOT)))
                break
    return offenders


def _statement_writes_flag(node: ast.stmt) -> bool:
    if isinstance(node, ast.Assign):
        return any(_is_environ_subscript_of_flag(t) for t in node.targets)
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return _is_environ_setdefault_of_flag(node.value)
    return False


def _is_environ_subscript_of_flag(target: ast.expr) -> bool:
    # os.environ["SPEC_KITTY_ENABLE_SAAS_SYNC"] = ...
    return (
        isinstance(target, ast.Subscript)
        and _is_os_environ(target.value)
        and _is_flag_constant(target.slice)
    )


def _is_environ_setdefault_of_flag(call: ast.Call) -> bool:
    # os.environ.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", ...)
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "setdefault"
        and _is_os_environ(func.value)
        and bool(call.args)
        and _is_flag_constant(call.args[0])
    )


def _is_os_environ(expr: ast.expr) -> bool:
    return (
        isinstance(expr, ast.Attribute)
        and expr.attr == "environ"
        and isinstance(expr.value, ast.Name)
        and expr.value.id == "os"
    )


def _is_flag_constant(expr: ast.expr) -> bool:
    return isinstance(expr, ast.Constant) and expr.value == _FLAG


def test_no_test_module_sets_the_flag_at_import_time() -> None:
    """Only tests/conftest.py may set the flag; module-level writes bring back
    the #3213 selection-dependence."""
    offenders = _module_level_flag_writers()
    assert not offenders, (
        f"These test modules set {_FLAG} at import time, which makes import-time "
        "skipif gates depend on the current selection (#3213). Remove the "
        "module-level write; the flag is set collection-wide in "
        "tests/conftest.py pytest_configure:\n"
        + "\n".join(f"    - {o}" for o in sorted(offenders))
    )


def test_scan_is_not_vacuous() -> None:
    """The AST scan actually detects a module-level flag write (bite proof)."""
    sample = f'import os\nos.environ.setdefault("{_FLAG}", "1")\n'
    tree = ast.parse(sample)
    assert any(_statement_writes_flag(node) for node in tree.body)
    # ...and does NOT flag a nested (in-function) write or a mere mention.
    nested = f'import os\ndef f():\n    os.environ["{_FLAG}"] = "1"\n'
    assert not any(_statement_writes_flag(node) for node in ast.parse(nested).body)
