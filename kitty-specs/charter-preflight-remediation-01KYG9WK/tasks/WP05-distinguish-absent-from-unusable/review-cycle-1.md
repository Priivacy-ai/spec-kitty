# WP05 Review — Cycle 1 — CHANGES REQUESTED

Reviewed commit `f128b197d` in isolation (lane-e is contaminated with WP01-WP04's
work; only this commit is WP05's own scope). Ran the real regression suites,
built F1/F2/F4 fixtures directly against `compute_freshness`, and constructed a
partial-bundle fixture the implementer's own tests never exercise.

## Issue 1 (blocking): F2's `detail` string overclaims for a partial legacy bundle

`_legacy_bundle_present()` returns `True` when **any** of the four legacy bundle
files exist (`governance.yaml`/`directives.yaml`/`metadata.yaml`/`references.yaml`),
but `_missing_charter_source_detail()` always renders the full, fixed-text claim:

```
no charter.yaml, but a legacy charter bundle
(governance.yaml/directives.yaml/metadata.yaml/references.yaml) is present;
this project has a charter, just not in the required form
```

Verified directly against production code (`compute_freshness`) with a repo
containing only `references.yaml` (a plausible real state — a stray leftover
from a partially-completed migration, a hand-edit, or a project mid-upgrade):

```
Files actually on disk: ['references.yaml']
charter_source.detail: 'no charter.yaml, but a legacy charter bundle
(governance.yaml/directives.yaml/metadata.yaml/references.yaml) is present;
this project has a charter, just not in the required form'
```

The rendered text asserts all four named files are present when only one is.
This is precisely the failure mode the WP prompt and review brief warned
against: a confidently-worded but factually wrong detail is worse than the
generic filler it replaced, because an operator now has an authoritative-sounding
but false inventory of their own `.kittify/charter/` directory.

None of the added tests catch this. The `test_computer.py` F2 test seeds **all
four** files; the `test_charter_status_freshness.py` F2 test seeds **three**
of four (missing `references.yaml`) but only asserts the substring `"legacy
charter bundle"` is present in the detail — it never checks that the specific
named-files claim matches what's actually on disk, so the same weak assertion
would pass even if the substring were wrong for other reasons. Neither test
exercises the single-stray-file case, which is where the overclaim is most
visible.

**Fix**: either (a) name only the legacy files that actually exist in the
`detail` text (e.g. build the file list from the same `any(...)` check,
substituting the existing names), or (b) soften the fixed-list wording so it
doesn't assert presence of files that may not exist (e.g. "one or more of the
legacy charter bundle files ... is present" without the specific inventory).
Add a partial-bundle regression test (one file only, and 2-of-4) that asserts
the rendered text does not name a file that isn't actually present.

## Issue 2 (blocking): DIRECTIVE_044 — duplicated detector lacks the drift guard its own cited precedent uses

The implementer's rationale for mirroring `_LEGACY_BUNDLE_FILENAMES`/
`_legacy_bundle_present()` locally instead of importing
`m_unify_charter_activation_finalize.LEGACY_BUNDLE_FILENAMES`/
`legacy_bundle_present` is **substantively correct** on the import-cost point:
that migration module registers itself with `MigrationRegistry` at import
time (module-level class definition under `@MigrationRegistry.register`), so
importing anything from it — even a bare constant — pulls the registry onto
`computer.py`'s hot path (NFR-003). That's a real, verified cost, not an
excuse. The `__all__`-based "unexported internals" framing is weaker (the
module's own tests import both symbols by fully-qualified path — `__all__`
only gates `from module import *`), but the import-cost argument stands on
its own.

However, the commit claims this "match[es] the existing `_CHARTER_YAML_FILENAME`
mirroring pattern" — and that pattern is **not just a mirror**, it's a
mirror-plus-drift-guard: `tests/specify_cli/charter_freshness/test_computer.py`
already contains

```python
assert tuple(_BUNDLE_FILES) == tuple(BUNDLE_CONTENT_HASH_FILES)
```

which imports the canonical `charter.bundle.BUNDLE_CONTENT_HASH_FILES` **in
the test file** (not the hot production path) specifically so a future edit
to one side and not the other fails loudly. WP05 added no equivalent
assertion for `_LEGACY_BUNDLE_FILENAMES` vs.
`m_unify_charter_activation_finalize.LEGACY_BUNDLE_FILENAMES` — nothing in
the test suite will catch the two four-file lists drifting apart if the
migration module's list is ever touched (e.g. a fifth legacy file discovered,
or a rename). Given the mission's own precedent supplies the exact mechanism
for free, and the stated rationale explicitly invokes that precedent, this is
a straightforward addition, not new design work.

