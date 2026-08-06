"""WP04 commit 0 — the malformed-input fallback pin for degrade site 13.

Mission ``meta-fail-closed-3162-01KZ7FSQ``, census row 13:
``specify_cli.upgrade.feature_meta.load_feature_meta``
(``src/specify_cli/upgrade/feature_meta.py:42`` read, ``:43`` handler).
Rows 1, 2 and 3 are pinned by the twin file
``tests/mission_runtime/test_wp04_degrade_site_fallbacks.py``.

Why this file exists, and why it must not be "simplified"
--------------------------------------------------------
This is part of the **green -> red -> green sandwich** that makes this work
package's charter ATDD exception *checkable by re-checkout*:

* **GREEN at baseline** -- the malformed -> ``None`` degrade already works,
  which is what ``NFR-003`` asserts must be preserved. A base-red is forbidden
  by ``D4=(a)``.
* **RED on commit 1 (routing only)** -- routing this read onto
  ``specify_cli.core.paths.load_meta_fail_closed`` makes a corrupt
  ``meta.json`` raise :class:`~specify_cli.core.paths.MissionMetaReadError`,
  a ``RuntimeError`` subclass (``core/paths.py:506``) and deliberately **not**
  a ``ValueError``, so it escapes the ``except ValueError`` at ``:43``. That
  escape is ``FR-002``'s red.
* **GREEN again on commit 2 (handlers only)** -- the ``except`` gains
  ``MissionMetaReadError`` and the observable fallback is byte-identical.

``NFR-003`` makes a base-red impossible by construction, so the red lives on an
*intermediate commit*. Squashing this commit into the routing commit destroys
the only red ``FR-002`` has. Do not fold, squash, or ``xfail`` this.

The test drives a **real corrupt ``meta.json`` on disk** through the public
entry point; nothing is patched, because a patched reader would pin the mock
rather than the site's own arm.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.upgrade.feature_meta import load_feature_meta

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

#: Truncated, syntactically invalid JSON -- a REAL corrupt file, not a stub.
_MALFORMED_META = '{"mission_id":'


def test_row13_load_feature_meta_degrades_to_none_on_malformed(tmp_path: Path) -> None:
    """Census row 13: ``load_feature_meta`` -> ``None`` on a malformed ``meta.json``.

    The sentinel ``None`` is **constant** -- a literal, never derived from file
    content, so a corrupt file cannot yield a plausible-but-wrong mapping.

    ``feature_meta.py`` is a pure absorb-adapter: its own docstring at ``:33-40``
    documents its purpose as converting ``ValueError`` to ``None``. Commit 2
    updates that sentence, because routing makes it false.
    """
    mission_dir = tmp_path / "kitty-specs" / "wp04-row13-pin"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(_MALFORMED_META, encoding="utf-8")

    result = load_feature_meta(mission_dir)

    assert result is None, (
        "row 13 degrade broken: load_feature_meta "
        "(src/specify_cli/upgrade/feature_meta.py:42, handler :43) must return "
        f"None on a malformed meta.json, got {result!r}"
    )


def test_row13_absent_and_valid_arms_are_untouched(tmp_path: Path) -> None:
    """The other two input shapes for row 13 (``NFR-003`` needs all three).

    ``load_meta(feature_dir)`` takes the canonical defaults
    ``allow_missing=True, on_malformed="raise"``
    (``src/specify_cli/mission_metadata.py:280-285``), so
    ``load_meta_fail_closed(feature_dir)`` is an exact 1:1 swap **including the
    absent-file arm**. This test is what proves the absent arm did not move.
    """
    absent_dir = tmp_path / "absent"
    absent_dir.mkdir()
    assert load_feature_meta(absent_dir) is None

    valid_dir = tmp_path / "valid"
    valid_dir.mkdir()
    payload = {"mission_id": "01KWP04ROW13PIN7X9QZTBVKMN", "mission_slug": "wp04-row13-pin"}
    (valid_dir / "meta.json").write_text(json.dumps(payload), encoding="utf-8")
    assert load_feature_meta(valid_dir) == payload
