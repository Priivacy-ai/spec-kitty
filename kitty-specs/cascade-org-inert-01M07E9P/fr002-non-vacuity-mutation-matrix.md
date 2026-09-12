# FR-002 non-vacuity evidence — mutation matrix

Recorded here (not in a "WP report" file, which never existed in this repo) so the
citations in commits `7f6b66f29` / `a8d0fd58b` and in
`tests/charter/test_context_org_chain.py`'s module docstring point at a real, committed
artifact instead of an unlocated one. See R1-003 in
`kitty-specs/cascade-org-inert-01M07E9P/reviews/pr-correspondence.findings.yaml` for the
finding this note closes.

## Why two halves were needed

FR-002's fix has two independent parts:

- **T017**: stop `specify_cli.cli.commands.charter.context`'s `context()` command from
  precomputing `org_root = org_roots[0] if org_roots else None` and threading that
  truncated value into `build_charter_context` / `build_charter_context_json`; pass
  `org_root=None` instead so the callee's own widening logic applies.
- **T018**: route `build_charter_context_json` through
  `charter.action_doctrine_bundle._resolve_action_bundle` (the same self-widening wrapper
  `build_charter_context` already used), instead of the private
  `_load_action_doctrine_bundle`, which never widens regardless of what `org_root` it is
  given.

An earlier draft applied only the T018 wrapper swap and treated that as the whole fix.
The mission's own spec-review squad (SPEC-ARCH-002) caught this as a no-op: the JSON path
was still being handed an already-truncated `org_root` by the CLI layer, one level above
where the swapped wrapper runs, so nothing observable changed.

## The matrix (source: PR #3534 description)

Four states, each independently exercised by reverting one or both fixes and re-running
the org-chain fixture (two org packs, doctrine content only in pack 2 / pack B):

| T017 (CLI truncation removed) | T018 (JSON routed through `_resolve_action_bundle`) | Result |
|---|---|---|
| no | no | RED — pack A honoured, pack B unreachable |
| yes | no | RED — *zero* org packs resolved |
| no | yes | RED — pack A present, pack B unreachable |
| yes | yes | GREEN — both packs present, in both plain-text and JSON output |

Non-vacuity was proven per work package by reverting each fix in isolation and observing
the new tests go red, then restoring both and re-verifying green — not by assertion. The
"CLI fix only" row is the one that most directly demonstrates T017 is necessary but not
sufficient on its own; R2-001 (pr-correctness.findings.yaml) separately notes that this
matrix was only ever exercised against the library functions
(`build_charter_context`/`build_charter_context_json`) directly, not through the real
`charter context` CLI command — closed by adding a CLI-level `CliRunner` regression test
alongside this note.
