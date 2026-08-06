"""WP04 commit 0 — the malformed-input fallback pin for degrade sites 1, 2 and 3.

Mission ``meta-fail-closed-3162-01KZ7FSQ``, census rows 1, 2 and 3. Row 13
(``specify_cli.upgrade.feature_meta.load_feature_meta``) is pinned by the twin
file ``tests/upgrade/test_wp04_row13_load_feature_meta_fallback.py``.

Why this file exists, and why it must not be "simplified"
--------------------------------------------------------
These tests are the **green -> red -> green sandwich** that makes this work
package's charter ATDD exception *checkable by re-checkout* rather than merely
asserted:

* **GREEN at baseline.** The malformed -> sentinel degrade already works, which
  is exactly what ``NFR-003`` asserts must be preserved. A base-red here is
  forbidden by ``D4=(a)``: it would pin a behaviour *change*.
* **RED on commit 1 (routing only).** Routing these reads onto
  ``specify_cli.core.paths.load_meta_fail_closed`` changes the exception a
  corrupt ``meta.json`` produces from ``ValueError`` to
  :class:`~specify_cli.core.paths.MissionMetaReadError`, whose MRO is
  ``RuntimeError -> Exception -> BaseException -> object`` -- it is deliberately
  **not** a ``ValueError`` (``core/paths.py:506``,
  ``class MissionMetaReadError(RuntimeError)``). The typed error therefore
  escapes each site's ``except ValueError`` and these tests fail. That escape is
  ``FR-002``'s red, and it exists at a named SHA rather than as a hand-rolled
  scratch traceback.
* **GREEN again on commit 2 (handlers only).** Each ``except`` gains
  ``MissionMetaReadError`` and the observable fallback returns byte-identical.

Because ``NFR-003`` makes a base-red **impossible by construction**, the red
lives on an *intermediate commit*. Squashing this commit into the routing commit
destroys the only red ``FR-002`` has -- measured: no pre-existing test in
``tests/mission_runtime`` or ``tests/upgrade`` drives these sites with corrupt
JSON, and the absent/valid arms are unchanged (``allow_missing=True`` is
hard-coded at ``core/paths.py:676``). Do not fold, squash, or ``xfail`` these.

Each test drives a **real corrupt ``meta.json`` on disk** through the site's own
entry point. Nothing is patched -- neither ``load_meta`` nor
``load_meta_fail_closed`` -- because a patched reader would pin the mock's
behaviour rather than the site's arm.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime.resolution import (
    _mid8_from_primary_meta,
    _resolve_coordination_branch,
    _resolve_mission_id,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

#: Truncated, syntactically invalid JSON -- a REAL corrupt file, not a stub.
_MALFORMED_META = '{"mission_id":'

_MISSION_ID = "01KWP04DEGRADEPIN7X9QZTBVK"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "wp04-degrade-fallback-pin"
#: The COMPOSED handle (``<human-slug>-<mid8>``) is the only form that reaches
#: the corrupt file. Bare mid8, full ULID and bare human slug are canonicalized
#: through an index that skips directories with unreadable meta, so they never
#: read it at all and the degrade arm would never be exercised.
_COMPOSED_HANDLE = f"{_HUMAN_SLUG}-{_MID8}"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _make_primary_root(tmp_path: Path, meta_text: str | None) -> Path:
    """A real git project root whose sole mission carries *meta_text*.

    ``meta_text=None`` writes no ``meta.json`` at all (the absent arm).
    """
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "wp04-degrade@example.test")
    _git(root, "config", "user.name", "WP04 Degrade Pin")
    _git(root, "commit", "--allow-empty", "-qm", "init")
    # ``.kittify/`` is the spec-kitty project-root marker. Without it resolution
    # fails earlier, on PROJECT_ROOT_NOT_FOUND, and the test would be red for a
    # fixture reason rather than for the arm under test.
    (root / ".kittify").mkdir()
    feature_dir = root / "kitty-specs" / _COMPOSED_HANDLE
    feature_dir.mkdir(parents=True)
    if meta_text is not None:
        (feature_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    # spec.md keeps the directory a valid detection candidate.
    (feature_dir / "spec.md").write_text("# degrade pin\n", encoding="utf-8")
    return root


@pytest.fixture
def malformed_primary_root(tmp_path: Path) -> Path:
    """Project root whose sole mission has a genuinely corrupt ``meta.json``."""
    return _make_primary_root(tmp_path, _MALFORMED_META)


def test_row1_mid8_from_primary_meta_degrades_to_empty_string(
    malformed_primary_root: Path,
) -> None:
    """Census row 1: ``_mid8_from_primary_meta`` -> ``""`` on malformed meta.

    Site: ``src/mission_runtime/resolution.py:509`` (read),
    ``:514`` (handler). Sentinel is the empty string and is **constant** -- it
    is a literal, never derived from file content, so a corrupt file cannot
    produce a plausible-but-wrong mid8.
    """
    result = _mid8_from_primary_meta(malformed_primary_root, _COMPOSED_HANDLE)

    assert result == "", (
        "row 1 degrade broken: _mid8_from_primary_meta "
        "(src/mission_runtime/resolution.py:509, handler :514) must return the "
        f'empty-string sentinel on a malformed meta.json, got {result!r}'
    )


def test_row2_resolve_coordination_branch_degrades_to_none(
    malformed_primary_root: Path,
) -> None:
    """Census row 2: ``_resolve_coordination_branch`` -> ``None`` on malformed meta.

    Site: ``src/mission_runtime/resolution.py:852`` (read), ``:853`` (handler).
    Sentinel ``None`` is **constant** -- a literal, never derived from the file.
    """
    result = _resolve_coordination_branch(malformed_primary_root, _COMPOSED_HANDLE)

    assert result is None, (
        "row 2 degrade broken: _resolve_coordination_branch "
        "(src/mission_runtime/resolution.py:852, handler :853) must return None "
        f"on a malformed meta.json, got {result!r}"
    )


def test_row3_resolve_mission_id_degrades_to_legacy_sentinel(
    malformed_primary_root: Path,
) -> None:
    """Census row 3: ``_resolve_mission_id`` -> ``legacy-<slug>`` on malformed meta.

    Site: ``src/mission_runtime/resolution.py:1107`` (read), ``:1108``
    (handler), sentinel composed at ``:1114``.

    The sentinel is **constant with respect to the file**: ``f"legacy-{mission_slug}"``
    interpolates the *caller's own argument*, and ``meta`` is ``None`` on this
    path, so no value is ever read out of the corrupt file. ``wps.yaml``'s T021
    text asserts the opposite ("derived from the malformed file"); that claim is
    wrong and this assertion is what disproves it.
    """
    result = _resolve_mission_id(malformed_primary_root, _COMPOSED_HANDLE)

    assert result == f"legacy-{_COMPOSED_HANDLE}", (
        "row 3 degrade broken: _resolve_mission_id "
        "(src/mission_runtime/resolution.py:1107, handler :1108, sentinel :1114) "
        f"must return the legacy-<slug> sentinel on a malformed meta.json, got {result!r}"
    )


def test_absent_and_valid_arms_are_untouched_by_the_malformed_pin(tmp_path: Path) -> None:
    """The other two input shapes, so a malformed-only pin cannot hide a regression.

    ``NFR-003`` requires all three input shapes at each site. The malformed arm
    is pinned by the three tests above; this one pins **absent** and **valid**
    for the same three sites, which is what stops a routing change from silently
    altering the absent-file arm while the malformed assertions stay green.
    """
    absent_root = _make_primary_root(tmp_path / "absent", None)
    assert _mid8_from_primary_meta(absent_root, _COMPOSED_HANDLE) == ""
    assert _resolve_coordination_branch(absent_root, _COMPOSED_HANDLE) is None
    assert _resolve_mission_id(absent_root, _COMPOSED_HANDLE) == f"legacy-{_COMPOSED_HANDLE}"

    valid_root = _make_primary_root(
        tmp_path / "valid",
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mid8": _MID8,
                "mission_slug": _HUMAN_SLUG,
                "coordination_branch": "kitty/coord-wp04-degrade-pin",
            }
        ),
    )
    assert _mid8_from_primary_meta(valid_root, _COMPOSED_HANDLE) == _MID8
    assert _resolve_coordination_branch(valid_root, _COMPOSED_HANDLE) == "kitty/coord-wp04-degrade-pin"
    assert _resolve_mission_id(valid_root, _COMPOSED_HANDLE) == _MISSION_ID
