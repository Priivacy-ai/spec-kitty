"""Golden-count inventory + recurrence guard (FR-014/FR-016/NFR-002, #2076 CT5).

Mission ``test-suite-friction-remediation-01KXDKBX`` WP11. Systematic sweep for the
``len(<collection>) == <int>`` "golden-count" friction: an assertion that pins a bare
cardinality where a set/frozenset-equality would express the real contract (adding,
removing, or renaming a member should force a *content* edit, not silently pass at an
unchanged count). ``tests/status/test_models.py::test_lane_member_names_exact`` (WP07)
is the exemplar this sweep follows: ``len(Lane) == 10`` became an exact frozenset of
member names.

This module has three jobs:

1. **Inventory** — :func:`scan_repo` walks ``tests/`` with an AST predicate for
   ``len(<expr>) == <int>`` (either operand order) and classifies each site ``keep``
   (cardinality genuinely *is* the contract) or ``convert`` (a set/frozenset/dict
   equality would be the stronger, real contract) via :func:`classify_golden_count`.
   ``../golden-count-inventory.md`` (a committed mission artifact, not a test-owned
   file) is the directory-partitioned, human-readable rendering of this scan, built by
   ``python -m tests.architectural.test_golden_count_ban --emit-inventory <path>``.

2. **Recurrence guard** — :func:`test_convert_sites_do_not_exceed_frozen_baseline`
   re-scans the real tree and asserts the number of ``convert``-classified,
   non-escaped sites in every top-level ``tests/<dir>`` never exceeds the frozen
   ceiling in ``_golden_count_baseline.json`` (this guard's own new sidecar data file
   — no other WP's ``owned_files`` claims it; see the mission's ownership-map leeway
   for rationale-backed additions outside a WP's literal owned-file list). A brand
   new directory, or one exceeding its recorded ceiling, fails — closing the class
   going forward *everywhere* in ``tests/``, not only in this mission's batch-owned
   directories. Batch WPs (WP12-WP14) burn their own directories' ceilings down
   (T057-style: "decrement the baseline"); the ceiling is regenerated wholesale via
   ``--freeze-baseline`` (a full re-scan snapshot, mirroring the gc3b
   ``--update-baseline`` idiom) after each batch's conversions land, never edited by
   hand for anything other than a documented decrease.

3. **Escape hatch** — a genuinely cardinality-only assertion the heuristic
   misclassifies as ``convert`` may carry an inline ``# golden-count:
   cardinality-is-contract`` comment on the assertion's own physical source line
   (:func:`is_escaped`) to opt out explicitly, mirroring
   ``test_ratchet_positional_anchor_ban.py``'s ``# diagnostic-locator`` escape hatch.
   An escaped site never counts against any directory's ceiling.

Classification heuristic (documented, not silently "smart")
-------------------------------------------------------------
``classify_golden_count(collection_expr, n)`` is deliberately simple and auditable,
not a semantic oracle over ~2000 sites:

* ``n == 0`` -> ``keep`` (an emptiness check has no members to name; a frozenset
  equality against ``frozenset()`` carries no more information).
* the counted expression's identifier words intersect :data:`_DYNAMIC_RUNTIME_WORDS`
  (``errors``, ``calls``, ``retries``, ``events``, ``results``, ... — the vocabulary
  of a runtime-measured quantity, where WHICH items occurred doesn't matter, only how
  many) -> ``keep``.
* otherwise -> ``convert`` (the default: a bare/attribute collection reference with no
  dynamic-measurement vocabulary — the WP07 ``len(Lane) == 10`` shape, and the common
  case in the mission's batch-owned "clean" directories, which were chosen precisely
  because they are dominated by counts of stable, nameable, config/registry-shaped
  data rather than runtime-measured quantities).

This is a first-pass heuristic, not a guarantee every existing ``keep``/``convert``
label is semantically perfect — the escape hatch corrects individual
misclassifications, and the batch WPs re-judge each site in context as they convert
it (a batch WP finding a heuristic ``convert`` that is actually cardinality-only
annotates it ``keep`` instead of converting; this narrows the baseline exactly the
same as a real conversion). The *guard's* real job is precise: never let the
un-annotated ``convert`` count grow beyond the frozen ceiling.

Known scope boundary: the per-directory ceiling is a **count**, not a per-site
identity set. Converting one site while a different, unrelated site regrows in the
same directory in the same landing would net to an unchanged count and not be
caught by this guard alone (review is the second line of defence for that). This
mirrors the existing ``marker_baseline.txt`` "count does not grow" idiom rather than
a full content-addressed diff, chosen deliberately to avoid re-triggering
``test_ratchet_positional_anchor_ban.py``'s ban on positional ``(file, line)``
anchors — a per-site baseline would need line-based keys to stay identifiable across
scans, which is exactly the anchoring anti-pattern that guard exists to prevent.

Spec source: spec.md FR-014/FR-016/NFR-002; plan.md IC-14; data-model.md E-10.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from specify_cli.contracts.anchoring import enclosing_qualname

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_ROOT = _REPO_ROOT / "tests"
_BASELINE_PATH = Path(__file__).resolve().with_name("_golden_count_baseline.json")

# Escape hatch: an inline comment on the assertion's own physical source line opts a
# genuinely cardinality-only site out of the ``convert`` classification entirely.
ESCAPE_HATCH_MARKER = "# golden-count: cardinality-is-contract"

# Vocabulary of a runtime-measured quantity (WHICH items occurred doesn't matter, only
# how many) -- see the module docstring's "Classification heuristic" section.
_DYNAMIC_RUNTIME_WORDS: frozenset[str] = frozenset(
    {
        "error", "errors", "warning", "warnings", "log", "logs", "call", "calls",
        "retry", "retries", "attempt", "attempts", "event", "events", "match",
        "matches", "result", "results", "record", "records", "row", "rows",
        "count", "counts", "occurrence", "occurrences", "duration", "request",
        "requests", "response", "responses", "iteration", "iterations", "cycle",
        "cycles", "execution", "executions", "commit", "commits", "worker",
        "workers", "thread", "threads", "queue", "pending", "failure",
        "failures", "success", "successes", "invocation", "invocations",
        "notification", "notifications", "metric", "metrics", "sample",
        "samples", "chunk", "chunks", "batch", "batches", "message", "messages",
        "packet", "packets", "poll", "polls", "tick", "ticks", "step", "steps",
        "trial", "trials", "diff", "diffs", "delta", "deltas", "mutation",
        "mutations", "violation", "violations", "issue", "issues", "finding",
        "findings", "alert", "alerts", "stdout", "stderr", "output", "outputs",
        "run", "runs", "elapsed",
    }
)

_WORD_RE = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class GoldenCountSite:
    """One ``len(<collection>) == <int>`` (or reversed-operand) finding."""

    relpath: str
    lineno: int
    qualname: str
    collection_expr: str
    n: int
    classification: str  # "keep" | "convert"
    escaped: bool

    @property
    def top_dir(self) -> str | None:
        """The ``tests/<name>`` bucket this site's directory ratchet is keyed by."""
        return top_level_dir(self.relpath)


