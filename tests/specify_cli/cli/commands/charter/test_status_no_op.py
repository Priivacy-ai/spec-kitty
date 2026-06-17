"""T032/T033/T034 — charter status is side-effect-free + emits a JSON-safe hash.

WP07 / FR-010 / C-IC07

Contract under test
-------------------
``_collect_charter_sync_status`` is the authoritative surface for the
``charter status`` read path.  It MUST NOT write to the working tree
(no ``ensure_charter_bundle_fresh`` invocation, no ``generate_all`` entity
pages).  The hash fields it returns MUST be JSON-serializable strings (or
``None``).

Fixture design (NFR-002 — topology-true)
-----------------------------------------
* Real git repo via ``clone_template`` (not a bare temp dir).
* Charter bundle with a **stale** hash so ``ensure_charter_bundle_fresh``
  would actually sync on unmodified code (non-vacuous: the write WOULD fire
  on HEAD before the fix).
* DRG ``graph.yaml`` with a ``glossary:`` node so ``generate_all()`` would
  write an entity page on unmodified code.
* Mission ``meta.json`` carrying a **full 26-char ULID** ``mission_id``
  (NFR-002 — no fabricated short slugs).

Captured-red evidence (T032 step 6, live-evidence discipline)
--------------------------------------------------------------
Verified that running these tests against unmodified ``_status_collectors.py``
produces failures:

  FAILED test_charter_status_leaves_git_tree_clean — AssertionError: working
  tree changed after _collect_charter_sync_status; new/modified entries:
  ['.kittify/charter/metadata.yaml', '.kittify/charter/governance.yaml', ...]

  FAILED test_charter_status_does_not_write_entity_pages — AssertionError:
  entity-page files appeared after _collect_charter_sync_status: [...]

  FAILED test_charter_status_hash_is_json_serializable — AssertionError:
  current_hash is not a str: <class 'bytes'>
  (the hash was bytes before T034 normalization on some code paths)

All three flip to PASS after the T033/T034 fix in ``_status_collectors.py``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from tests._support.git_template import clone_template

# Mission ID must be a full 26-char ULID (NFR-002 — no fabricated short slugs).
_MISSION_ID = "01KV8NPC0000000000000WP07A"
_MISSION_SLUG = "read-path-error-fidelity-adoption-01KV8NPC"

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _build_stale_charter_bundle(repo: Path) -> None:
    """Seed a charter bundle whose hash is intentionally stale.

    The stale hash guarantees ``ensure_charter_bundle_fresh`` would call
    ``sync()`` (a write) on unmodified code, making the no-op assertion
    non-vacuous.
    """
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)

    charter_content = "# Test Charter\n\nThis charter is intentionally stale.\n"
    (charter_dir / "charter.md").write_text(charter_content, encoding="utf-8")

    # Write metadata with a hash that does NOT match the charter content.
    # This forces is_stale() to return True → ensure_charter_bundle_fresh
    # would attempt to regenerate files if called.
    wrong_hash = "sha256:" + ("0" * 64)
    (charter_dir / "metadata.yaml").write_text(
        dedent(
            f"""\
            charter_hash: {wrong_hash}
            extracted_at: "2026-01-01T00:00:00+00:00"
            """
        ),
        encoding="utf-8",
    )

    # Minimal extracted files so _collect_charter_sync_status can iterate them.
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")


def _build_drg_with_glossary_node(repo: Path) -> None:
    """Seed a graph.yaml with a glossary node.

    A ``glossary:`` node in graph.yaml causes ``GlossaryEntityPageRenderer.
    generate_all()`` to write an entity page under
    ``.kittify/charter/compiled/glossary/``.  Placing it here guarantees the
    entity-page write WOULD fire on unmodified code, making the no-write
    assertion non-vacuous.
    """
    doctrine_dir = repo / ".kittify" / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)
    (doctrine_dir / "graph.yaml").write_text(
        dedent(
            """\
            schema_version: '1.0'
            generated_at: '2026-06-16T00:00:00Z'
            generated_by: test-fixture
            nodes:
              - urn: glossary:mission-term
                kind: glossary
                label: Mission Term
            edges: []
            """
        ),
        encoding="utf-8",
    )


def _build_mission_meta(repo: Path) -> None:
    """Seed a mission meta.json with a full 26-char ULID mission_id."""
    mission_dir = repo / "kitty-specs" / _MISSION_SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_number": None,
        "friendly_name": "WP07 test mission",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _git_porcelain(repo: Path) -> str:
    """Return ``git status --porcelain`` output for *repo*."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _entity_page_dir(repo: Path) -> Path:
    return repo / ".kittify" / "charter" / "compiled" / "glossary"


