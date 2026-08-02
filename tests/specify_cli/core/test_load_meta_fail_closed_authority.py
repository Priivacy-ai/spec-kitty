"""FR-007 / #3140 — the ONE public fail-closed ``meta.json`` reader.

``specify_cli.core.paths.load_meta_fail_closed`` is the single public authority
for the fail-closed ``meta.json`` contract (WP07).  These tests pin that
contract at the reader itself:

- a corrupt (unparseable) ``meta.json`` → typed :class:`MissionMetaReadError`
- a non-dict (``[]``) ``meta.json``     → typed :class:`MissionMetaReadError`
- a **raw** :class:`ValueError` never escapes the reader
- a missing ``meta.json``               → ``None`` (field-absent, not a failure)

They also pin the two structural guards the promotion must not break: the
reader is genuinely public (exported from ``core.paths``), and its
``mission_metadata`` import stays **function-local** so the
``core.paths <-> mission_metadata`` import cycle does not re-form.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from specify_cli.core.paths import MissionMetaReadError, load_meta_fail_closed

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# The reader's contract is "typed exception or None, never a raw ValueError".
# MissionMetaReadError subclasses RuntimeError precisely so a caller's
# ``except ValueError`` cannot silently absorb a corruption verdict.
_CORRUPT_JSON = '{"mission_id":"01CORRUPT12345678901234","coordination_branch":'


def _write_meta(feature_dir: Path, text: str) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(text, encoding="utf-8")
    return meta_path


# ---------------------------------------------------------------------------
# Fail-closed contract
# ---------------------------------------------------------------------------


def test_corrupt_meta_raises_typed_error_not_raw_value_error(tmp_path: Path) -> None:
    """Unparseable JSON → MissionMetaReadError carrying path + cause."""
    meta_path = _write_meta(tmp_path / "corrupt-mission", _CORRUPT_JSON)

    with pytest.raises(MissionMetaReadError) as exc_info:
        load_meta_fail_closed(tmp_path / "corrupt-mission")

    exc = exc_info.value
    assert exc.meta_path == meta_path
    assert isinstance(exc.cause, ValueError)
    # Fail-closed doctrine: the typed error is NOT a ValueError, so a caller's
    # ``except ValueError`` cannot launder corruption into a tolerant branch.
    assert not isinstance(exc, ValueError)


def test_non_dict_meta_raises_typed_error_not_raw_value_error(tmp_path: Path) -> None:
    """A valid-JSON but non-object top level fails closed too (US3 scenario 2)."""
    _write_meta(tmp_path / "array-mission", "[]")

    with pytest.raises(MissionMetaReadError) as exc_info:
        load_meta_fail_closed(tmp_path / "array-mission")

    assert "Expected JSON object" in str(exc_info.value)
    assert not isinstance(exc_info.value, ValueError)


@pytest.mark.parametrize(
    ("label", "content"),
    [
        ("corrupt", _CORRUPT_JSON),
        ("non_dict_list", "[]"),
        ("non_dict_scalar", '"just-a-string"'),
        ("empty_file", ""),
    ],
)
def test_no_raw_value_error_escapes_the_public_reader(
    tmp_path: Path, label: str, content: str
) -> None:
    """NFR-003: zero raw ValueError across the malformed shapes."""
    _write_meta(tmp_path / label, content)

    try:
        load_meta_fail_closed(tmp_path / label)
    except MissionMetaReadError:
        pass  # the typed, expected outcome
    except ValueError as exc:  # pragma: no cover - regression guard
        pytest.fail(f"raw ValueError leaked for {label!r}: {exc}")


def test_missing_meta_returns_none_not_an_error(tmp_path: Path) -> None:
    """A missing file is the field-absent case, never a read failure."""
    absent_dir = tmp_path / "no-meta-here"
    absent_dir.mkdir()

    assert load_meta_fail_closed(absent_dir) is None


def test_valid_meta_returns_parsed_mapping(tmp_path: Path) -> None:
    """The happy path still returns the parsed mapping unchanged."""
    payload = {"mission_id": "01ABCDEF1234567890123456", "target_branch": "main"}
    _write_meta(tmp_path / "good-mission", json.dumps(payload))

    assert load_meta_fail_closed(tmp_path / "good-mission") == payload


# ---------------------------------------------------------------------------
# Structural guards on the promotion (FR-007 / research.md D4)
# ---------------------------------------------------------------------------


def test_reader_is_public_and_exported() -> None:
    """One home, publicly reachable — no private-only second authority."""
    from specify_cli.core import paths

    assert "load_meta_fail_closed" in paths.__all__
    assert not load_meta_fail_closed.__name__.startswith("_")
    # The retired private name must not linger as a parallel alias.
    assert not hasattr(paths, "_load_meta_fail_closed")


def test_mission_metadata_import_stays_function_local() -> None:
    """D4 guard: hoisting the import re-forms the core.paths <-> mission_metadata cycle.

    Asserted structurally (AST) rather than by comment, because the failure mode
    is a silent import cycle that only bites at a specific import order.
    """
    from specify_cli.core import paths

    source = Path(paths.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    module_level_imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
        if node.module.startswith("specify_cli.mission_metadata")
    }
    assert not module_level_imports, (
        "specify_cli.mission_metadata must NOT be imported at module level in "
        f"core/paths.py (found {sorted(module_level_imports)}) — it re-forms the "
        "core.paths <-> mission_metadata circular import (research.md D4)."
    )

    reader = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "load_meta_fail_closed"
    )
    local_imports = {
        alias.name
        for node in ast.walk(reader)
        if isinstance(node, ast.ImportFrom) and node.module == "specify_cli.mission_metadata"
        for alias in node.names
    }
    assert "load_meta" in local_imports, (
        "load_meta_fail_closed must import the canonical parser inside the "
        "function body (deferred import) — see research.md D4."
    )
