# Tracer: Design Decisions — retire-doctrine-term

Seeded at planning (post-analyze, pre-implement). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## DD-001 — `kitty-specs/` is an audit boundary, not a classification

The operator ruled historical missions immutable (no slug/dir/file edits). Rather than introduce an
X-class or allowlist (forbidden by the program), the archive root is a single fixed pathspec applied
identically to inventory and terminal audits (`:(exclude)kitty-specs/`; ls-tree prefix drop). Omitting it
or adding any other exclusion is an audit error. Referrers outside the root that cite an archive path
containing the token are rewritten to cite `mission_id`/mid8 or a token-free path (M5).

## DD-002 — Ephemeral manifest, committed proof

`inventory-hits.tsv` (~49k rows) is generated, hash-pinned and counted in `inventory.md`, and
gitignored at mission level. Set equality is proven by deterministic regeneration (WP05 must match the
recorded SHA-256 byte-for-byte), which is stronger than reviewing a committed file and keeps the repo
small.

## DD-003 — Decisions are ledger entries, not prose

Both corrections were opened and resolved through `spec-kitty agent decision` (flow `plan`, resolved by
`operator`) before any artifact edit, so the fold is traceable to a decision id rather than chat context.

## DD-004 — ADR file identity and prior-ADR pointer (WP01)

Filename `2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md` (UTC authoring date,
next free sequence; basename satisfies the owned glob). The prior ADR `2026-07-15-1` keeps its `status:`
(its mechanics are not superseded) and gains a single pointer note marking only its terminology portion
superseded and assigning the file's future rewrite to M5 — the minimal diff T002 allows.

## DD-005 — OC granularity: seam-by-path, split on owner, no catch-all (WP02)

45 classes: 35 content + 10 pathname. Pathname rows get their own classes because renaming a file is distinct work from
rewriting its content even when the default owner is the same. `src/doctrine/skills/**` (M4 assets) is split from the
rest of `src/doctrine/**` (M2 topology); `packs/built-in/glossary_packs/**` (M1 authority) from other pack content
(M3/M4); test fixtures/baselines/allowlists (compatibility controls) from test code; generated manifests and docs data
from prose. `docs/reports/test-sanitation/**` (57% of rows) is one class so its bulk does not distort the others.
Rejected: a final catch-all rule (would hide missing coverage) and hand-labelled rows (irreproducible at 49k rows).

## DD-006 — CR candidates are path-scoped annotations with explicit budgets

Eight candidates (selection key, CLI group, tracker mode, org-pack key, URN prefix, import facade, overlay root,
skill/profile/directive IDs), each funded by disjoint frozen-base rows whose OC default owner equals the introduction
wave. Line-exact product coordinates are deliberately left to M2's frozen topology map; budgets bound them.

## DD-007 — Transition-level sequencing, not per-row ownership (WP03)

`methodology.md` fixes which transition retires each OC and proves the 49,050-row arithmetic; it leaves the one-row-
per-OC owner table and CR joins to `stacked-plan.md` (WP04) so that a finer split in WP04 cannot silently move rows
across a transition boundary without re-deriving §1.2.

## DD-008 — Guard fingerprint = audit coordinate, not file count (WP03)

The shrink-only guard compares coordinate+hash sets produced by the same checked procedure as the inventory, so
"equal-count substitution" and "moved hit" are detectable; CR-budgeted products and registered controls are the
only permitted additions until M6 deletes the baseline store.

## DD-009 — Archive immutability is a per-wave gate (WP03)

Every wave's merge gate compares the `kitty-specs` tree object at base vs result (this planning mission's own
directory excepted during this mission only), so the operator's immutability decision is enforced by construction.

## DD-010 — Owners inherit `inventory.md` defaults; no class moved (WP04)

Every OC's primary owner equals its WP02 default owner and the WP03 transition; no finer split was needed because no
class mixes two downstream owners. OC-22 (fixtures/baselines/allowlists) stays M2 for retargeting; the control
machinery created or retargeted after the frozen base is M6-removal work at the wave-local audit, per data-model §4.

## DD-011 — Executable archive gate (WP04)

"No pre-existing path under `kitty-specs/` edited/renamed/deleted; only the wave's own newly created mission directory
may be added" replaces literal tree-object equality, because each downstream wave is itself a Spec Kitty mission that
writes its own planning files under `kitty-specs/`. The terminal audit still excludes the whole root.

## DD-012 — `#2727` is a binding, not a deferral (WP04)

The issue-matrix row keeps `deferred-with-followup` (the issue's closure is the owner's) but its evidence states that
the glossary-authority slice is bound into M1 and cannot be split or deferred — resolving analysis finding I3.

## DD-013 — Verification reproduces from the contract, not from the implementer (WP05)

WP05 extracted the audit script from the committed `inventory.md` §8 (not the gitignored working copy), ran it in a
scratch directory against the frozen base, and additionally recomputed `match_sha256` and the direct `git grep` /
`git ls-tree` set equality with reviewer-written code from `contracts/inventory-schema.md`. Byte-identical SHA-256,
0 hash mismatches and set equality together discharge SC-002 without trusting the WP02 implementation.

