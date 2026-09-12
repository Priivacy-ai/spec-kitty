# Mission Specification: Self-documenting repo — migrate agent-memory gap-fillers into the repo

**Mission Branch**: `kitty/mission-self-doc-gapclose`
**Created**: 2026-08-15
**Status**: Draft (post-spec squad folded)
**Input**: Make Spec Kitty run well in a **bare system** — an agent given only the repo contents plus freshly-installed skills/packs. A large fraction of maintainer agent-memory is shadow-documentation for things the repo should tell you itself (gate remedies, template source, recovery procedures, workflow commands). Migrate those gap-fillers into the repo (gate assertions, CLAUDE.md, the existing operations recovery home, docs) so the private notes become deletable. Full audit + owner mapping: `work/memory-gap-filler-analysis.md`; tracking checklist: #3448.

**Verified premises (post-spec squad):** `src/doctrine/missions/mission-steps/` no longer exists; the real prompt source is `packs/built-in/missions/mission-steps/` (G2 correctly diagnosed). `docs/operations/recovery-index.md` already exists as the "Recovery guides" home (so recovery content reuses it — see C-001). `DivioType` is a closed enum (`tutorial|how-to|reference|explanation|none`) — a runbook is **not** a new kind (see C-002). Several G3 recovery classes already have a shipped `spec-kitty doctor … --fix` path (see FR-003).

## User Scenarios & Testing *(mandatory)*

The user is a **fresh agent (or new contributor) working the repo with zero private memory** — only the checkout, installed skills, and packs.

### User Story 1 - Fix any architectural/docs gate from its own message (Priority: P1)

An agent trips an architectural or docs gate (new arch test file not in the shard registry, a new `== N` cardinality assertion, a moved doc breaking `../` links, a re-baselined coverage gate). Today the remedy lives only in private notes; the assertion says *what* failed, not *how to fix it*.

**Why this priority**: Largest gap-filler cluster (G1), hit on every landing pass. Closing it removes the single biggest reason an agent needs private memory.

**Independent Test**: For each enumerated G1 gate, trip it in a scratch tree and confirm the assertion text now contains a content-anchored remedy; a test asserts the remedy substring is present. Independent of the runbook/docs work.

**Acceptance Scenarios**:

1. **Given** a new `tests/architectural/*.py` file missing from its registry, **When** the completeness gate fails, **Then** the message names the exact registry symbol **as read from the current gate code** (`tests._shard_registry` / `tests/_arch_shard_map.py` — verify, do not transcribe from memory) and how to append it, content-anchored (never file:line / whole-file allowlist).
2. **Given** the golden-count gate, **When** it trips, **Then** its message already states the `# golden-count: cardinality-is-contract` annotation + re-freeze command — this is the model the other G1 gates are brought up to.
3. **Given** the write-side-rederivation, gate-coverage-two-baselines, docs-move-relative-link, analysis-report-staleness, schema-slot, and mission-gate-artifact gates, **When** each fails, **Then** each carries a content-anchored remedy line **derived from the current gate logic and validated by tripping the gate**.

### User Story 2 - Recover a split-brain coord/lane mission from the operations recovery home (Priority: P1)

An agent hits a coord/lane topology split-brain (lane-alloc add/add on a coord-off-main mission, `--start-branch` coord divergence, stale lane seed, missing `-coord` worktree, cutover-flip-from-worktree, base-strand-after-rebase). Today the recovery steps live only in memory.

**Why this priority**: Load-bearing, hard-to-rediscover recovery (G3); high operator-visible value.

**Independent Test**: Reproduce each split-brain in a scratch mission and follow the published recovery entry to green; confirm each is discoverable from `docs/operations/recovery-index.md` and passes `check_docs_freshness --ci`.

**Acceptance Scenarios**:

1. **Given** a coord mission whose lane allocation add/add-conflicts, **When** the agent consults the operations recovery home, **Then** it finds a step-by-step recovery that **leads with the shipped `spec-kitty doctor <subcommand> --fix`** where one exists (verified: `doctor coordination --fix`, `sparse-checkout --fix`, `workspaces --fix`), falling back to manual steps (with the operator-grant caveat) only for classes with no `--fix` (cutover-flip → write `status_phase='1'`; base-strand → manual reset; `--start-branch` coord reconcile).
2. **Given** `check_docs_freshness --ci`, **When** the new recovery entries land, **Then** errors=0 (frontmatter, description 50–180 chars, `divio_type` one of the closed-enum values (`none`, matching existing operations runbooks), inventory + retrieval-index registration).
3. **Given** the docs information architecture, **When** a reader looks for operational recovery, **Then** the content lives under the existing `docs/operations/` recovery home (registered in `recovery-index.md`) — not a third recovery location.

### User Story 3 - Find the correct template source and regenerate (Priority: P2)

An agent edits a mission-step prompt and must regenerate the agent command copies + skill snapshots.

**Why this priority**: CLAUDE.md is actively wrong about the source location (G2); the regen command is undiscoverable (G4). Narrower than gates/recovery, and the regen automation is owned by #3447.

**Independent Test**: A fresh agent, from CLAUDE.md alone, locates the correct source (`packs/built-in/missions/mission-steps/…`) and the regen pointer.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md's "Template Source Location" table **and** its "Use Canonical Sources" section, **When** an agent reads either, **Then** both point to `packs/built-in/missions/…` (every `src/doctrine/missions/…` reference swept).
2. **Given** a source-prompt edit, **When** the agent looks for how to regenerate, **Then** the docs point to the regen entrypoint owned by #3447 (reference only — this mission does not re-implement it).

### Edge Cases

