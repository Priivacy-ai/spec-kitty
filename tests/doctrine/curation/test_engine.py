"""Tests for doctrine curation engine and state."""

from __future__ import annotations

from pathlib import Path

import pytest
from doctrine.curation.engine import (
    depth_first_order,
    discover_proposed,
    discover_shipped,
    drop_artifact,
    promote_artifact,
    seed_session,
)
from doctrine.curation.state import (
    CurationSession,
    clear_session,
    load_session,
    save_session,
)

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


class TestDiscovery:
    def test_discover_proposed_finds_all(self, doctrine_root: Path) -> None:
        artifacts = discover_proposed(doctrine_root)
        ids = {a.artifact_id for a in artifacts}
        assert "DIRECTIVE_001" in ids
        assert "DIRECTIVE_002" in ids
        assert "test-tactic" in ids
        assert len(artifacts) == 3

    def test_discover_proposed_empty_dirs_return_empty(self, tmp_path: Path) -> None:
        (tmp_path / "directives" / "_proposed").mkdir(parents=True)
        assert discover_proposed(tmp_path) == []

    def test_discover_shipped_initially_empty(self, doctrine_root: Path) -> None:
        assert discover_shipped(doctrine_root) == []

    def test_artifact_title(self, doctrine_root: Path) -> None:
        artifacts = discover_proposed(doctrine_root)
        by_id = {a.artifact_id: a for a in artifacts}
        assert by_id["DIRECTIVE_001"].title == "Test Directive"
        assert by_id["test-tactic"].title == "Test Tactic"

    def test_artifact_summary_fields(self, doctrine_root: Path) -> None:
        artifacts = discover_proposed(doctrine_root)
        directive = next(a for a in artifacts if a.artifact_id == "DIRECTIVE_001")
        fields = directive.summary_fields
        assert "intent" in fields
        assert "enforcement" in fields

        tactic = next(a for a in artifacts if a.artifact_id == "test-tactic")
        assert "steps" in tactic.summary_fields


class TestPromotion:
    def test_promote_moves_to_shipped(self, doctrine_root: Path) -> None:
        artifacts = discover_proposed(doctrine_root)
        directive = next(a for a in artifacts if a.artifact_id == "DIRECTIVE_001")

        dest = promote_artifact(directive, doctrine_root)
        assert dest.exists()
        assert "shipped" in str(dest)
        assert not directive.path.exists()

    def test_promote_preserves_subdirectory(self, doctrine_root: Path) -> None:
        from ruamel.yaml import YAML

        # Create a styleguide in a subdirectory
        subdir = doctrine_root / "styleguides" / "_proposed" / "writing"
        subdir.mkdir(parents=True)
        yaml = YAML()
        yaml.default_flow_style = False
        with (subdir / "test.styleguide.yaml").open("w") as f:
            yaml.dump({"id": "test-sub", "title": "Sub Style"}, f)

        artifacts = discover_proposed(doctrine_root)
        sg = next(a for a in artifacts if a.artifact_id == "test-sub")
        dest = promote_artifact(sg, doctrine_root)

        assert "shipped/writing/test.styleguide.yaml" in str(dest)
        assert dest.exists()

    def test_discover_shipped_after_promote(self, doctrine_root: Path) -> None:
        artifacts = discover_proposed(doctrine_root)
        directive = next(a for a in artifacts if a.artifact_id == "DIRECTIVE_001")
        promote_artifact(directive, doctrine_root)

        shipped = discover_shipped(doctrine_root)
        assert any(a.artifact_id == "DIRECTIVE_001" for a in shipped)

    def test_drop_deletes_file(self, doctrine_root: Path) -> None:
        artifacts = discover_proposed(doctrine_root)
        directive = next(a for a in artifacts if a.artifact_id == "DIRECTIVE_002")
        path = directive.path
        assert path.exists()

        drop_artifact(directive)
        assert not path.exists()


class TestSession:
    def test_seed_session_creates_pending(self, doctrine_root: Path) -> None:
        session = seed_session(doctrine_root)
        assert len(session.decisions) == 3
        assert all(d.verdict == "pending" for d in session.decisions.values())

    def test_seed_session_preserves_existing(self, doctrine_root: Path) -> None:
        session = CurationSession()
        session.record("directives", "DIRECTIVE_001", "001-test.directive.yaml", "accepted")
        session = seed_session(doctrine_root, existing=session)

        d1 = session.get_decision("directives", "DIRECTIVE_001")
        assert d1 is not None
        assert d1.verdict == "accepted"
        assert len(session.decisions) == 3

    def test_progress_percent(self) -> None:
        session = CurationSession()
        session.record("directives", "A", "a.yaml", "pending")
        session.record("directives", "B", "b.yaml", "accepted")
        session.record("directives", "C", "c.yaml", "dropped")
        session.record("directives", "D", "d.yaml", "skipped")
        assert session.progress_percent == 75.0

    def test_progress_percent_empty(self) -> None:
        session = CurationSession()
        assert session.progress_percent == 0.0

    def test_filter_properties(self) -> None:
        session = CurationSession()
        session.record("directives", "A", "a.yaml", "pending")
        session.record("directives", "B", "b.yaml", "accepted")
        session.record("directives", "C", "c.yaml", "dropped")
        session.record("directives", "D", "d.yaml", "skipped")
        assert len(session.pending) == 1
        assert len(session.accepted) == 1
        assert len(session.dropped) == 1
        assert len(session.skipped) == 1


class TestPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        session = CurationSession()
        session.record("directives", "DIRECTIVE_001", "001.yaml", "accepted", "LGTM")
        session.record("tactics", "test-tactic", "test.yaml", "pending")

        save_session(tmp_path, session)
        loaded = load_session(tmp_path)

        assert loaded is not None
        assert len(loaded.decisions) == 2
        d = loaded.get_decision("directives", "DIRECTIVE_001")
        assert d is not None
        assert d.verdict == "accepted"
        assert d.notes == "LGTM"

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        assert load_session(tmp_path) is None

    def test_clear_session(self, tmp_path: Path) -> None:
        session = CurationSession()
        session.record("directives", "A", "a.yaml", "pending")
        save_session(tmp_path, session)
        assert load_session(tmp_path) is not None

        clear_session(tmp_path)
        assert load_session(tmp_path) is None

    def test_clear_nonexistent_noop(self, tmp_path: Path) -> None:
        clear_session(tmp_path)  # Should not raise


class TestDepthFirstOrder:
    def test_directive_then_referenced_tactics(self, tmp_path: Path) -> None:
        """Directive appears before its referenced tactics."""
        from ruamel.yaml import YAML

        yaml = YAML()
        yaml.default_flow_style = False

        # Directive referencing a tactic
        d_dir = tmp_path / "directives" / "_proposed"
        d_dir.mkdir(parents=True)
        with (d_dir / "001-test.directive.yaml").open("w") as f:
            yaml.dump(
                {"id": "DIRECTIVE_001", "title": "D1", "tactic_refs": ["my-tactic"]},
                f,
            )

        # The referenced tactic
        t_dir = tmp_path / "tactics" / "_proposed"
        t_dir.mkdir(parents=True)
        with (t_dir / "my-tactic.tactic.yaml").open("w") as f:
            yaml.dump({"id": "my-tactic", "name": "My Tactic", "steps": []}, f)

        # An unrelated tactic (should come after)
        with (t_dir / "zzz-orphan.tactic.yaml").open("w") as f:
            yaml.dump({"id": "zzz-orphan", "name": "Orphan", "steps": []}, f)

        artifacts = discover_proposed(tmp_path)
        ordered = depth_first_order(artifacts)
        ids = [a.artifact_id for a in ordered]

        assert ids.index("DIRECTIVE_001") < ids.index("my-tactic")
        assert ids.index("my-tactic") < ids.index("zzz-orphan")

    def test_tactic_references_styleguide(self, tmp_path: Path) -> None:
        """Tactic → styleguide chain is depth-first."""
        from ruamel.yaml import YAML

        yaml = YAML()
        yaml.default_flow_style = False

        d_dir = tmp_path / "directives" / "_proposed"
        d_dir.mkdir(parents=True)
        with (d_dir / "001.directive.yaml").open("w") as f:
            yaml.dump({"id": "D1", "title": "D1", "tactic_refs": ["t1"]}, f)

        t_dir = tmp_path / "tactics" / "_proposed"
        t_dir.mkdir(parents=True)
        with (t_dir / "t1.tactic.yaml").open("w") as f:
            yaml.dump(
                {
                    "id": "t1",
                    "name": "T1",
                    "references": [
                        {"name": "S1", "type": "styleguide", "id": "s1", "when": "always"}
                    ],
                },
                f,
            )

        s_dir = tmp_path / "styleguides" / "_proposed"
        s_dir.mkdir(parents=True)
        with (s_dir / "s1.styleguide.yaml").open("w") as f:
            yaml.dump({"id": "s1", "title": "S1", "scope": "code"}, f)

        artifacts = discover_proposed(tmp_path)
        ordered = depth_first_order(artifacts)
        ids = [a.artifact_id for a in ordered]

        assert ids == ["D1", "t1", "s1"]

    def test_orphans_at_end(self, tmp_path: Path) -> None:
        """Unreferenced artifacts appear after all directive trees."""
        from ruamel.yaml import YAML

        yaml = YAML()
        yaml.default_flow_style = False

        d_dir = tmp_path / "directives" / "_proposed"
        d_dir.mkdir(parents=True)
        with (d_dir / "001.directive.yaml").open("w") as f:
            yaml.dump({"id": "D1", "title": "D1"}, f)

        p_dir = tmp_path / "paradigms" / "_proposed"
        p_dir.mkdir(parents=True)
        with (p_dir / "orphan.paradigm.yaml").open("w") as f:
            yaml.dump({"id": "orphan-paradigm", "name": "Orphan"}, f)

        artifacts = discover_proposed(tmp_path)
        ordered = depth_first_order(artifacts)
        ids = [a.artifact_id for a in ordered]

        assert ids.index("D1") < ids.index("orphan-paradigm")
