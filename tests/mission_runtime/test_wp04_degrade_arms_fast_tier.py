"""WP04 — the two routed ``except`` arms of ``mission_runtime.resolution``, at the FAST tier.

Mission ``meta-fail-closed-3162-01KZ7FSQ``. Twin of the integration-tier pins in
``test_wp04_degrade_site_fallbacks.py`` (row 1 / row 3) and
``test_wp04_sc007_guard_and_handler_contract.py`` (SC-007 a).

Why a SECOND file rather than an extra case in either twin
----------------------------------------------------------
Those twins carry ``pytest.mark.integration`` + ``pytest.mark.git_repo`` (they
``git init`` a real repo per case), which is the correct tier for what they do —
but it puts them in the ``integration-tests-core-misc (misc)`` shard, and that
job's ``if:`` requires ``pull_request.draft == false`` (or a ``ci:full`` /
``ready-for-ci`` label). On a DRAFT PR the job is skipped, its
``coverage-integration-core-misc-misc.xml`` is never uploaded, and the
``diff-coverage`` critical-path gate therefore scores these two ``except`` lines
as uncovered even though they are exercised. Measured on PR #3247 run
31137786167: ``integration-tests-core-misc`` skipped; 23 coverage reports
consumed, none of them ``coverage-integration-core-misc-*``; gate output
``src/mission_runtime/resolution.py (77.8%): Missing lines 545,1156``.

``tests/mission_runtime`` is ALSO selected by ``fast-tests-core-misc``'s
``core-misc`` shard (``paths: ''``, and its ignore list does not ignore this
root), which runs ``-m "fast and not windows_ci and not regression"`` with
``--cov=mission_runtime`` and runs on draft PRs. So the honest fix is a
``fast``-marked file: nothing here forks a subprocess, touches ``git``, or
patches a reader — ``get_main_repo_root`` falls through to the given path when
``.git`` is absent, so both arms are reachable from a bare ``tmp_path``. Same
tier and same rationale as the sibling ``test_write_target_degrade.py``.

Re-marking the twins ``fast`` instead would be the wrong fix: they really do
need a git repo, and the CI comment on that ``--cov=mission_runtime`` line
already rules that widening a file's markers away from its correct tier is not
how this repo buys instrumentation.
"""

from __future__ import annotations

import traceback
from pathlib import Path

import pytest

from mission_runtime.resolution import _mid8_from_primary_meta, _resolve_mission_id
from specify_cli.core.paths import MissionMetaReadError, load_meta_fail_closed
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    _compose_primary_feature_dir,
)

# Pure-logic, tmp_path-only, no subprocess/git — same tier as the sibling
# ``tests/mission_runtime/test_write_target_degrade.py``. This marker is what
# routes the file into a coverage report the diff-coverage gate actually
# consumes; see the module docstring.
pytestmark = [pytest.mark.fast]

#: Truncated, syntactically invalid JSON — a REAL corrupt file, not a stub. No
#: reader is patched anywhere in this module: a patched ``load_meta_fail_closed``
#: would pin the mock's behaviour rather than the arm's.
_MALFORMED_META = '{"mission_id":'

_MISSION_ID = "01KWP04FASTTIERARM7X9QZTB"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "wp04-fast-tier-degrade-arm"
#: The COMPOSED handle (``<human-slug>-<mid8>``) is the only form that reaches
#: the corrupt file: bare mid8 / full ULID / bare human slug are canonicalized
#: through an index that SKIPS directories with unreadable meta, so they never
#: read it and the arm would never be entered.
_COMPOSED_HANDLE = f"{_HUMAN_SLUG}-{_MID8}"

#: Every shape ``assert_safe_path_segment`` rejects as a traversal risk.
_UNSAFE_HANDLES = ["..evil", "a..b", ".hidden", "foo/bar", "evil/../x"]


def _primary_root(tmp_path: Path) -> Path:
    """A bare project root: ``.kittify`` marker + ``kitty-specs/``, no git.

    ``.kittify`` is the spec-kitty project-root marker; without it resolution
    fails earlier on ``PROJECT_ROOT_NOT_FOUND`` and a test would be red for a
    fixture reason rather than for the arm under test.
    """
    root = tmp_path / "repo"
    (root / ".kittify").mkdir(parents=True)
    (root / "kitty-specs").mkdir()
    return root


