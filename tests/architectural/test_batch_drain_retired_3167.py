"""Permanence guard: the queue-backed drain in ``sync/batch.py`` stays retired (#3167).

Mission ``chain-b-consent-bypass-3167-01KZ63HK`` deleted ``batch_sync``,
``sync_all_queued_events`` and their callee tree because they could POST queued
events **without traversing a per-project consent decision** — a consent bypass
on a code path no production caller reached. The 33 names watched here are the
frozen dead set from ``contracts/deletion-manifest.md`` §1 (24 first tier +
9 second tier), established over 3905 scanned files.

Why this file exists at all
---------------------------
``tests/architectural/test_no_dead_symbols.py`` does **not** cover this. It keys
on modules that declare ``__all__``, and ``sync/batch.py`` declares none — so
nothing in CI reds when a private is stranded or reintroduced in this module.
This file is the substitute, not a duplicate.

How it is kept honest
---------------------
Three failure modes are each closed by their own test:

* **Reintroduction** — ``test_retired_drain_symbols_are_absent`` names the
  offending symbols in the failure text, so the red is the consequence (which
  name came back) rather than a bare boolean.
* **A vacuous probe** — ``test_live_batch_symbols_are_still_visible`` is the
  positive control. If the AST walk saw nothing (file moved, renamed, emptied,
  or unparsed), the absence assertion above would pass for the wrong reason.
  This test fails instead.
* **A narrowed watch list** — ``test_watch_list_still_matches_the_frozen_manifest``
  pins the tier cardinalities. Quietly dropping a name from ``_RETIRED`` is the
  cheapest way to fake a green here.

``test_no_transmit_primitive_remains_in_batch`` is NFR-001/SC-001 made
permanent: the module went from 4 transmit call sites (3 senders) to zero, and
re-adding one is how the bypass would return.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BATCH = _REPO_ROOT / "src" / "specify_cli" / "sync" / "batch.py"

#: FIRST TIER — no external reference of any kind in ``src/``, ``scripts/`` or
#: ``tests/`` at the mission's base commit. Manifest §1.
_FIRST_TIER = frozenset(
    {
        "DECOMPRESSED_BYTES_SAFETY_FACTOR",
        "HISTORICAL_MISSION_STATE_FORBIDDEN_KEYS",
        "SYNC_INGRESS_LIMITS_TIMEOUT_SECONDS",
        "_body_mentions_missing_private_team",
        "_build_batch_payload",
        "_decompressed_byte_limit",
        "_extract_sync_ingress_limits",
        "_fetch_advertised_sync_ingress_limits",
        "_find_historical_mission_state_keys",
        "_handle_single_oversized_event",
        "_historical_mission_state_rejection",
        "_http_error_category",
        "_http_error_message",
        "_is_oversized_batch_response",
        "_merge_batch_sync_result",
        "_positive_int",
        "_prepare_events_for_ingress",
        "_record_all_events_failed",
        "_retry_limits_from_response",
        "_safe_response_json",
        "_select_events_for_advertised_limits",
        "_should_probe_advertised_limits",
        "_should_stop_sync_loop",
        "_single_oversized_event_result",
    }
)

#: SECOND TIER — dead in ``src/``, held only by the tests retired alongside
#: them. Manifest §1. ``batch_sync`` and ``sync_all_queued_events`` are the two
#: senders the mission is named for.
_SECOND_TIER = frozenset(
    {
        "DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH",
        "MAX_DECOMPRESSED_BYTES_PER_BATCH_CEILING",
        "_current_team_slug",
        "_is_checkout_sync_enabled_for_batch",
        "_parse_error_response",
        "_parse_event_results",
        "_shrink_events_for_retry",
        "batch_sync",
        "sync_all_queued_events",
    }
)

_RETIRED = _FIRST_TIER | _SECOND_TIER

#: ALIVE — must survive the retirement. Manifest §1 ALIVE tier. Four are held by
#: production code (``sync/background.py``, ``sync/diagnose.py``), three by the
#: ``specify_cli.sync`` lazy map, and the rest are derived from those.
#: This set is the positive control's subject, not a second watch list.
_MUST_SURVIVE = frozenset(
    {
        "BatchEventResult",
        "BatchSyncResult",
        "CATEGORY_ACTIONS",
        "ERROR_CATEGORIES",
        "FINAL_SYNC_MAX_ATTEMPTS",
        "FINAL_SYNC_RETRY_BACKOFF_SECONDS",
        "_emit_final_sync_failure_diagnostic",
        "_final_sync_result_error_text",
        "_finalize_exhausted_final_sync",
        "_handle_final_sync_exception",
        "_handle_final_sync_result",
        "_has_final_sync_retry_remaining",
        "_is_failed_final_sync_result",
        "_result_from_final_sync_exception",
        "_should_retry_final_sync_result",
        "_sleep_before_final_sync_retry",
        "categorize_error",
        "format_sync_summary",
        "generate_failure_report",
        "run_final_sync_with_retries",
        "write_failure_report",
    }
)

#: A *transmit primitive* is a ``requests.<verb>`` call or a call to
#: ``request_with_stdlib_fallback_sync``. Manifest §4 measured 4 such call sites
#: at the base commit (``:223``, ``:1125``, ``:1212``, ``:1282``).
_PRIMITIVE_MODULES = frozenset({"requests"})
_PRIMITIVE_FUNCTIONS = frozenset({"request_with_stdlib_fallback_sync"})


def _module() -> ast.Module:
    assert _BATCH.is_file(), f"the guarded module has moved or been deleted: {_BATCH}"
    return ast.parse(_BATCH.read_text(encoding="utf-8"), filename=str(_BATCH))


def _top_level_names(tree: ast.Module) -> set[str]:
    """Every module-level binding: callables, classes and constants."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _transmit_primitive_sites(tree: ast.Module) -> list[str]:
    """``"<primitive> :<line>"`` for every transmit call site in the module."""
    sites: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in _PRIMITIVE_MODULES:
            sites.append(f"{func.value.id}.{func.attr} :{node.lineno}")
        elif isinstance(func, ast.Name) and func.id in _PRIMITIVE_FUNCTIONS:
            sites.append(f"{func.id} :{node.lineno}")
    return sorted(sites)


