---
work_package_id: WP02
title: Occurrence Inventory — Mechanical Audit
dependencies:
- WP01
requirement_refs:
- C-003
- C-005
- FR-006
- FR-007
- NFR-001
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Evidence Base
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory-hits.tsv
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory-hits.tsv
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Occurrence Inventory

## Start

Run `spec-kitty agent profile show curator-carla`, load it, then read WP01's ADR, `contracts/inventory-schema.md`, `contracts/operator-surface-map-schema.md`, `data-model.md`, `research.md` R5–R9/R16, and `quickstart.md` §4. Check review feedback first.

## Goal

Create `inventory-hits.tsv` with one deterministic row per content occurrence and matching tracked pathname at a pinned commit. Derive `inventory.md` classes, totals, and deferrals from that manifest. Zero sampling; zero unclassified.

## T005 — Pin and audit

Load WP01's frozen snapshot and run these exact commands; never refetch/repoint the target mid-mission,
accept a stale branch-point merge base, or expand `git ls-files` into argv:

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

Both ancestor checks and exact target merge-base equality must pass, and the JSON SHAs must be
40-character commits; otherwise stop. The first forces all
tracked blobs to text and yields one row per match, not per matching line; do not replace `-a` with
`-I`, which drops NUL-containing migration/quarantine JSON/JSONL. The second yields one row per
matching tracked pathname. Preserve the frozen `target_ref`, `target_tip=base_commit`, raw counts, and commands
in inventory frontmatter.

## T006 — Build and classify manifest

Create `inventory-hits.tsv` with the fixed eight-column header from the contract. Sort by
`kind,path,line,column`; assign deterministic `H-C-######` / `H-P-######` IDs. Each row receives
exactly one OC-## or X1/X2/X3. OC rows also receive S1–S10; the planning snapshot's
`compatibility_registry_id` is empty because M1 has not introduced any CR product hit.

Mandatory coverage includes:

- CLI/help/errors/output and scripted consumers;
- all glossary authorities: `docs/context/doctrine.md`, every active referrer, immutable X2 references retained as historical text, `.kittify/glossaries/spec_kitty_core.yaml`, built-in glossary pack;
- skills, profiles, directives, prompts, `.kittify/overrides/`, generated agent artifacts;
- charter bundle with per-section ownership;
- built-in/org/project packs, `.kittify/doctrine/` pathnames and overlays, with canonical `.kittify/charter-packs/` destination fixed for M3;
- runtime output, workflow filenames/uses, root docs, and active human-facing Markdown/READMEs under source directories;
- `.kittify/config.yaml` serialized `doctrine:` and persisted paths;
- every command/serialized/API form and its producers/consumers, including target URNs, target-kind/category enums, policy/hash keys, tool-surface values, and emitted JSON aliases required by `contracts/operator-surface-map-schema.md`;
- every supported public Python name/import identified by `__all__`, package `__init__` re-export,
  public API/operator docs/skills, or external contract, including catalog/selection/service examples;
  record one aggregate `doctrine.api` facade/class input with exact `__all__` member evidence (without
  inventing hit rows for legacy-free names), plus public metadata content inside
  `src/doctrine/pyproject.toml`, the
  `spec-kitty-doctrine` project/distribution/wheel name, and wheel-closure consumers/tests;
  non-public symbols and non-emitted physical implementation pathnames such as
  `src/doctrine/pyproject.toml`/`src/doctrine/api.py` alone are X1;
- all eight doctrine-named skill directories, including `spec-kitty-charter-doctrine`, plus `doctrine-daphne` and `018-doctrine-versioning-requirement`, as in-scope operator IDs mapped by the ADR table.

Apply classifications per hit:

- X1 non-public internal code identifiers only; supported public APIs are OC;
- X2 every merged ADR body/title (including the new Accepted terminology ADR after merge), immutable
  event journals, and merged mission snapshots whether or not archived; active/unmerged mission
  artifacts are never X2, and ADR status/pointer metadata remains the narrow mutable carve-out;
- X3 intentional non-user-facing quoted test/matcher/data only. Later exact CR registry control
  records are X3 with an empty manifest CR column; product aliases/warnings/keys/paths/operator IDs
  remain OC.

Mixed files may contain OC and X rows. Path patterns/examples are summaries, not evidence.

Every pre-M1 OC is ordinary primary use with one future M1–M5 owner. Separately build the CR-candidate
table for every semantic legacy identifier/route/key/path/parser/migrator/redirect/warning form:
stable CR ID, full form, semantic seam, source OC IDs, pairwise-disjoint observed coordinates/count,
introduction wave, M6 removal, fixed target or fail-closed M2 owner/OC reference, fixed control path
`tests/architectural/legacy_terminology_compatibility_registry.yaml`, and planned tests. The same
literal may have several candidates only for disjoint semantic coordinates. These are planning
observations; M1 reruns the actual-base audit and materializes frozen maxima/control fingerprints.
WP04 must assign every funded source hit's OC primary owner to the same introduction wave; split any
mixed-owner OC/CR before assignment.

## T007 — Derive and prove

Derive each OC/X count from manifest rows. Confirm no duplicate `(kind,path,line,column)` coordinate,
no empty classification, empty CR column in this planning snapshot,
`manifest rows = content occurrences + pathname occurrences`, and
`OC totals + X1 + X2 + X3 = total_hits`. Prove CR candidate observed coordinate sets are pairwise
disjoint and aggregate counts per form do not exceed unique matching hits. Compute manifest SHA-256.

## T008 — Write inventory

Follow the five-section schema. Do not add OC/CR assignment fields; WP04 owns assignment. Out-of-repo rows require surface, repo, owner, milestone, tracking reference/downstream process, and rationale. No `TBD` may remain; a fail-closed M2 owner/OC target reference is the only allowed deferred target form.

Record the glossary parity dependency and open issue #2727, but do not defer atomic authority consistency or invent another mission.

## Verification

Re-run both audit commands at the recorded SHA and reproduce coordinate totals. Verify manifest hash, uniqueness, join completeness, class arithmetic, and ≤3 representative examples per class. A later SHA's drift is recorded separately, never absorbed into the pinned snapshot.

Reject per-file-only evidence, line-based counts, missing pathnames, active-glossary X3,
active/unmerged-mission X2, supported-public-API/operator-ID X1, or ownerless deferrals. Verify the
merged-mission X2 rule is independent of later archive state.

## Activity Log

The generation record below is immutable. Do not edit this prompt to append activity;
status/history is event-log owned. Use
`spec-kitty agent tasks move-task WP02 --to <status>`.

- 2026-08-21T00:00:00Z – system – Prompt created.
