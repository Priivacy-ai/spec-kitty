# Research: Complete Current-Tree Terminology Extinction

**Mission**: `retire-doctrine-term-01M0JMK9` · **Updated**: 2026-08-22

The operator's 2026-08-22 terminal decision supersedes earlier scope decisions that protected internal or
historical current-tree content, as amended by `DM-01M0NMS9WPH33EPFCJQRTQVNSA` (the `kitty-specs/`
historical archive is immutable and is the single fixed exclusion root of both audits) and
`DM-01M0NMSD60JYG7K7V5MJCKJ3P8` (`inventory-hits.tsv` is ephemeral, hash-pinned evidence). All cross-wave
decisions are resolved. M2 retains one bounded pre-edit topology-map approval; it cannot reduce scope or
change the terminal gate.

## R1 — ADR and Charter are joint authority

**Decision**: WP01 authors/registers the ADR. M1 then updates the complete Charter/glossary authority graph
and makes the override effective at I1. The frozen owner map is exact: directly curate `charter.md` and
human `charter.yaml` governance/directives/overrides only; activation fields are owned by
`activation_engine`/`CharterPackManager` through `charter activate`/`deactivate`, including interview
promotion/default seeding. Existing `interview/answers.yaml` is migrated by M1's sanctioned surgical,
byte-preserving path because today's interactive serializer is lossy; after M1 hardens round-trip
serialization, `charter interview` resumes ownership. `charter generate`
owns only `charter.yaml` catalog/metadata after owning-source updates and never overwrites `charter.md`;
`charter context` owns runtime-local `context-state.json`; `charter synthesize`/`resynthesize` owns
`synthesis-manifest.yaml`; and `.kittify/charter/graph.yml` is a writerless legacy activation snapshot
deleted only after its frozen zero-consumer audit is repeated. No-hit artifacts record verified no-ops.
`charter sync` is not a writer, and synthesis's `.kittify/doctrine/graph.yaml` is not `graph.yml`.

Glossary authority is one M1 transaction: rename/update `docs/context/doctrine.md` to
`docs/context/charter.md`, update `.kittify/glossaries/spec_kitty_core.yaml`, update
`packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`, and update all active referrers under
one semantic/hash/link parity gate. WP01 specifies the obligation; WP04 consumes canonical
`issue-matrix.json` #2727 and binds it to M1; no authority slice may remain deferred to that issue.

**Rejected**: treating the ADR alone as effective, editing only generated output, blanket regeneration of
human-curated content, or leaving the Charter itself for M5.

## R2 — Explicit extinction override

**Decision**: The ADR/Charter records a program-scoped exception that supersedes User Customization
Preservation only where an old-named path must disappear after content is preserved canonically, and
supersedes historical-current-tree immutability for ADRs/docs archives/evidence/fixtures and paths outside
`kitty-specs/`. Divergent destinations block before destructive action. Git object history and the
`kitty-specs/` archive are untouched.

**Rejected**: data loss, silent precedence, permanent old paths, current-tree historical carve-outs other
than the fixed `kitty-specs/` root, or using the override for unrelated cleanup.

## R3 — Exact audit and inventory

**Decision**: Freeze current `origin/main` plus implementation base before WP01 edits. WP02 runs forced-text
case-insensitive `git grep -a` over all tracked blobs with the fixed `:(exclude)kitty-specs/` pathspec and a
NUL-safe `git ls-tree -r -z` pathname filter that drops `kitty-specs/` paths after the rc check, through
the no-pipeline Python subprocess procedures in the inventory contract. They validate raw git return codes
before interpreting output: grep rc 1/empty means zero, rc >1 is error; ls-tree nonzero is always error.
`inventory-hits.tsv` is one row per match/path and set-equal to outputs; it is ephemeral evidence —
generated, untracked via the mission-local `.gitignore`, and pinned by SHA-256/row counts in committed
`inventory.md`, whose reproduction command regenerates it byte-identically. Excluded-root counts are
recorded as orientation only. Every row is OC work; there are no X1/X2/X3 classes.

**Rejected**: `-I`, shell-expanded file lists, docs-only roots, sampling, count-only summaries, pathname
omission, allowlists, any exclusion beyond the one fixed root, a committed multi-megabyte manifest, or
classifying internal/history/test data out.

## R4 — Transition guard ends in zero mode

**Decision**: M1 may create exact shrink-only fingerprints and bounded CR reservations for 3.x. Every
ordinary/control/product hit remains assigned work. M6 deletes CR controls, compatibility fixtures,
tombstones, baselines, and allowlists, then runs the exact zero gate over `HEAD` outside `kitty-specs/`. Post-M6 negative tests
construct bytes `(100,111,99,116,114,105,110,101)` rather than storing the token.

Frozen-base source coordinates retain their M1–M4 introduction-wave OC owner. Compatibility product and
control coordinates created later are distinct new work assigned to M6 at the next wave-local audit; this
does not duplicate or rewrite the source coordinate's primary ownership.

**Rejected**: terminal X records, permanent detector literals, file exemptions, baseline-as-permission, or
a supported-surface-only audit.

## R5 — Complete surface topology

**Decision**: S1–S10 cover CLI, glossary, all current-tree prose/history outside `kitty-specs/`, agent
assets, Charter, packs/
overlays, all code/build/test topology, serialized/workflow/generated surfaces, repo operations, and
tracker seams. Classification follows owning behavior, never audience-based exclusion.