def test_watch_list_still_matches_the_frozen_manifest() -> None:
    """Narrowing the watch list is the cheapest way to fake a green here.

    The tier sizes are the contract: ``contracts/deletion-manifest.md`` §1 froze
    ``dead=33 (first=24 second=9) alive=21`` over 3905 scanned files. A future
    edit that deletes an inconvenient name from ``_RETIRED`` reds here instead of
    silently shrinking the guard.
    """
    assert len(_FIRST_TIER) == 24, f"manifest §1 froze 24 first-tier names, watching {len(_FIRST_TIER)}"  # golden-count: cardinality-is-contract
    assert len(_SECOND_TIER) == 9, f"manifest §1 froze 9 second-tier names, watching {len(_SECOND_TIER)}"  # golden-count: cardinality-is-contract
    assert len(_MUST_SURVIVE) == 21, f"manifest §1 froze 21 alive names, watching {len(_MUST_SURVIVE)}"  # golden-count: cardinality-is-contract
    assert not (_RETIRED & _MUST_SURVIVE), f"a name cannot be both retired and alive: {sorted(_RETIRED & _MUST_SURVIVE)}"


def test_live_batch_symbols_are_still_visible() -> None:
    """POSITIVE CONTROL for the absence assertions below.

    ``test_retired_drain_symbols_are_absent`` would pass for entirely the wrong
    reason if this file's AST walk returned an empty name set — a moved module, a
    renamed package, or a probe bug. Establishing that the walk still finds all
    21 production-alive symbols is what makes the absence result evidence rather
    than silence.
    """
    names = _top_level_names(_module())
    missing = sorted(_MUST_SURVIVE - names)
    assert not missing, (
        f"{len(missing)} production-alive symbol(s) vanished from sync/batch.py: {missing}. "
        "Either the retirement over-reached (these are held by sync/background.py, "
        "sync/diagnose.py or the specify_cli.sync lazy map), or this probe can no "
        "longer see the module's symbols — in which case the absence assertions in "
        "this file are vacuous and prove nothing."
    )


def test_retired_drain_symbols_are_absent() -> None:
    """FR-001: no name from the frozen dead set is present in ``sync/batch.py``.

    Every one of these 33 names WAS present at this mission's base commit
    (``f04ee0a78``) — that is what makes their absence a measurement rather than
    a claim about a detector that never fires. The failure text names the
    offending symbols so the red is the consequence, not a boolean.
    """
    names = _top_level_names(_module())
    leaked = sorted(_RETIRED & names)
    assert not leaked, (
        f"{len(leaked)} retired queue-drain symbol(s) are present in sync/batch.py: {leaked}. "
        "These were deleted by #3167 because they could POST queued events without "
        "traversing a per-project consent decision. Reintroducing one revives the bypass; "
        "if the capability is genuinely needed, route it through the consent seam instead."
    )


def test_no_transmit_primitive_remains_in_batch() -> None:
    """NFR-001 / SC-001: ``sync/batch.py`` holds zero transmit primitives.

    Baseline at the mission's base commit was 4 call sites across 3 senders
    (manifest §4). The surviving surface — ``run_final_sync_with_retries`` and
    the reporting helpers — transmits nothing itself; it is driven by
    ``sync/background.py``. So any hit here is a new egress surface in a module
    whose ``E15`` unconsented-egress allowance was removed by this mission.
    """
    sites = _transmit_primitive_sites(_module())
    assert not sites, (
        f"{len(sites)} transmit primitive(s) reappeared in sync/batch.py: {sites}. "
        "This module is no longer on the egress allowlist (E15 was removed by #3167), "
        "so it must not hold a requests.* or request_with_stdlib_fallback_sync call."
    )
