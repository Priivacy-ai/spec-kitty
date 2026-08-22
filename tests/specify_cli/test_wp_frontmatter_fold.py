"""rc3 M5 WP04 — #2901 WP-frontmatter tolerant-reader fold (verify + anti-divergence pin).

Verify-first finding: the fold is already landed. ``status/wp_metadata.py`` is the
single tolerant reader; the import scan (``sync/history_import/scan.py``), the
mission_v1 lane guard (``mission_v1/guards.py``), bootstrap, and the dossier
indexer all route through it. The #2884 B3 defect ("incomplete import reported as
success") is closed — a malformed WP file is skipped BUT surfaced in the scan's
``skipped`` tuple, never silently counted as success.

``audit/classifiers/wp_files.py`` legitimately does NOT route through the typed
tolerant reader: it is a CLASSIFIER that needs the raw frontmatter dict to detect
legacy/unknown keys (the typed reader drops unknown keys, which would destroy its
finding taxonomy). ``review/prompt_metadata.py`` reads review-prompt frontmatter,
not WP frontmatter — out of scope.

These pins lock the landed state so a future refactor cannot re-introduce a
divergent reader or a silent-success import.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

_GOOD_WP = """---
work_package_id: "WP01"
title: "Good WP"
subtasks: ["T001"]
---

Body.
"""

# Has a `---` fence but the YAML block is malformed (a bare scalar/garbage),
# so the tolerant reader raises and the scan must SKIP-AND-SURFACE it.
_MALFORMED_WP = """---
: : : not : valid : yaml : {[}
work_package_id
---

Body.
"""


def _make_mission(tmp_path: Path, files: dict[str, str]) -> Path:
    tasks = tmp_path / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (tasks / name).write_text(content, encoding="utf-8")
    return tmp_path


class TestImportScanB3DefectClosed:
    """#2884 B3: a malformed WP is skipped AND surfaced — never silent success."""

    def test_malformed_wp_is_surfaced_in_skipped(self, tmp_path: Path) -> None:
        from specify_cli.sync.history_import.scan import _wps_from_task_files

        mission = _make_mission(
            tmp_path,
            {"WP01-good.md": _GOOD_WP, "WP02-bad.md": _MALFORMED_WP},
        )
        wps, skipped = _wps_from_task_files(mission)

        wp_ids = {wp.wp_id for wp in wps}
        assert "WP01" in wp_ids, "the valid WP must still import"
        assert "WP02-bad.md" in skipped, "the malformed WP must be surfaced, not silently dropped"


class TestSingleTolerantReaderAuthority:
    """The routable consumers reference the shared reader, not a private one."""

    @pytest.mark.parametrize(
        ("module", "symbol"),
        [
            ("specify_cli.sync.history_import.scan", "read_authored_wp_frontmatter_lenient"),
            ("specify_cli.mission_v1.guards", "_read_lane_from_frontmatter"),
        ],
    )
    def test_consumer_uses_shared_reader(self, module: str, symbol: str) -> None:
        import importlib
        import inspect

        mod = importlib.import_module(module)
        source = inspect.getsource(mod)
        # Each routes WP-frontmatter reads through status/wp_metadata's tolerant
        # readers (directly, or via the specify_cli.status re-export).
        assert "read_wp_frontmatter" in source or "read_authored_wp_frontmatter" in source


class TestAuditClassifierKeepsRawDict:
    """wp_files.py is a raw-dict classifier — legacy/unknown key detection intact."""

    def test_legacy_key_is_detected(self, tmp_path: Path) -> None:
        from specify_cli.audit.classifiers.wp_files import classify_wp_files

        # A legacy `feature_slug:` frontmatter key must still produce a finding —
        # proof the classifier reads the RAW dict (a typed reader would have
        # dropped the unknown key before the classifier ever saw it).
        mission = _make_mission(
            tmp_path,
            {"WP01.md": '---\nwork_package_id: "WP01"\ntitle: "t"\nfeature_slug: "x"\n---\n\nBody.\n'},
        )
        findings = classify_wp_files(mission)
        assert any("feature_slug" in (f.detail or "") for f in findings), (
            f"classifier must detect the legacy key from the raw dict; got {[f.detail for f in findings]}"
        )
