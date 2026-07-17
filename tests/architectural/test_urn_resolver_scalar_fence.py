"""C-002 scalar fence for the resolve-by-URN lane (WP07/T033).

``contracts/name-urn-resolution.md`` (mission
``mission-step-creatability-01KXQA6R``) freezes two invariants for
:func:`specify_cli.runtime.resolver.resolve_template_by_urn`:

1. It is a **second** resolution lane, added *alongside*
   :func:`specify_cli.runtime.resolver.resolve_configured_template` (Lane 1,
   the name-based creation path) -- neither lane re-wires the other.
2. (C-002) The new URN-lane code must **never reference** the scalar
   ``template_set`` surfaces: ``resolution.template_set`` (i.e.
   ``ResolvedMissionType.template_set``, read by Lane 1),
   ``MissionTypeProfile.template_set``, or ``doctrine.template_set``
   (``DoctrineSelectionConfig.template_set``, read by
   ``charter.resolver._resolve_template_set_selection``). Collapsing the two
   lanes onto the scalar mapping would turn the name-keyed override chain
   into dead code.

This test scopes its scan to the AST subtree of ``resolve_template_by_urn``
specifically (not the whole module), because Lane 1
(``resolve_configured_template``) legitimately reads
``resolved_mission_type.template_set`` and must keep doing so unchanged.
Modelled on the import/reference-boundary style used by
``tests/architectural/test_layer_rules.py`` and
``tests/architectural/test_runtime_charter_doctrine_boundary.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_RESOLVER_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "specify_cli"
    / "runtime"
    / "resolver.py"
)

#: The scalar attribute name shared by all three fenced surfaces
#: (``resolution.template_set``, ``MissionTypeProfile.template_set``,
#: ``doctrine.template_set`` all resolve to a ``.template_set`` attribute
#: access on their respective carrier object).
_FENCED_ATTRIBUTE = "template_set"

_URN_LANE_FUNCTION = "resolve_template_by_urn"
_NAME_LANE_FUNCTION = "resolve_configured_template"


def _resolver_source_and_tree() -> tuple[str, ast.Module]:
    source = _RESOLVER_PATH.read_text(encoding="utf-8")
    return source, ast.parse(source, filename=str(_RESOLVER_PATH))


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function {name!r} not found in {_RESOLVER_PATH}")


def _attribute_names(node: ast.AST) -> list[str]:
    """Collect every ``.attr`` name accessed anywhere inside ``node``."""
    return [child.attr for child in ast.walk(node) if isinstance(child, ast.Attribute)]


class TestURNResolverScalarFence:
    """``resolve_template_by_urn`` must never reference the scalar template_set surfaces."""

    def test_urn_lane_never_accesses_template_set_attribute(self) -> None:
        _, tree = _resolver_source_and_tree()
        urn_lane = _find_function(tree, _URN_LANE_FUNCTION)

        offenders = [attr for attr in _attribute_names(urn_lane) if attr == _FENCED_ATTRIBUTE]

        assert not offenders, (
            f"{_URN_LANE_FUNCTION} must never reference the scalar "
            "template_set surfaces (resolution.template_set, "
            "MissionTypeProfile.template_set, doctrine.template_set) per "
            f"C-002. Found {len(offenders)} attribute access(es)."
        )

    def test_urn_lane_source_text_never_mentions_template_set_literal(self) -> None:
        """Belt-and-braces textual check alongside the AST check above.

        Guards against any future string-keyed / ``getattr`` access to the
        scalar that would not surface as an ``ast.Attribute`` node.
        """
        source, tree = _resolver_source_and_tree()
        urn_lane = _find_function(tree, _URN_LANE_FUNCTION)

        segment = ast.get_source_segment(source, urn_lane)
        assert segment is not None, f"Could not extract source for {_URN_LANE_FUNCTION}"
        assert _FENCED_ATTRIBUTE not in segment

    def test_name_lane_still_owns_the_scalar_reference(self) -> None:
        """Sanity check: the fence targets the NEW lane, not the whole module.

        Lane 1 (``resolve_configured_template``, the name-based creation
        path) is untouched by WP07 and must keep legitimately reading
        ``resolved_mission_type.template_set`` -- proving this test would
        catch a real regression rather than passing vacuously because
        nothing in the module reads the scalar anymore.
        """
        _, tree = _resolver_source_and_tree()
        name_lane = _find_function(tree, _NAME_LANE_FUNCTION)

        assert _FENCED_ATTRIBUTE in _attribute_names(name_lane), (
            f"{_NAME_LANE_FUNCTION} (Lane 1) should still read "
            f"resolved_mission_type.{_FENCED_ATTRIBUTE} unchanged; its "
            "disappearance suggests the two lanes were collapsed."
        )

    def test_urn_lane_converges_on_the_same_stage_two_resolver(self) -> None:
        """The URN lane must delegate through ``resolve_template_by_id`` --
        the doctrine-side seam that itself terminates in the same Stage-2
        five-tier ``resolve_template`` -- rather than re-implementing tier
        precedence locally (which would silently drift from Lane 1).
        """
        _, tree = _resolver_source_and_tree()
        urn_lane = _find_function(tree, _URN_LANE_FUNCTION)

        called_names = {
            child.func.id
            for child in ast.walk(urn_lane)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        assert "resolve_template_by_id" in called_names
