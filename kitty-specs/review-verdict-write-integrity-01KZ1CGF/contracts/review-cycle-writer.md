# Contract: Generalized review-cycle writer

No external/REST/GraphQL contract applies to this mission — it is entirely internal Python behavior.
This document is the internal function-contract equivalent, per this repo's own convention of using
`contracts/` for behavioral contracts on internal seams (cf. `specify-plan-commit-boundary.md`).

## `create_rejected_review_cycle` → generalized writer (name unchanged; behavior extended)

**Before this mission**: writes only `verdict="rejected"` artifacts; validates `feedback_source` only
for existence/is-file/non-empty.

**After this mission**:

```
def create_rejected_review_cycle(
    *,
    main_repo_root: Path,
    mission_slug: str,
    wp_id: str,
    wp_slug: str,
    feedback_source: Path,
    reviewer_agent: str = "unknown",
    affected_files: list[dict[str, str]] | None = None,
    verdict: Literal["approved", "rejected"] = "rejected",   # NEW — default preserves every existing call site
    commit_router: CoordCommitRouter | None = None,   # NEW — optional, see commit-step note below
) -> CreatedRejectedReviewCycle:
```

**Contract**:

- **Backward compatibility**: there are two pre-existing callers —
  `_mt_finalize_plan`'s rejection and approval paths in `tasks_move_task.py`, and
  `_persist_review_feedback` in `tasks_materialization.py` — both continue to work unchanged, since
  `verdict` defaults to `"rejected"` and `commit_router` defaults to `None`.
- **New behavior (`verdict="approved"`)**: writes a new highest-numbered `review-cycle-(N+1).md` with
  `verdict: "approved"`, the caller-supplied `reviewer_agent` (must be real — the caller, not this
  function, is responsible for never passing the literal placeholder for a genuine approval), through
  the same `_review_cycle_wp_dir` seam unchanged.
- **New provenance guard (both verdicts)**: raises `ReviewCycleError` before writing if `feedback_source`
  is, by path or by content, a prior cycle's own artifact for this WP (see `data-model.md`'s Feedback-
  source acceptance transition). Applies uniformly — an `approved` write also goes through this guard,
  since a caller could in principle mis-supply a stale file for either verdict.
- **New commit step (both verdicts) — added post-plan, see `research.md` R1's correction**: after
  `artifact.write(artifact_path)` succeeds, the function commits the written file via the existing
  `commit_artifact` port capability (today called only from `tasks_mark_status.py`/
  `tasks_map_requirements.py`; this is its first review-cycle call site). Live reproduction confirmed
  the write was previously never committed by anything in the `move-task` pipeline — this closes that
  gap for both verdicts, and closes #2697 as the same underlying mechanism. `commit_router` is
  optional precisely so the second pre-existing caller, `_persist_review_feedback`
  (`tasks_materialization.py`), keeps compiling unchanged — but that caller does not pass
  `commit_router` at all, so its writes still land uncommitted; only `_mt_finalize_plan`'s two
  `tasks_move_task.py` call sites thread it, and only when auto-commit is resolved on.
- **Unchanged**: cycle-number assignment (`ReviewCycleArtifact.next_cycle_number`), the write target
  (`_review_cycle_wp_dir`, PRIMARY-partition, `WORK_PACKAGE_TASK` kind), and `validate_review_artifact`'s
  role as a post-construction sanity check (loosened per `research.md` R4 to accept both verdicts, not
  removed).

## `validate_review_artifact`

**Before**: `if artifact.verdict != "rejected": raise ReviewCycleError(...)`.
**After**: `if artifact.verdict not in REVIEW_ARTIFACT_VERDICTS: raise ReviewCycleError(...)` — matches
the schema-level `REVIEW_ARTIFACT_VERDICTS` frozenset already in `review/artifacts.py`, no new
vocabulary introduced (C-002).

## `_get_wp_review_verdict` (agent_utils/status.py) — RETRACTED redesign, verify-first instead

**Original plan-phase design** (retracted post-plan, see `research.md` R3's correction): resolve the
WP's event-sourced review state first via `resolve_snapshot_review(feature_dir, wp_id)`, falling back
to the existing file-glob read only when no snapshot entry exists. **This does not work**:
`resolve_snapshot_review` returns `ReviewOverride`, which has no `verdict` field — it cannot supply a
review verdict, only override actor/reason. Retracted before any code was written against it.

**Actual contract for this mission**: `_get_wp_review_verdict`'s signature and behavior are **UNCHANGED**
unless FR-003's post-FR-001 verification (see `plan.md` IC-02) finds the stale-verdict warning still
fires. If verification fails, the fix must be designed against the actual observed failure mode at that
time — not against this retracted design — and this contract document should be updated again before
that fix is implemented.
