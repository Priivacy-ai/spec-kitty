# T054 ADR Cross-reference Audit

**Date**: 2026-05-24
**Auditor**: claude:opus-4-7:curator-carla:curator
**Mission**: `charter-ux-and-org-pack-vocabulary-01KSAF14`

## Intent

Verify that the three new ADRs authored in this mission cross-reference each
other and `architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`
so a future reader landing on any of the four ADRs can navigate the full
decision chain without leaving the directory.

## Source ADRs (authored across separate lanes — read from lane worktrees)

| Lane | ADR | Path |
|------|-----|------|
| `lane-a` | `2026-05-24-1` — Charter Freshness UX Contract | `.worktrees/charter-ux-and-org-pack-vocabulary-01KSAF14-lane-a/architecture/3.x/adr/2026-05-24-1-charter-freshness-ux-contract.md` |
| `lane-e` | `2026-05-24-2` — Pack Augmentation Vocabulary | `.worktrees/charter-ux-and-org-pack-vocabulary-01KSAF14-lane-e/architecture/3.x/adr/2026-05-24-2-pack-augmentation-vocabulary.md` |
| `lane-g` | `2026-05-24-3` — `shipped` → `built-in` Cutover | `.worktrees/charter-ux-and-org-pack-vocabulary-01KSAF14-lane-g/architecture/3.x/adr/2026-05-24-3-shipped-to-built-in-cutover.md` |

## Findings

### `2026-05-24-1` (Charter Freshness UX Contract) — incomplete

| Target reference | Present? | Evidence |
|------------------|----------|----------|
| `2026-05-16-1` (doctrine layer merge semantics) | yes | line 6: `**Cross-references**: [...2026-05-16-1...]` |
| `2026-05-24-2` (pack augmentation vocabulary) | **MISSING** | no occurrence |
| `2026-05-24-3` (`shipped` → `built-in` cutover) | **MISSING** | no occurrence |

**Recommendation**: at mission merge time, extend the `Cross-references`
section of `2026-05-24-1` to include links to `2026-05-24-2` and
`2026-05-24-3`. The natural insertion point is the same line 6 block — make
it a bulleted list of three siblings + the predecessor `2026-05-16-1`.

### `2026-05-24-2` (Pack Augmentation Vocabulary) — incomplete

| Target reference | Present? | Evidence |
|------------------|----------|----------|
| `2026-05-16-1` (doctrine layer merge semantics) | yes | line 9, 13, 36, 47, 98 (named as predecessor) |
| `2026-05-24-1` (charter freshness UX contract) | **MISSING** | no occurrence |
| `2026-05-24-3` (`shipped` → `built-in` cutover) | **MISSING** | no occurrence |

**Recommendation**: at mission merge time, add a `Cross-references` section
near the predecessor block listing the two sibling ADRs. The vocabulary
rename ratified by `2026-05-24-3` is the natural follow-on; the freshness
contract from `2026-05-24-1` shares the same operator surface.

### `2026-05-24-3` (`shipped` → `built-in` Cutover) — almost complete

| Target reference | Present? | Evidence |
|------------------|----------|----------|
| `2026-05-16-1` (doctrine layer merge semantics) | yes | line 10, 18, 131, 138 |
| `2026-05-24-2` (pack augmentation vocabulary) | yes | line 11, 41, 96, 107, 141 |
| `2026-05-24-1` (charter freshness UX contract) | **MISSING** | no occurrence |

**Recommendation**: at mission merge time, add `2026-05-24-1` to the existing
`Cross-references` / `Predecessors` block (around lines 10-11 and 138-141).

## Why this audit instead of direct edits

WP09's `owned_files` declaration (`docs/**`, `CHANGELOG.md`, `README.md`)
intentionally excludes `architecture/3.x/adr/*`. The three new ADRs live on
their respective lane worktrees and have not yet been merged into the
mission branch. Modifying them from WP09's planning-artifact workspace
would either:

1. Write to lane worktrees that WP09 does not own, violating the
   single-owner contract for branched files; or
2. Land cross-references on the mission branch that conflict with the
   lane merges still ahead in the dependency chain.

The cleanest remedy is to capture the gap here so the mission-merge phase
(or a tiny follow-on WP) can apply the three missing cross-references in
one atomic commit on the mission branch, after all three new ADRs have
landed there.

## Suggested follow-up

Add to the mission's pre-merge checklist:

> Before declaring the mission ready for `spec-kitty merge`, apply the
> three missing ADR cross-references documented in
> `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/tasks/WP09-wave4-docs-and-changelog/adr-cross-ref-audit.md`.
> All three new ADRs must reference each other AND `2026-05-16-1` in a
> consistent `Cross-references` block so the directory reads as a coherent
> decision chain.

## Acceptance status

- [x] Predecessor `2026-05-16-1` referenced from every new ADR.
- [ ] `2026-05-24-1` references `2026-05-24-2`. → captured for mission-merge.
- [ ] `2026-05-24-1` references `2026-05-24-3`. → captured for mission-merge.
- [ ] `2026-05-24-2` references `2026-05-24-1`. → captured for mission-merge.
- [ ] `2026-05-24-2` references `2026-05-24-3`. → captured for mission-merge.
- [ ] `2026-05-24-3` references `2026-05-24-1`. → captured for mission-merge.
- [x] `2026-05-24-3` references `2026-05-24-2`. (already present)
