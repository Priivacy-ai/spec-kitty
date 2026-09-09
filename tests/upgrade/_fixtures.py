"""Shared project-shape builders for the ``spec-kitty upgrade`` test suite.

Mission: upgrade-no-migrations-provisioning-fix-01M20NK8 (#4032), WP02/T010.

Two project shapes recur across ``tests/upgrade/test_upgrade_idempotency.py``,
``tests/upgrade/test_upgrade_integration.py``, and
``tests/upgrade/test_upgrade_char_net.py`` (P5/FR-010 -- previously
triplicated as three near-identical ``_init_project``/``_METADATA_YAML``
local scaffolds):

* :func:`build_config_absent_project` -- the LEGACY, config-absent shape
  (``.kittify/metadata.yaml`` only, no ``.kittify/config.yaml``). This is the
  headline #4032 repro shape: ``prepare_mission_type_activations`` observes
  ``write.before_bytes is None`` (no config authority), which is the
  condition WP02's fix defers rather than fails on. **Consumers:** WP02's own
  ``tests/upgrade/test_upgrade_guard_absent.py``; WP03 T012 migrates
  ``test_upgrade_integration.py``/``test_upgrade_idempotency.py`` onto this
  builder (their existing config-absent fixtures are legitimate witnesses of
  the same shape and must be KEPT, not re-pinned away -- research.md
  Decision 4 / FR-008).
* :func:`build_initialized_project` -- a REAL ``spec-kitty init``-ed project
  (authority present: ``.kittify/config.yaml`` exists with real content),
  driven through the actual CLI entry point via ``CliRunner`` (mirrors
  ``tests/upgrade/test_upgrade_assessment.py``'s pattern) rather than a
  hand-rolled scaffold, so it exercises the real provisioning **apply** path
  (authority present -> in-place update, not the deferred-skip path this
  mission adds). **Consumers:** smoke-exercised by
  ``tests/upgrade/test_upgrade_guard_absent.py`` (T010 anti-dead-code
  requirement -- this builder had no WP02 consumer otherwise); WP03 T013
  re-pins ``test_upgrade_char_net.py``'s oracle fixture onto it so that test
  keeps exercising the apply path instead of drifting onto the new skip path.

This module is import-only for consumers (T010) -- it defines no tests of
its own; every ``pytest`` fixture/test that exercises these builders lives in
an owning ``test_*.py`` module.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

_METADATA_YAML = (
    "spec_kitty:\n"
    "  version: '{version}'\n"
    "  initialized_at: '2026-01-01T00:00:00'\n"
    "environment:\n"
    "  python_version: '3.12'\n"
    "  platform: linux\n"
    "  platform_version: ''\n"
    "migrations:\n"
    "  applied: []\n"
)


def build_config_absent_project(root: Path, *, version: str = "1.0.0a1") -> Path:
    """Build the legacy, config-absent project shape (metadata.yaml only).

    No ``.kittify/config.yaml`` is ever written -- ``load_agent_config``
    therefore reports zero available agents, and
    ``charter.activation.compiler.prepare_mission_type_activations`` observes
    an absent config authority (``write.before_bytes is None``). This is the
    exact #4032 repro shape: the project is otherwise a normal, committed git
    checkout, so `spec-kitty upgrade` must treat the absent authority as a
    deferred no-op, not a failure.

    Git-initializes *root* (mirrors the historical per-file ``_init_project``
    helpers this consolidates) so `spec-kitty upgrade`'s auto-commit path has
    a real repository to diff against.
    """
    root.mkdir(parents=True, exist_ok=True)
    kittify = root / ".kittify"
    kittify.mkdir()
    (kittify / "metadata.yaml").write_text(_METADATA_YAML.format(version=version), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    return root


def build_initialized_project(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    home: Path | None = None,
    ai: str = "codex",
) -> Path:
    """Build a REAL ``spec-kitty init``-ed project (config authority present).

    Drives the actual ``init`` CLI command (via ``CliRunner``, mirroring
    ``tests/upgrade/test_upgrade_assessment.py``) rather than hand-rolling
    ``.kittify/config.yaml`` bytes, so the resulting project is byte-for-byte
    what a real user gets -- the authority-present counterpart to
    :func:`build_config_absent_project`.

    *home* isolates the global skill-install root (``SPEC_KITTY_HOME``/
    ``HOME``/``USERPROFILE``) so this never touches the real
    ``~/.spec-kitty``; a fresh sibling directory of *root* is used when not
    supplied. The caller's ``monkeypatch`` owns cleanup.
    """
    from specify_cli import app

    home = home if home is not None else root.parent / f"{root.name}-home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    result = CliRunner().invoke(app, ["init", str(root), "--ai", ai, "--non-interactive"])
    if result.exit_code != 0:
        raise AssertionError(f"build_initialized_project: `init` failed (exit {result.exit_code}):\n{result.output}")
    return root