# ---------------------------------------------------------------------------
# Small, pure, directly-testable predicates (S3776 pre-extraction).
# ---------------------------------------------------------------------------


def _is_len_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
    )


def _is_int_constant(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    )


def _matching_len_compare(node: ast.Compare) -> tuple[ast.Call, ast.Constant] | None:
    """Return ``(len_call, int_constant)`` when *node* is ``len(x) == N`` or
    ``N == len(x)``. ``None`` for any other single-op ``Compare`` shape.
    """
    if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
        return None
    left, right = node.left, node.comparators[0]
    if _is_len_call(left) and _is_int_constant(right):
        return left, right  # type: ignore[return-value]
    if _is_len_call(right) and _is_int_constant(left):
        return right, left  # type: ignore[return-value]
    return None


def _collection_words(collection_expr: str) -> frozenset[str]:
    """Lower-cased identifier words in *collection_expr* (the ``len(...)`` argument's
    unparsed source), used to test against :data:`_DYNAMIC_RUNTIME_WORDS`.
    """
    return frozenset(w.lower() for w in _WORD_RE.findall(collection_expr))


def classify_golden_count(collection_expr: str, n: int) -> str:
    """Classify one ``len(collection_expr) == n`` site as ``"keep"`` or ``"convert"``.

    See the module docstring's "Classification heuristic" section for the full
    rationale; this function is the single source of truth both the inventory scan
    and the recurrence guard's tests exercise directly.
    """
    if n == 0:
        return "keep"
    if _collection_words(collection_expr) & _DYNAMIC_RUNTIME_WORDS:
        return "keep"
    return "convert"


