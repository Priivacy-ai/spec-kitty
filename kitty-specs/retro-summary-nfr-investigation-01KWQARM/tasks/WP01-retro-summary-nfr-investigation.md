---
work_package_id: WP01
title: Retro-summary NFR investigation + report
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: fix/retro-summary-nfr-investigation
merge_target_branch: fix/retro-summary-nfr-investigation
branch_strategy: Planning artifacts for this mission were generated on fix/retro-summary-nfr-investigation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/retro-summary-nfr-investigation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Investigation
assignee: ''
agent: "claude"
shell_pid: "2011204"
history:
- at: '2026-07-04T23:19:29Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/plans/engineering-notes/2342-retro-summary-nfr/
create_intent:
- docs/plans/engineering-notes/2342-retro-summary-nfr/report.md
- docs/plans/engineering-notes/2342-retro-summary-nfr/evidence/profile_harness.py
- docs/plans/engineering-notes/2342-retro-summary-nfr/evidence/profiling.txt
- docs/plans/engineering-notes/2342-retro-summary-nfr/evidence/bisect.log
- docs/plans/engineering-notes/2342-retro-summary-nfr/evidence/oracle-proof.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/plans/engineering-notes/2342-retro-summary-nfr/report.md
- docs/plans/engineering-notes/2342-retro-summary-nfr/evidence/**
- src/specify_cli/retrospective/reader.py
- src/specify_cli/retrospective/schema.py
- src/specify_cli/retrospective/summary.py
- tests/retrospective/test_summary_tolerance.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Retro-summary NFR investigation + report

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` before parsing the rest. Then work with an investigator's rigor: measure, don't assume; prove the oracle before trusting a bisect; state a single evidence-backed verdict.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Deliver a committed report with a definitive **verdict** (real regression | CI variance | inconclusive) on `tests/retrospective/test_summary_tolerance.py::test_200_missions_under_5s` (NFR-003) and **one recommended disposition**. Ship code only if a clean, low-risk root-cause regression falls out.

Done when the report records: ≥5-run profiling (median + spread, per-phase); a bisection outcome (regressing SHA or substantiated "no discrete regression", or "inconclusive" if the oracle couldn't be made to flip); one verdict; one recommended disposition with enactment + quarantine-lift steps; and — if a clean fix was applied — the test passes at 5.0s with the quarantine marker removed.

**Reproducible-evidence rule (non-negotiable — no prose-only claims).** Every number and verdict must be re-runnable by a reviewer, committed under `evidence/`:
- `evidence/profile_harness.py` — the runnable harness that builds the corpus and regenerates the profiling table.
- `evidence/profiling.txt` — the raw cProfile/pstats dump (the source of the report's per-phase numbers).
- `evidence/bisect.log` — the actual `git bisect log`.
- `evidence/oracle-proof.md` — the exact oracle command + measured seconds for a known-**BAD** and a known-**GOOD** endpoint proving the oracle flips. For an **inconclusive** verdict, this file must instead show the measured seconds where the known-bad endpoint did **not** read red AND the relative-delta threshold that failed to separate endpoints — otherwise "inconclusive" is indistinguishable from "skipped the bisect" and is rejected.

## Context & Constraints

- Charter: `.kittify/charter/charter.md`. Plan: [../plan.md](../plan.md). **Evidence base + methodology: [../research.md](../research.md) — read it first.**
- **The hot path is NOT `summary.py`.** `summary.py:421` is only the call site `record = read_record(retro_path)`. The measured cost lives in `reader.py` (`read_record` :333, `_load_yaml_mapping` :117, `_coerce_legacy_schema_versions` :355) and the Pydantic validation `RetrospectiveRecord.model_validate(...)` **called at `reader.py:355`** (the `RetrospectiveRecord` model is *defined* at `schema.py:380` — do not hunt for a `model_validate` symbol in schema.py; it's the pydantic-inherited classmethod invoked from reader.py), run ×200. Per-mission `YAML()` construction is ~0.2% of budget — a red herring.
- **Flippable-oracle rule (C-005).** Local hardware is faster than CI. Do NOT trust `git bisect run` with the raw `assert elapsed < 5.0` oracle unless you first prove a known-bad endpoint reads red on this machine. Otherwise use a **relative per-phase-delta** oracle with an explicit bad/good threshold. If the oracle cannot be made to flip across the window → verdict = **inconclusive**, not "no regression."
- **No budget-bump-to-green** (charter flakiness policy): the disposition may never be "raise the budget."
- **Reuse the corpus fixture** the test builds (`tests/retrospective/test_summary_tolerance.py`) as the profiling workload — do not invent a new one.
- Env: `.venv/bin/python`, `uv run`. Python 3.11.15.

## Branch Strategy
- **Strategy**: pr-bound (already-confirmed) · **Planning/merge base**: `fix/retro-summary-nfr-investigation`

## Subtasks & Detailed Guidance

### T001 — Profile build_summary (≥5 runs, per-phase)
- Build the test's 200-mission corpus (reuse the fixture from `test_summary_tolerance.py`; read it to see how the corpus is constructed).
- Run `cProfile` over `build_summary(corpus)` ≥5 times; capture `pstats` sorted by cumulative + tottime. Report **median + min–max** wall-time and a per-phase breakdown: filesystem scan, YAML parse (`reader.py:_load_yaml_mapping`), schema coerce+validate (`reader.py:_coerce_legacy_schema_versions` + `schema.py:model_validate`), reduce. Confirm/refute that the parse+validate path dominates.
- Record the raw numbers for the report.

### T002 — Establish a flippable oracle
- Attempt the 5.0s test oracle on this hardware at HEAD and at an old endpoint; if it never reads red, it is NOT flippable here. Instead define a **relative** oracle: a per-phase (or total build_summary) time threshold derived from the T001 median (e.g. "regression = cumulative parse+validate time > K× the pre-window baseline") that DOES flip across a known-bad/known-good pair.
- Prove the oracle flips: show one commit it marks BAD and one it marks GOOD before running the full bisect.

### T003 — Bisect with the flippable oracle
- Candidate window: `git log --oneline -- src/specify_cli/retrospective/reader.py src/specify_cli/retrospective/schema.py src/specify_cli/retrospective/summary.py`. Explicitly include `0818c7590` (#1778 — rewrote `_load_yaml_mapping` + added a per-record coerce pass on the hot path).
- Run `git bisect` (scripted with the flippable oracle) across that window. Record: regressing commit SHA (+ what it changed), or a substantiated "no discrete regression across the window." If the oracle could not flip → record **inconclusive**.
- **Confirm the corpus exercises the suspected branch** before trusting a flat delta (the retrospective-only corpus writes `retrospective.yaml` with no `meta.json`, so some read-path branches are dead).

### T004 — Verdict + disposition + report
- Create `docs/plans/engineering-notes/2342-retro-summary-nfr/report.md` with: the T001 profiling table, the T002 oracle design, the T003 bisection outcome, **one** verdict, and **one** recommended disposition from the issue matrix — real regression → fix + restore 5.0s + lift quarantine; CI-flake → dedicated non-blocking perf slice **or** `local_only` — with concrete enactment steps, the quarantine-lift step, and the maintainer's week-long `quarantine-visibility` variance-collection follow-up (out of session scope).

### T005 — Conditional clean fix
- **Only if** T003 found a clean, low-risk root-cause regression: apply the minimal `reader.py`/`schema.py` fix, restore `test_200_missions_under_5s` to 5.0s, remove the `@pytest.mark.quarantine` marker, and prove the test green (`mypy --strict` + `ruff` clean on any changed code, no new suppressions). **Otherwise ship no code** — the report states why the quarantine remains. Do not attempt a large/speculative fix; recommend it instead.

## Test Strategy
The deliverable is primarily the report. Any code fix (T005) must keep the full `tests/retrospective/` suite green and pass `mypy --strict` + `ruff`.

## Risks & Mitigations
- **Wrong-file trap**: profile/bisect `reader.py`+`schema.py`, not `summary.py` alone (the whole reason the plan was remediated).
- **False-GOOD bisect** on fast local hardware: mitigated by the mandatory flippable-oracle proof (T002).
- **Over-reach**: a large fix is out of scope — recommend, don't ship it.

## Review Guidance
- **Reject prose-only numbers.** Confirm the committed `evidence/` set exists and is re-runnable: run `evidence/profile_harness.py` and check it regenerates the report's table; confirm `evidence/profiling.txt` (pstats), `evidence/bisect.log` (real `git bisect log`), and `evidence/oracle-proof.md` are present and consistent with the report.
- Confirm the profiling is ≥5 runs with median+spread and a real per-phase breakdown targeting reader.py/schema.py.
- **Confirm the oracle-proof shows an actual BAD+GOOD flip** (measured seconds) before any non-inconclusive verdict; for an **inconclusive** verdict, confirm the committed failed-flip transcript (known-bad did not read red + the failed relative-delta threshold) — an unsubstantiated "inconclusive" is a reject.
- Confirm exactly one verdict + one disposition with enactment + quarantine-lift steps; no budget-bump recommendation.
- If a fix shipped: test green at 5.0s, quarantine removed, mypy/ruff clean.

## Activity Log
- 2026-07-04T23:19:29Z – system – Prompt created.
- 2026-07-04T23:31:53Z – claude – shell_pid=1928588 – Assigned agent via action command
- 2026-07-04T23:52:34Z – claude – shell_pid=1928588 – Ready for review: verdict=CI variance, disposition=keep quarantine+quarantine-visibility, no code shipped (T005 N/A)
- 2026-07-04T23:53:14Z – claude – shell_pid=1971213 – Started review via action command
- 2026-07-04T23:58:25Z – user – shell_pid=1971213 – Moved to planned
- 2026-07-04T23:59:04Z – claude – shell_pid=1983345 – Started implementation via action command
- 2026-07-05T00:01:09Z – claude – shell_pid=1983345 – Moved to for_review
- 2026-07-05T00:01:42Z – claude – shell_pid=1992952 – Started review via action command
- 2026-07-05T00:06:30Z – user – shell_pid=1992952 – Moved to planned
- 2026-07-05T00:07:07Z – claude – shell_pid=2003128 – Started implementation via action command
- 2026-07-05T00:08:37Z – claude – shell_pid=2003128 – Moved to for_review
- 2026-07-05T00:09:05Z – claude – shell_pid=2011204 – Started review via action command
