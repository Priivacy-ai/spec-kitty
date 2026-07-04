"""Fixture-workflow builders for the WP04 invariant fault-injection suite.

Mission ci-suite-map-bind (Wave 0), WP04. The invariant suites in
``test_marker_job_completeness.py`` / ``test_workflow_coherence.py`` /
``test_src_filter_coverage.py`` each need a *synthetic* workflow that VIOLATES
the parsed relation they guard, to prove the invariant reds (ATDD
fault-injection), plus a benign *reordered* twin to prove refactor-stability
(the FR-010/FR-012 red-negatives). Centralising the builders here keeps the
fault construction named, reusable, and out of the assertion bodies.

These builders emit the *minimum* workflow shape ``_gate_coverage``'s parser
reads for the relation under test — never a copy of the live 3,200-line
``ci-quality.yml`` (that would be the literal-mirror C-002 forbids).
"""

from __future__ import annotations

import textwrap
from pathlib import Path


def write_workflow(directory: Path, text: str, name: str = "wf.yml") -> Path:
    """Dedent ``text`` and write it as ``name`` under ``directory``."""
    path = directory / name
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def _filter_block(groups: dict[str, list[str]]) -> str:
    lines = ["          filters: |"]
    for name, globs in groups.items():
        lines.append(f"            {name}:")
        lines.extend(f"              - '{glob}'" for glob in globs)
    return "\n".join(lines)


def _unmatched_step(refs: list[str]) -> str:
    checks = "\n".join(
        f'            "${{{{ steps.filter.outputs.{ref} }}}}" \\' for ref in refs
    )
    return (
        "      - name: Compute catch-all unmatched signal\n"
        "        id: unmatched\n"
        "        env:\n"
        "          ANY_SRC: ${{ steps.filter.outputs.any_src }}\n"
        "        run: |\n"
        "          matched=false\n"
        "          for group_hit in \\\n"
        f"{checks}\n"
        '            "sentinel"; do\n'
        '            if [ "$group_hit" = "true" ]; then matched=true; fi\n'
        "          done\n"
        '          echo "unmatched=false" >> "$GITHUB_OUTPUT"\n'
    )


def filter_workflow(
    groups: dict[str, list[str]],
    *,
    unmatched_refs: list[str] | None,
    gated_jobs: dict[str, list[str]],
) -> str:
    """A ``changes`` job (dorny filter + optional unmatched step) plus gated jobs.

    ``groups`` -> dorny filter groups; ``unmatched_refs`` -> the group names the
    catch-all step enumerates (``None`` omits the step); ``gated_jobs`` maps a
    job name to the filter groups its ``if:`` gates on (each job runs pytest so
    it registers as a test-running job in the gate model).
    """
    parts = [
        "name: fixture",
        "on:",
        "  pull_request:",
        "    types: [opened, synchronize, reopened, ready_for_review]",
        "jobs:",
        "  changes:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v6",
        "      - uses: dorny/paths-filter@v4",
        "        id: filter",
        "        with:",
        _filter_block(groups),
    ]
    if unmatched_refs is not None:
        parts.append(_unmatched_step(unmatched_refs))
    for job, gate_groups in gated_jobs.items():
        cond = " || ".join(
            f"needs.changes.outputs.{g} == 'true'" for g in gate_groups
        )
        parts.extend(
            [
                f"  {job}:",
                "    needs: [changes]",
                f"    if: always() && ({cond})",
                "    runs-on: ubuntu-latest",
                "    steps:",
                "      - run: uv run pytest tests/ -m fast",
            ]
        )
    return "\n".join(parts) + "\n"
