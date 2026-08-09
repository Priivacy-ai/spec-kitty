"""WP01 census of consent grants and hosted-state writers.

The inventory is intentionally structural.  It keeps legacy refusal and grant
paths distinct, rejects growth, and exposes strict synthetic predicates that
later WPs can apply once ``ProjectSyncStore`` becomes the only write authority.
"""

from __future__ import annotations

import ast
import warnings
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.sync.consent import resolve_project_consent

pytestmark = [pytest.mark.architectural]

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
_SYNC_FILES = tuple(
    sorted(
        {
            *(_SRC / "specify_cli" / "sync").rglob("*.py"),
            _SRC / "specify_cli" / "cli" / "commands" / "sync.py",
        }
    )
)

_CONSENT_WRITERS = frozenset(
    {
        "set_project_consent",
        "set_project_consent_bulk",
        "set_checkout_sync_enabled",
        "set_repository_sync_enabled",
        "write_local_sync_enabled",
        "enable_checkout_sync",
        "disable_checkout_sync",
        "backfill_uuid_consent_index",
    }
)


@dataclass(frozen=True, order=True)
class WriterCall:
    relpath: str
    qualname: str
    callee: str
    lineno: int

    @property
    def key(self) -> str:
        return f"{self.relpath}::{self.qualname}::{self.callee}"


class _CallVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.scope: list[str] = []
        self.calls: list[WriterCall] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        callee = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
        if callee in _CONSENT_WRITERS:
            self.calls.append(
                WriterCall(
                    self.path.relative_to(_SRC).as_posix(),
                    ".".join(self.scope) or "<module>",
                    callee,
                    node.lineno,
                )
            )
        self.generic_visit(node)


def scan_consent_writer_calls(paths: tuple[Path, ...] = _SYNC_FILES) -> tuple[WriterCall, ...]:
    found: list[WriterCall] = []
    for path in paths:
        visitor = _CallVisitor(path)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        found.extend(visitor.calls)
    return tuple(sorted(found))


_KNOWN_CONSENT_WRITER_CALLS = frozenset(
    {
        "specify_cli/cli/commands/sync.py::_run_consent_index_backfill::backfill_uuid_consent_index",
        "specify_cli/cli/commands/sync.py::opt_in::enable_checkout_sync",
        "specify_cli/cli/commands/sync.py::opt_out::disable_checkout_sync",
        "specify_cli/sync/config.py::SyncConfig.set_project_consent::set_project_consent_bulk",
        "specify_cli/sync/consent.py::_reconcile_index::set_project_consent",
        "specify_cli/sync/consent.py::backfill_uuid_consent_index::set_project_consent_bulk",
        "specify_cli/sync/consent.py::set_project_consent::set_project_consent",
        "specify_cli/sync/routing.py::disable_checkout_sync::set_project_consent",
        "specify_cli/sync/routing.py::disable_checkout_sync::set_repository_sync_enabled",
        "specify_cli/sync/routing.py::disable_checkout_sync::write_local_sync_enabled",
        "specify_cli/sync/routing.py::enable_checkout_sync::set_project_consent",
        "specify_cli/sync/routing.py::enable_checkout_sync::set_repository_sync_enabled",
        "specify_cli/sync/routing.py::enable_checkout_sync::write_local_sync_enabled",
        "specify_cli/sync/routing.py::write_local_sync_enabled::set_checkout_sync_enabled",
    }
)

_LEGACY_REFUSAL_CALLS = frozenset(
    {
        "specify_cli/sync/routing.py::disable_checkout_sync::set_project_consent",
        "specify_cli/sync/routing.py::disable_checkout_sync::set_repository_sync_enabled",
        "specify_cli/sync/routing.py::disable_checkout_sync::write_local_sync_enabled",
    }
)

_GRANT_INPUT_CENSUS = {
    "explicit-project-local": "sync.enabled",
    "machine-uuid-index": "set_project_consent",
    "bulk-index": "set_project_consent_bulk",
    "checkout-default": "set_checkout_sync_enabled",
    "repository-default": "set_repository_sync_enabled",
    "environment-arming": "SPEC_KITTY_ENABLE_SAAS_SYNC",
    "legacy-backfill": "backfill_uuid_consent_index",
    "cli-explicit-opt-in": "opt_in",
}

