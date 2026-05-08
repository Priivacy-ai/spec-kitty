"""OpenAPI snapshot stability test.

Generates the OpenAPI document for the dashboard FastAPI app and asserts it
is byte-identical to the committed snapshot at
``tests/test_dashboard/snapshots/openapi.json``. Any drift fails this test
and points the developer at the refresh procedure documented in
``kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md``.

The test is intentionally strict: catching unintentional schema or route
changes is the whole point. When an OpenAPI change *is* intentional, the
mission's stability contract documents the refresh procedure (regenerate
the snapshot, inspect the diff, obtain reviewer signoff) before committing
the new bytes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "openapi.json"
STABILITY_CONTRACT = (
    "kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/"
    "contracts/openapi-stability.md"
)


def _serialize(spec: dict) -> str:
    """Canonical serialization used for both the snapshot and the comparison."""
    return json.dumps(spec, sort_keys=True, indent=2) + "\n"


def test_openapi_snapshot_matches(tmp_path: Path) -> None:
    """The generated OpenAPI document must match the committed snapshot.

    Failure indicates either an intentional contract change (in which case
    follow the refresh procedure) or unintentional drift (in which case
    revert the change).
    """
    from dashboard.api import create_app

    app = create_app(project_dir=tmp_path, project_token=None)
    actual = _serialize(app.openapi())

    assert SNAPSHOT_PATH.exists(), (
        f"OpenAPI snapshot missing at {SNAPSHOT_PATH}. "
        f"Regenerate per {STABILITY_CONTRACT}."
    )
    expected = SNAPSHOT_PATH.read_text(encoding="utf-8")

    if actual != expected:
        # Surface a focused diff hint without dumping the entire 2k-line spec.
        actual_lines = actual.splitlines()
        expected_lines = expected.splitlines()
        first_diff = None
        for idx, (a, b) in enumerate(zip(actual_lines, expected_lines)):
            if a != b:
                first_diff = (idx + 1, a, b)
                break
        diff_hint = ""
        if first_diff is not None:
            line_no, actual_line, expected_line = first_diff
            diff_hint = (
                f"\nFirst differing line ({line_no}):\n"
                f"  expected: {expected_line!r}\n"
                f"  actual  : {actual_line!r}"
            )
        elif len(actual_lines) != len(expected_lines):
            diff_hint = (
                f"\nLine count differs: actual={len(actual_lines)} "
                f"expected={len(expected_lines)}"
            )

        pytest.fail(
            "OpenAPI snapshot drift detected. If this change is intentional, "
            f"regenerate the snapshot per {STABILITY_CONTRACT} and obtain "
            f"reviewer signoff.{diff_hint}"
        )