**Fix**: add one test (in `tests/specify_cli/charter_freshness/test_computer.py`,
alongside the existing `_BUNDLE_FILES`/`BUNDLE_CONTENT_HASH_FILES` pin) that
imports `LEGACY_BUNDLE_FILENAMES` from
`specify_cli.upgrade.migrations.m_unify_charter_activation_finalize` and
asserts it equals `_LEGACY_BUNDLE_FILENAMES` (as a set or sorted tuple, since
declared order need not match).

## Everything else checked out

- **T024/T025/T026 framing**: correct — F1 vs F2 was indeed the real gap
  (verified: F1 vs F4 was already distinguishable via `state` + existing
  `invalid` detail before this WP).
- **No new state value**: confirmed — `FreshnessState` Literal is unchanged
  (`fresh`/`stale`/`missing`/`built_in_only`/`invalid`); `detail` was already
  a field, just unpopulated on the `missing` branches.
- **`cli.py` untouched**: confirmed via `git show --stat` — zero changes to
  the WP's authoritative surface; the fix genuinely lands upstream in the
  model, as claimed.
- **F1 non-blocking (FR-006)**: confirmed through the real gate path —
  `test_f1_still_non_blocking_without_strict` invokes the actual `charter
  preflight --json` Typer CLI (not a unit-level shortcut) against an F1
  fixture and asserts `exit_code == 0` without `--strict`.
- **WP01's `test_remediation_effectiveness.py` mechanism**: the lineno re-pin
  (322→382, 368→435, 472→540, 503→571, 516→584) is mechanically correct —
  verified by grepping the new `computer.py` for `remediation=` and matching
  every pinned lineno exactly. The `_EXEMPT_STATES` frozenset
  (`("_compute_charter_source", "invalid")`, `("_compute_synced_bundle",
  "stale")`) is untouched by the diff. Ran the suite: 13 passed. One minor
  attribution note (non-blocking): the commit message lists this re-pin
  under "two pre-existing, unrelated-to-this-WP items," but it isn't
  pre-existing — verified against the parent commit that the old linenos
  (322/368/472/503/516) were still correct there; the shift is a direct,
  in-scope mechanical consequence of WP05's own edit to `computer.py`, not
  an inherited defect. The re-pin itself is legitimate and required either
  way; only the framing is slightly off.
- **The `test_charter_status_freshness.py` stale-assertion fold**: verified
  genuinely pre-existing — checked out the parent commit
  (`f128b197d^`, the lane-c merge) into a scratch worktree and ran
  `test_freshness_state_invalid_when_charter_yaml_unparseable` there: it was
  already **red** (`remediation == "spec-kitty charter sync"` vs. actual
  `None`, from WP03's C-EFF-2 exemption). This fold is legitimate, not
  smuggled scope.
- **Regression suites**: `charter_preflight/` + `charter_freshness/` — 61
  passed. `test_remediation_effectiveness.py` — 13 passed. `ruff check` on
  all five changed files — clean.

## Verdict

Both blocking issues are narrow and mechanical to fix — they don't require
touching `cli.py` or introducing new design. Please address both and
resubmit.
