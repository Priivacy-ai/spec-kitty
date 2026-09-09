"""Single gate-selection authority (FR-016 / #2476).

This module is the one authority for "which shards/gates does a changed-path set
select". It **parses** the two hand-authored routing authorities straight out of
the on-disk ``.github/workflows/ci-router.yml``:

1. the dorny ``changes`` filter block — ``group -> globs[]`` (path -> group), and
2. the job ``if: needs.changes.outputs.<group>`` gates — group -> job.

It never re-encodes the routing as a second hand-maintained map: that duplication
is the very #2476 hazard this module exists to close. It is reused by CI routing,
the WP17 completeness oracle, and WP18 local pre-PR parity — one parser, one
answer, no drift.

Public API:
    ``load_router(path=None) -> Router``   parse the two authorities.
    ``select_gates(changed_paths, *, router=None, mode="pr") -> GateSelection``
                                            answer the selection question.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "DEFAULT_ROUTER_PATH",
    "PROBE_GROUPS",
    "GateSelection",
    "Router",
    "load_router",
    "select_gates",
]

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUTER_PATH = _REPO_ROOT / ".github" / "workflows" / "ci-router.yml"

# The ``any_src`` filter row is the FR-004 fail-closed PROBE (matches any
# ``src/**``), consumed only by the router's ``unmatched`` step. It is never a
# routing group and is never gated on a job (contract Invariant 1).
PROBE_GROUPS = frozenset({"any_src"})

_GROUP_REF = re.compile(r"needs\.changes\.outputs\.([A-Za-z0-9_]+)")


@dataclass(frozen=True)
class Router:
    """The two parsed routing authorities of ``ci-router.yml``.

    ``filters`` is authority 1 (path -> group); ``job_gates`` is authority 2
    (job -> the groups its ``if:`` references). Everything else below is derived.
    """

    filters: dict[str, tuple[str, ...]]
    job_gates: dict[str, frozenset[str]]

    @property
    def routing_groups(self) -> frozenset[str]:
        """Every filter group except the fail-closed probe."""
        return frozenset(group for group in self.filters if group not in PROBE_GROUPS)

    @property
    def src_backed_groups(self) -> frozenset[str]:
        """Routing groups carrying at least one ``src/`` glob (code, not data)."""
        return frozenset(group for group in self.routing_groups if any(glob.startswith("src/") for glob in self.filters[group]))

    @property
    def always_on_jobs(self) -> frozenset[str]:
        """Jobs with no filter-group gate — they run unconditionally."""
        return frozenset(job for job, groups in self.job_gates.items() if not groups)

    @property
    def code_shard_jobs(self) -> frozenset[str]:
        """Gated jobs whose ``if:`` references at least one src-backed group."""
        src = self.src_backed_groups
        return frozenset(job for job, groups in self.job_gates.items() if groups & src)


@dataclass(frozen=True)
class GateSelection:
    """The answer to "what does this diff select", derived from the two authorities."""

    matched_groups: frozenset[str]
    unmatched_src: bool
    selected_jobs: frozenset[str]
    selected_code_shards: frozenset[str]


def _dorny_filters(workflow: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    changes = workflow["jobs"]["changes"]
    for step in changes["steps"]:
        if "dorny/paths-filter" in str(step.get("uses", "")):
            raw = step["with"]["filters"]
            parsed = yaml.safe_load(raw) if isinstance(raw, str) else raw
            return {group: tuple(str(g) for g in (globs or ())) for group, globs in parsed.items()}
    raise ValueError("ci-router.yml `changes` job has no dorny/paths-filter step")


def _job_gates(workflow: dict[str, Any]) -> dict[str, frozenset[str]]:
    gates: dict[str, frozenset[str]] = {}
    for name, job in workflow["jobs"].items():
        if name == "changes" or not isinstance(job, dict):
            continue
        condition = job.get("if")
        gates[name] = frozenset(_GROUP_REF.findall(str(condition))) if condition else frozenset()
    return gates


def load_router(path: Path | None = None) -> Router:
    """Parse the two routing authorities out of ``ci-router.yml``."""
    workflow = yaml.safe_load((path or DEFAULT_ROUTER_PATH).read_text(encoding="utf-8"))
    return Router(filters=_dorny_filters(workflow), job_gates=_job_gates(workflow))


def _match_groups(paths: list[str], router: Router) -> frozenset[str]:
    hit: set[str] = set()
    for group, globs in router.filters.items():
        if group in PROBE_GROUPS:
            continue
        if any(fnmatch.fnmatch(path, pattern) for pattern in globs for path in paths):
            hit.add(group)
    return frozenset(hit)


def select_gates(
    changed_paths: Iterable[str | Path],
    *,
    router: Router | None = None,
    mode: str = "pr",
) -> GateSelection:
    """Return which jobs / code shards a changed-path set selects.

    ``mode="full"`` (or an unmapped ``src/**`` change — the FR-004 fail-closed
    catch-all) forces run-all: every routing group is selected. Otherwise only
    the groups the paths matched are selected. Always-on jobs (no filter group)
    are always included; ``selected_code_shards`` is the src-backed subset.
    """
    router = router or load_router()
    paths = [str(path) for path in changed_paths]
    matched = _match_groups(paths, router)

    any_src = any(path.startswith("src/") for path in paths)
    unmatched_src = any_src and not (matched & router.src_backed_groups)

    run_all = mode == "full" or unmatched_src
    selected_groups = router.routing_groups if run_all else matched

    gated_selected = frozenset(job for job, groups in router.job_gates.items() if groups and (groups & selected_groups))
    return GateSelection(
        matched_groups=matched,
        unmatched_src=unmatched_src,
        selected_jobs=router.always_on_jobs | gated_selected,
        selected_code_shards=gated_selected & router.code_shard_jobs,
    )
