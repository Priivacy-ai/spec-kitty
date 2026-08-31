"""Tests for `spec-kitty charter pack {list,path,apply}` (#3064 follow-up).

`src/charter/offering/assets/built-in/charter_scaffold_minimal.yml` (+ sidecar) was a
doctrine *asset* despite being structurally a charter pack — the same shape
as `src/charter/packs/default.yaml` (`activated_kinds` /
`mission_type_activations` / `activated_directives` / `activated_tactics`).
It has been relocated to `src/charter/packs/minimal.yaml`, first-class
alongside `default.yaml`, and is now discoverable/applyable via an on-demand
pack CLI instead of `doctrine asset path`.

Covers:
- `pack list` — enumerates the shipped built-in packs (`default`, `minimal`).
- `pack path <name>` — resolves a built-in pack name to its shipped file;
  fails closed (exit 1) on an unknown name.
- `pack apply <name>` — merges a pack's activation keys into a project's
  `.kittify/config.yaml`; additive by default (User Customization
  Preservation — an existing key is never silently overwritten), full
  replacement of the pack's keys with `--force`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from charter.catalog import load_doctrine_catalog
from charter.pack_context import charter_activated_urns
from specify_cli.cli.commands.charter import charter_app
from specify_cli.invocation.empty_charter import is_charter_empty

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

_REPO_ROOT = Path(__file__).resolve().parents[5]
_PACKS_DIR = _REPO_ROOT / "src" / "charter" / "packs"
_MINIMAL_PATH = _PACKS_DIR / "minimal.yaml"
_DEFAULT_PATH = _PACKS_DIR / "default.yaml"


def _load_yaml(path: Path) -> dict[str, object]:
    yaml = YAML(typ="safe")
    loaded = yaml.load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


# ---------------------------------------------------------------------------
# `pack list`
# ---------------------------------------------------------------------------


def test_list_shows_default_and_minimal() -> None:
    result = runner.invoke(charter_app, ["pack", "list"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "default" in result.output
    assert "minimal" in result.output


def test_list_json_shows_default_and_minimal_with_paths() -> None:
    result = runner.invoke(charter_app, ["pack", "list", "--json"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    names = {pack["name"] for pack in payload["packs"]}
    assert names == {"default", "minimal"}
    paths = {pack["name"]: Path(pack["path"]) for pack in payload["packs"]}
    assert paths["minimal"] == _MINIMAL_PATH
    assert paths["default"] == _DEFAULT_PATH


# ---------------------------------------------------------------------------
# `pack path <name>`
# ---------------------------------------------------------------------------


def test_path_minimal_resolves_to_the_shipped_file() -> None:
    result = runner.invoke(charter_app, ["pack", "path", "minimal"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    resolved = Path(result.output.strip())
    assert resolved == _MINIMAL_PATH
    assert resolved.is_file()


def test_path_json_minimal() -> None:
    result = runner.invoke(
        charter_app, ["pack", "path", "minimal", "--json"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["name"] == "minimal"
    assert Path(payload["path"]) == _MINIMAL_PATH


def test_path_unknown_name_fails_closed() -> None:
    result = runner.invoke(
        charter_app, ["pack", "path", "no-such-pack"], catch_exceptions=False
    )

    assert result.exit_code == 1
    assert "no-such-pack" in result.output


def test_path_unknown_name_json_fails_closed() -> None:
    result = runner.invoke(
        charter_app, ["pack", "path", "no-such-pack", "--json"], catch_exceptions=False
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "no-such-pack" in payload["error"]


# ---------------------------------------------------------------------------
# `pack apply <name>` — happy path, activatability
# ---------------------------------------------------------------------------


def _apply(project_root: Path, name: str, *extra: str) -> object:
    return runner.invoke(
        charter_app,
        ["pack", "apply", name, "--repo-root", str(project_root), *extra],
        catch_exceptions=False,
    )


def test_apply_minimal_writes_curated_keys_into_config_yaml(tmp_path: Path) -> None:
    result = _apply(tmp_path, "minimal")

    assert result.exit_code == 0, result.output
    config_path = tmp_path / ".kittify" / "config.yaml"
    assert config_path.is_file()

    written = _load_yaml(config_path)
    expected = _load_yaml(_MINIMAL_PATH)
    assert written["activated_kinds"] == expected["activated_kinds"]
    assert written["mission_type_activations"] == expected["mission_type_activations"]
    assert written["activated_directives"] == expected["activated_directives"]
    assert written["activated_tactics"] == expected["activated_tactics"]


def test_apply_minimal_json_reports_keys_written(tmp_path: Path) -> None:
    result = _apply(tmp_path, "minimal", "--json")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["pack"] == "minimal"
    assert "activated_directives" in payload["keys_written"]
    assert "activated_tactics" in payload["keys_written"]
    assert payload["keys_skipped"] == []


def test_apply_unknown_pack_fails_closed(tmp_path: Path) -> None:
    result = _apply(tmp_path, "no-such-pack")

    assert result.exit_code == 1


def test_applied_minimal_activates_urns_but_stays_empty_for_dispatch_until_compiled(
    tmp_path: Path,
) -> None:
    """Real done-line: applying the pack activates URNs (config-level effect),
    but does NOT compile a bundle — so ``is_charter_empty`` correctly still
    reports "empty" (no ``.kittify/charter/charter.yaml``) until
    ``charter generate`` runs.

    NOTE (NFR-004/#3104): pre-fix, this test asserted
    ``is_charter_empty(tmp_path) is False`` right after ``apply`` with no
    compile — that encoded the #3104 defect (``charter pack apply`` writing
    activation keys with no bundle and no profile activation used to flip the
    dispatch net off, producing a bare ``ROUTER_NO_MATCH`` for an unmatched
    request instead of the safe generic-agent fallback). The bundle-presence +
    org-pack-safe predicate in ``specify_cli.invocation.empty_charter``
    decouples "activatable" (config carries activation keys — still true and
    asserted below) from "empty-for-dispatch" (compiled bundle absent — now
    correctly ``True`` here).
    """
    result = _apply(tmp_path, "minimal")
    assert result.exit_code == 0, result.output

    # Applying activates URNs at the config level -- unchanged.
    urns = charter_activated_urns(tmp_path)
    assert urns, "applying minimal must activate at least one URN"
    assert "directive:DIRECTIVE_001" in urns
    assert "tactic:acceptance-test-first" in urns

    # ...but no compiled bundle exists yet, so dispatch correctly still
    # treats the project as empty (NFR-004 bundle-presence predicate).
    assert not (tmp_path / ".kittify" / "charter" / "charter.yaml").exists()
    assert is_charter_empty(tmp_path) is True


def test_applied_minimal_directive_and_tactic_ids_resolve_in_the_built_in_catalog(
    tmp_path: Path,
) -> None:
    """Every id the minimal pack activates must be a REAL built-in artifact."""
    result = _apply(tmp_path, "minimal")
    assert result.exit_code == 0, result.output

    urns = charter_activated_urns(tmp_path)
    catalog = load_doctrine_catalog()
    directive_ids = {urn.split(":", 1)[1] for urn in urns if urn.startswith("directive:")}
    tactic_ids = {urn.split(":", 1)[1] for urn in urns if urn.startswith("tactic:")}

    assert directive_ids, "expected at least one activated directive"
    assert directive_ids <= catalog.directives
    assert tactic_ids, "expected at least one activated tactic"
    assert tactic_ids <= catalog.tactics


# ---------------------------------------------------------------------------
# `pack apply <name>` — User Customization Preservation (no clobber without --force)
# ---------------------------------------------------------------------------


def _existing_project(tmp_path: Path) -> Path:
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "activated_kinds:\n  - directives\n"
        "activated_directives:\n  - 003-decision-documentation-requirement\n",
        encoding="utf-8",
    )
    return tmp_path


def test_apply_without_force_does_not_overwrite_an_existing_key(tmp_path: Path) -> None:
    project_root = _existing_project(tmp_path)

    result = _apply(project_root, "minimal")

    assert result.exit_code == 0, result.output
    config_path = project_root / ".kittify" / "config.yaml"
    data = _load_yaml(config_path)
    # The user's pre-existing activated_directives value is untouched...
    assert data["activated_directives"] == ["003-decision-documentation-requirement"]
    # ...but a key the user never set (activated_tactics) IS written from the pack.
    assert data["activated_tactics"] == _load_yaml(_MINIMAL_PATH)["activated_tactics"]


def test_apply_without_force_reports_skipped_keys(tmp_path: Path) -> None:
    project_root = _existing_project(tmp_path)

    result = _apply(project_root, "minimal", "--json")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "activated_directives" in payload["keys_skipped"]
    assert "activated_directives" not in payload["keys_written"]
    assert "activated_tactics" in payload["keys_written"]


def test_apply_with_force_overwrites_the_existing_key(tmp_path: Path) -> None:
    project_root = _existing_project(tmp_path)

    result = _apply(project_root, "minimal", "--force")

    assert result.exit_code == 0, result.output
    config_path = project_root / ".kittify" / "config.yaml"
    data = _load_yaml(config_path)
    assert data["activated_directives"] == _load_yaml(_MINIMAL_PATH)["activated_directives"]


def test_apply_does_not_touch_a_different_pre_existing_user_charter(tmp_path: Path) -> None:
    """Activating the pack in ONE repo must never write to a DIFFERENT project."""
    user_repo = tmp_path / "existing-user-project"
    fresh_repo = tmp_path / "fresh-project"
    user_repo.mkdir()
    fresh_repo.mkdir()
    _existing_project(user_repo)

    user_config = user_repo / ".kittify" / "config.yaml"
    before = user_config.read_bytes()

    result = _apply(fresh_repo, "minimal")
    assert result.exit_code == 0, result.output

    after = user_config.read_bytes()
    assert after == before, "applying the pack elsewhere must not mutate a user's charter"
