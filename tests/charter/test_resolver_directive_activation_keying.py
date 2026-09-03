"""#3816 sibling — the gated ``DoctrineService.directives`` property must
reconcile the two directive identity spaces.

``config.yaml`` stores ``activated_directives`` as file-stem **slugs**
(``025-boy-scout-rule``), exactly as the ``--json`` surface advertises them,
while the ``DirectiveRepository`` keys its items by the canonical model
``id`` (``DIRECTIVE_025``). The gated property builds ``{item.id: item}`` and
membership-tests each key against ``activated_directives``. Without
normalizing the two spaces onto one form, EVERY directive is silently
dropped whenever activation is configured — the same slug-vs-``DIRECTIVE_NNN``
root cause as the ``--include directive:<id>`` selector bug (#3816), at a
distinct call site (``charter.activation.resolver.DoctrineService.directives``).

This is the sole gated kind affected: tactics/styleguides/etc. carry an
``id`` that already equals their slug, so their activated set and their item
keys coincide. Directives are the one kind where the two diverge.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from charter.activation.pack_context import PackContext
from charter.activation.resolver import DoctrineService

pytestmark = pytest.mark.fast


def _directive(directive_id: str) -> MagicMock:
    item = MagicMock()
    item.id = directive_id
    return item


def _ctx_activating_slugs(repo_root: Path, slugs: frozenset[str]) -> PackContext:
    """A hermetic PackContext activating directives by their file-stem slug,
    the exact shape ``PackContext.from_config`` reads out of ``config.yaml``.
    """
    return PackContext(
        activated_kinds=frozenset({"directives"}),
        activated_mission_types=frozenset({"software-dev"}),
        pack_roots=(),
        org_pack_names=(),
        repo_root=repo_root,
        activated_directives=slugs,
    )


def test_slug_activated_directives_survive_the_gate(tmp_path: Path) -> None:
    boy_scout = _directive("DIRECTIVE_025")
    architecture = _directive("DIRECTIVE_001")
    inner = MagicMock()
    inner.directives.list_all.return_value = [boy_scout, architecture]

    ctx = _ctx_activating_slugs(
        tmp_path,
        frozenset({"025-boy-scout-rule", "001-architectural-integrity-standard"}),
    )

    gated = DoctrineService(inner, pack_context=ctx).directives

    # The activated directives resolve, keyed by their canonical id.
    assert set(gated) == {"DIRECTIVE_025", "DIRECTIVE_001"}
    assert gated["DIRECTIVE_025"] is boy_scout
    assert gated["DIRECTIVE_001"] is architecture


def test_gate_still_drops_non_activated_directives(tmp_path: Path) -> None:
    # Non-vacuity: the gate must still narrow. Activate only one slug and
    # confirm the other directive is excluded — otherwise the test above
    # could pass on a gate that had simply stopped filtering.
    boy_scout = _directive("DIRECTIVE_025")
    architecture = _directive("DIRECTIVE_001")
    inner = MagicMock()
    inner.directives.list_all.return_value = [boy_scout, architecture]

    ctx = _ctx_activating_slugs(tmp_path, frozenset({"025-boy-scout-rule"}))

    gated = DoctrineService(inner, pack_context=ctx).directives

    assert set(gated) == {"DIRECTIVE_025"}


def test_canonical_form_in_activated_set_also_resolves(tmp_path: Path) -> None:
    # An activated set already in canonical DIRECTIVE_NNN form must keep
    # working — the fix normalizes both sides, it does not swap one broken
    # keyspace for another.
    boy_scout = _directive("DIRECTIVE_025")
    inner = MagicMock()
    inner.directives.list_all.return_value = [boy_scout]

    ctx = _ctx_activating_slugs(tmp_path, frozenset({"DIRECTIVE_025"}))

    gated = DoctrineService(inner, pack_context=ctx).directives

    assert set(gated) == {"DIRECTIVE_025"}
