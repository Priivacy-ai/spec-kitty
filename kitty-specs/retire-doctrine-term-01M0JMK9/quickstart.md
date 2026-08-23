# Verification Runbook: Complete Terminology-Extinction Plan

**Mission**: `retire-doctrine-term-01M0JMK9`

## 1. Planning scope

This mission may change its specification, plan, research, data model, contracts, task prompts, ADR and
registration surfaces, inventory/methodology/stacked-plan/verification outputs, squad evidence, and
required docs-contract metadata. It must not execute downstream product renames or add runtime migration
architecture.

Compare both committed and working-tree deltas to WP01's frozen implementation base. Product `src/`,
tests, package, skill, Charter, and migration changes are downstream M1–M6 work, not this planning PR.

## 2. Frozen snapshot

Before WP01 edits:

1. `git fetch origin main`;
2. require fetched tip is incorporated by `HEAD`;
3. atomically persist `target_ref`, exact `target_tip`, `implementation_base`, commands, timestamp, actor,
   and `wp_id=WP01` to `implementation-baseline.json`;
4. bind WP02–WP05 to it. A different target requires fresh target branch, planning-commit replay, WP01
   restart.

## 3. ADR review

An independent reviewer must derive from the ADR alone:

1. canonical Charter Pack/Bundle and Active/Inactive vocabulary;
2. complete current-tree scope outside the single fixed `kitty-specs/` exclusion root, including internal
   code/history/tests/generated/metadata/pathnames;
3. operator override and its no-data-loss boundary;
4. M1 complete Charter/glossary authority graph and owner workflows;
5. M2 old-source-tree convergence into collision-free `src/charter/`;
6. M3/M4 data preservation plus old-path extinction on completed migration;
7. M5 current-tree history rewrite outside `kitty-specs/`, archive immutability (no slug/directory/file
   rename or edit under it; referrers recited by `mission_id`/mid8 or token-free path), and the two fixed
   exclusions (Git object history, `kitty-specs/`);
8. M6 compatibility/control/fixture/baseline removal and exact zero audits.

Any “user-visible only”, X1/X2/X3, immutable-current-tree-outside-`kitty-specs/`, unsupported internal,
supported-surface-only, or additional-exclusion wording fails.

## 4. Reproduce inventory

At frozen `base_commit`, run the exact cross-platform Python subprocess algorithms in
`contracts/inventory-schema.md` with `mode=inventory` (fixed `:(exclude)kitty-specs/` pathspec; `kitty-specs/`
paths dropped after the ls-tree rc check); do not use a shell pipeline. Preserve argv, raw git return code,
and stdout/stderr hashes. A content rc 1 with empty stdout is the expected no-match result;
rc >1 or inconsistent output is an audit error. Any pathname-command nonzero rc is an audit error before
the NUL stream may be classified.

Prove `inventory-hits.tsv` set-equal to outputs, deterministic, duplicate-free, and entirely `OC-##` +
S1–S10. The TSV is ephemeral, untracked evidence: regenerate it from the frozen base and require a
byte-identical match to the SHA-256, row count, and per-kind/S/OC counts recorded in `inventory.md`, whose
excluded-root orientation counts must also be present. Reject X/exempt/ignored rows, missing pathnames,
sampling, `-I`, shell-expanded file lists, any exclusion other than the fixed root, or current-repo
deferrals.

## 5. Methodology checks

- M1: execute the ADR contract's exact map—direct `charter.md` plus human YAML governance/directives/
  overrides only; activation exclusively via activate/deactivate + shared engine; existing answers via
  backup-backed surgical migration plus serializer hardening before interview ownership;
  generate-only YAML catalog/metadata; context-owned local state; synthesis-owned manifest;
  repeated zero-consumer proof then deletion of obsolete writerless `graph.yml`. Verify/no-op each no-hit
  artifact; override effective; guard last.