**Rejected**: default-out for unlisted directories or treating physical/internal path hits as harmless.

## R6 — M2 owns internal and public topology

**Decision**: M2 freezes one exhaustive `canonical-operator-surface-map.md` despite the historical name;
it includes every public/private package/module/file/symbol/import/test/fixture/build hook plus CLI,
serialized/API/event/workflow/distribution/wheel/metadata producer and consumer. It maps the entire
`src/doctrine/` tree into the existing `src/charter/` aggregate. Every collision is `merge-existing` or
exact `relocate` before edits. CLI projection is set-equal to CLI rows. M2 cannot close while an old live
code/executable content/path hit remains outside registered 3.x compatibility owned by M6.

**Rejected**: preserving old internals, facade-only migration, directory-based ownership, TBD collisions,
or leaving imports/tests/build metadata for later prose work.

## R7 — Fixed semantic seams and vocabulary

**Decision**: Charter Pack, Charter Bundle, Active Charter, and Inactive Charter have the meanings in the
ADR contract; kind labels survive. Selection, org-pack, tracker ownership, target URN, skill/profile/
directive, public API, distribution, and wheel seams use the fixed canonical mappings plus M2's exhaustive
map. Old aliases warn through 3.x and disappear in M6.

**Rejected**: blanket token substitution without semantic mapping, retaining operator IDs as internals,
or introducing a new “domain” brand.

## R8 — M3 project overlay migration

**Decision**: M3 migrates `.kittify/doctrine/` to `.kittify/charter-packs/`, never into the Charter Bundle.
Preflight inventories source/destination and backs up. Absent target is copied/moved and verified before
source removal; identical target is verified then source removed; divergent target hard-fails with both
intact and explicit operator resolution. Canonical writers use only the new root. Completed migration
requires old root absent. M6 removes the 3.x old-root reader/migrator/fixture.

**Rejected**: runtime managed-path ledgers/state stores, silent canonical precedence, old-root retention,
dual writes, or “preservation” that preserves the retired pathname after completion.

## R9 — M4 installed/generated asset migration

**Decision**: M4 applies the same bounded preflight/backup/verify/conflict rule to every source, generated,
installed, shared, override, profile, directive, prompt, skill, and agent artifact. Canonical IDs/paths are
the only completed state. 3.x aliases route/warn; M6 removes them and their fixtures.

**Rejected**: source-only rename, name-based overwrite, old installed paths after completion, or an
unbounded runtime migration architecture.

## R10 — Current-tree history belongs to M5

**Decision**: M5 rewrites/renames every remaining current-tree prose/history occurrence and pathname
outside `kitty-specs/`, including all ADR bodies/titles/files, docs archives, evidence, comments, READMEs,
and referrers. `kitty-specs/` is an immutable historical archive: no mission slug, directory, or file
under it is renamed or edited; a referrer outside it that cites an archive path containing the token is
rewritten to cite the mission by `mission_id`/mid8 or a token-free path, never by changing the archive
path. Earlier program evidence remains recoverable from Git object history.

**Rejected**: immutable current-tree snapshots outside `kitty-specs/`, archived-file exclusions beyond that
root, editing or renaming anything under it, or leaving detector prose literal.

## R11 — M6 exact release boundary

**Decision**: M6 removes all CR products/controls, aliases, keys, routes, imports, old-root readers,
migrators, redirects, warnings, distribution aliases, test fixtures, and transition guard data. It runs
the checked forced-text content audit and NUL-safe pathname audit over one exact final commit/tree with
the single fixed `kitty-specs/` exclusion; both counts are zero. Any tree change invalidates evidence, and
CI/release reruns on the merge/publish result tree. Charter is not excluded. Any hit/error, omission of
the fixed root, or any other narrowing blocks 4.0.

M6 creates/uses token-literal-free `scripts/audit_retired_term_zero.py`; external CI/release requires
`terminology-zero-current-tree`. The entrypoint emits commit/tree-bound JSON to stdout only, so recording
the attestation cannot mutate or self-invalidate the audited tree.

**Rejected**: user-visible-only, supported-only, source-only, file-extension-only, current-branch allowlist,
an entrypoint whose pathspec differs from the contract, or exception-bearing completion.

## R12 — Sequence, ownership, and rollback

**Decision**: strict M1 authority → M2 code topology → M3 packs/root → M4 agent assets → M5 all remaining
current-tree prose/history outside `kitty-specs/` → M6 compatibility extinction. Every OC/hit has one M1–M6 owner. CR source
coordinates keep their introduction-wave owner; later product/control coordinates have M6 removal
ownership. Before dependents, revert one wave; afterward reverse suffix/forward-fix.
M3/M4 restore verified backups on failure. After 4.0, rollback is release-level.

**Rejected**: ownerless current-repo deferrals, parallel authority/code flips, middle-wave rollback after
dependents, or declaring I6 from a curated inventory rather than fresh `HEAD` audits.

## R13 — Durable planning snapshot

**Decision**: WP01 atomically records fetched `target_tip` and `implementation_base` in
`implementation-baseline.json`; WP02–WP05 bind to it. A changed target forces fresh branch/replay/restart.
Each downstream M1–M6 later captures its own current target and audit.

**Rejected**: transient shell variables, stale merge-base identity, or mid-mission refetch/repoint.
