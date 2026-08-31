"""Reader tests for the project ``path_conventions`` override (#3016, WP01 T003).

Covers FR-001 (read), FR-007 (validate keys), FR-008 (fail-closed section), C-010 (deliverables
excluded), C-011 (reads the subkey, not the whole ``project:`` block).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.config.path_conventions import (
    PathConventionsConfigError,
    load_project_path_conventions,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_config(repo_root: Path, body: str) -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(body, encoding="utf-8")


def test_absent_config_returns_empty(tmp_path: Path) -> None:
    assert load_project_path_conventions(tmp_path) == {}


def test_absent_section_returns_empty(tmp_path: Path) -> None:
    _write_config(tmp_path, "project:\n  slug: demo\n")
    assert load_project_path_conventions(tmp_path) == {}


def test_valid_subset_returned(tmp_path: Path) -> None:
    _write_config(tmp_path, "project:\n  path_conventions:\n    workspace: apps/\n    tests: tests/\n")
    assert load_project_path_conventions(tmp_path) == {"workspace": "apps/", "tests": "tests/"}


def test_identity_fields_alongside_override_not_rejected(tmp_path: Path) -> None:
    """C-011: the reader reads only the ``path_conventions`` subkey, so the real ``project:`` identity
    fields (uuid/slug/node_id/build_id) coexist without being rejected."""
    _write_config(
        tmp_path,
        "project:\n  uuid: 01ABC\n  slug: my-project\n  node_id: node-7\n  build_id: b-42\n  path_conventions:\n    workspace: apps/\n",
    )
    assert load_project_path_conventions(tmp_path) == {"workspace": "apps/"}


def test_typo_key_rejected(tmp_path: Path) -> None:
    _write_config(tmp_path, "project:\n  path_conventions:\n    worksapce: apps/\n")
    with pytest.raises(PathConventionsConfigError, match="worksapce"):
        load_project_path_conventions(tmp_path)


def test_deliverables_key_ignored(tmp_path: Path) -> None:
    """C-010: overriding the artifact-routed ``deliverables`` key is warned-and-ignored, never applied."""
    _write_config(
        tmp_path,
        "project:\n  path_conventions:\n    workspace: apps/\n    deliverables: build/\n",
    )
    with pytest.warns(UserWarning, match="deliverables"):
        result = load_project_path_conventions(tmp_path)
    assert result == {"workspace": "apps/"}


def test_section_not_a_mapping_raises(tmp_path: Path) -> None:
    _write_config(tmp_path, "project:\n  path_conventions: not-a-mapping\n")
    with pytest.raises(PathConventionsConfigError, match="must be a mapping"):
        load_project_path_conventions(tmp_path)


def test_non_string_value_raises(tmp_path: Path) -> None:
    _write_config(tmp_path, "project:\n  path_conventions:\n    workspace: 123\n")
    with pytest.raises(PathConventionsConfigError, match="workspace"):
        load_project_path_conventions(tmp_path)


def test_null_value_raises(tmp_path: Path) -> None:
    _write_config(tmp_path, "project:\n  path_conventions:\n    workspace:\n")
    with pytest.raises(PathConventionsConfigError, match="workspace"):
        load_project_path_conventions(tmp_path)


def test_corrupt_file_is_lenient(tmp_path: Path) -> None:
    """A whole-file-corrupt ``config.yaml`` returns ``{}`` (lenient), matching the co-resident section
    readers — fail-closed is scoped to the section shape, not the file."""
    _write_config(tmp_path, "project: [this: is, : broken yaml\n  path_conventions\n")
    assert load_project_path_conventions(tmp_path) == {}


def test_empty_string_value_raises(tmp_path: Path) -> None:
    """MAJOR (adversarial squad, fix #1): an empty-string value must be rejected, not silently accepted.

    ``Path("")`` collapses to the repo root under ``validate_mission_paths`` (which always exists), so
    an empty override silently defeats strict enforcement (SC-006/SC-007) instead of naming a missing
    directory. See the red-first proof in ``tests/agent/test_validators_unit.py``.
    """
    _write_config(tmp_path, 'project:\n  path_conventions:\n    workspace: ""\n')
    with pytest.raises(PathConventionsConfigError, match="workspace"):
        load_project_path_conventions(tmp_path)


def test_blank_string_value_raises(tmp_path: Path) -> None:
    """A whitespace-only value is just as empty as ``""`` once ``.strip()``-ped — must also raise."""
    _write_config(tmp_path, 'project:\n  path_conventions:\n    workspace: "   "\n')
    with pytest.raises(PathConventionsConfigError, match="workspace"):
        load_project_path_conventions(tmp_path)


def test_absolute_path_value_raises(tmp_path: Path) -> None:
    """MINOR (fix #2): an absolute-path value would target an out-of-repo directory that always exists
    (e.g. ``/tmp``), making the gate trivially pass — ``path_conventions`` values are repo-relative
    layout directories only."""
    _write_config(tmp_path, "project:\n  path_conventions:\n    workspace: /tmp\n")
    with pytest.raises(PathConventionsConfigError, match="workspace"):
        load_project_path_conventions(tmp_path)


def test_dotdot_traversal_value_raises(tmp_path: Path) -> None:
    """A ``..``-traversal value could walk the check outside the repo — reject it, same as an
    absolute path."""
    _write_config(tmp_path, "project:\n  path_conventions:\n    workspace: ../elsewhere\n")
    with pytest.raises(PathConventionsConfigError, match="workspace"):
        load_project_path_conventions(tmp_path)


def test_relative_trailing_slash_value_still_accepted(tmp_path: Path) -> None:
    """Non-regression: a normal repo-relative value with a trailing slash (e.g. ``apps/``) must still be
    accepted — it is later normalized by ``_normalize_path_token`` at the merge site, not here."""
    _write_config(tmp_path, "project:\n  path_conventions:\n    workspace: apps/\n")
    assert load_project_path_conventions(tmp_path) == {"workspace": "apps/"}