# ---------------------------------------------------------------------------
# resolution.py — ``_mid8_from_primary_meta``'s ``except (ValueError,
# MissionMetaReadError)`` tuple. Both limbs, because the tuple is the contract.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unsafe_handle", _UNSAFE_HANDLES)
def test_traversal_valueerror_limb_degrades_mid8_to_empty_string(
    tmp_path: Path, unsafe_handle: str
) -> None:
    """The traversal ``ValueError`` limb: unsafe segment -> ``""``, never a raise.

    This is the assertion that dies if the handler is narrowed to
    ``except MissionMetaReadError`` alone. **Do not rewrite the final assertion
    as ``pytest.raises(ValueError)`` around ``_mid8_from_primary_meta``** — that
    is the cheat the in-code comment names: it is green *after* the narrowing,
    so it would report the behaviour intact while the degrade was deleted.

    The two provenance assertions above it are not decoration. They pin that a
    genuine ``ValueError`` still comes out of ``_compose_primary_feature_dir``
    (via ``assert_safe_path_segment``) for this input, so the outcome assertion
    cannot quietly turn into a no-op if the traversal guard is ever relaxed and
    ``""`` starts arriving down the ordinary ``if not meta`` path instead.
    """
    root = _primary_root(tmp_path)

    with pytest.raises(ValueError) as excinfo:
        _compose_primary_feature_dir(root, unsafe_handle)
    frames = [frame.name for frame in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "_compose_primary_feature_dir" in frames and "assert_safe_path_segment" in frames, (
        "provenance lost: the traversal ValueError this arm's ValueError limb exists to "
        f"catch no longer originates in _compose_primary_feature_dir/assert_safe_path_segment: {frames}"
    )
    assert not isinstance(excinfo.value, MissionMetaReadError), (
        "the traversal guard now raises MissionMetaReadError, so this case no longer "
        "exercises the ValueError limb and a narrowed handler would go undetected"
    )

    result = _mid8_from_primary_meta(root, unsafe_handle)

    assert result == "", (
        "SC-007 violated: _mid8_from_primary_meta must keep degrading an unsafe path "
        f"segment to the empty string, got {result!r}. A handler narrowed to "
        "`except MissionMetaReadError` raises ValueError here instead of returning ''."
    )


def test_malformed_meta_limb_degrades_mid8_to_empty_string(tmp_path: Path) -> None:
    """The ``MissionMetaReadError`` limb of the same tuple: corrupt meta -> ``""``.

    Pinned at this tier alongside the ``ValueError`` limb so the arm is not half
    covered: a tuple whose second member is only ever exercised by a job the
    gate does not consume is, to the gate, not exercised at all.
    """
    root = _primary_root(tmp_path)
    _write_corrupt_mission(root)

    result = _mid8_from_primary_meta(root, _COMPOSED_HANDLE)

    assert result == "", (
        "NFR-003 violated: _mid8_from_primary_meta must return the empty-string "
        f"sentinel on a malformed meta.json, got {result!r}"
    )


# ---------------------------------------------------------------------------
# resolution.py — ``_resolve_mission_id``'s ``except MissionMetaReadError``.
# ---------------------------------------------------------------------------


def _write_corrupt_mission(root: Path) -> Path:
    """Materialize the sole mission dir carrying a genuinely corrupt ``meta.json``."""
    mission_dir = root / "kitty-specs" / _COMPOSED_HANDLE
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(_MALFORMED_META, encoding="utf-8")
    # spec.md keeps the directory a valid detection candidate.
    (mission_dir / "spec.md").write_text("# wp04 fast-tier degrade arm\n", encoding="utf-8")
    return mission_dir


def test_malformed_meta_degrades_mission_id_to_legacy_sentinel(tmp_path: Path) -> None:
    """Corrupt ``meta.json`` -> ``legacy-<slug>``; the arm must not become a crash.

    ``MissionMetaReadError`` is a ``RuntimeError`` subclass (``core/paths.py``),
    deliberately **not** a ``ValueError`` — which is exactly why this ``except``
    has to name it. The middle assertion pins that MRO fact directly, so if the
    class is ever re-parented under ``ValueError`` this test says so instead of
    silently passing for a new reason.

    The first assertion pins that the read really lands on the corrupt file: the
    canonicalizing index skips dirs with unreadable meta for the non-composed
    handle forms, so a handle typo here would produce a green test that never
    entered the arm at all.
    """
    root = _primary_root(tmp_path)
    mission_dir = _write_corrupt_mission(root)

    primary_dir = _compose_primary_feature_dir(
        root, _canonicalize_primary_read_handle(root, _COMPOSED_HANDLE)
    )
    assert primary_dir == mission_dir, (
        "fixture drift: the resolved primary dir is not the one carrying the corrupt "
        f"meta.json ({primary_dir} != {mission_dir}), so the read never reaches the arm"
    )

    with pytest.raises(MissionMetaReadError) as excinfo:
        load_meta_fail_closed(primary_dir)
    assert not isinstance(excinfo.value, ValueError), (
        "MissionMetaReadError is now a ValueError; this arm's reason for naming it "
        "explicitly (RuntimeError subclass, NFR-003) no longer holds"
    )

    result = _resolve_mission_id(root, _COMPOSED_HANDLE)

    assert result == f"legacy-{_COMPOSED_HANDLE}", (
        "NFR-003 violated: _resolve_mission_id must degrade a malformed meta.json to "
        f"the legacy-<slug> sentinel, got {result!r}. With the `except "
        "MissionMetaReadError` arm deleted this raises instead of returning."
    )
