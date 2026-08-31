"""Regression guard: charter compiler reads MOVED built-in kinds from packs/built-in.

Completeness audit for mission ``relocate-builtin-doctrine-packs-01KYT87F``.

The relocation flattened built-in doctrine content out of
``src/charter/offering/<kind>/built-in`` into ``packs/built-in/<kind>``. Every reader of
a MOVED kind must resolve through the shared ``resolve_pack_root("built-in")``
seam. ``compiler._build_references_from_yaml`` had one straggler: the
Python-implementation styleguide read (``compiler.py:867``) still joined onto the
now-emptied ``resolve_doctrine_root() / "styleguides"`` tree, so it would have
silently emitted no styleguide reference post-relocation.

This test exercises the fixed read directly. The styleguide fixture exists ONLY
under a temporary ``packs/built-in`` root (surfaced via ``SPEC_KITTY_PACKS_ROOT``)
and NOT under the src/doctrine tree — so the styleguide reference materializes
only when the read is repointed to the pack root. A regression back to
``doctrine_root`` would find nothing and drop the reference, re-reddening this
test.

Fixture note (mission ``resolution-activation-foundation-01KZ9FKG`` WP02,
charter DIRECTIVE_041 re-pin discipline): ``_template_reference`` (exercised
via ``_build_references_from_yaml`` below) calls
``MissionTemplateRepository.default()``, which resolves
``default_missions_root()`` under this same ``SPEC_KITTY_PACKS_ROOT``. Since
WP02 made ``default_missions_root()`` correctly honor ``SPEC_KITTY_PACKS_ROOT``
(previously it silently ignored the var and always resolved the real
installed/editable missions tree instead), a synthetic PACKS_ROOT that carries
only ``built-in/styleguides/`` now fails closed with ``MissionsRootNotFound``
on the missing ``missions`` leaf -- correct new behavior, not a bug. Each
fixture below adds an empty ``built-in/missions/`` stub alongside the
styleguide fixture so ``MissionTemplateRepository.default()`` resolves (an
empty directory is sufficient: ``get_mission_config`` returns ``None`` for an
absent ``mission.yaml`` and ``_template_reference`` falls back to a display-only
``{"name": mission}`` in that case) and this test keeps exercising what it
always intended -- the styleguide read, not the missions fail-closed path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.catalog import resolve_doctrine_root
from charter.compiler import _build_references_from_yaml
from charter.interview import CharterInterview

pytestmark = [pytest.mark.unit]

_STYLEGUIDE_YAML = """\
id: python-implementation
title: Python Implementation Styleguide
summary: Write idiomatic, type-safe Python.
principles:
  - Prefer pathlib over os.path.
"""


def _python_interview() -> CharterInterview:
    return CharterInterview(
        mission="software-dev",
        profile="default",
        answers={"languages_frameworks": "Python 3.12"},
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
    )


def test_python_styleguide_reference_reads_from_packs_built_in(
    tmp_path: Path, monkeypatch
) -> None:
    """The Python styleguide reference resolves from packs/built-in, not src/doctrine."""
    packs_root = tmp_path / "packs"
    styleguide_path = packs_root / "built-in" / "styleguides" / "python-implementation.styleguide.yaml"
    styleguide_path.parent.mkdir(parents=True)
    styleguide_path.write_text(_STYLEGUIDE_YAML, encoding="utf-8")

    # MissionTemplateRepository.default() also resolves under this same
    # SPEC_KITTY_PACKS_ROOT (WP02) -- an empty missions/ leaf is sufficient
    # fail-closed satisfaction; see module docstring "Fixture note".
    (packs_root / "built-in" / "missions").mkdir(parents=True)

    # The fixture must exist ONLY in the pack root — never in the src/doctrine
    # tree — so this test can only pass by reading the relocated home. If the
    # emptied tree ever regains this file the guard would weaken silently.
    legacy = resolve_doctrine_root() / "styleguides" / "python-implementation.styleguide.yaml"
    assert not legacy.exists(), (
        "The src/doctrine styleguide tree unexpectedly holds the relocated file; "
        "this regression guard is no longer discriminating."
    )

    monkeypatch.setenv("SPEC_KITTY_PACKS_ROOT", str(packs_root))

    references = _build_references_from_yaml(
        mission="software-dev",
        template_set="software-dev",
        interview=_python_interview(),
        paradigms=[],
        directives=[],
    )

    styleguides = [ref for ref in references if ref.kind == "styleguide"]
    assert [ref.id for ref in styleguides] == ["STYLEGUIDE:python-implementation"], (
        "The Python styleguide reference did not materialize from packs/built-in — "
        "the built-in styleguide read regressed to the emptied src/doctrine tree."
    )
    assert styleguides[0].title == "Python Implementation Styleguide"


def test_non_python_interview_emits_no_styleguide_reference(
    tmp_path: Path, monkeypatch
) -> None:
    """Guard against a false positive: without a Python hint, no styleguide is read."""
    packs_root = tmp_path / "packs"
    styleguide_path = packs_root / "built-in" / "styleguides" / "python-implementation.styleguide.yaml"
    styleguide_path.parent.mkdir(parents=True)
    styleguide_path.write_text(_STYLEGUIDE_YAML, encoding="utf-8")

    # MissionTemplateRepository.default() also resolves under this same
    # SPEC_KITTY_PACKS_ROOT (WP02); see module docstring "Fixture note".
    (packs_root / "built-in" / "missions").mkdir(parents=True)

    monkeypatch.setenv("SPEC_KITTY_PACKS_ROOT", str(packs_root))

    interview = CharterInterview(
        mission="software-dev",
        profile="default",
        answers={"languages_frameworks": "Rust"},
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
    )

    references = _build_references_from_yaml(
        mission="software-dev",
        template_set="software-dev",
        interview=interview,
        paradigms=[],
        directives=[],
    )

    assert not [ref for ref in references if ref.kind == "styleguide"]
