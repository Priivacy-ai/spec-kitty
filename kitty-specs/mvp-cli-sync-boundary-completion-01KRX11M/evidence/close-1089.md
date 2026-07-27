## Resolution: PR #1107

This issue is fixed by PR #1107 (mission `mvp-cli-sync-boundary-completion-01KRX11M`).

### What changed (this issue's scope)

- `spec-kitty agent mission setup-plan` now invokes `run_preflight()` after the existing auth preflight and before any enqueue, SaaS event emission, or body upload. FR-008 refuse-loudly behavior is preserved (the command exits non-zero when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set without authenticated identity), and FR-009 is now also gated structurally: any boundary failure short-circuits before the code path can write to `body_upload_queue`.
- FR-008 ordering is intact: the auth preflight still fires first so an unauthenticated invocation produces the operator-facing "Hosted SaaS sync is enabled but no authenticated identity is available — run `spec-kitty auth login`" refusal, not a confusing field-mismatch error. Only after auth passes does the boundary preflight inspect daemon coherence.
- An AST-level regression test enforces FR-009: `tests/runtime/test_setup_plan_sync_evidence.py:369` asserts no call to `_legacy_queue_db_path()` exists anywhere in the `setup-plan` source path. WP04 keeps this property as it adds the boundary preflight import.

### Verification

```
$ uv run --with pytest python -m pytest tests/runtime/test_setup_plan_sync_evidence.py -q
..........                                                                [100%]
10 passed in 0.41s
```

Full transcripts: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/targeted.txt`.

Live `setup-plan` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no auth produces the existing refusal path (auth preflight fires first); with auth present but a mismatched daemon, the new boundary preflight refuses with the canonical mismatched-field name. The same surface is also exercised by `sync status --check` (see `close-1087.md` and the live transcript at `evidence/test-transcripts/sync-status-check-coherent.txt`).

### Code references

- `src/specify_cli/cli/commands/agent/mission.py:927` — Docstring documenting that this code path delegates to `specify_cli.sync.preflight.run_preflight`.
- `src/specify_cli/cli/commands/agent/mission.py:1015-1017` — Import + invocation of `run_preflight(...)` in the `setup-plan` body, positioned after the auth preflight and before any SaaS-producing work.
- `src/specify_cli/cli/commands/agent/mission.py:1650` — Comment in `finalize-tasks` documenting that downstream SaaS egress is gated by `run_preflight` via `sync now`, completing the FR-002 coverage matrix for SaaS-producing mission paths.
- `tests/runtime/test_setup_plan_sync_evidence.py` — All ten cases pass, including:
  - authenticated `setup-plan` writes scoped queue (line 116)
  - unauthenticated `setup-plan` refuses (line 296)
  - no `_legacy_queue_db_path()` in `setup-plan` path (line 369)
  - `setup-plan` invokes boundary preflight after auth preflight (new in WP04)

### Implementing commits

- `36f1b774` — feat(WP04): setup-plan preflight integration; SaaS-producing path inventory

Closing per the mission's Definition of Done.
