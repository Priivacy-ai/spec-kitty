#!/usr/bin/env python3
"""Acceptance-time content check for WP04 (FR-006).

Asserts that the testing-principles styleguide received the six refactor-stable
principles and the required patterns/anti_patterns from WP04.

This is an acceptance-time script — NOT a standing suite test (C-001).
Run it at review time:

    python kitty-specs/refactor-stable-gate-substrate-01KWK3FY/doctrine_content_check.py

Exit 0 = all assertions pass.  Non-zero + printed failures = needs attention.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    # ruamel.yaml is available in the project venv; fall back gracefully.
    try:
        from ruamel.yaml import YAML as _YAML  # type: ignore[import-untyped]

        _r = _YAML()
        yaml = type("_yaml_shim", (), {"safe_load": staticmethod(lambda s: _r.load(s))})()  # type: ignore[assignment]
    except ImportError:
        print("FATAL: neither PyYAML nor ruamel.yaml is importable. Activate the project venv.")
        sys.exit(2)

# ---------------------------------------------------------------------------
# Target file
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.parent
_STYLEGUIDE = (
    _REPO_ROOT
    / "src"
    / "doctrine"
    / "styleguides"
    / "built-in"
    / "testing-principles.styleguide.yaml"
)

# ---------------------------------------------------------------------------
# Snapshot of pre-existing principle strings — additive-only guard.
# Each string must survive verbatim in the final file.
# ---------------------------------------------------------------------------
_PRE_EXISTING_PRINCIPLES: list[str] = [
    "Fast: tests execute quickly enough that running them after every small change is not a burden.",
    "Isolated: each test sets up its own preconditions and does not depend on test order or shared mutable state.",
    "Repeatable: a test produces the same result every time it runs, on any machine, in any order.",
    "Self-validating: a test either passes or fails — no human inspection of logs required.",
    "Timely: tests are written at the same time as (or before) the production code they validate.",
    "Thorough: the test suite covers edge cases, failure paths, and boundary conditions — not only the happy path.",
    "Truthful: a passing test proves the behavior it describes is actually present in production code.",
    (
        "Realistic: test data mirrors the shape and invariants of production data — real-format identifiers,"
        " valid lengths and ranges, plausible values. Fabricated placeholder values that violate production"
        " constraints test a world that cannot occur; they mask real behavior and mislead debugging."
    ),
    "Inspiring: reading the test suite gives a new contributor a clear model of how the system behaves.",
    "Exemplary: tests are the best usage examples of the production code they exercise.",
    "Specific: a failing test clearly identifies which behavior is broken, not just that something is wrong.",
    "Predictive: the test suite reliably catches regressions before they reach production.",
    "Minimal: each test contains only the code necessary to validate one behavior increment.",
]

# Snapshot of pre-existing pattern names — must survive.
_PRE_EXISTING_PATTERN_NAMES: list[str] = [
    "Testing Pyramid",
    "Clear Test Boundaries",
    "Quad-A Test Structure",
]

# Snapshot of pre-existing anti_pattern names — must survive.
_PRE_EXISTING_ANTI_PATTERN_NAMES: list[str] = [
    "Over-Mocking",
    "Shared Mutable State Between Tests",
    "Asserting Implementation Details",
    "Fabricated / Unrealistic Test Data",
]

# ---------------------------------------------------------------------------
# D7 topic markers — each new principle must match at least one of these
# keywords (case-insensitive) to prove topic coverage.
# ---------------------------------------------------------------------------
_D7_TOPICS: list[tuple[str, list[str]]] = [
    ("invariants-over-shape", ["invariant", "shape", "refactor"]),
    ("negative-and-behavioral-forms-first", ["negative", "behavioral", "absence", "literal-presence"]),
    ("size-metrics-belong-to-sonar", ["sonar", "loc", "size metric", "complexity threshold"]),
    ("convert-or-delete-never-re-pin", ["re-pin", "convert or delete", "surviving-coverage"]),
    ("shrink-only-count-ratchets-are-sanctioned", ["ratchet", "shrink", "allowlist count"]),
    (
        "transitional-shape-guards-need-a-retirement-path",
        ["transitional", "retirement", "quarantine backlog"],
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load() -> dict:  # type: ignore[type-arg]
    raw = _STYLEGUIDE.read_text(encoding="utf-8")
    try:
        return yaml.safe_load(raw)  # type: ignore[no-any-return]
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: YAML parse error in {_STYLEGUIDE}: {exc}")
        sys.exit(2)


def _check(condition: bool, msg: str, failures: list[str]) -> None:
    if not condition:
        failures.append(msg)


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


def check_principles(data: dict, failures: list[str]) -> None:  # type: ignore[type-arg]
    principles: list[str] = data.get("principles", [])

    # (a) Pre-existing principles survive verbatim.
    for pre in _PRE_EXISTING_PRINCIPLES:
        # Strip trailing whitespace variation for robust comparison.
        found = any(p.strip() == pre.strip() for p in principles)
        _check(found, f"Pre-existing principle missing or mutated: {pre[:60]!r}...", failures)

    # Collect new principles (those not in the pre-existing snapshot).
    new_principles = [p for p in principles if p.strip() not in {e.strip() for e in _PRE_EXISTING_PRINCIPLES}]

    # (a) At least 6 new principles.
    _check(
        len(new_principles) >= 6,
        f"Expected ≥6 new principles, found {len(new_principles)}: {[p[:40] for p in new_principles]}",
        failures,
    )

    # (a) Each new principle ≥ 80 chars, no TODO/placeholder.
    for p in new_principles:
        _check(
            len(p) >= 80,
            f"New principle too short ({len(p)} chars): {p[:60]!r}",
            failures,
        )
        _check(
            "TODO" not in p and "placeholder" not in p.lower(),
            f"New principle contains TODO/placeholder: {p[:60]!r}",
            failures,
        )

    # (a) Each D7 topic is covered by at least one new principle.
    for topic_name, keywords in _D7_TOPICS:
        covered = any(
            any(kw.lower() in p.lower() for kw in keywords) for p in new_principles
        )
        _check(covered, f"D7 topic '{topic_name}' not covered by any new principle.", failures)


def check_patterns(data: dict, failures: list[str]) -> None:  # type: ignore[type-arg]
    patterns: list[dict] = data.get("patterns", [])  # type: ignore[type-arg]
    pattern_names = [p.get("name", "") for p in patterns]

    # Pre-existing pattern names survive.
    for pre in _PRE_EXISTING_PATTERN_NAMES:
        _check(pre in pattern_names, f"Pre-existing pattern missing: {pre!r}", failures)

    # (b) At least 2 NEW patterns, each with non-empty good_example and bad_example.
    new_patterns = [p for p in patterns if p.get("name", "") not in _PRE_EXISTING_PATTERN_NAMES]
    _check(
        len(new_patterns) >= 2,
        f"Expected ≥2 new patterns, found {len(new_patterns)}: {[p.get('name') for p in new_patterns]}",
        failures,
    )
    for pat in new_patterns:
        name = pat.get("name", "<unnamed>")
        _check(
            bool(pat.get("good_example", "").strip()),
            f"New pattern {name!r} has empty good_example.",
            failures,
        )
        _check(
            bool(pat.get("bad_example", "").strip()),
            f"New pattern {name!r} has empty bad_example.",
            failures,
        )


def check_anti_patterns(data: dict, failures: list[str]) -> None:  # type: ignore[type-arg]
    anti_patterns: list[dict] = data.get("anti_patterns", [])  # type: ignore[type-arg]
    ap_names = [ap.get("name", "") for ap in anti_patterns]

    # Pre-existing anti_pattern names survive.
    for pre in _PRE_EXISTING_ANTI_PATTERN_NAMES:
        _check(pre in ap_names, f"Pre-existing anti_pattern missing: {pre!r}", failures)

    # (b) At least 1 NEW anti_pattern with non-empty good_example and bad_example.
    new_aps = [ap for ap in anti_patterns if ap.get("name", "") not in _PRE_EXISTING_ANTI_PATTERN_NAMES]
    _check(
        len(new_aps) >= 1,
        f"Expected ≥1 new anti_pattern, found {len(new_aps)}.",
        failures,
    )
    for ap in new_aps:
        name = ap.get("name", "<unnamed>")
        _check(
            bool(ap.get("good_example", "").strip()),
            f"New anti_pattern {name!r} has empty good_example.",
            failures,
        )
        _check(
            bool(ap.get("bad_example", "").strip()),
            f"New anti_pattern {name!r} has empty bad_example.",
            failures,
        )


def check_pr2308_citation(data: dict, failures: list[str]) -> None:  # type: ignore[type-arg]
    """(c) At least one entry literally cites #2308 or one of its commits."""
    raw_text = _STYLEGUIDE.read_text(encoding="utf-8")
    citations = ["#2308", "052d465e9", "50abe2fdc"]
    found = any(c in raw_text for c in citations)
    _check(found, f"No citation of PR #2308 or its commits ({citations}) found in the file.", failures)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    failures: list[str] = []

    if not _STYLEGUIDE.exists():
        print(f"FATAL: styleguide not found at {_STYLEGUIDE}")
        return 2

    data = _load()

    check_principles(data, failures)
    check_patterns(data, failures)
    check_anti_patterns(data, failures)
    check_pr2308_citation(data, failures)

    # Summary
    principles = data.get("principles", [])
    patterns = data.get("patterns", [])
    anti_patterns = data.get("anti_patterns", [])

    pre_p = {e.strip() for e in _PRE_EXISTING_PRINCIPLES}
    new_principle_count = sum(1 for p in principles if p.strip() not in pre_p)
    new_pattern_count = sum(
        1 for p in patterns if p.get("name", "") not in _PRE_EXISTING_PATTERN_NAMES
    )
    new_ap_count = sum(
        1 for ap in anti_patterns if ap.get("name", "") not in _PRE_EXISTING_ANTI_PATTERN_NAMES
    )

    print("=" * 60)
    print("WP04 doctrine content check")
    print("=" * 60)
    print(f"  Styleguide: {_STYLEGUIDE.relative_to(_REPO_ROOT)}")
    print(f"  Total principles : {len(principles)}  (new: {new_principle_count})")
    print(f"  Total patterns   : {len(patterns)}  (new: {new_pattern_count})")
    print(f"  Total anti_pats  : {len(anti_patterns)}  (new: {new_ap_count})")
    print()

    if failures:
        print(f"FAILED — {len(failures)} assertion(s):")
        for i, f in enumerate(failures, 1):
            print(f"  [{i}] {f}")
        return 1

    print("ALL ASSERTIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
