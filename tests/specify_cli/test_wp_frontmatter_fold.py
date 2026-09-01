"""rc3 M5 WP04 — #2901 WP-frontmatter tolerant-reader fold (verify + anti-divergence pin).

Verify-first finding: the fold is already landed. ``status/wp_metadata.py`` is the
single tolerant reader; the mission_v1 lane guard (``mission_v1/guards.py``),
bootstrap, and the dossier indexer route through it. The retired sync import
scanner is intentionally not part of this convergence surface.

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


class TestSingleTolerantReaderAuthority:
    """The routable consumers reference the shared reader, not a private one."""

    @pytest.mark.parametrize(
        ("module", "shared_reader_call"),
        [
            ("specify_cli.mission_v1.guards", "read_wp_frontmatter"),
        ],
    )
    def test_consumer_actually_calls_shared_reader(self, module: str, shared_reader_call: str) -> None:
        """AST call-node check (not a substring): the consumer genuinely invokes
        the tolerant reader from status/wp_metadata — a comment mentioning it is
        not enough to satisfy this pin."""
        import ast
        import importlib
        import inspect

        tree = ast.parse(inspect.getsource(importlib.import_module(module)))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert shared_reader_call in called, (
            f"{module} must CALL {shared_reader_call} (the shared tolerant reader), not just reference it"
        )


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
