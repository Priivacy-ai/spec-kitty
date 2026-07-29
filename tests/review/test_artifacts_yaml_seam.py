"""Byte-stability pin for the #3058 follow-up migration of
``ReviewCycleArtifact.write`` to ``kernel.yaml_io.serialize_mapping``.

``_make_yaml()`` (rt, preserve_quotes=True, default_flow_style=False,
width=4096) is an exact configuration match for
``serialize_mapping``'s defaults. This test proves that match holds for a
representative frontmatter payload — including the optional
affected-files / override fields — with every scalar within the 4096 wrap
width, so the migration in ``src/specify_cli/review/artifacts.py``
(``write()``) is a pure internal seam consolidation with no on-disk byte
change for real review-cycle payloads, not a silent format drift. (The one
input where the two diverge — a scalar that wraps past 4096 columns —
strips non-semantic trailing whitespace the old path left, a strict
improvement, not covered here.)

If this test ever goes red because ``_make_yaml()``'s dump legitimately
diverges from ``serialize_mapping``, that is the signal to REVERT the
``write()`` migration (per the mission instructions), not to "fix" this test.
"""

from __future__ import annotations

from typing import Any

import pytest
from ruamel.yaml import YAML

from kernel.yaml_io import serialize_mapping
from specify_cli.review.artifacts import _make_yaml

pytestmark = pytest.mark.fast


def _dump_with_make_yaml(data: dict[str, Any]) -> bytes:
    from io import StringIO

    yaml = _make_yaml()
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue().encode("utf-8")


def _representative_payloads() -> list[dict[str, Any]]:
    return [
        {
            "affected_files": [],
            "cycle_number": 1,
            "mission_slug": "066-test",
            "reproduction_command": None,
            "reviewed_at": "2026-04-06T14:00:00+00:00",
            "reviewer_agent": "reviewer-renata",
            "verdict": "approved",
            "wp_id": "WP01",
        },
        {
            "affected_files": [
                {"path": "src/kernel/yaml_io.py"},
                {
                    "path": "src/specify_cli/retrospective/writer.py",
                    "line_range": "150-200",
                },
            ],
            "cycle_number": 2,
            "mission_slug": "read-side-seam-primary-primitive-closure-01KYKMMT",
            "reproduction_command": "uv run pytest tests/kernel/test_yaml_io.py -q",
            "reviewed_at": "2026-07-28T09:30:00+00:00",
            "reviewer_agent": "unknown",
            "verdict": "rejected",
            "wp_id": "WP03-ledger-grammar",
            "override_actor": "operator",
            "override_reason": (
                "Reviewer flagged a pre-existing gap unrelated to this change; "
                "confirmed via git blame that the assertion was already broken "
                "on main before this work package branched off."
            ),
        },
    ]


def test_serialize_mapping_matches_make_yaml_byte_for_byte() -> None:
    for data in _representative_payloads():
        old_bytes = _dump_with_make_yaml(data)
        new_bytes = serialize_mapping(data)
        assert new_bytes == old_bytes, (
            f"serialize_mapping diverged from _make_yaml for payload {data!r}:\n"
            f"old={old_bytes!r}\nnew={new_bytes!r}"
        )


def test_serialize_mapping_output_still_parses_identically_to_make_yaml_load() -> None:
    for data in _representative_payloads():
        new_bytes = serialize_mapping(data)
        loaded_via_make_yaml = _make_yaml().load(new_bytes.decode("utf-8"))
        loaded_via_safe = YAML(typ="safe").load(new_bytes.decode("utf-8"))
        assert dict(loaded_via_make_yaml) == data
        assert loaded_via_safe == data
