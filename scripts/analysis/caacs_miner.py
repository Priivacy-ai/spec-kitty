#!/usr/bin/env python3
"""CaaCS: change-coupling-as-a-code-smell miner for test suites.

Mines `git log --name-only` to measure, per test file, how often it changes in
the SAME commit as production code (`src/`). High coupling = the test tracks
production churn rather than behaviour → refactor-fragile, a revision candidate.

Metrics per test file:
  changes        : commits touching the file
  co_src         : commits touching the file AND >=1 src/ file
  coupling_ratio : co_src / changes  (share of the test's edits driven by prod churn)
  top_partners   : the src/ modules it most-often co-changes with

Read-only; no repo mutation.
"""
from __future__ import annotations

import subprocess
from collections import Counter, defaultdict

SRC_PREFIX = "src/"
TEST_PREFIX = "tests/"


def commits():
    out = subprocess.run(
        ["git", "log", "--no-merges", "--name-only", "--pretty=format:@@@%H"],
        capture_output=True, text=True, check=True,
    ).stdout
    cur: list[str] = []
    for line in out.splitlines():
        if line.startswith("@@@"):
            if cur:
                yield cur
            cur = []
        elif line.strip():
            cur.append(line.strip())
    if cur:
        yield cur


def main() -> None:
    test_changes: Counter[str] = Counter()
    test_co_src: Counter[str] = Counter()
    partners: dict[str, Counter[str]] = defaultdict(Counter)

    def src_module(p: str) -> str:  # src/specify_cli/<pkg>/<file>
        return "/".join(p.split("/")[:4])

    for files in commits():
        srcs = [f for f in files if f.startswith(SRC_PREFIX) and f.endswith(".py")]
        tests = [f for f in files if f.startswith(TEST_PREFIX) and f.endswith(".py")]
        has_src = bool(srcs)
        for t in tests:
            test_changes[t] += 1
            if has_src:
                test_co_src[t] += 1
                for s in srcs:
                    partners[t][src_module(s)] += 1

    rows = []
    for t, ch in test_changes.items():
        co = test_co_src[t]
        ratio = co / ch if ch else 0.0
        rows.append((t, ch, co, ratio, partners[t].most_common(3)))

    def section(title, subset, key, top=25):
        print(f"\n## {title}\n")
        print("| test file | changes | co-src | ratio | top src partners |")
        print("|---|--:|--:|--:|---|")
        for t, ch, co, ratio, part in sorted(subset, key=key, reverse=True)[:top]:
            pstr = ", ".join(f"{m.replace('src/specify_cli/','')}×{c}" for m, c in part)
            print(f"| {t.replace('tests/','')} | {ch} | {co} | {ratio:.2f} | {pstr} |")

    arch = [r for r in rows if r[0].startswith("tests/architectural/")]
    charz = [r for r in rows if r[0].startswith("tests/characterization/")]
    # "core test packages": the trio + status + core domains
    core = [r for r in rows if r[0].startswith((
        "tests/specify_cli/cli/commands", "tests/status/", "tests/specify_cli/status",
        "tests/unit/status", "tests/specify_cli/acceptance", "tests/agent/",
    ))]

    print("# CaaCS test change-coupling report\n")
    print(f"History mined: {sum(1 for _ in commits())} non-merge commits.")
    print(f"Test files seen: {len(test_changes)} · arch: {len(arch)} · core-pkg: {len(core)}")

    # Rank arch tests by VOLUME of co-src change (maintenance burden) and by ratio.
    section("Architectural tests — by co-change VOLUME with src (maintenance burden)",
            arch, key=lambda r: r[2])
    section("Architectural tests — by coupling RATIO (>=4 changes)",
            [r for r in arch if r[1] >= 4], key=lambda r: (r[3], r[2]))
    section("Core test packages — by co-change VOLUME with src",
            core, key=lambda r: r[2])
    section("Characterization tests — by co-change VOLUME",
            charz, key=lambda r: r[2], top=15)


if __name__ == "__main__":
    main()