_NON_GRANT_INPUTS = frozenset(
    {
        "login",
        "host",
        "target",
        "project discovery",
        "path alias",
        "shared store presence",
        "truthy environment",
    }
)


def final_grant_writer_violations(calls: tuple[WriterCall, ...]) -> tuple[WriterCall, ...]:
    """Only the explicit per-project store decision may grant in the final tree."""
    allowed = (
        "specify_cli/sync/project_store.py",
        "ProjectSyncStore.set_consent_decision",
    )
    return tuple(call for call in calls if not (call.relpath == allowed[0] and call.qualname == allowed[1]))


def source_grants_from_environment(source: str) -> bool:
    """Synthetic mutation predicate: a truthy env branch must not grant."""
    tree = ast.parse(source)
    env_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) for target in node.targets):
            value_text = ast.unparse(node.value)
            if "getenv" in value_text or "environ" in value_text:
                env_names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and any(isinstance(name, ast.Name) and name.id in env_names for name in ast.walk(node.test))
            and any(
                isinstance(item, ast.Return) and isinstance(item.value, ast.Constant) and item.value.value is True for stmt in node.body for item in ast.walk(stmt)
            )
        ):
            return True
    return False


def test_consent_writer_census_cannot_grow_and_refusals_remain_distinct() -> None:
    calls = scan_consent_writer_calls()
    keys = {call.key for call in calls}
    growth = keys - _KNOWN_CONSENT_WRITER_CALLS
    assert not growth, "new consent writer call paths:\n" + "\n".join(sorted(growth))
    assert keys >= _LEGACY_REFUSAL_CALLS
    shrink = _KNOWN_CONSENT_WRITER_CALLS - keys
    if shrink:
        warnings.warn(
            "consent-writer census shrank; do not widen the baseline: " + ", ".join(sorted(shrink)),
            stacklevel=1,
        )


def test_grant_input_census_names_every_legacy_source_and_non_grant() -> None:
    assert set(_GRANT_INPUT_CENSUS) == {
        "explicit-project-local",
        "machine-uuid-index",
        "bulk-index",
        "checkout-default",
        "repository-default",
        "environment-arming",
        "legacy-backfill",
        "cli-explicit-opt-in",
    }
    assert {
        "login",
        "host",
        "target",
        "project discovery",
        "path alias",
        "shared store presence",
        "truthy environment",
    } == _NON_GRANT_INPUTS


def test_absence_denies_despite_truthy_env_and_unrelated_operator_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "isolated-home"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://app.spec-kitty.ai")
    monkeypatch.setenv("SPEC_KITTY_TEAM", "logged-in-team")
    decision = resolve_project_consent(
        "aaaaaaaa-0000-0000-0000-000000000001",
        repo_root=tmp_path / "same-slug-does-not-vouch",
    )
    assert decision.granted is False


def test_synthetic_environment_grant_mutant_is_rejected() -> None:
    clean = """
def decide():
    armed = os.getenv('SPEC_KITTY_ENABLE_SAAS_SYNC')
    if armed:
        return read_explicit_project_decision()
    return False
"""
    mutant = """
def decide():
    armed = os.getenv('SPEC_KITTY_ENABLE_SAAS_SYNC')
    if armed:
        return True
    return False
"""
    assert source_grants_from_environment(clean) is False
    assert source_grants_from_environment(mutant) is True


def test_final_writer_predicate_rejects_a_legacy_grant_path() -> None:
    legacy = WriterCall(
        "specify_cli/sync/routing.py",
        "enable_checkout_sync",
        "set_project_consent",
        1,
    )
    canonical = WriterCall(
        "specify_cli/sync/project_store.py",
        "ProjectSyncStore.set_consent_decision",
        "set_consent_decision",
        1,
    )
    assert final_grant_writer_violations((canonical,)) == ()
    assert final_grant_writer_violations((legacy,)) == (legacy,)
