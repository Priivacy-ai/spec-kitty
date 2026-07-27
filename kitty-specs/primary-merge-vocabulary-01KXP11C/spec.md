# Mission Specification: Primary & Merge Vocabulary Disambiguation

**Mission Branch**: `feat/terminology-primary-merge-disambiguation`
**Created**: 2026-07-16
**Status**: Draft
**Input**: GitHub issue #2653 — disambiguate the overloaded terms **"primary"** (4 senses) and **"merge"** (3 senses). Operator directive (2026-07-16): per DDD ubiquitous language / language-oriented design and the project charter §Terminology Canon ("keep domain language precise across specs, **code**, and docs"), the disambiguation MUST also reach **code artefacts** (safe renames), not glossary/prose alone. This mission is **Track 1** of a two-track epic. Grounded in the research report `research-2653-primary-merge-disambiguation.md` and the two locked operator decisions: (D1) **keep "Primary Branch"** as the canonical Sense-B term (reject the issue's "default branch" proposal); (D2) structure as an **epic** — Track 1 (this mission: cheap, low-risk) + Track 2 (a separate, isolated, bulk-edit-gated Sense-C code rename).

## Context & Motivation *(why this mission exists)*

Two Spec Kitty terms are overloaded badly enough to cause real misreads.

**"primary" carries 4 distinct senses** (~1,857 occurrences across code + docs + doctrine):

| Sense | Meaning | **Canonical term (this mission enforces)** | Aliases to retire in prose |
|-------|---------|--------------------------------------------|----------------------------|
| **A. Partition** | artifact-kind partition — PRIMARY (planning) vs COORD (status) | **"PRIMARY partition"** | bare "primary" without "partition/artifact" |
| **B. Branch** | the repository's default integration branch | **"Primary Branch"** (already canonical in the glossary; D1) | "default branch", "the primary", bare "main" |
| **C. Surface/checkout** | canonical repo-root checkout vs lane worktree (the dominant cluster) | **"repository root checkout"** (charter-decreed) | "primary surface", "primary checkout" |
| **D. Ref/target** | the ref planning artifacts commit to | **"target ref / commit target"** | "primary target", "primary ref" |

**"merge" carries 3 distinct operations**:

| Sense | Meaning | **Canonical term** |
|-------|---------|--------------------|
| **1** | `spec-kitty merge` — LOCAL lane consolidation into the mission branch (no push) | **"lane consolidation / consolidate"** |
| **2** | `git merge` — branch integration (mission → target) | **"branch integration / git merge"** (explicit) |
| **3** | PR merge to origin/main (operator-only) | **"publish to origin/main / operator merge"** |

The overload is not academic: during a plan double-check on mission `implement-loop-commit-hardening-01KXJ1ZX`, a `kind=None → PRIMARY` **partition** verdict was nearly implemented as "route to the primary **branch** (main)" — which would have re-broken the WP00 refusal-to-main fix (ADR `2026-06-24-2`). Governance prose already carries the collision (that ADR uses "primary checkout", "PRIMARY-partition kinds", and "primary target_branch" in one paragraph) and `CLAUDE.md` carries three defensive warnings about it — a smell that the words, not the readers, are the problem.

**Two of issue #2653's premises were stale and are corrected here** (research-grounded):
1. The glossary is **not** unpopulated at `glossary/contexts/`. That path is the **retired legacy home**; the charter (FR-009) folded canonical terminology to **`docs/context/`**, where `orchestration.md` and `execution.md` are mature. `glossary/README.md` still indexes the dead `glossary/contexts/` dir — a stale-pointer bug this mission fixes.
2. Sense B is **already** canonicalized as **"Primary Branch"** in `docs/context/orchestration.md`; the issue's "rename to default branch" would regress against the glossary. D1 keeps "Primary Branch".

**This is Track 1** — the cheap, low-regression surface. It changes **no shipped identifier, no serialized key, no CLI/command name, no node kind, and no runtime behavior.** The heavy, high-risk Sense-C **code** rename (`primary_feature_dir_for_mission` cluster → `repository_root_checkout_*`; ~400 occ / 111 pinning test files / two literal-string arch gates / WP00-load-bearing) is deliberately deferred to **Track 2** (a separate isolated bulk-edit mission). The removal of the runtime glossary **package** `src/glossary/` is out of scope entirely and tracked as **#2727** (blocked-by #1418, under epic #1629).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A reader learns one canonical term per concept (Priority: P1)

