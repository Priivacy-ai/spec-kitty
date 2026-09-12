"""Tests for `charter pack apply --compile` + truthful output (WP02).

Covers mission `charter-pack-usage-journey-01KYWWTF` FR-003/FR-004/FR-008:

- T010: default `apply` (no `--compile`) names the exact next command
  (`spec-kitty charter generate`) instead of a vague "a compile may still
  be needed" -- and stays a pure, git-agnostic additive merge (C-004: no
  `charter.yaml` is produced).
- T011: `apply --compile` chains the EXISTING compile seam
  (`compile_charter` + `write_compiled_charter`, the same functions
  `charter generate --no-from-interview` calls) after the config merge.
  It inherits `generate`'s git-worktree requirement and fails closed,
  naming that requirement, outside one.
- T014 (IC-05/FR-008): `apply --compile` and the upgrade finalize
  migration's full-document producer (`_compose_charter_yaml_document`)
  transform the SAME config-activation input into a CONVERGENT
  `charter.yaml` -- same top-level catalog SHAPE, and the SAME
  activation subset copied verbatim -- without being byte-identical
  (see the module docstring on `test_apply_compile_converges_with_...`
  below for why byte-identity is the wrong bar).
- Squad fold B (landing PR #3146): `_compile_bundle_after_merge` used to
  hardcode `profile="minimal"` when resolving the interview it feeds
  `compile_charter`, regardless of which pack `apply` was given. The
  `minimal.yaml` pack's own docstring says it exists so a project can get a
  "sane governance baseline WITHOUT running the full charter interview" --
  i.e. the pack name <-> interview-profile pairing is a deliberate design
  correspondence, not a coincidence -- so `apply default --compile` silently
  reusing minimal's filtered interview was a real bug. The fix threads the
  applied pack `name` straight into `profile=`;
  `charter.activation.interview.default_interview`'s only live branch is `"minimal"`
  vs "everything else", so today's two built-in packs (`default`/`minimal`)
  map onto it exactly. See `test_apply_compile_derives_interview_profile_*`
  below for the regression pin.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from charter.activation.charter_yaml_io import load_charter_yaml
from charter.activation.interview import MINIMAL_QUESTION_ORDER, QUESTION_ORDER, CharterInterview
from specify_cli.cli.commands.charter import charter_app
from specify_cli.upgrade.migrations.m_unify_charter_activation_finalize import (
    ACTIVATION_KEYS,
    _compose_charter_yaml_document,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()


def _apply(project_root: Path, name: str, *extra: str) -> object:
    return runner.invoke(
        charter_app,
        ["pack", "apply", name, "--repo-root", str(project_root), *extra],
        catch_exceptions=False,
    )


def _git_init(repo_root: Path) -> None:
    """Minimal git init -- `_is_inside_git_worktree` only needs a worktree,
    no identity/config, since the compile bridge never commits or stages."""
    subprocess.run(
        ["git", "init", "--quiet"], cwd=repo_root, check=True, capture_output=True
    )


def _load_yaml(path: Path) -> dict[str, object]:
    yaml = YAML(typ="safe")
    loaded = yaml.load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


# ---------------------------------------------------------------------------
# T010 -- truthful default `apply` output (FR-004)
# ---------------------------------------------------------------------------


def test_default_apply_output_names_generate_as_the_exact_next_command(
    tmp_path: Path,
) -> None:
    """No `--compile`: output must name `spec-kitty charter generate` -- not
    a vague "a compile may still be needed" -- and must NOT compile."""
    result = _apply(tmp_path, "minimal")

    assert result.exit_code == 0, result.output
    # rich's `console.print` reflows long lines to the terminal width, so a
    # phrase spanning a wrap point (e.g. "...spec-kitty \ncharter generate")
    # would fail a raw substring check -- normalize whitespace first.
    normalized = " ".join(result.output.split())
    assert "spec-kitty charter generate" in normalized
    assert "may still be needed" not in normalized
    assert not (tmp_path / ".kittify" / "charter" / "charter.yaml").exists()


def test_default_apply_json_reports_not_compiled(tmp_path: Path) -> None:
    result = _apply(tmp_path, "minimal", "--json")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["compiled"] is False
    assert payload["compiled_files"] == []


def test_default_apply_stays_git_agnostic_even_without_a_git_repo(
    tmp_path: Path,
) -> None:
    """C-004: default `apply` (no `--compile`) must succeed with no `.git`
    at all -- only `--compile` inherits the git-worktree requirement."""
    result = _apply(tmp_path, "minimal")

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".kittify" / "config.yaml").is_file()


# ---------------------------------------------------------------------------
# T011 -- `apply --compile` chains the EXISTING seam (FR-003)
# ---------------------------------------------------------------------------


def test_apply_compile_reports_compiled_and_leaves_charter_yaml_present(
    tmp_path: Path,
) -> None:
    _git_init(tmp_path)

    result = _apply(tmp_path, "minimal", "--compile")

    assert result.exit_code == 0, result.output
    assert "compiled" in result.output.lower()
    charter_yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    assert charter_yaml_path.is_file()


def test_apply_compile_json_reports_compiled_files(tmp_path: Path) -> None:
    _git_init(tmp_path)

    result = _apply(tmp_path, "minimal", "--compile", "--json")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["compiled"] is True
    assert "charter.yaml" in payload["compiled_files"]


def test_apply_compile_without_git_fails_closed_naming_the_requirement(
    tmp_path: Path,
) -> None:
    """`--compile` inherits `charter generate`'s git-worktree requirement --
    the config merge still runs (compile is chained AFTER it), but no
    `charter.yaml` is produced and the error names the git requirement."""
    result = _apply(tmp_path, "minimal", "--compile")

    assert result.exit_code == 1
    lowered = result.output.lower()
    assert "git" in lowered
    assert (tmp_path / ".kittify" / "config.yaml").is_file(), (
        "the config merge must still have run before the compile step failed"
    )
    assert not (tmp_path / ".kittify" / "charter" / "charter.yaml").exists()


def test_apply_compile_without_git_json_fails_closed(tmp_path: Path) -> None:
    result = _apply(tmp_path, "minimal", "--compile", "--json")

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "git" in payload["error"].lower()


# ---------------------------------------------------------------------------
# T014 -- IC-05 / FR-008 convergence with the finalize migration's producer
# ---------------------------------------------------------------------------


def test_apply_compile_converges_with_finalize_migration_producer(
    tmp_path: Path,
) -> None:
    """`apply --compile` and the upgrade finalize migration's full-document
    producer (`_compose_charter_yaml_document`, used by
    `ConsolidateCharterBundleMigration` -- the "fourth producer" the mission
    edge cases call out) must NOT be allowed to independently diverge on how
    a project's `config.yaml` activation is transformed into `charter.yaml`.

    They are NOT asserted byte-identical: the migration composes
    `governance`/`directives`/`catalog` by reading the retired legacy
    triad (`governance.yaml`/`directives.yaml`/`references.yaml`) -- absent
    here, so it falls back to empty schema defaults -- while
    `write_compiled_charter`'s bootstrap path (the seam `apply --compile`
    chains) derives `governance`/`directives` from
    `charter.activation.sync.load_governance_config`/`load_directives_config` and
    resolves `catalog.references` from the live doctrine catalog. Those are
    two legitimately different provenance paths for the SAME sections
    (compiler.py's `_bootstrap_charter_yaml` docstring), so per FR-008's
    "document-as-equivalent" instruction this test pins the SHARED contract
    instead: (a) both producers emit a document whose top level carries
    `governance`/`directives`/`catalog`/`metadata`, and (b) both copy the
    SAME config-activation input onto that document VERBATIM under the
    SAME flat `activated_*` keys -- the one-authority transform FR-008
    actually cares about.
    """
    _git_init(tmp_path)
    result = _apply(tmp_path, "minimal", "--compile")
    assert result.exit_code == 0, result.output

    charter_yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    produced = load_charter_yaml(charter_yaml_path)
    config_data = _load_yaml(tmp_path / ".kittify" / "config.yaml")

    activation_present = [key for key in ACTIVATION_KEYS if key in config_data]
    assert activation_present, "the minimal pack must have written activation keys"

    # Producer B: the finalize migration's full-document producer, fed the
    # EXACT SAME activation input. `_compose_charter_yaml_document` only
    # reads legacy bundle files under `<project_path>/.kittify/charter/` --
    # none exist under this unrelated, uncreated path, so it degrades to
    # empty governance/directives/catalog defaults (mirroring a pre-M2
    # project that never ran `charter generate`), then copies the passed
    # `config_data` activation verbatim -- exactly what this test compares.
    other_project = tmp_path.parent / "migration-producer-input"
    migration_document = _compose_charter_yaml_document(other_project, config_data)

    for section in ("governance", "directives", "catalog", "metadata"):
        assert section in produced, f"apply --compile document missing {section!r}"
        assert section in migration_document, (
            f"finalize migration document missing {section!r}"
        )

    for key in activation_present:
        assert produced.get(key) == config_data[key], (
            f"apply --compile did not copy activation key {key!r} verbatim"
        )
        assert migration_document.get(key) == config_data[key], (
            f"finalize migration did not copy activation key {key!r} verbatim"
        )
        assert produced.get(key) == migration_document.get(key), (
            f"activation key {key!r} diverged between the two producers "
            "for the SAME config-activation input -- the config->bundle "
            "transform is no longer one authority (FR-008)"
        )


# ---------------------------------------------------------------------------
# Squad fold B -- interview profile derives from the applied pack name
# (regression pin for the `profile="minimal"` hardcode)
# ---------------------------------------------------------------------------
#
# `write_compiled_charter` only refreshes `charter.yaml`'s DERIVED `catalog`/
# `metadata` sections (see its own docstring); the `CharterInterview` fed
# into `compile_charter` never lands verbatim in the written bundle (its
# `USER:PROJECT_PROFILE` reference `content` -- where `interview.profile`
# and the per-profile answer set actually appear -- is stripped down to
# static id/kind/title/summary/path fields by `_build_catalog_dict`). So the
# faithful regression pin is at the `compile_charter` call boundary itself:
# assert the `CharterInterview` `_compile_bundle_after_merge` builds and
# passes in actually carries the applied pack's own name as its `profile`,
# not a hardcoded `"minimal"`.


def _capture_compiled_interview(project_root: Path, name: str) -> tuple[object, CharterInterview]:
    """Run `apply <name> --compile` and capture the interview passed to
    `compile_charter` (the real function still runs; the wrapper only spies)."""
    from charter.activation.compiler import compile_charter as _real_compile_charter

    captured: dict[str, CharterInterview] = {}

    def _spy(*, interview: CharterInterview, **kwargs: Any) -> Any:
        captured["interview"] = interview
        return _real_compile_charter(interview=interview, **kwargs)

    with patch("charter.activation.compiler.compile_charter", side_effect=_spy):
        result = _apply(project_root, name, "--compile")

    assert result.exit_code == 0, result.output  # type: ignore[attr-defined]
    assert "interview" in captured, "compile_charter was never invoked"
    return result, captured["interview"]


def test_apply_default_compile_derives_interview_profile_from_pack_name(
    tmp_path: Path,
) -> None:
    """`apply default --compile` must build the interview with
    `profile="default"` (full 11-question set) -- NOT a hardcoded
    `"minimal"` (the pre-fix behavior, which silently reused minimal's
    filtered 7-question defaults for every pack)."""
    _git_init(tmp_path)

    _result, interview = _capture_compiled_interview(tmp_path, "default")

    assert interview.profile == "default"
    assert set(interview.answers) == set(QUESTION_ORDER)
    assert set(interview.answers) != set(MINIMAL_QUESTION_ORDER)


def test_apply_minimal_compile_still_uses_the_filtered_interview(
    tmp_path: Path,
) -> None:
    """Sibling pin: `apply minimal --compile` keeps its pre-fix behavior --
    only `default` (and any other non-`"minimal"` pack) was wrong."""
    _git_init(tmp_path)

    _result, interview = _capture_compiled_interview(tmp_path, "minimal")

    assert interview.profile == "minimal"
    assert set(interview.answers) == set(MINIMAL_QUESTION_ORDER)
