# Tracer: Design Decisions

Mission: accept-path-remediation-honesty-01M0TWZP (issues #3730, #3085)

## Decision: one mission spec covers both issues, not two

Rationale: same functions, same seam (`validate_mission_paths` and its two callers),
readiness report verdict `autonomous` explicitly recommends the combined WP1-4
shape. Splitting would force WP1 (path correctness) to land twice or force an
artificial ordering dependency between two missions instead of two WPs.

## Decision: WP2's fix is code-side reconciliation, not a `mission.yaml` declaration
change

Per the readiness report's resolved ambiguity #2: `software-dev/mission.yaml`
declaring `contracts/` under both `artifacts.optional` and `paths.deliverables` is the
root cause, but #3085's own suggested fix targets the code (`collect_feature_summary`
/ `evaluate_path_conventions`) rather than un-declaring the path from one of the two
YAML lists. This mission fixes the reconciliation logic; whether `mission.yaml`'s dual
declaration should also change is left as an option, not a requirement, consistent
with the issue's own suggested-fix framing.

**Correction (post spec-review, SPEC-ARCH-001):** "the functions that read both
lists" is imprecise about which of the two functions is actually config-driven.
`collect_feature_summary`'s `optional_missing` side is computed by
`_missing_artifacts(feature_dir)` from a hardcoded, mission-type-agnostic literal
list (`QUICKSTART_FILE`, `DATA_MODEL_FILE`, `RESEARCH_FILE`, `"contracts"`) — it
takes no `mission` parameter and never reads `mission.config.artifacts.optional`.
Only `evaluate_path_conventions` → `validate_mission_paths` genuinely reads
`mission.config.paths` / `mission.config.artifacts`.

**Correction (post spec-review, SPEC-FRESH-001):** the above was itself imprecise —
`path_violations` (what `evaluate_path_conventions` returns) is not a list of
individually comparable resolved-path strings; it collapses
`PathValidationResult.missing_paths` into one already-rendered `format_errors()`
string before returning, and SC-005 pins that exact 2-tuple return shape via a
literal `violations, warning = evaluate_path_conventions(...)` destructure in a
regression test that must keep passing unmodified. So the code-side reconciliation
FR-002 requires is not a cross-reference between two already-computed, comparable
result lists — it is an interface change: `evaluate_path_conventions` needs a new
way to receive `optional_missing` (an additive input, not a change to its pinned
return arity) so it can drop the matching, normalized entry from that list before
its existing rendering step runs; `path_violations` itself keeps rendering the full,
unfiltered `missing_paths` exactly as today, which is what keeps `path_violations`
(not `optional_missing`) as the side that wins and keeps the pass/fail boundary
intact. See `spec.md`'s Key Entities `AcceptanceSummary` bullet for the full
data-flow and the token-normalization rule this also requires
(`optional_missing`'s bare tokens vs. `missing_paths`'s FR-001-resolved strings).

**Correction (post spec-review, SPEC-FRESH2-001):** the above named the interface
change (an additive input) but left the propagation mechanism itself unstated. Since
the return arity is pinned and `collect_feature_summary` binds `missing_optional`
once and reuses that same list object for both `build_warnings(...)` and the
`AcceptanceSummary(optional_missing=missing_optional, ...)` construction, the only
way the dedup reaches the caller is for `evaluate_path_conventions` to mutate the
passed-in `optional_missing` list **in place** before its existing 2-tuple return
runs — not to compute and discard a filtered copy. This is a deliberate departure
from the module's otherwise-pure-transform convention; spec.md's Key Entities
bullet now states this explicitly and requires WP2 to name the parameter and
document the side effect so a reviewer cannot mistake it for a no-op input.

This also means the fix is inherently `software-dev`-specific today (the literal
list happens to include `"contracts"`) — it does not generalize to `research`'s
analogous-looking `data/` dual declaration (`artifacts.optional` + `paths.data`),
which does not reproduce the double-report defect since `_missing_artifacts` never
checks `data/`. Out of scope for WP2.

## Decision: WP3's honesty fix combines three of #3730's four candidate directions

Per the readiness report's resolved ambiguity #1: combining "make 'required'
conditional on strict mode" + "name `--lenient` in the failure text" (via a
mode-parameter, not a hardcoded flag-name string, to avoid validator/CLI coupling) +
"widen `--help`" satisfies all four of #3730's acceptance criteria. The fourth
direction (drop/gate the `mkdir -p` suggestion) is treated as optional polish: keep
the suggestion, but rank `--lenient` first with a note that `mkdir -p` only silences
the check. This is a plan-phase implementation choice; the spec states the
operator-facing outcome (all four ACs) without prescribing the internal parameter
shape.

## Decision: repro/acceptance fixture is an explicit spec deliverable

Per the #3085 maintainer triage comment (2026-08-02, binding maintainer requirement).
Not treated as automatically satisfied by WP4's red-first tests — the spec calls out
the fixture as its own functional requirement so it cannot be silently dropped during
planning/tasking.

## Decision (plan phase, 2026-08-25): concrete WP1 resolved-string formatting approach

The spec pins *what* WP1 must report (the resolved path, e.g.
`kitty-specs/<slug>/contracts/`, not the bare token) but leaves the exact formatting
mechanics to planning. Resolved during this plan phase: at
`validate_mission_paths`'s missing-path branch (`paths.py:207`), compute the reported
string from `full_path` (already computed at `:197`/`:200`/`:202`) rather than from
`relative_path`, preferring `full_path.relative_to(project_root)` when it succeeds and
falling back to `str(full_path)` on `ValueError` (cross-worktree topology safety —
`format_errors()`/`format_warnings()` must never crash on a resolvable-but-unreported
path). The resolved string must preserve the declared token's trailing-slash
convention, since `suggest_directory_creation`'s `mkdir -p` vs. `touch` branch keys on
`path_str.endswith("/")` and a bare `Path` loses that trailing slash. This keeps the
repo-root/build-path case's reported string identical to today's (since
`full_path.relative_to(project_root) == candidate` there), satisfying User Story 1
Scenario 2 (repo-root reporting unchanged) as a natural consequence of the fix rather
than a separate branch.

## Decision (plan phase, 2026-08-25): concrete WP2 parameter name/signature

Per spec.md's Key Entities instruction to name the new parameter so it cannot be
mistaken for an inert pass-through: the parameter is named
`optional_missing_to_dedup: list[str] | None = None` on `evaluate_path_conventions`.
Both pinned tests (`test_strict_metadata_true_blocks_with_violation`,
`test_strict_metadata_false_downgrades_to_warning`) call the function positionally
with today's 4 args + `strict_metadata=` only, so `None` must be a true no-op default
(no dedup attempted) to keep both green unmodified. Token comparison normalizes each
side to its final path segment, slash-stripped (e.g. `"contracts"` from
`optional_missing` vs. the final segment of the resolved `missing_paths` entry, also
normalized to `"contracts"`) rather than full-string equality, since the two lists'
entries have different qualification levels (bare vs. `feature_dir`-resolved) even
after WP1 lands. The call site in `acceptance/__init__.py`'s `collect_feature_summary`
passes `optional_missing_to_dedup=missing_optional` into the existing
`evaluate_path_conventions(...)` call (`:1056`) before the `build_warnings(...)` call
that follows it (`:1058`), so the in-place mutation is visible to both `build_warnings`
and the later `AcceptanceSummary(optional_missing=missing_optional, ...)`
construction without any further plumbing change.
