"""#4174 landing-pass Concern 2: ``check_assets``'s membership/inventory
check has no toleration branch, unlike the content check just above it.

``check_assets`` (``asset_preparation.py``) observes a ``destination_probe``
node's directory membership (``members=True``) for the two NON-bootstrap
global owners -- ``agent_commands.py``'s output directory and
``agent_skills.py``'s ``destination_root`` -- and, when the current on-disk
child-name set no longer matches the recorded set, unconditionally raises
``Global asset inventory changed``. Unlike the CONTENT check immediately
above it (which tolerates a concurrent peer materializing this batch's own
canonical bytes, #4017 WP02), this membership check has no such branch: a
concurrent peer that adds (or retires) exactly one of THIS batch's own
managed names -- e.g. a commands/skills upgrade racing a cold install --
still raises, even once the anchor lock is held and even though the peer's
addition is exactly what this batch itself is about to (or already did)
write.

This module drives that gap directly against ``check_assets`` (no locking
plumbing needed -- the bug is in the pure comparison function itself, not in
when it is called): a destination root that PRE-EXISTS at assess time (so
``children`` is recorded as a real tuple, not ``None``), a peer that
materializes exactly one of the batch's own planned command files with
correct canonical bytes, and control cases where the peer instead adds an
UNMANAGED name, or the RIGHT name with the WRONG bytes, both of which must
still refuse.

The toleration test below models a realistic INCREMENTAL upgrade delta
(one managed name missing from an otherwise-complete, unchanged destination
root), not a from-scratch cold materialize: toleration additionally requires
every genuine content-file write in the SAME batch to already match
canonical bytes (mirroring the sibling content check's own
``content_confirmed`` requirement for a bookkeeping-stamp match, since a
directory-membership match alone -- like a stamp alone -- proves nothing
about the rest of the tree). A destination root that is still fully cold
(most managed names absent) is Concern 1's mid-write scenario instead
(``tests/runtime/test_recheck_mid_write_convergence.py``), not this one.

Building that realistic fixture surfaced a SEPARATE, blocking latent bug in
``agent_commands.py``'s existing-file predecessor-marker peek (line ~342):
``existing_bytes = prepared.source(target)`` reads an EXISTING DESTINATION
file's bytes via ``AssetPreparation.source()``, whose default role is
``"source_read"`` -- re-observing `target` under that role there silently
downgrades both `target` and (via ``observe()``'s ancestor walk) the
destination ROOT itself from ``"destination_probe"`` to ``"source_read"``,
because the role "stickiness" (``observe()``'s "once source_read, stays
source_read" rule) is one-directional and does not protect a
``destination_probe`` node from being overwritten by a LATER untagged call.
This permanently disables ALL peer-tolerance -- both the pre-existing
content check and this module's new membership toleration -- for the whole
destination tree on any WARM reassess where existing command files are
already present (i.e. on every real incremental-upgrade race, never on a
from-scratch cold install, which never takes this code path). Fixed by
reading the bytes directly (``target.read_bytes()``) instead of re-observing
an already-confirmed regular file through the wrong-default-role helper.
``TestDestinationRoleSurvivesWarmReassess`` below pins this independently of
the membership-toleration behavior it was blocking.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime import agent_commands
from specify_cli.runtime.asset_preparation import PreparedAssets, _write_asset, check_assets

pytestmark = [pytest.mark.unit, pytest.mark.fast]

GLOBAL_ASSET_INVENTORY_CHANGED_SIGNAL = "Global asset inventory changed"


@pytest.fixture
def owner_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    return home


def _assess_incremental_upgrade_addition(owner_home: Path):
    """Materialize the full canonical "claude" command bundle for real, then
    delete exactly ONE managed file and reassess -- the resulting batch's own
    plan is to recreate just that one file (a realistic incremental-upgrade
    delta), with every other managed name already present and unchanged, so
    ``content_paths`` is exactly that single file.
    """
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    output = agent_commands.get_global_command_dir("claude")
    existing = sorted(p for p in output.iterdir() if p.is_file())
    assert existing, "fixture must have installed at least one command file"
    removed = existing[0]
    removed_name = removed.name
    removed.unlink()

    assessment = agent_commands.assess_global_agent_commands(agent_keys=["claude"])
    assert assessment.complete and assessment.effects
    prepared = assessment.prepared
    assert isinstance(prepared, PreparedAssets)
    observation = next(o for o in prepared.observations if o.path == output)
    assert observation.children is not None and removed_name not in observation.children
    assert observation.role == "destination_probe", (
        f"the destination root's role must survive a warm reassess with existing command files present, got: {observation.role!r}"
    )
    return assessment, output, removed_name


def _assess_with_preexisting_empty_output(owner_home: Path):
    """Assess the real "claude" command bundle against a destination root
    that already exists (empty) -- so ``children`` is recorded as ``()``,
    not ``None``, exactly matching the described upgrade-race shape (a
    pre-existing managed root, not a genuinely cold one).
    """
    output = agent_commands.get_global_command_dir("claude")
    output.mkdir(parents=True)
    assessment = agent_commands.assess_global_agent_commands(agent_keys=["claude"])
    assert assessment.complete and assessment.effects
    prepared = assessment.prepared
    assert isinstance(prepared, PreparedAssets)
    observation = next(o for o in prepared.observations if o.path == output)
    assert observation.children == (), "fixture must record an empty pre-existing destination root"
    return assessment, output


class TestMembershipDriftPeerAdditionsTolerance:
    def test_peer_materializing_this_batchs_own_managed_file_is_tolerated(
        self,
        owner_home: Path,
    ) -> None:
        """A peer that added exactly one of THIS batch's own planned command
        files (with correct canonical bytes) must converge, mirroring the
        content check's own peer-tolerance immediately above it in
        ``check_assets``. Pre-fix, the unconditional membership check still
        raises here -- this is the RED half of the fix.
        """
        assessment, output, removed_name = _assess_incremental_upgrade_addition(owner_home)
        prepared = assessment.prepared
        assert isinstance(prepared, PreparedAssets)
        own_write = next(w for w in prepared.writes if w.effect.destination == output / removed_name)

        # --- A concurrent peer materializes exactly this batch's own ---
        # planned addition, with correct canonical bytes.
        _write_asset(own_write)
        assert own_write.effect.destination.is_file()

        diagnostics = check_assets(assessment)

        assert not diagnostics, f"expected a peer's own-batch addition to be tolerated, got: {diagnostics!r}"

    def test_peer_adding_a_managed_name_with_wrong_bytes_still_refuses(
        self,
        owner_home: Path,
    ) -> None:
        """Control case: the ADDED name is one of this batch's own managed
        names, but its bytes do NOT match the canonical content this batch
        is about to write -- must still refuse, both before and after the
        fix. Toleration requires canonical-EQUAL bytes, never a name match
        alone.
        """
        assessment, output = _assess_with_preexisting_empty_output(owner_home)
        prepared = assessment.prepared
        assert isinstance(prepared, PreparedAssets)
        own_write = next(w for w in prepared.writes if w.effect.destination.parent == output and w.effect.after.kind == "file")

        own_write.effect.destination.write_bytes(b"not the canonical bytes this batch would write")

        diagnostics = check_assets(assessment)

        assert diagnostics, "a managed name with non-canonical bytes must never be tolerated"
        assert GLOBAL_ASSET_INVENTORY_CHANGED_SIGNAL in diagnostics[0].message or "Global asset input changed" in diagnostics[0].message

    def test_peer_adding_an_unmanaged_name_still_refuses(
        self,
        owner_home: Path,
    ) -> None:
        """Control case: an UNMANAGED name appearing in the destination root
        must still refuse, both before and after the fix -- toleration is
        scoped exactly to this batch's own planned additions.
        """
        assessment, output = _assess_with_preexisting_empty_output(owner_home)

        (output / "rogue-unmanaged-file.txt").write_text("not part of this batch's canonical set")

        diagnostics = check_assets(assessment)

        assert diagnostics, "an unmanaged addition must never be tolerated"
        assert GLOBAL_ASSET_INVENTORY_CHANGED_SIGNAL in diagnostics[0].message
        assert str(output) in diagnostics[0].message


class TestDestinationRoleSurvivesWarmReassess:
    """Standalone regression pin for the latent role-downgrade bug this
    module's toleration fixture surfaced: a WARM reassess (existing command
    files already present) must never downgrade the destination root's own
    recorded role from ``"destination_probe"`` to ``"source_read"``.
    """

    def test_output_root_role_stays_destination_probe_with_existing_files_present(
        self,
        owner_home: Path,
    ) -> None:
        agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
        output = agent_commands.get_global_command_dir("claude")
        assert any(output.iterdir()), "fixture must have installed at least one command file"

        # A second, ordinary warm assess against the SAME already-installed
        # bundle takes the existing-file predecessor-marker peek for EVERY
        # canonical command file -- exactly the code path that downgraded
        # the role before the fix.
        assessment = agent_commands.assess_global_agent_commands(agent_keys=["claude"])
        prepared = assessment.prepared
        assert isinstance(prepared, PreparedAssets)
        observation = next(o for o in prepared.observations if o.path == output)

        assert observation.role == "destination_probe", (
            f"a warm reassess with existing command files present must never downgrade the destination root's role, got: {observation.role!r}"
        )
