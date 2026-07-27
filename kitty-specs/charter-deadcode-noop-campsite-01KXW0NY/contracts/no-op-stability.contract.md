# Contract — Governed charter operations are no-op-stable

**Requirements:** FR-005, FR-006, FR-007; NFR-001, NFR-003. **Invariants:** INV-1, INV-2, INV-6.

## Statement

A *governed charter operation* — any read/render/gate that consults charter or doctrine state
without the user explicitly asking to (re)generate — MUST NOT modify a git-tracked artifact.
Running such an operation on an unchanged, **doctrine-tracked** tree, any number of times, leaves
`git status --porcelain` empty.

Governed operations in scope:
- `spec-kitty charter context [--action …]` (render path — `build_charter_context`)
- `spec-kitty doctor doctrine`
- any preflight-gated command (`next`, `implement`, dashboard) via `run_charter_preflight`

## Preconditions

- Clean working tree.
- `.kittify/doctrine/**` is git-tracked (the committed `.gitignore` state) — NOT the local
  `.git/info/exclude` masked state. Tests establish this explicitly (remove the exclude / use a
  fresh clone) so the assertion is meaningful.

## Guarantees

| # | Given | When | Then |
|---|-------|------|------|
| G1 | clean tree, `synthesized_drg` fresh | `charter context` renders | 0 tracked-file diffs (only untracked `context-state.json` may change) |
| G2 | clean tree, `synthesized_drg` fresh | preflight-gated command runs | `charter synthesize` is NOT invoked; 0 tracked-file diffs |
| G3 | clean tree | any governed op runs **twice** | 2nd run: 0 tracked-file diffs |
| G4 | `charter.yaml` genuinely edited | preflight-gated command runs | synthesize DOES run; doctrine refreshed (INV-2 — no over-suppression) |

## Non-guarantees

- Untracked runtime state (`.kittify/charter/context-state.json`) MAY be written — it is gitignored
  by design.
- An explicit `spec-kitty charter synthesize` / write command MAY (and should) regenerate artifacts.

## Test obligations (red-first)

- Extend `tests/charter/test_context.py` with a git-clean assertion after `build_charter_context`
  against a real charter in a doctrine-tracked temp repo (G1/G3).
- Add a preflight no-op ratchet asserting G2/G3 in `tests/specify_cli/charter_runtime/`.
- Add an INV-2 test (G4) so the fix cannot over-suppress genuine staleness.