- A gate remedy must never encode a line number or whole-file allowlist (DIRECTIVE_041 / #2077) — content-descriptor based only.
- A recovery entry must not imply a `doctor --fix` that doesn't exist; explicitly split "run the shipped command" from "manual steps".
- Remedy text transcribed from private memory can name a stale symbol (the memory note and the current gate can disagree) — remedies are derived from the current code and validated by tripping the gate. This is the mission's own failure mode; do not reproduce it.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Gate remedies in assertions | As a bare-system agent, I want each enumerated architectural/docs gate to print how to satisfy it (content-anchored, derived from current gate logic), so I can fix it without private notes. | High | Open |
| FR-002 | Sweep CLAUDE.md template source | As an agent editing prompts, I want EVERY `src/doctrine/missions/…` reference in CLAUDE.md (the source table, the flow diagram, and the "Use Canonical Sources" section) corrected to `packs/built-in/missions/…`. | High | Open |
| FR-003 | Coord/lane recovery in the operations home | As an operator, I want published recovery entries for the six split-brain classes in `docs/operations/`, each leading with the shipped `doctor … --fix` where one exists and manual steps otherwise. | High | Open |
| FR-004 | Reuse the existing recovery IA | As a docs reader, I want recovery content registered in `docs/operations/recovery-index.md`, not a new third recovery location. | High | Open |
| FR-005 | Discoverable workflow commands (repo-owned) | As an agent, I want the docs-inventory-freshen (`scripts/docs/inventory_lockfile.py`) and mission-wrap-up (DIRECTIVE_046) commands discoverable; the regen entrypoint is a pointer to #3447 only. | Medium | Open |
| FR-006 | File the behavior-quirk bugs | As a maintainer, I want the finalize-clobbers-matrix / review-cycle-double-increment / status-daemon-stale-commit quirks FILED (issue refs recorded in the migration manifest). Fixing is deferred to those issues — NOT an acceptance obligation of this mission. | Medium | Open |
| FR-007 | Env + tracker conventions in docs | As a new contributor, I want pyenv/pre-commit-hook gotchas and the retired-`bug`-label / tension-edge conventions in the dev-setup / contributing docs. | Low | Open |
| FR-008 | Migration mapping manifest | As the memory owner, I want a committed manifest that maps each G1–G6 gap-filler to the repo file/assertion that now covers it (or the issue that tracks it) — the repo-testable proof of migration. Private-memory deletion is an operator checklist on #3448, not a repo deliverable. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Docs stay fresh | Every doc/recovery entry added or edited keeps `check_docs_freshness --ci` at errors=0 (frontmatter, description 50–180 chars, `divio_type` in the closed enum, inventory + retrieval-index registration). | Reliability | High | Open |
| NFR-002 | No new merge-blocking red | No change lands a new merge-blocking gate red; honor red-main-is-honest (ADR 2026-07-17-1). | Reliability | High | Open |
| NFR-003 | Content-anchored, not positional | Gate remedy text anchors on content descriptors, never file:line or whole-file allowlists (DIRECTIVE_041). | Maintainability | High | Open |
| NFR-004 | Terminology canon | All new prose passes `test_no_legacy_terminology.py`. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Reuse the operations recovery home | Recovery content extends the existing `docs/operations/` home (registered in `recovery-index.md`) — NOT a new top-level `docs/runbooks/`, and NOT under `docs/development/guides`. (Operator's "don't overload development guides" is already met: operations/ is not under development/.) | Technical | High | Open |
| C-002 | `divio_type` is a closed enum | A recovery entry is NOT a new Divio kind. It classifies as `type: none` (or omit `type`, matching existing operations runbooks — the inventory reads the `type` key) (matching existing operations runbooks) — do NOT add an enum member or change `_inventory.py`. | Technical | High | Open |
| C-003 | Do not duplicate #3447 | The regen automation entrypoint is owned by #3447; reference it, don't re-implement. | Technical | Medium | Open |
| C-004 | Migration is repo-testable | Proof of migration is the committed manifest (FR-008) + filed issues; deleting private memory is out-of-repo operator hygiene. | Process | Medium | Open |
| C-005 | Remedies derived, not transcribed | G1 remedy text is derived from the current gate logic and validated by tripping the gate — never transcribed from a private note (which may name a stale symbol). | Technical | High | Open |

### Key Entities

- **Gate remedy** — the human-facing "how to satisfy me" text on an architectural/docs gate assertion.
- **Recovery entry** — an operational recovery doc under `docs/operations/` (`type: none` (or omit `type`, matching existing operations runbooks — the inventory reads the `type` key)), registered in `recovery-index.md`.
- **Migration manifest** — a committed file mapping each G1–G6 gap-filler to its repo home / tracking issue (`work/memory-gap-filler-analysis.md` is the source audit; the manifest is the in-repo, testable derivative).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (machine)** A test over the enumerated G1 gate set asserts each gate's assertion contains a content-anchored remedy substring matching a registered pattern. **(manual acceptance note)** A fresh agent can fix each gate using only its message.
- **SC-002** All six coord/lane split-brain classes have a recovery entry in `docs/operations/` (registered in `recovery-index.md`), each leading with the shipped `doctor … --fix` where one exists; `check_docs_freshness --ci` errors=0.
- **SC-003** Every `src/doctrine/missions/…` reference in CLAUDE.md is corrected to `packs/built-in/missions/…`; a fresh agent locates source + regen pointer from CLAUDE.md alone.
- **SC-004** The three behavior quirks (G5) are filed with issue refs recorded in the manifest; fixes are tracked, NOT required for this mission. Env/tracker conventions (G6) are in the dev-setup / contributing docs.
- **SC-005** The migration manifest (FR-008) is complete: every G1–G6 gap-filler maps to a repo home or a tracking issue. (Private-memory deletion is checklisted on #3448 — out of mission scope.)
