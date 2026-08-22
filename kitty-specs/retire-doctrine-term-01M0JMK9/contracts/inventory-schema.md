# Contract: Inventory Artifact Schema (IC-02)

**Governs**: `inventory.md` and supporting `inventory-hits.tsv`
**Requirements**: FR-006, FR-007, NFR-001, SC-002
**Consumed by**: M1–M6 occurrence maps, per-wave re-audits, and closeout

## Canonical pinned audit

WP01 fetches the target immediately before its first edit, fails closed unless the branch incorporates
that tip, and atomically records `target_ref`, `target_tip`, and `implementation_base` in
`implementation-baseline.json`. WP02 loads that frozen `target_tip` as `base_commit`; WP02–WP05 never
refetch/repoint it mid-mission. A branch-point merge base is not current enough. Run both audit
commands verbatim at that commit; do not shell-expand `git ls-files` (the repository exceeds
`ARG_MAX`).

```bash
baseline_file="kitty-specs/retire-doctrine-term-01M0JMK9/implementation-baseline.json"
target_ref="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["target_ref"])' "$baseline_file")"
base_commit="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["target_tip"])' "$baseline_file")"
implementation_base="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["implementation_base"])' "$baseline_file")"
git merge-base --is-ancestor "$base_commit" "$implementation_base"
git merge-base --is-ancestor "$implementation_base" HEAD
test "$(git merge-base "$target_ref" HEAD)" = "$base_commit"
git grep -aino --column -e 'doctrine' "$base_commit" -- .
git ls-tree -r -z --name-only "$base_commit" | python -c 'import sys; paths=sys.stdin.buffer.read().split(b"\0"); sys.stdout.buffer.write(b"\0".join(p for p in paths if p and b"doctrine" in p.lower()))'
```

Both ancestor checks and the exact merge-base equality must pass; both JSON SHAs must resolve to
40-character commits. If a
different target tip was incorporated after capture, the mission evidence is invalid: create a fresh
branch from that target, replay only planning commits, and restart at WP01.
The first command forces every tracked blob to text (`-a`) and emits one coordinate per
case-insensitive occurrence, including NUL-containing JSON/JSONL migration data. The second emits one
NUL-delimited record per tracked pathname containing the term. Content and pathname hits are
separate; a file can contribute both. `.git`, worktrees, and untracked/vendor files are excluded
structurally because the audit reads the pinned Git tree.

## `inventory-hits.tsv`

This supporting artifact is the non-sampled evidence behind `inventory.md`. Header and columns are fixed:

```text
hit_id	kind	path	line	column	classification_id	surface_category	compatibility_registry_id
```

- One row per `git grep -o` match: `kind=content`, with repo-relative path, line, and column. Strip the command's leading `<base_commit>:` revision prefix from the path; retain the SHA in frontmatter.
- One row per matched tracked path: `kind=pathname`, with empty line and column.
- Deterministic sort: `kind,path,line,column`; IDs are `H-C-######` and `H-P-######` in sorted order.
- `classification_id` is exactly one `OC-##`, `X1`, `X2`, or `X3`. `surface_category` is required for OC rows and empty for X rows.
- `compatibility_registry_id` is empty in the pre-M1 snapshot. Later per-wave manifests may set one
  `CR-##` overlay only on an OC product-compatibility hit after its introduction wave; X1/X2/X3 rows
  always leave it empty. The exact registry control record is X3 and is joined by its CR's separate
  `control_record_fingerprint`, not this column. No row is counted twice.
- No quoted line text is required; coordinates plus the pinned commit make every record independently recoverable.

## `inventory.md` frontmatter

```yaml
# round-trip: skip: illustrative inventory frontmatter schema; inventory.md is a documentation artifact, not a Pydantic payload
base_commit: <40-character SHA>
target_ref: origin/main
target_tip: <same 40-character SHA as base_commit>
date: <YYYY-MM-DD>
content_audit_command: <exact command, verbatim>
pathname_audit_command: <exact command, verbatim>
content_occurrences: <int>
pathname_occurrences: <int>
total_hits: <content_occurrences + pathname_occurrences>
manifest_sha256: <SHA-256 of inventory-hits.tsv>
```

## `inventory.md` sections

