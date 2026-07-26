"""Architectural gate: doctrine artefacts must live at ``<type>/<pack>/[<category>/]<name>``.

Pins ADR 2026-07-26-2. The layout is not cosmetic -- it is what the resolvers key on:

* per-kind repositories scan **only** ``<type>/built-in``
  (``repository.py::_default_builtin_dir`` → ``Path(__file__).parent / "built-in"``);
* DRG node discovery scans ``<plural>/built-in`` and ``rglob``s beneath it, so a category
  directory *inside* the pack layer is found automatically.

Consequently an artefact placed anywhere else is **silently invisible**: never loaded, never
registered as a DRG node, never resolvable, never a legal edge target. It looks authored,
passes review, and does nothing. That is the defect class this gate closes by construction
(charter standing order #5 / ``DIRECTIVE_043``).

Two real violation shapes motivated it, both found by inspection because no gate existed:

1. PR #2918 shipped assets at ``assets/audiences/built-in/`` -- pack and category inverted.
   The correct path is ``assets/built-in/audiences/``.
2. Nine artefacts sat outside any pack layer (three byte-identical duplicates of live
   built-ins, two *stale divergent* copies claiming a live artefact id, four content-free
   seed stubs). All nine were dead. They are cleared in the same change that lands this gate,
   which is why :data:`_ALLOWLIST` is **empty** -- there is nothing to grandfather, and a
   frozen list of dead files would only invite a future reader to assume they mattered.

The gate is non-vacuous: :class:`TestGateNonVacuity` plants each violation shape in a tmp
tree and proves the checker rejects it, so a layout gate that always passes cannot
self-validate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.artifact_kinds import ArtifactKind

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_DOCTRINE_ROOT = Path(__file__).resolve().parents[2] / "src" / "doctrine"

#: The pack (provenance layer) directory name. ``built-in`` is the *only* legal spelling for
#: shipped artefacts -- ``shipped/`` appeared in several READMEs and cross-links but has never
#: existed on disk (ADR 2026-07-26-2 corrects those).
_PACK_DIR = "built-in"

#: Mission-tier kinds: these resolve from their own documented locations rather than from
#: the artifact-tier ``<type>/<pack>/`` shape, so the layout rule does not apply to them.
#:
#: * ``TEMPLATE`` -- mission-tier, empty glob, no ``*.template.yaml`` convention
#:   (see ``doctrine.artifact_kinds.ArtifactKind.glob_pattern``).
#: * ``ANTI_PATTERN`` -- hand-authored inside graph fragments; no standalone artifact file.
#: * ``MISSION_STEP_CONTRACT`` -- lives at ``missions/built_in_step_contracts/`` , which
#:   ``extractor.py::_iter_step_contract_data`` documents as the *authoritative source*.
#:   There is no ``mission_step_contracts/`` directory at all. This is a genuine tier
#:   exception, not a stray -- and it is pinned positively by
#:   :class:`TestMissionTierExceptions` so the carve-out cannot quietly become a hiding place.
_MISSION_TIER_KINDS: frozenset[ArtifactKind] = frozenset(
    {
        ArtifactKind.TEMPLATE,
        ArtifactKind.ANTI_PATTERN,
        ArtifactKind.MISSION_STEP_CONTRACT,
    }
)

#: Kinds discovered as files on disk under ``<plural>/<pack>/``.
_FILE_BACKED_KINDS: tuple[ArtifactKind, ...] = tuple(
    kind for kind in ArtifactKind if kind not in _MISSION_TIER_KINDS
)

#: Paths (relative to ``src/doctrine/``) exempted from the layout rule. Deliberately EMPTY:
#: the nine pre-existing violators were cleared rather than frozen. Adding an entry here
#: re-opens the silent-invisibility class for that path and needs an ADR amendment, not a
#: convenience edit.
_ALLOWLIST: frozenset[str] = frozenset()


def _is_legal_artefact_path(relative: Path) -> bool:
    """Return whether *relative* matches ``<type>/<pack>/[<category>/...]/<name>``.

    *relative* is relative to ``src/doctrine/``. Legal shape requires at least three parts
    (type, pack, filename) with the pack segment exactly at index 1. Any number of category
    directories may sit between the pack and the file.
    """
    parts = relative.parts
    if len(parts) < 3:
        return False
    return parts[1] == _PACK_DIR


def _iter_artefact_files(root: Path) -> list[Path]:
    """Return every ``*.<kind>.yaml`` artefact file under *root*, as relative paths."""
    found: list[Path] = []
    for kind in _FILE_BACKED_KINDS:
        for path in root.rglob(kind.glob_pattern):
            if "__pycache__" in path.parts:
                continue
            found.append(path.relative_to(root))
    return sorted(set(found))


def _violations(root: Path) -> list[Path]:
    return [
        rel
        for rel in _iter_artefact_files(root)
        if not _is_legal_artefact_path(rel) and rel.as_posix() not in _ALLOWLIST
    ]


class TestShippedTreeIsCompliant:
    def test_no_artefact_outside_the_pack_layer(self) -> None:
        violations = _violations(_DOCTRINE_ROOT)
        assert not violations, (
            "doctrine artefacts must live at `<type>/<pack>/[<category>/]<name>` "
            f"(pack dir = {_PACK_DIR!r}); these are silently invisible to the resolvers:\n"
            + "\n".join(f"  - {v.as_posix()}" for v in violations)
            + "\nSee docs/adr/3.x/2026-07-26-2-doctrine-artefact-pack-layout-convention.md"
        )

    def test_gate_actually_scanned_something(self) -> None:
        """Floor check: a glob that silently matches nothing would pass vacuously."""
        assert len(_iter_artefact_files(_DOCTRINE_ROOT)) > 100

    def test_allowlist_is_empty(self) -> None:
        """The nine violators were cleared, not frozen. Keep it that way."""
        assert len(_ALLOWLIST) == 0

    def test_no_phantom_shipped_pack_dir_exists(self) -> None:
        """``shipped/`` is not a second spelling of the pack layer -- it never existed."""
        strays = [
            p.relative_to(_DOCTRINE_ROOT).as_posix()
            for p in _DOCTRINE_ROOT.glob("*/shipped")
            if p.is_dir()
        ]
        assert not strays, f"unexpected `shipped/` pack dirs: {strays}"


class TestMissionTierExceptions:
    """Pin the mission-tier carve-out positively, so it cannot become a hiding place.

    Excluding a kind from the layout rule is only honest if that kind's real location is
    itself asserted. Otherwise "it's mission-tier" becomes an excuse for any stray.
    """

    def test_step_contracts_live_at_their_authoritative_mission_tier_path(self) -> None:
        contracts_dir = _DOCTRINE_ROOT / "missions" / "built_in_step_contracts"
        assert contracts_dir.is_dir(), "authoritative step-contract dir is missing"
        found = sorted(contracts_dir.glob("*.step-contract.yaml"))
        assert len(found) > 10, f"expected the shipped step contracts, found {len(found)}"

    def test_no_step_contract_lives_anywhere_else(self) -> None:
        expected_parent = _DOCTRINE_ROOT / "missions" / "built_in_step_contracts"
        strays = [
            p.relative_to(_DOCTRINE_ROOT).as_posix()
            for p in _DOCTRINE_ROOT.rglob("*.step-contract.yaml")
            if p.parent != expected_parent and "__pycache__" not in p.parts
        ]
        assert not strays, f"step contracts outside the authoritative dir: {strays}"

    def test_artifact_tier_kinds_are_still_covered(self) -> None:
        """The carve-out must not have swallowed a kind the rule should govern."""
        covered = set(_FILE_BACKED_KINDS)
        for kind in (
            ArtifactKind.DIRECTIVE,
            ArtifactKind.TACTIC,
            ArtifactKind.STYLEGUIDE,
            ArtifactKind.TOOLGUIDE,
            ArtifactKind.PARADIGM,
            ArtifactKind.PROCEDURE,
            ArtifactKind.AGENT_PROFILE,
            ArtifactKind.ASSET,
            ArtifactKind.GLOSSARY_PACK,
        ):
            assert kind in covered, f"{kind} must be governed by the layout rule"


class TestGateNonVacuity:
    """Self-mutation proofs: each real-world violation shape must be rejected."""

    def _plant(self, root: Path, relative: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("schema_version: '1.0'\nid: planted\nname: Planted\n")
        return path

    def test_rejects_artefact_directly_under_type_dir(self, tmp_path: Path) -> None:
        """Shape 2: the nine pre-existing strays (no pack layer at all)."""
        self._plant(tmp_path, "tactics/planted.tactic.yaml")
        assert [p.as_posix() for p in _violations(tmp_path)] == ["tactics/planted.tactic.yaml"]

    def test_rejects_category_above_pack(self, tmp_path: Path) -> None:
        """Shape 1: the #2918 inversion -- `assets/<category>/built-in/`."""
        self._plant(tmp_path, "assets/audiences/built-in/planted.asset.yaml")
        assert [p.as_posix() for p in _violations(tmp_path)] == [
            "assets/audiences/built-in/planted.asset.yaml"
        ]

    def test_accepts_pack_at_root_and_nested_category(self, tmp_path: Path) -> None:
        """The two legal shapes must pass, or the gate would reject the shipped tree."""
        self._plant(tmp_path, "directives/built-in/planted.directive.yaml")
        self._plant(tmp_path, "tactics/built-in/testing/planted.tactic.yaml")
        self._plant(tmp_path, "assets/built-in/audiences/planted.asset.yaml")
        assert _violations(tmp_path) == []

    def test_rejects_artefact_at_doctrine_root(self, tmp_path: Path) -> None:
        self._plant(tmp_path, "planted.tactic.yaml")
        assert [p.as_posix() for p in _violations(tmp_path)] == ["planted.tactic.yaml"]


class TestPromotedPowershellToolguideIsReachable:
    """The one promotion in the #2936 cleanup: it must now actually resolve.

    ``toolguides/powershell-syntax.toolguide.yaml`` + its 245-line ``POWERSHELL_SYNTAX.md``
    sat outside the pack layer since the doctrine framework's first commit, so the guide was
    never loadable. Promotion is only real if the artefact loads *and* its ``guide_path``
    points at the file's new home.
    """

    def test_toolguide_loads_from_the_pack_layer(self) -> None:
        from doctrine.toolguides.repository import ToolguideRepository

        toolguide = ToolguideRepository().get("powershell-syntax")
        assert toolguide is not None, "promoted powershell toolguide does not resolve"

    def test_guide_path_points_at_the_relocated_markdown(self) -> None:
        from doctrine.toolguides.repository import ToolguideRepository

        toolguide = ToolguideRepository().get("powershell-syntax")
        assert toolguide is not None
        guide_path = Path(toolguide.guide_path)
        assert guide_path.parts[:4] == ("src", "doctrine", "toolguides", _PACK_DIR)
        repo_root = _DOCTRINE_ROOT.parents[1]
        assert (repo_root / guide_path).is_file(), f"{guide_path} does not exist on disk"
