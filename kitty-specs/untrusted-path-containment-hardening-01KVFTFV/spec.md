# Mission Specification: Untrusted-Path Containment Hardening

**Mission slug**: `untrusted-path-containment-hardening-01KVFTFV`
**Mission type**: software-dev
**Target / merge branch**: `automation/sonar-security-20260619` (stacked on PR #2036)
**Status**: Draft

## Purpose

spec-kitty routinely consumes path segments — `mission_slug`, `feature_slug`,
`wp_id` — that originate from **untrusted on-disk content**: `status.events.jsonl`
event records, `meta.json`, frontmatter, config, and CLI arguments. Several code
paths join those segments straight into a filesystem location and then read or
write/`mkdir`, with no containment check. A crafted segment such as
`"../../../../tmp/evil"` can therefore cause reads or writes **outside** the
repository's trusted, derived roots.

This mission closes that **vulnerability class** — not a single instance — by
routing every untrusted segment through a single canonical validation seam
before it reaches any filesystem sink, and by adding a regression guard that
prevents new ad-hoc unvalidated joins from reappearing. It builds directly on
the hardening already landed in PR #2036 (this branch), generalising those
point fixes into a codebase-wide invariant.

## User Scenarios & Testing

**Primary actor**: the spec-kitty CLI (and its runtime), acting on a repository
whose on-disk state may have been authored or corrupted by an untrusted party.

**Primary scenario (happy path)**: A maintainer runs a normal command
(`spec-kitty status materialize`, `merge`, status read) on a repository with
well-formed mission metadata. Every path segment passes the canonical guard
unchanged; behaviour is identical to today. No legitimate workflow is affected.

**Adversarial scenario (must fail closed)**: A repository contains a
`status.events.jsonl` line with `"mission_slug": "../../../../tmp/evil"` (or a
segment naming a symlink directory that points outside `kitty-specs/`). The
operator runs `spec-kitty status materialize` / a status read / a merge. The CLI
**must not** read or write any path outside the trusted root. Instead it fails
closed: the hostile segment is rejected, a warning is logged, and the operation
either falls back to the trusted `feature_dir` name (write surfaces) or skips
the unresolvable record (read surfaces). The CLI never crashes and never widens
access silently.

**Exception / edge cases**:

- Segment is empty or absent → existing fallback to `feature_dir.name` (already
  handled) continues to apply.
- Segment is a valid single label but names a **symlink directory** planted
  under a trusted root pointing outside it → must be rejected via
  `resolve()`-containment (the residual closed by this mission).
- A new code path introduces an unvalidated untrusted-segment join after this
  mission lands → the regression guard fails CI.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| untrusted path segment | a slug / id read from on-disk content or CLI input, not yet validated | "user input" (too broad) |
| trusted root | a repo-derived directory a sink is allowed to touch (`.kittify/derived/`, `kitty-specs/`, `.worktrees/`, merge-state) | "safe dir" |
| containment validation | proving a resolved path stays within a trusted root (segment grammar **and** `resolve()`-containment) | "sanitisation" (ambiguous) |
| canonical seam | the single shared validation entry point (`assert_safe_path_segment` / `safe_mission_slug` / `ensure_within_any`) | per-call-site guard |
| fail closed | on a rejected segment, skip/fallback to a trusted value + warn; never read/write outside, never crash | "fail safe" |

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Every untrusted path segment in the FR-004 audit inventory whose disposition is `routed-through-seam` MUST pass the canonical seam before its filesystem read/write/`mkdir` sink, verified by a negative test per sink. "Close the class" = (every inventory sink dispositioned) + (FR-005 guard preventing new ad-hoc joins); it is NOT a claim of mathematical completeness over future code. | Draft |
| FR-002 | `status/store.py` `_SlugResolver.resolve` MUST apply `resolve()`-containment (not segment-grammar alone), so a valid-label slug naming a symlink directory that escapes `kitty-specs/` is rejected. (Q1→A) | Draft |
| FR-003 | `status/aggregate.py`'s existing slug guard (`_validate_mission_slug`, which raises `InvalidMissionSlug`) MUST be documented as already covering the slug grammar; any aggregate composed-path read lacking `resolve()`-containment (e.g. `_find_meta_path` globs) MUST be recorded and dispositioned in the FR-004 audit, not assumed to need resolver-parity work. | Draft |
| FR-004 | A reproducible audit (script/ruleset committed under a tracked location, e.g. `tests/architectural/untrusted_path_audit/`) MUST enumerate every `src/specify_cli` call site where a path built from a defined seed-set of untrusted sources (`mission_slug`, `feature_slug`, `wp_id`, and any segment read from `status.events.jsonl`/`meta.json`/frontmatter/CLI args) reaches a defined sink predicate (`open`/`read_text`/`read_bytes`/`write_text`/`write_bytes`/`mkdir`/`Path(...) / <segment>`). The seed-set and sink predicate MUST be recorded so a reviewer can re-run and reproduce the inventory. (Q2→C) | Draft |
| FR-005 | A `tests/architectural/` regression guard MUST fail when a new unvalidated untrusted-segment join is introduced on an FR-004 audited surface. The guard MUST itself be load-bearing: a fixture introducing such a join MUST make the guard fail, and removing the guard MUST make that fixture test pass. The guard's matched-surface set is the FR-004 inventory, not a heuristic over all `Path /` joins. | Draft |
| FR-006 | The loopback-only rationale for `core/loopback_http.py` MUST be documented in-code and its 127.0.0.1-binding regression tests retained; the open Sonar hotspots MUST be recorded for UI hotspot review (no code change). | Draft |
| FR-007 | The mission MUST recognise PR #2036 as the landed first increment (merge.py capture-time snapshot validation, wrapper `0755→0700`, `store.py` segment guard, the `safe_mission_slug` helper, and the reducer-seam chokepoint). The chokepoint covers ONLY the event-log slug path; `progress.py` is fully covered, but the `meta.json`-derived slug fallback feeding `views.py`/`lifecycle.py` is NOT (see FR-009). The mission MUST build on #2036 without regressing it. | Draft |
| FR-008 | Each containment guard added or extended MUST carry a mutation-killing negative test (fails when the guard is removed), including (a) a symlink-escape case for surfaces using `resolve()`-containment AND (b) a symlinked-root positive case proving a legitimate slug under a symlinked repo/specs/temp root is ACCEPTED (no false reject). | Draft |
| FR-009 | The `meta.json`-derived mission slug (`resolve_mission_identity` in `mission_metadata.py`, consumed by `views.py:_stale_check_slug` and the `lifecycle.py` empty-slug fallback into `derived_dir / <slug>` `mkdir`) MUST pass the canonical seam, failing closed to `feature_dir.name`. This closes the write-path traversal still live after #2036 when the event slug is empty or downgraded. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | New and touched code passes the quality gates with zero issues. | `ruff` and `mypy` report 0 errors/warnings on changed files; no new `# noqa`/`# type: ignore`. | Draft |
| NFR-002 | Containment validation adds no meaningful runtime cost. | Validation is O(segment length) with no new disk reads/syscalls in the validation path; satisfied by code inspection (no `open`/`stat` beyond the single `resolve()` already required) — no benchmark gate. | Draft |
| NFR-003 | Backward compatibility for legitimate inputs. | 100% of pre-existing status/merge tests pass unchanged; no legitimate slug is rejected, including under a symlinked repo/temp root (the macOS `/tmp`→`/private/tmp` case). | Draft |
| NFR-004 | Fail-closed behaviour is observable. | Each distinct rejected segment emits at most one WARNING naming the segment (de-duplicated via the resolver cache); 0 unhandled exceptions on the read path. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | MUST NOT force HTTPS on loopback (127.0.0.1) control-plane URLs; loopback transport semantics are preserved. | Draft |
| C-002 | MUST reuse the canonical guards (`assert_safe_path_segment`, `safe_mission_slug`, `ensure_within_any`); no parallel validation mechanism (migrate, don't wrap). | Draft |
| C-003 | MUST NOT prescribe a version/patch number; scope is framed as focus/milestone (release versioning is assigned by the PO at release time). | Draft |
| C-004 | Read sinks MUST fail closed by skipping (return `None`); write sinks MUST fail closed by falling back to the trusted `feature_dir` name. Neither may crash or silently widen access. | Draft |
| C-005 | Cite related artifacts and findings by canonical id/issue number, never by fragile file path, in mission prose. | Draft |

## Success Criteria

- **SC-001**: A crafted `status.events.jsonl` (traversal `mission_slug`) AND a
  crafted `meta.json` (traversal `mission_slug`, with empty event slug), run
  through every audited command, produce **zero** filesystem reads or writes
  outside the trusted roots (verified by negative tests per sink, covering the
  `meta.json` fallback path of FR-009).
- **SC-002**: The symlink-escape case is rejected on every surface that adopts
  `resolve()`-containment (`store.py`), proven by mutation-killing tests; and a
  legitimate slug under a symlinked root is ACCEPTED (no false reject).
- **SC-003**: The audit inventory assigns every untrusted→FS sink exactly one
  disposition — `routed-through-seam` (seam call cited), `unreachable`
  (reachability rationale naming the call chain), or `trusted-source` (segment
  proven to originate from `feature_dir.name` or another derived value). The
  audit script's emitted count MUST equal the inventory row count (no manually
  dropped rows); a row with no disposition fails this criterion.
- **SC-004**: Removing any newly-added guard causes at least one test to fail
  (no fake guards).
- **SC-005**: The SonarCloud code-scanning alerts resolved by PR #2036 are
  confirmed closed and the two `core/loopback_http.py` hotspots have a recorded
  rationale for UI review (cited by Sonar rule key + PR #2036 per C-005).
- **SC-006**: The FR-005 architectural guard fails when a new ad-hoc unvalidated
  untrusted-segment join is introduced on an audited surface (guard is
  load-bearing, not vacuous).

## Key Entities

- **Untrusted path segment** — a slug/id sourced from on-disk content or CLI args.
- **Trusted root set** — the allowlist of repo-derived directories a sink may touch.
- **Canonical seam** — `assert_safe_path_segment` (segment grammar),
  `safe_mission_slug` (fail-closed fallback), `ensure_within_any`
  (`resolve()`-containment).
- **Sink** — a filesystem read / write / `mkdir` that consumes a path built from
  an untrusted segment.

## Findings / Sonar Matrix

| Source | Disposition |
|--------|-------------|
| SonarCloud code-scanning: `merge.py` path-injection | Fixed in PR #2036 (capture-time trusted-path validation). |
| SonarCloud code-scanning: `claude_wrapper.py` world-accessible chmod | Fixed in PR #2036 (`0755→0700`). |
| SonarCloud hotspot ×2: `core/loopback_http.py` loopback HTTP | Document loopback-only rationale; retain regression tests; no code change (FR-006, C-001). |
| Squad-found sibling: `status/store.py` resolver (read) | Segment guard landed in #2036; `resolve()`-containment to be added (FR-002). |
| Squad-found sink: `progress.py` write sink | Fully closed in #2036 (uses only `snapshot.mission_slug or feature_dir.name`). |
| Review-found (code-verified) bypass: `views.py` / `lifecycle.py` write sinks via `meta.json` slug | NOT closed by #2036 — the reducer seam covers only the event-log slug; `resolve_mission_identity` reads `meta.json mission_slug` unvalidated, reachable when the event slug is empty/downgraded. New work this mission (FR-009). |

## Assumptions

- The threat model is a repository whose on-disk mission state is untrusted
  (same model as the merge.py rollback hardening already shipped); spec-kitty is
  run by a trusted operator against that repo.
- `feature_dir.name` is a single path component (`Path.name` strips separators)
  derived from the directory the operator is acting in; it is treated as trusted.
  Defense-in-depth passing it through `assert_safe_path_segment` is optional, not
  required.
- Containment is evaluated against the **resolved** form of both the candidate
  and the trusted root, so a symlinked trusted/temp root (e.g. macOS
  `/tmp`→`/private/tmp`, repo under `/var`→`/private/var`) is handled — the
  caller passes the un-resolved logical root and lets `ensure_within_any` resolve
  both sides. Tests MUST include a symlinked-root positive case (FR-008b).
- TOCTOU (a symlink swapped between `resolve()` and the subsequent read) is OUT
  of scope under the threat model: on-disk state is authored before the run, not
  mutated concurrently by an active adversary.
- The codebase-wide audit is scoped to `src/specify_cli`; the shared runtime and
  external packages are out of scope unless the audit surfaces a reachable sink.

## Out of Scope

- Forcing TLS/HTTPS on loopback-only control-plane URLs (C-001).
- Hardening the shared runtime / external PyPI packages beyond confirmed sinks.
- Any version-number or release-milestone assignment (C-003).
