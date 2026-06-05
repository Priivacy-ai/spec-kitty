"""Tests for ``specify_cli.doctrine_service_factory`` (WP03, FR-010).

Covers:
* the three-state ``activated_agent_profiles`` filtering contract
  (absent key → all built-ins; empty set → ``{}``; explicit set → those IDs);
* a layer-safety guard proving the factory module does not drag
  ``specify_cli`` into the ``charter`` / ``doctrine`` layers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.doctrine_service_factory import (
    build_activation_aware_doctrine_service,
)


def _write_config(repo_root: Path, body: str) -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(body, encoding="utf-8")


def _builtin_profile_ids() -> set[str]:
    """Return the IDs of the real built-in agent profiles.

    The factory builds the inner service from the packaged built-in doctrine
    root, so the unfiltered result must equal this discovered set.
    """
    from charter.catalog import resolve_doctrine_root
    from doctrine.agent_profiles import AgentProfileRepository

    repo = AgentProfileRepository(
        built_in_dir=resolve_doctrine_root() / "agent_profiles" / "built-in",
    )
    return {p.profile_id for p in repo.list_all()}


@pytest.fixture()
def builtin_ids() -> set[str]:
    ids = _builtin_profile_ids()
    if not ids:
        pytest.skip("no built-in agent profiles available in this layout")
    return ids


def test_absent_key_returns_all_builtins(tmp_path: Path, builtin_ids: set[str]) -> None:
    """No ``activated_agent_profiles`` key → every built-in is available."""
    _write_config(tmp_path, "agents:\n  available:\n    - claude\n")

    service = build_activation_aware_doctrine_service(tmp_path)

    assert set(service.agent_profiles.keys()) == builtin_ids


def test_empty_set_returns_nothing(tmp_path: Path, builtin_ids: set[str]) -> None:
    """Explicit empty ``activated_agent_profiles: []`` → no profiles available."""
    _write_config(tmp_path, "activated_agent_profiles: []\n")

    service = build_activation_aware_doctrine_service(tmp_path)

    assert service.agent_profiles == {}


def test_explicit_set_returns_only_those_ids(
    tmp_path: Path, builtin_ids: set[str]
) -> None:
    """Explicit ``activated_agent_profiles`` → only the listed IDs survive."""
    chosen = sorted(builtin_ids)[0]
    _write_config(tmp_path, f"activated_agent_profiles:\n  - {chosen}\n")

    service = build_activation_aware_doctrine_service(tmp_path)

    assert set(service.agent_profiles.keys()) == {chosen}


def test_returns_charter_resolver_wrapper(tmp_path: Path) -> None:
    """The factory returns the reused ``charter.resolver.DoctrineService`` wrapper."""
    from charter.resolver import DoctrineService as ActivationDoctrineService

    _write_config(tmp_path, "agents:\n  available:\n    - claude\n")

    service = build_activation_aware_doctrine_service(tmp_path)

    assert isinstance(service, ActivationDoctrineService)


def test_layer_safety_charter_and_doctrine_do_not_import_specify_cli() -> None:
    """Importing the factory must not pull ``specify_cli`` into charter/doctrine.

    The factory lives in ``specify_cli.*`` and may import ``charter.*`` +
    ``doctrine.service`` (the allowed direction).  But the modules it pulls in
    from the ``charter`` and ``doctrine`` layers must never import back into
    ``specify_cli`` — that would invert the dependency direction (C-005).
    """
    import ast
    import importlib
    import sys

    # Ensure the factory and its transitive charter/doctrine deps are loaded.
    importlib.import_module("specify_cli.doctrine_service_factory")
    importlib.import_module("charter.resolver")
    importlib.import_module("charter.pack_context")
    importlib.import_module("doctrine.service")

    def _imports_specify_cli(source_path: Path) -> bool:
        """Return True iff the module *actually* imports ``specify_cli`` (AST, not text).

        A docstring or comment that merely mentions the string ``specify_cli``
        must not count; only real ``import``/``from`` statements do.
        """
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] == "specify_cli" for alias in node.names):
                    return True
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root == "specify_cli":
                    return True
        return False

    offenders: list[str] = []
    for name, module in list(sys.modules.items()):
        if module is None:
            continue
        if not (name == "charter" or name == "doctrine" or name.startswith(("charter.", "doctrine."))):
            continue
        source = getattr(module, "__file__", None)
        if not source:
            continue
        if _imports_specify_cli(Path(source)):
            offenders.append(name)

    assert not offenders, (
        "charter/doctrine layer modules must not import specify_cli "
        f"(found: {sorted(offenders)})"
    )
