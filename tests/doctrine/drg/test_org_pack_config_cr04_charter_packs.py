"""CR-04 compat shim: ``.kittify/config.yaml`` ``doctrine.org.packs`` ->
``charter_packs.org.packs`` (mission ``charter-code-topology-01M152G1`` S4).

Precedent for the read-both / canonical-wins / warn-once shape:
``charter.sync`` CR-01 (``src/charter/sync.py:245-311``).

Precedence order exercised here: ``charter_packs.org.packs`` (canonical, no
warning) -> ``doctrine.org.packs`` (legacy, warns once) -> top-level
``organisation_packs`` (oldest legacy, unchanged pre-existing
``DeprecationWarning`` every call -- CR-04 does not touch that tier).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.offering.drg.org_pack_config import (
    LegacyOrgPackDoctrineKeyWarning,
    OrgPackConfig,
    PackRegistry,
    _warn_legacy_org_pack_doctrine_key_once,
    load_pack_registry,
    save_pack_registry,
)

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


@pytest.fixture(autouse=True)
def _reset_warn_once_gate() -> None:
    """Each test gets a fresh warn-once gate (precedent: charter.sync tests)."""
    _warn_legacy_org_pack_doctrine_key_once.cache_clear()


def _write_config(repo_root: Path, text: str) -> Path:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(text, encoding="utf-8")
    return config_path


class TestCanonicalCharterPacksKeyReadsSilently:
    def test_charter_packs_org_packs_reads_without_warning(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        org_root = tmp_path / "org-pack"
        org_root.mkdir()
        _write_config(
            tmp_path,
            (
                "charter_packs:\n"
                "  org:\n"
                "    packs:\n"
                "      - name: example-org\n"
                f"        local_path: {org_root}\n"
            ),
        )

        registry = load_pack_registry(tmp_path)

        assert registry.names() == ["example-org"]
        assert not any(
            issubclass(w.category, LegacyOrgPackDoctrineKeyWarning) for w in recwarn.list
        )

    def test_charter_packs_wins_over_doctrine_org_when_both_present(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        canonical_root = tmp_path / "canonical-pack"
        canonical_root.mkdir()
        legacy_root = tmp_path / "legacy-pack"
        legacy_root.mkdir()
        _write_config(
            tmp_path,
            (
                "charter_packs:\n"
                "  org:\n"
                "    packs:\n"
                "      - name: canonical-org\n"
                f"        local_path: {canonical_root}\n"
                "doctrine:\n"
                "  org:\n"
                "    packs:\n"
                "      - name: legacy-org\n"
                f"        local_path: {legacy_root}\n"
            ),
        )

        registry = load_pack_registry(tmp_path)

        assert registry.names() == ["canonical-org"]
        # Canonical wins silently -- no nag for an operator who already has
        # both keys (mirrors CR-01's `apply_legacy_governance_selection_key_compat`).
        assert not any(
            issubclass(w.category, LegacyOrgPackDoctrineKeyWarning) for w in recwarn.list
        )


class TestLegacyDoctrineOrgKeyWarnsOnce:
    def test_doctrine_org_packs_reads_with_warning(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        org_root = tmp_path / "org-pack"
        org_root.mkdir()
        _write_config(
            tmp_path,
            (
                "doctrine:\n"
                "  org:\n"
                "    packs:\n"
                "      - name: legacy-org\n"
                f"        local_path: {org_root}\n"
            ),
        )

        registry = load_pack_registry(tmp_path)

        assert registry.names() == ["legacy-org"]
        assert any(
            issubclass(w.category, LegacyOrgPackDoctrineKeyWarning) for w in recwarn.list
        )

    def test_doctrine_org_packs_warns_only_once_per_process(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        org_root = tmp_path / "org-pack"
        org_root.mkdir()
        _write_config(
            tmp_path,
            (
                "doctrine:\n"
                "  org:\n"
                "    packs:\n"
                "      - name: legacy-org\n"
                f"        local_path: {org_root}\n"
            ),
        )

        load_pack_registry(tmp_path)
        load_pack_registry(tmp_path)
        load_pack_registry(tmp_path)

        warnings_seen = [
            w for w in recwarn.list if issubclass(w.category, LegacyOrgPackDoctrineKeyWarning)
        ]
        assert len(warnings_seen) == 1


class TestSavePackRegistryWritesCanonicalShape:
    def test_save_writes_charter_packs_not_doctrine(self, tmp_path: Path) -> None:
        registry = PackRegistry(
            packs=[OrgPackConfig(name="example-org", local_path=tmp_path / "pack")]
        )

        save_pack_registry(tmp_path, registry)

        raw = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
        assert "charter_packs" in raw
        assert "doctrine" not in raw

    def test_save_then_load_round_trips_via_canonical_key(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        registry = PackRegistry(
            packs=[OrgPackConfig(name="example-org", local_path=tmp_path / "pack")]
        )

        save_pack_registry(tmp_path, registry)
        loaded = load_pack_registry(tmp_path)

        assert loaded.names() == ["example-org"]
        assert not any(
            issubclass(w.category, LegacyOrgPackDoctrineKeyWarning) for w in recwarn.list
        )
