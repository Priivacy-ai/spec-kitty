# Specification Quality Checklist: CLI Upgrade Nag and Lazy Project Migration

**Purpose**: Validate the *quality* of `spec.md` — its completeness, clarity, consistency, measurability, and coverage — before `/spec-kitty.plan`. This checklist tests the **requirements writing**, not the future implementation.
**Created**: 2026-04-27
**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN`
**Spec**: [`../spec.md`](../spec.md)
**Audience**: Reviewer / planner (the person about to read the spec into `/spec-kitty.plan`).
**Depth**: Standard. Block planning on any unchecked item in *Requirement Completeness*, *Acceptance Criteria Quality*, or *Non-Functional Requirements*.

---

## Requirement Completeness

- [ ] CHK001 — Are all five FR-023 user-facing case names (`cli_update_available`, `project_migration_needed`, `project_too_new_for_cli`, `project_not_initialized`, `install_method_unknown`) traceable to at least one user scenario? [Completeness, Spec §FR-023, §"User Scenarios & Testing"]
- [ ] CHK002 — Is the full enumeration of "unsafe" commands explicitly listed (not just exemplified) in the Safe/Unsafe Command Classification section? [Completeness, Spec §"Safe / Unsafe Command Classification"]
- [ ] CHK003 — Is the full enumeration of "safe" commands explicitly listed (not just exemplified)? [Completeness, Spec §"Safe / Unsafe Command Classification"]
- [ ] CHK004 — Are requirements defined for the case where `.kittify/metadata.yaml` is missing or unreadable, distinguishing it from "incompatible schema"? [Completeness, Spec §"Edge cases", §"Key Entities → Compatibility plan"]
- [ ] CHK005 — Are requirements defined for the "developer / source install" case in addition to packaged installs (pipx, pip, brew)? [Completeness, Spec §A-008, §"Key Entities → Install-method descriptor"]
- [ ] CHK006 — Are requirements specified for what the nag prints when the latest-version source is unreachable (network error, offline, malformed payload)? [Completeness, Spec §NFR-002, §"Edge cases"]
- [ ] CHK007 — Are requirements defined for invalidating or warming the nag cache when the user installs a different CLI version? [Completeness, Spec §FR-025]
- [ ] CHK008 — Are requirements documented for what configuration surface controls the throttle window (env var name, file path, key)? [Completeness, Spec §NFR-009] [Gap]
- [ ] CHK009 — Are requirements documented for what configuration / environment variable disables the nag (`SPEC_KITTY_NO_NAG`, `--no-nag`)? [Completeness, Spec §A-007] [Gap]
- [ ] CHK010 — Is the JSON output schema for `spec-kitty upgrade --dry-run --json` and `spec-kitty upgrade --json` described at field-name level (not just "structured plan")? [Completeness, Spec §FR-022, §"Key Entities → Compatibility plan"] [Gap]
- [ ] CHK011 — Are documentation deliverables (which docs files must change) named, beyond the single mention of `docs/how-to/install-and-upgrade.md`? [Completeness, Spec §SC-008, §"Dependencies"]
- [ ] CHK012 — Are requirements specified for the exit codes used when the CLI blocks an unsafe command (specific non-zero values, distinguishing "needs migration" from "needs CLI upgrade")? [Completeness] [Gap]

## Requirement Clarity

- [ ] CHK013 — Is "throttled" quantified everywhere it appears with a specific window (the spec says 24h default — is that consistently referenced)? [Clarity, Spec §FR-004, §A-005, §NFR-009]
- [ ] CHK014 — Is "passive" defined operationally (one line, before command output, no prompt) so readers cannot interpret it differently? [Clarity, Spec §"Scenario A", §NFR-007]
- [ ] CHK015 — Is "unsafe state-mutating command" defined by reference to the Safe/Unsafe section, not left to reader judgment? [Clarity, Spec §FR-008, §"Safe / Unsafe Command Classification"]
- [ ] CHK016 — Is "lazy" defined (checked only when inside a Spec Kitty project, only on command invocation, never proactively across projects)? [Clarity, Spec §"Purpose", §"Problem Statement"]
- [ ] CHK017 — Is "non-interactive" defined as an explicit predicate (CI env var OR no-TTY OR explicit opt-out) and not left ambiguous? [Clarity, Spec §A-007, §FR-005]
- [ ] CHK018 — Is "fail open" defined for the network-check path (no stack trace, no nag printed, no non-zero exit attributable to the nag)? [Clarity, Spec §NFR-002] [Ambiguity]
- [ ] CHK019 — Is the difference between `--cli`, `--project`, and the unflagged `spec-kitty upgrade` clear at the level of which behaviors each enables and suppresses? [Clarity, Spec §FR-013, §FR-015, §FR-016]
- [ ] CHK020 — Are "diagnostic mode" vs "repair mode" of `doctor`, and "read-only mode" vs "write/init/sync/repair mode" of `dashboard`, defined in terms a reader can verify from the spec alone? [Clarity, Spec §"Safe / Unsafe Command Classification", §"Edge cases"]
- [ ] CHK021 — Is "concise" in NFR-007 quantified with the stated thresholds (one-line nag, ≤4-line block message)? [Clarity, Spec §NFR-007]

## Requirement Consistency

- [ ] CHK022 — Do FR-017 (`--yes` non-interactive confirmation) and A-006 (`--yes` is a functional alias of `--force`) describe the same semantics without contradiction? [Consistency, Spec §FR-017, §A-006]
- [ ] CHK023 — Are the safe-command lists in §"Safe / Unsafe Command Classification" and §"Scenario G" consistent with each other? [Consistency, Spec §"Safe / Unsafe Command Classification", §"Scenario G"]
- [ ] CHK024 — Do FR-014 (no "not a Spec Kitty project" failure when `upgrade` is run outside a project) and FR-016 (`--cli` restricts to CLI guidance) compose without ambiguity for the no-flag case? [Consistency, Spec §FR-014, §FR-016]
- [ ] CHK025 — Do FR-005 (no network checks in CI) and SC-005 (zero outbound network calls in CI) refer to the same scope (the nag path), and not accidentally to the entire CLI? [Consistency, Spec §FR-005, §SC-005]
- [ ] CHK026 — Do C-008 (single compatibility planner authority) and FR-024 (planner emits the structured plan) line up without leaving a third surface that could decide compatibility independently? [Consistency, Spec §C-008, §FR-024]
- [ ] CHK027 — Are FR-012 (dry-run shows CLI + project + decision + migration plan) and SC-004 (stable JSON across all five scenarios) jointly satisfiable, i.e., does every scenario yield each of those four sections? [Consistency, Spec §FR-012, §SC-004]
- [ ] CHK028 — Do "current project" usages in the spec consistently refer to the project containing the working directory, never to "the most recently used project" or any cached selection? [Consistency, Spec §"Domain Language → Current project", §FR-021]

## Acceptance Criteria Quality

- [ ] CHK029 — Are all eight Success Criteria measurable from outside the implementation (no internal-state assertions)? [Measurability, Spec §"Success Criteria"]
- [ ] CHK030 — Are SC thresholds stated with units everywhere (seconds, milliseconds, count, percent), and consistent with NFR thresholds? [Measurability, Spec §"Success Criteria", §"Non-Functional Requirements"]
- [ ] CHK031 — Is "warm cache" defined with a concrete predicate (cache file exists AND mtime within throttle window AND CLI version key matches)? [Measurability, Spec §SC-002, §SC-003, §SC-006] [Ambiguity]
- [ ] CHK032 — Is "100% of test scenarios" in SC-006 paired with an explicit enumeration of those scenarios (not left to interpretation)? [Measurability, Spec §SC-006]
- [ ] CHK033 — Are AC-001…AC-010 from the source brief each traceable to at least one FR/NFR/SC in the spec (no acceptance criterion is orphaned)? [Traceability, Spec §"User Scenarios & Testing", §"Functional Requirements"]

## Scenario Coverage

- [ ] CHK034 — Are requirements present for the **primary path** (compatible CLI, compatible project, normal command)? [Coverage, Spec §"Scenario A"]
- [ ] CHK035 — Are requirements present for the **alternate path** (compatible CLI, no project at all)? [Coverage, Spec §"Scenario F"]
- [ ] CHK036 — Are requirements present for the **exception path** (incompatible project — both directions)? [Coverage, Spec §"Scenario B", §"Scenario C"]
- [ ] CHK037 — Are requirements present for the **recovery path** after a blocked unsafe command (i.e., the user runs `upgrade`, command becomes runnable)? [Coverage, Spec §"Scenario B"]
- [ ] CHK038 — Are requirements present for the **non-functional path** in CI / non-interactive / no-TTY environments? [Coverage, Spec §"Scenario H", §FR-005, §NFR-004]
- [ ] CHK039 — Is the "nag suppression while still gating unsafe commands" combination (interactive but `--no-nag`, schema mismatch) explicitly addressed? [Coverage, Spec §A-007] [Gap]
- [ ] CHK040 — Are requirements specified for re-entry into the same project shortly after a successful migration (no re-block, no re-prompt within the throttle window)? [Coverage] [Gap]

## Edge Case Coverage

- [ ] CHK041 — Are requirements defined for **corrupt or partial** `.kittify/metadata.yaml` (parse error, missing fields)? [Edge Case, Spec §"Edge cases"]
- [ ] CHK042 — Are requirements defined for the user passing **mutually-exclusive flags** (`--project` + `--cli`)? [Edge Case, Spec §"Edge cases"]
- [ ] CHK043 — Are requirements defined for the user passing **redundant equivalent flags** (`--yes` + `--force` together)? [Edge Case, Spec §"Edge cases", §A-006]
- [ ] CHK044 — Are requirements defined for **clock skew** affecting the throttle window (system clock moved backward, far-future cache mtime)? [Edge Case] [Gap]
- [ ] CHK045 — Are requirements defined for **read-only home directories** where the nag cache cannot be written? [Edge Case] [Gap]
- [ ] CHK046 — Are requirements defined for the case where the **PyPI provider returns an older version** than the installed CLI (no nag, no spurious downgrade hint)? [Edge Case] [Gap]
- [ ] CHK047 — Are requirements defined for the case where the **migration registry is empty** for the current project (no migrations needed even though schema differs at the patch level)? [Edge Case] [Gap]
- [ ] CHK048 — Are requirements defined for invocation **inside a Spec Kitty project that is *also* a git submodule or worktree of another project**, so "current project" remains unambiguous? [Edge Case] [Gap]

## Non-Functional Requirements Quality

- [ ] CHK049 — Is the NFR-001 100 ms threshold attached to a stated measurement protocol (median of N runs, on what kind of machine)? [Measurability, Spec §NFR-001]
- [ ] CHK050 — Is NFR-002's 2 s timeout binding on every network path the nag could take (not only on the success path)? [Measurability, Spec §NFR-002]
- [ ] CHK051 — Is NFR-003 ("no normal command writes project files") testable via a single observable predicate (e.g., file-system writes under `.kittify/` and `kitty-specs/`)? [Measurability, Spec §NFR-003]
- [ ] CHK052 — Is NFR-005's "testable without network" expressed as an architectural constraint (provider abstraction) rather than a wish? [Clarity, Spec §NFR-005, §A-002]
- [ ] CHK053 — Is NFR-006's "preserve existing project upgrade behavior" backed by a named test set that must continue to pass? [Traceability, Spec §NFR-006, §"Verification Expectations"]
- [ ] CHK054 — Is NFR-008's prohibition on SaaS / tracker / hosted-auth dependencies expressed as something a code reviewer can check (no new imports, no new outbound hostnames)? [Measurability, Spec §NFR-008] [Ambiguity]
- [ ] CHK055 — Is NFR-009's "configurable throttle window" tied to a specific configuration surface (file or env var) rather than left implicit? [Completeness, Spec §NFR-009] [Gap]

## JSON & CLI Contract Quality

- [ ] CHK056 — Is the stability promise for the `--json` schema scoped (across patch releases? minor releases? both?), with a documented breakage policy? [Clarity, Spec §FR-022] [Ambiguity]
- [ ] CHK057 — Are the FR-023 case-name strings (`cli_update_available`, etc.) declared as **stable JSON tokens**, not just example labels? [Clarity, Spec §FR-023, §"Key Entities → Upgrade message catalog"]
- [ ] CHK058 — Are exit-code semantics specified for `--dry-run` (always 0? non-zero when migrations pending? non-zero when CLI is too old)? [Completeness] [Gap]
- [ ] CHK059 — Are help-text requirements specified for the new flags (`--yes`, `--cli`, `--project`, `--no-nag`)? [Completeness] [Gap]

## Domain Language Quality

- [ ] CHK060 — Does every term in §"Domain Language" have a definition that is testable (a reviewer can label a real-world example as matching or not)? [Clarity, Spec §"Domain Language"]
- [ ] CHK061 — Are the avoided synonyms in §"Domain Language" actually absent from the rest of the spec body? [Consistency, Spec §"Domain Language"]
- [ ] CHK062 — Does the spec consistently use "current project" rather than "the workspace" / "this repo" / "the project"? [Consistency, Spec §"Domain Language"]

## Dependencies & Assumptions

- [ ] CHK063 — Are A-001 (cache location), A-002 (injectable provider), A-003 (planner architecture), and A-006 (`--yes`/`--force` aliasing) each annotated with their **revision triggers** (what would invalidate them)? [Traceability, Spec §"Assumptions"]
- [ ] CHK064 — Are the existing modules listed in §"Dependencies" each annotated with the kind of change expected (refactor / wrap / replace / unchanged)? [Completeness, Spec §"Dependencies"] [Gap]
- [ ] CHK065 — Is the assumption that PyPI is the canonical authoritative source for "latest version" validated against the project's release process (i.e., no parallel release channel that would lie)? [Assumption, Spec §A-002]
- [ ] CHK066 — Is the assumption that `platformdirs`-equivalent logic is acceptable for cache location validated against C-009 (no new mandatory runtime dependency)? [Assumption, Spec §A-001, §C-009]

## Ambiguities & Conflicts

- [ ] CHK067 — Does any FR/NFR/C in the spec leave the decision of *whether* to print the nag in addition to a block message ambiguous? [Ambiguity, Spec §FR-002, §FR-009, §"Scenario B"]
- [ ] CHK068 — Does the spec resolve whether `spec-kitty upgrade --cli` may attempt a self-upgrade or only print guidance? FR-016 says "supported self-upgrade behavior" — is that scoped to install methods that support it? [Ambiguity, Spec §FR-016]
- [ ] CHK069 — Does the spec resolve whether the planner runs (and consults the network) for `--help` and `--version`? [Ambiguity, Spec §"Scenario G"] [Gap]
- [ ] CHK070 — Does the spec resolve whether the nag's fetch-on-first-call behavior in an interactive shell counts as "uncached network in CI" if `CI=1` is unset but stdout is not a TTY (e.g., piping to `less`)? [Ambiguity, Spec §A-007] [Gap]

---

## Notes

- Items marked `[Gap]` denote missing content that the spec should add (or the planner should explicitly defer with rationale).
- Items marked `[Ambiguity]` denote present-but-imprecise content that should be sharpened before planning.
- Items marked `[Assumption]` denote claims that should be validated against external reality before becoming load-bearing.
- A passing checklist does **not** mean implementation is correct — it means the requirements are well-written enough to plan against. Implementation correctness is verified later by `/spec-kitty.review` and the test matrix in §"Verification Expectations".
- Address `[Gap]` and `[Ambiguity]` items by editing `spec.md` (preferred) or by recording a justified deferral in the plan's decision log.