A contributor or AI agent reading the doctrine docs, glossary contexts, CLI `--help`, and code docstrings encounters exactly **one** term for each sense: "PRIMARY partition", "Primary Branch", "repository root checkout", "target ref" for the four `primary` senses, and "lane consolidation", "branch integration", "publish to origin/main" for the three `merge` operations. They never have to disambiguate which "primary" or which "merge" a passage means.

**Why this priority**: This is the core deliverable and the whole point of the epic. Track 2 and every future terminology PR build on these shared words; ambiguity here propagates into every downstream design.

**Independent Test**: Read the touched glossary/docs/help/docstring surfaces end-to-end. Each sense is named by exactly its canonical term; every remaining bare "primary"/"merge" either refers unambiguously to one sense by adjacent qualification, or is an exempt shipped identifier. No passage uses "primary" or "merge" ambiguously.

**Acceptance Scenarios**:

1. **Given** `docs/context/orchestration.md` and `execution.md`, **When** a reader looks up "primary" or "merge", **Then** each of the 4 primary senses and 3 merge senses has a distinct glossary entry with its canonical term, `Do NOT use when` guidance, and cross-links — using the existing per-term table format.
2. **Given** `spec-kitty merge --help` and the merge-step doctrine prompts, **When** a reader reads them, **Then** the three merge operations are named explicitly (consolidate / integrate / publish), while the literal strategy values `merge`/`squash`/`rebase` and the command name `merge` are unchanged.
3. **Given** the conflating ADR paragraph and `CLAUDE.md`'s three defensive warnings, **When** a reader reads them post-mission, **Then** each "primary" is qualified to its sense and the defensive warnings are replaced by a single glossary cross-reference.

### User Story 2 — A maintainer inherits safe, de-duplicated code (Priority: P2)

A maintainer touching the branch resolvers or the merge/partition helpers finds (a) a **single** canonical `resolve_primary_branch` instead of two divergent copies, and (b) the low-risk **internal** merge/partition helper names aligned to the canonical operations — with **zero** change to any shipped identifier, serialized key, enum literal, or CLI/command name.

**Why this priority**: The operator directive requires the vocabulary to reach code, and these are the code changes that are safe to make in the cheap track. Consolidating the duplicate resolver also removes a real drift/whack-a-field hazard.

**Independent Test**: `core/git_ops.py:270` is the single canonical `resolve_primary_branch` behavior; the `tasks_shared` re-export decision is reflected in `tasks.py.__all__` + `test_tasks_compat_surface`, and `_resolve_primary_branch_for_recommendation` is either folded (with `bias` param) or scoped out with rationale. A diff review confirms every exempt token (C-001) is byte-identical, and `is_primary_artifact_kind` is untouched. `ruff` + `mypy --strict` + the full suite stay green.

**Acceptance Scenarios**:

1. **Given** the canonical `resolve_primary_branch` + its delegating shim + the recommendation re-implementation, **When** FR-007 lands, **Then** there is one canonical behavior, the compat re-export contract (`tasks.py.__all__` + `test_tasks_compat_surface`) is updated in lockstep, and `_resolve_primary_branch_for_recommendation` is folded-with-bias-param OR explicitly scoped-out with rationale — never left as an unremarked third re-implementation.
2. **Given** the genuinely internal helpers `merge_lane_to_mission` / `merge_mission_to_target` and `_primary_ref_for` (NOT the public `is_primary_artifact_kind`), **When** they are renamed to their canonical-operation names, **Then** no public/serialized surface changes, and ALL callers + tests move in the same change (incl. `orchestrator_api/commands.py`, ~13 merge-helper test importers, the `write_candidate_classification.yaml` arch fixture, and the two `_primary_ref_for` pinning tests).

### User Story 3 — One prose-glossary home (Priority: P3)

A reader looking for the living glossary finds a single home (`docs/context/`) — the stale `glossary/README.md` pointer no longer sends them to a dead `glossary/contexts/` dir, and the legacy `glossary/` prose has been folded into `docs/context/`.

**Why this priority**: Reduces the two-glossary-drift maintenance tax and prevents future contributors from seeding terminology in the retired location. It is prerequisite hygiene for the sense entries in US1 to be discoverable.

