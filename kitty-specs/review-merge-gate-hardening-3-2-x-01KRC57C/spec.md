# Review/Merge Gate Hardening (3.2.x)

**Mission ID**: `01KRC57CNW5JCVBRV8RAQ2ARXZ`
**Parent Epic**: [Priivacy-ai/spec-kitty#822](https://github.com/Priivacy-ai/spec-kitty/issues/822) — 3.2.0 stabilization and release readiness
**Sibling Epic**: [Priivacy-ai/spec-kitty#992](https://github.com/Priivacy-ai/spec-kitty/issues/992) — drain the bug queue by repairing domain boundaries
**ADR**: [2026-05-11-1](../../architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md) — WP07 deferral rationale
**Planning draft**: originally at `kitty-specs/_drafts/3.2.x-review-merge-gate-hardening.md` — removed after the canonical mission absorbed its content; superseded by this spec.

## Problem Statement

The 3.2.0-rc line is nearly stable: epic #822's original blocker tranche (#967, #966, #964, #968, #904, #848) has landed, but a residual cluster of P1 bugs remains, all of which target the **release-gate apparatus itself**:

- The mission-review command can pass with a one-line report and no issue matrix (#985).
- Gate command patterns can fall through to globally installed `pytest` and import the wrong package versions (#987).
- Parallel contract + architectural gate runs race on a shared pytest-venv fixture (#986).
- `spec-kitty merge` is not idempotent after a partial mission-number commit (#983).
- `spec-kitty agent tasks status` resolves to the wrong checkout from a detached worktree (#984).

Separately, the encoding chokepoint work in #644 has been waiting for a "narrowable to one lifecycle chokepoint" condition that epic #822 explicitly imposed. That narrowing is now possible.

The unifying invariant: **a 3.2.x stable release cannot ship if the release-gate apparatus itself can silently pass on missing evidence, race on shared fixture state, fall through to global tooling, or read stale state from the wrong checkout.**

## Motivation

- **Release confidence.** Every bug above can produce a *false pass* on the release-gate apparatus. False passes are worse than false fails because they ship.
- **Bisection isolation.** Each fix is a narrow surface with a clear regression fixture. Bundled into one mission, they share a single review/merge cycle while keeping per-WP diff scope tight.
- **Epic #822 closure.** With this mission and the in-flight PR set (#806, #1027, #1028) landed, the 3.2.x stable gate has no further P1 blockers.
- **Single-chokepoint hygiene** (#644). Epic #822's anti-scope demands a narrowed encoding fix; this mission delivers exactly that, deferring the broader audit.

## Scope

### In Scope

1. **Hermetic mission-review gate invocation** (#987). Mission-review gate commands fail fast when `pytest` is not in the project `.venv`, or invoke `python -m pytest` so PATH fallthrough cannot occur. Documentation updated accordingly.
2. **Concurrency-safe pytest-venv fixture** (#986). Fixture creation is either file-locked, per-worker, or pre-created before parallel shards run.
3. **Mission-review report contract enforcement** (#985). `spec-kitty review` distinguishes lightweight consistency mode from post-merge mission-review mode. Post-merge mode requires `issue-matrix.md`, Gate 1–4 records, and `mission-exception.md` (when applicable) — failing loudly when absent. The `issue-matrix.md` validator contract is derived from an audit of all 6 existing real-world matrices on `main` (see §"Existing-mission audit findings (2026-05-12)") and uses a closed-set vocabulary: 3 mandatory canonical columns, 7 named-optional columns, all other columns hard-fail. Existing matrices that drift from the canonical contract are remediated as part of this WP — not as an unsupervised migration but with operator-visible diagnostic + per-mission repair guidance.
4. **Idempotent mission-number assignment** (#983). The mission-number assignment step is short-circuited when `meta.json.mission_number` already equals the computed value; merge-state records `mission_number_baked: true` so resume skips it.
5. **Worktree-aware status read resolution** (#984). Read-only status commands prefer the current worktree's artifacts over `get_main_repo_root()` switching; intentional non-support paths fail loudly.
6. **Single encoding chokepoint + provenance** (#644, narrowed). One ingestion chokepoint at charter-content boundary detects source encoding, records provenance, normalizes to UTF-8, and fails loudly on mixed/ambiguous content (with `--unsafe` bypass). One regression fixture (`cp1252`-encoded charter input). Per-mission and (for non-mission-scoped content) centralized provenance log under a shared schema.
7. **`review.py` hygiene refactor** (prerequisite to WP03; introduced 2026-05-12 per HiC's WP03 Q3 resolution). Mechanical file/method split of `src/specify_cli/cli/commands/review.py` into a package + sibling files to reduce god-class risk before WP03's contract enforcement lands on top of it. **Not** a domain extraction.
8. **Charter-content encoding migration flow** (follow-on to WP06; introduced 2026-05-12 per HiC's WP06 Q2 resolution). A migration class/flow scans existing missions' charter content for non-UTF-8 encodings and either auto-normalizes (with provenance) or fails with the same diagnostic so an operator can repair the artifact before the WP06 chokepoint goes live in operator workflows. Prevents apparent regressions on legacy files.
9. **Cross-cutting documentation surface** (introduced 2026-05-12 per HiC's diagnostic-code-discoverability directive). Each subsystem that emits diagnostic codes publishes a sibling `ERROR_CODES.md` documenting every code (name, when it fires, remediation guidance, JSON-stability commitment). The defining `StrEnum` class carries a class-level docstring that names the sibling file path so future operators following the code reach the doc, and future readers of the doc are pointed back to the code. This is the **interim mitigation** for code-to-doc drift while a Javadoc-style code-to-docs compilation flow is envisioned but not yet built (see comment posted on #645).
10. **Glossary obligation** (introduced 2026-05-12 per HiC's glossary directive). Every WP that introduces a new canonical term (e.g., "lightweight mode", "post-merge mode", "encoding chokepoint", "encoding provenance", "unsafe bypass", "mode mismatch") adds the corresponding entry to `.kittify/glossaries/spec_kitty_core.yaml` with `surface`, `definition`, `confidence`, `status: active`. Glossary additions are part of each WP's done criteria, not deferred to a housekeeping pass.

### Out of Scope (Non-Goals)

- **#391 structural extraction** (#612, #613, #614) — deferred per ADR 2026-05-11-1.
- **Broader UTF-8 audit** beyond the single charter-content chokepoint — explicit deferral, follow-up ticket on completion.
- **ReviewCycle aggregate refactor** (#990, #991) — belongs to a successor mission per epic #992 phasing.
- **#971 mypy strict gate baseline** — separate scoped sub-mission once gate semantics are decided.
- **#1009 FR-012 profile-invocation regression** — isolated, smaller surface; separate ticket.
- **#889 sync rejection classification** — already in flight via PR #1028.
- **#988 `next --json` claimability** — already in flight via PR #1027.
- **#662 CI duplication** — already in flight via PR #806.
- **#1010 (#645 API surface)** — product expansion, not stabilization.
- **No CLI command additions; no backwards-compatibility shims that are not issue-backed.**

## Existing-mission audit findings (2026-05-12)

Per HiC directive: *"do not assume 'extension point' too liberally; actually inspect the contents of existing meta-information to detect conceptual drift."*

Architect Alphonso audited all 6 `issue-matrix.md` files on `origin/main`:

| Mission | Header shape | Capitalization | Verdict values | Outliers |
|---------|--------------|----------------|----------------|----------|
| `stability-and-hygiene-hardening-2026-04-01KQ4ARB` (origin doctrine) | `repo \| issue \| theme \| verdict \| wp_id \| evidence_ref` | lower / snake_case | `fixed`, `verified-already-fixed`, `deferred-with-followup` | `repo` column (multi-repo scope) |
| `charter-golden-path-e2e-tranche-1-01KQ806X` | **3 separate tables**, each with different columns (`ID \| Title \| Surface \| …`) | mixed | all `deferred-with-followup` | non-canonical multi-table structure |
| `release-3-2-0a5-tranche-1-01KQ7YXH` | `Issue \| FR \| WP \| Verdict \| evidence_ref` | Mixed Case + snake | `fixed`, `verified-already-fixed` | adds `FR` traceability |
| `release-3-2-0a6-tranche-2-01KQ9MKP` | `Issue \| Title \| WP \| FR(s) \| NFR(s) \| SC \| Verdict \| Verifying tests` | Mixed Case | `fixed` only | richest schema (FR/NFR/SC traceability) |
| `stable-320-p1-release-confidence-01KQTPZC` | `issue \| scope \| verdict \| evidence_ref` | all lower | `fixed`, `verified-already-fixed`, `deferred-with-followup` | minimal canonical |
| `stable-320-release-blocker-cleanup-01KQW4DF` | `Issue \| Scope \| Verdict \| Evidence ref` | Mixed Case | `fixed`, `deferred-with-followup` | minimal canonical, Title Case variant |

**Drift modes observed:**
- **Capitalization**: `Issue`/`issue`, `Evidence ref`/`evidence_ref`, `Verdict`/`verdict` co-exist across missions.
- **Column-name aliases for the same concept**: `Evidence ref` ↔ `evidence_ref`; `Scope` ↔ `theme`.
- **Structural variance**: 5 of 6 missions use a single table; the charter-golden-path mission uses 3 disaggregated tables.
- **Principled extensions** appear in 3 missions: `FR`, `WP`/`wp_id`, `NFR(s)`, `SC` (traceability columns), `Title`, `repo` (multi-repo scope).
- **Ad-hoc extensions**: `Surface`, `Where surfaced in code`, `Theme` (one mission only; appears author-driven).

**Verdict allow-list — no drift observed.** All 6 missions use only `fixed | verified-already-fixed | deferred-with-followup`. This is the canonical allow-list; the WP03 validator can lock it.

**Sharpened WP03 validator contract** (derived from the audit, replacing the prior "additive-tolerant" handwave):

- **Mandatory columns** (must appear in this exact order, case-insensitive but normalized to lowercase): `issue`, `verdict`, `evidence_ref`.
- **Named-optional columns** (allowed, fixed namespace): `title`, `scope`, `wp` (alias: `wp_id`), `fr` (alias: `fr(s)`), `nfr` (alias: `nfr(s)`), `sc`, `repo`. Aliases normalize to the canonical name in the parsed representation.
- **REJECTED**: any column not in `{mandatory ∪ named-optional}`. Hard-fail with `MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT` naming the unknown column.
- **Verdict allow-list**: `{fixed, verified-already-fixed, deferred-with-followup}`. Anything else → `MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN`.
- **Structural constraint**: exactly one matrix table per file. The 3-table charter-golden-path layout is **non-canonical** and the validator rejects it with `MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE`.
- **Body-cell rules**: `evidence_ref` must be non-empty; if `verdict == deferred-with-followup`, `evidence_ref` must contain a follow-up handle (issue link or precise narrower title), reinforcing the verdict-allow-list doctrine established by the `stability-and-hygiene-hardening-2026-04-01KQ4ARB` mission.

**Existing-mission remediation (in-scope for WP03):**

Each of the 6 existing matrices is run through the validator at WP03 implementation time. For each drift mode detected, the WP03 worker either (a) **auto-normalizes** trivial drift (capitalization-only, alias-only) writing a one-line note in the file recording the normalization, or (b) **emits operator-visible diagnostic with repair guidance** for structural drift (charter-golden-path's 3-table layout, ad-hoc unknown columns). No silent rewrites; every change is traceable in the commit and in the mission's repair log.

## Actors

- **Release operator**: runs the post-merge mission-review and trusts its verdict.
- **Mission reviewer (agent or human)**: invokes the gate commands and reads the report.
- **CLI maintainer**: maintains `spec-kitty merge`, `spec-kitty review`, status commands, and the test fixtures.
- **Implementer agent**: works inside detached/parallel worktrees and depends on correct status reads.

## User Scenarios & Testing

### Scenario 1: Hermetic gate invocation in a fresh clone (#987)

**Given** a fresh shallow clone of the repository with only `uv sync` (no `--extra test`) executed,
**When** the operator runs the documented mission-review gate command,
**Then** the command exits non-zero with a diagnostic naming the missing `test` extra — and does **not** silently invoke a system `pytest`.

### Scenario 2: Concurrent contract + architectural gates (#986)

**Given** `tests/contract/` and `tests/architectural/` are launched concurrently,
**When** both suites need the shared pytest-venv fixture,
**Then** neither suite observes a half-created venv, and both complete deterministically with their expected pass count.

### Scenario 3: Post-merge mission-review enforces issue-matrix (#985)

**Given** a finished mission lacking `issue-matrix.md`,
**When** `spec-kitty review --mission <slug>` is invoked in post-merge mode,
**Then** the command exits non-zero with a JSON-stable diagnostic code citing the missing artifact, and the report does **not** record `verdict: pass`.

### Scenario 4: Lightweight review mode is explicit (#985)

**Given** `spec-kitty review` is invoked in lightweight consistency mode,
**When** the command completes,
**Then** stdout/JSON output explicitly states "lightweight consistency check; not a release gate" so reviewers cannot mistake it for a mission-review verdict.

### Scenario 5: Resume merge after partial mission-number commit (#983)

**Given** an earlier `spec-kitty merge` run assigned `mission_number=115` and committed, then failed during final integration,
**When** the operator reruns `spec-kitty merge --resume`,
**Then** the rerun skips the mission-number assignment step (recognizing `mission_number_baked: true`), completes the remaining recovery, and produces no empty mission-number commit.

### Scenario 6: Detached-worktree status read (#984)

**Given** two worktrees of the same repo with divergent `status.events.jsonl` content,
**When** `spec-kitty agent tasks status --json` is invoked from the detached worktree,
**Then** the output reflects the **current worktree's** event log, matching what a direct reducer pass over that worktree's events would produce.

### Scenario 7: Encoding chokepoint catches cp1252 input (#644)

**Given** a charter input file encoded in Windows-1252 with characters that mis-decode under UTF-8,
**When** the charter compile path ingests the file,
**Then** the chokepoint either (a) detects cp1252, records provenance, and normalizes to UTF-8, or (b) fails loudly with a diagnostic naming the file and detected encoding — and never silently emits mis-decoded text downstream.

### Scenario 8: Mode-mismatch diagnostic is actionable (#985 / WP03 / HiC 2026-05-12)

**Given** a pre-merge mission whose `meta.json.baseline_merge_commit` is absent,
**When** the operator runs `spec-kitty review --mission <slug> --mode post-merge`,
**Then** the command exits non-zero with code `MISSION_REVIEW_MODE_MISMATCH`, and the diagnostic body lists three remediation options: run `spec-kitty merge` first, re-run with `--mode lightweight`, or run identity backfill for pre-083 missions.

### Scenario 9: `--unsafe` bypass on ambiguous encoding (#644 / WP06 / HiC 2026-05-12)

**Given** a charter file whose encoding cannot be unambiguously detected (mixed cp1252/UTF-8 bytes),
**When** the operator re-runs the loading path with `--unsafe`,
**Then** the loader uses the higher-confidence decode candidate, succeeds, and records a provenance entry with `bypass_used: true` so the override is auditable.

### Scenario 10: `review.py` refactor preserves behavior (WP07 / HiC 2026-05-12)

**Given** the pre-WP07 test suite for `review_mission()`,
**When** WP07's refactor moves methods to sibling files inside `commands/review/`,
**Then** every pre-existing test passes unchanged (same inputs → same outputs → same exit codes → same persisted artifacts).

### Scenario 11: Charter-content migration on legacy mission (WP08 / HiC 2026-05-12)

**Given** an existing mission directory containing a charter file authored in cp1252 (legacy Windows artifact),
**When** the operator runs the migration command,
**Then** the file is normalized to UTF-8 with a provenance record, the summary report names the file and the detected encoding, and a second run of the migration on the same directory is a no-op (idempotency check).

### Scenario 12: Validator rejects unknown column in existing matrix (audit 2026-05-12)

**Given** the `charter-golden-path-e2e-tranche-1-01KQ806X/issue-matrix.md` file with its non-canonical `Surface` and `Where surfaced in code` columns,
**When** the WP03 remediation pass runs over that file,
**Then** the validator emits `MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT` naming the unknown columns AND `MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE` for the 3-table layout, with repair guidance pointing the operator at the canonical contract documented in `src/specify_cli/cli/commands/review/ERROR_CODES.md`.

### Scenario 13: Validator auto-normalizes trivial capitalization drift (audit 2026-05-12)

**Given** the `stable-320-release-blocker-cleanup-01KQW4DF/issue-matrix.md` file with `Issue | Scope | Verdict | Evidence ref` header (Title Case),
**When** the WP03 remediation pass runs over that file,
**Then** the validator normalizes the header to `issue | scope | verdict | evidence_ref` lowercase, writes a one-line provenance note inside the file (e.g., `<!-- normalized 2026-05-NN: header case folded to lowercase; aliases resolved -->`), and the file passes validation on the next run.

### Scenario 14: ERROR_CODES.md exists and is referenced from Enum (scope #9)

**Given** WP03's `src/specify_cli/cli/commands/review/_diagnostics.py` defining `class MissionReviewDiagnostic(StrEnum)`,
**When** a developer or operator reads the class docstring,
**Then** the docstring contains a reference of the form "See: `src/specify_cli/cli/commands/review/ERROR_CODES.md` for human-readable descriptions and remediation guidance", and the file exists at that path with one section per Enum member.

### Scenario 15: Glossary entry exists for new canonical term (scope #10)

**Given** WP03 introduces the canonical term "post-merge mode" (`spec-kitty review`'s release-gate invocation),
**When** WP03 reaches the `for_review` lane,
**Then** `.kittify/glossaries/spec_kitty_core.yaml` contains a `terms:` entry with `surface: post-merge mode`, a non-empty `definition`, `confidence >= 0.8`, and `status: active`; the same is verified for every other new canonical term the mission introduces.

## Functional Requirements

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-001 | Mission-review gate documentation specifies `uv run python -m pytest …` (or equivalent) — never bare `uv run pytest …` for release gates | #987 | Proposed |
| FR-002 | A preflight or wrapper guarantees `pytest` is invoked from the project `.venv`; PATH fallthrough to system pytest is impossible for gate commands | #987 | Proposed |
| FR-003 | The shared pytest-venv fixture is concurrency-safe via one of: file lock, per-worker cache directory, or preflight creation | #986 | Proposed |
| FR-004 | A regression test runs contract + architectural gates concurrently and asserts both pass deterministically | #986 | Proposed |
| FR-005 | `spec-kitty review` exposes two explicit modes: `lightweight` and `post-merge`; the active mode is recorded in the report and JSON output | #985 | Proposed |
| FR-006 | In post-merge mode, `spec-kitty review` requires `issue-matrix.md` present (or auto-generated from tracked issues); absence → non-zero exit + JSON-stable diagnostic code | #985 | Proposed |
| FR-007 | In post-merge mode, the report records Gate 1–4 with command, exit code, and result for each gate | #985 | Proposed |
| FR-008 | When cross-repo E2E has an environmental xfail, `mission-exception.md` is validated against schema; invalid/missing → non-zero exit | #985 | Proposed |
| FR-009 | Diagnostic codes emitted by review-mode failures are JSON-stable and documented for the cross-surface fixture harness (#992 Phase 0) | #985 | Proposed |
| FR-010 | Mission-number assignment is a no-op when `meta.json.mission_number` already equals the computed value | #983 | Proposed |
| FR-011 | `MergeState` records `mission_number_baked: true` after a successful assignment; `--resume` reads this flag and skips the step | #983 | Proposed |
| FR-012 | A regression test simulates a partial merge that committed `mission_number` then failed; rerun completes without an empty commit | #983 | Proposed |
| FR-013 | Read-only status commands resolve repo-root to the current worktree, not to `get_main_repo_root()`, when invoked from a detached worktree | #984 | Proposed |
| FR-014 | If detached-worktree status reads are intentionally unsupported, the command fails with a diagnostic naming the constraint — never silently reads the wrong checkout | #984 | Proposed |
| FR-015 | A regression fixture exercises two worktrees with divergent `status.events.jsonl`; each worktree's `agent tasks status` reads its own events | #984 | Proposed |
| FR-016 | A single encoding-detection chokepoint exists at the charter-content ingestion boundary; it records detected encoding in provenance metadata | #644 | Proposed |
| FR-017 | The chokepoint normalizes persisted text to UTF-8 only after the source-encoding decision is known | #644 | Proposed |
| FR-018 | Mixed or ambiguous content fails loudly with a diagnostic naming the file and the encodings observed | #644 | Proposed |
| FR-019 | A regression fixture ingests a `cp1252`-encoded charter input and asserts either correct provenance + UTF-8 normalization, or fail-loud diagnostic | #644 | Proposed |
| FR-020 | The encoding chokepoint's fail-loud diagnostic (`CHARTER_ENCODING_AMBIGUOUS`) names the file, the detected candidate encodings + confidences, the affected byte offsets, and concrete remediation steps (UTF-8-aware editor, `iconv`, or `--unsafe` bypass) | #644 / WP06 / HiC 2026-05-12 | Proposed |
| FR-021 | A `--unsafe` bypass flag on the charter-loading code path proceeds past `CHARTER_ENCODING_AMBIGUOUS` using the higher-confidence decode candidate; the bypass writes `bypass_used: true` to provenance | #644 / WP06 / HiC 2026-05-12 | Proposed |
| FR-022 | Encoding-provenance records are persisted under a single schema; per-mission events go to `kitty-specs/<mission>/.encoding-provenance.jsonl`, non-mission-scoped events go to `.kittify/encoding-provenance/global.jsonl`; the same event MUST NOT appear in both files | #644 / WP06 / HiC 2026-05-12 | Proposed |
| FR-023 | The mode-mismatch failure path (`MISSION_REVIEW_MODE_MISMATCH`) emits a diagnostic body that explains *what is going on* and lists *remediation options* (run `spec-kitty merge`, re-run with `--mode lightweight`, or run identity backfill for pre-083 missions) | #985 / WP03 / HiC 2026-05-12 | Proposed |
| FR-024 | `src/specify_cli/cli/commands/review.py` is split into a package (`commands/review/__init__.py` + sibling files per gate/concern); the public `review_mission()` entry point remains importable from the original path so existing callers do not break | WP07 / HiC 2026-05-12 | Proposed |
| FR-025 | The WP07 refactor introduces no new public types, no new abstractions, and no domain modeling beyond moving methods to sibling files; any change beyond mechanical extraction is out of scope and belongs to a #992 WS-5 successor mission | WP07 / HiC 2026-05-12 | Proposed |
| FR-026 | A migration class/flow (`spec-kitty migrate charter-encoding` or equivalent) scans every existing mission's charter content, detects non-UTF-8 encodings, and either auto-normalizes with provenance or fails with `CHARTER_ENCODING_AMBIGUOUS` per file so the operator can repair before WP06's chokepoint goes live | WP08 / HiC 2026-05-12 | Proposed |
| FR-027 | The migration produces a summary report listing all files inspected, the detected encoding per file, the action taken (normalized / failed / already-UTF-8), and overall pass/fail; the report is JSON-stable and suitable for CI consumption | WP08 / HiC 2026-05-12 | Proposed |
| FR-028 | `issue-matrix.md` validator enforces exactly the mandatory + named-optional column set documented in §"Existing-mission audit findings"; unknown columns hard-fail with `MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT` naming the offending column | WP03 / audit 2026-05-12 | Proposed |
| FR-029 | The validator's verdict allow-list is `{fixed, verified-already-fixed, deferred-with-followup}`; any other value hard-fails with `MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN` | WP03 / audit 2026-05-12 | Proposed |
| FR-030 | The validator rejects multi-table `issue-matrix.md` files (more than one Markdown table at the top level) with `MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE` | WP03 / audit 2026-05-12 | Proposed |
| FR-031 | The validator hard-fails when `verdict == deferred-with-followup` and `evidence_ref` does not contain a follow-up handle (issue link or precise narrower title) | WP03 / audit 2026-05-12 | Proposed |
| FR-032 | A WP03 remediation pass over the 6 existing `issue-matrix.md` files on `main` auto-normalizes trivial capitalization/alias drift (writing a one-line provenance note inside the file) and emits operator-visible diagnostic + repair guidance for structural drift (charter-golden-path's 3-table layout; any ad-hoc unknown columns) — no silent rewrites | WP03 / HiC 2026-05-12 | Proposed |
| FR-033 | Each subsystem that emits diagnostic codes publishes a sibling `ERROR_CODES.md` documenting every code (name, when it fires, JSON-stability commitment, remediation guidance); the `StrEnum` class carries a class-level docstring naming the sibling file path | scope #9 / HiC 2026-05-12 | Proposed |
| FR-034 | Every new canonical term introduced by this mission ("lightweight mode", "post-merge mode", "encoding chokepoint", "encoding provenance", "unsafe bypass", "mode mismatch", and any other surface added during implementation) has a corresponding entry in `.kittify/glossaries/spec_kitty_core.yaml` with `surface`, `definition`, `confidence ≥ 0.8`, `status: active` before the relevant WP can move to `done` | scope #10 / HiC 2026-05-12 | Proposed |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-001 | All new diagnostic codes (FR-006, FR-008, FR-009, FR-014, FR-018) are JSON-stable strings that can be asserted from the cross-surface fixture harness referenced in #992 Phase 0. |
| NFR-002 | No FR introduces a global suppression, broad skip, or compatibility fallback unless the suppression is typed, diagnosed, and issue-backed. |
| NFR-003 | The mission's own mission-review (final acceptance) must satisfy FR-005 through FR-008 — eat-our-own-dogfood. |
| NFR-004 | WP06 (encoding chokepoint) does not modify >5 unrelated modules. If implementation reveals broader retrofit is needed, escalate to scope review — do **not** silently broaden scope. **WP08's migration counts against its own budget, not WP06's.** |
| NFR-005 | WP07 produces **no functional change** to `review.py`'s observable behavior. Existing tests against `review_mission()` pass unchanged before and after the refactor (same inputs → same outputs → same exit codes → same report writes). If a behavior change is unavoidable, escalate to scope review. |
| NFR-006 | WP08 is idempotent: re-running the migration on an already-normalized mission directory is a no-op (no new provenance records, no file rewrites). The migration is safe to run automatically in CI before the WP06 chokepoint is invoked. |
| NFR-007 | The validator's vocabulary (mandatory columns, named-optional columns with aliases, verdict allow-list) is encoded once as a typed object in code; the `ERROR_CODES.md` for `review/_diagnostics.py` is derived from or pointer-linked to that object so the doc cannot silently drift from the implementation. Until a code-to-docs compilation flow exists (cf. #645), the cross-reference is hand-maintained but mechanically auditable. |
| NFR-008 | `ERROR_CODES.md` files are produced as part of the WP that introduces the codes — not as a follow-on housekeeping pass. A WP cannot move to `for_review` until its associated `ERROR_CODES.md` exists, the codes it documents match the StrEnum members in code, and the StrEnum class docstring references the file. |

## Dependencies and Sequencing

WPs decompose along the following dependency graph (updated 2026-05-12 after WP07 / WP08 added):

```
WP01 (#987) ──┐
              ├──► WP03 (#985 — contract enforcement on top of refactored review.py)
WP02 (#986) ──┘     ▲
                    │
WP07 (review.py hygiene refactor) ─────┘  prerequisite to WP03

WP04 (#983)   independent
WP05 (#984)   independent

WP06 (#644) ──► WP08 (charter-content encoding migration; runs before WP06 chokepoint
                       is exposed to operator workflows so legacy files don't regress)
```

WP01, WP02, and WP07 are prerequisites for WP03. WP06 is a prerequisite for WP08.
WP04 and WP05 run in parallel lanes.

**Sequencing rationale for WP07 before WP03:** WP03 adds significant new code to `review.py` (mode resolution, schema validators, gate record writers, diagnostic emitters). Landing that on top of the existing flat file produces a god-module *and* large merge conflicts with the refactor. Doing WP07 first means WP03 writes its new code into the already-split package structure.

**Sequencing rationale for WP08 after WP06 but before WP06 reaches operator paths:** WP06 introduces a chokepoint that fails loudly on non-UTF-8 charter content. Existing missions already have files on disk that *might* be in non-UTF-8 encodings (rare, but possible on Windows-authored historical content). If WP06 ships first and an operator opens an older mission, they get a hard fail and call it a regression. WP08's migration step normalizes those files preemptively (or surfaces them for manual repair) so the chokepoint goes live only on conforming content.

## Risks

| Risk | Mitigation |
|------|------------|
| WP06 scope creep into a full encoding audit | NFR-004 hard guardrail; escalation trigger at >5 modules |
| WP03 mode contract disagreement (lightweight vs post-merge) | Architect Alphonso consult before implementation |
| WP04 mission-number lock semantics regression | Reuse the existing merge-state lock from the canonical-identity work (mission #557); explicit lock-held assertion in regression test |
| WP05 worktree edge cases (managed vs external) | Audit fixture covers both, per CLAUDE.md "worktree/main resolution has a contract fixture covering managed and external worktrees" |

## Acceptance for the Mission as a Whole

- All FRs (FR-001 through FR-019) are met and covered by tests.
- NFR-001 through NFR-004 hold.
- Cross-surface fixture (cf. #992 Phase 0): the same fixture mission state passes through `next`, `agent action`, `move-task`, status, dashboard scanner, `review`, `merge --dry-run`, and real merge preflight without divergence on any artifact this mission touches.
- Fresh-clone smoke `init → specify → plan → tasks → implement/review → merge → PR` passes without manual state repair, with and without `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- This mission's own mission-review report satisfies FR-005 through FR-008 (eat-our-own-dogfood per NFR-003).

## Open Questions for Architect Consult

**Status as of 2026-05-12 (afternoon update):** All architectural sub-questions are now resolved. Both ADRs (`2026-05-12-1-wp03-review-mode-contract-PROPOSED.md` and `2026-05-12-2-wp06-charter-encoding-chokepoint-PROPOSED.md`) remain in **Proposed** status pending a final rename pass (drop the `-PROPOSED` suffix, re-status to `Accepted`) once `/spec-kitty.plan` is approved.

| ADR | Sub-question | Resolution status |
|-----|--------------|-------------------|
| WP03 | Q1 — Mode mismatch behavior | **Resolved** (hard-block with remediation guidance) |
| WP03 | Q2 — `issue-matrix.md` validator strictness | **Resolved 2026-05-12 PM** via audit of all 6 existing matrices: strict mandatory columns + closed-set named-optional columns + verdict allow-list + single-table requirement; existing matrices remediated as part of WP03 |
| WP03 | Q3 — Gate source-of-truth | **Resolved** (keep inline, but split `review.py` via WP07) |
| WP06 | Q1 — `charset-normalizer` dependency | **Resolved 2026-05-12 PM**: promote to direct dep `>=3.4,<4`; already in supply chain via `requests` at 3.4.7 (zero net new install surface) |
| WP06 | Q2 — Mixed-content policy | **Resolved** (hard-fail with `--unsafe` bypass + new WP08 migration to cover legacy artifacts) |
| WP06 | Q3 — Provenance file location | **Resolved** (dual storage: per-mission preferred, centralized for non-mission-scoped content) |
| Cross-cutting | Diagnostic-code registry shape | **Resolved 2026-05-12 PM**: per-subsystem `StrEnum` + sibling `ERROR_CODES.md` + class docstring cross-reference (interim mitigation for code-to-doc drift until #645's code-to-docs compilation flow is built) |

`/spec-kitty.plan` is fully unblocked for all 8 WPs (WP01–WP08).
