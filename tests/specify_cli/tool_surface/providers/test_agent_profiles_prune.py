"""R8 — projection ``--fix`` prunes de-activated/orphaned projected artifacts.

Debbie's finding: ``doctor tool-surfaces --kind agent-profile --fix`` projected
org/agent files but never removed a stale ``.claude/agents/<id>.md`` (or its
manifest entry) once a profile was de-activated. The in-memory projection set
shrank, but disk + manifest kept the orphan.

This drives the real provider (no injected projector, so projection applies the
charter activation gate via ``default_profile_repository``) over a real-format
org pack: project an org agent with ``--fix``, then de-activate it and re-run
``--fix``. The orphaned file AND its manifest entry must be gone, while a
still-projected built-in profile (and its entry) is untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.tool_surface.profiles.manifest import ProfileManifest
from specify_cli.tool_surface.providers.agent_profiles import (
    AgentProfilesProvider,
    agent_profile_definition,
)

pytestmark = pytest.mark.fast

_PACK_NAME = "orgzilla-governance-pack"
_ORG_ANALYST_ID = "orgzilla-org-analyst"
# A real built-in projected (ungated by projection) in both regimes; it is the
# "still-activated/unrelated" control that must NOT be pruned.
_UNRELATED_BUILTIN_ID = "reviewer-renata"
_TOOL_KEY = "claude"


def _agent_yaml(profile_id: str, *, name: str, role: str) -> str:
    return (
        f"profile-id: {profile_id}\n"
        f"name: {name}\n"
        "description: Org-pack profile for prune fixtures\n"
        'schema-version: "1.0"\n'
        "roles:\n"
        f"  - {role}\n"
        "purpose: >\n"
        "  Organisation-provided analyst used to verify prune-on-deactivation.\n"
        "specialization:\n"
        "  primary-focus: >\n"
        "    Organisation-specific evidence-provenance analysis.\n"
        "  avoidance-boundary: unrelated work\n"
    )


def _write_org_pack(repo_root: Path) -> Path:
    pack_root = repo_root / "org-packs" / _PACK_NAME
    profiles_dir = pack_root / "agent_profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / f"{_ORG_ANALYST_ID}.agent.yaml").write_text(
        _agent_yaml(_ORG_ANALYST_ID, name="Orgzilla Org Analyst", role="researcher"),
        encoding="utf-8",
    )
    return pack_root


def _write_config(repo_root: Path, pack_root: Path, *, activated: list[str] | None) -> None:
    data: dict[str, object] = {
        "doctrine": {"org": {"packs": [{"name": _PACK_NAME, "local_path": str(pack_root)}]}},
    }
    if activated is not None:
        data["activated_agent_profiles"] = activated
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        YAML().dump(data, fh)


def _run_fix(repo_root: Path) -> None:
    """Drive the provider's expand -> probe -> repair (``--fix``) cycle."""
    provider = AgentProfilesProvider()
    definition = agent_profile_definition()
    instances = provider.expand(definition, _TOOL_KEY, repo_root)
    statuses = [provider.probe(instance) for instance in instances]
    provider.repair(repo_root, statuses, dry_run=False)


def _manifest_output_names(repo_root: Path) -> set[str]:
    manifest = ProfileManifest.load(repo_root)
    return {entry.output_path.name for entry in manifest.all_entries()}


def test_fix_prunes_deactivated_profile_file_and_manifest_entry(tmp_path: Path) -> None:
    """De-activating an org agent and re-running ``--fix`` removes its orphan."""
    pack_root = _write_org_pack(tmp_path)
    _write_config(tmp_path, pack_root, activated=None)

    _run_fix(tmp_path)

    org_file = tmp_path / ".claude" / "agents" / f"{_ORG_ANALYST_ID}.md"
    unrelated_file = tmp_path / ".claude" / "agents" / f"{_UNRELATED_BUILTIN_ID}.md"
    assert org_file.exists(), "the admitted org agent must be projected to disk"
    assert unrelated_file.exists()
    names = _manifest_output_names(tmp_path)
    assert f"{_ORG_ANALYST_ID}.md" in names
    assert f"{_UNRELATED_BUILTIN_ID}.md" in names

    # De-activate the org agent (activate only the unrelated built-in).
    _write_config(tmp_path, pack_root, activated=[_UNRELATED_BUILTIN_ID])

    _run_fix(tmp_path)

    # The orphaned file AND its manifest entry are gone.
    assert not org_file.exists(), "the de-activated org agent file must be pruned"
    names_after = _manifest_output_names(tmp_path)
    assert f"{_ORG_ANALYST_ID}.md" not in names_after, (
        "the de-activated org agent manifest entry must be dropped"
    )
    # The still-projected built-in (and its entry) is untouched.
    assert unrelated_file.exists()
    assert f"{_UNRELATED_BUILTIN_ID}.md" in names_after


def test_fix_does_not_prune_unrelated_user_file(tmp_path: Path) -> None:
    """A user-authored ``.claude/agents`` file not in the manifest is never pruned."""
    pack_root = _write_org_pack(tmp_path)
    _write_config(tmp_path, pack_root, activated=None)
    _run_fix(tmp_path)

    # Seed an unrelated user file the projector never wrote / tracked.
    user_file = tmp_path / ".claude" / "agents" / "my-handwritten-agent.md"
    user_file.write_text("# hand-authored, not managed by spec-kitty\n", encoding="utf-8")

    # De-activate the org agent and re-run --fix (triggers a prune pass).
    _write_config(tmp_path, pack_root, activated=[_UNRELATED_BUILTIN_ID])
    _run_fix(tmp_path)

    assert user_file.exists(), "untracked user files must never be pruned"