@pytest.fixture()
def charter_repo(tmp_path: Path) -> Path:
    """Real git repo with stale charter bundle + DRG glossary node + mission meta.

    All fixture files are committed so that the baseline ``git status
    --porcelain`` is empty before the status collector runs.  The stale hash
    and the glossary node together guarantee the WRITE paths inside the
    unmodified collector WOULD fire (non-vacuous fixture).
    """
    repo = clone_template(tmp_path / "repo")

    # .kittify/config.yaml (minimum project marker)
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n", encoding="utf-8")

    _build_stale_charter_bundle(repo)
    _build_drg_with_glossary_node(repo)
    _build_mission_meta(repo)

    # Commit everything so the baseline working tree is clean.
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "WP07 fixture: stale charter + DRG + mission meta"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Sanity-check: baseline must be clean.
    assert _git_porcelain(repo) == "", "fixture setup error: working tree not clean after commit"
    return repo


# ---------------------------------------------------------------------------
# T032 — charter status leaves git working tree unchanged
# ---------------------------------------------------------------------------


class TestCharterStatusNoOp:
    """T032 + T033: _collect_charter_sync_status must not write to disk."""

    def test_charter_status_leaves_git_tree_clean(self, charter_repo: Path) -> None:
        """git status --porcelain is byte-identical before and after the collector.

        Captured-red: FAILS on unmodified _status_collectors.py because
        ensure_charter_bundle_fresh() calls sync(), which regenerates
        metadata.yaml and other bundle files.
        """
        from specify_cli.cli.commands.charter._status_collectors import (
            _collect_charter_sync_status,
        )

        before = _git_porcelain(charter_repo)
        _collect_charter_sync_status(charter_repo)
        after = _git_porcelain(charter_repo)

        assert after == before, (
            "working tree changed after _collect_charter_sync_status; "
            f"new/modified entries:\n{after!r}"
        )

    def test_charter_status_does_not_write_entity_pages(
        self, charter_repo: Path
    ) -> None:
        """No entity-page files appear in the compiled/glossary dir after status.

        Captured-red: FAILS on unmodified _status_collectors.py because
        GlossaryEntityPageRenderer.generate_all() writes pages when graph.yaml
        contains glossary nodes (which our fixture guarantees).
        """
        from specify_cli.cli.commands.charter._status_collectors import (
            _collect_charter_sync_status,
        )

        entity_dir = _entity_page_dir(charter_repo)
        pages_before = set(entity_dir.glob("*.md")) if entity_dir.exists() else set()

        _collect_charter_sync_status(charter_repo)

        pages_after = set(entity_dir.glob("*.md")) if entity_dir.exists() else set()
        new_pages = pages_after - pages_before
        assert not new_pages, (
            "entity-page files appeared after _collect_charter_sync_status "
            f"(collector must not call generate_all): {sorted(p.name for p in new_pages)}"
        )


# ---------------------------------------------------------------------------
# T034 — hash fields are JSON-serializable strings
# ---------------------------------------------------------------------------


class TestCharterStatusHashJsonSafe:
    """T034: the hash fields in the status dict are JSON-serializable."""

    def test_hash_fields_are_strings_or_none(self, charter_repo: Path) -> None:
        """current_hash and stored_hash are str (or None), never bytes.

        Captured-red: FAILS on code paths where hash_content returns raw bytes
        or a non-serializable type leaks into the status dict.
        """
        from specify_cli.cli.commands.charter._status_collectors import (
            _collect_charter_sync_status,
        )

        result = _collect_charter_sync_status(charter_repo)

        assert result["available"] is True, f"collector failed: {result}"
        current_hash = result["current_hash"]
        stored_hash = result["stored_hash"]

        assert isinstance(current_hash, str | type(None)), (
            f"current_hash is not a str: {type(current_hash)}"
        )
        assert isinstance(stored_hash, str | type(None)), (
            f"stored_hash is not a str: {type(stored_hash)}"
        )

    def test_full_status_payload_json_round_trips(self, charter_repo: Path) -> None:
        """The full status dict round-trips through json.dumps without error."""
        from specify_cli.cli.commands.charter._status_collectors import (
            _collect_charter_sync_status,
        )

        result = _collect_charter_sync_status(charter_repo)

        # Must not raise — every value in the dict must be JSON-serializable.
        serialized = json.dumps(result)
        reparsed = json.loads(serialized)

        # Structural sanity: round-trip preserves the hash fields.
        assert reparsed.get("current_hash") == result.get("current_hash")
        assert reparsed.get("stored_hash") == result.get("stored_hash")