def is_escaped(source_lines: list[str], lineno: int) -> bool:
    """``True`` when the 1-based *lineno* physical line carries
    :data:`ESCAPE_HATCH_MARKER`.
    """
    if 1 <= lineno <= len(source_lines):
        return ESCAPE_HATCH_MARKER in source_lines[lineno - 1]
    return False


def top_level_dir(relpath: str) -> str | None:
    """The ``tests/<name>`` prefix *relpath* falls under, or ``None`` for a file
    directly at ``tests/`` root (no sub-directory ratchet bucket).
    """
    parts = relpath.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else None


# ---------------------------------------------------------------------------
# Scan (inventory + ratchet share this).
# ---------------------------------------------------------------------------


def scan_file(path: Path, *, repo_root: Path = _REPO_ROOT) -> list[GoldenCountSite]:
    """Return every :class:`GoldenCountSite` in *path*, or ``[]`` on a parse error
    (a syntactically invalid test file is out of this guard's scope; other guards
    already require the suite to import cleanly).
    """
    relpath = path.resolve().relative_to(repo_root).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relpath)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    source_lines = source.splitlines()
    sites: list[GoldenCountSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        matched = _matching_len_compare(node)
        if matched is None:
            continue
        len_call, const_node = matched
        collection_expr = ast.unparse(len_call.args[0])
        # _is_int_constant already guarantees const_node.value is a bare (non-bool) int.
        n = cast(int, const_node.value)
        sites.append(
            GoldenCountSite(
                relpath=relpath,
                lineno=node.lineno,
                qualname=enclosing_qualname(source, node.lineno),
                collection_expr=collection_expr,
                n=n,
                classification=classify_golden_count(collection_expr, n),
                escaped=is_escaped(source_lines, node.lineno),
            )
        )
    return sites


def scan_repo(*, tests_root: Path = _TESTS_ROOT, repo_root: Path = _REPO_ROOT) -> list[GoldenCountSite]:
    """Walk every ``*.py`` file under *tests_root* and return all findings."""
    sites: list[GoldenCountSite] = []
    for path in sorted(tests_root.rglob("*.py")):
        sites.extend(scan_file(path, repo_root=repo_root))
    return sites


def convert_counts_by_dir(sites: list[GoldenCountSite]) -> dict[str, int]:
    """Non-escaped ``convert``-classified site counts, keyed by ``tests/<dir>``."""
    counts: dict[str, int] = {}
    for site in sites:
        if site.classification != "convert" or site.escaped:
            continue
        bucket = site.top_dir
        if bucket is None:
            continue
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def ratchet_violations(current: dict[str, int], baseline: dict[str, int]) -> list[str]:
    """Directories where *current* exceeds the frozen *baseline* ceiling.

    Pure and baseline-agnostic so both the fixture-backed unit tests and the
    real-tree integration test exercise the identical predicate.
    """
    violations = []
    for directory, count in sorted(current.items()):
        ceiling = baseline.get(directory, 0)
        if count > ceiling:
            violations.append(
                f"{directory}: {count} un-annotated convert-classified golden-count "
                f"site(s) exceeds the frozen baseline ceiling of {ceiling}. Either "
                f"convert the new site(s), annotate genuine cardinality-only sites "
                f"with `{ESCAPE_HATCH_MARKER}`, or (if this is a legitimate batch "
                f"landing that also converted sites elsewhere) re-freeze via "
                f"`python -m tests.architectural.test_golden_count_ban "
                f"--freeze-baseline`."
            )
    return violations


def load_baseline(path: Path = _BASELINE_PATH) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ceilings = data["ceilings"]
    if not isinstance(ceilings, dict):
        raise TypeError(f"{path}: 'ceilings' must be an object, got {type(ceilings)!r}")
    return {str(k): int(v) for k, v in ceilings.items()}


def _regenerate_baseline() -> dict[str, int]:
    """Full re-scan snapshot of the real tree (the gc3b ``--update-baseline`` idiom:
    a last-writer-regenerates full recompute, not a hand-edited textual merge).
    """
    return convert_counts_by_dir(scan_repo())


def freeze_baseline(path: Path = _BASELINE_PATH) -> dict[str, int]:
    ceilings = _regenerate_baseline()
    payload = {
        "$schema-note": (
            "Per-directory ceiling on non-escaped `convert`-classified golden-count "
            "sites (FR-014/#2076). Regenerate via `python -m "
            "tests.architectural.test_golden_count_ban --freeze-baseline` after a "
            "batch conversion lands; never hand-edit except to record a documented "
            "decrease. A directory absent here has an implicit ceiling of 0 -- any "
            "convert-classified site appearing there fails the guard immediately."
        ),
        "ceilings": dict(sorted(ceilings.items())),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return ceilings


# ---------------------------------------------------------------------------
# Guard tests.
# ---------------------------------------------------------------------------


def test_zero_length_check_is_always_kept() -> None:
    assert classify_golden_count("errors_from_a_totally_unknown_thing", 0) == "keep"


def test_dynamic_runtime_measured_quantity_is_kept() -> None:
    assert classify_golden_count("collected_errors", 3) == "keep"
    assert classify_golden_count("mock_client.call_args_list", 2) == "keep"


def test_fresh_unannotated_golden_count_is_classified_convert() -> None:
    """T050 (part 1): a fresh, non-dynamic, non-zero ``len(x) == N`` site — the
    WP07 ``len(Lane) == 10`` shape — is classified ``convert``, matching the
    exemplar this sweep follows.
    """
    assert classify_golden_count("Lane", 10) == "convert"
    assert classify_golden_count("supported_colors", 3) == "convert"


def test_escape_hatch_on_own_line_excludes_site() -> None:
    """T050 (part 2): the escape-hatch annotation is read from the assertion's own
    physical source line and marks the site escaped regardless of classification.
    """
    source_lines = [
        "def test_something():",
        f"    assert len(supported_colors) == 3  {ESCAPE_HATCH_MARKER}",
        "",
    ]
    assert is_escaped(source_lines, 2) is True
    assert is_escaped(source_lines, 1) is False


def test_fresh_unannotated_site_in_new_directory_fails_ratchet() -> None:
    """T050: a fresh un-annotated golden-count assertion in a directory with no
    recorded baseline entry (implicit ceiling 0) fails the guard.
    """
    violations = ratchet_violations(current={"tests/brand_new_dir": 1}, baseline={})
    assert len(violations) == 1
    assert "tests/brand_new_dir" in violations[0]


def test_site_within_frozen_ceiling_passes_ratchet() -> None:
    """An annotated site never reaches ``current`` (escaped sites are excluded by
    :func:`convert_counts_by_dir`); a non-escaped site already accounted for in the
    frozen baseline passes.
    """
    assert ratchet_violations(current={"tests/charter": 40}, baseline={"tests/charter": 40}) == []
    assert ratchet_violations(current={"tests/charter": 30}, baseline={"tests/charter": 40}) == []


def test_convert_counts_by_dir_excludes_escaped_and_keep_sites() -> None:
    sites = [
        GoldenCountSite("tests/foo/test_a.py", 10, "<module>", "Lane", 10, "convert", escaped=False),
        GoldenCountSite("tests/foo/test_a.py", 20, "<module>", "errors", 3, "keep", escaped=False),
        GoldenCountSite("tests/foo/test_a.py", 30, "<module>", "Palette", 5, "convert", escaped=True),
    ]
    assert convert_counts_by_dir(sites) == {"tests/foo": 1}


def test_baseline_file_exists_and_parses() -> None:
    assert _BASELINE_PATH.exists(), (
        f"{_BASELINE_PATH} is missing -- run `python -m "
        f"tests.architectural.test_golden_count_ban --freeze-baseline` to generate it."
    )
    ceilings = load_baseline()
    assert ceilings, "frozen baseline must not be empty on a repo with known golden-count debt"
    assert all(isinstance(v, int) and v >= 0 for v in ceilings.values())


def test_convert_sites_do_not_exceed_frozen_baseline() -> None:
    """The recurrence guard (T049/T053): re-scan the real tree and assert no
    directory's non-escaped ``convert`` count exceeds its frozen baseline ceiling.
    Green on the real tree today (the ceiling was just frozen from this exact
    scan); goes red the moment a NEW un-annotated golden-count assertion is added
    anywhere under ``tests/`` beyond what a directory's ceiling already accounts
    for.
    """
    current = convert_counts_by_dir(scan_repo())
    baseline = load_baseline()
    violations = ratchet_violations(current, baseline)
    assert violations == [], "Golden-count regrowth detected:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# CLI: inventory emission + baseline (re)freeze.
# ---------------------------------------------------------------------------


def _format_site_row(site: GoldenCountSite) -> str:
    return (
        f"| `{site.relpath}` | {site.lineno} | `{site.qualname}` | "
        f"`len({site.collection_expr}) == {site.n}` |"
    )


def _render_inventory(sites: list[GoldenCountSite]) -> str:
    from datetime import UTC, datetime

    batch_dirs = {
        "WP12": (
            "tests/charter", "tests/doctrine", "tests/doctrine_synthesizer",
            "tests/glossary",
        ),
        "WP13": (
            "tests/upgrade", "tests/dossier", "tests/lanes", "tests/migration",
            "tests/migrate", "tests/post_merge", "tests/merge", "tests/coordination",
            "tests/review",
        ),
        "WP14": (
            "tests/audit", "tests/auth", "tests/tasks", "tests/missions",
            "tests/cross_cutting", "tests/docs", "tests/cli", "tests/doctor",
            "tests/core", "tests/characterization", "tests/kernel", "tests/policy",
            "tests/delivery", "tests/research", "tests/git_ops", "tests/event_journal",
            "tests/dashboard", "tests/context", "tests/ci", "tests/paths",
            "tests/init", "tests/e2e", "tests/cross_branch", "tests/concurrency",
            "tests/release", "tests/readiness", "tests/proof", "tests/mission_metadata",
            "tests/calibration",
        ),
    }
    deferred_dirs = {
        "tests/specify_cli": "#2625 (largest bucket -- WP04-owned)",
        "tests/runtime": "#2625 (WP04-owned)",
        "tests/next": "#2625 (WP03-owned)",
        "tests/integration": "#2625 (WP04-owned)",
    }

    convert_sites = [s for s in sites if s.classification == "convert" and not s.escaped]
    by_dir: dict[str, list[GoldenCountSite]] = {}
    for s in convert_sites:
        by_dir.setdefault(s.top_dir or "<root>", []).append(s)

    lines: list[str] = []
    lines.append("# Golden-count inventory (WP11, #2076/FR-014)")
    lines.append("")
    lines.append(
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by "
        "`python -m tests.architectural.test_golden_count_ban --emit-inventory`. "
        "Classification heuristic: see `tests/architectural/test_golden_count_ban.py` "
        "module docstring."
    )
    lines.append("")
    total_keep = sum(1 for s in sites if s.classification == "keep")
    total_convert = len(convert_sites)
    total_escaped = sum(1 for s in sites if s.escaped)
    lines.append(
        f"- Total `len(<collection>) == <int>` sites scanned: **{len(sites)}**\n"
        f"- `keep` (cardinality is the contract): **{total_keep}**\n"
        f"- `convert` (set/frozenset-equality is the real contract), non-escaped: "
        f"**{total_convert}**\n"
        f"- escaped via `{ESCAPE_HATCH_MARKER}`: **{total_escaped}**"
    )
    lines.append("")
    lines.append(
        "## Partition 1 -- batch-owned (WP12/WP13/WP14 burn these down)"
    )
    lines.append("")
    for wp in ("WP12", "WP13", "WP14"):
        dirs = batch_dirs[wp]
        wp_sites = [s for d in dirs for s in by_dir.get(d, [])]
        lines.append(f"### {wp} ({len(wp_sites)} convert sites across {len(dirs)} directories)")
        lines.append("")
        for d in dirs:
            d_sites = by_dir.get(d, [])
            if not d_sites:
                continue
            lines.append(f"#### `{d}` ({len(d_sites)})")
            lines.append("")
            lines.append("| File | Line | Enclosing qualname | Assertion |")
            lines.append("|---|---|---|---|")
            for s in d_sites:
                lines.append(_format_site_row(s))
            lines.append("")

    lines.append("## Partition 2 -- deferred (owned-file dir), ledgered to follow-up #2625")
    lines.append("")
    lines.append(
        "Convert-sites inside directories wholesale-owned by another WP in this "
        "mission (Lane 0/A/B) are **out of scope for this mission's batches** -- "
        "deliberately deferred and tracked here, not silently grandfathered into the "
        "baseline."
    )
    lines.append("")
    for d, note in deferred_dirs.items():
        d_sites = by_dir.get(d, [])
        lines.append(f"### `{d}` ({len(d_sites)} convert sites) -- {note}")
    lines.append("")

    lines.append(
        "## Partition 3 -- no owner in this mission (informational; neither batch-"
        "assigned nor part of the #2625 deferral)"
    )
    lines.append("")
    lines.append(
        "Directories with convert-classified sites that no WP in this mission owns "
        "wholesale or partially. Not silently grandfathered either -- listed here for "
        "visibility; the recurrence guard still bounds them at their current ceiling "
        "and any future mission may pick them up."
    )
    lines.append("")
    handled = {d for dirs in batch_dirs.values() for d in dirs} | set(deferred_dirs)
    for d in sorted(by_dir):
        if d in handled:
            continue
        lines.append(f"- `{d}` ({len(by_dir[d])} convert sites)")
    lines.append("")

    lines.append("## Partially-owned directories (noted, not batch-assigned)")
    lines.append("")
    lines.append(
        "No convert-classified site fell inside a directory this mission's ownership "
        "map marks as owned-by-file-only (rather than wholesale) by another WP as of "
        "this scan; if a future re-scan finds one, route it to the owning WP rather "
        "than a batch."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-baseline", action="store_true")
    parser.add_argument("--emit-inventory", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.freeze_baseline:
        ceilings = freeze_baseline()
        print(f"Froze {len(ceilings)} directory ceiling(s) into {_BASELINE_PATH}")
    if args.emit_inventory is not None:
        sites = scan_repo()
        args.emit_inventory.write_text(_render_inventory(sites), encoding="utf-8")
        print(f"Wrote inventory ({len(sites)} sites scanned) to {args.emit_inventory}")
    if not args.freeze_baseline and args.emit_inventory is None:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