**Independent Test**: `glossary/README.md` links resolve to live `docs/context/` pages; the legacy prose files no longer exist at the old path (moved, with redirects/links updated); relative-link and `.github` symlink gates pass.

**Acceptance Scenarios**:

1. **Given** `glossary/README.md`, **When** a reader follows its context links, **Then** every link resolves to a live `docs/context/*.md` page (no dead `glossary/contexts/` targets).
2. **Given** the legacy `glossary/` prose (`historical-terms.md`, `naming-decision-tool-vs-agent.md`, `README.md`), **When** the fold lands, **Then** their content lives under `docs/context/` and inbound references are updated; the docs anti-sprawl ratchet and relative-link gate stay green.

### Edge Cases

- **An occurrence is genuinely ambiguous** (a bare "primary"/"merge" that could be two senses): resolved by explicit human classification in the plan's `occurrence_map.yaml` — never blanket find-replace. Unresolved → left as-is and flagged, not guessed.
- **A shipped identifier contains the substring "primary"/"merge"** (`is_primary_artifact_kind`, `Surface.PRIMARY="primary"`, `primary_branch`/`current_is_primary` template vars, `MergeState` keys, `MergeStrategy` literals, `resolve_merge_target_branch`, the `merge` command): exempt — surrounding prose/docstrings may be clarified, but the token survives byte-identical.
- **An UNRELATED "primary"** (`primaryColor`/`primaryTextColor` mermaid theming; `primary_language`; `primary_adapter_*`; `primary_focus` agent-profile field; `primary_agent`; charter-synthesizer `primary_target`): out of scope entirely — must not be touched.
- **A Sense-C "primary checkout" code symbol** (`primary_feature_dir_for_mission`, `primary_dir`, `primary_anchor`, `_canonicalize_primary_read_handle`): prose around it may say "repository root checkout", but the **symbol is NOT renamed in this mission** (Track 2).
- **A docs section is added or moved** during the prose fold: any new section carries an `index.md` (anti-sprawl ratchet), every added page satisfies the description-length gate (≤180 chars) and passes the terminology guard; moved pages fix `../` relative links and re-`git add -f` any `.github` symlinks.
- **A user-facing string literal whose text is ambiguous but whose value is asserted in a test**: clarify the text AND update the pinning assertion in the same change; if the string is a stable contract, treat it as exempt (do not silently red-fail a string-equality test).
- **A single docstring/sentence mixes two senses** (e.g. the ADR paragraph carrying "primary partition" + "primary branch" + "primary target"): classify as `clarify-prose` with a **sentence-level rewrite note** — this is a rewrite, not a one-token substitution, so `occurrence_map.yaml`'s per-occurrence model must carry the rewrite intent.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Seed the 4 `primary` sense entries | US1 | As a reader, I want a distinct glossary entry for each `primary` sense (A/B/C/D) in `docs/context/{orchestration,execution}.md` with its canonical term and `Do NOT use when` guidance, so the word is unambiguous. | High | Open |
| FR-002 | Seed the 3 `merge` operation entries | US1 | As a reader, I want a distinct glossary entry for each `merge` operation (consolidate / integrate / publish) so I know which one a passage means. | High | Open |
| FR-003 | Prose / `--help` / docstring disambiguation sweep | US1 | As a reader, I want the conflating surfaces reworded to name the specific sense: `spec-kitty merge --help`, the accept→merge help in `cli/commands/agent/mission_accept_merge.py` (`--target`/`--push`/`--keep-branch`), `lanes/merge.py` + `merge.py` docstrings, merge-step doctrine prompts, the conflating ADR paragraph. `CLAUDE.md`'s 3 defensive warnings are **condensed to one glossary cross-reference that STILL names the partition-vs-branch footgun** (not silently removed — see FR-011). | High | Open |
| FR-004 | Keep "Primary Branch" canonical (D1) | US1 | As a maintainer, I want Sense B to remain "Primary Branch" (the existing glossary term), with the issue's "default branch" proposal explicitly rejected and the `primary_branch`/`current_is_primary` wire keys unchanged. | High | Open |
| FR-005 | Fix the stale `glossary/README.md` pointer | US3 | As a reader, I want `glossary/README.md` to point at the live `docs/context/` home instead of the dead `glossary/contexts/` dir. | Medium | Open |
| FR-006 | Fold legacy `glossary/` prose into `docs/context/` | US3 | As a maintainer, I want the legacy `glossary/` prose consolidated under `docs/context/` so there is one prose-glossary home, with inbound references updated (note downstream consumers of the `glossary/` surface: #1341 event-log SoT, #648 static-site gen). | Medium | Open |
| FR-007 | Consolidate the `resolve_primary_branch` re-export + the recommendation duplicate | US2 | As a maintainer, I want the canonical `resolve_primary_branch` (`core/git_ops.py:270`) to be the single source: (a) `cli/commands/agent/tasks_shared.py:56` is already a **delegating shim** re-exported as a compat symbol (`tasks.py.__all__` + `test_tasks_compat_surface`) — decide keep-vs-remove and update the compat guard in lockstep; (b) `_resolve_primary_branch_for_recommendation` (`mission_branch_context.py:197`) **re-implements** the origin/HEAD cascade with a deliberate no-feature-bias divergence — either fold it into the canonical via a `bias` param, or scope it out with explicit rationale (do NOT claim split-brain closed while it stands). | High | Open |
| FR-008 | Rename genuinely module-internal merge/Sense-D helpers | US2 | As a maintainer, I want ONLY genuinely internal helpers renamed to canonical-operation names: `merge_lane_to_mission` / `merge_mission_to_target` (`lanes/merge.py`) — updating their ~13 test importers, the `orchestrator_api/commands.py` callers, and the arch fixture `surface_resolution_audit/write_candidate_classification.yaml` in the same change; `_primary_ref_for` (`implement_cores.py`, cross-module — updating `implement.py` + `test_precondition_ref_unification.py` + `test_partition_authority_characterization.py`); optionally `_resolve_primary_target_branch` (`commit_router.py:553`, Sense-B/D internal). **`is_primary_artifact_kind` is EXCLUDED** (public `__all__` symbol → exempt, C-001). No shipped/public surface touched. | Medium | Open |
| FR-009 | Classify every occurrence before editing | (all) | As a maintainer, I want every in-scope occurrence classified (rename / clarify-prose / exempt-identifier / do-not-touch-unrelated / defer-to-Track-2) in `occurrence_map.yaml` before any edit, so ambiguous and Sense-C cases are decided by a human. | High | Open |
| FR-010 | Pass the terminology + freshness + docs gates | (all) | As a maintainer, I want the touched prose/docs to pass the docs anti-sprawl ratchet (`--strict`), description-length gate, relative-link gate, and `test_no_legacy_terminology.py` with zero new suppressions — where "pass terminology guard" means only "introduces no `ceremony`/`status-writing` regression" (see FR-011 for what it does NOT cover), and the guard is proven to actually execute over the new entries (#2701 skip risk). | Medium | Open |
| FR-011 | Disclose the enforcement model + defer the alias-ban guard | US1 | As a maintainer, I want the spec to state honestly that Track 1 ships **no automated primary/merge sense-guard** — sense-correctness is review-enforced against `occurrence_map.yaml`. A durable alias-ban guard (extending `test_no_legacy_terminology.py` to the retired-alias phrases) is deferred to Track 2 because the Sense-C alias phrases (`"primary checkout"`, `"primary surface"`) legitimately persist until the code rename; non-Sense-C aliases (`"primary target"`, `"primary ref"`) MAY be banned now (optional). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Shipped-identifier invariance | 100% of exempt tokens (C-001 list) are byte-identical before/after — verified by grep + diff review showing edits only to surrounding prose/comments, never the token. | Reliability | High | Open |
| NFR-002 | Behavior invariance | Zero runtime behavior change: the full test suite, `ruff`, and `mypy --strict` exit 0 on the mission diff. The `resolve_primary_branch` consolidation keeps the canonical `core/git_ops` behavior unchanged — proven by the existing `test_git_ops` suite green + the `test_tasks_compat_surface` guard updated in lockstep (no new cross-repo-shape harness needed; `core/git_ops` is already the sole behavior). If `_resolve_primary_branch_for_recommendation` is folded, its no-feature-bias behavior is preserved via the `bias` param and pinned by `mission_branch_context` tests. | Reliability | High | Open |
| NFR-003 | Gate cleanliness (honest scope) | The docs anti-sprawl ratchet (`--strict`), docs-freshness/description-length, relative-link gate, and `test_no_legacy_terminology.py` all exit 0 with zero new suppressions. Explicit caveat: a green `test_no_legacy_terminology.py` means ONLY "no `ceremony`/`status-writing` regression" — it does NOT verify primary/merge sense-correctness (FR-011). The run must prove the guard actually executes over the new entries (guard-skip risk, #2701). | Maintainability | High | Open |
| NFR-004 | Occurrence-map coverage | `occurrence_map.yaml` assigns an explicit action to all 8 standard categories (code_symbols, import_paths, filesystem_paths, serialized_keys, cli_commands, user_facing_strings, tests_fixtures, logs_telemetry); no category left unclassified. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not rename shipped/serialized identifiers | Byte-exact exempt: `Surface.PRIMARY="primary"` + `MissionArtifactKind`(incl. `PRIMARY_METADATA="primary_metadata"`); `primary_branch`/`PRIMARY_BRANCH`/`current_is_primary` template vars; **`merge_target_branch`** (serialized WP-frontmatter/meta key, pinned by `audit/shape_registry.py` — distinct from the `resolve_merge_target_branch` function); the `merge` command name; `merge/` package + `MergeState` + its 13 serialized keys + `merge-state.json`/`state.json`; `MergeStrategy` literals `"merge"/"squash"/"rebase"`; `resolve_merge_target_branch`; other serialized "merge" keys `merged_into` / `merge_phase` / `MERGE_BOOKKEEPING="merge_bookkeeping"` / `merge_postcondition`; and **`is_primary_artifact_kind`** — DEFINITIVELY EXEMPT (public `mission_runtime.__all__` symbol, pinned by `test_mission_runtime_surface` + `test_shared_package_boundary`, 24 callers/7 packages). | Technical | High | Open |
| C-002 | Sense-C code rename is OUT (Track 2) | The `primary_feature_dir_for_mission` / `primary_dir` / `primary_anchor` / `_canonicalize_primary_read_handle` cluster is NOT renamed here; only prose around it is clarified. **Its serialized Sense-C tokens are also byte-exact / Track-2**: `primary_repo_root` (accept-gate JSON key), `primary_candidate` (orchestrator-api error `data`), `WorktreeTopology.PRIMARY="primary"` (StrEnum, distinct from `Surface.PRIMARY`), `PRIMARY_CHECKOUT`/`PRIMARY_CHECKOUT_APPEND` StrEnum op-kinds. Separate isolated bulk-edit mission (WP00 + two literal-string arch gates make it high-risk). | Technical | High | Open |
| C-003 | `src/glossary/` removal is OUT (#2727) | The runtime glossary package retirement (6,379 LOC, 7 wired consumers) is bounded-context #2 under epic #1629, blocked-by #1418 — not this mission. | Business | High | Open |
| C-004 | Do not touch UNRELATED "primary" or "merge" | UNRELATED "primary" (different domains, survive untouched): mermaid `primaryColor*`, `primary_language`, `primary_adapter_*`, `primary_focus` (agent-profile schema), `primary_agent`, charter-synthesizer `primary_target`. UNRELATED "merge" (NOT git operations — data/layer composition, survive untouched): DRG doctrine-layer merges `merge_layers` / `merge_three_layers` / `merge_topology_artifact`; git plumbing `merge_base*`; generic dict/set merges. | Technical | High | Open |
| C-005 | Bulk-edit discipline | `change_mode: bulk_edit`; `occurrence_map.yaml` is a required planning artifact and `implement` refuses the first WP without it (DIRECTIVE_035). Ambiguous occurrences → explicit human classification, never blanket replace. | Technical | High | Open |
| C-006 | Sequence around in-flight `mission-step-authority` | The in-flight mission `mission-step-authority-01KXNZMT` edits `docs/context/orchestration.md` AND restructures `src/doctrine/missions/mission-steps/` — the exact surfaces FR-001/002/003 mutate. Land order must be coordinated (prefer landing `mission-step-authority` first, then rebase; or make the sense-entry additions append-only blocks) to avoid a hot-file merge conflict. | Technical | High | Open |

### Key Entities

- **Primary — Sense A/B/C/D**: the four meanings and their canonical terms (PRIMARY partition / Primary Branch / repository root checkout / target ref). Vocabulary entities; only Sense-A/B/D internal *code* may be safely renamed here, Sense-C prose-only.
- **Merge — Sense 1/2/3**: lane consolidation / branch integration / publish to origin/main. Internal helpers (`merge_lane_to_mission`, `merge_mission_to_target`) are renamable; command/enum/state contracts are exempt.
- **Glossary context files** (`docs/context/orchestration.md`, `execution.md`): the canonical prose-glossary home the sense entries land in.
- **`resolve_primary_branch` (consolidation target)**: one canonical def (`core/git_ops.py:270`); `tasks_shared.py:56` is a delegating shim re-exported as a compat symbol; `_resolve_primary_branch_for_recommendation` (`mission_branch_context.py:197`) is the real partial re-implementation to fold-or-scope-out. Name unchanged (D1).
- **`occurrence_map.yaml`**: the single authority for what changes vs stays vs defers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the 4 `primary` senses and 3 `merge` operations has exactly one canonical glossary entry in `docs/context/`; every in-scope occurrence in `occurrence_map.yaml` carries an explicit action + human classification, and reviewer sign-off confirms no touched passage is left ambiguous (verification is review-against-the-map, not an automated count — see FR-011). Measurable proxy: residual retired-alias phrases in the *touched* files equal the classified-as-intentional set (grep-checkable).
- **SC-002**: **0** exempt shipped/serialized identifiers changed (C-001 list) — confirmed by grep + diff review.
- **SC-003**: `core/git_ops.resolve_primary_branch` is the single canonical behavior; the `tasks_shared` compat re-export decision is reflected in `tasks.py.__all__` + `test_tasks_compat_surface` (green), and `_resolve_primary_branch_for_recommendation` is folded (with `bias` param) or scoped-out with recorded rationale — no unremarked third re-implementation remains.
- **SC-004**: `glossary/README.md` has **0** dead `glossary/contexts/` links; legacy `glossary/` prose lives under `docs/context/`; one prose-glossary home.
- **SC-005**: All gates green on the mission diff — terminology guard, anti-sprawl ratchet (`--strict`), docs-freshness/description-length, relative-link, `ruff`, `mypy --strict` — with **0** new suppressions.
- **SC-006**: The mission artifacts contain an explicit, decision-cited record that Sense-C code rename → Track 2 and `src/glossary/` removal → #2727, so a later reader sees the boundary in one place.

## Traceability

Mission tracking issue: **#2729** (Track 1, sub-issue of **#2653**; sibling **#2730** = Track 2, blocked-by #2729). This spec was hardened by a post-spec adversarial squad (paula-patterns / reviewer-renata / architect-alphonso, 2026-07-16) — findings folded into FR-007/008/011, NFR-002/003, C-001/002/004/006, SC-001/003, and the edge cases.

| Requirement | Source |
|-------------|--------|
| FR-001, FR-002, FR-003 | Issue #2653 (glossary + prose/help sweep); research §2/§3 census; squad (alphonso F4: accept→merge help) |
| FR-004 | Operator decision D1 (keep "Primary Branch"); `docs/context/orchestration.md` existing entry |
| FR-005, FR-006 | Research §1 (stale `glossary/README.md` pointer; charter FR-009 `docs/context/` home); downstream #1341 / #648 |
| FR-007 | Issue #2653 "fold the duplicate `resolve_primary_branch` defs"; squad (paula MAJOR-3 delegating-shim; alphonso F3 recommendation re-impl) |
| FR-008 | Operator directive (code artefacts too) + research §3; squad (paula BLOCKER-2 / renata MAJOR-3 / alphonso F2: `is_primary_artifact_kind` public → excluded) |
| FR-009, NFR-004, C-005 | DIRECTIVE_035 bulk-edit; `spec-kitty-bulk-edit-classification` |
| FR-010, FR-011, NFR-003 | anti-sprawl ratchet; docs-freshness; relative-link gate; squad (renata MAJOR-1 guard honesty); guard-skip risk #2701 |
| C-001, NFR-001 | Research §2/§3 exempt-contract lists; squad (paula BLOCKER-1 `merge_target_branch`; MINOR-7 serialized merge keys) |
| C-002 | Operator decision D2 (Track 2); ADR `2026-06-24-2` (WP00); squad (paula MAJOR-5 Sense-C serialized tokens) |
| C-003 | Issue #2727 (blocked-by #1418, epic #1629) |
| C-004 | Research §2 UNRELATED-symbols list; squad (paula MAJOR-6 unrelated-merge cluster) |
| C-006 | Squad (alphonso F1: in-flight `mission-step-authority-01KXNZMT` collision on `orchestration.md` + `mission-steps/`) |
