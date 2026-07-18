"""Tests for ``write_compiled_charter``'s charter.yaml partial/merge write.

consolidate-charter-bundle WP03 (T011/T012/T015): the compile pipeline no
longer overwrites ``charter.md`` (data-model.md Landmine 3 -- the #2772
clobber, one level down, on a now-tracked file) or emits
``references.yaml`` (retired). Instead it refreshes ONLY the DERIVED
``catalog``/``metadata`` sections of ``charter.yaml`` through the shared
INV-9 write helper, preserving AUTHORED ``governance``/``directives``/
activation/``overrides`` byte-for-byte via a ruamel round-trip.

Authoritative: ``kitty-specs/consolidate-charter-bundle-01KXSYB9/
data-model.md`` (Landmine 3, INV-9), ``contracts/charter-yaml-schema.md``
(G5).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.compiler import CompiledCharter, compile_charter, write_compiled_charter
from charter.interview import default_interview

pytestmark = pytest.mark.fast


_AUTHORED_FIXTURE = """\
schema_version: "2.0.0"
governance:
  testing:
    min_coverage: 87  # AUTHORED-GOVERNANCE-SENTINEL
  quality: {}
  commits: {}
  performance: {}
  branch_strategy: {}
  doctrine: {}
  activations: []
  enforcement: {}
directives:
  directives:
  - id: DIRECTIVE_001
    title: AUTHORED-DIRECTIVE-SENTINEL
    description: ''
    severity: warn
    references: []
catalog:
  mission: stale-mission
  template_set: stale-template-set
  languages: []
  references: []
activated_kinds:
- directives
activated_directives:
- 001-architectural-integrity-standard  # AUTHORED-ACTIVATION-SENTINEL
overrides:
  some-future-key: authored-override-sentinel
metadata:
  generated_at: '2020-01-01T00:00:00Z'
  bundle_schema_version: 2