### Assess at close (mission-tracer-files procedure)

DD-001 (archive root as audit boundary), DD-002 (ephemeral manifest), DD-005 (rule-derived OCs, no catch-all),
DD-008 (guard fingerprint = audit coordinate) and DD-011 (executable archive gate) are the decisions downstream M1–M6
must not reopen; all are encoded in the ADR/contracts and were verified consistent across spec, contracts, inventory,
methodology and stacked plan. No decision was found open at close.

## DD-014 — Terminal audit is toplevel-only and `:(top)`-anchored (squad fold)

A cwd-relative `-- . ':(exclude)kitty-specs/'` reported zero from any token-free subdirectory on the real repo
(reproduced by the live-evidence lens). The contract now requires `git rev-parse --show-prefix` to be empty, anchors the
pathspec with `:(top)` / `:(top,exclude)kitty-specs/` (verified live: identical counts from root and subdir), uses
`ls-tree --full-tree`, and names `mutation_subdir_cwd_cannot_pass_zero`. Symlink-target and NFKC/format-character
passes were added as checked steps because `git grep` never sees either.

## DD-015 — Guard fingerprint re-keyed tree-independently (squad fold; supersedes DD-008's hash clause)

`match_sha256` embeds the tree OID, so the "compare by hash" clause could never match across waves, and `(line,column)`
coordinates shift under unrelated edits. The fingerprint is now per path: occurrence count + multiset of
`(match, SHA-256 of containing line)`; shrink = no new path, no per-path count increase, no new line-pair. DD-008's
intent (coordinate, not file count) stands.

## DD-016 — Ownership follows the live seam, not the directory prefix (squad fold; supersedes DD-010 where they differ)

`src/doctrine/skills/**` is `doctrine` package data (registry, wheel, release gate) → M2 relocates the tree, M4 renames
IDs; `.kittify/doctrine` code literals → M2 with CR-07; `.kittify/config.yaml`'s two rows are the `doctrine.org.packs`
block (CR-04, M2) while `governance.doctrine` is `charter.yaml` (CR-01, M1). Sums re-derived (302 / 13,344 / 111 / 564 /
34,729 / 0); the TSV annotation column is orientation, `stacked-plan.md` §2.2 is the authority.

## DD-017 — Wave gates are "no row owned by this or an earlier wave", never "occurrence map empty"

Generated `charter.yaml` partitions are emitted by M2-owned code and carry M4-owned IDs; M1 cannot make them token-free
without editing M2/M4 surfaces. Later-wave rows are carried forward and listed; I6 alone is absolute.

## DD-018 — `src/doctrine/` converges into one named offer-side sub-package of `src/charter/`

The live boundary gates (`test_runtime_charter_doctrine_boundary`, `test_charter_sole_door_resolver_imports`,
`test_charter_facades_reexport_doctrine`, `_PRODUCTION_ROOTS`) and the one-way import rule are preserved under new names;
facade and implementation are never merged into one module. The sub-package name is fixed at M2's single map gate.

## DD-019 — Serialized historical records are an operator decision, not a planner's call

Quarantine `status.events.jsonl`, `kitty-ops/*.jsonl`, and `retrospective.yaml` files carry archive slugs / retired
profile IDs as identity values. Opened and deferred `DM-01M0P6C8C7Q6SPBT412V39RPN0`; it is M5's only open question.

## DD-020 — Immutable historical-record exclusion is four fixed roots, not one (resolves DD-019)

Operator decision 2026-08-23 resolved `DM-01M0P6C8C7Q6SPBT412V39RPN0` as **Option 1**: the three record roots
DD-019 named — `.kittify/migrations/mission-state/quarantine/` (quarantine `status.events.jsonl`), `kitty-ops/`
(`*.jsonl`), and `.kittify/missions/` (`**/retrospective.yaml`) — join `kitty-specs/` in the fixed, enumerated
exclusion set, amending `DM-01M0NMS9WPH33EPFCJQRTQVNSA`. Same mechanism as the archive root: one
`:(top,exclude)<root>` content pathspec and one ls-tree prefix drop per root — four independent excludes, never an
allowlist. No pre-existing path under any of the four is edited, renamed, or deleted by any wave; runtime may keep
appending new records to the three non-archive roots (this is the DD-009/DD-011 archive-gate pattern extended to
all four roots, not a new mechanism). The inventory was regenerated at the unchanged frozen base:
content 48,328→48,245 (−83), pathname 722→719 (−3), total 49,050→48,964 (−86); the 86 rows that left the manifest
are exactly the frozen-base rows under the three newly-fixed roots (OC-33 −22, OC-34 −61, OC-49 −3, all now M5's
`local_design_questions = 0`). `contracts/inventory-schema.md`, `inventory.md` §1/§3/§8, the ADR's terminal-audit
section and scope table, `data-model.md`, `methodology.md`, `stacked-plan.md`, `research.md`, and `quickstart.md`
were propagated in this landing pass; DD-001/DD-009/DD-011 (archive root as audit boundary / per-wave gate /
executable gate) now read as "the four fixed exclusion roots" wherever they said "the archive root" — the
mechanism DD-001 established is unchanged, only its enumerated root set grew.
