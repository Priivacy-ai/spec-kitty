# Corpus Recovery Contract

Audience: agentic-framework-core-team. Updated: 2026-09-06.
Normative for FR-007-010 and NFR-004. This is a future execution plan, not
authorization for blanket repair or a claim data has already changed.

## Provenance and Exact Recovery Set

Original cyclic mission: `reject-cyclic-lane-graphs-01M0QCK4`.
Original identity: `01M0QCK4D9D65AVNC15HKWAQZ7`.
Source commit: `3442ca1afc20b1b83b27a7bc64fd7014050b12a1`.
Convergence merge: `2554bd13adc289d3457681308645fe52619bca0e`.
The source tree at that mission path matches convergence's first public parent;
path-scoped git diff was empty during planning. Source has 32 files; current
HEAD retains only contracts/lane-dependency-cycle.schema.json, blob
`26cb3b8bafde72894f0d1ec0a9c1701cd511f497`, unchanged from source.

Restore these 31 missing paths, relative to that historical mission directory:

```text
.kittify/dossiers/reject-cyclic-lane-graphs-01M0QCK4/snapshot-latest.json
acceptance-matrix.json
adversarial-review.md
analysis-report.md
checklists/requirements.md
data-model.md
decisions/DM-01M0QCNTD5CM0SE0HKQ79C9NF6.md
decisions/DM-01M0QDJWKXD5JHSVHV0NWSJDWM.md
decisions/DM-01M0QEAKZVM8QAVZPF9AE6D1N8.md
decisions/index.json
issue-matrix.json
lanes.json
meta.json
mission-review.md
plan.md
pr-summary.md
quickstart.md
research.md
retrospective.yaml
spec.md
status.events.jsonl
status.json
tasks.md
tasks/.gitkeep
tasks/README.md
tasks/WP01-authoritative-domain-cycle-gate.md
tasks/WP01-authoritative-domain-cycle-gate/review-cycle-1.md
tasks/WP01-authoritative-domain-cycle-gate/review-cycle-2.md
tasks/WP01-authoritative-domain-cycle-gate/review-feedback-1.md
tasks/WP02-finalization-diagnostics-and-persistence.md
tasks/WP03-determinism-performance-and-regression.md
```

Before restore, recheck source object availability and every current destination.
A newly present divergent file is a conflict, not overwrite permission.
Recover exact Git blob bytes and modes, including the zero-byte .gitkeep and
nested dossier. Use the parent-authorized bounded Git/blob restoration workflow
in the IC-08 isolated workspace; do not reset the entire directory or checkout.
No metadata-only fix, new ULID, rewritten acceptance record or regenerated raw
events. Do not rewrite historical vocabulary or author attribution.

Verify all 31 restored blobs against source before any materialization. Original
created_at `2026-08-23T13:22:37.098012+00:00` and accepted_at
`2026-08-23T17:12:57.441258+00:00` remain; raw event history has 71 rows in the
verified source. Keep the surviving schema path so
tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py
continues consuming it. A later derived snapshot correction is a distinct
canonical replay step with before/after evidence; preserve the historical
snapshot blob reference even if current replay differs.

## R2-T1 Documentation Relocation

Classify `kitty-specs/R2-T1-local-legacy-removal/` as a documentation bundle,
not an identity-less mission. Move, byte-for-byte:

| Old path under kitty-specs/R2-T1-local-legacy-removal | New path |
| --- | --- |
| deletion-manifest.md | docs/archive/program-evidence/R2-T1-local-legacy-removal/deletion-manifest.md |
| commit-history-notes.md | docs/archive/program-evidence/R2-T1-local-legacy-removal/commit-history-notes.md |

The new archive directory does not yet exist; creating it is intentional
repository-data work, outside immediate mission scanning. Retain exact document
bytes and Git history; do not mint metadata, create a placeholder under
kitty-specs or leave an alias directory that the audit still scans.

Provenance: deletion manifest introduced at
`0be7d692adcc71503ad1c3b0ad6b0d16accdef62`; attribution note at
`557a55946d9a23f0c4f7bf4311eb02bb8d3d04cb`.
Record old/new SHA-256 and modes plus rename provenance. Scan tracked references
across the repo, not just docs; update active navigation/test/code references
through their file owners. Historical mission/issue text quoting the old path
remains evidence, with an adjacent new archive index mapping old to new paths,
not an edit of immutable historical records. Inspect relative links in moved
documents; preserve content and supply needed context/mapping in the archive
index if relocation changes their interpretation. No invented classification CLI.

## Two Scoped Snapshot Repairs

### Separately Adjudicated Restored-Mission Replay

Parent disposition, 2026-09-06: exact restoration exposed the anticipated cyclic
snapshot drift. Independent Debugger Debbie reproduced both pins and traced
every changed field to unchanged historical metadata/annotations. Authorize one
additional derived replay, only
`kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/status.json`.
This supersedes WP11/WP12 two-snapshot/eight-verdict total counts: two original
repairs plus one separately recorded restored-mission replay, preserving eleven
complete standing review_result objects (five plus three plus three).

