---
affected_files: []
cycle_number: 2
mission_slug: consolidate-charter-bundle-01KXSYB9
reproduction_command: PWHEADLESS=1 uv run pytest tests/charter/test_compiler.py tests/charter/test_generator.py tests/charter/test_compiler_charter_yaml.py tests/agent/cli/commands/test_charter_cli.py tests/specify_cli/cli/commands/test_charter_generate_autotrack.py -q
reviewed_at: '2026-07-18T14:30:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP03
---

# WP03 Review — Cycle 2 — APPROVED

The complete slice lands. Both cycle-1 completions are done and every acceptance
item verified against `data-model.md` Landmine 3 / INV-9 and the WP03 prompt
(T011–T015 + T014b).

## Landmine 3 — internal-clobber PREVENTED (the load-bearing guarantee)
`write_compiled_charter` refreshes ONLY the derived `catalog` + `metadata`
through WP01's `charter_yaml_io.update_charter_yaml_section` (ruamel round-trip).
Authored `governance`/`directives`/`activation`/`overrides` survive byte-for-byte
on recompile — the whole file is never reconstructed from `CompiledCharter` when
it already exists. `activation` is read-only input (bootstrap copies legacy
`config.yaml` activation VERBATIM; no catalog←activation circularity). Directly
pinned by `test_authored_governance/directives/activation/overrides_survive_refresh`
— real production-path tests writing authored sentinels to a real charter.yaml,
refreshing, and asserting survival (delete the impl → they fail). This is the
guarantee WP04/WP08 stack on, and it holds.

## #2772 clobber removed
No generate/compile path writes `charter.md` (the `charter_path.write_text`
clobber is gone). `_write_references_yaml` retired — references.yaml no longer
emitted. `force` is a logged no-op (nothing destructive left to gate). Pinned by
`test_refresh_never_writes_charter_md_or_references_yaml` +
`test_survives_refresh_without_force`.

## Bootstrap + pointer mint (T014) — closes the WP02-review init-pointer gap
`_bootstrap_charter_yaml` creates charter.yaml on first compile AND
`_mint_config_charter_pointer` writes `charter: .kittify/charter/charter.yaml`
into config.yaml (comment-preserving ruamel; other keys/comments survive;
graceful when config.yaml absent). Verified on THIS repo: `.kittify/config.yaml`
carries the pointer (comment-annotated, siblings intact) and
`.kittify/charter/charter.yaml` is committed + git-tracked with
governance/directives/catalog/overrides/metadata plus the 6 `activated_*` keys
seeded verbatim from config. Pointer-mint pinned by
`test_bootstrap_mints_pointer_into_absent_config`,
`test_bootstrap_mints_pointer_preserving_other_config_keys`,
`test_no_repo_root_does_not_touch_config`,
`test_pointer_not_reminted_on_refresh_of_existing_charter_yaml`.

## #2758 preflight
`_synthesis.py` `BUNDLE_INCOMPLETE_MESSAGE` re-messaged to the charter.yaml
fail-loud world (migration/generate remediation); the fail-closed guard is kept,
not deleted (C-003).

## Symlink-guard ruling — acceptable narrowing (follow-up, NOT a regression)
The retired guard refused to overwrite a symlinked `charter.md` because the old
write was a full-file clobber that would destroy a symlink target. The new write
is a PARTIAL MERGE via in-place `open("w")` in `save_charter_yaml` /
`update_charter_yaml_section` — NOT an atomic temp+rename. So a symlinked
charter.yaml would have its TARGET written through with authored content
preserved and the symlink itself left intact (the semantically-correct behavior
for a symlink; a rename-based save WOULD replace the symlink with a regular file
and THAT would be a real regression — but that is not what this code does). The
output-DIR symlink guard (`_assert_safe_charter_output_dir`) remains. A symlinked
charter.yaml is an odd, unsupported setup. Net: the narrowing is if anything
safer than before. Follow-up only if a symlinked charter.yaml ever becomes a
supported setup (add an explicit file-level symlink behavior/guard then).

## Gates
- ruff: clean (C901 in-config ⇒ complexity ≤15 confirmed, incl. `generate()`
  after the two-helper extraction `_sync_charter_if_present` /
  `_finalize_sync_result`).
- mypy --strict: 2 errors, both PRE-EXISTING zero-diff — `charter_bundle.py`
  `no-any-return` and `generate.py` `untyped-decorator` (typer) — confirmed
  identical on the base branch (`:260`/`:204`), line-shifted here only by the
  added helpers.
- pytest (owned suite): 86 passed, 1 skipped (symlink test — no local FS symlink
  support; not a failure).

## Anti-pattern checklist
1. Dead code — PASS (all new helpers live off `write_compiled_charter` /
   `generate()`).
2. Synthetic-fixture test — PASS (tests invoke the real write path with authored
   sentinels).
3. Silent empty return — PASS (each early/empty return documented: verbatim
   activation copy, absent charter.md skip, pointer fallback).
4. FR coverage — PASS (FR-001/007/011 pinned by partial-write, clobber-removal,
   pointer-mint tests).
5. Frozen surface — PASS (`init.py` untouched — #2519 fence respected).
6. Locked decision — PASS (no charter.md write; MUST-NOT clobber honored).
7. Shared-file ownership — PASS (WP03 own commits touch only owned files + the
   T014 repo artifacts; WP01 files present via the dependency-lane merge, not
   authored here).
8. Production fragility — PASS (pydantic-validated derive fails loud on schema
   drift; no bare raise on a transient race).

Unblocks WP04 (the big lane) + WP08.
