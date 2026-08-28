# WP06 review — cycle 1 — CHANGES REQUESTED

## What's solid (independently re-verified, not just re-read)

- **Baseline SHA is genuine, not guessed.** `_MERGE_BASE_COMMIT = 1aed89411b...` was
  confirmed to equal `git merge-base main kitty/mission-charter-preflight-remediation-01KYG9WK`
  **and** local `main`'s own tip — i.e. they used the true pre-mission merge-base, not
  `fix/charter-preflight-remediation`'s current tip (which already carries WP03/WP05 merge
  commits and would have made the comparison vacuous). Confirmed by direct `git merge-base`
  re-run in this review.
- **All four baseline cells independently re-derived**, not just two. Using a detached
  `git worktree add` at the baseline SHA and that commit's own lower-level fixture
  primitives (`init_git_repo`, `seed_charter_yaml`, `seed_charter`/`write_metadata`/
  `seed_bundle_files` — the WP01 `build_fN_*` wrappers don't exist yet at that commit, which
  the module docstring says and I confirmed), all four `(mutation_gate_blocked,
  advisory_blocked)` pairs matched the frozen `_BASELINE` table exactly:
  F1=(True,False), F2=(True,False), F3=(False,False), F4=(True,True). The frozen table is
  real measured data, not decorative.
- **Before/after arms measure different trees.** After-arm uses WP01's `build_fN_*`
  fixtures against the mission tip (WP01-WP05 present); before-arm is the baseline
  worktree. Re-ran F1 against the tip directly and got the same result as frozen baseline
  (True,False) — consistent, not coincidentally-identical-tree.
- **FR-006 "pre-existing" claim checked, not just accepted**: diffed
  `runner.py`'s `_is_optional_missing_charter_fresh_project` (the function that decides
  whether F1 is waved through as advisory) baseline-to-tip — byte-identical except for a
  docstring comment. The surrounding `run_charter_preflight` mutation-gate logic is also
  unchanged (only line-offset diff from unrelated docstring growth). The claim that "the
  mutation gate fails closed on F1 by pre-existing design" is verified true, not merely
  asserted.
- **T028 reproduced for a different shape (F3, not the F1 example in the docstring).**
  Swapped F3's builder to `build_f4_invalid_charter_yaml` while keeping its recorded
  baseline (`mutation_gate_blocked=False`); got exactly:
  `shape 'F3' newly blocks the MUTATION gate ... before=False after=True`. Reverted;
  `git status` clean afterward.
- Per-shape assertion (not aggregate-only), fixture reuse from WP01's `_fixtures.py`
  (DIRECTIVE_044), `ruff check` and `mypy --strict` both clean on the new file, and the
  file itself runs green in isolation: `32 passed` on
  `tests/architectural/test_charter_blocking_envelope.py`.

## Issue: T030's diagnostic-surface coverage is incomplete, and the gap is a real bug

T030's own framing is unconditional: "exercise **every** operator-facing diagnostic surface
WP04 converged" (subtask steps) and the DoD checkbox reads "No uncaught exceptions on **any**
surface for **any** shape" — not scoped to "surfaces we happened to pick." WP04's binding doc
(`WP04-converge-charter-presence-resolution.md`) enumerates **nine** operator-reachable
resolvers (R-003), including **site 7 — `cli/commands/charter_bundle.py:363`** (the `charter
bundle validate` command), which is one of WP04's own `owned_files`.

`_DIAGNOSTIC_CLI_INVOCATIONS` in this module tests six CLI invocations but never invokes
`charter bundle validate` at all. I added it myself and ran it against all four shapes, both
plain and `--json`:

```
F1 bundle validate            rc=1  traceback? False
F2 bundle validate            rc=1  traceback? False
F3 bundle validate            rc=1  traceback? False
F4 bundle validate            rc=1  traceback? True   <-- uncaught ruamel.yaml.ParserError
F4 bundle validate --json     rc=1  traceback? True   <-- same, breaks the --json contract too
```

This is real and reproducible: `validate_synthesis_state` (`src/charter/bundle.py`) parses
`charter.yaml` with no exception handling around the YAML load, so an unparseable
`charter.yaml` (exactly the F4 shape this module's other 24 T030 cases already build) blows
past the CLI boundary as a raw traceback — on both the human and `--json` output paths.

I also checked whether this is a mission regression or pre-existing: reproduced the identical
crash on a scratch checkout at the baseline commit (`1aed89411b...`) using that commit's own
`init_git_repo` + `seed_charter_yaml(valid=False)` primitives. It is byte-identical pre-existing
behaviour — `git diff` of `src/charter/bundle.py` baseline-to-tip shows WP04 only *added* the
new `charter_yaml_present()` seam function to this file; `validate_synthesis_state` (the
function that actually crashes) is untouched. So this is not a WP01-WP05 regression, and NFR-004
("zero **new** uncaught exception paths") is not literally violated.

That said, this module already demonstrates the correct way to handle exactly this situation:
the `doctrine.spdd_reasons.activation` crash on `build_charter_context` (site 2) is
investigated, confirmed pre-existing, confirmed not reachable from WP01's F4 fixture (no
`charter.md` companion), and explicitly documented with a rationale in the T030 docstring.
`charter bundle validate` (site 7) got no such treatment — it was simply never added to the
tested surface list, so the gap is invisible rather than documented. For a WP whose entire
purpose is "zero new uncaught exception paths on **any** diagnostic surface" as the closing
regression envelope before merge, silently not testing one of WP04's nine declared sites — and
that site turning out to crash on `--json` for the shape most likely to throw — is a real
completeness gap, not a nitpick.

(For contrast: I also independently checked `charter resynthesize` and `charter sync` — both
plain and `--json`, all four shapes — and both are clean. So this is not a systemic problem, it
is specifically `charter bundle validate`.)

### Requested fix (stays within this WP's owned_files — no production code needed)

Add `charter bundle validate` (plain + `--json`) to `_DIAGNOSTIC_CLI_INVOCATIONS`, and give the
discovered F4 crash the same honest treatment already given to the site-2 exclusion: either (a)
exclude F4 from that one invocation with a documented, verified-pre-existing rationale (pointing
at `validate_synthesis_state` and the baseline reproduction), so the gap is visible to the
mission review instead of silently absent, or (b) if you'd rather not carve out an exclusion,
add a short paragraph to the module docstring's existing "genuine finding" section recording
this as a second pre-existing NFR-004 gap (parallel to the `doctrine.spdd_reasons.activation`
one), the same way the F2/`_is_optional_missing_charter_fresh_project` state-matching finding is
already recorded there.

Either way, the surface should end up **tested and accounted for**, not omitted.

## Not blocking, for awareness only

The full `tests/architectural/` suite did not finish inside this review session due to heavy
concurrent load on the shared host (other sessions running SaaS test suites); it reached ~29%
with no failures observed before I stopped it to avoid resource contention. This is an
environment-timing artifact of this review session, not a finding about the diff — the
WP06-owned file itself is green in full isolation (32/32) and `ruff`/`mypy --strict` are clean.
Re-run `tests/architectural/` on a quieter host before merge if you want full-suite confidence;
I would not gate cycle-2 approval on it.
