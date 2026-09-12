"""#4174 landing-pass Concern 3 (include() role note): a later family's
``destination_probe`` observation of a SHARED path must never downgrade an
earlier family's ``source_read`` tag for that same path in the merged
``_GlobalAssetPreparation`` batch.

``AssetPreparation.observe()`` already enforces this stickiness WITHIN one
owner's own builder (a path once recorded ``source_read`` stays
``source_read`` even if the SAME builder later probes it as a destination --
source and destination trees can share the HOME prefix under test layouts).
``_GlobalAssetPreparation.include()`` -- which merges each family's own
``AssetPreparation.observed`` dict into the shared cross-family batch --
already mirrors this for ``children`` (explicitly carried forward from the
first family that recorded them), but does last-writer-wins on the REST of
the merged ``AssetObservation``, including ``role``: whichever family's
``include()`` call happens to run LAST for a shared path silently overwrites
an earlier ``source_read`` tag with its own ``destination_probe`` tag,
reopening exactly the role-tagged toleration hole #4017/#4174 WP02 closed
(a shared path that is genuinely a package/template SOURCE for one family
could then be treated as a benign, peer-tolerable destination for the
BATCH as a whole).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.asset_preparation import AssetPreparation, _GlobalAssetPreparation
from specify_cli.tool_surface.operations import ApplyConsent, OperationRoot

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class TestIncludePreservesSourceReadStickinessAcrossFamilies:
    def test_later_destination_probe_family_cannot_downgrade_an_earlier_source_read_path(
        self,
        tmp_path: Path,
    ) -> None:
        shared = tmp_path / "shared-node"
        shared.write_text("shared bytes both families happen to observe")

        consent = ApplyConsent()
        cache_a = tmp_path / "cache_a"
        cache_a.mkdir()
        cache_b = tmp_path / "cache_b"
        cache_b.mkdir()

        builder_a = AssetPreparation("family_a", OperationRoot("family_a", "global", tmp_path), cache_a, ".family-a.lock", consent)
        builder_a.observe(shared, role="source_read")

        builder_b = AssetPreparation("family_b", OperationRoot("family_b", "global", tmp_path), cache_b, ".family-b.lock", consent)
        builder_b.observe(shared, role="destination_probe")

        batch = _GlobalAssetPreparation(consent)
        batch.include(builder_a, effects=())
        batch.include(builder_b, effects=())

        merged = batch.observations[shared]

        assert merged.role == "source_read", f"a later destination_probe family must never downgrade an earlier source_read path, got: {merged.role!r}"

    def test_reversed_include_order_still_preserves_source_read(
        self,
        tmp_path: Path,
    ) -> None:
        """The stickiness must not depend on which family happens to include
        first -- a ``destination_probe`` family included BEFORE the
        ``source_read`` family must still end up sticky, exactly mirroring
        ``observe()``'s own order-independent guarantee within one builder.
        """
        shared = tmp_path / "shared-node"
        shared.write_text("shared bytes both families happen to observe")

        consent = ApplyConsent()
        cache_a = tmp_path / "cache_a"
        cache_a.mkdir()
        cache_b = tmp_path / "cache_b"
        cache_b.mkdir()

        builder_a = AssetPreparation("family_a", OperationRoot("family_a", "global", tmp_path), cache_a, ".family-a.lock", consent)
        builder_a.observe(shared, role="source_read")

        builder_b = AssetPreparation("family_b", OperationRoot("family_b", "global", tmp_path), cache_b, ".family-b.lock", consent)
        builder_b.observe(shared, role="destination_probe")

        batch = _GlobalAssetPreparation(consent)
        batch.include(builder_b, effects=())  # destination_probe FIRST this time
        batch.include(builder_a, effects=())  # source_read SECOND

        merged = batch.observations[shared]

        assert merged.role == "source_read", f"stickiness must be order-independent, got: {merged.role!r}"

    def test_two_destination_probe_families_stay_destination_probe(
        self,
        tmp_path: Path,
    ) -> None:
        """Non-regression control: when NEITHER family ever tagged the shared
        path ``source_read``, the merged role must stay ``destination_probe``
        -- stickiness must not spuriously upgrade an ordinary shared
        destination node.
        """
        shared = tmp_path / "shared-node"
        shared.write_text("shared bytes both families happen to observe")

        consent = ApplyConsent()
        cache_a = tmp_path / "cache_a"
        cache_a.mkdir()
        cache_b = tmp_path / "cache_b"
        cache_b.mkdir()

        builder_a = AssetPreparation("family_a", OperationRoot("family_a", "global", tmp_path), cache_a, ".family-a.lock", consent)
        builder_a.observe(shared, role="destination_probe")

        builder_b = AssetPreparation("family_b", OperationRoot("family_b", "global", tmp_path), cache_b, ".family-b.lock", consent)
        builder_b.observe(shared, role="destination_probe")

        batch = _GlobalAssetPreparation(consent)
        batch.include(builder_a, effects=())
        batch.include(builder_b, effects=())

        merged = batch.observations[shared]

        assert merged.role == "destination_probe"
