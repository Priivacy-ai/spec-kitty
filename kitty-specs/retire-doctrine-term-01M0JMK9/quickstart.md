# Quickstart / Verification Runbook: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 1 output**

Run in order from the repository root. SaaS sync stays disabled for local mission control.

## 1. Planning-scope and CI checks

Fetch the target and fail closed unless this branch incorporates its exact tip; a stale branch-point
base is not a valid inventory. Capture that target tip as the planning anchor. Before any WP01 edit,
persist the implementation anchor in `kitty-specs/retire-doctrine-term-01M0JMK9/implementation-baseline.json`; the shell variable alone is not evidence.

```bash
git fetch origin main
git merge-base --is-ancestor origin/main HEAD
planning_base="$(git rev-parse origin/main)"
git diff --name-only "$planning_base"
git diff --name-only
```

WP01's first operation is `git rev-parse HEAD`, before any other edit. Record that exact 40-character SHA as `implementation_base` plus `captured_at` (UTC), `captured_by`, `wp_id` (`WP01`), and `capture_command` in the owned JSON artifact, then commit it with WP01. WP05 loads the SHA from that file, verifies it is an ancestor of `HEAD`, and runs both `git diff --name-only <implementation_base>` and `git diff --name-only` so committed and working-tree deltas are covered.

The planning diff may contain mission planning/lifecycle files, ADR deliverables/registration surfaces, squad evidence, and docs-contract CI metadata. The implementation diff must remain within the union of WP-owned deliverables and these exact mission-relative runtime placements: `status.events.jsonl`, reduced `status.json`, `lanes.json`, `acceptance-matrix.json`, `issue-matrix.md`, `analysis-report.md`, `.kittify/dossiers/<mission>/...`, and `tasks/<WP-slug>/review-cycle-N.md` (all below `kitty-specs/<mission>/`). WP prompts are immutable inputs and must not be edited for activity logs. Both checks include committed changes; the final command includes working-tree changes.

```bash
pytest -q tests/contract/test_example_round_trip.py tests/architectural/test_ratchet_baselines.py
pytest -q tests/architectural/test_no_legacy_terminology.py
```

## 2. ADR registration and immutable history

```bash
python -m scripts.docs.freshen_adr_inventory --check docs/adr/3.x/<new-adr-file>.md
git diff docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
```

Expected: new ADR has actual date/deciders/reviewers and `status: Accepted`, with product-vocabulary effectiveness conditional on M1/I1. Index and page inventory are current. Old ADR diff is `Superseded` status/pointer metadata only; body remains byte-identical.

## 3. ADR self-sufficiency (SC-001)

One named independent reviewer — adversarial squad lens **or** operator — reads only the new ADR and answers these exact six questions:

1. What decision was made and what canonical term replaces the retired one?
2. How does Charter Pack differ from Charter Bundle, and what distinguishes Active Charter from Inactive Charter?
3. Which existing kind labels survive in their roles, and what replaces the former “Doctrine Domain” glossary sense?
4. What is in/out of scope, including operator IDs and the distinction between non-public internals versus supported public Python API names/imports, exact `doctrine.api.__all__`, and distribution/wheel metadata with canonical charter facades?
5. What is the 3.x compatibility policy and the 4.0 removal rule?
6. How does “charter” the governance term differ from the pre-existing `src/charter/` package?

All six correct from the ADR alone = pass. A second operator review is welcome but not a gate.

## 4. Inventory completeness (SC-002)

Run the contract's two commands verbatim at `inventory.md`'s `base_commit`:

```bash
base_commit="<inventory.md base_commit>"
git grep -aino --column -e 'doctrine' "$base_commit" -- .
git ls-tree -r -z --name-only "$base_commit" | python -c 'import sys; paths=sys.stdin.buffer.read().split(b"\0"); sys.stdout.buffer.write(b"\0".join(p for p in paths if p and b"doctrine" in p.lower()))'
```

Verify:

- `inventory-hits.tsv` has one row per content occurrence and matched pathname, with no duplicate coordinate, using the fixed eight-column header including nullable `compatibility_registry_id`;
- every row has exactly one OC-## or X1/X2/X3 classification;
- the CR column is empty in the planning snapshot and always empty for X rows; introduced product-compatibility OC rows later join exactly one CR without changing arithmetic;
- CR candidates have pairwise-disjoint observed source coordinates and counts; no coordinate funds two candidates;
- class/X totals are mechanically derived from manifest rows;
- `total_hits = content_occurrences + pathname_occurrences = OC totals + X1 + X2 + X3`;
- manifest SHA-256 matches frontmatter;
- `target_ref=origin/main`, `target_tip=base_commit`, and the target tip is an ancestor of current `HEAD`;
- all out-of-repo deferrals name repo, owner, milestone, tracking reference/process, and rationale; no `TBD`.

## 5. Stacked-plan determinism (SC-003)

