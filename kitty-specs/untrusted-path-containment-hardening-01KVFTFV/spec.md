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
| FR-001 | Every untrusted path segment consumed by the CLI MUST pass the canonical containment seam before it reaches any filesystem read, write, or `mkdir` sink. | Draft |
| FR-002 | `status/store.py` `_SlugResolver.resolve` MUST apply `resolve()`-containment (not segment-grammar alone), so a valid-label slug naming a symlink directory that escapes `kitty-specs/` is rejected. (Q1→A) | Draft |
| FR-003 | `status/aggregate.py` resolver MUST receive the same `resolve()`-containment treatment as `store.py`, keeping the two sibling resolvers at parity. | Draft |
| FR-004 | A codebase-wide audit MUST enumerate every untrusted-string→FS-path sink in `src/specify_cli`; confirmed-reachable sinks MUST be routed through the canonical seam, and any sink left unfixed MUST be explicitly documented with its reachability rationale. (Q2→C) | Draft |
| FR-005 | A regression test MUST fail when a new untrusted-segment join bypasses the canonical seam (ban ad-hoc `root / <untrusted> ` joins for the audited surfaces). | Draft |
| FR-006 | The loopback-only rationale for `core/loopback_http.py` MUST be documented in-code and its 127.0.0.1-binding regression tests retained; the open Sonar hotspots MUST be recorded for UI hotspot review (no code change). | Draft |
| FR-007 | The mission MUST recognise PR #2036 as the landed first increment (merge.py capture-time snapshot validation, wrapper `0755→0700`, `store.py` segment guard, the `safe_mission_slug` helper, and the reducer-seam chokepoint protecting the three derived-view write sinks) and build on it without regressing it. | Draft |
| FR-008 | Each containment guard added or extended MUST carry a mutation-killing negative test (a test that fails when the guard is removed), including a symlink-escape case for the surfaces using `resolve()`-containment. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | New and touched code passes the quality gates with zero issues. | `ruff` and `mypy` report 0 errors/warnings on changed files; no new `# noqa`/`# type: ignore`. | Draft |
| NFR-002 | Containment validation adds no meaningful runtime cost. | No measurable regression in `status materialize` wall-time on a 100-event log (validation is O(segment length)). | Draft |
| NFR-003 | Backward compatibility for legitimate inputs. | 100% of pre-existing status/merge tests pass unchanged; no legitimate slug is rejected. | Draft |
| NFR-004 | Fail-closed behaviour is observable. | Every rejection emits exactly one WARNING naming the offending segment; 0 unhandled exceptions on the read path. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | MUST NOT force HTTPS on loopback (127.0.0.1) control-plane URLs; loopback transport semantics are preserved. | Draft |
| C-002 | MUST reuse the canonical guards (`assert_safe_path_segment`, `safe_mission_slug`, `ensure_within_any`); no parallel validation mechanism (migrate, don't wrap). | Draft |
| C-003 | MUST NOT prescribe a version/patch number; scope is framed as focus/milestone (release versioning is assigned by the PO at release time). | Draft |
| C-004 | Read sinks MUST fail closed by skipping (return `None`); write sinks MUST fail closed by falling back to the trusted `feature_dir` name. Neither may crash or silently widen access. | Draft |
| C-005 | Cite related artifacts and findings by canonical id/issue number, never by fragile file path, in mission prose. | Draft |

## Success Criteria

- **SC-001**: A crafted `status.events.jsonl` with a traversal `mission_slug`, run
  through every audited command, produces **zero** filesystem reads or writes
  outside the trusted roots (verified by negative tests per sink).
- **SC-002**: The symlink-escape case is rejected on every surface that adopts
  `resolve()`-containment (`store.py`, `aggregate.py`), proven by mutation-killing
  tests.
- **SC-003**: The audit output lists every untrusted-string→FS sink in the CLI
  with a fixed/decided/documented disposition; none is left unaccounted for.
- **SC-004**: Removing any newly-added guard causes at least one test to fail
  (no fake guards).
- **SC-005**: The two SonarCloud code-scanning alerts are resolved and the two
  loopback hotspots have a recorded rationale for UI review.

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
| Squad-found siblings: `progress.py` / `lifecycle.py` / `views.py` write sinks | Closed in #2036 via reducer-seam chokepoint (FR-007). |

## Assumptions

- The threat model is a repository whose on-disk mission state is untrusted
  (same model as the merge.py rollback hardening already shipped); spec-kitty is
  run by a trusted operator against that repo.
- `feature_dir.name` is a trusted segment (derived from the on-disk directory the
  operator is acting on), suitable as the write-surface fallback.
- The codebase-wide audit is scoped to `src/specify_cli`; the shared runtime and
  external packages are out of scope unless the audit surfaces a reachable sink.

## Out of Scope

- Forcing TLS/HTTPS on loopback-only control-plane URLs (C-001).
- Hardening the shared runtime / external PyPI packages beyond confirmed sinks.
- Any version-number or release-milestone assignment (C-003).
