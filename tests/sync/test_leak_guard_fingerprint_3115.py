"""FR-007 leak-guard fingerprint regression witness (#3115).

``tests/sync/conftest.py``'s ``_content_fingerprint`` helper fingerprints
arbitrary class instances (the "everything else" branch, see that
function's own docstring) as
``(type(value).__name__, id(value), repr(value))`` -- identity first,
repr() second. The ``id(value)`` component is the mission's headline
self-fix: without it, two distinct ``SyncRuntime`` instances collide,
because ``SyncRuntime``'s generated ``repr()`` reduces to two booleans
(7 of its 9 fields are ``repr=False``) and is therefore identical for
any two unstarted instances.

The only pre-existing bite-test for this helper
(``test_leak_guard_probe_3115.py``) mutates a ``set``
(``ALLOWED_CALL_SITES``), which routes through the ``list``/``set``/
``frozenset``/``tuple`` repr-only branch -- it never exercises the
class-instance / ``id()`` branch at all. Deleting ``id(value)`` from
that branch's tuple reds nothing today. This file closes that gap: it
witnesses the ``id()`` branch directly, using two distinct *unstarted*
``SyncRuntime()`` instances (constructing one has no side effects --
no ``__post_init__``, no thread/service start; ``start()`` is never
called here).
"""

from __future__ import annotations

import pytest

from specify_cli.sync.runtime import SyncRuntime
from tests.sync.conftest import _content_fingerprint

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_distinct_unstarted_sync_runtime_instances_fingerprint_differently() -> None:
    """Two distinct unstarted ``SyncRuntime()`` instances must NOT collide.

    Both instances share the same two-boolean repr
    (``SyncRuntime(_build_registered=False, started=False)``), so a
    repr()-only fingerprint would wrongly treat a
    ``SyncRuntime -> SyncRuntime`` replacement (a genuine leak: the
    watched slot now points at a *different* object) as "no change".
    ``id()`` is what discriminates them.
    """
    first = SyncRuntime()
    second = SyncRuntime()

    assert repr(first) == repr(second), (
        "test premise broken: SyncRuntime's own repr() no longer collides "
        "for two unstarted instances -- this test's assumption needs revisiting"
    )
    assert first is not second

    assert _content_fingerprint(first) != _content_fingerprint(second), (
        "two distinct SyncRuntime instances fingerprinted identically -- the "
        "id() component of _content_fingerprint's class-instance branch is "
        "missing or broken, which is exactly the SyncRuntime -> SyncRuntime "
        "leak this guard exists to catch (see conftest.py's own measured "
        "22-node control)"
    )


def test_same_sync_runtime_instance_fingerprints_identically_to_itself() -> None:
    """A value compared against itself (the guard's actual before/after use)
    must fingerprint equal -- otherwise the guard would false-positive on
    every unchanged watched global.
    """
    runtime = SyncRuntime()

    first_fingerprint = _content_fingerprint(runtime)
    second_fingerprint = _content_fingerprint(runtime)
    assert first_fingerprint == second_fingerprint
