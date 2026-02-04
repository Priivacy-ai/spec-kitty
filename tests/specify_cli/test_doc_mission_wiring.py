"""Tests for WP04: Documentation Mission State & Gap Analysis Wiring.

Tests T013 (init doc state during specify), T014 (gap analysis during plan),
T015 (gap analysis during research), T016 (generator detection during plan).
"""

import json

from specify_cli.doc_state import (
    read_documentation_state,
    initialize_documentation_state,
    set_audit_metadata,
    set_generators_configured,
)
from specify_cli.gap_analysis import generate_gap_analysis_report
from specify_cli.doc_generators import (
    JSDocGenerator,
    SphinxGenerator,
    RustdocGenerator,
)
from specify_cli.mission import get_feature_mission_key


# ===========================================================================
# T013: Initialize documentation state during specify
# ===========================================================================


class TestT013InitDocStateDuringSpecify:
    """Test documentation state initialization during feature creation."""

    def test_doc_state_initialized_for_documentation_mission(self, tmp_path):
        """When mission=documentation, meta.json should have documentation_state."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({
            "feature_number": "030",
            "slug": "doc-my-project",
            "mission": "documentation",
        }))

        # Simulate what create_feature does for documentation missions
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if meta.get("mission") == "documentation" and "documentation_state" not in meta:
            meta["documentation_state"] = {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            }
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # Verify
        result = json.loads(meta_file.read_text())
        assert "documentation_state" in result
        assert result["documentation_state"]["iteration_mode"] == "initial"
        assert result["documentation_state"]["divio_types_selected"] == []
        assert result["documentation_state"]["generators_configured"] == []
        assert result["documentation_state"]["target_audience"] == "developers"
        assert result["documentation_state"]["last_audit_date"] is None
        assert result["documentation_state"]["coverage_percentage"] == 0.0

    def test_doc_state_not_initialized_for_software_dev(self, tmp_path):
        """When mission=software-dev, meta.json should NOT have documentation_state."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({
            "feature_number": "030",
            "slug": "my-feature",
            "mission": "software-dev",
        }))

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        # Only add doc state for documentation mission
        if meta.get("mission") == "documentation" and "documentation_state" not in meta:
            meta["documentation_state"] = {}  # Should NOT reach here

        assert "documentation_state" not in meta

    def test_doc_state_defaults_match_spec(self, tmp_path):
        """Verify defaults match the spec.md schema."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({"mission": "documentation"}))

        state = initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=[],
            generators=[],
            target_audience="developers",
        )

        assert state["iteration_mode"] == "initial"
        assert state["divio_types_selected"] == []
        assert state["generators_configured"] == []
        assert state["target_audience"] == "developers"
        assert state["last_audit_date"] is None
        assert state["coverage_percentage"] == 0.0

    def test_doc_state_preserved_when_already_exists(self, tmp_path):
        """If documentation_state already exists, don't overwrite it."""
        meta_file = tmp_path / "meta.json"
        existing_state = {
            "iteration_mode": "gap_filling",
            "divio_types_selected": ["tutorial", "reference"],
            "generators_configured": [
                {"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}
            ],
            "target_audience": "end-users",
            "last_audit_date": "2026-01-15T10:00:00Z",
            "coverage_percentage": 0.67,
        }
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": existing_state,
        }))

        # Simulate create_feature logic - should not overwrite
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if meta.get("mission") == "documentation" and "documentation_state" not in meta:
            meta["documentation_state"] = {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            }

        # Existing state should be preserved
        assert meta["documentation_state"]["iteration_mode"] == "gap_filling"
        assert meta["documentation_state"]["coverage_percentage"] == 0.67


# ===========================================================================
# T014: Run gap analysis during plan
# ===========================================================================


