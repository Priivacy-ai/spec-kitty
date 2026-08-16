# Mission Specification: Mission A — P0 Read/Write Consistency

**Mission Branch**: `fix/mission-a-p0-consistency`
**Created**: 2026-08-13
**Status**: Draft
**Input**: Remediate four accepted, open P0 defects (#3231, #3320, #3334, #3311), each with a committed red-first reproduction under `tests/regression/`, as four independent, surgically-scoped fixes.

## User Scenarios & Testing *(mandatory)*

Each defect is an independent slice: it can be fixed, tested, reviewed, and merged on its own, and each delivers standalone operator value. Priorities encode delivery sequence — the highest-blast-radius fix (#3311) is sequenced last so a contested review cannot hold the other three P0s hostage. All four share a design theme (a read/compute/report step trusting the wrong slice of state) but are implemented with **no shared helper** — the theme guides, it is not codified into one seam.

### User Story 1 - Retrospective reports what it persisted (#3320) (Priority: P1)

An operator runs `spec-kitty retrospect create --update` on a mission that already has a retrospective record carrying a gap. The generator, on an artifact-poor mission, yields a `ran_no_findings` record; the writer merges it with the existing record on disk, preserving the gap. The operator must see reported counts, `findings_status`, and the emitted lifecycle event that match the **persisted merged record** — not the pre-merge generated one.

**Why this priority**: Lowest blast radius (contained to one command; read-back uses an existing reader). Landing it first banks a P0 with minimal review risk.

**Independent Test**: Seed a `has_findings` record with one gap; invoke `create --update` with a stubbed `ran_no_findings` generator and the real merging writer; assert the reported JSON **and** the emitted event payload equal the on-disk record.

**Acceptance Scenarios**:

1. **Given** an on-disk record with `findings_status=has_findings` and one gap, **When** `create --update` runs with a generator yielding `ran_no_findings`, **Then** the reported `findings_status`/gap count equal the persisted (`has_findings`, 1).
2. **Given** the same run, **When** the `RetrospectiveCaptured` event is emitted, **Then** its payload reflects the merged persisted record, not the pre-merge record.
3. **Given** a `--overwrite` or `mode="error"` run (persisted == new), **When** it completes, **Then** reporting is unchanged (read-back is a no-op there).

---

### User Story 2 - A scaffold placeholder cannot poison acceptance (#3231) (Priority: P1)

An operator accepts a mission whose real acceptance criteria all pass, but a leftover `finalize-tasks` empty scaffold placeholder row (`AC-001`, `pending`) survived a squash merge into the acceptance matrix. The aggregate verdict must not be blocked by that contentless placeholder — while a genuinely unauthored matrix must still read as `pending`.

**Why this priority**: A demonstrated false-block on acceptance; but the fix carries a symmetric false-**accept** hazard (below) that must be closed in the same change.

**Independent Test**: Drive the real verdict authority (`AcceptanceMatrix.overall_verdict`) over row sets: real-all-pass + empty placeholder; partial authoring; all-scaffold.

**Acceptance Scenarios**:

1. **Given** a matrix with all real criteria `pass` plus the empty `AC-001` scaffold placeholder, **When** the verdict is computed, **Then** it is not `pending` (acceptance not blocked).
2. **Given** a matrix where 9 of 10 seeded functional-requirement rows are still `pending` (unauthored, marker in `notes`), **When** the verdict is computed, **Then** it is `pending` (a seeded-but-unauthored requirement still blocks).
3. **Given** an all-scaffold matrix (no authored criterion), **When** the verdict is computed, **Then** it is `pending`.

---

### User Story 3 - A failed upgrade leaves a recoverable project (#3334) (Priority: P2)

An operator's `spec-kitty upgrade` fails partway and strips `schema_version` from `.kittify/metadata.yaml`. Every subsequent invocation must leave a forward path: the project must be repairable via the normal upgrade/repair route, and must not be misclassified into an unrecoverable wedge. A **genuinely** pre-3.x project must remain protected from unsafe mutating commands.

**Why this priority**: The committed reproduction pins the wrong contract (it drives the compat decision gate with a fake unsafe command, but `upgrade` is already SAFE/allowed). Resolving it requires tracing the real exit-producer and reframing the fix to the failed-upgrade write path — more discovery than US1/US2.

**Independent Test**: Reproduce a post-failed-upgrade metadata fixture (version behind, `schema_version` absent, `migrations.applied` carrying 3.x history) and drive the real repair route end-to-end; separately assert a genuine pre-3.x fixture stays blocked from unsafe commands.

**Acceptance Scenarios**:

1. **Given** a project whose `schema_version` was stripped by a failed upgrade but whose `migrations.applied` shows 3.x history, **When** the operator re-runs the repair route, **Then** the project recovers (schema stamp restored/re-established) with no unrecoverable exit.
2. **Given** a genuinely pre-3.x project (no `schema_version`, empty/absent `migrations.applied`), **When** an unsafe mutating command is invoked, **Then** it remains blocked.
3. **Given** a project with garbled/half-written `migrations.applied`, **When** classified, **Then** it fails toward the conservative (blocked) classification.

---

### User Story 4 - Re-finalizing after execution preserves provenance (#3311) (Priority: P3)

After implementation has begun, an operator re-runs `finalize-tasks` following an ownership-only `owned_files` amendment. Finalization must not silently clear the established `planning_commit_sha` (or recompute executed lane identities) — it preserves them, or refuses before writing any bytes. A re-finalize **before** any execution has begun must still regenerate freely (idempotent pre-execution re-plan preserved).

**Why this priority**: Highest blast radius — a behavior change touching the provenance-freeze ADR. Sequenced last so its review does not gate US1–US3.

**Independent Test**: Run the real `finalize_tasks` twice — establish lanes + a recorded `planning_commit_sha`, then re-run after an ownership-only amendment with "execution begun" simulated via the status event log; assert provenance preserved (or a pre-write refusal). Separately, re-run with no execution begun and assert free regeneration.

**Acceptance Scenarios**:

1. **Given** a mission whose lanes are materialized and at least one WP has advanced past `planned`, **When** `finalize-tasks` re-runs after an ownership-only amendment, **Then** `planning_commit_sha` is preserved (or the run refuses before writing).
2. **Given** the preservation path, **When** the branch tip differs from the recorded SHA (non-`None`), **Then** the recorded SHA is still preserved (not overwritten with the current tip).
3. **Given** a mission where no WP has left `planned`, **When** `finalize-tasks` re-runs, **Then** lanes regenerate freely and the run does not refuse.

### Edge Cases

- A real acceptance criterion legitimately carrying the scaffold marker in its `description` (must be confirmed impossible, or the discriminator refined) — #3231.
- `migrations.applied` present but hand-forged to spoof 3.x history on a schema-less project — must not unlock unsafe commands (#3334).
- A `finalize-tasks` re-run that adds a **new** WP (vs. amending an existing one) — whether that is a supported re-plan or a refuse case (#3311, open discovery).
- `--update` on a mission with no existing record (merge degenerates to the new record) — reporting must still match disk (#3320).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retrospect `--update` reports the persisted record | As an operator, I want `retrospect create --update` to report counts and `findings_status` from the merged on-disk record so that the summary never contradicts what was saved. | High | Open |
| FR-002 | Retrospect `--update` emits the persisted record | As an operator, I want the `RetrospectiveCaptured` event to carry the merged persisted record so downstream consumers never receive pre-merge data. | High | Open |
| FR-003 | Scaffold placeholder does not block a passing verdict | As an operator, I want a mission whose real criteria all pass to not be blocked by a leftover empty `finalize-tasks` scaffold placeholder row. | High | Open |
| FR-004 | Seeded-but-unauthored requirement still blocks | As an operator, I want a seeded functional-requirement row that is still `pending` (and an all-scaffold matrix) to keep the verdict `pending`, so unauthored requirements are never silently accepted. | High | Open |
| FR-005 | A failed upgrade leaves a recoverable project | As an operator, I want a project whose `schema_version` was stripped by a failed upgrade to remain repairable via the normal route, with no unrecoverable wedge. | High | Open |
| FR-006 | Genuine pre-3.x projects stay protected | As a maintainer, I want a genuinely pre-3.x project (no `schema_version`, no 3.x migration history) to remain blocked from unsafe mutating commands. | High | Open |
| FR-007 | Re-finalize after execution preserves provenance | As an operator, I want a `finalize-tasks` re-run after execution has begun to preserve the established `planning_commit_sha` (or refuse before writing), so an ownership-only amendment never destroys planning provenance. | High | Open |
| FR-008 | Pre-execution re-finalize stays idempotent | As an operator, I want a `finalize-tasks` re-run before any WP execution has begun to regenerate lanes freely without refusing, preserving the documented pre-execution re-plan. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first repros green via product fix only | All four committed `tests/regression/` reproductions (or their reframed replacements) turn green solely from the product fix; none is weakened, skipped, or xfail'd. 100% of the four pass under `-m regression`; suites selected by `not regression` stay unchanged. | Reliability | High | Open |
| NFR-002 | Green-wash guard tests present | Each fix adds focused tests that execute its new branch directly, covering the negative/partial cases the repro omits: partial-authoring + all-scaffold (#3231), non-`None`-tip preservation + benign re-finalize (#3311), genuine-pre-3.x-blocked (#3334), emitted-event-payload (#3320). All named tests present and passing. | Test Coverage | High | Open |
| NFR-003 | Quality gates clean on changed code | Changed code passes `ruff` and `mypy` with zero issues/warnings and cyclomatic complexity ≤ 15; no new blanket suppressions. | Maintainability | High | Open |
| NFR-004 | No collateral regression | Targeted suites for every touched module stay green on the mission branch; no other CI suite is reddened by these changes. | Reliability | High | Open |
| NFR-005 | Regression-exit discipline | After each fix lands, its `tests/regression/` reproduction **leaves the suite**: relocated to the functional-slice test suite matching the module it exercises (or, for #3334, replaced), with `@pytest.mark.regression` removed and the red-first docstring replaced by a canonical guard docstring + canonical marks from `docs/context/testing-taxonomy.md`. **Zero `regression`-marked tests attributable to this mission remain green at mission completion** (a green `regression` test is a mission-incomplete signal, per `tests/regression/README.md` exit rule). | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No shared abstraction (non-goal) | The four fixes introduce no shared helper or shared "read-state" abstraction; each stays local to its module. The design theme guides review, it is not implemented as one seam. | Technical | High | Open |
| C-002 | #3320 preserves the writer return type | `write_gen_record`'s `Path` return type is not changed; the fix reads the persisted record back via the existing `read_gen_record`. Any enrichment is additive (e.g. `(path, record)`), never a replacement. | Technical | High | Open |
| C-003 | #3231 discriminator is the empty placeholder only | Scaffold exemption keys on the contentless empty placeholder (`description == SCAFFOLD_TODO_MARKER`), never on `notes == SCAFFOLD_TODO_MARKER` (which the scaffold builder also stamps on real per-requirement rows). | Technical | High | Open |
| C-004 | #3334 keeps unsafe commands blocked | Any compatibility-classification change keeps unsafe mutating commands blocked on a schema-less install and fails toward the LEGACY/blocked classification on missing or garbled `migrations.applied`; the classifier change (if any) is messaging/diagnosis-only. | Technical | High | Open |
| C-005 | #3311 respects the provenance-freeze ADR and triggers on execution | The fix respects the ADR `2026-07-29-1` single-write provenance-freeze requirement. The preserve/refuse trigger keys on "execution has begun" (status events past `planned` and/or materialized lane worktrees), never on `lanes.json` / `planning_commit_sha` presence. | Technical | High | Open |
| C-006 | #3334 reproduction is replaced, not kept | The committed #3334 reproduction (which drives the compat decision gate via a fake unsafe command) is replaced by a reproduction that pins the real recoverability contract; the mis-targeted assertion is not retained. | Technical | High | Open |
| C-007 | #3311 scoped to the confirmed defect; #3307 out of scope | The #3311 fix is scoped to the confirmed provenance-clobber; no topology-preservation behavior is promised without first reproducing that defect. #3307 belongs to Mission B and is out of scope here. | Business | Medium | Open |
| C-008 | #3334 root fix: `save()` round-trips `schema_version` (in scope) | The durable fix is in scope: `ProjectMetadata` load+save must round-trip `spec_kitty.schema_version` so no `save()` caller strips it (root fix at the strip site, `metadata.py:188-210`), keeping `None` for genuinely pre-3.x projects. This subsumes a separate failure-path restore. The success path still advances the stamp to `REQUIRED_SCHEMA_VERSION`; `dry_run` writes nothing. The second schema writer (`migration/runner.py:193`) must stay consistent. Contributes to Epic #3347. | Technical | High | Open |

### Key Entities

- **Acceptance verdict** (`AcceptanceMatrix.overall_verdict`): the single computed authority over accept/block; must distinguish an empty scaffold placeholder from authored and seeded-but-unauthored criteria.
- **Retrospective record** (`GenRetrospectiveRecord`): the on-disk, merge-authoritative record; the CLI must report and emit from the persisted form.
- **Project compatibility status** (`schema_version` + `migrations.applied` in `.kittify/metadata.yaml`): the state a failed upgrade corrupts; recovery must survive a stripped `schema_version`.
- **Lanes manifest** (`LanesManifest.planning_commit_sha`): frozen planning provenance that a re-finalize must not silently clobber once execution has begun.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 false-blocks — a mission whose real acceptance criteria all pass is never blocked by a leftover empty scaffold placeholder; and 0 false-accepts — an unauthored/seeded-pending matrix is never accepted.
- **SC-002**: 100% of `retrospect create --update` runs report counts, `findings_status`, and an emitted event that match the persisted record.
- **SC-003**: 100% of projects broken by a failed upgrade (schema stripped, 3.x history present) are recoverable via the normal route with no unrecoverable exit; genuine pre-3.x projects remain protected in 100% of cases.
- **SC-004**: A `finalize-tasks` re-run after execution has begun never silently clears established planning provenance; pre-execution re-finalize remains idempotent (regenerates without refusing).
- **SC-005**: All four committed red-first reproductions (or reframed replacements) turn green via product fixes only, with no regression in any other test suite.
- **SC-006**: At mission completion, `pytest tests/ -m regression` shows **zero green tests attributable to this mission** — each of the four has been relocated to its functional-slice suite (or replaced) with the `regression` marker and red-first docstring swapped for canonical marks + a guard docstring.
