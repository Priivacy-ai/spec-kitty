Tranche 2 of `#827` is up for review: <PR_URL>

## What shipped

This PR closes six product gaps that PR #838 had bypassed in the charter golden-path E2E, then converts that test from a softened diagnostic spine into a strict regression gate. Concretely:

- `#840` — `spec-kitty init` stamps `schema_version` + `schema_capabilities` in `.kittify/metadata.yaml`.
- `#839` — fixture synthesis writes canonical doctrine artifacts under `SPEC_KITTY_FIXTURE_AUTO_STUB=1`.
- `#841` — `charter generate --json` emits a `next_step` instruction with action `git_add` and a non-empty paths list when the generated charter is untracked.
- `#842` — `--json` stdout is exactly one JSON document; atexit diagnostic prints are suppressed via `mark_invocation_succeeded` on success paths.
- `#843` — composed actions issued by `next` write paired started/completed profile-invocation records keyed by `invocation_id`.
- `#844` — runtime-next always returns a resolvable `prompt_file` in `kind=step` envelopes (with `kind=blocked` carrying a non-empty reason); the `SKILL.md` workaround text is removed and migration `m_3_2_5_fix_prompt_file_workaround.py` rewrites legacy copies on consuming projects.

`#336` (closed previously by PR #803) is now locked into the strict E2E: every issued step is asserted to carry a non-empty resolvable `prompt_file`.

All six PR-#838 bypasses are deleted from `tests/e2e/test_charter_epic_golden_path.py`. The narrow gate runs in ~22s (NFR-001 budget: 5 min), passes 5 consecutive determinism runs, and fails loudly when any of the six product fixes is reverted.

## Recommended remaining tranches for `#827`

The following are out of scope for tranche 2 and recommended for follow-up tranches under this epic:

- **Tranche 3 — cross-repo E2E coverage**: extend `Priivacy-ai/spec-kitty-end-to-end-testing` with the plain-English suite expansion and SaaS canaries that this tranche explicitly deferred (C-002, C-003).
- **Tranche 4 — runtime/dossier ergonomics**:
  - `#845` dossier snapshot side effects beyond the pollution guard.
  - `#846` specify/plan auto-commit content.
  - `#847` decision events corrupting the status reducer.
  - `#848` `uv.lock` vs installed-events pin drift.

Once tranche 2 lands, I'd recommend opening tranche 3 against the cross-repo testing repository before tackling tranche 4's runtime cleanup, so the cross-repo gate exists before more product behavior is touched.
