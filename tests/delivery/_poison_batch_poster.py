"""Shared content-aware fake poster for the poison-batch delivery tests (#2736).

Relocated verbatim from :mod:`test_poison_batch_2736` so both that anchor and
:mod:`test_batch_bisection_ordering` import the *same* class off one surface
(no cross-test-module import). Pure relocation — no behaviour change.
"""
from __future__ import annotations

import gzip
import json
from collections.abc import Mapping, Sequence
from typing import Any


class _FakeResponse:
    """Minimal ``requests.Response`` stand-in (same surface as WP06's fixture)."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return self._body


class _AllOrNothingBatchPoster:
    """Content-aware poster that models the server's whole-batch 400 (#2736).

    Decompresses the posted batch body and inspects which events it carries:

    * if a genuinely-invalid event is present, the **whole** batch is rejected with
      HTTP 400 carrying only a top-level ``error`` string (no per-event
      ``details`` granularity) — exactly the all-or-nothing server contract;
    * otherwise every event in the batch is accepted (HTTP 200), and the server's
      idempotency memory maps a repeat ``event_id`` to ``duplicate`` (NFR-003).

    Two **ordered** receipt logs let a test pin isolation *ordering*, not just counts:

    * :attr:`receipt_log` — one entry per POST, the exact ``event_id`` sequence in
      **POST-execution order** (a bisecting path drives the culprit down to a size-1
      POST while innocents POST in later halves);
    * :attr:`accepted_receipts` — each genuinely-accepted (``success``) ``event_id``
      appended on the 200/accept branch, again in **POST-execution order, never input
      order**. Re-posted duplicates are not re-appended, so the accepted multiset holds
      no duplicates (NFR-003).
    """

    def __init__(self, *, invalid_event_ids: Sequence[str], batch_error: str) -> None:
        self._invalid_event_ids = frozenset(invalid_event_ids)
        self._batch_error = batch_error
        self.receipt_log: list[list[str]] = []
        self.accepted_receipts: list[str] = []
        self._accepted_ids: set[str] = set()

    def __call__(
        self, url: str, *, data: bytes, headers: Mapping[str, str], timeout: float
    ) -> _FakeResponse:
        payload = json.loads(gzip.decompress(data).decode("utf-8"))
        ids = [str(event["event_id"]) for event in payload["events"]]
        self.receipt_log.append(list(ids))
        if self._invalid_event_ids & set(ids):
            # Whole-batch 400: top-level error only, no per-event `details`.
            return _FakeResponse(400, {"error": self._batch_error})
        results = []
        for eid in ids:
            if eid in self._accepted_ids:
                results.append({"event_id": eid, "status": "duplicate"})
            else:
                self._accepted_ids.add(eid)
                self.accepted_receipts.append(eid)  # genuine acceptance, POST-order
                results.append({"event_id": eid, "status": "success"})
        return _FakeResponse(200, {"results": results})

    def _singleton_posts(self) -> list[list[str]]:
        """The size-1 POSTs (each isolated a single event), in receipt order.

        Single source of truth for "a POST that isolated one event" — the set-view
        and tuple-view accessors below both derive from this, so the singleton
        predicate (a size-1 batch *is* the isolation contract) lives in one place.
        """
        return [post for post in self.receipt_log if len(post) == 1]  # golden-count: cardinality-is-contract

    def singleton_posts(self) -> list[set[str]]:
        """The size-1 POSTs, as id-sets — where an isolated culprit must land."""
        return [set(post) for post in self._singleton_posts()]

    def singleton_post_tuples(self) -> list[tuple[str, ...]]:
        """The size-1 POSTs, as ordered id-tuples (for repeat/termination checks)."""
        return [tuple(post) for post in self._singleton_posts()]