- M1 glossary parity: update `docs/context/doctrine.md` → `docs/context/charter.md`,
  `.kittify/glossaries/spec_kitty_core.yaml`,
  `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`, and active referrers atomically;
  WP04 binds #2727 from canonical `issue-matrix.json` into M1, which rolls back on semantic/hash/link
  divergence.
- M2: every public/private source module/file/symbol/import/test/fixture/build hook and CLI/API/config/
  workflow/metadata row; all `src/charter/` collisions resolved before edits; no old live code topology at
  close outside registered CR.
- M3: backup/check/copy-or-move/verify/remove-old; divergent destination blocks with both intact; no old
  project root after completed migration.
- M4: same safety for every source/generated/installed/shared agent asset; no old installed path after
  completed migration.
- M5: all remaining current-tree ADR/docs/archive/history/evidence prose, filenames, and referrers outside
  `kitty-specs/`; `kitty-specs/` byte-identical; archive referrers recited by `mission_id`/mid8 or
  token-free path.
- M6: every alias/key/path/control/fixture/tombstone/baseline/allowlist removed; numeric-byte tests; exact
  zero over `HEAD` outside the fixed `kitty-specs/` root.

Require one named verifier per S1–S10 and rollback/failure tests for every transition.

## 6. Stacked-plan cardinality

- OC member sets are exact and disjoint.
- M1–M6 owner sets are pairwise disjoint; their union equals all manifest hits.
- Every CR frozen-base source hit funds at most one CR and its introduction equals its OC owner. Product/
  control coordinates introduced later are distinct M6-removal work, not duplicate ownership of source.
- M1 local questions = 0. Dry-run all Charter inputs/outputs and sequencing.
- M2 local gate = one topology-map approval; every collision/consumer mapped before first edit.
- M3–M6 local policy questions = 0.
- Each wave names fresh base/audit, inputs/outputs/owned surfaces/tests/gate/rollback/I-level.

## 7. Exact terminal gate design

M6 runs both inventory-contract subprocess algorithms with `mode=terminal`. The content git process must
return raw rc 1/empty stdout; the pathname git process must return raw rc 0 and zero matches; the wrapper
then exits 0. Charter is included; the fixed `kitty-specs/` pathspec/drop is the one permitted boundary. Any hit,
git failure, return-code/output inconsistency, audit error, unreadable input, omitted archive exclusion,
any other narrowed root, exception list, baseline, or external deferral blocks I6.
Record exact commit/tree OIDs. Any tree mutation invalidates the result; CI/release reruns terminal mode on
the final merge/publish tree.
Mandatory entrypoint: `python scripts/audit_retired_term_zero.py --commit <final-commit-oid> --mode
terminal --json -`; mandatory check marker: `terminology-zero-current-tree`. JSON is external stdout only,
never a tracked post-audit write.

Run named failure cases `test_content_audit_accepts_rc1_empty_only`,
`test_content_audit_rejects_git_rc_gt1`, `test_path_audit_propagates_ls_tree_failure`, and
`mutation_git_audit_failure_cannot_pass_zero`.

Post-M6 tests construct the token from numeric bytes; source and fixture files may not store it literally.
The two fixed exclusions are Git object history outside `HEAD` (not scanned) and the immutable
`kitty-specs/` historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`).

## 8. Required planning checks

```bash
git diff --check
spec-kitty agent tasks validate-workflow WP01 --mission retire-doctrine-term-01M0JMK9 --json
spec-kitty agent tasks validate-workflow WP02 --mission retire-doctrine-term-01M0JMK9 --json
spec-kitty agent tasks validate-workflow WP03 --mission retire-doctrine-term-01M0JMK9 --json
spec-kitty agent tasks validate-workflow WP04 --mission retire-doctrine-term-01M0JMK9 --json
spec-kitty agent tasks validate-workflow WP05 --mission retire-doctrine-term-01M0JMK9 --json
```

WP05 records commands, hashes, outputs/reviewer answers, timestamps, and pass/fail. Missing evidence fails;
substantive defects route to WP01–WP04.
