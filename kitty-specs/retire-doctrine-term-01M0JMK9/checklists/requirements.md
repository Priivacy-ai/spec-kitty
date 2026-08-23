# Requirements Quality Checklist

**Mission**: `retire-doctrine-term-01M0JMK9` · **Updated**: 2026-08-22

## Scope and authority

- [x] Operator override explicitly supersedes earlier user-facing-only/internal/history scope.
- [x] The two fixed exclusions are Git object history outside current `HEAD` and the immutable `kitty-specs/`
  historical-archive root (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`); no slug/directory/file under it is renamed or
  edited.
- [x] No X1/X2/X3, internal, historical-current-tree, fixture, generated, metadata, or pathname exemption
  outside that root.
- [x] Planning-only C-001 remains explicit; downstream product changes are not executed here.
- [x] ADR and M1 use the exact per-artifact Charter owner/no-op/deletion map; `charter generate` is limited
  to YAML catalog/metadata.

## Coverage and assignment

- [x] Forced-text all-blob content and NUL-safe tracked-path audits use checked no-pipeline subprocesses;
  grep rc >1 and any ls-tree nonzero rc fail closed.
- [x] Manifest is one row per hit/path and set-equal to both outputs; it is ephemeral, untracked evidence
  pinned by SHA-256/counts in `inventory.md` (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`).
- [x] Every hit must receive exactly one M1–M6 owner; current-repository deferral is forbidden.
- [x] CR introduction/removal does not duplicate primary ownership.
- [x] M5 explicitly owns current-tree ADR/docs/archive/history/evidence files and referrers outside
  `kitty-specs/`; archive referrers are recited by `mission_id`/mid8 or token-free path.

## Downstream executability

- [x] M1 has zero local decisions, including verified no-op behavior and obsolete-graph consumer proof.
- [x] Activation uses activate/deactivate + shared engine only; existing answers use lossless surgical
  migration and serializer round-trip hardening before interactive ownership resumes.
- [x] M2 owns all public/private code topology and freezes every `src/charter/` collision before edits.
- [x] M3 preserves project data canonically, blocks divergence, and cannot complete with old root.
- [x] M4 covers source/generated/installed/shared agent assets and cannot complete with old path.
- [x] M6 removes all aliases/keys/paths/controls/fixtures/baselines/allowlists.
- [x] Runtime managed-path ledger/state overdesign is explicitly rejected.

## Terminal proof

- [x] I6 content count is zero across forced-text `HEAD` blobs with the fixed `:(exclude)kitty-specs/` pathspec.
- [x] I6 tracked pathname count is zero through NUL-safe audit after the `kitty-specs/` drop.
- [x] Charter is included; no supported/user-visible qualifier or narrowing beyond the one fixed root remains.
- [x] Post-M6 negative tests construct the token from numeric bytes without storing it.
- [x] Content/path `match_sha256` preimages are fully framed and independently byte-reproducible.
- [x] M6 names one token-literal-free audit entrypoint and required external CI/release check marker.
- [x] Any hit, error, exception, baseline, allowlist, or deferral blocks completion.

## Quality

- [x] Requirements are testable and use consistent FR/NFR/C/SC identifiers.
- [x] Dependencies, inputs, outputs, gates, rollback, and ownership cardinality are explicit.
- [x] Data-preservation exception is narrow and conflict-safe; no silent overwrite/data loss.
- [x] Research, data model, contracts, plan, tasks, prompts, quickstart, and this checklist are set-equal.
