"""Negatives the census must **not** flag, plus the ``in``-form n=0 case.

Control fixture for ``scripts/patch_seam_census.py`` (WP03 / SC-015). Not named
``test_*``, so pytest never collects it.

Three distinct negatives:

1. ``case_own_module_patch`` — patches a symbol **defined in** the module it
   names. This is the *correct* idiom and lands in the ``own_module`` bucket;
   flagging it is the 97.7% over-breadth FR-005's literal wording would cause.
2. ``case_monotonic_only`` — patches a reach-through seam that is **not** a
   sleep seam, so the function must not count as a sleep node.
3. ``case_membership_without_cardinality`` — reads the mock, but asserts
   **membership**, not cardinality. It must report ``n=0``. Deriving ``n`` from
   the length of the printed delay list would report ``n=1`` here and make
   SC-002 fakeable.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


@patch("specify_cli.tracker.saas_client.SaaSTrackerClient")
def case_own_module_patch(mock_client: MagicMock) -> None:
    """Own-module patch — the correct idiom. Must not be flagged."""
    assert mock_client.call_count == 0


@patch("specify_cli.tracker.saas_client.time.monotonic")
def case_monotonic_only(mock_monotonic: MagicMock) -> None:
    """A monotonic-only node. Reach-through, but not a *sleep* seam."""
    mock_monotonic.side_effect = [0.0, 301.0]
    assert mock_monotonic.call_count == 0


@patch("specify_cli.tracker.saas_client.time.sleep")
def case_membership_without_cardinality(mock_sleep: MagicMock) -> None:
    """Reads the mock but asserts no cardinality — must report ``n=0``."""
    mock_sleep(3.0)
    assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]
