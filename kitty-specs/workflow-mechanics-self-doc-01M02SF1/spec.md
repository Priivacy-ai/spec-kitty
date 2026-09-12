# Mission Specification: Self-documenting repo (Bucket 2) — workflow/CI/status mechanics

**Mission Branch**: `kitty/mission-workflow-self-doc`
**Created**: 2026-08-15
**Status**: Draft
**Input**: Migrate the workflow / CI / git / status-&-sync **mechanics** still stranded in a maintainer's private agent-memory into the repo's canonical knowledge homes, so a bare-system agent (repo + installed skills/packs only) is self-sufficient. Follow-up to `self-documenting-repo` (#3448/#3453); umbrella #3464. Audit: `work/bucket2-workflow-memory-audit.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A bare-system agent stops learning gate mechanics the hard way (Priority: P1)

An agent working the mission lifecycle hits a merge-gate, an issue-matrix verdict, a review-cycle artifact, or a SaaS sync drain, and today must consult a maintainer's private notes because no canonical doc states the mechanics. After this mission, the durable mechanics live in Common Docs (`review-gates.md`, a new `sync-drain.md`, the coverage/CI references) and are discoverable via `spec-kitty docs query`.

**Why this priority**: the status/mission/sync gate mechanics are the genuine gap surface (Cluster C of the audit) — the highest-value, least-documented residue.

**Independent Test**: a reader finds, in Common Docs alone, (a) why a hand-authored `approved` artifact fails the merge gate and how to recover, (b) how issue references are discovered (over ALL mission docs) and that `issue-verdict` needs `--actor` — with `review-gates.md` **citing** `ERROR_CODES.md` + `spec-kitty-mission-review/SKILL.md` for the verdict vocabulary/schema/`.json`-canonical semantics rather than restating them (C-003), and (c) the 3-gate sync drain order — with no private memory.

**Acceptance Scenarios**:

1. **Given** a WP blocked at merge on `terminal_wp_latest_review_artifact_must_not_be_rejected`, **When** the agent reads `review-gates.md`, **Then** it learns the recover-by-fresh-review path (never hand-author an approval).
2. **Given** a mission with un-drained SaaS sync, **When** the agent reads `docs/operations/sync-drain.md`, **Then** it applies the three gates in order and distinguishes the `sync doctor` false-green from `sync status` Delivered.

### User Story 2 — The canonical docs stop lying about workspace resolution (Priority: P1)

`AGENTS.md`/`CLAUDE.md` line 307 still claims a `lanes.json`-absent legacy fallback that the code removed (`resolve_workspace_for_wp` raises `MissingLanesError`). An agent trusting it is actively misled.

**Why this priority**: a live stale-doc regression in the most-loaded file — it proves the mission thesis and is a quick, high-value correctness fix.

**Independent Test**: `grep` shows no surviving legacy-fallback claim in `AGENTS.md`; a guard test pins the corrected statement; `execution-lanes.md` carries the real `MissingLanesError` contract.

**Acceptance Scenarios**:

1. **Given** the corrected `AGENTS.md`, **When** an agent reads the workspace-resolution section, **Then** it learns that flat/`SINGLE_BRANCH`/`LANES` missions still require `lanes.json` (no `-WP##` fallback).

### User Story 3 — Landing/CI practices are cited, not re-remembered; ephemera are team-shared, not private (Priority: P2)

The landing/git/CI-tooling half of the audit is already-home in `pr-landing.md` and the toolguides; those private notes become deletable echoes. The genuine landing/CI residue (stale-stack diagnostic, history-compression recipe, the diff-coverage critical-path-move trap, the CI-label skip guard, the closing-keyword `gh` trap) migrates to its home; four narrow-but-shareable heuristics seed the git-tracked `.kittify/memory/` store.

**Why this priority**: lower-leverage than Cluster C but completes the migration and clears the private index.

**Independent Test**: each of the five genuine landing/CI gaps is findable in its cited home; the four learned-facts are present in `.kittify/memory/`; the migration manifest maps every audited memory to home / already-home@citation / learned-fact / keep-private.

**Acceptance Scenarios**:

1. **Given** the manifest, **When** the completeness test runs, **Then** every `home:`/`already-home:` path resolves on disk and every one of the 49 audited memories carries a resolution token.

### Edge Cases

- A memory is *partially* already-home (principle documented, operational checklist not) → route the missing operational half to Common Docs, cite the principle's home by its **actual wording/ADR** — e.g. `read_write_partition_symmetry`: the read/write-symmetry principle is in `artifact-placement-seam.md` (governing ADR 2026-06-24-1), the partition-move audit checklist is not (cite the ADR/wording, NOT a phantom "INV-5" label — that string does not appear in the file).
- A memory documents a behavior *quirk* → no new bug filed; the three Bucket-2 quirks were already filed by Bucket 1's G5 (#3450/#3451/#3452).
- A rule with no charter/directive statement → route mechanics to Common Docs; **do NOT** add a charter directive without explicit operator opt-in (C-004).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Review-gate mechanics home | As an agent, I want the review-cycle-artifact + merge-gate mechanics + the genuinely-absent issue-matrix half (discovery-surface over all mission docs; `issue-verdict --actor`) in one `review-gates.md` section, **citing** `ERROR_CODES.md`/`spec-kitty-mission-review/SKILL.md` for the already-home verdict vocabulary/schema/`.json`-canonical facts (no restatement — C-003). | High | Open |
| FR-009 | Doctrine-tactic enrichment (practice half) | As an agent at `review`/`implement`, I want the review-*discipline* heuristics enriching the existing doctrine tactics that own them — `gate_unmask_cannot_self_validate` + `seam_classification_two_axes` → `architectural-gate-non-vacuity.tactic.yaml`; `review_artifact_no_hand_author` (principle) → `reviewer-implementer-role-separation.tactic.yaml`; `seam_bypass_stale_comment` → `canonical-source-unification.tactic.yaml` — so they reach the action-scoped doctrine retrieval path, not just Common-Docs navigation. (Doctrine enrichment, NOT a charter edit — C-004 does not gate this.) | Medium | Open |
| FR-002 | Sync-drain runbook | As an operator, I want a `docs/operations/sync-drain.md` with the 3-gate drain order and the doctor-false-green trap (durable core only; drop fixed-defect analyses). | High | Open |
| FR-003 | Stale-doc correctness fix | As an agent, I want `AGENTS.md`/`CLAUDE.md` line 307 corrected (no phantom `lanes.json`-absent fallback) with a guard, and the real `MissingLanesError` contract in `execution-lanes.md`. **Spans two lanes**: the `AGENTS.md`-only fix+guard is a standalone fast lane (repo-root, no rollup regen — the P1 quick win); the `execution-lanes.md` half lives in the serialized DOCS lane. | High | Open |
| FR-004 | CI reference enrichments | As an agent, I want the module-move diff-coverage remedy (`coverage-signals.md`), the CI-label skip guard + lint-inputs-tracked trap (`known-friction-points.md`), and the multi-WP true-base classification documented. | Medium | Open |
| FR-005 | Landing/history how-to | As a maintainer, I want the stale-stack two-dot/three-dot diagnostic in `pr-landing.md` and a `compress-mission-history.md` how-to with the path-bucket `git commit-tree` recipe + tree-parity proof. | Medium | Open |
| FR-006 | Tracker toolguide | As an agent, I want the `gh` closing-keyword pitfall ("Closes #A,#B" links only #A) in `GITHUB_TRACKER.md` + its `.toolguide.yaml`, DRG-consistent. | Medium | Open |
| FR-007 | Learned-facts seeding | As the team, I want the four narrow-but-shareable heuristics (collect-universe-once, no-RecursionError≠no-cycle, sync-identity-form-split, lane-base-vs-moving-upstream) in the git-tracked `.kittify/memory/`. | Low | Open |
| FR-008 | Migration manifest + completeness test | As a reviewer, I want a committed manifest mapping all 49 audited memories → `home:` / `already-home:` / `learned-fact:` / `keep-private` / `charter-candidate`, with a NEW test (not the inherited G1–G6 one) whose token set + cluster taxonomy (A/B/C) match this mission: `home:`/`already-home:`/`learned-fact:` are **path-checked** (the cited/created file must exist), `keep-private`/`charter-candidate` are **recognised-but-pathless**; every one of the 49 rows carries a token. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Docs freshness | `check_docs_freshness --ci` errors=0 after every doc touch; new pages carry frontmatter + `toc.yml`/inventory entries; rollups regenerated. | Reliability | High | Open |
| NFR-002 | No new merge-blocking red | No new honest-red on `main` (ADR 2026-07-17-1); terminology guard green on every prose/doctrine touch. | Reliability | High | Open |
| NFR-003 | Derived-from-repo, not memory | Every migrated fact is verified against current code/behavior (C-005), not transcribed from the private note; stale claims corrected, not copied. | Correctness | High | Open |
| NFR-004 | Doctrine integrity | Doctrine edits (WP-E toolguide + FR-009 tactics) pass: `test_no_dead_doctrine_paths.py` (every `packs/built-in/**` cross-link resolves — a new closing-keyword section adds links); `spec-kitty doctrine regenerate-graph --check` byte-identical (regen ONLY if a node **title** changes — body/summary edits are byte-identical); `spec-kitty doctor doctrine --json` clean; terminology guard (NFR-002). **Not** golden-count/description-length (phantom for toolguides) and **no** 12-agent parity/regen (toolguides aren't copied to agent dirs). | Reliability | Medium | Open |
| NFR-005 | Content-anchored, not empty-stub | Each migrated doc/tactic carries a machine-checkable content anchor (a stable heading/keyword grep) so an empty-file false-green is impossible — e.g. `sync-drain.md` contains `SPEC_KITTY_ENABLE_SAAS_SYNC` (not `..._ENABLED`); `compress-mission-history.md` contains `git commit-tree`; `review-gates.md` cites `terminal_wp_latest_review_artifact_must_not_be_rejected`. The completeness/guard tests assert these anchors, not mere file existence. | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Reuse established homes | Route to the #2860 canonical homes (charter / toolguides / Common Docs / `.kittify/memory/`); never invent a parallel home. | Technical | High | Open |
| C-002 | Already-home = delete, not duplicate | The 20 already-home echoes get NO new repo content; the manifest cites their existing home and they are dropped from private memory. | Technical | High | Open |
| C-003 | Cite, don't restate | Where a principle already lives in a home, migrate only the missing operational half and cite the principle (avoid the SSOT drift the Bucket-1 squad flagged). | Technical | High | Open |
| C-004 | No unilateral charter edit | The one charter-routing candidate (two-party review integrity) is **operator-gated**: route mechanics to `review-gates.md`; add a directive ONLY on explicit operator opt-in. | Governance | High | Open |
| C-005 | Manifest allows non-migrating outcomes | The manifest must permit `already-home` / `learned-fact` / `keep-private` resolutions, not force every memory to a new Common-Docs page. | Technical | Medium | Open |
| C-006 | Serialize the shared rollups | Every `docs/**` page touch regenerates `docs/development/3-2-page-inventory.yaml` + `3-2-docs-retrieval-index.yaml`; these two files live in the write-scope of **exactly one** serialized DOCS lane. `AGENTS.md` (repo-root), the toolguide/tactic doctrine lane (`packs/**`), and the learned-facts lane (`.kittify/memory/**`) are standalone parallel lanes; the terminal manifest+test lane depends on all home-producing lanes. Never strip the rollups from a WP to dodge the collapse (concurrent regen clobbers at merge). | Technical | High | Open |

### Key Entities

- **Audited memory**: one private-memory entry with a disposition (already-home / migrate:common-docs / migrate:toolguide / learned-fact / keep-private / charter-candidate).
- **Canonical home**: charter, a doctrine toolguide, a Common Doc, or the git-tracked `.kittify/memory/` store.
- **Migration manifest**: the committed proof mapping every audited memory to its resolution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bare-system agent can, from Common Docs alone, resolve a merge-gate rejection, an issue-matrix verdict, and a sync drain — verified by the manifest home-paths existing and containing the claimed mechanics.
- **SC-002**: `grep` finds zero surviving legacy `lanes.json`-fallback claims in `AGENTS.md`/`CLAUDE.md`; the guard test passes.
- **SC-003**: `check_docs_freshness --ci` errors=0; terminology guard green; `doctor doctrine --json` clean after the toolguide edit.
- **SC-004**: The migration manifest resolves all 49 audited memories; the completeness test (home-path existence + resolution-token presence) passes.
- **SC-005**: After merge, the migrated + already-home + learned-fact memories are removable from the private store (a per-operator checklist, out of mission scope — mirrors Bucket 1 C-004).

## Post-spec squad reconciliation (folded)

Three profile-loaded opus lenses (paula-patterns SSOT, curator-carla routing/gates, planner-priti decomposition) corrected the spec before planning:

- **SSOT re-scope of the issue-matrix migration (paula, MAJOR).** The verdict vocabulary/schema/`.json`-canonical/deferred-handle/in-mission facts are **already home** in `src/specify_cli/cli/commands/review/ERROR_CODES.md` and `.agents/skills/spec-kitty-mission-review/SKILL.md` (C-008 block) — the audit never opened them. FR-001 now migrates only the genuinely-absent operational half (the `discover_issue_references`-over-all-mission-docs discovery surface + `issue-verdict --actor` gate) and **cites** the rest as `already-home` manifest rows. (`ERROR_CODES.md` ships under `src/` so a bare-system agent has it, but it's outside the `spec-kitty docs query` index — a pointer is legitimate.)
- **Doctrine-tactic layer the audit skipped (curator, MAJOR-1) → new FR-009.** Three review-*discipline* heuristics have exact-fit existing tactic homes reachable on the action-scoped doctrine path: `gate_unmask_cannot_self_validate` + `seam_classification_two_axes` → `architectural-gate-non-vacuity.tactic.yaml`; `review_artifact_no_hand_author` (principle) → `reviewer-implementer-role-separation.tactic.yaml`; `seam_bypass_stale_comment` → `canonical-source-unification.tactic.yaml`. Their gate *mechanics* stay in `review-gates.md` (reference); the *heuristic* half enriches the tactic. Doctrine enrichment, not charter (C-004 unaffected).
- **NFR-004 gate list corrected (curator, MAJOR-2).** Real doctrine gates: `test_no_dead_doctrine_paths.py` cross-link resolution, `doctrine regenerate-graph --check` (regen only on a node **title** change), `doctor doctrine --json`. Removed phantom golden-count/description-length; confirmed no 12-agent parity step (toolguides aren't copied).
- **Lane decomposition (planner, MAJOR-1) → C-006.** One serialized DOCS lane owns the two rollup yaml; `AGENTS.md`, the `packs/**` doctrine lane, and `.kittify/memory/**` are standalone parallel lanes; terminal manifest depends on all. Mirrors Bucket 1's proven lane-c shape.
- **FR-008 test vocabulary + NFR-005 content anchors (planner, MAJOR-2/3).** The completeness test is authored fresh for this mission's token set + A/B/C clusters (not the inherited G1–G6 test); `already-home`/`learned-fact` are path-checked, `keep-private`/`charter-candidate` pathless. Each migrated doc/tactic carries a grep-able content anchor so an empty stub can't false-green.
- **MINORs folded:** phantom "INV-5" citation → cite the ADR/wording (Edge Cases); `review-gates.md` title/scope widened for the seam heuristics; trim the decorative `lane_move_task_sync_hang` second citation; `collect_universe_once` LF fit is weak (already embodied in `_gate_coverage.collect_universe`) — WP-G reconsiders (drop or toolguide) and adds a one-note format convention so the learned-facts store doesn't reproduce the grab-bag failure.

**Charter-gating verified (curator, charge #2 held):** no Bucket-2 memory states a rule absent from the charter/a directive/an ADR; the one candidate stays operator-gated (C-004). Standing Order #9 (`charter.md:92`) and ADR 2026-07-01-1 confirmed as the homes for the two "rule-like" already-home entries.