- Historical blob: `b1925001e8a3bed8d95b06e1c7c166a45d3e4db0`.
- Historical SHA-256: `fd53f81b4d658491d9035c5cedad769055639d717ac7117e3afb1a7294ccd640`.
- Reviewed canonical SHA-256: `b20f7ea141534ceccc7a761fcbf4df9ae8a46eb337a20e4da371da4b37ed15f8`.
- Unchanged event SHA-256: `1502470338a65a478c8d04424b642552317eb95d1d96c526a8c2e444df456099`.
- Unchanged metadata SHA-256: `287f11b13d075c89fea910db940c668ef697ba072578958ceab765cf9693f203`.

Restore and replay remain separate operations. Prove all 31 restored blobs and
retained schema match historical input before replay; afterward only this
status.json differs, with historical blob proof retained. Verify the supported
CLI partition, then use `agent status materialize --mission reject-cyclic-lane-graphs-01M0QCK4 --json`.
Require exact reviewed output and current read-only canonical replay; unchanged
raw files/IDs/three approvals, done lanes/force counts/transition markers; and
second-pass byte/mode/mtime idempotence. Shell projections change to existing
winning annotations; do not claim those derived values remain unchanged.

WP12 independently binds this operation and pins, rejects forged receipt/output,
altered history/verdict/identity, extra paths and post-landing mutations. No
receipt-only authority, directory-wide exemption, raw-event repair or fourth
snapshot admission. This disposition is not executed repair, WP approval or a
waiver of the full zero-blocker audit. Independent external evidence:
`cyclic-replay-adjudication.md` beside this checkout.

Original evidence (recheck before mutation; divergence requires adjudication):

| Mission | Event SHA-256 | Original verdict/done lanes |
| --- | --- | --- |
| doctrine-drg-silent-drop-boundary-01M0PE7E | 518d572629a39d026341d0cc26f47cc1a87c5f3323e21c5b8759cd0a02477b20 | 5 |
| symbolkey-source-module-01M0B0SF | 7e0326d9d1a9af04f3d1ce353e0b97caba765aab298de01074df4b889a455aaf | 3 |

Capture current meta, snapshots, raw events, per-WP review_result objects,
lanes, transition IDs, force provenance and annotated metadata before repair.
Resolve each mission's real status partition through the supported command
context in the IC-08 isolated checkout; verify the command will write the intended
mission artifact, not an unrelated active mission or the parent's coord.

Then use the verified narrow command:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent status materialize --mission doctrine-drg-silent-drop-boundary-01M0PE7E --json
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent status materialize --mission symbolkey-source-module-01M0B0SF --json
```

Expected: canonical annotation-aware replay adds/corrects metadata; doctrine
mission_type becomes software-dev. All eight done lanes and complete
review_result objects remain identical, including reference/reviewer/verdict.
Event bytes/hashes, immutable IDs and raw annotation evidence remain unchanged.
Do not replace absent historical model/provider values with invented data.
Materialize twice; second pass changes nothing (bytes and mtimes).

The command may use resolver/lock infrastructure; inspect its actual output
paths before accepting the diff. A misplaced output is a blocker to diagnose,
not a reason to hand-write snapshots or edit coord. Avoid both global and
mission-scoped doctor --fix, which can canonicalize raw events/metadata beyond
this task. No reducer/audit source change is expected.

## Final Evidence

The portable recovery receipt lives at
`docs/archive/program-evidence/upgrade-preview-mission-health-01M1V6E1/recovery-receipt.json`.
WP11 produces it with the confined corpus/document changes; WP12 owns
`tests/upgrade/test_mission_corpus_recovery.py` and independently validates the
receipt and original/corrupted counterfactuals. Neither the receipt producer nor
the preservation-gate implementer may approve its own evidence exemption.
WP11 still demonstrates real CLI failure before recovery and exact provenance,
no-churn and full-audit success before its independent data review.

Run the real full-corpus gate in the repaired isolated checkout:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty doctor mission-state --audit --fail-on teamspace-blocker --json
```

Require exit 0 and zero TeamSpace blockers, not merely four removed names.
Record complete output or content hash plus exact filtered evidence, corpus
count, executable/commit provenance, recovery blob manifest, rename hashes,
snapshot diffs, eight unchanged review objects and second-run idempotence.
Historical total 422/424 is not a fixed acceptance count.

If restoring the cyclic history exposes a derived-snapshot drift, preserve its
raw recovered files and perform a separately recorded canonical scoped replay;
do not alter raw history to match a stale snapshot. Any other newly exposed
blocker needs explicit diagnosis/disposition, never weakened audit thresholds.
Unrelated warning/info counts remain observed, not blanket remediation scope.

Retain negative upgrade --yes consent test and existing positive explicit
mission-repair control. #3903 is committed-data repair; it does not widen upgrade
consent or fold mission repairs into generated churn commits.
