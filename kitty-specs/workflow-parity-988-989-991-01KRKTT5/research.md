# Research — Workflow Parity Fixes 988/989/991

## #988 — next --json claimability parity

### Code map

- Payload builder: `src/specify_cli/next/decision.py:115` (`Decision.to_dict()`)
- CLI emission: `src/specify_cli/cli/commands/next_cmd.py:353` (`_print_decision()`)
- Current discovery primitive (read-only event-log scan): `src/specify_cli/next/decision.py:338` (`_find_first_wp_by_lane()`)
- Canonical claim algorithm used by explicit action: `src/specify_cli/status/work_package_lifecycle.py:98` (`start_implementation_status()`), invoked from `src/specify_cli/cli/commands/implement.py:580` (`implement()`).

### Decision

Add a side-effect-free **discovery** helper in `src/specify_cli/next/discovery.py` (or extend the existing module) that mirrors the candidate-selection portion of `start_implementation_status()`. The helper returns:

```python
@dataclass(frozen=True)
class ClaimablePreview:
    wp_id: str | None
    selection_reason: str | None  # e.g. "no_planned_wps", "all_wps_in_progress", "dependencies_unsatisfied"
    candidates: tuple[str, ...]   # WPs that would be considered, in deterministic order
```

The `next --json` payload builder calls this helper when `mission_state == "implement"` and `preview_step == "implement"`, then writes `wp_id` and `selection_reason` into the JSON payload.

### Rationale

- Sharing the candidate-selection list keeps the two surfaces in sync without forcing `next --json` to actually mutate state (which would be wrong — `next` is read-only).
- A structured `selection_reason` satisfies FR-002 and lets agents distinguish "nothing to do" from "all WPs claimed by other agents" without re-parsing event logs.

### Alternatives considered

- **Have `next --json` call `start_implementation_status()` in a dry-run mode.** Rejected: requires plumbing a `commit=False` flag through the entire status emission pipeline. Adds risk for unrelated commands.
- **Leave selection in `_find_first_wp_by_lane()` and just enrich the message.** Rejected: violates FR-003 (single implementation path).

## #989 — lightweight review dead-code skip

### Code map

- Dead-code skip message: `src/specify_cli/cli/commands/review/_dead_code.py:30` (`scan_dead_code()`)
- Mode dispatch: `src/specify_cli/cli/commands/review/__init__.py:45` (`review_mission()`)
- Mode resolution: `src/specify_cli/cli/commands/review/_mode.py:57` (`resolve_mode()`); peer diagnostic at `_mode.py:24` (mode mismatch error for `post-merge`)
- Diagnostic registry: `src/specify_cli/cli/commands/review/_diagnostics.py:21` (`MISSION_REVIEW_MODE_MISMATCH`)

### Decision

Introduce a new structured diagnostic code `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` (added to `_diagnostics.py` alongside `MISSION_REVIEW_MODE_MISMATCH`). When `scan_dead_code()` is called from the lightweight path:

1. If `baseline_merge_commit` is non-null → run scan as today, no behavior change.
2. If `baseline_merge_commit` is null AND the mission is modern (has `mission_id` set in `meta.json`) → return a non-passing diagnostic whose payload includes `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`, the mission identity, and the remediation hint ("run merge to bake a baseline_merge_commit, or use `--mode post-merge` after merge").
3. If the mission is genuinely legacy (no `mission_id` field present, i.e., pre-`mission-id-canonical-identity-migration` schema) → preserve current "skipped" pass behavior but tag the diagnostic with `LEGACY_MISSION_DEAD_CODE_SKIP` so the path is still discoverable.

### Rationale

- Spec C-005 forbids silent fallback; the legacy path must be opt-in via mission schema signal. `mission_id` is the canonical marker introduced in mission `083-mission-id-canonical-identity-migration` (see `src/specify_cli/CLAUDE.md` — "Mission Identity Model (083+)"), so its presence cleanly identifies modern missions.
- Reusing the diagnostic pattern from `MISSION_REVIEW_MODE_MISMATCH` keeps the structured-failure surface uniform.

### Alternatives considered

- **Always fail lightweight mode without baseline_merge_commit, including legacy missions.** Rejected: violates FR-006 and risks breaking existing CI pipelines on the small number of pre-083 missions still tracked.
- **Downgrade verdict to "incomplete" instead of failing.** Considered viable; rejected in favor of a hard fail because operators reading green/red signals do not parse a third "incomplete" state reliably. The hard fail with a structured code is the safer default.

## #991 — merge --dry-run review artifact parity

### Code map

- Diagnostic constant: `src/specify_cli/post_merge/review_artifact_consistency.py:12` (`REJECTED_REVIEW_ARTIFACT_CONFLICT`)
- Detection gate: `src/specify_cli/post_merge/review_artifact_consistency.py:53` (`find_rejected_review_artifact_conflicts()`)
- Diagnostic emitter: `src/specify_cli/post_merge/review_artifact_consistency.py:101` (`review_artifact_conflict_diagnostic()`)
- Merge CLI: `src/specify_cli/cli/commands/merge.py` (real merge path calls the gate; dry-run path at lines 549–614 bypasses it).

### Decision

Extract the existing gate invocation into a single helper `run_review_artifact_consistency_preflight(...)` that is called from **both** the real-merge path and the dry-run path. The dry-run path must:

- Always invoke the preflight before computing the merge preview.
- On detection, exit non-zero, print the human-readable diagnostic, and (when `--json` is set) emit a JSON payload whose top-level `blockers` (or analogous list — match the real merge's existing key) includes the `REJECTED_REVIEW_ARTIFACT_CONFLICT` entry with the same shape the real merge uses.
- On no detection, fall through to the existing dry-run preview logic with zero behavior change.

### Rationale

- The real-merge consistency gate already exists and is well-tested (`tests/post_merge/test_review_artifact_consistency.py`). The dry-run fix is wiring, not new gate logic.
- Re-using the same emitter guarantees identical JSON shape between dry-run and real merge (FR-008 / FR-009).

### Alternatives considered

- **Add a fresh dry-run-only gate that approximates the real gate.** Rejected: violates FR-007 (single implementation path) and would drift over time.
- **Make the dry-run preview optimistic and document the gap.** Rejected: this is exactly the bug the mission exists to fix.

## Cross-cutting concerns

- **Mypy --strict**: All new helpers are fully typed; new dataclasses are `frozen=True`.
- **No new dependencies**: All changes stay inside existing modules; no new top-level packages.
- **Test infrastructure**: Existing pytest fixtures (`tmp_path`, mission scaffolding helpers) cover the three new tests.
- **SaaS sync**: Not touched. New tests run without the env var.