1. **Snapshot evidence** — frontmatter values, command output counts, and manifest hash.
2. **Occurrence classes and compatibility reservations** — OC table:
   `id | surface_category | path_patterns | occurrence_count | representative_examples | operator_typed`.
   Counts are manifest-row counts, never matching-line or file counts; every OC is assigned once to
   M1–M5 for primary-use retirement. Then a separate CR-candidate table:
   `id | legacy_form | semantic_seam | source_oc_ids | observed_source_hit_coordinates | observed_count | introduction_wave | removal_owner | canonical_target | control_record_path | verification`.
   These are planning observations, not future frozen values. `removal_owner` is M6;
   `control_record_path` is fixed to
   `tests/architectural/legacy_terminology_compatibility_registry.yaml`. `canonical_target` is either a fixed literal/path or
   `owner:M2; source_oc:<OC-##>`; the latter is a stable, fail-closed reference to M2's sole bounded
   question, never blank/TBD. M2 must replace it with the literal authoritative map row before any
   source relocation; target resolution does not change stable CR identity. Observed source coordinate sets are pairwise disjoint: one planning-base hit
   supports at most one semantic candidate. M1 reruns the audit at its actual pre-M1 base, reconciles
   drift fail-closed, and materializes disjoint actual coordinates, frozen product maxima, initial
   `reserved` disposition, and exact X3 control records/fingerprints. Aggregate maxima for a shared
   legacy form cannot exceed unique actual pre-M1 hits. The unpublished-distribution candidate later
   becomes `active` or a `closed-no-channel` tombstone at M2; either remains until M6. Examples are presentation only.
3. **Classified-out totals** — X1 non-public internal identifiers (supported public APIs are OC), X2 every merged ADR body/title (including the new Accepted terminology ADR after merge), immutable event journals, and merged-mission history, and X3 intentional non-user-facing quoted/test/data. Later manifests include exact CR control records as X3, with an empty manifest CR column; WP02's pre-M1 candidate table does not pretend those uncreated records exist. State each per-hit rule and manifest-derived count. Mission snapshots become X2 at merge whether or not later archived; active/unmerged mission artifacts are never X2. ADR status/pointer metadata is the narrow mutable carve-out. Glossary authorities, product aliases, warnings, and operator IDs are never X3 merely because they contain the string intentionally.
4. **Completeness arithmetic** — `total_hits = OC rows + X1 + X2 + X3`; manifest has no empty/unknown classification IDs and no duplicate coordinates. The optional CR overlay does not add a row or count. CR product rows are OC; X rows have empty CR IDs. Reservation source coordinate sets/control fingerprints are unique and disjoint.
5. **Out-of-repo deferrals** — each row requires `surface | repo | owner | target milestone | tracking reference or downstream process | rationale`. These records are outside arithmetic. No `TBD` or ownerless deferral may remain at closeout.

The inventory reserves every known public legacy identifier/route/key/path/parser or migrator
literal/redirect/warning as a CR candidate backed by disjoint planning-base evidence. No compatibility
literal or pathname may be invented later without such a candidate and source OC IDs. M1 records
actual-base drift, fixed target or M2 owner/OC reference, introduction wave, named tests, disjoint
actual source hits, frozen product maximum, and exact X3 control record. Each actual source hit funds
at most one semantic CR; its OC primary owner must equal the CR introduction wave (split a mixed-owner
OC/CR before assignment); aggregate maxima per shared legacy form cannot exceed unique actual pre-M1
hits. The introduction wave removes ordinary fingerprints, changes `reserved` to `active` (or M2
distribution-only `closed-no-channel`), and creates no more than the reserved budget of exact CR
product fingerprints; its full-literal X3 control record is separately exact and
never consumes that budget. M2 freezes any referenced target/disposition before edits.

OC/CR-to-mission assignment does not appear in the inventory. `stacked-plan.md` is its single owner.

## Per-wave contract

This planning mission's WP02–WP05 share its WP01 snapshot. Each future M1–M6 mission independently,
immediately before that wave's first edit, fetches/incorporates and freezes its own exact current
target tip plus wave implementation base; all WPs inside that wave reuse the wave-local snapshot. Each
wave reruns the ancestry/merge-base checks and two commands at its own exact base, and regenerates its scoped
occurrence map and hit manifest, records drift, and proves zero unclassified hits in scope. Manifests
retain one OC/X classification per hit and may add one CR overlay ID only to introduced OC product
compatibility hits, without double-counting. X rows always leave it empty. M6
additionally requires zero user-visible content and pathname hits, an empty CR registry, and only
explicit X1/X2/X3 rows.
