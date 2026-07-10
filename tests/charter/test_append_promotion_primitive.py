"""Unit tests for ``charter.activation_engine.promote_activations`` (WP06, T022).

``promote_activations`` is the append-only promotion primitive shared by the
config-seeded migration + interview command (WP07) and the org-pack
``required_*`` union (WP04). It accepts an arbitrary ``{yaml_key: [ids]}`` set
(NOT roots-only — org packs can mandate non-root kinds such as tactics or
styleguides) and writes exclusively through :func:`commit_plan`.

Covers:

- T022(a): promoting a directive+paradigm+styleguide set appends exactly
  those IDs, is idempotent on a second call, and writes via ``commit_plan``
  only (no direct ``save``).
- T022(b) LAND-BLOCKER — first-run parity: promoting into a previously-absent
  key preserves all-built-ins-active (the caller-supplied ``default_ids`` are
  unioned into the plan before the promoted IDs are appended) rather than
  writing a bare restrictive list. Pinned against
  ``charter.pack_context.PackContext.from_config``'s three-state absent-key
  contract so a ~19-built-in drop regression would fail this test.
- T022(c): this module carries no ``specify_cli`` import (layer rule,
  C-001) — a static AST guard, matching the style of the other layer-rule
  spot-checks in this package.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from charter.activation_engine import ActivationPlan, promote_activations
from charter.pack_context import PackContext

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers / fixtures (mirrors tests/charter/test_activation_engine.py)
# ---------------------------------------------------------------------------


def _yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


def _load(config_path: Path) -> tuple[dict[str, Any], YAML]:
    yaml = _yaml()
    data = yaml.load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    return (data or {}), yaml


def _save_with(yaml: YAML):
    """Return a single-write ``save`` callable bound to *yaml* (round-trip)."""

    def _save(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh)

    return _save


def _write_config(tmp_path: Path, content: str) -> Path:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    path = kittify / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# T022(a) — arbitrary multi-kind promotion, append-only, idempotent
# ---------------------------------------------------------------------------


def test_promote_arbitrary_kinds_appends_exactly_those_ids(tmp_path: Path) -> None:
    """Promoting a directive+paradigm+styleguide set appends exactly those."""
    config_path = _write_config(
        tmp_path,
        "activated_directives:\n  - 001-foo\n"
        "activated_paradigms:\n  - ddd\n",
    )
    data, yaml = _load(config_path)
    save = _save_with(yaml)

    plans = promote_activations(
        {
            "activated_directives": ["002-bar"],
            "activated_paradigms": ["tdd"],
            "activated_styleguides": ["py-style"],
        },
        config_path=config_path,
        config_data=data,
        save=save,
    )

    assert [p.yaml_key for p in plans] == [
        "activated_directives",
        "activated_paradigms",
        "activated_styleguides",
    ]
    assert all(isinstance(p, ActivationPlan) for p in plans)

    reloaded, _ = _load(config_path)
    assert list(reloaded["activated_directives"]) == ["001-foo", "002-bar"]
    assert list(reloaded["activated_paradigms"]) == ["ddd", "tdd"]
    # Absent-key kind (styleguides) gets exactly the promoted id — no
    # pre-existing default_ids were supplied for this key.
    assert list(reloaded["activated_styleguides"]) == ["py-style"]


def test_promote_arbitrary_kinds_writes_via_commit_plan_only(tmp_path: Path) -> None:
    """No sibling writer — every byte on disk traces to a commit_plan call."""
    config_path = _write_config(tmp_path, "activated_directives:\n  - 001-foo\n")
    data, yaml = _load(config_path)

    write_calls: list[Path] = []

    def counting_save(path: Path, payload: dict[str, Any]) -> None:
        write_calls.append(path)
        _save_with(yaml)(path, payload)

    plans = promote_activations(
        {"activated_directives": ["002-bar", "003-baz"]},
        config_path=config_path,
        config_data=data,
        save=counting_save,
    )

    # Exactly one commit_plan-mediated write per yaml_key (one key here).
    assert write_calls == [config_path]
    assert plans[0].activated == ["002-bar", "003-baz"]
    reloaded, _ = _load(config_path)
    assert list(reloaded["activated_directives"]) == ["001-foo", "002-bar", "003-baz"]


def test_promote_is_idempotent_on_repeated_calls(tmp_path: Path) -> None:
    """Promoting the same ids twice appends them exactly once (no duplicates)."""
    config_path = _write_config(tmp_path, "activated_directives:\n  - 001-foo\n")
    data, yaml = _load(config_path)
    save = _save_with(yaml)

    promote_activations(
        {"activated_directives": ["002-bar"]},
        config_path=config_path,
        config_data=data,
        save=save,
    )
    # Re-load fresh config_data the way a real caller would on a second
    # invocation (e.g. re-interview run twice).
    data2, _ = _load(config_path)
    second_plans = promote_activations(
        {"activated_directives": ["002-bar"]},
        config_path=config_path,
        config_data=data2,
        save=save,
    )

    assert second_plans[0].activated == []
    assert any("already activated" in w for w in second_plans[0].warnings)
    reloaded, _ = _load(config_path)
    assert list(reloaded["activated_directives"]) == ["001-foo", "002-bar"]


def test_promote_dedupes_ids_within_a_single_call(tmp_path: Path) -> None:
    """A duplicate id in the same promotion request is only appended once."""
    config_path = _write_config(tmp_path, "activated_tactics:\n  - t1\n")
    data, yaml = _load(config_path)
    save = _save_with(yaml)

    plans = promote_activations(
        {"activated_tactics": ["t2", "t2", "t1"]},
        config_path=config_path,
        config_data=data,
        save=save,
    )

    assert plans[0].activated == ["t2"]
    reloaded, _ = _load(config_path)
    assert list(reloaded["activated_tactics"]) == ["t1", "t2"]


# ---------------------------------------------------------------------------
# T022(b) LAND-BLOCKER — absent-key first-run parity (no built-in drop)
# ---------------------------------------------------------------------------


def test_promote_into_absent_key_preserves_all_builtins_active(tmp_path: Path) -> None:
    """Promoting into an absent key unions built-ins first — never a bare list.

    Stands in for the real ~24-directive built-in set with a small synthetic
    default_ids set so the test stays hermetic (no doctrine-tree scan). The
    key point pinned here: after the commit, none of the un-promoted
    "built-ins" (d1, d2, d3) are dropped — the promoted id (d4) is *added*,
    not substituted.
    """
    config_path = _write_config(tmp_path, "vcs:\n  type: git\n")
    data, yaml = _load(config_path)
    save = _save_with(yaml)
    builtin_directives = ["d1", "d2", "d3"]

    plans = promote_activations(
        {"activated_directives": ["d4"]},
        config_path=config_path,
        config_data=data,
        save=save,
        default_ids={"activated_directives": builtin_directives},
    )

    plan = plans[0]
    assert plan.new_list == ["d1", "d2", "d3", "d4"]
    assert plan.activated == ["d4"]
    assert any("no explicit activation set" in w for w in plan.warnings)

    reloaded, _ = _load(config_path)
    assert list(reloaded["activated_directives"]) == ["d1", "d2", "d3", "d4"]

    # PackContext.from_config resolution: none of the un-promoted built-ins
    # dropped out of the three-state activation set after the write.
    ctx = PackContext.from_config(tmp_path)
    assert ctx.activated_directives is not None
    for builtin_id in builtin_directives:
        assert builtin_id in ctx.activated_directives
    assert "d4" in ctx.activated_directives
    assert ctx.activated_directives == frozenset({"d1", "d2", "d3", "d4"})


def test_promote_into_absent_key_never_writes_bare_restrictive_list(
    tmp_path: Path,
) -> None:
    """Regression guard: an absent-key promotion must not equal the raw ids.

    Directly pins the LAND-BLOCKER: writing ``activated_directives: [d4]``
    (bare, no built-ins) into a previously-absent key would flip runtime
    resolution from "all built-ins active" to "only d4 active", dropping every
    other built-in. This asserts the committed list is a strict superset of
    the promoted ids whenever default_ids is non-empty.
    """
    config_path = _write_config(tmp_path, "vcs:\n  type: git\n")
    data, yaml = _load(config_path)
    save = _save_with(yaml)
    builtin_directives = [f"builtin-{i}" for i in range(19)]

    plans = promote_activations(
        {"activated_directives": ["promoted-1"]},
        config_path=config_path,
        config_data=data,
        save=save,
        default_ids={"activated_directives": builtin_directives},
    )

    committed = plans[0].new_list
    assert committed != ["promoted-1"]
    assert set(builtin_directives).issubset(set(committed))
    assert len(committed) == len(builtin_directives) + 1


def test_promote_into_present_key_ignores_default_ids(tmp_path: Path) -> None:
    """When the key is already present, default_ids must not be materialized."""
    config_path = _write_config(tmp_path, "activated_directives:\n  - 001-foo\n")
    data, yaml = _load(config_path)
    save = _save_with(yaml)

    plans = promote_activations(
        {"activated_directives": ["002-bar"]},
        config_path=config_path,
        config_data=data,
        save=save,
        default_ids={"activated_directives": ["999-should-not-appear"]},
    )

    reloaded, _ = _load(config_path)
    assert list(reloaded["activated_directives"]) == ["001-foo", "002-bar"]
    assert "999-should-not-appear" not in plans[0].new_list


# ---------------------------------------------------------------------------
# T022(c) — layer rule: no specify_cli import in this module
# ---------------------------------------------------------------------------


def test_activation_engine_module_has_no_specify_cli_import() -> None:
    """C-001: charter must never import specify_cli (hard layer ratchet)."""
    module_path = (
        Path(__file__).resolve().parents[2] / "src" / "charter" / "activation_engine.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "specify_cli" not in imported_roots
    # Also pin the module's own documented claim: zero charter-internal
    # imports (avoids the pack_manager <-> activation_engine import cycle).
    assert "charter" not in imported_roots
    assert "pack_manager" not in imported_roots
