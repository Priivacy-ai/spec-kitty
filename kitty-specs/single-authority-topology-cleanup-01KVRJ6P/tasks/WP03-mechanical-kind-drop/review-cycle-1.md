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
