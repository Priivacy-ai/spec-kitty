#!/usr/bin/env python3
"""Quality-gate skipped-suite decision (mission ci-suite-map-bind, FR-011).

Extracted, hermetically-testable verdict logic for the ``quality-gate``
aggregator in ``.github/workflows/ci-quality.yml``. The workflow (WP03)
assembles a single JSON document and pipes it to this script on stdin
(or via ``--input``); the script prints a Markdown run/skipped table for
``$GITHUB_STEP_SUMMARY`` and exits:

- ``0`` — all blocking suites accounted for;
- ``1`` — at least one FAIL verdict (failed/cancelled job, improperly
  skipped mapped suite, or unmet release-required job);
- ``2`` — input contract violation (malformed payload, phantom group
  reference, or the C-005 tripwire).

Input schema (one JSON object)::

    {
      "needs": {"<job>": "<result>" | {"result": "<result>", ...}, ...},
      "changes": {"<group>": "true"|"false"|bool, ...},
      "job_groups": {"<job>": ["<group>", ...], ...},
      "run_all": "true"|"false"|bool,
      "catchall_unmatched": "true"|"false"|bool,
      "pr_is_draft": "true"|"false"|bool,
      "draft_gated_jobs": ["<job>", ...],
      "release_required_jobs": ["<job>", ...]   # optional
    }

Decision table (spec FR-011 — encoded exactly)::

    full_run     = run_all OR catchall_unmatched
    filter_true  = any(changes[g] for g in job_groups.get(job, []))
    job_skipped  = needs[job] == "skipped"
    draft_exempt = job in draft_gated_jobs AND pr_is_draft
    FAIL iff filter_true AND job_skipped AND NOT full_run AND NOT draft_exempt
    failure/cancelled results always FAIL; filter-false skips stay OK.

Release-required slot: when the ``release`` filter group is true, every job
in ``release_required_jobs`` must have result ``success`` (skipped is not
enough), preserving the existing quality-gate release arm.

Two-authority rule (Adjudicated Decision 8): the ``job_groups`` mapping is
DATA generated in-workflow from the same source as the job ``if:`` gates.
This script hardcodes NO job->group knowledge; WP04's invariant asserts the
mapping equals the parsed gating.

C-005 tripwire: ``quarantine-visibility`` is non-blocking by design and must
never enter the blocking input set. If it appears anywhere in the payload's
job collections the script aborts loudly with exit code 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

QUARANTINE_JOB = "quarantine-visibility"
RELEASE_GROUP = "release"

RESULT_SUCCESS = "success"
RESULT_SKIPPED = "skipped"
VALID_RESULTS = frozenset({RESULT_SUCCESS, "failure", "cancelled", RESULT_SKIPPED})
_FAILING_RESULTS = frozenset({"failure", "cancelled"})

VERDICT_OK = "OK"
VERDICT_FAIL = "FAIL"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_CONTRACT_ERROR = 2

_MUST_BE_MAPPING = "input field {field!r} must be a JSON object"


class InputContractError(ValueError):
    """The payload violates the documented input contract."""


@dataclass(frozen=True)
class GateInput:
    """Normalized decision inputs (all workflow strings coerced)."""

    needs: dict[str, str]
    changes: dict[str, bool]
    job_groups: dict[str, tuple[str, ...]]
    run_all: bool
    catchall_unmatched: bool
    pr_is_draft: bool
    draft_gated_jobs: frozenset[str]
    release_required_jobs: tuple[str, ...]


@dataclass(frozen=True)
class JobVerdict:
    """One row of the run/skipped table."""

    job: str
    filter_state: str
    result: str
    verdict: str
    reason: str


# ---------------------------------------------------------------------------
# Payload parsing / normalization
# ---------------------------------------------------------------------------


def _coerce_bool(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise InputContractError(
        f"input field {field_name!r} must be a boolean or 'true'/'false', got {value!r}"
    )


def _coerce_result(value: object, job: str) -> str:
    result: object = value
    if isinstance(value, Mapping):
        result = value.get("result")
    if not isinstance(result, str) or result not in VALID_RESULTS:
        raise InputContractError(
            f"job {job!r} has invalid result {result!r}; "
            f"expected one of {sorted(VALID_RESULTS)}"
        )
    return result


def _parse_str_list(payload: Mapping[str, object], field_name: str) -> tuple[str, ...]:
    raw = payload.get(field_name, [])
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        raise InputContractError(f"input field {field_name!r} must be a list of job names")
    items: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            raise InputContractError(
                f"input field {field_name!r} must contain only strings, got {entry!r}"
            )
        items.append(entry)
    return tuple(items)


def _parse_needs(payload: Mapping[str, object]) -> dict[str, str]:
    raw = payload.get("needs")
    if not isinstance(raw, Mapping) or not raw:
        raise InputContractError("input field 'needs' must be a non-empty JSON object")
    return {str(job): _coerce_result(value, str(job)) for job, value in raw.items()}


def _parse_changes(payload: Mapping[str, object]) -> dict[str, bool]:
    raw = payload.get("changes")
    if not isinstance(raw, Mapping):
        raise InputContractError(_MUST_BE_MAPPING.format(field="changes"))
    return {
        str(group): _coerce_bool(value, f"changes[{group}]")
        for group, value in raw.items()
    }


def _parse_job_groups(
    payload: Mapping[str, object], changes: Mapping[str, bool]
) -> dict[str, tuple[str, ...]]:
    raw = payload.get("job_groups")
    if not isinstance(raw, Mapping):
        raise InputContractError(_MUST_BE_MAPPING.format(field="job_groups"))
    job_groups: dict[str, tuple[str, ...]] = {}
    for job, groups in raw.items():
        if not isinstance(groups, Sequence) or isinstance(groups, str | bytes):
            raise InputContractError(f"job_groups[{job!r}] must be a list of group names")
        for group in groups:
            if group not in changes:
                raise InputContractError(
                    f"job_groups[{job!r}] references filter group {group!r} "
                    "which is absent from the 'changes' outputs — the mapping "
                    "and the filter block have drifted (Decision 8)"
                )
        job_groups[str(job)] = tuple(str(group) for group in groups)
    return job_groups


def _assert_no_quarantine_job(gate: GateInput) -> None:
    """C-005 tripwire: the quarantine job must never enter the blocking set."""
    offending_collections = [
        name
        for name, jobs in (
            ("needs", gate.needs.keys()),
            ("job_groups", gate.job_groups.keys()),
            ("draft_gated_jobs", gate.draft_gated_jobs),
            ("release_required_jobs", gate.release_required_jobs),
        )
        if QUARANTINE_JOB in jobs
    ]
    if offending_collections:
        raise InputContractError(
            f"C-005 VIOLATION: {QUARANTINE_JOB!r} appeared in the blocking "
            f"input set (in: {', '.join(offending_collections)}). The "
            "quarantine job is non-blocking by design and must never be "
            "evaluated by the quality gate."
        )


def parse_payload(payload: Mapping[str, object]) -> GateInput:
    """Validate the raw JSON payload and normalize it into a :class:`GateInput`."""
    changes = _parse_changes(payload)
    gate = GateInput(
        needs=_parse_needs(payload),
        changes=changes,
        job_groups=_parse_job_groups(payload, changes),
        run_all=_coerce_bool(payload.get("run_all"), "run_all"),
        catchall_unmatched=_coerce_bool(
            payload.get("catchall_unmatched"), "catchall_unmatched"
        ),
        pr_is_draft=_coerce_bool(payload.get("pr_is_draft"), "pr_is_draft"),
        draft_gated_jobs=frozenset(_parse_str_list(payload, "draft_gated_jobs")),
        release_required_jobs=_parse_str_list(payload, "release_required_jobs"),
    )
    _assert_no_quarantine_job(gate)
    return gate


# ---------------------------------------------------------------------------
# Decision logic (spec FR-011 decision table)
# ---------------------------------------------------------------------------


def _filter_state(groups: tuple[str, ...], matched: tuple[str, ...]) -> str:
    if not groups:
        return "always-run"
    if matched:
        return f"matched ({', '.join(matched)})"
    return "unmatched"


def evaluate_job(job: str, result: str, gate: GateInput) -> JobVerdict:
    """Apply the FR-011 decision table to a single blocking job."""
    groups = gate.job_groups.get(job, ())
    matched = tuple(group for group in groups if gate.changes[group])
    filter_true = bool(matched)
    full_run = gate.run_all or gate.catchall_unmatched
    draft_exempt = job in gate.draft_gated_jobs and gate.pr_is_draft
    state = _filter_state(groups, matched)

    if result in _FAILING_RESULTS:
        return JobVerdict(job, state, result, VERDICT_FAIL, f"job {result}")
    if result != RESULT_SKIPPED:
        return JobVerdict(job, state, result, VERDICT_OK, "ran")
    if filter_true and not full_run and not draft_exempt:
        return JobVerdict(
            job,
            state,
            result,
            VERDICT_FAIL,
            f"improperly skipped: filter output(s) {', '.join(matched)} "
            "matched but the suite did not run",
        )
    if filter_true and full_run:
        return JobVerdict(job, state, result, VERDICT_OK, "superseded by full run")
    if filter_true:
        return JobVerdict(job, state, result, VERDICT_OK, "draft-exempt skip")
    return JobVerdict(job, state, result, VERDICT_OK, "legitimately skipped")


def _apply_release_arm(gate: GateInput, verdicts: list[JobVerdict]) -> list[JobVerdict]:
    if not gate.release_required_jobs or not gate.changes.get(RELEASE_GROUP, False):
        return verdicts
    missing = [job for job in gate.release_required_jobs if job not in gate.needs]
    if missing:
        raise InputContractError(
            f"release-required job(s) absent from 'needs': {', '.join(missing)}"
        )
    required = set(gate.release_required_jobs)
    return [
        replace(
            verdict,
            verdict=VERDICT_FAIL,
            reason="release-required job must succeed",
        )
        if verdict.job in required
        and verdict.result != RESULT_SUCCESS
        and verdict.verdict == VERDICT_OK
        else verdict
        for verdict in verdicts
    ]


def evaluate(gate: GateInput) -> list[JobVerdict]:
    """Verdicts for every job in the blocking ``needs`` set, in stable order."""
    verdicts = [
        evaluate_job(job, result, gate) for job, result in sorted(gate.needs.items())
    ]
    return _apply_release_arm(gate, verdicts)


# ---------------------------------------------------------------------------
# Rendering + CLI
# ---------------------------------------------------------------------------


def render_summary(verdicts: Sequence[JobVerdict]) -> str:
    """Markdown run/skipped table for ``$GITHUB_STEP_SUMMARY``."""
    lines = [
        "### Quality gate — suite run/skipped decision",
        "",
        "| Job | Filter state | Result | Verdict |",
        "| --- | --- | --- | --- |",
    ]
    for verdict in verdicts:
        cell = verdict.verdict
        if verdict.verdict == VERDICT_FAIL:
            cell = f"{VERDICT_FAIL} — {verdict.reason}"
        lines.append(
            f"| {verdict.job} | {verdict.filter_state} "
            f"| {verdict.result} | {cell} |"
        )
    failed = [verdict for verdict in verdicts if verdict.verdict == VERDICT_FAIL]
    lines.append("")
    if failed:
        names = ", ".join(f"`{verdict.job}`" for verdict in failed)
        lines.append(f"**Blocking verdicts ({len(failed)}):** {names}")
    else:
        lines.append("**All blocking suites accounted for.**")
    return "\n".join(lines)


def _read_payload(input_path: str | None) -> Mapping[str, object]:
    try:
        if input_path is None:
            document = json.load(sys.stdin)
        else:
            with open(input_path, encoding="utf-8") as handle:
                document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise InputContractError(f"cannot read decision payload: {exc}") from exc
    if not isinstance(document, Mapping):
        raise InputContractError("decision payload must be a single JSON object")
    return document


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: JSON in, Markdown table out, verdict as exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--input",
        default=None,
        help="path to the JSON payload (default: read stdin)",
    )
    args = parser.parse_args(argv)
    try:
        gate = parse_payload(_read_payload(args.input))
        verdicts = evaluate(gate)
    except InputContractError as exc:
        print(f"::error::quality-gate decision input contract violated: {exc}", file=sys.stderr)
        return EXIT_CONTRACT_ERROR
    print(render_summary(verdicts))
    failed = [verdict for verdict in verdicts if verdict.verdict == VERDICT_FAIL]
    if failed:
        for verdict in failed:
            print(
                f"::error::{verdict.job}: {verdict.reason} "
                f"(filter state: {verdict.filter_state}, result: {verdict.result})",
                file=sys.stderr,
            )
        return EXIT_FAIL
    return EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
