"""MissionStepRepository — compound-key layered resolution (FR-012).

Resolution algorithm (highest precedence wins):
    1. Project layer: ``.kittify/overrides/mission-steps/{mission_type_id}/{step_id}/step.yaml``
    2. Org layer:     for each pack root in ``pack_context.pack_roots``,
                      check ``{root}/mission-steps/{mission_type_id}/{step_id}/step.yaml``
    3. Built-in layer: ``{builtin_steps_root}/{mission_type_id}/{step_id}/step.yaml``

Compound-key isolation guarantee
---------------------------------
The shadowing key is the **full compound key** ``(mission_type_id, step_id)``.
A shadow for ``("software-dev", "review")`` only overrides the *review* step of
the *software-dev* mission type.  It has **no effect** on
``("documentation", "review")`` because those two compound keys are distinct.

The :class:`StepKey` frozen dataclass enforces this at the cache layer: Python
``==`` and ``hash()`` compare *both* fields, so two ``StepKey`` instances with
the same ``step_id`` but different ``mission_type_id`` values are always
treated as separate entries.

Layer precedence in full
------------------------
project > org (earliest pack_root wins) > built-in

If ``pack_context`` is ``None``, only the built-in layer is queried.
If ``pack_context.repo_root`` is available, the project layer is also queried.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ruamel.yaml import YAML

from .models import MissionStep


class _PackContextLike(Protocol):
    """Narrow structural protocol for the pack-context object.

    Replaces the ``TYPE_CHECKING`` import of ``charter.pack_context.PackContext``
    (C-004: doctrine must not import from charter).  Only the two attributes
    accessed by this module are declared; the protocol is intentionally
    minimal so that any conforming object — including test fakes — satisfies
    it without needing to depend on the charter package.

    ``__hash__`` is declared explicitly (NFR-003, mission-step-creatability-01KXQA6R
    WP01) so this protocol is a structural subtype of ``collections.abc.Hashable``
    for ``mypy --strict`` -- ``resolve_all_for_mission_type``'s shared cache
    keys on ``pack_context`` directly. The real ``charter.pack_context.PackContext``
    (and every test double used against this module) is a frozen
    ``@dataclass``, which synthesizes ``__hash__`` automatically.
    """

    pack_roots: tuple[Path, ...]
    repo_root: Path

    def __hash__(self) -> int: ...

__all__ = [
    "StepKey",
    "MissionStepRepository",
]

# ---------------------------------------------------------------------------
# YAML loader (module-level singleton — thread-safe for reads)
# ---------------------------------------------------------------------------

_YAML = YAML(typ="safe")
_STEP_FILENAME = "step.yaml"

# ---------------------------------------------------------------------------
# Public value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StepKey:
    """Cache key for a compound ``(mission_type_id, step_id)`` pair.

    Both fields participate in equality and hashing.  This guarantees that
    ``StepKey("software-dev", "review") != StepKey("documentation", "review")``,
    which is the foundation of the compound-key isolation guarantee.
    """

    mission_type_id: str
    step_id: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_step_yaml(step_file: Path) -> MissionStep | None:
    """Parse *step_file* into a :class:`~doctrine.missions.models.MissionStep`.

    Returns ``None`` when the file does not exist, is empty, or cannot be
    parsed.  Any extra keys in the YAML (e.g. ``display_name``, ``step_type``,
    ``guidance``, ``delegates_to``) are passed through as-is; ``MissionStep``
    is configured with ``extra="forbid"`` so we strip unknown keys before
    validation.

    The mapping between step.yaml field names and MissionStep field names:

    step.yaml field         → MissionStep field
    ─────────────────────────────────────────────
    id                      → id
    display_name            → display_name  (human-readable label; also accessible as .title)
    step_type               → step_type     (executor discriminant)
    prompt_template         → prompt_template
    agent_profile           → agent-profile (alias)
    depends_on              → depends_on
    sequence_index          → sequence_index          (S-B, WP01)
    in_action_sequence      → in_action_sequence       (S-B, WP01)
    recommended_model_tier  → recommended_model_tier   (S-B, WP01; advisory offer, WP08 consumer)
    template                → template                 (S-B, WP01; MissionStepTemplateRef)
    (guidance)              → stripped (not in MissionStep)
    (delegates_to)          → stripped (not in MissionStep)

    ``MissionStep`` is ``extra="forbid"`` — any field absent from this
    mapping is **silently stripped** before validation rather than raising.
    Every new ``MissionStep`` field MUST be added here or it vanishes on
    load with no error (see :mod:`tests.doctrine.missions.test_step_schema`
    for the round-trip regression guard).
    """
    if not step_file.exists():
        return None
    try:
        raw: Any = _YAML.load(step_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(raw, dict):
        return None

    # Map step.yaml fields → MissionStep fields and strip unknown keys.
    _STEP_YAML_TO_MODEL: dict[str, str] = {
        "id": "id",
        "display_name": "display_name",
        "step_type": "step_type",
        "prompt_template": "prompt_template",
        "agent_profile": "agent-profile",  # alias
        "depends_on": "depends_on",
        "sequence_index": "sequence_index",
        "in_action_sequence": "in_action_sequence",
        "recommended_model_tier": "recommended_model_tier",
        "template": "template",
    }
    mapped: dict[str, Any] = {}
    for src_key, dst_key in _STEP_YAML_TO_MODEL.items():
        if src_key in raw:
            mapped[dst_key] = raw[src_key]

    try:
        return MissionStep.model_validate(mapped)
    except Exception:  # noqa: BLE001
        return None


def _add_step_ids_from_dir(step_ids: set[str], mission_type_dir: Path) -> None:
    """Add step ids from ``mission_type_dir`` when ``step.yaml`` exists."""
    if not mission_type_dir.is_dir():
        return
    for entry in mission_type_dir.iterdir():
        if entry.is_dir() and (entry / _STEP_FILENAME).exists():
            step_ids.add(entry.name)


def _project_mission_type_dir(
    pack_context: _PackContextLike, mission_type_id: str,
) -> Path:
    """Return the project override directory for a mission type."""
    return (
        pack_context.repo_root
        / ".kittify"
        / "overrides"
        / "mission-steps"
        / mission_type_id
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class MissionStepRepository:
    """Resolves MissionStep definitions via built-in → org → project layering.

    Shadowing key: compound ``(mission_type_id, step_id)``.

    A ``software-dev/review`` shadow does **NOT** affect
    ``documentation/review``.  See module docstring for the full resolution
    algorithm and compound-key isolation guarantee.

    Parameters
    ----------
    builtin_steps_root:
        Directory that contains the built-in step definitions, laid out as
        ``{mission_type_id}/{step_id}/step.yaml`` sub-paths.

        Defaults to the ``mission-steps/`` directory co-located with this
        module when constructed via :meth:`default`.
    """

    def __init__(self, builtin_steps_root: Path) -> None:
        self._builtin_root: Path = builtin_steps_root

    # ------------------------------------------------------------------
    # Class-level constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    def default(cls) -> MissionStepRepository:
        """Return a repository loaded from the doctrine-bundled mission-steps directory."""
        return cls(Path(__file__).parent / "mission-steps")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def resolve(
        self,
        mission_type_id: str,
        step_id: str,
        pack_context: _PackContextLike | None = None,
    ) -> MissionStep | None:
        """Return the highest-precedence MissionStep for the given compound key.

        Layer order (highest wins): project → org → built-in.

        Parameters
        ----------
        mission_type_id:
            The mission type identifier (e.g. ``"software-dev"``).
        step_id:
            The step identifier (e.g. ``"review"``).
        pack_context:
            Optional :class:`~charter.pack_context.PackContext` providing org
            pack roots and the repository root for project-layer overrides.
            When ``None``, only the built-in layer is consulted.

        Returns
        -------
        MissionStep | None
            The resolved step, or ``None`` if not found in any layer.
        """
        # ── Layer 1: project ──────────────────────────────────────────────
        if pack_context is not None:
            project_step = self._resolve_project_layer(
                mission_type_id, step_id, pack_context
            )
            if project_step is not None:
                return project_step

        # ── Layer 2: org ──────────────────────────────────────────────────
        if pack_context is not None:
            org_step = self._resolve_org_layer(mission_type_id, step_id, pack_context)
            if org_step is not None:
                return org_step

        # ── Layer 3: built-in ─────────────────────────────────────────────
        return self._resolve_builtin_layer(mission_type_id, step_id)

    def resolve_all_for_mission_type(
        self,
        mission_type_id: str,
        pack_context: _PackContextLike | None = None,
    ) -> dict[str, MissionStep]:
        """Return all steps for a mission type, with shadowing applied.

        Scans the built-in layer for available ``step_id`` values, then
        applies org and project shadows via :meth:`resolve`.

        **Shared cache (NFR-003):** the underlying filesystem walk is
        memoised in a **module-level** cache keyed by
        ``(builtin_steps_root, mission_type_id, pack_context)`` -- shared
        across every :class:`MissionStepRepository` instance and call site,
        not scoped to ``self`` or to a single consumer. This is deliberate:
        after the S-C cutover (mission-step-creatability-01KXQA6R WP01)
        both the retained ``action_sequence`` overlay
        (``mission_type_repository._inject_projected_fields``) and the
        projected ``template_set`` slot
        (``charter.mission_type_profiles._resolve_template_set_slot``)
        resolve steps for the same ``(mission_type, pack_context)`` per
        resolution; without a shared cache that would be two filesystem
        walks instead of one. Cleared via :meth:`cache_clear` (test seam).

        Parameters
        ----------
        mission_type_id:
            The mission type identifier (e.g. ``"software-dev"``).
        pack_context:
            Optional pack context for org/project layer resolution.

        Returns
        -------
        dict[str, MissionStep]
            Mapping of ``step_id → MissionStep`` with shadowing applied.
            Only step IDs that exist in the built-in layer (or in org/project
            overrides for the same mission type) are returned.
        """
        return _resolve_all_for_mission_type_cached(
            self._builtin_root, mission_type_id, pack_context
        )

    @staticmethod
    def cache_clear() -> None:
        """Test seam (NFR-003): clear the shared ``resolve_all_for_mission_type`` cache.

        Production never mutates the bundled ``mission-steps/`` tree
        mid-process, so the cache is safe there; tests that write into a
        synthetic tree and expect a subsequent call to observe the change
        must call this first (mirrors the ``MissionTypeRepository.default``
        cache-vs-test-seam contract, C-010).
        """
        _resolve_all_for_mission_type_cached.cache_clear()

    def _resolve_all_for_mission_type_uncached(
        self,
        mission_type_id: str,
        pack_context: _PackContextLike | None,
    ) -> dict[str, MissionStep]:
        """Perform the actual layered filesystem walk (the cache-miss path)."""
        result: dict[str, MissionStep] = {}

        # Collect step_ids from all layers.
        step_ids: set[str] = set()

        # Built-in layer
        _add_step_ids_from_dir(step_ids, self._builtin_root / mission_type_id)

        # Org layer (collect any extra step_ids present in org packs)
        if pack_context is not None:
            step_ids.update(self._collect_org_step_ids(mission_type_id, pack_context))

        # Project layer (collect any extra step_ids present in project overrides)
        if pack_context is not None:
            _add_step_ids_from_dir(
                step_ids, _project_mission_type_dir(pack_context, mission_type_id),
            )

        # Resolve each step_id through the full layer stack.
        for step_id in step_ids:
            step = self.resolve(mission_type_id, step_id, pack_context)
            if step is not None:
                result[step_id] = step

        return result

    # ------------------------------------------------------------------
    # Private layer helpers
    # ------------------------------------------------------------------

    def _collect_org_step_ids(
        self, mission_type_id: str, pack_context: _PackContextLike
    ) -> set[str]:
        """Collect step_ids discoverable in org packs for *mission_type_id*.

        Iterates over ``pack_context.pack_roots``, skipping the built-in root
        (``self._builtin_root.parent``) which is handled by the built-in layer.
        """
        step_ids: set[str] = set()
        builtin_pack_root = self._builtin_root.parent
        for pack_root in pack_context.pack_roots:
            if pack_root == builtin_pack_root:
                continue
            org_mt_dir = pack_root / "mission-steps" / mission_type_id
            _add_step_ids_from_dir(step_ids, org_mt_dir)
        return step_ids

    def _resolve_builtin_layer(
        self, mission_type_id: str, step_id: str
    ) -> MissionStep | None:
        """Attempt to load ``{builtin_steps_root}/{mission_type_id}/{step_id}/step.yaml``."""
        step_file = self._builtin_root / mission_type_id / step_id / _STEP_FILENAME
        return _load_step_yaml(step_file)

    def _resolve_org_layer(
        self,
        mission_type_id: str,
        step_id: str,
        pack_context: _PackContextLike,
    ) -> MissionStep | None:
        """Iterate over ``pack_context.pack_roots`` in order.

        The first org-layer file found (earliest in ``pack_roots`` order)
        wins over the built-in layer.

        The built-in root (``self._builtin_root.parent``) is skipped when it
        appears in ``pack_roots`` — it is already handled by
        :meth:`_resolve_builtin_layer` and must not be re-scanned here.

        Org pack layout convention:
            ``{pack_root}/mission-steps/{mission_type_id}/{step_id}/step.yaml``
        """
        builtin_pack_root = self._builtin_root.parent
        for pack_root in pack_context.pack_roots:
            if pack_root == builtin_pack_root:
                continue
            step_file = (
                pack_root / "mission-steps" / mission_type_id / step_id / _STEP_FILENAME
            )
            step = _load_step_yaml(step_file)
            if step is not None:
                return step
        return None

    def _resolve_project_layer(
        self,
        mission_type_id: str,
        step_id: str,
        pack_context: _PackContextLike,
    ) -> MissionStep | None:
        """Check ``.kittify/overrides/mission-steps/{mission_type_id}/{step_id}/step.yaml``.

        Project-layer shadow wins over both org and built-in layers.
        """
        step_file = _project_mission_type_dir(
            pack_context, mission_type_id,
        ) / step_id / _STEP_FILENAME
        return _load_step_yaml(step_file)


# ---------------------------------------------------------------------------
# Shared cache (NFR-003, mission-step-creatability-01KXQA6R WP01)
# ---------------------------------------------------------------------------


@functools.cache
def _resolve_all_for_mission_type_cached(
    builtin_root: Path,
    mission_type_id: str,
    pack_context: _PackContextLike | None,
) -> dict[str, MissionStep]:
    """Module-level, cross-instance cache for ``resolve_all_for_mission_type``.

    Keyed by ``(builtin_root, mission_type_id, pack_context)`` -- **not**
    keyed on any :class:`MissionStepRepository` instance, so it stays
    shared even though ``MissionStepRepository.default()`` itself is not
    memoised (only ``MissionTypeRepository.default()`` singletons the
    *repository object*; this cache is what actually avoids re-walking
    ``mission-steps/`` on repeat resolutions, per NFR-003). ``pack_context``
    is either ``None`` or a hashable frozen dataclass (real
    ``charter.pack_context.PackContext``, or a test double satisfying the
    same shape), so it is safe to use directly as part of the cache key.

    Cleared via :meth:`MissionStepRepository.cache_clear` (test seam) --
    never call ``.cache_clear()`` on this private function directly from
    outside this module.
    """
    return MissionStepRepository(
        builtin_root
    )._resolve_all_for_mission_type_uncached(mission_type_id, pack_context)
