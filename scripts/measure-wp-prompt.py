#!/usr/bin/env python3
"""Measure the character count + build time of a WP prompt (WP05 T021).

Used for the C-004 baseline (NFR-001 / NFR-002).  Reports per-WP results.

Usage::

    python scripts/measure-wp-prompt.py --feature layered-doctrine-org-layer-01KRNPEE
    python scripts/measure-wp-prompt.py --feature layered-doctrine-org-layer-01KRNPEE --wp WP01
    python scripts/measure-wp-prompt.py --feature layered-doctrine-org-layer-01KRNPEE --action review

The helper invokes the same ``_build_wp_prompt`` entry point used by
``spec-kitty next`` so the measurement reflects the production prompt
shape, not a synthetic approximation.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def discover_wps(feature_dir: Path) -> list[str]:
    """Return the sorted list of WP IDs declared under feature_dir/tasks."""

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return []
    wp_pattern = re.compile(r"^(WP\d+)")
    wp_ids: set[str] = set()
    for path in tasks_dir.glob("WP*.md"):
        match = wp_pattern.match(path.name)
        if match:
            wp_ids.add(match.group(1))
    return sorted(wp_ids)


def build_wp_prompt(
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    action: str,
    agent: str,
    mission_type: str,
) -> str:
    """Invoke the prompt builder directly and return the rendered text."""

    from specify_cli.next.prompt_builder import _build_wp_prompt

    return _build_wp_prompt(
        action=action,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        agent=agent,
        repo_root=REPO_ROOT,
        mission_type=mission_type,
    )


def measure_one(
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    action: str,
    agent: str,
    mission_type: str,
) -> tuple[int, float, str | None]:
    """Return ``(char_count, wall_seconds, error_or_None)``."""

    start = time.perf_counter()
    try:
        text = build_wp_prompt(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            action=action,
            agent=agent,
            mission_type=mission_type,
        )
    except Exception as exc:  # noqa: BLE001 — surface measurement errors
        elapsed = time.perf_counter() - start
        return 0, elapsed, f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - start
    return len(text), elapsed, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--feature",
        required=True,
        help="Feature slug under kitty-specs/ (e.g. layered-doctrine-org-layer-01KRNPEE)",
    )
    parser.add_argument(
        "--wp",
        default=None,
        help="Optional WP id to measure (e.g. WP01). When omitted, all WPs are measured.",
    )
    parser.add_argument(
        "--action",
        default="implement",
        choices=("implement", "review"),
        help="Action to render the prompt for (default: implement).",
    )
    parser.add_argument(
        "--agent",
        default="claude",
        help="Agent identifier passed to the prompt builder.",
    )
    parser.add_argument(
        "--mission-type",
        default="software-dev",
        help="Mission template identifier (default: software-dev).",
    )
    args = parser.parse_args(argv)

    feature_dir = REPO_ROOT / "kitty-specs" / args.feature
    if not feature_dir.is_dir():
        print(f"ERROR: feature directory not found: {feature_dir}", file=sys.stderr)
        return 2

    wp_ids = [args.wp] if args.wp else discover_wps(feature_dir)
    if not wp_ids:
        print(f"ERROR: no WP files found under {feature_dir / 'tasks'}", file=sys.stderr)
        return 2

    print(f"# Measuring {len(wp_ids)} WP prompts (action={args.action})")
    print(f"# Feature: {args.feature}")
    print(f"# Repo: {REPO_ROOT}")
    print()
    print(f"{'WP':<6}  {'chars':>10}  {'seconds':>10}  status")
    print(f"{'-' * 6}  {'-' * 10}  {'-' * 10}  -------")

    total_chars = 0
    total_seconds = 0.0
    max_chars = 0
    failures: list[tuple[str, str]] = []

    for wp_id in wp_ids:
        chars, seconds, error = measure_one(
            feature_dir=feature_dir,
            mission_slug=args.feature,
            wp_id=wp_id,
            action=args.action,
            agent=args.agent,
            mission_type=args.mission_type,
        )
        total_chars += chars
        total_seconds += seconds
        max_chars = max(max_chars, chars)
        status = "OK" if error is None else f"ERR: {error}"
        print(f"{wp_id:<6}  {chars:>10,}  {seconds:>10.3f}  {status}")
        if error is not None:
            failures.append((wp_id, error))

    print()
    print(f"{'TOTAL':<6}  {total_chars:>10,}  {total_seconds:>10.3f}")
    if wp_ids:
        print(
            f"{'MAX':<6}  {max_chars:>10,}  "
            f"(NFR-001 budget=32,000)"
        )

    if failures:
        print(file=sys.stderr)
        print(f"{len(failures)} WP(s) failed to render:", file=sys.stderr)
        for wp_id, error in failures:
            print(f"  {wp_id}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
