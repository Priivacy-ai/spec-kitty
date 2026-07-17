"""MissionTypeRepository — loads and indexes MissionType YAML files."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .mission_step_repository import MissionStepRepository
from .models import MissionType
from .step_projection import project_action_sequence

__all__ = [
    "MissionTypeRepository",
    "builtin_mission_type_id_set",
    "builtin_mission_type_ids",
]


class MissionTypeRepository:
    """Loads and indexes MissionType YAML files from a directory.

    Scans *mission_types_dir* for ``*.yaml`` files, parses each via the
    :class:`~doctrine.missions.models.MissionType` Pydantic model, validates
    that each file's ``id`` field matches the filename stem, then indexes the
    results for O(1) lookup.

    The repository is eager: all files are loaded at construction time.
    Any parse or validation error raises immediately so callers never receive
    a partially populated repository.

    Parameters
    ----------
    mission_types_dir:
        Path to the directory that contains ``*.yaml`` MissionType files.
    """

    def __init__(self, mission_types_dir: Path) -> None:
        self._dir = mission_types_dir
        self._index: dict[str, MissionType] = self._load(mission_types_dir)

    # ------------------------------------------------------------------
    # Class-level constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    @functools.cache
    def default(cls) -> MissionTypeRepository:
        """Return a repository loaded from the doctrine-bundled mission_types directory.

        Memoized (NFR-007, WP02): loading a mission type now also resolves
        that type's builtin ``step.yaml`` set to compute the
        ``action_sequence``/``template_set`` projection (see
        :func:`_inject_projected_fields`), so an un-memoized ``default()``
        would re-walk and re-parse the entire ``mission-steps/`` tree on
        every hot-path call. Reuses the exact ``@functools.cache`` idiom
        applied to :func:`builtin_mission_type_ids` below.

        Test seam: call ``MissionTypeRepository.default.cache_clear()``
        (auto-provided by ``functools.cache``, reachable through the
        classmethod's bound-method attribute proxy) to force a rebuild --
        e.g. after pointing at a synthetic ``mission_types/`` fixture tree.
        Production never mutates the bundled ``mission_types/``/
        ``mission-steps/`` trees mid-process, so the cache is safe there;
        tests must never write into the real bundled trees to exercise this
        seam (mirrors the ``builtin_mission_type_ids`` cache-vs-test-seam
        contract, C-010).
        """
        try:
            from importlib.resources import files

            resource = files("doctrine") / "missions" / "mission_types"
            return cls(Path(str(resource)))
        except (ModuleNotFoundError, TypeError):
            return cls(Path(__file__).parent / "mission_types")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_all(self) -> list[MissionType]:
        """Return all loaded :class:`MissionType` objects, sorted by ``id``.

        Returns
        -------
        list[MissionType]
            Sorted by ``id`` (ascending, lexicographic).
        """
        return sorted(self._index.values(), key=lambda m: m.id)

    def get(self, mission_type_id: str) -> MissionType | None:
        """Look up a MissionType by its id.

        Parameters
        ----------
        mission_type_id:
            The ``id`` field value (e.g. ``"software-dev"``).

        Returns
        -------
        MissionType | None
            The matching :class:`MissionType`, or ``None`` if not found.
        """
        return self._index.get(mission_type_id)

    def ids(self) -> list[str]:
        """Return a sorted list of all registered mission-type IDs.

        Returns
        -------
        list[str]
            Sorted ascending, lexicographic.
        """
        return sorted(self._index.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(directory: Path) -> dict[str, MissionType]:
        """Scan *directory* for ``*.yaml`` files and return an id-keyed dict.

        Raises
        ------
        ValueError
            If a file's parsed ``id`` does not match the filename stem.
        pydantic.ValidationError
            If any YAML file fails :class:`MissionType` validation.
        """
        _yaml = YAML(typ="safe")
        index: dict[str, MissionType] = {}
        if not directory.is_dir():
            return index

        for yaml_file in sorted(directory.glob("*.yaml")):
            raw: Any = _yaml.load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError(
                    f"Expected a YAML mapping in {yaml_file}; got {type(raw).__name__}"
                )
            payload = _inject_projected_fields(raw, mission_type_id=yaml_file.stem)
            mission_type = MissionType.model_validate(payload)
            expected_id = yaml_file.stem
            if mission_type.id != expected_id:
                raise ValueError(
                    f"MissionType id {mission_type.id!r} in {yaml_file.name} "
                    f"does not match filename stem {expected_id!r}. "
                    "Rename the file or correct the id field."
                )
            index[mission_type.id] = mission_type

        return index


# ----------------------------------------------------------------------------
# WP02 projection injection (S-B transitional seam)
# ----------------------------------------------------------------------------


def _inject_projected_fields(raw: dict[str, Any], *, mission_type_id: str) -> dict[str, Any]:
    """Overlay the WP02 ``action_sequence`` projection onto *raw* YAML fields.

    Resolves *mission_type_id*'s **builtin-only** step set
    (``pack_context=None`` -- org/project overrides never leak into this
    repository-load-time injection; those apply through the separate
    runtime consumer switch, WP06) and derives ``action_sequence`` via
    :func:`~doctrine.missions.step_projection.project_action_sequence`.

    **Transitional fallback (``action_sequence`` only, C-007-retained):**
    ``action_sequence`` is still YAML-authored for every built-in mission
    type. Until a given type's steps carry ``sequence_index`` /
    ``in_action_sequence`` data, the projection over that type's steps is
    legitimately empty. Injecting an empty value in that case would violate
    ``MissionType``'s non-empty invariant. So an **empty projection falls
    back to the raw YAML-authored value** rather than overwriting it; only
    a *non-empty* projection is injected in its place.

    ``template_set`` (S-C cutover, mission-step-creatability-01KXQA6R WP01,
    FR-001): the persisted field and its overlay are retired entirely --
    this function no longer reads or writes a ``template_set`` key at all.
    ``payload = dict(raw)`` below preserves any (incorrect) raw-authored
    ``template_set:`` key verbatim; ``MissionType``'s ``extra="forbid"``
    then rejects it during validation (SC-002 loud-fail), rather than this
    seam silently honoring or dropping it. Consumers now source the
    template mapping from the step authority directly at the consumption
    boundary (:func:`charter.mission_type_profiles._resolve_template_set_slot`),
    not from this repository-load-time injection.
    """
    steps = list(
        MissionStepRepository.default()
        .resolve_all_for_mission_type(mission_type_id, pack_context=None)
        .values()
    )

    projected_sequence = project_action_sequence(steps)

    payload = dict(raw)
    payload["action_sequence"] = projected_sequence or raw.get("action_sequence")
    return payload


# ----------------------------------------------------------------------------
# Module-level canonical accessors (single source of truth, IC-1a / #2669)
# ----------------------------------------------------------------------------


@functools.cache
def builtin_mission_type_ids() -> tuple[str, ...]:
    """The built-in mission-type ids, derived from the doctrine mission_types/*.yaml source.

    Single canonical authority for "which mission types ship". Sorted (lexicographic).
    Cached: one filesystem scan per process (NFR-002). Raises transitively if the
    repository loud-fails on an id/stem mismatch or invalid schema.

    Test seam (C-010): tests inject a synthetic roster by monkeypatching
    :meth:`MissionTypeRepository.default` (or the root it resolves to), then calling
    ``builtin_mission_type_ids.cache_clear()`` (auto-provided by ``functools.cache``)
    before asserting. Production never adds/removes built-in type YAMLs mid-process,
    so the cache is safe there; tests must never write into the real bundled
    ``mission_types/`` directory to exercise this seam.
    """
    return tuple(MissionTypeRepository.default().ids())


def builtin_mission_type_id_set() -> frozenset[str]:
    """Frozenset projection of :func:`builtin_mission_type_ids` for membership/default consumers."""
    return frozenset(builtin_mission_type_ids())
