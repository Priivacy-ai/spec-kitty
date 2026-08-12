"""Red-first reproduction of #3334 — a failed upgrade strips ``schema_version``
from ``.kittify/metadata.yaml``, and the compatibility classifier then treats the
project as pre-3.x ``legacy`` and blocks every non-exempt command, so the tool
cannot recover a project its own failure broke.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3334

Root cause (verified against current source): ``_scan_project``
(``src/specify_cli/compat/planner.py``) maps a *missing* ``schema_version``
UNCONDITIONALLY to ``ProjectState.LEGACY`` and never consults
``migrations.applied``. ``decide`` then answers ``BLOCK_PROJECT_MIGRATION``
(exit 4) for ``LEGACY`` + ``UNSAFE``. The failed-upgrade path removes the
``schema_version`` key without advancing ``version`` or restoring it, so a
project whose ``migrations.applied`` log clearly shows 3.x history is
classified identically to a genuinely pre-3.x project — the repair path is
gated behind exactly the state the failure destroyed.

This drives the REAL production entry point ``plan()`` with a non-exempt
(``UNSAFE``) command against a post-failed-upgrade metadata fixture (version
stamped behind, ``schema_version`` absent, ``migrations.applied`` carrying 3.x
records).

Desired post-fix outcome: a project missing ``schema_version`` but whose
``migrations.applied`` log shows 3.x history is distinguishable from a genuinely
pre-3.x project and is NOT classified ``LEGACY``-blocked — ``plan()`` must not
return ``BLOCK_PROJECT_MIGRATION`` / exit 4, so the project remains recoverable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.compat.planner import Decision, Invocation, plan
from specify_cli.compat.provider import FakeLatestVersionProvider

from tests.specify_cli.compat.test_planner import (
    _INSTALLED,
    _NOW,
    _make_nag_cache_tmp,
    _make_project_root_resolver,
)

pytestmark = pytest.mark.regression

# Post-failed-upgrade metadata: version stamped several releases behind,
# `schema_version` ABSENT (stripped by the failure), but `migrations.applied`
# shows real 3.x history — i.e. this is NOT a genuinely pre-3.x legacy project.
_WEDGED_METADATA = """\
spec_kitty:
  version: "3.0.0"
  initialized_at: "2025-01-01T00:00:00+00:00"
  last_upgraded_at: "2025-06-01T00:00:00+00:00"
migrations:
  applied:
    - id: m_3_0_0_canonical_context
      applied_at: "2025-06-01T00:00:00+00:00"
      result: success
      notes: null
    - id: m_3_2_4_derived_views_gitignore_backfill
      applied_at: "2025-06-01T00:00:00+00:00"
      result: success
      notes: null
"""


def test_missing_schema_version_with_3x_history_is_not_legacy_blocked(
    tmp_path: Path,
) -> None:
    resolver = _make_project_root_resolver(tmp_path, metadata_content=_WEDGED_METADATA)
    # A non-exempt (UNSAFE) command — the wedge fires for any command that is not
    # `upgrade`/`init`; an unregistered command fails closed to UNSAFE.
    inv = Invocation(
        command_path=("spec-kitty-test-unknown-cmd",),
        raw_args=(),
        is_help=False,
        is_version=False,
        flag_no_nag=False,
        env_ci=False,
        stdout_is_tty=True,
    )

    result = plan(
        inv,
        latest_version_provider=FakeLatestVersionProvider(version=_INSTALLED),
        nag_cache=_make_nag_cache_tmp(tmp_path),
        now=_NOW,
        project_root_resolver=resolver,
    )

    # RED today: missing schema_version -> classified LEGACY -> LEGACY + UNSAFE ->
    # BLOCK_PROJECT_MIGRATION (exit 4), even though migrations.applied shows 3.x
    # history. The project its own failed upgrade broke cannot be recovered.
    assert result.decision != Decision.BLOCK_PROJECT_MIGRATION, (
        "a project missing schema_version but carrying 3.x migrations.applied "
        "history must not be classified as pre-3.x legacy and blocked; got "
        f"decision={result.decision}"
    )
    assert result.exit_code != 4, f"expected recoverable (exit != 4), got {result.exit_code}"
