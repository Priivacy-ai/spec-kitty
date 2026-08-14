# Tracer — design decisions

Mission `mission-type-guard-registry-01KZY2FG` (issue #3386), plan phase, 2026-08-13.
Seeded at planning per charter Standing Order #3 (mission tracer files). Each entry
states the decision, the alternative(s) considered, and why the alternative was
rejected — not just the outcome.

## 1. Registry-dict dispatch shape: `dict[str, Callable]` inside `runtime_bridge_cores.py`, not a new module

**Decision**: `_GUARD_TABLES` is a plain `dict[str, Callable[[_ArtifactPresenceSnapshotLike],
list[str]]]` defined in the same module that already owns `evaluate_guards` and all
four per-family evaluator functions.

**Alternative considered**: a `NodeKind.GUARD` / `GATES`-relation DRG primitive,
formalizing guards as graph-modeled doctrine artifacts.

**Why rejected**: verified first-hand against
`docs/adr/3.x/2026-07-16-2-mission-type-step-authority-and-template-vocabulary.md:104-105,122-123`
— that ADR explicitly defers exactly this ("S-E — Guards... Deferred without debt")
to an unrelated future epic slice. A dict registry is filling in the existing,
already-engine-baked condition-table pattern the four per-family functions already
use; it is not anticipating or blocking that epic. Building the DRG version now
would be scope creep past what #3386 asks for and would collide with work an ADR
has already reserved for later.

## 2. Strict-vs-tolerant split: two call sites into the SAME registry, not two registries

**Decision**: one `_GUARD_TABLES` dict, looked up by one new function
(`evaluate_guards_strict`) that either returns the evaluator's result or raises
`UnregisteredMissionFamilyError`. The legacy path (`_check_cli_guards`) calls this
strict function directly and lets the exception propagate. The composed path
(`_check_composed_action_guard`) also calls it directly, but wraps the call in its
own try/except, catches the exception, and returns `[]`. `evaluate_guards`'s
existing public name is kept as a third, tolerant-by-default wrapper purely for
backward compatibility with direct callers (existing tests) that already call it
by that name today.

**Alternative considered**: keep one shared `evaluate_guards(snapshot)` entry
point and thread a `strict: bool` parameter through it, or dispatch on a
"caller identity" flag.

**Why rejected**: this is exactly the shape SPEC-ARCH-001 (a confirmed spec-review
finding) warned against — a boolean/flag-threaded shared function makes it
possible for an implementation to satisfy a literal unit test on the flag's
raising branch while the real call site (`_check_cli_guards`) never actually
passes `strict=True`, silently keeping the legacy path on the tolerant behavior.
Making the strict path a SEPARATE, directly-callable function that
`_check_cli_guards` itself invokes as its literal last line closes that loophole
by construction — there is no flag to forget to pass, because there is no flag.

## 3. WARNING log level, and WHICH FILE logs it

**Decision**: the composed path's neutral-degrade WARNING log call lives inside
`_check_composed_action_guard` in `runtime_bridge_composition.py` — not inside
`runtime_bridge_cores.py`'s tolerant wrapper, and not inside the
`runtime_bridge.py` compat delegate that forwards to the real implementation.

**Alternative considered**: put the log call inside `runtime_bridge_cores.py`'s
`evaluate_guards` tolerant-wrapper itself, so both the direct-`evaluate_guards`
caller and the composed path get the log "for free" from one place.

**Why rejected**: two independent reasons, both verified first-hand rather than
asserted. First, `runtime_bridge_cores.py`'s own module docstring declares it a
"zero-dependency leaf" where "every function here is pure: no filesystem, no git,
no `meta.json` reads" — a logging call is a real I/O side effect, and adding one
to the module's tolerant wrapper would quietly break an invariant the module's own
header exists to protect, for the sake of a shortcut. Second, FR-004 in spec.md
already names the destination explicitly ("the composed path's actual
implementation site... not `runtime_bridge.py`") specifically because an earlier
review round (R4) caught the spec citing the WRONG destination file for this exact
log call — repeating that mistake at the design level, even after the prose was
fixed, would defeat the point of the correction. The log level itself, WARNING,
was pinned by SPEC-VERIFY-002 against the cross-file precedent at
`runtime_bridge.py:348-354` (the `DecisionGitLog`-construction-failure fallback,
`logger.warning(...)`) — a "problem detected, continuing anyway" precedent, not
`_dispatch_via_composition`'s own `logger.exception(...)` at ERROR (a different
failure mode: an executor crash, not a tolerant degrade).

## 4. `doctor mission-type`'s state taxonomy: read-both-keys-separately, not reuse `_canonical_meta_mission_type`

**Decision**: the FR-008 classifier reads the `mission_type` key and the legacy
`mission` key as two SEPARATE canonicalization results (both going through the
shared `canonical_mission_type_key` primitive), and branches on which one, if
either, produced a non-`None` key — rather than calling
`_canonical_meta_mission_type` and working only with its single collapsed answer.

**Alternative considered**: call `_canonical_meta_mission_type(meta)` directly,
since it is the existing, already-correct canonicalization function used
elsewhere in the runtime.

**Why rejected**: read `_canonical_meta_mission_type`'s body directly
(`specify_cli/mission.py:551-556`) — it loops `("mission_type", "mission")` and
returns the FIRST field whose canonicalized value is non-`None`, which means a
blank/null/non-string `mission_type` value silently falls through to the legacy
`mission` key and returns THAT value as if it were the resolved type. That is
precisely the "two divergent meta readers" defect class Out of Scope item 2 names
as a real, independent, NOT-fixed-by-this-mission problem. Calling that function
here would make `doctor mission-type`'s own classification depend on, and
implicitly bless, the exact ambiguity the mission is explicitly not authorized to
touch. Reading both keys independently keeps `legacy-key-only` a real,
distinguishable state (per FR-008's own definition) and keeps the audit command's
behavior independent of whichever way that separate defect eventually gets fixed.
One direct, spec-mandated consequence of this choice: a present-but-blank
`mission_type` key classifies as `typeless` even when the legacy `mission` key
holds a real value — read FR-008's closing sentence literally, it says blank/null/
non-string `mission_type` values classify as `typeless`, full stop, with no carved-out
exception for "unless the legacy key has something." This is counter-intuitive
enough that it gets its own boundary test per FR-08's own requirement, and its own
called-out paragraph in plan.md so a later implementer does not silently pick the
more-intuitive-but-wrong reading.

## 5. The `_PRESENCE_FILE_TAGS` gap — found during verification, not proposed by the spec

**Decision**: add `"research.md"` to `runtime_bridge_io.py`'s `_PRESENCE_FILE_TAGS`
tuple as part of this mission, even though neither spec.md nor the readiness probe
named this file.

**Why this exists as a decision at all**: `_check_artifact_present(snapshot, tag)`
only ever reports a tag present if it appears in `snapshot.present_artifacts`,
which `gather_artifact_presence` builds by scanning exactly the filenames listed
in `_PRESENCE_FILE_TAGS` — a fixed 9-tuple that does not include `"research.md"`.
Without this one-line addition, `plan`'s own new `research`-step guard (FR-002)
would always report `research.md` missing, even when the file genuinely exists on
disk — reintroducing a small silent-misbehavior defect inside the very fix this
mission exists to ship. This was only found by reading `gather_artifact_presence`'s
actual implementation end-to-end (not by reading its docstring, which merely says
it mirrors "the exact set of ... reads ... across all three mission families" —
true today, but silently wrong once a fourth family with a new artifact tag is
added) — a direct instance of the orchestrating brief's instruction to verify
citations against real code rather than trust prose. Confirmed safe for NFR-001
by checking that no existing per-family evaluator function reads the
`"research.md"` tag anywhere today, so the addition is purely additive.

## 6. No distinct campsite-clean-first commit

**Decision**: this mission's first commit is the FR-010 ATDD red-first test, not a
separate tidy-up commit.

**Why**: charter Standing Order #2 requires an explicit determination, not silent
skipping. I checked the exact lines this mission's functional change touches
(`runtime_bridge_cores.py:348-567`, `runtime_bridge.py:670-699`,
`runtime_bridge_composition.py:427-486`) for pre-existing, unrelated Sonar
findings, complexity violations, or stale in-code citations, and found none — the
one stale citation this mission's own review trail already caught (the 2-line
`_check_cli_guards` line-number drift) was in spec.md's PROSE, already fixed there
in a prior review round, and was never a code-level defect to begin with. There is
nothing domain-matched to fold in as a preceding tidy-first step.

## 7. Post-rebase citation refresh (#3346 landed underneath this mission) — decision: correct coordinates only, never re-open the design

**Context**: after this mission's design phase completed (spec → plan → tasks →
analyze, verdict `ready`, all citations verified first-hand against `main` @
`ab0a0b9b5`), the mission branch was rebased onto `main` @ `7923fda40` (#3346,
"fix: isolate explicit owned-checkout mission state"), which added 182 lines to
`src/runtime/next/runtime_bridge.py` (first hunk at old line 233) and 23 lines to
`.github/workflows/ci-quality.yml` (one hunk at old line 3392), plus touched
`src/runtime/next/decision.py` and `tests/next/test_runtime_bridge_unit.py` (both
uncited by this mission's design artifacts, so untouched here).

**Decision**: treat every `runtime_bridge.py`/`ci-quality.yml` citation whose old
line number falls after the respective insertion point as needing a coordinate
correction only — re-verify the code at the new location is byte-identical to
what was verified at plan/tasks time, correct the line number, and add a short
"re-verified post-#3346-rebase" annotation so a future reader can tell the
correction from an original claim. Do NOT touch the requirement, acceptance
criterion, or design decision the citation supports.

**Verification method, not assumption**: diffed `7923fda40^..7923fda40` for both
files, computed the exact cumulative line-delta at each cited line (deltas are
NOT uniform across a file — they step at each hunk boundary), then confirmed each
new coordinate by reading the actual current file content and checking it matches
the original cited text verbatim. Two deltas resulted, not one: `runtime_bridge.py`
citations between old line 360 and old line 1203 shifted by a stable **+105**
lines (`_check_cli_guards` 680-698→785-803, its `mission_family="software-dev"`
hardcode 692→797, the `_check_composed_action_guard` compat delegate 878-891→
983-996, the guard-evaluation section header 670-699→775-804); the one citation
inside the earlier, variable-delta hunk zone (the `DecisionGitLog`
construction-failure WARNING-log precedent, FR-004's cross-file motivation for
picking WARNING) shifted by **+51** (348-354→399-405) because it sits between two
hunks of different sizes, not in the stable-delta zone most of the other
citations share — computing this one by uniform-offset assumption would have
been wrong by 54 lines. `ci-quality.yml`'s diff-coverage `critical_paths` entry
and its `--fail-under=90 --include` invocation both shifted by a uniform **+23**
(3489→3512, 3516-3517→3539-3540) since #3346 touched that file with exactly one
insertion, before both citations.

**What did NOT move, confirmed by direct verification, not by assumption from
"only these three files changed"**: `runtime_bridge_cores.py`,
`runtime_bridge_composition.py`, and `runtime_bridge_io.py` were not part of
#3346's diff at all, so every citation into them (`evaluate_guards` at 351,
`_evaluate_research_guards` at 415, `_evaluate_documentation_guards` at 439 with
its `accept`-case precedent at 455-456, `_evaluate_software_dev_guards` at 554
with its catch-all `return []` at 566, `_PRESENCE_FILE_TAGS` at 708-718, the
composed path's real `_check_composed_action_guard` at 427-486) is unchanged —
confirmed by reading each cited line, not inferred from the commit's file list
alone. The historical citation inside `runtime_bridge_cores.py`'s own module
docstring ("moved VERBATIM from `runtime_bridge.py:343-473`, pre-decomposition
line numbers") is correctly left untouched — plan.md's Campsite-Clean Scope
section already, correctly, flagged this as a frozen provenance record rather
than a live cross-reference, and it lives in a file #3346 never touched, so it
is doubly unaffected. `runtime_bridge.py:162` (the `_cores` import) is also
unaffected — it precedes #3346's first hunk (old line 233).

**Also re-confirmed, not assumed**: the #3386 defect itself still reproduces
byte-for-byte on the rebased base — `plan`/`review` still returns
`["Not all work packages are approved or done"]`, `_check_cli_guards` still
hardcodes `mission_family="software-dev"` and does not raise for an unregistered
family, the composed path still returns the same WP-iteration message (not a
neutral degrade) with zero WARNING-level log records naming the family, and
`evaluate_guards_strict` / `UnregisteredMissionFamilyError` / `_evaluate_plan_guards`
still do not exist. #3346's own scope (checkout ownership / coordination-workspace
resolution) never touched guard dispatch — it added parameters and new
functions around `_wrap_with_decision_git_log` / `_dn_bootstrap` /
`decide_next_via_runtime`, nowhere near `_check_cli_guards` or
`_check_composed_action_guard`'s guard-evaluation logic itself. No RED pin
flipped to green; none of this mission's WPs ship coverage that proves nothing.
