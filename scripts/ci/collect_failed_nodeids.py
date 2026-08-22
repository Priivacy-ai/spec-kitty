#!/usr/bin/env python3
"""Red-first re-run ordering (mission ci-flake-report-workflow WP05, FR-018).

On a new push to an already-open PR, we want the test nodeids that failed on
the *previous* run to execute FIRST, ahead of the rest of the relevant suite,
so a still-broken fix goes red as fast as possible. This module is the pure,
stdlib-only logic that makes that possible without a double-run:

- **Collect** (:func:`parse_failed_nodeids_from_output`,
  :func:`parse_failed_nodeids_from_junit`) — pull failing nodeids out of a
  pytest terminal log or a JUnit XML report.
- **Persist** (:func:`write_persisted_nodeids`, :func:`read_persisted_nodeids`)
  — a plain one-nodeid-per-line file, the payload cached/uploaded as
  ``flake-lastfailed-<pr-number>`` across pushes to the same PR.
- **Select** (:func:`select_priority_nodeids`) — intersect the persisted list
  against the currently-collected test set, preserving persisted order and
  silently dropping anything removed or renamed.
- **Seed** (:func:`build_lastfailed_cache`, :func:`write_lastfailed_cache`) —
  produce pytest's own ``.pytest_cache/v/cache/lastfailed`` JSON shape so a
  plain ``pytest --ff`` re-run tries the priority nodeids first, in ONE pass
  (no separate priority + remainder invocations).

Every public function here is defensive by design (FR-018's own note): this
is an ergonomics optimization, never a correctness gate. Corrupt or absent
input degrades to "no prior failures" (normal test order) — it never raises
to the caller, and it must never make a CI run fail or block on its own
account.

NFR-001: standard library only; ``ruff``/``mypy --strict`` clean; every
function kept at cyclomatic complexity <= 15.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

ENCODING = "utf-8"

#: Same anchored shape as ``scripts/ci/flake_report.py``'s
#: ``_FAILED_NODEID_PATTERN`` -- kept as its own copy rather than an import
#: because this module has no other dependency on that one and stays a
#: standalone, minimally-coupled CI tool (mirrors ``flake_report_cli.py``'s
#: own note about single-purpose modules under ``scripts/ci``).
_FAILED_LINE_PATTERN = re.compile(r"^FAILED (\S+)", re.MULTILINE)

#: Relative path (under a pytest cache root) of pytest's own lastfailed
#: cache file. ``--ff``/``--lf`` read this exact location.
LASTFAILED_RELATIVE_PATH = Path("v") / "cache" / "lastfailed"

DEFAULT_CACHE_DIR = Path(".pytest_cache")


# ---------------------------------------------------------------------------
# Collect: pull failing nodeids out of a pytest log / JUnit XML report
# ---------------------------------------------------------------------------


def parse_failed_nodeids_from_output(text: str) -> list[str]:
    """Extract failing nodeids from pytest's terminal ``FAILED <nodeid>`` lines.

    Order-preserving, de-duplicated (first occurrence wins). Defensive:
    empty/garbage input yields an empty list, never raises.
    """
    if not text:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _FAILED_LINE_PATTERN.finditer(text):
        nodeid = match.group(1).strip()
        if nodeid and nodeid not in seen:
            seen.add(nodeid)
            ordered.append(nodeid)
    return ordered


def parse_failed_nodeids_from_junit(xml_path: Path) -> list[str]:
    """Extract failing nodeids from a JUnit XML report (``--junitxml`` output).

    A ``<testcase>`` counts as failing if it has a ``<failure>`` or
    ``<error>`` child. The nodeid is reconstructed from the testcase's
    ``classname``/``name`` attributes (JUnit XML carries no ``::``-joined
    pytest nodeid directly): trailing dotted components that look like a
    Python class (start with an uppercase letter -- pytest's own discovery
    convention for test classes) become ``::``-joined class/method segments;
    the remaining dotted prefix becomes the module path.

    This reconstruction is best-effort, not authoritative -- a wrong guess
    simply will not match any currently-collected nodeid, and
    :func:`select_priority_nodeids` drops it exactly like a renamed/removed
    test (harmless skip, per FR-018). Defensive: a missing file,
    unparseable XML, or unexpected structure all degrade to an empty list.
    """
    try:
        if not xml_path.is_file():
            return []
        # NFR-001 forbids a third-party dep (defusedxml); this parses
        # `--junitxml` output this SAME CI job just wrote (its own pytest
        # run), never externally-supplied/untrusted XML.
        root = ET.parse(xml_path).getroot()  # noqa: S314
    except (OSError, ET.ParseError):
        return []

    seen: set[str] = set()
    nodeids: list[str] = []
    for testcase in root.iter("testcase"):
        if testcase.find("failure") is None and testcase.find("error") is None:
            continue
        name = testcase.get("name", "").strip()
        if not name:
            continue
        nodeid = _junit_nodeid(testcase.get("classname", ""), name)
        if nodeid and nodeid not in seen:
            seen.add(nodeid)
            nodeids.append(nodeid)
    return nodeids


def _junit_nodeid(classname: str, name: str) -> str:
    """Best-effort ``file.py::Class::test`` nodeid from a JUnit ``classname``/``name`` pair."""
    if not classname:
        return name
    parts = classname.split(".")
    class_parts: list[str] = []
    while parts and parts[-1][:1].isupper():
        class_parts.insert(0, parts.pop())
    if not parts:
        # The whole classname looked class-like (no lowercase module prefix
        # survived) -- fall back to treating it as the file path itself.
        return f"{'/'.join(class_parts)}.py::{name}" if class_parts else name
    file_part = "/".join(parts) + ".py"
    suffix = "::".join([*class_parts, name])
    return f"{file_part}::{suffix}"


# ---------------------------------------------------------------------------
# Persist: read/write the plain one-nodeid-per-line file that gets
# cached/uploaded as ``flake-lastfailed-<pr-number>`` across pushes.
# ---------------------------------------------------------------------------


def write_persisted_nodeids(path: Path, nodeids: Iterable[str]) -> None:
    """Persist failing nodeids, one per line, sorted for deterministic output.

    Defensive: any write failure (unwritable path, missing parent that
    cannot be created, etc.) is swallowed -- persisting is an optimization
    for the NEXT run, never a requirement for THIS run to succeed.
    """
    unique_sorted = sorted({nodeid.strip() for nodeid in nodeids if nodeid.strip()})
    body = "\n".join(unique_sorted)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body + ("\n" if unique_sorted else ""), encoding=ENCODING)
    except OSError:
        return


def read_persisted_nodeids(path: Path) -> list[str]:
    """Read a previously persisted nodeid list.

    Defensive: an absent file, unreadable file, or non-UTF8/corrupt content
    all degrade to an empty list (normal test order) rather than raising --
    FR-018's "missing/renamed nodeids skip harmlessly" contract starts here.
    """
    try:
        if not path.is_file():
            return []
        text = path.read_text(encoding=ENCODING)
    except (OSError, UnicodeDecodeError):
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Select: persisted list ∩ current tests, persisted order preserved
# ---------------------------------------------------------------------------


def select_priority_nodeids(persisted: Iterable[str], current: Iterable[str]) -> list[str]:
    """Return the subset of ``persisted`` still present in ``current``.

    Order is preserved from ``persisted`` (the prior run's failure order).
    A persisted nodeid absent from ``current`` (removed or renamed test) is
    dropped silently -- never an error. Empty ``persisted`` -> empty result,
    i.e. normal test order.
    """
    current_set = set(current)
    return [nodeid for nodeid in persisted if nodeid in current_set]


# ---------------------------------------------------------------------------
# Seed: pytest's own lastfailed cache, so a plain ``--ff`` run does the
# reordering in ONE pass -- no separate priority + remainder invocations.
# ---------------------------------------------------------------------------


def build_lastfailed_cache(nodeids: Iterable[str]) -> dict[str, bool]:
    """Build the payload shape of pytest's ``.pytest_cache/v/cache/lastfailed`` file.

    Pytest's own cache is a flat JSON object mapping each previously-failed
    nodeid to ``true``; this reproduces that shape exactly so ``--ff``/
    ``--lf`` read it natively.
    """
    return {nodeid.strip(): True for nodeid in nodeids if nodeid.strip()}


def write_lastfailed_cache(cache_dir: Path, nodeids: Iterable[str]) -> Path:
    """Seed pytest's lastfailed cache under ``cache_dir`` from ``nodeids``.

    ``cache_dir`` is the pytest cache root (conventionally ``.pytest_cache``).
    Returns the target path regardless of outcome. Defensive: any write
    failure is swallowed -- seeding the cache is an optimization; a plain
    ``pytest --ff`` with no seeded cache just runs in normal order, which is
    the correct no-op fallback (FR-018).
    """
    target = cache_dir / LASTFAILED_RELATIVE_PATH
    payload = build_lastfailed_cache(nodeids)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding=ENCODING)
    except OSError:
        return target
    return target


# ---------------------------------------------------------------------------
# CLI (T019 wiring: one `collect` step after the run, one `seed` step before)
# ---------------------------------------------------------------------------


def _cmd_collect(args: argparse.Namespace) -> int:
    """Parse failing nodeids (log and/or JUnit XML) and persist them for next time."""
    nodeids: list[str] = []
    if args.junit_xml is not None:
        nodeids.extend(parse_failed_nodeids_from_junit(Path(args.junit_xml)))
    if args.from_output is not None:
        try:
            text = Path(args.from_output).read_text(encoding=ENCODING)
        except (OSError, UnicodeDecodeError):
            text = ""
        nodeids.extend(parse_failed_nodeids_from_output(text))
    write_persisted_nodeids(Path(args.out), nodeids)
    print(f"collect_failed_nodeids: persisted {len(set(nodeids))} nodeid(s) -> {args.out}")
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    """Seed pytest's lastfailed cache from a previously persisted nodeid file."""
    persisted = read_persisted_nodeids(Path(args.persisted))
    target = write_lastfailed_cache(Path(args.cache_dir), persisted)
    print(f"collect_failed_nodeids: seeded {len(persisted)} nodeid(s) -> {target}")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collect_failed_nodeids.py",
        description=(
            "Red-first re-run ordering (FR-018): persist a PR run's failing test nodeids, and "
            "seed pytest's own lastfailed cache from them so the NEXT push's `pytest --ff` run "
            "tries them first, in one pass."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Parse and persist this run's failing nodeids.")
    collect.add_argument("--junit-xml", default=None, help="Path to a JUnit XML report to parse.")
    collect.add_argument("--from-output", default=None, help="Path to a captured pytest terminal log to parse.")
    collect.add_argument("--out", required=True, help="Path to write the persisted nodeid list to.")
    collect.set_defaults(func=_cmd_collect)

    seed = subparsers.add_parser("seed", help="Seed pytest's lastfailed cache from a persisted nodeid list.")
    seed.add_argument("--persisted", required=True, help="Path to a previously persisted nodeid list.")
    seed.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR), help=f"Pytest cache root (default: {DEFAULT_CACHE_DIR})."
    )
    seed.set_defaults(func=_cmd_seed)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Never raises -- any unexpected failure is reported and swallowed (exit 0).

    This tool must never gate or error the CI run it assists (FR-018's own
    note): a broken collect/seed step degrades to "no red-first ordering
    this run", not a red build.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 -- deliberate: this tool must never fail the CI run it assists
        print(f"collect_failed_nodeids: non-fatal error ({exc!r}) -- continuing without red-first ordering", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
