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
    """

    pack_roots: tuple[Path, ...]
    repo_root: Path

__all__ = [
    "StepKey",
    "MissionStepRepository",
]

# ---------------------------------------------------------------------------
# YAML loader (module-level singleton — thread-safe for reads)
# ---------------------------------------------------------------------------

_YAML = YAML(typ="safe")

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

    step.yaml field   → MissionStep field
    ─────────────────────────────────────
    id                → id
    display_name      → display_name  (human-readable label; also accessible as .title)
    step_type         → step_type     (executor discriminant)
    prompt_template   → prompt_template
    agent_profile     → agent-profile (alias)
    depends_on        → depends_on
    (guidance)        → stripped (not in MissionStep)
    (delegates_to)    → stripped (not in MissionStep)
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
    }
    mapped: dict[str, Any] = {}
    for src_key, dst_key in _STEP_YAML_TO_MODEL.items():
        if src_key in raw:
            mapped[dst_key] = raw[src_key]

    try:
        return MissionStep.model_validate(mapped)
    except Exception:  # noqa: BLE001
        return None


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
        result: dict[str, MissionStep] = {}

        # Collect step_ids from all layers.
        step_ids: set[str] = set()

        # Built-in layer
        builtin_mt_dir = self._builtin_root / mission_type_id
        if builtin_mt_dir.is_dir():
            for entry in builtin_mt_dir.iterdir():
                if entry.is_dir() and (entry / "step.yaml").exists():
                    step_ids.add(entry.name)

        # Org layer (collect any extra step_ids present in org packs)
        if pack_context is not None:
            step_ids.update(self._collect_org_step_ids(mission_type_id, pack_context))

        # Project layer (collect any extra step_ids present in project overrides)
        if pack_context is not None:
            project_mt_dir = (
                pack_context.repo_root
                / ".kittify"
                / "overrides"
                / "mission-steps"
                / mission_type_id
            )
            if project_mt_dir.is_dir():
                for entry in project_mt_dir.iterdir():
                    if entry.is_dir() and (entry / "step.yaml").exists():
                        step_ids.add(entry.name)

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
            if org_mt_dir.is_dir():
                for entry in org_mt_dir.iterdir():
                    if entry.is_dir() and (entry / "step.yaml").exists():
                        step_ids.add(entry.name)
        return step_ids

    def _resolve_builtin_layer(
        self, mission_type_id: str, step_id: str
    ) -> MissionStep | None:
        """Attempt to load ``{builtin_steps_root}/{mission_type_id}/{step_id}/step.yaml``."""
        step_file = self._builtin_root / mission_type_id / step_id / "step.yaml"
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
                pack_root / "mission-steps" / mission_type_id / step_id / "step.yaml"
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
        step_file = (
            pack_context.repo_root
            / ".kittify"
            / "overrides"
            / "mission-steps"
            / mission_type_id
            / step_id
            / "step.yaml"
        )
        return _load_step_yaml(step_file)