- Every OC-## appears exactly once across M1–M5 in `stacked-plan.md`'s primary-owner table; every CR appears once at its M1–M4 introduction and once at M6 removal, with no coordinate double-funded or double-owned. Every funded source hit's OC primary owner equals its CR introduction wave; mixed-owner OCs/CRs are split.
- M1 has zero local design questions.
- M2's canonical operator-surface map is the only later question: M2 owns every command route,
  otherwise-unfixed serialized/API occurrence, supported public Python API name/import, the aggregate
  `doctrine.api` facade row with exact `__all__` evidence, separate legacy-bearing member rows, public
  distribution/wheel metadata, publication-evidence disposition, and mapped consumer regardless
  directory; it freezes the authoritative map + set-equal CLI projection. Each OC joins once; an
  unpublished distribution records no-channel evidence instead of inventing an alias. M3–M5 exclude
  mapped hits; non-public implementation remains X1.
- Fixed known rows need no question: M1 moves active glossary referrers to `docs/context/charter.md` and maps `governance.doctrine` → `governance.charter`; M2 separately maps org-pack config, tracker ownership, target URNs, and the known schema/category/policy/hash/tool-enum/JSON forms in the operator-map contract; M3 moves `.kittify/doctrine/` → `.kittify/charter-packs/` under the checked dual-read/collision contract.
- Every M1–M6 entry is `change_mode: bulk_edit`, owns an occurrence map, and states prefix-safe rollback.
- Invariant map is exact: M1→I1, M2→I2, M3→I3, M4→I4, M5→I5, M6→I6.

## 6. M1 spec-readiness (SC-004)

Draft `charter-authority-flip` using only this mission's ADR, inventory/manifest, methodology, and stacked plan. Pass requires zero new decisions and all of these owner-correct operations:

- rename `docs/context/doctrine.md` to `docs/context/charter.md`, update every active referrer, leave immutable X2 refs as byte-identical historical text, prove zero dangling active link/referrer, register the 3.x old-path redirect/loader alias, and update both YAML glossary authorities atomically under parity/#2727 coordination;
- direct-edit human-authored `charter.yaml` sections and curated `charter.md` text where classified; route graph/interview/runtime sections through owning workflows;
- use `charter generate` only for catalog/metadata refresh; never rely on `charter sync` as a writer;
- insert the exact legacy-free Terminology Canon line from the ADR contract in `charter.yaml`, not `AGENTS.md`;
- arm from exact fingerprints for every actual pre-M1 guard-root hit, including owner=M1. Materialize the complete pre-edit ordinary OC/X baseline, record the scoped same-PR M1 source/baseline shrink, then land the final post-M1 guard; each OC has one M1–M5 owner. From WP02 CR candidates, reconcile actual-base drift and materialize `tests/architectural/legacy_terminology_compatibility_registry.yaml` with semantic/disjoint source coordinates, frozen product maxima, fixed or fail-closed M2-referenced targets, dispositions, exact X3 control records, introduction waves, M6 removal, and named tests. Only the introduction wave may replace ordinary hits with at-budget OC product compatibility and it atomically changes `reserved` to `active` (or M2 distribution-only `closed-no-channel`); every funded source hit's OC owner equals that wave. M2 freezes referenced target/publication disposition before edits without changing CR identity. Control records do not consume budget, no coordinate funds two CRs, and unpublished distribution creates no alias. I6 requires only justified X plus empty CR control/product inventory. Add ordinary and compatibility-evasion mutations including overlap/double-funding/duplicate-control.

## 7. Methodology and rollback

For I0–I6, verify one state invariant and one named verifier for every S1–S10 surface. Guard tests must fail when a baselined file gains a hit, an allowed hit is replaced at equal count, a removed hit leaves a stale fingerprint, or a new file gains a hit. Compatibility tests also fail for an unregistered/wrong-wave legacy value or path, product-budget excess, product fragment construction, a double-funded source coordinate, an overlapping product fingerprint, or a duplicated/moved/stale X3 control record; unresolved M2 target/disposition blocks introduction before edits. Each wave regenerates per-hit evidence, shrinks ordinary records, and performs only its registered compatibility introductions/relocations.

Before a dependent wave lands, rollback may revert the current wave alone. Afterward, reverse the landed suffix or forward-fix. M6 can restore aliases only during supported 3.x compatibility; after 4.0, rollback is a release-level decision.

## Merge gate

| Check | Pass condition |
|-------|----------------|
| CI + scope | targeted tests green; both diff anchors valid |
| ADR | registered; six-question review 1/1 |
| Inventory | content + paths fully joined; zero unclassified |
| Plan | every OC has one M1–M5 owner; every CR has one introduction + M6 removal; funded OC owner = introduction; no unresolved cross-wave input |
| M1 dry run | zero decisions; file ownership and authority parity correct |
| Methodology | I0–I6, S1–S10 verifiers, fingerprint mutations, rollback all explicit |