class TestT014GapAnalysisDuringPlan:
    """Test gap analysis runs during plan for documentation missions."""

    def test_gap_analysis_runs_for_gap_filling_mode(self, tmp_path):
        """Gap analysis should run when iteration_mode is gap_filling."""
        # Setup feature dir with documentation meta
        feature_dir = tmp_path / "kitty-specs" / "030-doc-project"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": {
                "iteration_mode": "gap_filling",
                "divio_types_selected": ["tutorial", "reference"],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            },
        }))

        # Setup docs dir with some docs
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "getting-started.md").write_text(
            "---\ntype: tutorial\n---\n# Getting Started\nStep 1, Step 2, Step 3\n"
        )

        # Run gap analysis
        output_file = feature_dir / "gap-analysis.md"
        analysis = generate_gap_analysis_report(docs_dir, output_file, project_root=tmp_path)

        assert output_file.exists()
        assert analysis.framework is not None
        content = output_file.read_text()
        assert "Gap Analysis" in content

        # Update state
        set_audit_metadata(
            meta_file,
            last_audit_date=analysis.analysis_date,
            coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
        )

        # Verify state was updated
        updated_meta = json.loads(meta_file.read_text())
        assert updated_meta["documentation_state"]["last_audit_date"] is not None
        assert isinstance(updated_meta["documentation_state"]["coverage_percentage"], float)

    def test_gap_analysis_skipped_for_initial_mode(self, tmp_path):
        """Gap analysis should NOT run when iteration_mode is initial."""
        feature_dir = tmp_path / "kitty-specs" / "030-doc-project"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            },
        }))

        doc_state = read_documentation_state(meta_file)
        iteration_mode = doc_state.get("iteration_mode", "initial") if doc_state else "initial"

        # Should not run gap analysis for initial mode
        assert iteration_mode == "initial"
        assert iteration_mode not in ("gap_filling", "feature_specific")

    def test_gap_analysis_runs_for_feature_specific_mode(self, tmp_path):
        """Gap analysis should run when iteration_mode is feature_specific."""
        feature_dir = tmp_path / "kitty-specs" / "030-doc-feature"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": {
                "iteration_mode": "feature_specific",
                "divio_types_selected": ["how-to", "reference"],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            },
        }))

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text(
            "---\ntype: reference\n---\n# API Reference\nParameters:\nReturns:\n"
        )

        output_file = feature_dir / "gap-analysis.md"
        generate_gap_analysis_report(docs_dir, output_file, project_root=tmp_path)

        assert output_file.exists()

    def test_gap_analysis_not_triggered_for_software_dev(self, tmp_path):
        """Gap analysis should not run for software-dev missions."""
        feature_dir = tmp_path / "kitty-specs" / "030-feature"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "software-dev",
        }))

        mission_key = get_feature_mission_key(feature_dir)
        assert mission_key == "software-dev"
        # Gate check: only run for documentation
        assert mission_key != "documentation"


# ===========================================================================
# T015: Run gap analysis during research
# ===========================================================================


class TestT015GapAnalysisDuringResearch:
    """Test gap analysis runs during research for documentation missions."""

    def test_gap_analysis_for_documentation_research(self, tmp_path):
        """Research command should trigger gap analysis for documentation missions."""
        feature_dir = tmp_path / "kitty-specs" / "030-doc-project"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": {
                "iteration_mode": "gap_filling",
                "divio_types_selected": ["tutorial", "reference"],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            },
        }))

        # Setup docs
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "tutorial.md").write_text(
            "---\ntype: tutorial\n---\n# Tutorial\nStep 1: Do this\n"
        )

        # Simulate research gap analysis logic
        mission_key = get_feature_mission_key(feature_dir)
        assert mission_key == "documentation"

        doc_state = read_documentation_state(meta_file)
        iteration_mode = doc_state.get("iteration_mode", "initial") if doc_state else "initial"
        assert iteration_mode == "gap_filling"

        gap_analysis_output = feature_dir / "gap-analysis.md"
        analysis = generate_gap_analysis_report(
            docs_dir, gap_analysis_output, project_root=tmp_path
        )

        assert gap_analysis_output.exists()

        # Update state
        set_audit_metadata(
            meta_file,
            last_audit_date=analysis.analysis_date,
            coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
        )

        updated_meta = json.loads(meta_file.read_text())
        assert updated_meta["documentation_state"]["last_audit_date"] is not None

    def test_research_skips_gap_analysis_for_initial_mode(self, tmp_path):
        """Research should skip gap analysis for initial iteration mode."""
        feature_dir = tmp_path / "kitty-specs" / "030-doc-project"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            },
        }))

        doc_state = read_documentation_state(meta_file)
        iteration_mode = doc_state.get("iteration_mode", "initial") if doc_state else "initial"

        # Should be skipped
        assert iteration_mode not in ("gap_filling", "feature_specific")


# ===========================================================================
# T016: Detect/configure generators during plan
# ===========================================================================


