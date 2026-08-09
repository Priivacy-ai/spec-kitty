"""FR-004 propagation: a per-glob non-vacuity refusal must surface as ``CoverageError``.

``description_length_check`` does not decide publication for itself — it consumes the
shared resolver via :func:`scripts.docs.description_length_check._resolve_page_set`,
which catches ``(FileNotFoundError, ValueError)`` and re-raises
:class:`~scripts.docs.description_length_check.CoverageError` (exit 2). For that
translation to hold, the resolver's per-glob pre-exclusion guard (WP01/T002) MUST raise
``ValueError``: a non-``ValueError`` type would escape ``_resolve_page_set`` and crash the
gate with a traceback instead of failing it cleanly as a gate malfunction.

This test drives the empty-glob fixture through the *consumer's* own entry point to prove
the shared-resolver failure path is inherited, not just present in the resolver.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.docs._published_pages import MINIMUM_EXPECTED_PAGES
from scripts.docs.description_length_check import CoverageError, validate_descriptions

pytestmark = [pytest.mark.unit, pytest.mark.fast]

#: Comfortably above the non-vacuity floor so the *populated* glob alone clears it —
#: the CoverageError under test can then only originate from the per-glob guard, never
#: from the aggregate floor.
_POPULATED_PAGE_COUNT = MINIMUM_EXPECTED_PAGES + 20


@pytest.fixture(scope="session")
def large_docs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A docs tree whose ``context/`` subtree alone exceeds the non-vacuity floor."""
    root = tmp_path_factory.mktemp("desc_prop") / "docs"
    context = root / "context"
    context.mkdir(parents=True)
    for index in range(_POPULATED_PAGE_COUNT):
        (context / f"page_{index:04d}.md").write_text(
            f"---\ndescription: page {index} " + ("x" * 60) + "\n---\n# page\n",
            encoding="utf-8",
        )
    return root


def _write_config(directory: Path, files: list[str], *, name: str) -> Path:
    """Write a minimal single-entry ``docfx.json`` and return its path."""
    config_path = directory / name
    config_path.write_text(
        json.dumps({"build": {"content": [{"files": files}]}}), encoding="utf-8"
    )
    return config_path


def test_dropped_glob_surfaces_as_coverage_error(large_docs: Path, tmp_path: Path) -> None:
    """An empty declared glob reds the description gate as a CoverageError, not a crash."""
    config = _write_config(tmp_path, ["context/**.md", "nowhere/**.md"], name="dropped.json")

    with pytest.raises(CoverageError, match=r"nowhere/\*\*\.md"):
        validate_descriptions(
            docs_root=large_docs, repo_root=large_docs.parent, docfx_config=config
        )


def test_populated_globs_do_not_trip_the_coverage_error(large_docs: Path, tmp_path: Path) -> None:
    """A configuration whose globs all resolve does not raise CoverageError from the guard."""
    config = _write_config(tmp_path, ["context/**.md"], name="clean.json")

    report = validate_descriptions(
        docs_root=large_docs, repo_root=large_docs.parent, docfx_config=config
    )

    assert report.checked_count >= MINIMUM_EXPECTED_PAGES
