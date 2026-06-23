---
affected_files: []
cycle_number: 2
mission_slug: single-authority-topology-cleanup-01KVRJ6P
reproduction_command:
reviewed_at: '2026-06-23T08:43:12Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
review_artifact_override_at: "2026-06-23T08:57:27Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP03"
review_artifact_override_reason: "Cycle 2 APPROVED: transitional kind=PRIMARY default makes the drop behavior-neutral; mypy call-arg errors at safe_commit_cmd.py:243,263 resolved (only pre-existing no-any-return:71 remains); 8 PRIMARY drops intact; no CommitTargetKind imports remain in 5 owned files; out-of-map context.py edit is exactly 1 line with rationale; WP01 ratchet green (10/10); test_commit_target_kind_default_is_primary PASSED; 16/16 tests pass; ruff clean. --force: lane-c is 94 commits behind feat/single-authority-topology-cleanup but rebase conflicts on planning artifacts (kitty-specs/spec.md, issue-matrix.md) — conflict is in non-code files only, all code checks passed."
---

# WP03 Review — Cycle 1: CHANGES REQUESTED

**Verdict:** the mechanical `kind=PRIMARY` drop is NOT behavior-neutral as it stands, and leaves 2 new mypy `call-arg` errors — a DoD violation ("ruff/mypy clean; full tests green; behavior-neutral").

## Blocking issue — `CommitTarget.kind` has no default

`CommitTarget` (`src/mission_runtime/context.py`) is:
```python
@dataclass(frozen=True)
class CommitTarget:
    ref: str
    kind: CommitTargetKind   # <-- NO default
```
So dropping `kind=CommitTargetKind.PRIMARY` turns `CommitTarget(ref=…, kind=PRIMARY)` into `CommitTarget(ref=…)`, which is a **missing-required-argument TypeError at runtime** (and the 2 mypy `call-arg` errors at `safe_commit_cmd.py:243,263`). This is broken in the intermediate state, not behavior-neutral. "Resolves when WP16 lands" is not acceptable — every WP must be green on its own.

## Required fix — add the transitional default (justified out-of-map edit)

Add a default to the dataclass so the drop is genuinely behavior-neutral:
```python
    ref: str
    kind: CommitTargetKind = CommitTargetKind.PRIMARY   # transitional; field removed by WP16
```
- `context.py` is owned by WP02/WP04/WP16 (same lane B, sequential, dependency-ordered after WP02) — this is a **legal, justified out-of-map edit**; record the one-line rationale ("makes the FR-001a kind=PRIMARY drop behavior-neutral; the field itself is removed by WP16").
- Order is valid: `ref` (no default) precedes `kind` (default).
- After this, `CommitTarget(ref=…)` constructs with PRIMARY (the prior implicit value) → behavior-identical; COORDINATION sites still pass `kind` explicitly; mypy `call-arg` errors resolve.
- WP14/WP15 (the other mechanical-drop slices) inherit this default from your lane tip.

## Verify
- `mypy` clean on `safe_commit_cmd.py` (no call-arg errors) + `context.py`.
- A focused test (or existing construction-exercising test) confirms `CommitTarget(ref="x").kind is CommitTargetKind.PRIMARY` (the default is wired) — assert the observable default, behavior-neutral.
- Full owned-file + ratchet tests stay green.

The 8 PRIMARY-site drops + import cleanups + the ratchet shrink are otherwise correct — keep them.