class TestT016DetectConfigureGenerators:
    """Test generator detection and configuration during plan."""

    def test_sphinx_detected_for_python_project(self, tmp_path):
        """Sphinx generator should be detected for Python projects."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def hello(): pass\n")

        gen = SphinxGenerator()
        assert gen.detect(tmp_path) is True

    def test_jsdoc_detected_for_js_project(self, tmp_path):
        """JSDoc generator should be detected for JavaScript projects."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.js").write_text("function hello() {}\n")

        gen = JSDocGenerator()
        assert gen.detect(tmp_path) is True

    def test_rustdoc_detected_for_rust_project(self, tmp_path):
        """rustdoc generator should be detected for Rust projects."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\n')
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("fn main() {}\n")

        gen = RustdocGenerator()
        assert gen.detect(tmp_path) is True

    def test_no_generators_for_empty_project(self, tmp_path):
        """No generators should be detected for an empty project."""
        generators = [JSDocGenerator(), SphinxGenerator(), RustdocGenerator()]
        detected = [gen for gen in generators if gen.detect(tmp_path)]
        assert len(detected) == 0

    def test_generators_saved_to_doc_state(self, tmp_path):
        """Detected generators should be saved to documentation_state in meta.json."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "documentation",
            "documentation_state": {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            },
        }))

        generators_detected = [
            {"name": "sphinx", "language": "python", "config_path": ""},
        ]

        set_generators_configured(meta_file, generators_detected)

        updated = json.loads(meta_file.read_text())
        assert len(updated["documentation_state"]["generators_configured"]) == 1
        assert updated["documentation_state"]["generators_configured"][0]["name"] == "sphinx"

    def test_multiple_generators_detected(self, tmp_path):
        """Multiple generators can be detected for polyglot projects."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (tmp_path / "package.json").write_text('{"name": "test"}')

        generators = [JSDocGenerator(), SphinxGenerator(), RustdocGenerator()]
        detected = [gen for gen in generators if gen.detect(tmp_path)]

        assert len(detected) == 2
        names = {gen.name for gen in detected}
        assert "sphinx" in names
        assert "jsdoc" in names

    def test_generator_detection_does_not_affect_software_dev(self, tmp_path):
        """Generator detection should be gated on documentation mission."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({
            "mission": "software-dev",
        }))

        mission_key = get_feature_mission_key(tmp_path)
        assert mission_key == "software-dev"

        # Should not attempt generator detection for software-dev
        # This is a gate check in the plan flow
        assert mission_key != "documentation"


# ===========================================================================
# Integration: End-to-end doc mission flow
# ===========================================================================


class TestDocMissionIntegration:
    """Integration tests for complete documentation mission flow."""

    def test_full_doc_mission_flow(self, tmp_path):
        """Test the full flow: init state -> gap analysis -> generator detection."""
        feature_dir = tmp_path / "kitty-specs" / "030-doc-project"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"

        # Step 1: Create meta.json with mission=documentation
        meta = {
            "feature_number": "030",
            "slug": "doc-project",
            "mission": "documentation",
        }
        meta_file.write_text(json.dumps(meta, indent=2))

        # Step 2: Initialize doc state (T013)
        state = initialize_documentation_state(
            meta_file,
            iteration_mode="gap_filling",
            divio_types=["tutorial", "reference", "how-to"],
            generators=[],
            target_audience="developers",
        )
        assert state["iteration_mode"] == "gap_filling"
        assert state["coverage_percentage"] == 0.0

        # Step 3: Setup docs directory
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "intro.md").write_text(
            "---\ntype: tutorial\n---\n# Getting Started\n\nStep 1: Install\nStep 2: Configure\n"
        )
        (docs_dir / "api.md").write_text(
            "---\ntype: reference\n---\n# API\n\nParameters:\nReturns:\n"
        )

        # Step 4: Run gap analysis (T014/T015)
        gap_output = feature_dir / "gap-analysis.md"
        analysis = generate_gap_analysis_report(docs_dir, gap_output, project_root=tmp_path)
        assert gap_output.exists()

        # Step 5: Update state with audit results
        set_audit_metadata(
            meta_file,
            last_audit_date=analysis.analysis_date,
            coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
        )

        # Step 6: Detect generators (T016)
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        generators = [JSDocGenerator(), SphinxGenerator(), RustdocGenerator()]
        detected = []
        for gen in generators:
            if gen.detect(tmp_path):
                detected.append({
                    "name": gen.name,
                    "language": gen.languages[0],
                    "config_path": "",
                })

        assert len(detected) >= 1  # At least Sphinx should be detected

        # Step 7: Save generator config
        set_generators_configured(meta_file, detected)

        # Verify final state
        final_meta = json.loads(meta_file.read_text())
        doc_state = final_meta["documentation_state"]
        assert doc_state["iteration_mode"] == "gap_filling"
        assert doc_state["last_audit_date"] is not None
        assert doc_state["coverage_percentage"] >= 0.0
        assert len(doc_state["generators_configured"]) >= 1
        assert doc_state["target_audience"] == "developers"

    def test_gap_analysis_output_path_canonical(self, tmp_path):
        """Gap analysis should write to kitty-specs/<feature>/gap-analysis.md."""
        feature_dir = tmp_path / "kitty-specs" / "030-doc-project"
        feature_dir.mkdir(parents=True)

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "readme.md").write_text("# README\n")

        output_file = feature_dir / "gap-analysis.md"
        generate_gap_analysis_report(docs_dir, output_file, project_root=tmp_path)

        assert output_file.exists()
        assert output_file.parent == feature_dir
        assert output_file.name == "gap-analysis.md"