"""


def _compiled() -> CompiledCharter:
    interview = default_interview(mission="software-dev", profile="minimal")
    return compile_charter(mission="software-dev", interview=interview)


class TestBootstrapCreate:
    """charter.yaml absent -- a bootstrap create, NOT the Landmine 3 clobber."""

    def test_creates_charter_yaml_not_charter_md(self, tmp_path: Path) -> None:
        compiled = _compiled()

        result = write_compiled_charter(tmp_path, compiled, force=True)

        assert result.files_written == ["charter.yaml"]
        assert (tmp_path / "charter.yaml").exists()
        assert not (tmp_path / "charter.md").exists()
        assert not (tmp_path / "references.yaml").exists()

    def test_bootstrapped_catalog_matches_compiled_references(self, tmp_path: Path) -> None:
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        yaml = YAML()
        document = yaml.load((tmp_path / "charter.yaml").read_text(encoding="utf-8"))
        catalog = document["catalog"]
        assert catalog["mission"] == compiled.mission
        assert catalog["template_set"] == compiled.template_set
        assert len(catalog["references"]) == len(compiled.references)

    def test_bootstrapped_activation_keys_absent_without_config(self, tmp_path: Path) -> None:
        """No repo_root -> no config.yaml to read -> activation stays absent
        (three-state None == default-pack fallback, contract G3)."""
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        yaml = YAML()
        document = yaml.load((tmp_path / "charter.yaml").read_text(encoding="utf-8"))
        assert "activated_directives" not in document

    def test_bootstrapped_governance_and_directives_are_empty_defaults(self, tmp_path: Path) -> None:
        """No repo_root -> no legacy triad to seed from -> empty AUTHORED
        defaults (nothing has been authored yet)."""
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        yaml = YAML()
        document = yaml.load((tmp_path / "charter.yaml").read_text(encoding="utf-8"))
        assert document["directives"]["directives"] == []


class TestPartialMergeRefresh:
    """charter.yaml already exists -- the Landmine 3 regression guard."""

    def _seed(self, tmp_path: Path) -> Path:
        charter_yaml_path = tmp_path / "charter.yaml"
        charter_yaml_path.write_text(_AUTHORED_FIXTURE, encoding="utf-8")
        return charter_yaml_path

    def test_authored_governance_survives_refresh(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        surviving = (tmp_path / "charter.yaml").read_text(encoding="utf-8")
        assert "AUTHORED-GOVERNANCE-SENTINEL" in surviving
        assert "min_coverage: 87" in surviving

    def test_authored_directives_survive_refresh(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        surviving = (tmp_path / "charter.yaml").read_text(encoding="utf-8")
        assert "AUTHORED-DIRECTIVE-SENTINEL" in surviving

    def test_authored_activation_survives_refresh(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        surviving = (tmp_path / "charter.yaml").read_text(encoding="utf-8")
        assert "AUTHORED-ACTIVATION-SENTINEL" in surviving
        assert "001-architectural-integrity-standard" in surviving

    def test_authored_overrides_survive_refresh(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        surviving = (tmp_path / "charter.yaml").read_text(encoding="utf-8")
        assert "authored-override-sentinel" in surviving

    def test_catalog_is_refreshed_from_compiled_state(self, tmp_path: Path) -> None:
        """The DERIVED section is the one thing that IS expected to change."""
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        yaml = YAML()
        document = yaml.load((tmp_path / "charter.yaml").read_text(encoding="utf-8"))
        assert document["catalog"]["mission"] == compiled.mission
        assert document["catalog"]["mission"] != "stale-mission"

    def test_metadata_generated_at_is_refreshed(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        yaml = YAML()
        document = yaml.load((tmp_path / "charter.yaml").read_text(encoding="utf-8"))
        assert document["metadata"]["generated_at"] != "2020-01-01T00:00:00Z"
        assert document["metadata"]["bundle_schema_version"] == 2

    def test_refresh_never_writes_charter_md_or_references_yaml(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=True)

        assert not (tmp_path / "charter.md").exists()
        assert not (tmp_path / "references.yaml").exists()

    def test_survives_refresh_without_force(self, tmp_path: Path) -> None:
        """force no longer gates anything destructive -- a merge refresh is
        always safe, force=False or not."""
        self._seed(tmp_path)
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled, force=False)

        surviving = (tmp_path / "charter.yaml").read_text(encoding="utf-8")
        assert "AUTHORED-GOVERNANCE-SENTINEL" in surviving


class TestConfigPointerMinting:
    """WP02-review gap (T014): bootstrap must ALSO mint config.yaml's
    ``charter:`` pointer, or a project that never runs the WP07 migration
    falls to the config-activation branch permanently (split-brain)."""

    def test_bootstrap_mints_pointer_into_absent_config(self, tmp_path: Path) -> None:
        """No config.yaml at all -> bootstrap creates one containing just
        the pointer (does not depend on ``spec-kitty init`` ordering)."""
        output_dir = tmp_path / ".kittify" / "charter"
        compiled = _compiled()

        write_compiled_charter(output_dir, compiled, repo_root=tmp_path)

        config_path = tmp_path / ".kittify" / "config.yaml"
        assert config_path.exists()
        yaml = YAML()
        config = yaml.load(config_path.read_text(encoding="utf-8"))
        assert config["charter"] == ".kittify/charter/charter.yaml"

    def test_bootstrap_mints_pointer_preserving_other_config_keys(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".kittify" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            "vcs:\n  type: git\n"
            "# a comment that must survive\n"
            "project:\n  slug: my-project\n",
            encoding="utf-8",
        )
        output_dir = tmp_path / ".kittify" / "charter"
        compiled = _compiled()

        write_compiled_charter(output_dir, compiled, repo_root=tmp_path)

        surviving = config_path.read_text(encoding="utf-8")
        assert "# a comment that must survive" in surviving
        assert "slug: my-project" in surviving
        yaml = YAML()
        config = yaml.load(surviving)
        assert config["vcs"]["type"] == "git"
        assert config["charter"] == ".kittify/charter/charter.yaml"

    def test_no_repo_root_does_not_touch_config(self, tmp_path: Path) -> None:
        """No repo_root -> no config.yaml resolution context -> pointer is
        never minted (mirrors the existing 'activation stays absent'
        contract for the no-repo_root bootstrap path)."""
        compiled = _compiled()

        write_compiled_charter(tmp_path, compiled)

        assert not (tmp_path / "config.yaml").exists()
        assert not (tmp_path / ".kittify" / "config.yaml").exists()

    def test_pointer_not_reminted_on_refresh_of_existing_charter_yaml(self, tmp_path: Path) -> None:
        """Once charter.yaml exists, writes are a partial-merge refresh (not
        bootstrap) -- the config.yaml pointer path is not touched again."""
        charter_yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
        charter_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        charter_yaml_path.write_text(_AUTHORED_FIXTURE, encoding="utf-8")
        config_path = tmp_path / ".kittify" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("vcs:\n  type: git\n", encoding="utf-8")
        compiled = _compiled()

        write_compiled_charter(charter_yaml_path.parent, compiled, repo_root=tmp_path)

        surviving = config_path.read_text(encoding="utf-8")
        assert "charter:" not in surviving
