# Implementation Plan: Tracker Egress Refusal

**Branch**: `bundle-c-tracker-refusal-3108` | **Date**: 2026-07-31 | **Spec**: [`spec.md`](spec.md)
**Input**: Mission specification from `/kitty-specs/tracker-egress-refusal-3108-01KYWF1R/spec.md`

**Note**: This plan is filled in by the `/spec-kitty.plan` command against the canonical template at
`src/doctrine/missions/software-dev/templates/plan-template.md`. Authored at `bb2020fea`
(upstream/main, 2026-07-31 08:52), the commit every measurement in this dossier was taken at.

**Implementation is deferred by operator instruction.** The plan is this step's deliverable;
implementation happens later, by a different worker. **Sibling Bundle A is a scheduling dependency,
not a technical prerequisite** — the earlier claim that it was one is corrected under *Coordination
with Sibling Bundles*, and that correction is **not** permission to begin. Whoever picks this up
starts at *Sequencing*, Stage 0, which pins the real base, revalidates ~40 line citations by symbol
name, and re-measures every baseline against a stated prediction. This document is written to be
executable by someone with no access to the session that produced it: every stage carries an **exit
criterion** naming its suite, its expected count and the pin to observe red-then-green; every
ordering claim names the hazard it defends against and is labelled **necessity** or **preference**;
and every hazard is measured in
[`tracer-evidence-base.md`](tracer-evidence-base.md) or [`tracer-squad-findings.md`](tracer-squad-findings.md).

**Authority order.** The code at `bb2020fea` wins; then `tracer-evidence-base.md` (measured); then
`tracer-squad-findings.md` (four-lens squad + operator decisions); then `spec.md`. Where this plan
resolves a disagreement between the brief and `spec.md`, it says so at the point of resolution and
again in *Open Items*.

---

## Planning Questions

The three `plan`-flow decision moments (`plan.approach`, `plan.risks`, `plan.dependencies`) were
deferred at the interview. They are answered here, as the template requires, before later phases.

**Approach.** Add a second, tracker-scoped consent channel in the project's own committed
`.kittify/config.yaml`, and join it with the existing hosted-sync channel in exactly one named
function **that is told which destination it is being asked about**. Nothing about Channel 1
changes. Channel 2's polarity follows the destination — two-way at `LOCAL_SUBPROCESS`,
narrowing-only at `HOSTED_SERVICE` — and *the destination is a required, keyword-only parameter
drawn from a closed two-member set, never derived from a config read*. That single change is what
makes the polarity rule a `mypy`-checkable, guard-pinned property instead of a convention: it is
**unsound** to derive the destination from the on-disk provider, because
`_resolve_saas_backend_for_provider` (`service.py:84-98`) overrides the provider in memory for
`--provider <saas>` and never rewrites the file. The function has **five enclosing call sites and
six call expressions** — three local gates, the hosted gate, and `sync doctor`'s renderer, which
asks once per destination. Ship the data layer and the verdict before the gate, because the gate is
the breaking change and its own blast-radius repair criterion depends on the data layer already
being correct.

**Risks.** The dominant risk is not a wrong gate — it is a gate that is installed, green, and never
entered. **Five** measured mechanisms produce that outcome: the house test pattern patches out the
gate; the default ownership mode makes the positive control vacuous; the arming abort already
satisfies every refusing assertion; **an empty tracker store never reaches `create_issue`, so a
fixture satisfying the first three still captures zero sentinel argv on the un-gated tree**; and
`bind`/`unbind` erase the committed key. All five are sequenced against in *Sequencing* and
enumerated with detection signals in *Risks*.

**Dependencies.** Bundle A (`#3115`, `#3113`) is a **scheduling** dependency, not a technical one —
see *Coordination with Sibling Bundles* for the correction and for why implementation is deferred
regardless. Bundle B (`#3110`) moves `project_egress_refusal` into a new `src/specify_cli/egress/`
package; this Mission is designed so that move is a one-line change in one file, in either landing
order. The internal dependency structure of this Mission is a **graph with two independent roots**,
not a chain — published as such under *Sequencing*.

---

## Summary

`spec-kitty tracker sync pull|push|run` on a `beads` or `fp` binding executes an operator-named
executable, resolved from a **machine-global** credential file, with the project's issue `title`,
`body`, `labels` and `assignees` as argv — and consults **zero** consent functions on the way.
A committed `sync: {enabled: false}` does not stop it. This is measured, not inferred
(`tracer-squad-findings.md` §8): a real fake `bd` installed on disk and named through the credential
file captured `['…/fake-bd', '--json', 'create', 'ACME Holdings carve-out', …]` with nothing in the
production path patched.

The premise of issue `#3108` is nevertheless false: `LocalTrackerService` **cannot** construct a
Jira or Linear connector (`factory.py:17` — `SUPPORTED_PROVIDERS = ("beads", "fp")`), and the
Jira/Linear path is already gated at `saas_client.py:329-331` by the chokepoint `#3030` FR-029
shipped. This Mission does not build that gate. It closes the two gaps that are actually open:
**Gap A**, no separability (one key, `sync.enabled`, answers two unrelated questions), and
**Gap B**, the entirely ungated `beads`/`fp` path.

**The decided model.** Tracker egress is decided by two channels joined in exactly one function.

- **Channel 1** — `resolve_egress_consent(repo_root)` reached through `project_egress_refusal`
  (`tracker/egress_consent.py:147`). Unchanged. Keyed on `project_uuid`. **Absence denies.**
- **Channel 2** — `tracker.egress` in the project's own committed `.kittify/config.yaml`. A closed
  set of two strings, `refused | permitted`; **absence is the key being missing**; any other present
  value is a **fault, and a fault refuses** (with the decode `isinstance`-guarded, because a bare
  membership test raises `TypeError: unhashable type` for a mapping or a list at the key).
- **The destination** — a required, keyword-only argument of the join function, drawn from the
  closed set `{LOCAL_SUBPROCESS, HOSTED_SERVICE}`, passed as a **literal** at every call site and
  **never derived from a config read**. At `LOCAL_SUBPROCESS` Channel 2 is two-way — `permitted`
  grants **independently of Channel 1**. At `HOSTED_SERVICE` it is **narrowing only** — `permitted`
  is a no-op, because `saas_client.py:247` resolves the base URL from
  `resolve_runtime_target().resolved_server_url` and every endpoint is `/api/v1/tracker/…` with a
  bearer token and `X-Team-Slug`: **the destination is spec-kitty's own hosted service**, so a grant
  there would reopen `#3030`'s P0 boundary to the destination the 2026-07-27 incident leaked to.
- **Absence of both channels still denies**, which makes this a breaking change for every existing
  local binding, carried as a first-class deliverable rather than a footnote.

**The technical approach, in one line:** one new module holding
`tracker_egress_verdict(root, *, destination)` and the `EgressDestination` enum, one new known field
on `TrackerProjectConfig` carrying its raw value plus a derived fault, preservation work at six
config-construction sites, five enclosing call sites, **five** AST guards, and an acceptance harness
whose own positive control — **against a seeded store** — is established on the un-gated tree before
any gate exists.

---

## Technical Context

**Language/Version**: Python 3.11+ (charter minimum). CI runs 3.11/3.12; the local interpreter in
this environment is 3.14. **Record the interpreter version alongside every bind count and every
guard input count** — a zero bind count on 3.14 is evidence that the environment differs, not that
the branch is dead (see *Red-First Proof Strategy*, "five ways a mutation silently lies", item 4).

**Primary Dependencies**: `ruamel.yaml` (round-trip loader; `preserve_quotes` is in scope per
FR-010), `typer` + `rich` (CLI surface and `sync doctor` rendering), `httpx` (trip-wire target only —
this Mission adds no HTTP), `spec-kitty-tracker` (external contract package per charter — the
**public** names this Mission composes with are `SyncEngine`, `OwnershipPolicy`, `CanonicalIssue`,
`ExternalRef`, `CanonicalStatus`, `CanonicalIssueType` and the store protocol's `upsert_issue` /
`list_issues`), `pytest`.

> **`SubprocessCommandRunner` is not an injection seam and must not be described as one.**
> Checked: it is **absent from `spec_kitty_tracker.__all__`**, so it is not publicly importable, and
> `build_connector` passes **no runner**, so there is nothing to inject into. The charter's
> shared-package boundary forbids reaching into the private submodule to manufacture a seam. **The
> recorder *is* the fake executable on disk** — a script named through the machine-global tracker
> credential file (`factory.py:56`) that appends its argv to a file. Every phrasing of the form
> "installed at or below `SubprocessCommandRunner.run`" is dropped from this dossier.

**Storage**: the project's committed `.kittify/config.yaml` `tracker:` block (Channel 2 — read and
written); the machine-global consent index (Channel 1 — read only, via the existing chain); the
machine-global tracker credential file (read, and **only behind the gate** after FR-001); the tracker
SQLite store at the resolved db path (`store.py:278-281` — **must not exist** after a refused
command, NFR-002).

**Testing**: pytest, targeted packages per the charter's Testing Requirements (the full ~17k-test
suite is not this Mission's gate). ATDD red-first with the failing test committed before the
implementation commit (charter C-011). Acceptance exercised **end to end through the CLI**, with a
real fake `bd` executable on disk named through the machine-global credential file, and with the
**tracker store seeded** before every push/run case. Mutations are **pytest plugins injected via
`PYTHONPATH`**, never source edits.

**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+). **The acceptance harness is
POSIX-scoped and must say so.** The recorder is a `#!`-script made executable and `subprocess.run`
takes no shell, so on Windows the credential-named command must be a `.cmd`/`.bat` sibling. Either
ship the sibling or mark the acceptance suite `skipif(os.name == "nt")` **with the reason recorded
in the file and in the WP** — a silently POSIX-only acceptance suite on a target platform that
includes Windows is a coverage claim the Mission has not earned. Chosen default: **document the
skip**; the Windows sibling is a follow-up, because it would need a Windows CI runner to be worth
anything and this Mission has no way to prove it works.

**Project Type**: single project — CLI library under `src/specify_cli/`, tests under `tests/`.

**Performance Goals**: CLI operations < 2 s (charter). The gate adds, per sync command, one read of
the project's `.kittify/config.yaml` and one hosted-sync consent resolution — both already performed
downstream today; the gate moves one of them earlier and adds one file read.

**Constraints**:
- `tracker_egress_verdict` and Channel 2's resolver **never raise** (NFR-003) — for every probed
  input shape, including `chmod 000`, unparseable YAML, a non-mapping `tracker:` block, and a
  `repo_root` that is not a project root.
- **No import-time dependency on `specify_cli.sync` from `tracker/`.** The hosted-sync imports the
  Channel-1 reporting classifier needs (`resolve_project_consent`,
  `resolve_checkout_sync_routing_readonly`) are made **at call time inside a guarded block**,
  degrading to generic Channel-1 wording on failure. This is also why the absence sentinel is
  module-local rather than imported from `sync/consent.py:145`.
- `mypy --strict` clean, `ruff check` clean, no blanket suppressions, ≥90 % coverage on new branches.
- **`ruff format` is NOT clean on this repository** (`line-length = 164`). Only `ruff check` is
  meaningful; a formatting diff is evidence of nothing.
- Terminology canon: **Mission**, never "feature". No version numbers assigned in scope.

**Scale/Scope**: one new source module; **six** existing source files modified (`config.py`,
`local_service.py`, `service.py`, **`saas_service.py`**, `saas_client.py`, `cli/commands/sync.py`,
plus docstring-only edits in `cli/commands/tracker.py`); **five enclosing call sites / six call
expressions** of the new verdict function in `src/`; **six** repo-wide AST guards; an **8-cell**
composition table; a probed set of **exactly 15** values for the round-trip and fault pins (now including a mapping
and a list **at the key**); four new test files plus one repaired existing test class; two
documentation deliverables (CHANGELOG entry, upgrade note) and two follow-up issues filed rather
than absorbed. **`saas_service.py` was absent from the previous revision's scope and is not
optional** — it holds one site that erases the key today and two that this Mission's own field
promotion breaks (`data-model.md` §5).

---

## Charter Check

*GATE: passed before Phase 0 research; re-checked after Phase 1 design. Re-check again after tasks.*

| Charter rule | How this plan satisfies it |
|---|---|
| **ATDD-first / red-first discipline** (Governing Principles; Standing Order 4; C-011) | Every implementation concern names the test that reds first, on what, and why the red is the *consequence* rather than a proxy — see *Red-First Proof Strategy*. The ATDD test is committed before the implementation commit in each WP. |
| **Architectural gate discipline** (Standing Order 5; `DIRECTIVE_043`; `architectural-gate-non-vacuity`) | FR-015's **six** guards assert **exact membership and an exact count** (never `<=`), each prints and asserts its own **non-zero input count**, and each carries a self-mutation proof performed by a `PYTHONPATH`-injected pytest plugin with the killed-pin count reported. G5 is the guard that makes FR-004's polarity structural rather than conventional. |
| **Single canonical authority** (Governing Principles; `DIRECTIVE_044`) | Exactly **one** function computes the two-channel join (FR-003), pinned to exactly five enclosing call sites and six call expressions (FR-015 G4), each passing a literal destination (G5). No new `ConsentLevel` member (algebra mismatch, C-003), no new `EgressConsent` member (registry contract, C-004), no second definition of `project_egress_refusal` (C-008). Chain B — a genuine second answerer for a neighbouring question — is **named and filed**, not absorbed (C-014). |
| **Canonical sources, never improvise** (Standing Order 6) | This plan is filled against `src/doctrine/missions/software-dev/templates/plan-template.md`. No structure was copied from an older mission in `kitty-specs/`. |
| **Campsite cleaning** (Standing Order 2) | The only tidy-first work in scope is what FR-010 forces: `load_tracker_config` may need `preserve_quotes = True` (matching `save_tracker_config` at `config.py:160`) and `clear_tracker_config` needs it too (`config.py:184` builds a third `YAML()` without it, so `unbind` destroys sibling-block quoting today). Blast radius **measured, not assumed**: `from_dict` `str()`-coerces every known string field, so only `_extra` values and the raw `egress` retain the ruamel subclass. Byte-identity is scoped to the `egress:` line. No unrelated refactor of `tracker/config.py` is in scope. |
| **Red-main & release discipline** (Standing Order 9; ADR `2026-07-17-1`) | The known-red roster (C-013) is not chased, not fixed in-PR, and not retried to green. Any **newly** encountered pre-existing failure is filed as a GitHub issue before being treated as baseline (charter Pre-existing Failure Reporting Rule). |
| **Targeted test surface** (Testing Requirements) | Each WP declares its targeted suites; the surfaces are enumerated in *Verification Plan*. The full suite is not this Mission's gate. |
| **Breaking changes documented** (Code Review Checklist) | FR-013 makes the CHANGELOG Breaking Changes entry and the `docs/migrations/` upgrade note **deliverables with an anchor check**, not notes. |
| **Adversarial squad cadence** (Standing Order 1) | A post-specify squad already ran (4 × REJECT, resolutions folded). A post-plan squad is recommended before `/spec-kitty.tasks`; advisory, never a gate. |
| **Git & workflow discipline** (Standing Order 7; `DIRECTIVE_045`) | PRs only; the operator merges. Staging is **explicit-path** (`git add <paths>`), never `git add -A` — 13 files were lost to a stray `add -A` in this lineage. |
| **Terminology canon** | Mission, never "feature". `pytest tests/architectural/test_no_legacy_terminology.py` is run before pushing any prose or doctrine change. |

**No charter violations require justification.** Two items are recorded in *Complexity Tracking*
because a reviewer will reasonably ask about them.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/tracker-egress-refusal-3108-01KYWF1R/
├── spec.md                     # the specification this plan implements
├── plan.md                     # This file
├── research.md                 # Phase 0 output — options considered and rejected
├── data-model.md               # Phase 1 output — the key, the verdict type, the lifecycle
├── tracer-evidence-base.md     # measured facts, authoritative
├── tracer-squad-findings.md    # four-lens squad findings, resolutions, operator decisions
├── research/                   # evidence-log.csv, source-register.csv
├── decisions/                  # decision moments
└── tasks/                      # Phase 2 output (/spec-kitty.tasks — NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── tracker/
│   ├── egress_verdict.py       # NEW — EgressDestination, tracker_egress_verdict(root, *, destination),
│   │                           #       Channel-2 resolver (isinstance-guarded decode), module-local
│   │                           #       sentinel, Channel-1 reporting classifier (debt; retires on B/Q3)
│   ├── egress_consent.py       # UNCHANGED — project_egress_refusal (Channel 1); moves under Bundle B
│   ├── config.py               # `egress` known field + fault, write-side omit, round trip,
│   │                           #       clear_tracker_config retains the key, preserve_quotes (:160, :184)
│   ├── local_service.py        # the gate (3 sites, LOCAL_SUBPROCESS literal), bind preservation, docstring
│   ├── service.py              # bind's local branch hands the loaded config (:163); :98 substitution
│   ├── saas_service.py         # preservation at :266 (erases today) and :219/:316 (FR-002 breaks them)
│   ├── saas_client.py          # _request consults the verdict, HOSTED_SERVICE unconditionally
│   └── factory.py              # UNCHANGED — pinned by guard G1
└── cli/commands/
    ├── tracker.py              # two docstrings amended; no behavioural change
    └── sync.py                 # NEW tracker-egress renderer, ONE ROW PER DESTINATION (:5737 caller)

tests/
├── sync/tracker/               # acceptance (seeded store) + config round-trip suites (new);
│                               #   TestSyncOperations repaired by one committed config line
├── cli/commands/               # sync doctor rendering suite (new) — 7 checkouts x 2 destination rows
└── architectural/              # the six falsity guards (new)

docs/migrations/                # upgrade note + index link + anchor check
CHANGELOG.md                    # Breaking Changes entry
```

**Structure Decision**: single project. All source lands under `src/specify_cli/` in the existing
`tracker/` and `cli/commands/` packages; all tests land under the existing `tests/sync/tracker/`,
`tests/cli/commands/` and `tests/architectural/` directories. No new top-level package is created —
deliberately: `tracker_egress_verdict` and `EgressDestination` are defined **once, in `tracker/`**
(C-008), and Bundle B is the Mission that relocates them (C-009).

**The key's placement was also a decision, and it is recorded** (`research.md` §2, option 6): the
key stays in the `tracker:` block. The alternatives were a top-level `egress:` block owned by no
command — which would have made the whole six-site preservation problem disappear, and was rejected
because it adds a third reader of `.kittify/config.yaml` and moves the key away from the binding it
qualifies — and the `sync:` block, rejected because it drags the key into `CONFIG_FAULT_KINDS`
(pinned by exact equality) and `_render_consent_fault`, which this Mission measured to be wrong
three ways for this content. The accepted cost is stated rather than glossed: preservation at six
sites, a manufactured red, a `preserve_quotes` change in two more places, and an `unbind` that
leaves a binding-named block holding only a consent decision.

---

## Architecture and Data Flow

### The two-channel join

```
        tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)
                          ── src/specify_cli/tracker/egress_verdict.py ──
                                            │
             ┌──────────────────────────────┼──────────────────────────────┐
             │                              │                              │
      CHANNEL 1 (existing)          CHANNEL 2 (new)              DESTINATION (a PARAMETER)
      project_egress_refusal(root)  _resolve_tracker_egress(root)   supplied by the caller
        └ resolve_egress_consent      └ reads tracker.egress from     as a LITERAL member of
          └ permits_egress              the project's own             a closed 2-member set:
        `None` == permission            .kittify/config.yaml            LOCAL_SUBPROCESS
        absence DENIES                  {absent | refused |             HOSTED_SERVICE
                                         permitted | fault(raw)}      NEVER read from config
             │                              │                              │
             └──────────────────────────────┴──────────────────────────────┘
                                            │
                              FR-005's total 8-cell table
                       (Channel-2 value × destination — no short-circuit;
                        BOTH channels are always evaluated, because the
                        granting half must be able to satisfy a path that
                        Channel 1 alone would deny)
                                            │
                                    TrackerEgressVerdict
        refused · refusing_channels (ALL of them) · destination (echoed) · channel-1 state
        · channel-2 state + raw value · operator message · ordered remedies
        (NO binding-kind field; the provider is never read)
                                            │
       ┌────────────────────┬───────────────┴────────────┬─────────────────────────┐
       │                    │                            │                         │
 LOCAL GATES ×3      HOSTED GATE (FR-016)        sync doctor (FR-014) — TWO calls
 (FR-001)            SaaSTrackerClient._request   new renderer beside
 sync_pull/push/run  (:329-331), still BEFORE     _render_consent_readability;
 FIRST EXECUTABLE    _fetch_access_token_sync();  ONE ROW PER DESTINATION;
 STATEMENT, ahead    passes HOSTED_SERVICE        prints in all cases, including
 of _load_runtime;   UNCONDITIONALLY; raises      permitted.
 each passes         TrackerEgressRefusedError,   REPORTS the verdict; never
 LOCAL_SUBPROCESS    unchanged identity           computes a second one
```

**Exactly five enclosing call sites and exactly six call expressions in `src/`**, pinned by exact
membership *and* exact counts (FR-015 G4). Never `<=` — a `<=` assertion passes on a zero-call
scan, which is precisely what happens after Bundle B moves the file. The sixth expression is the
doctor renderer's second destination row; the five *functions* are the three local gates, `_request`
and the renderer. **G5** additionally pins that every one of the six passes an `Attribute` node on
`EgressDestination` — never a `Name`, never a `Call`, never a value read from configuration.

**No `_require_egress` helper.** A helper would satisfy G3's "first executable statement" property
with a call to *the helper*, which stops pinning `tracker_egress_verdict` at the three local sites
altogether. The gate is written out at each site; the duplication is three lines and it is the
duplication the guard exists to check.

### The composition rule, and why it cannot be a short-circuit

Both channels are **always evaluated**. A Channel-1-first short-circuit would refuse a project that
Channel 2 permits — which is the whole of US2 and the dissolution of the *"consent to hosted sync or
lose your local tracker"* coercion the operator rejected. The join is written as one enumerated
**8-cell** table, exercised by one parametrised test that asserts the number of cells it ran is
**exactly 8** (SC-015).

| Channel-2 value | `LOCAL_SUBPROCESS` | `HOSTED_SERVICE` |
|---|---|---|
| `fault` (any present value outside the closed pair) | **refuses** | **refuses** |
| `refused` | **refuses** | **refuses** |
| `permitted` | **permits, independently of Channel 1** | no-op, **reported as a no-op**; Channel 1 decides |
| `absent` (key missing, or a non-mapping `tracker:` block) | defers to Channel 1 | defers to Channel 1 |

**The `none` column is gone.** It existed only to describe a root the function could not classify.
`root=None` is reachable only from `SaaSTrackerClient._request` (`self._project_root` is
`Path | None`), so it is now simply `HOSTED_SERVICE` with Channel 2 absent, and must answer with
text byte-identical to `UNDETERMINED_PROJECT_REFUSAL`.

**A second consequence worth stating: the binding-kind config read disappears.** The previous
revision's verdict read the project config twice — once for `tracker.egress`, once for the provider
— which made a single command perform three reads of one file and made the verdict internally
racy against itself. With the destination supplied, the verdict reads the file **once**. The
remaining gate-versus-`_load_runtime` window is the pre-existing one, unchanged and still recorded.

When more than one channel refuses, `refusing_channels` names **all** of them, so an operator who
clears the tracker key is not surprised by a second refusal.

### Why the destination cannot be derived — the measurement

```
PRECONDITION on-disk provider : 'beads'
SUBJECT backend class         : SaaSTrackerService
SUBJECT in-memory cfg.provider: 'jira'
SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
CONTROL (disk=jira) backend   : SaaSTrackerService
NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
```

`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) substitutes
`TrackerProjectConfig(provider=provider)` in memory and never rewrites the file. Three
operator-reachable commands take that path, all `allow_unbound=True`: `list-tickets --provider`
(`cli/commands/tracker.py:998-1007` → `service.py:220` → `saas_client.py:613` → `_request`),
`issue-search --provider` (`tracker.py:369-386` → `service.py:214`), `map list --provider`
(`tracker.py:942-963` → `service.py:210`). A config-derived polarity reads `beads` on all three,
applies the local half, and turns `tracker.egress: permitted` into an **affirmative grant to
spec-kitty's hosted service with Channel 1 absent**. Pinned by US5 sc4 + SC-005a, structurally by
G5, and by `mypy` at the signature.

### Two vocabularies that must never be conflated

- **Channel-2 value** — `{absent, refused, permitted, fault}`, carrying the raw loaded value.
- **Channel-1 state** — `{no record, recorded refusal, not consentable}`, the **reporting-only**
  triple (FR-012, C-004, `data-model.md` §3).

Every requirement, message and `sync doctor` line names which of the two it means.

### The Channel-1 classifier is reporting-only, and structurally so

The enforced verdict has exactly **one** derivation: `project_egress_refusal` →
`resolve_egress_consent` → `permits_egress`. The three-way Channel-1 state is produced by a separate
classifier that (1) runs **only** on a path whose refusal has already been decided, (2) returns a
label from a closed set of three and can return nothing else, and (3) is pinned non-authoritative by
a test that **forces each of its three labels while Channel 1 actually permits** and asserts the
command still permits, plus one that makes it **raise** and asserts the refusal still prints with
generic wording. Its inputs are `resolve_checkout_sync_routing_readonly(root).project_uuid` and,
when identity resolves, `resolve_project_consent(uuid, checkout_roots=[routing.repo_root]).level` — both imported at call
time inside a guarded block. Using `ConsentDecision.level` **for a message** widens neither
`EgressConsent` nor the `Callable[[Path], bool]` resolver contract. **Bundle B's Q3 stays closed.**

### Why the gate sits ahead of `_load_runtime`, and what a later reader must not do with it

`_load_runtime` is called **synchronously** at `local_service.py:116/131/141`, before the coroutine
that reaches `_build_engine`, and it calls `load_tracker_config`, which **raises**
`TrackerConfigError` on an unparseable file (`config.py:148-149`). With the gate at `_build_engine`,
a refusing project with a broken config would get a traceback instead of its refusal — the property C-021 now pins at the unit level, since `_is_local_binding`'s `with suppress(Exception)` (`cli/commands/tracker.py:280-293`) makes it unreachable through the CLI — and a
refused command would still read the machine-global credential store and construct
`TrackerSqliteStore`, which `mkdir`s and creates a SQLite file with three tables
(`store.py:278-281`). That is why NFR-002 can assert **zero local side effects** and why C-018
records the move back as a decision someone would have to argue for: it produces no egress, so it
would look harmless.

`_load_runtime` itself is **not** the gate site — `map_add` and `map_list` also call it and perform
no egress, so gating there would withdraw local-only commands from a refusing project. `status()`
bypasses it entirely (`local_service.py:81`). `TrackerService._resolve_backend` is bypassed by
`bind()` (`service.py:131-166`). `cli/commands/tracker.py::_service` covers the CLI only, and a gate
in a CLI helper is invisible to any future library caller.

### Data flow of a refused local command, end to end

```
spec-kitty tracker sync push
  └ tracker_callback         is_saas_sync_enabled()  → armed (fixtures set it explicitly)
  └ _check_sync_readiness    _is_local_binding() → short-circuits (unchanged)
  └ _service() → TrackerService.sync_push → _resolve_backend() → LocalTrackerService.sync_push
      └ ▸ GATE  ← FIRST EXECUTABLE STATEMENT (written out here; no helper)
          verdict = tracker_egress_verdict(
              self._repo_root,
              destination=EgressDestination.LOCAL_SUBPROCESS,   ← LITERAL (G5)
          )
          if verdict.refused: raise <LocalTrackerServiceError subclass>(verdict.message)
      └ _load_runtime()          NOT REACHED  → no credential-store read, no SQLite file
      └ _build_engine()          NOT REACHED  → no connector
      └ the credential-named executable   NOT REACHED  → 0 argv, 0 subprocess.run
  └ _run_or_exit catches RuntimeError → red text on stderr, exit 1
```

And the hosted counterpart, which cannot be anything but hosted:

```
spec-kitty tracker list-tickets --provider jira      (on-disk provider may be `beads`)
  └ _service(allow_unbound=True) → TrackerService.list_tickets   (service.py:220)
      └ _resolve_saas_backend_for_provider('jira')               (service.py:84-98)
          ↳ overrides cfg.provider IN MEMORY; the file still says `beads`
      └ SaaSTrackerClient.list_tickets (saas_client.py:613) → _request (:329-331)
          └ ▸ GATE: tracker_egress_verdict(
                        self._project_root,
                        destination=EgressDestination.HOSTED_SERVICE,  ← UNCONDITIONAL LITERAL
                    )
          └ _fetch_access_token_sync()   NOT REACHED on refusal
```

`LocalTrackerServiceError` is already a `RuntimeError` subclass (`local_service.py:27`), so
`_run_or_exit` (`tracker.py:346-351`) prints it and exits 1 with no change to that helper. The two
refusal exception hierarchies are **not** unified — the *verdict* is (FR-012).

---

## Affected Surfaces

Every file, with what changes in it. Line numbers are as measured at `bb2020fea`.

### Source

| Path | Change | Requirements |
|---|---|---|
| `src/specify_cli/tracker/egress_verdict.py` | **NEW.** `EgressDestination` (closed 2-member enum); `tracker_egress_verdict(root: Path \| None, *, destination: EgressDestination)`; the verdict value object; Channel 2's resolver with the **`isinstance`-guarded** decode; the module-local absence sentinel; the Channel-1 reporting classifier (**debt**, retires on Bundle B Q3, offers `checkout_roots=[routing.repo_root]`); message and remedy composition. Holds the Mission's **only** module-level import of `project_egress_refusal`. Advertises only names with a real `src/` consumer in `__all__` (the symbol-level dead-code gate is shrink-only). | FR-003, FR-004, FR-005, FR-006, FR-007, FR-012, NFR-003, C-001, C-002, C-004, C-008 |
| `src/specify_cli/tracker/config.py` | `egress` added to `_KNOWN_KEYS` (`:69-72`). `TrackerProjectConfig` gains a field carrying the **raw loaded value plus a derived fault** — never a narrowed `enum \| None` or `bool \| None`. `from_dict` distinguishes "key missing" from "key holds `null`" with the module-local sentinel. `to_dict` **omits** `egress` entirely when nothing is recorded (never a written-out `null`). `load_tracker_config` may gain `preserve_quotes = True`, matching `save_tracker_config` at **`:160`**. `clear_tracker_config` (`:178-194`) replaces its unconditional `del payload["tracker"]` with: retain a `tracker:` block holding only a recorded `egress`; delete the block entirely when none is recorded — **and gains `preserve_quotes` on the third `YAML()` at `:184`**, which today makes `unbind` destroy quoting in sibling blocks. | FR-002, FR-009, FR-010, FR-011 (C), C-001, C-020 |
| `src/specify_cli/tracker/local_service.py` | The gate as the **first executable statement** of `sync_pull` (`:115`), `sync_push` (`:130`) and `sync_run` (`:140`), ahead of `self._load_runtime()`, each passing `destination=EgressDestination.LOCAL_SUBPROCESS` as a literal, **written out at each site — no helper**. `bind` (`:47-63`, construction at `:57`) loads the committed config first and carries `egress` and `_extra` forward. A new `LocalTrackerServiceError` subclass for the refusal. Module docstring (`:8`) amended: *"No SaaS imports live here"* must record that the file now consults the egress verdict. | FR-001, FR-011 (A1), FR-012, FR-015 G3/G5, FR-017, NFR-002, NFR-004 |
| `src/specify_cli/tracker/service.py` | `bind`'s local branch (`:163`) hands `LocalTrackerService` the **loaded** config instead of `TrackerProjectConfig()`, matching the SaaS branch above (`:142-145`). **And** `_resolve_saas_backend_for_provider` (`:98`) stops substituting a bare `TrackerProjectConfig(provider=provider)` whose `_extra`/`egress` are empty — **defence-in-depth only**: measured, `_persist_binding`'s three call sites (`saas_service.py:347,412,505`) are all inside bind flows entered from `TrackerService.bind` (`:141-145`), `_resolve_saas_backend_for_provider` serves only the three read paths (`:210,214,220`), and `apply_binding_upgrade` (`saas_service.py:191`) has zero callers in `src/`. **No red-first pin exists for this site**; assert it at the unit level against the substituted object. | FR-011 (A2, A4) |
| `src/specify_cli/tracker/saas_service.py` | **NEW to scope, and not optional.** `bind` (`:266`) builds a bare `TrackerProjectConfig(provider=…, project_slug=…)` and saves — **measured to erase a committed `egress` today**. The upgrade path (construction `:206`, carry `:219`) and `_persist_binding` (construction `:303`, carry `:316`) preserve `egress` **only because it rides in `_extra`**, and FR-002's promotion to `_KNOWN_KEYS` (`config.py:107` excludes known keys from `_extra`) **destroys that mechanism** — these were cited by the previous revision as *the pattern to copy*, and they are the lines this Mission breaks. `unbind` (`:281`) resets `self._config` to an empty config in memory, which a later `_persist_binding` on the same instance would write back, undoing site C; reset it to `load_tracker_config(self._repo_root)` instead. All four gain an explicit carry. Both construction and carry lines are cited so the `grep` the inventory instructs and the citations agree. | FR-011 (A3, B1, B2, D) |
| `src/specify_cli/tracker/saas_client.py` | `_request` (`:329-331`) consults `tracker_egress_verdict(self._project_root, destination=EgressDestination.HOSTED_SERVICE)` instead of `project_egress_refusal` directly. **The destination literal is unconditional** — no branch, no provider read. Position **before** `_fetch_access_token_sync()` unchanged. `TrackerEgressRefusedError` keeps its identity and base class. `SaaSTrackerService` and every other line of the file untouched. `self._project_root` is `Path \| None`, so the verdict must accept `None` and reproduce `UNDETERMINED_PROJECT_REFUSAL` byte-identically. | FR-016, C-002, C-016, SC-016 |
| `src/specify_cli/cli/commands/tracker.py` | `_check_sync_readiness` (`:296-312`) and `_check_binding_readiness` (`:315-324`) docstrings amended — the claim that local providers *"reach the sync command without going through the SaaS surface at all"* becomes false the moment the local path consults the hosted-sync consent chain. **No behavioural change**; `_is_local_binding`'s short-circuit is unchanged. | FR-017, SC-019 |
| `src/specify_cli/cli/commands/sync.py` | A **new** renderer for the tracker-egress verdict, placed beside `_render_consent_readability` (`:1736`) and called from `doctor()` (**`:5737`**, already `# noqa: C901`) immediately after it. Printed **unconditionally**, including the permitted case, with **one row per `EgressDestination` member** — two calls to the verdict, each with a literal — and **no provider read** deciding what to show. **Not** routed through `_render_consent_fault` (`:1711-1733`), **not** added to the per-project Consent column (`_per_project_store_table`, `:1429-1473`), and `CONFIG_FAULT_KINDS` is **not** extended. The new block must never print `_CONSENT_FAULT_NOT_ABSENCE`'s *"This is NOT a missing consent record"* and must contribute **0** to `flat.count("REPAIR THE FILE'S SYNTAX")`. | FR-014, SC-014 |
| `src/specify_cli/tracker/factory.py` | **Unchanged** — pinned by guard G1 (`set(SUPPORTED_PROVIDERS) == {"beads", "fp"}`). Recorded here because the guard makes it a surface. | FR-015 G1, C-006 (1) |

### Documentation

| Path | Change | Requirements |
|---|---|---|
| `CHANGELOG.md` | Breaking Changes entry: `beads`/`fp` bindings now require a recorded decision at one of the two channels; absence of both denies. Links the upgrade note. **No version number is assigned in scope.** | FR-013, SC-018 |
| `docs/migrations/<upgrade-note>.md` | All remediation paths, including the Channel-2 grant — the only one that works without a project identity — and the remaining one-direction limitation for SaaS bindings (C-016). Carries a stable anchor. | FR-013, C-016, SC-018 |
| `docs/migrations/index.md` | Link to the upgrade note. | FR-013 |

### Tests

Filenames are indicative; the placement is not.

| Path | Change | Requirements |
|---|---|---|
| `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (**new**) | The acceptance suite: US1–US6, all three entry points, the fake-`bd` recorder, the executed-remedy tests, the bind counter, the negative pin against `saas_sync_disabled_message()`. Patches `_build_engine`, `build_connector`, `SyncEngine`, `LocalTrackerService` and `TrackerService` **nowhere**. | FR-018, NFR-001, NFR-002, NFR-004, SC-001–SC-007, SC-011–SC-013 |
| `tests/sync/tracker/test_tracker_egress_config_3108.py` (**new**) | The Channel-2 data layer: the probed-set round trip through `bind`, the `unbind` preservation in both directions with the sibling `sync:` block as control, the no-null-planting pin, the fault-message pin naming the offending value and both legal values. | FR-002, FR-009, FR-010, FR-011, C-020, SC-008–SC-010 |
| `tests/cli/commands/test_sync_doctor_tracker_egress_3108.py` (**new**) | Seven distinguishable renderings; the block printed in all seven; the rendered verdict asserted equal **field-for-field** to the enforced verdict for the same checkout. | FR-014, SC-014 |
| `tests/architectural/test_tracker_egress_guards_3108.py` (**new**) | G1–**G6**, each an **analyzer callable** invoked twice — against `src/` and against synthetic mutated source held in the test — with exact membership, exact count, a printed non-zero input count and the killed-pin count reported; no source is edited during a verification run. Matchers resolve **both `ast.Name` and `ast.Attribute` func nodes**. G4 and G5 each kill **three** mutants: a config-derived `destination` name, swapped literals, and a **module-qualified sixth call site** (the form measured to pass an `ast.Name`-only matcher). G6 kills one: a provider read reintroduced into `egress_verdict.py`. | FR-015, SC-017 |
| `tests/sync/tracker/test_local_service.py` | `TestSyncOperations` (`:235,262,287`) goes **red** under the gate. Repaired by a committed `tracker: {egress: permitted}` in the fixture repo — **not** by patching out the gate. `_build_engine` stays patched only for its own delegation assertions. **This repair is order-dependent on FR-011** — see *Sequencing*, Stage 2. | C-012 (1), SC-020 |
| `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | **Detection signal, not a planned edit.** `:366`'s `flat.count("REPAIR THE FILE'S SYNTAX") == 4` must **stay 4**. If it moves, that is evidence the new block routed through the fault renderer — a defect, not a repair. (The brief anticipated this test moving; `spec.md` FR-014 / US7 sc5 / SC-014 require the count to be unchanged. This plan follows the spec — see *Open Items*.) | FR-014, US7 sc5 |
| `tests/specify_cli/tracker/test_binding_report_only.py` | **Detection signal, not a planned edit.** `:254-268`'s `test_apply_binding_upgrade_preserves_extra_fields` asserts `svc._config._extra == {"future_flag": True}` — the forward-compat `_extra` contract at **`saas_service.py:219`, the exact line B1 modifies**. It must stay green: `_extra` keeps carrying `future_flag` after `egress` stops riding in it. If it reds, the B1 fix **replaced** the `_extra` carry instead of adding an `egress` carry beside it. **Do not weaken the assertion to "repair" it.** | FR-011 (B1), C-012 (5) |
| `tests/specify_cli/sync/test_worktree_clean_invariant.py` | **Untouched.** `:22` documents the `apply_binding_upgrade` / `bind` write boundary this Mission now writes through. Listed so the boundary is not widened in passing. | FR-011, C-012 (5) |
| `tests/sync/test_consent_fault_vocabulary_3030.py` | **Untouched.** `:261` pins `CONFIG_FAULT_KINDS` by exact equality; the set is not extended. Listed as blast radius so nobody "repairs" it. | C-012 (3), FR-014 |
| `tests/architectural/test_egress_consent_boundary.py` | **Untouched.** `local_service.py` holds zero HTTP sinks (measured: 0, against a control of 8 in `saas_client.py`, over 1198 scanned files) and therefore **cannot** be allowlisted — `test_every_listed_file_still_holds_a_sink` (`:792-805`) deletes entries that guard nothing. **No `_baselines.yaml` bump** (`egress_allowlist_files: 28`) is needed or permitted. The same applies to the new `egress_verdict.py`. | C-010 |

---

## Complexity Tracking

*Two items a reviewer will reasonably challenge, recorded rather than left to be re-litigated.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| A **second** consent key and a **new module** in a tree whose governing principle is single canonical authority | Two invariants, not two representations of one: hosted-sync consent must be answerable for a project whose checkout has moved, been renamed or deleted (hence a uuid and a machine-global index); the tracker question is only ever asked with the checkout in hand (C-005, C-006 precondition 3). One key answering both is Gap A itself. FR-003 keeps the *join* single-authority: exactly one function, exactly five enclosing call sites and six call expressions, each passing a literal destination, all guarded (G4, G5). | Reusing `sync.enabled` does not close Gap A. A new `ConsentLevel` member fails on **algebra** — `PROJECT_CONSENT_PRECEDENCE` is walked first-level-that-answers-wins, so a tracker key inserted there would *answer the hosted-sync question*, verbatim the `sync.auto_start` failure mode at `consent.py:52-56`; this Mission needs an AND-conjunct. A new `EgressConsent` member fails on the **registry contract** — `Callable[[Path], bool]` (`adapters.py:81`) manufactures the member from a bool, so it cannot exist without widening the callable, which forces Bundle B's Q3. Both rejections were steelmanned by two squad lenses and both survived (C-017 (3)). |
| **Chain B is left in place** — a genuine second answerer to "may this data leave", live on a real egress gate | `sync/routing.py:178-252` → `is_sync_enabled_for_checkout` answers hosted-sync **fan-out**, not tracker egress; its blast radius is the drain and the daemon. Folding it in would be a second Mission wearing this one's branch. This Mission adds **no third answerer** — Channel 1 reuses `project_egress_refusal` → Chain A. | Absorbing it now would put the drain, the daemon (`sync/runtime.py:106`) and `sync/batch.py:1070` inside a Mission whose acceptance harness is built around a tracker subprocess recorder. **A follow-up issue is filed** (C-014) — framed as ***"finish `#3030` FR-031's migration at the two remaining enforcement sites"***, not as "consolidate two chains", because the second framing is what got it deferred last time. See *Out of Scope and Follow-Ups to File* for the content it must carry. |

**Not a violation, recorded so it is not mistaken for one:** `doctor()` (`sync.py:5737`) already
carries `# noqa: C901`. This Mission adds **one call** to it and puts all new branching in a
separate renderer function, so the complexity ceiling of 15 is respected rather than nudged.

**Corrected 2026-08-01 — there is no per-destination loop.** An earlier draft of this row said the
renderer holds "the per-destination loop". That contradicts Open Item 11, FR-003's six-call-expression
count and guard G5: a loop variable is an `ast.Name` node, and G5 requires every `destination`
argument to be an `Attribute` on `EgressDestination`, so the loop form **reds G5**. The renderer
writes **two literal calls**, one per destination. The duplication is deliberate and is precisely
what the guard exists to check — the same trade this plan makes at the three local gate sites in
refusing a `_require_egress` helper. The renderer's own branching (row composition, the
not-applicable rendering for a `permitted` on a hosted destination) is what keeps it a separate
function; the two verdict calls are not the reason.

---

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become multiple WPs;
> multiple small concerns may merge into one WP. Do not label concerns with WP-style IDs or
> sequencing language.

### IC-01 — Acceptance harness and the measurement contract

- **Purpose**: Build the harness that makes every later absence assertion mean something, and prove
  it on the **un-gated** tree, where its positive control must already pass.
- **Relevant requirements**: FR-018 (H1–H7), NFR-001, NFR-002, NFR-004, SC-011, SC-012, SC-013, SC-020
- **Affected surfaces**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (new); a fake `bd`
  executable written to disk per fixture and named through the machine-global credential file
  (`factory.py:56` — `command=str(credentials.get("command") or "bd")`)
- **Sequencing/depends-on**: **none** — this is one of the Mission's two independent roots
- **Risks**: **All four measured false-greens live here.** **H1** — every fixture pins
  `doctrine: {mode: spec_kitty_authoritative}`, because under the default `external_authoritative`
  (`tracker/config.py:39`) `local_can_write("title")` is `False` and `SyncEngine.push` skips without
  calling `create_issue`. **H2** — the recorder **is** the fake executable on disk, named through the
  credential file; there is **no** `SubprocessCommandRunner` injection seam (not in `__all__`,
  `build_connector` passes no runner); `_build_engine`, `build_connector`, `SyncEngine`,
  `LocalTrackerService` and `TrackerService` are un-patched. POSIX-scoped with a documented skip on
  Windows. **H3** — every fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` explicitly and asserts refusal
  **text**, never merely a non-zero exit. **H4** — a delegating wrapper (never a stub) on the name
  `local_service` binds the verdict under, with the counter asserted non-zero in every acceptance
  test and one test proving the wrapper changes no outcome. **H8 (new, measured)** — the tracker
  store is **seeded** with the sentinel issue before every push/run case, via
  `store.upsert_issue(CanonicalIssue(...))`. `SyncEngine.push` iterates
  `store.list_issues(system=…)`, so an empty store never reaches `create_issue`:
  `### EMPTY STORE ### {'pushed_created': 0} · 1 argv · sentinel False` versus
  `### SEEDED STORE ### {'pushed_created': 1} · 3 argv · sentinel True`. **A fixture satisfying H1,
  H2 and H3 but not H8 still captures zero sentinel argv on the un-gated tree** — the shape of a
  passing refusal test with nothing behind it. Expected consenting argv count is **3** (`list`,
  `create`, `show`), not 2: `BeadsConnector.create_issue` ends with a `get_issue`
  (`spec_kitty_tracker/connectors/beads.py:151-153`). Seed `status=CanonicalStatus.TODO` or `IN_PROGRESS`.
  Measured across all six `CanonicalStatus` members: those two give **3** argv; every other member
  gives **5** (`list`, `create`, `update`, `show`, `show`), because `transition_issue` contributes an
  `update` **and** its own `show`. The band is right; the arithmetic is **two** extra argv, not one.

### IC-02 — Channel 2's key: shape, fault, and byte-identical round trip

- **Purpose**: Make `tracker.egress` a first-class known field whose recorded value cannot be
  silently replaced by a default, and whose absence stays spelled as the key being missing.
- **Relevant requirements**: FR-002, FR-006, FR-009, FR-010, C-001, C-019, C-020, SC-008, SC-010
- **Affected surfaces**: `src/specify_cli/tracker/config.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py` (new)
- **Sequencing/depends-on**: **none** — this is the Mission's second independent root
- **Risks**: A narrowed field type is the measured trap — on the `doctrine.mode` precedent a known
  field with an unusable value comes back as its **default** on read, which would convert a refusing
  project into a permitting one at the next `bind`. The field carries the **raw value plus a derived
  fault**. `preserve_quotes = True` on `load_tracker_config` may be required for byte-identity; its
  blast radius is **narrower than previously claimed and was measured**: `from_dict` `str()`-coerces
  every known string field, so only `_extra` values and the raw `egress` retain the ruamel subclass.
  Promoting `egress` to `_KNOWN_KEYS` **creates** the null-planting defect FR-009 then closes — see
  *Red-First Proof Strategy* — **and simultaneously breaks the two `_extra`-carrying preservation
  sites at `saas_service.py:219,316`**, which is why IC-02 and IC-03 land together (below).

### IC-03 — A recorded decision outlives its binding

- **Purpose**: Stop `bind`, rebind and `unbind` erasing a committed decision, at **all** the sites
  that reach disk. Erasing a `refused` is a **silent fail-open**; erasing a `permitted` silently
  withdraws a working local binding.
- **Relevant requirements**: FR-011, SC-009
- **Affected surfaces**: `local_service.py` (`bind`, construction at `:57`); `service.py` (`:163`
  and `:98`, the latter defence-in-depth only); **`saas_service.py` (`:266`; `:206`/`:219`;
  `:303`/`:316`; `:281`)**; `config.py`
  (`clear_tracker_config`, `:178-194`, plus `preserve_quotes` at `:184`);
  `tests/sync/tracker/test_tracker_egress_config_3108.py`
- **Sequencing/depends-on**: IC-02 — **and it is the same change set, not a following one** (below)
- **Risks**: The inventory is **nine** construction sites, not three, and it was re-derived from
  `grep -n "TrackerProjectConfig(" src/` rather than recalled. Three erase today (`local_service.py:57`,
  `service.py:163`, **`saas_service.py:266` — measured**), one is **defence-in-depth with no
  production write path and therefore no red-first pin** (`service.py:98`), one is library-caller
  reachable only (`saas_service.py:281`, `unbind`'s in-memory reset, which a later `_persist_binding`
  would write back over site C's fix), two never reach `save_tracker_config` at all
  (`origin.py:536`, `config.py:142`),
  **two work today and are broken by IC-02** (`saas_service.py:219,316` — they preserve `egress` only
  because it rides in `_extra`, and `config.py:107` excludes known keys from `_extra`). **This is why
  the claim that the data-layer stage has "no blast radius" was wrong**: the promotion is precisely
  what breaks the two SaaS sites, and those two were cited by the previous revision as the pattern to
  copy. Pins run in **both** directions (`refused` and `permitted`) at every site, with the sibling
  `sync:` block asserted present as the control. **This concern gates IC-05's blast-radius repair
  criterion** — see *Sequencing*, Stage 2.

### IC-04 — The verdict: one function, one message, never raising

- **Purpose**: Compose the two channels and the caller-supplied destination into a single value object that both
  gates raise from and `sync doctor` renders, so the enforced and the reported answers cannot
  disagree.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-012, NFR-003, C-002,
  C-003, C-004, C-005, SC-015
- **Affected surfaces**: `src/specify_cli/tracker/egress_verdict.py` (new) — including its **module
  docstring** and the **classifier's docstring**, which are named deliverables carrying the debt's
  cause (`invocation/adapters.py:81`), its retirement condition (Q3 → **delete, not migrate**, both
  pins named) and the unregistered-consumer note, because Bundle B's implementer reads `src/` and
  never reads `kitty-specs/`
- **Sequencing/depends-on**: IC-02
- **Risks**: **NFR-003** — the function must never raise, for every probed shape **including a
  mapping and a list at the `egress` key** (a bare `raw in _LEGAL` raises
  `TypeError: unhashable type` for both; the decode is `isinstance(raw, str) and raw in _LEGAL`),
  an unparseable file, a non-mapping `tracker:` block, `chmod 000`, an absent file, `root=None`, and
  a `repo_root` that is not a project root — for **both** destinations; and it must hold **no
  import-time dependency on `specify_cli.sync`**. The Channel-1 classifier must be pinned
  **non-authoritative** by tests that force each of its three labels while Channel 1 permits, and by
  one that makes it raise; it must offer `checkout_roots=[routing.repo_root]`, pinned equal to the
  registered resolver's root **for a checkout invoked from a subdirectory**; and it is recorded as
  **debt that deletes when Bundle B's Q3 gives the resolver port a decision return value**. Polarity
  is **not a free parameter** (C-002), and neither is the destination: a call site that computes it
  from configuration is out of contract even when its answers happen to be right — **and so is a
  provider read inside the function's own body**, which G6 forbids. **Complexity is a design
  constraint here, not a lint outcome:** a conservative feature-complete single function measures
  `C901 17 > 15`, so the 8-cell join is a module-level `_JOIN` mapping of exactly 8 entries (which
  also makes "exactly 8 cells" a *structural* pin, `len(_JOIN)`) and the decode, both channels, the
  classifier and the message composition are separate helpers, each ≤ 3.

### IC-05 — The local gate: the breaking change

- **Purpose**: Close Gap B. Three call sites, first statement of each, ahead of `_load_runtime`.
- **Relevant requirements**: FR-001, FR-012, FR-017, NFR-001, NFR-002, NFR-004, C-018,
  SC-001–SC-004, SC-006, SC-007, SC-019, SC-020
- **Affected surfaces**: `src/specify_cli/tracker/local_service.py`;
  `src/specify_cli/cli/commands/tracker.py` (docstrings only);
  `tests/sync/tracker/test_local_service.py` (`TestSyncOperations` repaired)
- **Sequencing/depends-on**: IC-01, IC-03, IC-04
- **Risks**: Known blast radius — three tests go red and are repaired by **one committed config
  line**, never by patching out the gate. Three docstrings become false at this moment and are
  amended in the same change. `LocalTrackerServiceError` is already a `RuntimeError` subclass, so
  `_run_or_exit` needs no change. The `map_add`/`map_list`/`status` paths stay ungated deliberately —
  they construct no connector and run no subprocess.

### IC-06 — The hosted gate: Channel 2 as a narrowing conjunct only

- **Purpose**: Make the tracker key refuse at `HOSTED_SERVICE` while granting nothing there, without
  perturbing the shipped `#3030` behaviour by one byte — **including when the hosted transport was
  selected by `--provider` from a repository whose on-disk provider is local.**
- **Relevant requirements**: FR-004, FR-016, C-002, C-016, SC-005, SC-005a, SC-010, SC-016
- **Affected surfaces**: `src/specify_cli/tracker/saas_client.py` (`:329-331` only)
- **Sequencing/depends-on**: IC-04, IC-05
- **Risks**: This is the highest-consequence edit in the Mission and the one with the least new value
  — it changes no verdict for any Channel-1 state. The three measured Channel-1 outcomes must
  reproduce **byte-identically**, plus `root=None` → `UNDETERMINED_PROJECT_REFUSAL`. The destination
  literal is **unconditional**; a branch here would be exactly the defect G5 exists to catch.
  **Landing alone is a necessity, not a preference** (see *Sequencing*, Stage 5), because a red in
  `tests/sync/tracker/test_saas_client_consent_gate_3030.py` must be attributable to the swap and to
  nothing else. **Patch-target note for anyone writing a mutation here:** before this change the
  deciding name is `specify_cli.tracker.saas_client.project_egress_refusal`; **after** it, it is
  `specify_cli.tracker.saas_client.tracker_egress_verdict`. A recipe naming only the first is
  correct on the base and inert on the delivered tree.

### IC-07 — `sync doctor` reports the same verdict the gate enforces

- **Purpose**: Make a tracker-egress refusal discoverable without running the command that fails.
  `doctor` reported healthy throughout the 2026-07-27 incident.
- **Relevant requirements**: FR-014, C-020, SC-014
- **Affected surfaces**: `src/specify_cli/cli/commands/sync.py`;
  `tests/cli/commands/test_sync_doctor_tracker_egress_3108.py` (new)
- **Sequencing/depends-on**: IC-04 — **note this concern is schedulable much earlier than its stage
  position suggests**; it is placed late only so that G4's membership set is stable when IC-08 lands
- **Risks**: `_render_consent_fault` is measured wrong three ways for this content and must not be
  reused; `CONFIG_FAULT_KINDS` must not be extended; the per-project Consent column is hard-coded
  binary and has nowhere to put a second *decision*. **The block prints one row per destination and
  never reads the provider** — a provider-conditional rendering would confirm `permitted` as in force
  to an operator whose `list-tickets --provider jira` is refused, which is the exact false-green
  shape this Mission exists to close, with the sign flipped. `sync doctor` is the right surface for a
  **structural** reason: the `spec-kitty tracker` group is conditionally registered
  (`cli/commands/__init__.py:238-243,300`) and does not exist unless armed, while `sync` is
  registered unconditionally (`:298`) — a tracker-side diagnostic would be unreachable in exactly the
  configuration where an operator most needs it. **This concern must land alone**, for the same
  reason IC-06 must: its detection signal is a **count assertion over the whole rendered output**
  (`test_sync_doctor_consent_health_3030.py:366` must stay exactly `4`), and a count over shared
  output cannot attribute a movement to one of two co-landing changes.

### IC-08 — Falsity guards, repo-wide, exact, non-vacuous

- **Purpose**: Make the properties a future change can silently break structural rather than
  test-dependent.
- **Relevant requirements**: FR-015 (G1–**G6**), C-002, C-006, C-009, C-010, SC-017
- **Affected surfaces**: `tests/architectural/test_tracker_egress_guards_3108.py` (new)
- **Sequencing/depends-on**: IC-05, IC-06, IC-07 — **G4's exact-membership assertion is only
  satisfiable once all five enclosing call sites exist**
- **Risks**: A guard written earlier would be edited by every later stage, and a guard whose own
  history is a series of edits proves nothing. Each guard asserts exact membership **and** an exact
  count, prints and asserts its own non-zero input count, and is killed by a `PYTHONPATH`-injected
  pytest plugin with the killed-pin count reported. **Never `<=`** — it passes on a zero-call scan,
  which is what happens after Bundle B moves the file. **G5 is the guard that carries FR-004**: it
  asserts every call expression's `destination` argument is an `Attribute` on `EgressDestination`
  (never a `Name`, never a `Call`), and — **the load-bearing clause** — that `_request`'s is always
  `HOSTED_SERVICE` while the three local sites' are always `LOCAL_SUBPROCESS`. (Its set-equality
  clause carries little alone: the doctor renderer supplies both members by itself.) **Its matcher
  must resolve `ast.Attribute` func nodes as well as `ast.Name`** — measured, a module-qualified
  sixth call site passes an `ast.Name`-only matcher on both G4 and G5. Three mutants: config-derived
  name, swapped literals, module-qualified call site. **G6** additionally forbids any provider read
  inside `egress_verdict.py` (empty expected set, input count = AST nodes scanned), because G5
  guards the call sites and the original defect lived in the body. Every guard is an **analyzer
  callable** invoked twice — against `src/` and against synthetic mutated source — so no source is
  edited during a verification run.

### IC-09 — The breaking change as a deliverable

- **Purpose**: Carry the upgrade cost in the three places an operator will actually look.
- **Relevant requirements**: FR-013, C-016, SC-018
- **Affected surfaces**: `CHANGELOG.md`; `docs/migrations/<note>.md`; `docs/migrations/index.md`;
  an anchor check in CI (the `#3030` FR-018 pattern)
- **Sequencing/depends-on**: **split into two deliverables, because they have different owners in
  time.** *(a)* the **CHANGELOG Breaking Changes entry** is authored **in the same change as IC-05**,
  so the break never lands undocumented; *(b)* the **upgrade note, its `index.md` link and the CI
  anchor check** follow **IC-06**, because only then is the remaining `HOSTED_SERVICE`-side
  limitation's exact shape fixed. The previous revision's diagram put all of IC-09 at the end while
  its prose said the entry lands with the break; the diagram was wrong and is corrected.
- **Risks**: The note must give the Channel-2 grant as a remedy — it is the **only** one that works
  without a project identity — and must state the remaining one-direction limitation at
  `HOSTED_SERVICE` (C-016) as a decided limitation, not an oversight. Run
  `pytest tests/architectural/test_no_legacy_terminology.py` before pushing prose.

### IC-10 — Follow-ups filed rather than absorbed

- **Purpose**: Keep live defects out of this Mission's branch without losing them.
- **Relevant requirements**: C-013, C-014, C-015
- **Affected surfaces**: none in this repository — GitHub issues only
- **Sequencing/depends-on**: none. **Stated once, here, and nowhere contradicted: the issues are
  filed *before implementation starts*.** Not "at any point", not "at the end".
- **Risks**: All are tempting to fix in passing. See *Out of Scope and Follow-Ups to File* for the
  exact content each issue must carry — in particular the Chain B issue, whose framing is what
  determines whether it gets done or deferred.

### IC-11 — Quality gates, typing, and the citation revalidation

- **Purpose**: Own the requirements that would otherwise be nobody's. NFR-005 was the one requirement
  no concern's list named, which is how a quality gate stops being run.
- **Relevant requirements**: **NFR-005**, C-011 (measurement discipline and citation revalidation)
- **Affected surfaces**: all new and modified source; the dossier's ~40 line citations
- **Sequencing/depends-on**: the revalidation half runs **first, in Stage 0**; the gate half runs
  continuously and is re-checked at each stage exit
- **Risks**: `mypy --strict` is not a lint step in this Mission — the `EgressDestination` parameter
  is the mechanism by which FR-004's polarity becomes type-checked, so a `mypy` error on a
  `destination` argument is a **contract** failure. `ruff format` is **not** clean on this repository
  (`line-length = 164`); only `ruff check` is meaningful. Coverage ≥90 % on new branches must come
  from focused tests executing the new helpers directly, not from the acceptance suite alone.

---

## Sequencing and Dependencies

Sequencing matters more than usual here because **every hazard in this Mission produces a green
suite with no gate**, and each one is invisible unless something earlier established what the
non-vacuous result looks like. Each stage below names what would otherwise be **unprovable**.

**The dependency structure is a graph, not a chain**, and publishing it as a chain hid two facts a
scheduler needs: there are **two independent roots**, and one concern (IC-07) is schedulable far
earlier than its stage position. The `depends-on` fields in the *Implementation Concern Map* are the
authority; this is their transitive closure.

```
Stage 0   base pinned · citations revalidated · baselines re-measured with predicted deltas
          │
          ├──────────────────────────────┬───────────────────────────────┐
          ▼  ROOT 1                       ▼  ROOT 2                       │
    IC-01 acceptance harness        IC-02 Channel-2 field shape           │
    (no deps)                       (no deps)                            │
          │                               │                              │
          │                               ▼                              │
          │                         IC-03 preservation, 6 sites          │
          │                         (SAME change set as IC-02 —          │
          │                          the promotion breaks 219/316)       │
          │                               │                              │
          │                               ▼                              │
          │                         IC-04 tracker_egress_verdict ────────┤
          │                               │              │               │
          └───────────────┬───────────────┘              │               │
                          ▼                              ▼               │
                    IC-05 LOCAL GATE  ◀── breaking    IC-07 sync doctor  │
                          │      │          change    (dep: IC-04 only;  │
                          │      │                     schedulable here) │
                          │      └──▶ IC-09(a) CHANGELOG entry           │
                          │            — SAME change as IC-05            │
                          ▼                              │               │
                    IC-06 hosted gate  ── ALONE ─────────┤               │
                          │                              │               │
                          ├──▶ IC-09(b) upgrade note + anchor check      │
                          │                              │               │
                          └──────────────┬───────────────┘               │
                                         ▼                               │
                                   IC-08 falsity guards G1–G6            │
                                   (needs all 5 call sites)              │
                                                                         │
    IC-10 follow-up issues ── filed BEFORE implementation starts ────────┤
    IC-11 quality gates + citation revalidation ── Stage 0, then continuous
```

**Ordering claims, separated by strength** — because the previous revision labelled a *necessity*
and a *preference* identically:

| Claim | Kind | Why |
|---|---|---|
| IC-06 lands **alone** (nothing else in the same change) | **necessity** | Its detection signal is a byte-comparison against the shipped `#3030` refusal strings; a co-landing change makes any difference unattributable. |
| IC-07 lands **alone** | **necessity** | Same shape of argument: its detection signal is a **count assertion over the whole rendered output** (`…:366` must stay `4`). Counts over shared output cannot attribute. *(The previous revision made this argument for IC-06 and not for IC-07; the argument transfers verbatim.)* |
| IC-06 lands **after** IC-05 | **preference** (risk ordering) | Nothing technical requires it; it is preferred so the verdict function is already exercised by the local path before the shipped gate is touched. **Annotated as `risk-ordering` on the `WP05 -> WP04` edge in `wps.yaml`**, so the board does not present it as a necessity the way an unqualified `dependencies:` list otherwise would. |
| IC-07 lands **after** IC-06 | **preference** (risk ordering) | **Its only technical dependency is IC-04, the verdict function** — stated in the diagram above and repeated in WP06's own prompt. Chaining it behind the hosted gate buys stability of G4's membership set when IC-08 lands, which **IC-08's own dependencies already guarantee**, and it costs a level of critical path. Kept because the doctor renderer's land-alone detection signal is a **count over shared rendered output**, which is easiest to attribute on an otherwise quiet tree. **Annotated as `risk-ordering` on the `WP06 -> WP05` edge in `wps.yaml`**; a scheduler short of parallelism may drop it to IC-04/WP03. |
| `WP04 -> WP02`, `WP07 -> WP04`, `WP07 -> WP05` | **transitively redundant** | Each is implied by another path (`WP04 -> WP03 -> WP02`; `WP07 -> WP05 -> WP04`; `WP07 -> WP06 -> WP05`). Kept explicit because each names a *direct* subject-matter relationship a reader should see, but **none is load-bearing for scheduling**. Annotated as such in `wps.yaml` so a later reader can tell which edges actually constrain the order. |
| IC-02 and IC-03 land **together** | **necessity** | The promotion to `_KNOWN_KEYS` is what breaks `saas_service.py:219,316`. Landing IC-02 alone ships a window where two preservation sites are silently wrong. |
| Data layer **before** the gate | **necessity, on a re-grounded argument** | See Stage 2. |

### Stage 0 — Pin the base, revalidate the citations, re-measure with predictions

**Must precede everything.**

**(0a) Pin and record the base.** Record the **actual base SHA**. Implementation is deferred by
operator instruction, so the base will not be `bb2020fea`, and **every measurement and citation in
this dossier was taken at `bb2020fea`**.

**(0b) Revalidate the citations — roughly forty of them.** Run
`git diff --stat bb2020fea..<base>` over `src/specify_cli/tracker/`, `src/specify_cli/sync/`,
`src/specify_cli/cli/commands/` and `src/specify_cli/invocation/`. Then **re-derive every cited line
by symbol name (`grep`), never by line number.** A line that moved is bookkeeping. **A symbol that
moved *semantically* — a changed signature, a relocated gate, a changed default, a new caller of
`LocalTrackerService` — is a re-plan trigger**, and the correct response is to stop and re-plan, not
to patch the citation and continue. Four drifts were already found *at `bb2020fea` itself* and are
corrected in this revision (`config.py:160` not `:165`; `config.py:39` not `:38`; `sync.py:5737` not
`:5736`; `saas_service.py:219,316` not `:220,317`) — which is the evidence that this step is
necessary rather than ceremonial.

**(0c) Re-measure the baselines, each against its prediction.** Inheriting numbers across a base
change is the tautology the worktree rule exists to prevent; re-measuring *without a prediction* is
almost as bad, because there is nothing for the new number to fail against.

| Suite | `bb2020fea` | Predicted at the new base — **direction and cause, not just "movement"** |
|---|---|---|
| six consent/boundary suites | `154 passed in 51.31s` | **increases**, by exactly the tests `#3113` adds to `tests/architectural/test_egress_consent_boundary.py`. A **decrease** is a stop-and-attribute event; so is **any** movement when `#3113` has *not* landed. |
| `tests/architectural/test_egress_consent_boundary.py` alone | `27 passed in 77.30s` | **increases**, same tests, same cause. Same two stop conditions. |
| `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | `519 passed, 1 warning in 64.73s` | **unchanged** |
| `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `15 passed in 54.64s` | **unchanged** |
| **`tests/specify_cli/`** — entered scope with `saas_service.py`; absent from every earlier revision | `35 passed in 54.65s`, exit 0 | **unchanged** |

*"Movement expected" alone is unfalsifiable — it is satisfied by any number, in either direction,
from any cause.* Each prediction above therefore names a **direction** and an **attributable cause**,
and states what makes it a stop. Re-take all **five** unpiped, exit status trusted, in a worktree
pinned to the base with `PYTHONPATH=$WT/src`.

**Exit criterion:** the base SHA is recorded; the citation sweep is recorded with a symbol-by-symbol
verdict; all **five** suites re-measured, each `N passed` line quoted, and each reconciled against its
direction-and-cause prediction.

### Stage 1 — The acceptance harness, before any product code

Build IC-01 and prove it against `bb2020fea`'s **un-gated** behaviour. The proof is the **positive
control**: a consenting-shaped fixture must capture argv containing the sentinel title verbatim, on a
tree where no gate exists.

**Why first:** **four** measured mechanisms make a refusing assertion pass with no gate present, and
each is only visible against a working positive control.

1. `SPEC_KITTY_ENABLE_SAAS_SYNC` unset → the group aborts at `tracker.py:354-366` with exit 1,
   0 subprocess, 0 HTTP, **nothing built**. SC-001, SC-003, SC-004 and NFR-002 are all green today.
2. `doctrine_mode` defaults to `external_authoritative` (`tracker/config.py:39`) →
   `local_can_write("title")` is `False` and `SyncEngine.push` skips without calling `create_issue`,
   so a *consenting* push on a default binding captures only `['<cmd>', '--json', 'list']` and the
   sentinel never appears.
3. The house pattern at `test_local_service.py:235,262,287` patches out `_build_engine` — a
   plugin-injected gate on that seam measured **bind count 0 with 519 tests green**.
4. **The store is empty.** `SyncEngine.push` iterates `store.list_issues(system=…)`, so with nothing
   seeded it never reaches `create_issue`. Measured with the harness built exactly as (1)–(3)
   specify, nothing in the production path patched, `doctrine: {mode: spec_kitty_authoritative}`
   pinned and `SPEC_KITTY_HOME` isolated:

   ```
   ### EMPTY STORE ###   push stats: {'pushed_created': 0}   CAPTURED 1 argv   sentinel: False
   ### SEEDED STORE ###  push stats: {'pushed_created': 1}   CAPTURED 3 argv   sentinel: True
   ```

   **A fixture that satisfies all three previously-known guards still captures zero sentinel argv on
   the un-gated tree.** Seeding seam: `store.upsert_issue(CanonicalIssue(...))`, with
   `ref=ExternalRef(system="beads", workspace=<bound workspace>, id=<local id>)`,
   `title="ACME Holdings carve-out"`, `body="confidential body"`, `status=CanonicalStatus.TODO`
   (or `IN_PROGRESS`; any other member adds **two** argv — an `update` and a second `show` — taking
   the count to 5), `issue_type=CanonicalIssueType.TASK`,
   `assignees=["alice@acme.example"]`, `labels=["secret-label"]`. **The consenting argv count is 3,
   not 2** — `list`, `create`, `show` — because `create_issue` ends with `get_issue`
   (`spec_kitty_tracker/connectors/beads.py:151-153`).

**Unprovable otherwise:** that any later "zero argv" result is the gate acting rather than the
harness failing to fire. Every absence assertion in this Mission is paired, in the same test file
and against the same recorder, with a consenting control that captures argv.

**Exit criterion for Stage 1:** in `tests/sync/tracker/test_tracker_egress_refusal_3108.py`, run
alone, the consenting `push` control captures **exactly 3** argv with the sentinel verbatim in the
`create`, on the **un-gated** base — and the unseeded variant captures **1**. Quote the `N passed`
line. If the consenting control captures 1 argv, the fixture is wrong and no later result from this
suite means anything.

**Also fixed here:** the pull-direction assertion. `LocalTrackerService.sync_pull` calls
`engine.pull(limit=limit)` and `SyncEngine.pull(filters=None)` builds
`[<cmd>, "--json", "list"]` plus an optional `--updated-after`. **No issue title crosses on pull
today.** So pull's refusing assertion is **zero captured argv**, and its consenting control asserts
argv **shape and count** — never a title's absence, which would be asserting the absence of something
that never happens.

### Stage 2 — Channel 2's data layer and preservation, before the gate

IC-02 **and** IC-03, as one change set. **This stage does have a blast radius** — the previous
revision said it had none, and that was wrong: promoting `egress` to `_KNOWN_KEYS` is precisely what
breaks the two `_extra`-carrying preservation sites at `saas_service.py:219,316`.

**Why before the gate — three independent reasons.**

1. **The gate's blast-radius repair *criterion* depends on it.**
   `TestSyncOperations._setup_bound_service` calls `svc.bind(...)` on a `repo` fixture that has **no
   `.kittify/config.yaml` at all**, and `LocalTrackerService.bind` builds a **fresh**
   `TrackerProjectConfig`. So a `tracker: {egress: permitted}` seeded before the `bind()` is
   **erased by the `bind()`**. If the gate lands first, the available repairs are (a) patch out the
   gate, or (b) write the key *after* `bind()` — a fixture shape that hides the very erasure bug
   FR-011 exists to fix. **Note the re-grounding, because the previous revision's version of this
   argument was wrong:** it claimed (a) was *"forbidden"* by FR-018 H2. It is not.
   `TestSyncOperations` is a **pre-existing unit test**, H2's prohibition is scoped to the *new
   acceptance* tests and their named seams, and the spec explicitly permits `_build_engine` to stay
   patched there (SC-020). The argument that actually holds is the **criterion**: C-012 and SC-020
   claim *"the repair is one committed config line in the fixture repo"*, and landing the gate first
   makes that criterion **unsatisfiable** — not the repair impossible. **Unprovable otherwise:** the
   one-line claim itself. Reasons 2 and 3 are untouched by this correction and are independently
   sufficient.
2. **A narrowed field type silently converts refused → permitted.** Measured on the `doctrine.mode`
   precedent: a known field with an unusable value comes back as its **default**. If the gate lands
   on a field that does not carry the raw value, the Mission's own acceptance fixtures — which bind —
   become non-deterministic in the refusing direction. **Unprovable otherwise:** that a refusal
   survives the commands an operator will actually run.
3. **`preserve_quotes` and the six-site preservation work are config-layer changes with their own
   blast radius.** Making them while no gate exists means any red in the 519-test tracker baseline is
   attributable to them alone. **Unprovable otherwise:** whose change caused the red.

**Within Stage 2, IC-02's field shape is written before IC-03's carries** — preservation has nothing
to preserve until the field exists — **but both land in one commit**, because the interval between
them is an interval in which `saas_service.py:219,316` silently stop preserving. If they must be
split, the split requires a guard asserting that every `TrackerProjectConfig(` construction feeding
`save_tracker_config` carries `egress`.

Note the ordering artefact this creates: promoting `egress` to `_KNOWN_KEYS` **introduces** the
null-planting defect (`to_dict` emits every known field unconditionally, including `None`s), which
FR-009 then closes. That red is real and must be deliberately produced and observed — see
*Red-First Proof Strategy*.

**The FR-002-only tree is a required measurement point, not a commit boundary.** The plan already
requires it to exist so FR-009's null-planting red can be observed there. On that *same* tree, B1's
and B2's preservation pins are also red. So the rule is: build it, observe and **quote all three
reds**, then close them. The previous revision declared B1/B2's red unobservable because IC-02 and
IC-03 land in one commit — but the tree is built regardless, and this was the only requirement in the
Mission that would have shipped without an observed red. Nothing about the landing rule changes;
only the measurement is added.

> **Correction — 2026-08-01. Stage 2's exit criterion below still lists A1, and the board does not
> deliver A1 in Stage 2. This is the plan's one recorded departure, and it is recorded here rather
> than silently reconciled.**
>
> - **The cycle that forced it.** Site **A1** is `LocalTrackerService.bind` (`local_service.py:57`).
>   Keeping the erasure work whole — all of FR-011 in one WP — would put `local_service.py` in the
>   data-layer WP (WP02). But `local_service.py` is also where the **gate** lands (WP04), and WP04
>   already depends on WP02 through WP03. Putting A1 in WP02 therefore makes **the data-layer WP
>   depend on the WP that depends on it**, or else puts two live agents on one file, which the
>   Mission's own one-agent-per-file rule forbids.
> - **The resolution taken.** **A1 moves into WP04, as subtask T024, ordered ahead of the
>   `TestSyncOperations` fixture repair (T026).** WP02 keeps A2, A3, A4, B1, B2, C and D.
> - **Why A2 also changed class.** `LocalTrackerService.bind` **never reads `self._config`** — it
>   builds a fresh `TrackerProjectConfig` at `local_service.py:57`. So WP02's A2 fix at
>   `service.py:163` (hand `bind` the loaded config) is **inert on disk until A1 lands**. A2 is
>   therefore **class A′**: fixed as defence-in-depth, asserted at the unit level against the
>   constructed object, **with no red-first pin and no Stage-2 exit pin**. The Red-First table below
>   already says the preservation reds were *"measured independently at three of them: A1, A3, C"* —
>   A2 was never among them. The **end-to-end `TrackerService.bind` preservation pin lives in WP04
>   T024**, where A1 makes it real.
> - **What preserves the criterion.** The property Stage 2 was asserting — *a recorded decision
>   outlives its binding at every site that reaches disk* — is preserved by **intra-WP ordering**
>   (T024 before T026) rather than by stage boundary, and by the fact that **WP02 and WP04 land on
>   one branch and are never released separately**. The spec makes a cross-site guard the condition
>   of splitting FR-011 across change sets; that guard is not written, and **the window — from WP02
>   landing until WP04 T024 lands, `LocalTrackerService.bind` still erases** — is named in both WP02's
>   and WP04's prompts instead. Nothing ships inside it.
>
> **Read the criterion below as: A2, A3, B1, B2, C and D in Stage 2 (A2 and A4 at the unit level);
> A1 in Stage 4, subtask T024.**

**Exit criterion for Stage 2:** `tests/sync/tracker/test_tracker_egress_config_3108.py` green,
including the round-trip pin over the probed set of **exactly 15** values (enumerated once in
`spec.md` FR-010; the parametrised test prints and asserts its own case count is 15) and the
preservation pins at **A1, A2, A3, B1, B2, C and D**; **and** `tests/sync/tracker/
tests/agent/cli/commands/test_tracker.py` **and `tests/specify_cli/`** still at their Stage-0 numbers
— the latter because `test_apply_binding_upgrade_preserves_extra_fields`
(`tests/specify_cli/tracker/test_binding_report_only.py:254-268`) pins the `_extra` contract at the
exact line B1 modifies. **A4 has no exit pin**: it has no production write path, so it is asserted at
the unit level against the substituted config object and reds nowhere. Pins observed **red then
green** on the FR-002-only tree: the no-null-planting pin (`egress: null` in the rendered block), and
B1's and B2's preservation pins.

### Stage 3 — The verdict function, before either gate

IC-04. Still no call sites; a pure function with a value object.

**Why before the gates:** it is the only place the enforced answer and the reported answer can
diverge, and it is fully testable — the **8-cell** table, the never-raises contract over the probed
shape set (including a mapping and a list **at the key**, for **both** destinations), the
non-authoritative classifier pins, the classifier's root-equality pin — with **zero** blast radius.
**Unprovable otherwise:** NFR-003's never-raises property. Once the function is behind a gate, an
exception in it surfaces as a CLI traceback in an acceptance test, and distinguishing "the verdict
raised" from "the gate is misplaced" costs a bisect.

FR-015 guards **G4 and G5 do not land here** — they assert five call sites, and there are zero.

**Exit criterion for Stage 3:** the new unit suite for `egress_verdict.py` green, with
`len(_JOIN) == 8` asserted structurally, the parametrised table test **printing and asserting `8`
cells**, and the never-raises test **printing and asserting `24` cases** — NFR-003's **twelve**
enumerated shapes × **two** destinations, that enumeration being the single source and not
re-listed here. `ruff check` clean with **no `# noqa: C901`** on the new module (the decomposition in
`data-model.md` §2a is what makes that achievable; a conservative single function measures
`C901 17 > 15`). The specific pin to observe red-then-green: the
mapping-at-the-key case, whose red on a bare `raw in _LEGAL` implementation is a `TypeError`, not an
`AssertionError` — classify it and require the fixed implementation to return a fault verdict.

### Stage 4 — The local gate: the breaking change

IC-05, **with IC-09(a)'s CHANGELOG entry in the same commit**. The refusing acceptance tests written
in Stage 1 flip from red to green; the Stage-1 positive controls stay green.

**Why here and not earlier:** it depends on Stage 1 (a harness that can tell a gate from a no-op),
Stage 2 (a decision that survives `bind`), and Stage 3 (something to ask). **Unprovable otherwise:**
that the gate is the cause of the change in behaviour rather than a coincidence of the harness.

Three docstrings become false at this exact moment (`local_service.py:8`, `_check_sync_readiness`,
`_check_binding_readiness`) and are amended in the **same** change, pinned by a test so a later
revert reds.

**Exit criterion for Stage 4:** the acceptance suite green run **alone** and again inside the full
`tests/sync/tracker/` directory, with **every** test asserting a non-zero bind counter and the
interpreter version recorded beside it; `TestSyncOperations` green with a **one-line** fixture
repair. The specific pin observed red-then-green: **US1 sc1**, whose red prints
`ACME Holdings carve-out` inside a captured argv element.

### Stage 5 — The hosted gate

IC-06, **alone**, as its own change. **Landing alone is a necessity; landing it *after* Stage 4 is a
risk-ordering preference.** The two were previously stated as one claim, which made the preference
look load-bearing and the necessity look optional.

- **Necessity — alone.** Its detection signal is a byte-comparison against the shipped `#3030`
  refusal strings. A co-landing change makes any difference unattributable. **Unprovable
  otherwise:** SC-016's byte-identical claim for the three measured Channel-1 outcomes plus
  `root=None`.
- **Preference — after Stage 4.** It is the shipped `#3030` gate, the highest-consequence edit in
  the Mission and the one with the least new value. Doing it against a verdict function already
  exercised by the local path is safer, but nothing technical forbids the reverse order.

**Exit criterion for Stage 5:** `tests/sync/tracker/test_saas_client_consent_gate_3030.py`
**green with its `N passed` quoted, N being the number recorded for that file alone at Stage 0** —
stated this way because its count is otherwise folded invisibly into the 519 and "at its Stage-0
number" would cite a number that stage never produced. And **SC-005a** green — on-disk
`provider: beads` + `egress: permitted` + Channel 1 absent + `list-tickets --provider jira` →
refused, 0 HTTP, message naming Channel 1 — together with its positive control (on-disk `jira`,
Channel 1 granted, no tracker key → `No valid access token`), **both in
`tests/sync/tracker/test_tracker_egress_refusal_3108.py`**, the acceptance file, because both run
end to end through the CLI and the pairing is only meaningful in one file against one trip-wire. The specific pin observed red-then-green: **US5 sc1**, whose red is the
**exception type and message**, never the HTTP count (see *Open Items* 3).

### Stage 6 — Reporting, then the guards

IC-07 **alone**, then IC-08 **alone**.

**Why IC-07 alone:** its detection signal is `test_sync_doctor_consent_health_3030.py:366`'s
`flat.count("REPAIR THE FILE'S SYNTAX") == 4` — an exact count over the **whole rendered output**.
A count over shared output cannot attribute a movement to one of two co-landing changes. This is the
same argument already made for Stage 5, and it applies here verbatim.

**Why the guards last:** G4's exact membership (five enclosing functions, six call expressions) and
G5's literal-member set are only satisfiable once every call site exists, and a guard written earlier
would be edited by every later stage. A guard whose own history is a chain of edits is a guard nobody
can trust. **Unprovable otherwise:** that the guard's counts are a property of the architecture
rather than of the guard's most recent revision.

**How an AST guard is mutated without editing source — stated once, applying to all six.** The plan
forbids source edits during a verification run and requires mutations to be `PYTHONPATH`-injected
plugins; neither instruction tells an implementer how to mutate a guard whose subject *is* the source
tree. The rule: **each guard is written as an analyzer callable taking source text or a root path**
and returning its findings, and its test invokes it **twice** — once against `src/` (the real run,
reporting the real input count) and once against **synthetic mutated source held in the test string**
(the mutant run, reporting the killed-pin count). Nothing on disk is touched. Without this stated, an
implementer at this stage either breaks the no-source-edits rule or quietly ships the guards with no
mutants at all.

**The matcher's call form is specified, because the obvious implementation is blind.** Measured: a
sixth, **ungated** call site written module-qualified —

```python
from specify_cli.tracker import egress_verdict as ev
ev.tracker_egress_verdict(root, destination=ev.EgressDestination.LOCAL_SUBPROCESS)
```

— **passes both G4 and G5**, with G4's input count merely *rising* to 4, because a matcher inspecting
only `ast.Name` func nodes never sees it. Both previously specified G5 mutants keep the `ast.Name`
form, so a guard with this hole **kills 2/2 and reports itself healthy**. Every call-site guard
therefore resolves **both `ast.Name` and `ast.Attribute` func nodes**, and G4 and G5 each carry a
**third mutant in module-qualified form**. A guard that survives its own mutants while blind to its
subject is worse than no guard: it converts an unexamined property into an examined one that is
false.

**G6 — the body, not just the call sites.** G5 guards where the destination comes from; the original
defect lived **inside** the verdict. A future change reading *"if the on-disk provider is local,
treat this as local regardless of the argument"* passes G5 at all six expressions, and only one
behavioural test (SC-005a) would catch it. G6 asserts that
`src/specify_cli/tracker/egress_verdict.py` contains **no** reference to `provider`,
`LOCAL_PROVIDERS` or `SAAS_PROVIDERS`, and **no `.provider` attribute access on a
`load_tracker_config` result** — exact membership, expected set **empty**, with the printed
non-zero input count being **the number of AST nodes scanned** (an empty-set assertion over zero
nodes is exactly the vacuity the rule exists to prevent). One mutant reintroduces a provider read.

**What G5's clauses are actually worth.** Its set-equality clause — *"the literal members passed are
exactly the two"* — carries almost nothing alone, because the doctor renderer supplies both members
by itself. **The per-site mapping is the load-bearing half**: `_request` always `HOSTED_SERVICE`, the
three local sites always `LOCAL_SUBPROCESS`. That is the clause whose mutant must kill.

**Exit criteria.** *Stage 6a (IC-07):* the new doctor suite green with **14** rows asserted across
seven checkouts, at least one checkout rendering **different answers on its two rows**; and
`test_sync_doctor_consent_health_3030.py` still `15 passed` with the count still `4`. *Stage 6b
(IC-08):* all **six** guards green, each **printing** its non-zero input count, and each **killed**
by its mutants with the killed-pin count reported — **G4 and G5 by three each** (config-derived name,
swapped literals, module-qualified call site), **G6 by one** (a reintroduced provider read). The
specific pin observed red-then-green: **G5 under the module-qualified mutant**, because that is the
one a naive matcher passes.

### Stage 7 — The upgrade note

IC-09(b): the `docs/migrations/` upgrade note, its `index.md` link and the CI anchor check.
**IC-09(a), the CHANGELOG Breaking Changes entry, is not here** — it lands in the same change as
Stage 4, so the break never lands undocumented. The note is completed after Stage 5 because only
then is the remaining `HOSTED_SERVICE`-side limitation's exact shape fixed (C-016).

**Exit criterion for Stage 7:** the anchor check fails when the section is renamed (demonstrated,
not assumed) and passes otherwise; `pytest tests/architectural/test_no_legacy_terminology.py` green.

**IC-10's follow-up issues are filed before implementation starts** — stated once, in IC-10, and not
qualified anywhere else in this document.

### The ordering that was rejected

**Gate first, data layer after.** It is the shortest path to a green refusing test, and it is wrong
twice: it makes the *"repair is one committed config line"* criterion unsatisfiable (the `bind()` in
the fixture erases the seeded key, so the only remaining repairs either patch the gate out or write
the key after `bind()`, hiding the erasure bug), and every red in `tests/sync/tracker/` becomes
jointly caused by the gate and the config change. It would produce a Mission whose central claim —
*"the repair is one committed line"* — is untested.

---

## Red-First Proof Strategy

**The rule:** red first, and make the red the **consequence**. Assert the bytes, not a boolean.

### What reds first, on what, and why the red is the consequence

| Pin | Reds on | The red is | Why it is the consequence, not a proxy |
|---|---|---|---|
| **US1 sc1** — `beads`, Channel 1 granted, `tracker: {egress: refused}`, **seeded store**, `sync push` | the base, at Stage 1 | the recorder captures **3** argv — `list`, `create`, `show` — the `create` containing `ACME Holdings carve-out` verbatim | The failure message **prints the confidential title in a captured argv element**. It is the leak itself, not a return code standing in for one. **Without the seeded store the base captures 1 argv and no sentinel**, and the pin is green for the wrong reason. |
| **US3 sc1** — no record at either channel, seeded store, `sync push` | the base | same capture | Same. Additionally asserts the tracker SQLite file's **bytes are unchanged** across the refused command (NFR-002 clause a). |
| **US3 sc4** — the **unseeded** pair | the base | the consenting member creates the db file and captures 1 argv | Carries NFR-002's **file-existence** clause, which the seeded pair cannot: it is the pin that reds if the gate is later moved back to `_build_engine`, where `TrackerSqliteStore.__init__` `mkdir`s and creates the file. No sentinel assertion is made here — nothing crosses on an unseeded push in either member. |
| **US5 sc4 / SC-005a** — on-disk `provider: beads` + `egress: permitted` + Channel 1 absent + `list-tickets --provider jira` | the base **and** any config-derived implementation | the command **succeeds past the gate** (base: reaches the token check; derived implementation: **grants**) where it must refuse naming Channel 1 | This is the pin that discriminates *destination as a parameter* from *destination as a derivation*. Its positive control (on-disk `jira`, Channel 1 granted, no key → `No valid access token`) proves the zero-HTTP count in the refusing member is not vacuous. |
| **US4 pull refusing** | the base | `len(captured) == 1`, argv printed: `[<cmd>, '--json', 'list']` | Pull's red is argv **shape and count**. A title-absence assertion here would be green on the base for the wrong reason — **no title crosses on pull today**. |
| **US4 run refusing** | the base | argv captured for both halves | The verdict is computed once at the head of `sync_run`, so both halves are downstream of it; the red proves neither half reaches the runner. |
| **FR-010 round-trip** | the base | a byte diff of the `egress:` line for at least the quoted-string and `null` cases | Compares bytes before and after a `bind`, and asserts the rest of the file differs only in lines a `bind` is supposed to touch. |
| **FR-011 preservation, sites A1, A2, A3, C** | the base (measured independently at three of them: A1, A3, C) | `egress` absent from the rendered block after `bind` / `SaaSTrackerService.bind` / `unbind`, with the sibling `sync:` block present as the control | The control proves the file was written and the rest survived, so the missing key is erasure and not a write failure. `SaaSTrackerService.bind`'s red is `AFTER bind: egress present? False` against `CONTROL (_extra-carrying pattern): True`. |
| **FR-011 site A4** | **nowhere** | — | **No red-first pin, deliberately.** `service.py:98`'s substituted config has **no production write path**: `_persist_binding`'s three call sites (`saas_service.py:347,412,505`) are all inside bind flows entered from `TrackerService.bind` (`service.py:141-145`), the substitution serves only the three read paths (`service.py:210,214,220`), and `apply_binding_upgrade` (`saas_service.py:191`) has zero callers in `src/`. It is fixed as **defence-in-depth** against a future write-capable caller and asserted at the unit level. An implementer told to "red it first" would be writing a pin against code no production path executes. |
| **FR-011 site D** | **nowhere on the CLI** | — | `saas_service.py:281` resets `self._config` in memory; library-caller reachable only. Asserted at the unit level: after `unbind`, `self._config.egress` equals what site C left on disk. |
| **FR-011 preservation, sites B1–B2** | **the FR-002-only tree — a required measurement point** | `egress` absent after a binding-ref upgrade (`saas_service.py:206`/`:219`) / `_persist_binding` (`:303`/`:316`) | On the base these two are **green**, because `egress` rides in `_extra`; the promotion to `_KNOWN_KEYS` (`config.py:107`) is what breaks them. **The FR-002-only tree is built regardless** — the plan already requires FR-009's null-planting red to be observed there — so both reds are observed and **quoted at that same point**, then closed. This is a *measurement point, not a commit boundary*: the landing rule still keeps IC-02 and IC-03 in one commit. Without this, B1/B2 would be the only requirement in the Mission shipping without an observed red. |
| **FR-015 G5** | under its two injected mutants | the guard's own assertion, on a config-derived `destination` and on a swapped literal | The guard's property *is* FR-004; a mutant that swaps `HOSTED_SERVICE` for `LOCAL_SUBPROCESS` at `_request` is the exact defect that would reopen `#3030`. |
| **FR-009 no-null-planting** | **not the base — the Stage-2 intermediate tree** | `egress: null` in the rendered `tracker:` block after a `bind` into a project with no tracker key | On the base, `egress` is an unknown key handled by `_extra`, so the pin is **vacuously green**. Promoting it to `_KNOWN_KEYS` is what creates the defect. **This red must be deliberately produced and observed on the FR-002-only tree** — skipping it means FR-009 ships untested. |
| **FR-014 doctor block** | the base | the block is absent | Assert the block is printed in all seven checkouts, and that the rendered verdict equals the enforced verdict **field-for-field** for the same checkout. |
| **FR-015 G1–G6** | under their injected mutants (three each for G4/G5, one for G6) | the guard's own assertion | Each guard is an analyzer callable invoked against synthetic mutated source, with the killed-pin count and the real input count reported separately. The G4/G5 mutant that matters most is the **module-qualified call site** — the form measured to pass an `ast.Name`-only matcher. |
| **US5 sc1** — `jira`, Channel 1 granted, `tracker: {egress: refused}` | the base | **the exception type and message**, not the HTTP count | **Important:** `_request` raises at the token check *before* any HTTP, so "0 HTTP attempts" is **already green on the base**. The base behaviour is `No valid access token`; the required behaviour is `TrackerEgressRefusedError` naming Channel 2. The red must pin the text. See *Open Items*. |

### What must be green before and after — the positive controls

- **US1 sc2 / US3 sc3 / US4 sc3** — consenting fixture, sentinel captured verbatim. Green on the base,
  green after. Without these, every zero-argv assertion is indistinguishable from a harness that never
  ran the code.
- **US2 sc1** — no Channel-1 record, `tracker: {egress: permitted}` committed, argv captured. Green on
  the base (nothing gates the local path today), green after (Channel 2 grants). Its **paired
  negative** — the same fixture with that one line removed — is the red, and the two fixtures differ
  by **exactly one committed line**.
- **US5 sc3** — `jira`, Channel 1 granted, no tracker key: the gate passes and the call fails later at
  `No valid access token`. The shipped `#3030` behaviour, unchanged.
- **US1 sc4** — hosted sync is unaffected: `sync now` drains **N ≥ 1** events and the paired fixture
  (identical but for the tracker key) delivers exactly the same N, compared event-for-event. A drain
  that never ran would satisfy the weaker wording.

### Executed remedies, never substrings

Every remedy a message claims is asserted by **applying it to the refusing fixture and re-running**,
asserting the sentinel title now reaches the recorder (FR-018 H5, SC-004, SC-007). That test, and
only that test, catches the measured state in which the message told the operator to do exactly what
they had just done — an identity-less checkout where `enable_checkout_sync` raises
`ConsentIdentityUnresolvedError` (`routing.py:320-321`) and hand-authoring `sync.enabled: true` still
denies.

### Five ways a mutation silently lies — checked, each

1. **The architecture moved and the patched gate became a redundant second**, so all-green reads as
   "your pin is fine". *Check:* the mutant's own bind counter must be non-zero, and removing the real
   gate must red. A mutation with a zero bind count is **no measurement**.
2. **The reds are `TypeError`s from a changed signature, not assertion failures.** *Check:* the mutant
   preserves the signature; classify every red by exception type and require `AssertionError`. Read
   the failure **text**, not the tally.
3. **The mutant hard-codes a value the tests vary**, so it no-ops for exactly the tests most likely to
   catch the defect. *Check:* the Channel-2 mutant used for SC-005's pin **removes** Channel 2 (makes
   the resolver answer `absent`) rather than hard-coding a verdict; then confirm the tests that vary
   the Channel-2 value still discriminate between cells.
4. **The branch is unreachable on the local interpreter (3.14) and live on CI's (3.11/3.12).** *Check:*
   record the interpreter version beside every bind count and every guard input count. A zero bind
   count is a statement about **the environment**, not about the code.
5. **`from X import f` rebinds by value**, so patching the defining module leaves the deciding module
   inert. *Check:* patch the **deciding** module's name, and **note that the hosted path has two
   targets which apply at different times, because IC-06 deletes the first**:

   | Path | Target **before** the IC-06 swap | Target **after** the IC-06 swap |
   |---|---|---|
   | hosted (`saas_client._request`) | `specify_cli.tracker.saas_client.project_egress_refusal` | `specify_cli.tracker.saas_client.tracker_egress_verdict` |
   | local (`local_service` gates) | — (no gate yet) | whatever name `local_service.py` binds `tracker_egress_verdict` under, throughout |

   A recipe naming only the pre-swap target is **correct on the base and inert on the delivered
   tree** — a mutation that silently lies, and the exact class this list exists to catch. **Report
   the split per site.** Measured at `bb2020fea`: after patching
   `specify_cli.tracker.egress_consent.project_egress_refusal`,
   `TSC.project_egress_refusal is TE.project_egress_refusal` → **`False`**; and the split is **not
   uniform** — `specify_cli.invocation.resolve_egress_consent` and
   `specify_cli.invocation.propagator.resolve_egress_consent` do **not** observe a patch on
   `invocation.adapters` (measured `False`), while the call-time import inside
   `tracker/egress_consent.py:178` **does** (measured: flipped refuse → permit).

**Clarification an implementer will need:** FR-018 H2's prohibition on patching is scoped to the
**acceptance** tests and to the specific seams named there (`_build_engine`, `build_connector`,
`SyncEngine`, `LocalTrackerService`, `TrackerService`). The unit-level pins that force the Channel-1
classifier's three labels (C-004) legitimately patch that classifier by name; that is not a violation
of H2.

### The mutation pin that proves which criterion carries the Mission

With Channel 2 removed entirely by a `PYTHONPATH`-injected plugin, **US1 sc1 must go red while SC-005
stays green** (SC-005). That asymmetry is the proof that SC-005 alone cannot carry the Mission and
SC-001 is the criterion that does.

---

## Verification Plan

### Measurement rules — binding on every claim

- **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports `tail`'s
  status and buffers until exit. **Quote the `N passed` line.** An empty output file is **no
  measurement**.
- **A killed run is neither a pass nor a fail.** Re-run narrowed; do not explain it.
- **Measure in a `git worktree` pinned to a commit, and set `PYTHONPATH=$WT/src`** (or use a dedicated
  venv). The editable install hard-codes the **main checkout's** `src` path, so a worktree run
  otherwise imports the live tree and any "identical results" conclusion is a tautology.
- **Read the failure text, not the tally.**
- **Print the input count alongside any "all checks passed."** A gate that ran on zero files passes
  vacuously.
- **Any assertion of absence must establish why the thing would otherwise have happened.**
- **Control your diagnostic** — run any probe against a case whose answer you already know before
  trusting it.
- **Mutations are pytest plugins injected via `PYTHONPATH`, never source edits**, and **never** source
  edits during a verification run.
- **Explicit-path staging.** `git add <paths>`, never `git add -A` — 13 files were lost to a stray
  `add -A` in this lineage.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`). Only `ruff check` is meaningful.

### Targeted suites, per the charter's Testing Requirements

| Surface | Suite | Baseline at `bb2020fea` | **Predicted at the real base (Stage 0)** |
|---|---|---|---|
| Tracker package + CLI | `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | `519 passed, 1 warning in 64.73s` | **unchanged** |
| Consent chain and egress boundary | the six consent/boundary suites (`tests/sync/test_consent_resolver_3030.py`, `test_consent_fault_vocabulary_3030.py`, `test_consent_read_fault_3030.py`, `test_consent_field_fault_3030.py`, `tests/invocation/test_adapters.py`, `tests/architectural/test_egress_consent_boundary.py`) | `154 passed in 51.31s` | **movement expected** — contains the file `#3113` modifies |
| `sync doctor` consent health | `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `15 passed in 54.64s` | **unchanged** |
| **SaaS tracker service + write boundary** | **`tests/specify_cli/`** | **`35 passed in 54.65s`** | **unchanged** |
| Hosted consent gate (own row, so Stage 5 can cite a number) | `tests/sync/tracker/test_saas_client_consent_gate_3030.py` | **measure and record at Stage 0** — its count is otherwise folded invisibly into the 519 | **unchanged** |
| Egress guard alone | `tests/architectural/test_egress_consent_boundary.py` | `27 passed in 77.30s` | **movement expected** — same file |
| This Mission's new suites | the four new files listed in *Affected Surfaces* | n/a — new | n/a |
| Architectural sweep (pre-PR) | `tests/architectural/` | known-red roster applies (C-013) | roster applies |
| Terminology guard (before pushing prose/doctrine) | `tests/architectural/test_no_legacy_terminology.py` | ≈0.1 s | unchanged |

**A re-measurement without a prediction has no control.** An **unpredicted** movement in any row is a
**stop-and-attribute event** — identify the cause before continuing, and file it if it is not
Bundle A's landing.

**Run the new acceptance suite twice: alone, and inside a full `tests/sync/tracker/` run.** A
discrepancy between the two is cross-test pollution (the `#3115` class), not this Mission — and is a
finding to report, not to chase to green.

### Quality gates

- `ruff check` clean on new code; **no blanket `# noqa`**, no per-file ignore additions. Complexity
  ceiling 15 (`C901` / Sonar `S3776`): the new `sync doctor` renderer is its own function so
  `doctor()` gains one call, not branches.
- `mypy --strict` clean, no `# type: ignore` added to achieve it.
- ≥90 % coverage on new branches, with focused tests executing the new helpers directly rather than
  relying on the acceptance suite alone.
- Repeated non-trivial literals (the two legal values, the key path, the message fragments) hoisted to
  named module constants once they appear ≥3 times (Sonar `S1192`).

### Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green

`tests/architectural/test_tid251_enforcement.py` (4 tests);
`test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
two `test_safe_commit_cmd::…_3033`;
`test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
`test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
`ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental.

**Any *newly* encountered pre-existing failure is filed as a GitHub issue before being treated as
baseline** (charter Pre-existing Failure Reporting Rule). Confirm a suspected pre-existing red by
running the same test against the merge-base with `PYTHONPATH=<worktree>/src`.

### Non-vacuity checks specific to this Mission

- Every acceptance test asserts the gate's **bind counter is non-zero**, and one test asserts the
  counting wrapper changes no outcome.
- Every guard **prints and asserts its own non-zero input count**.
- Every absence assertion is paired with a consenting control in the same file, against the same
  recorder.
- A grep-based pin over this Mission's new test files asserts `_build_engine` is patched **nowhere**,
  with its input count printed (SC-020).
- Every refusing acceptance test asserts its matched refusal text is **not**
  `saas_sync_disabled_message()` (SC-013).
- **Every push/run acceptance test asserts its consenting control captured exactly 3 argv** — the
  seeded-store non-vacuity check. A control that captured 1 argv means the store was empty and every
  absence assertion in that file is void (FR-018 H8).
- **Every absence assertion states why the thing would otherwise have happened**, and the two that
  cannot are marked as such: `pull`'s refusing case asserts zero argv and **never** a title's
  absence (no title crosses on pull today), and the unseeded NFR-002 pair asserts file existence and
  **never** the sentinel.
- **The classifier's root is asserted equal to the registered resolver's root** for a checkout
  invoked from a subdirectory (C-004).

---

## Risks

| # | Risk | Mitigation | Detection signal |
|---|---|---|---|
| R-01 | **The gate is installed and never entered.** The house pattern patches out `_build_engine`; measured **bind count 0 with 519 tests green**. | FR-018 H2 — the recorder **is** the credential-named fake executable on disk (there is no `SubprocessCommandRunner` injection seam); the named seams un-patched in acceptance tests. Delegating bind-counter wrapper (H4). | Bind counter `== 0` in any acceptance test → fail the test. Plus the grep pin over new test files for `_build_engine`, input count printed. |
| R-02 | **The positive control is vacuous** because the default `external_authoritative` mode means no title crosses on push. | FR-018 H1 — every fixture pins `doctrine: {mode: spec_kitty_authoritative}`. | The consenting control captures only `['<cmd>', '--json', 'list']` and the sentinel is absent → the fixture's doctrine mode is wrong. |
| R-03 | **The arming abort satisfies every refusing assertion** with nothing built. SC-001/003/004 and NFR-002 are green today. | FR-018 H3 — `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set explicitly; assert refusal **text**. | The matched refusal text equals `saas_sync_disabled_message()` → fail (SC-013). |
| R-04 | **`bind`/`unbind` erase the committed decision** — a silent fail-open for `refused`, a silent withdrawal for `permitted`. **Six** sites, re-derived from `grep -n "TrackerProjectConfig(" src/`: four erase today (`local_service.py:57`, `service.py:163`, `saas_service.py:266` — measured, `service.py:98`) and two are broken by FR-002 (`saas_service.py:219,316`). | IC-02 and IC-03 land together and **before** the gate; all six sites fixed; both directions pinned at each, with the sibling `sync:` block as control. | The `TestSyncOperations` repair requires writing the key *after* `bind()` → FR-011 has not landed. A preservation pin red at `saas_service.py:219` or `:316` → FR-002 landed without its class-B carries. |
| R-05 | **A narrowed field type silently replaces a recorded value with a default** on round trip, converting a refusing project into a permitting one. | Raw value plus derived fault on the dataclass; `egress` in `_KNOWN_KEYS`, not `_extra`. | The FR-010 byte-identical pin over the **whole probed set** (not the one shape that surfaced first). |
| R-06 | **`preserve_quotes` blast radius** — previously stated as "every string from `tracker:` becomes a ruamel scalar-string subclass of `str`". **Measured much narrower:** `from_dict` `str()`-coerces every known string field, so only `_extra` values and the raw `egress` retain the subclass. Separately, `clear_tracker_config` (`config.py:184`) builds a **third** `YAML()` with no `preserve_quotes` and dumps directly, so `unbind` destroys sibling-block quoting today. | Both `load_tracker_config` and `clear_tracker_config` gain it; **byte-identity is scoped to the `egress:` line**, with the rest of the file asserted to differ only in lines the operation should touch. Made as its own change while no gate exists. | Any red in `tests/sync/tracker/test_config.py` or `test_local_service.py` traceable to that change. |
| R-07 | **Bundle B moves the call sites and G4/G5 fall to zero, passing vacuously.** | G4 asserts exact **membership and counts `5` enclosing functions / `6` call expressions**, never `<=`, and prints its input count; G5 asserts the literal set. C-009 records the move as a rename Bundle B must perform, not a thing it may let fall to zero. | G4's printed input count and the membership set naming the five sites explicitly; G5's literal set. |
| R-08 | **Cross-test pollution from `#3115`** makes a red in `tests/sync/tracker/` unattributable. | **Correction:** `#3115`'s only affected test under `tests/sync/tracker/` is `test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`, which this Mission does not touch; the pollution is **CI-shard-only and explicitly not locally reproducible**; and the `519 passed` baseline was taken serially with A unlanded. So this risk is **materially smaller** than previously stated, and A is not a technical prerequisite. Mitigation stands anyway: run the new suite alone **and** inside the full directory. | A discrepancy between the two runs is pollution, not this Mission — report it, do not chase it. |
| R-17 | **The store is empty and the acceptance suite is a false green** — the fourth measured mechanism. A fixture satisfying the ownership-mode, patched-seam and arming guards **still captures zero sentinel argv on the un-gated tree**, which is exactly the shape of a passing refusal test. | FR-018 **H8**: seed via `store.upsert_issue(CanonicalIssue(...))` with the specified shape; assert the consenting control's argv count is **exactly 3**. | The consenting control captures **1** argv (`list` only) and the sentinel is absent → the store was not seeded, and every refusal result in that file is meaningless. |
| R-18 | **The destination is derived from configuration by a later change**, silently converting `tracker.egress: permitted` into a hosted grant for `--provider` commands. | The parameter is **required and keyword-only**; `mypy --strict` rejects omission; **G5** rejects a non-literal argument; **SC-005a** fails behaviourally. | G5 red; or SC-005a red with the refusing member reaching `No valid access token` instead of a Channel-1 refusal. |
| R-20 | **A call-site guard is blind to the call form it is meant to police.** Measured: a sixth, ungated call site written module-qualified (`ev.tracker_egress_verdict(…, destination=ev.EgressDestination.…)`) **passes both G4 and G5** on an `ast.Name`-only matcher, with G4's input count merely rising. Both originally specified G5 mutants keep the `ast.Name` form, so such a guard kills 2/2 and reports itself healthy. | Matchers resolve **both `ast.Name` and `ast.Attribute` func nodes**; G4 and G5 each carry a **third mutant** in module-qualified form. | The module-qualified mutant failing to kill. That mutant *is* the detection. |
| R-21 | **The polarity is re-derived inside the verdict's body**, passing G5 at all six call sites. | **G6**: no `provider` / `LOCAL_PROVIDERS` / `SAAS_PROVIDERS` reference and no `.provider` access on a `load_tracker_config` result inside `egress_verdict.py`; empty expected set with the AST-node count printed. | G6 red; or SC-005a red with G5 green — the signature of a body-side derivation. |
| R-19 | **The field promotion silently breaks two working preservation sites.** `saas_service.py:219,316` preserve `egress` only because it rides in `_extra`; `config.py:107` excludes known keys from `_extra`. The previous revision cited these two lines as *the pattern to copy*. | IC-02 and IC-03 land as **one change set**; if split, a guard asserts every `TrackerProjectConfig(` construction feeding `save_tracker_config` carries `egress`. | A preservation pin at `:219` or `:316` red on the IC-02-only tree — which is the red an implementer must either observe deliberately or avoid by not splitting. |
| R-09 | **The SaaS swap perturbs the shipped `#3030` gate**, trading one leak for another. | Done last, alone; the three measured Channel-1 outcomes reproduce **byte-identically**; gate position before `_fetch_access_token_sync()` unchanged; `TrackerEgressRefusedError` identity unchanged. | Red in `tests/sync/tracker/test_saas_client_consent_gate_3030.py`, or any byte difference in the three refusal strings. |
| R-10 | **The doctor block contributes to an existing count-based pin.** | A **new** renderer, not a third scope through `_render_consent_fault`; `CONFIG_FAULT_KINDS` not extended. | `test_sync_doctor_consent_health_3030.py:366` flipping off `4`. If it moves, the block routed through the fault renderer. |
| R-11 | **A typo takes a working local binding offline.** `tracker: {egress: refuse}` (singular) is a fault, and a fault refuses. **Intended, not a side effect** — on a confidentiality control the only safe reading of a value nobody defined is refusal. | The mitigation is the **message**, not a looser decode: the fault names the offending value **verbatim** and names **both** legal values. `sync doctor` renders the same wording for the same checkout. | SC-010's parametrised probe over the full probed set, on both a local and a SaaS binding. |
| R-12 | **The verdict raises out of a gate that must never raise** — e.g. an `ImportError` from `specify_cli.sync`. | NFR-003: call-time guarded imports for the hosted-sync symbols; module-local sentinel rather than importing `sync/consent.py:145`'s `_MISSING`; `TrackerConfigError` caught and answered with a fault refusal. | A parametrised never-raises test over the probed shape set — unreadable, unparseable, wrong-shape, non-mapping `tracker:`, empty, comments-only, `chmod 000`, absent file, non-project root, and `root=None`. |
| R-13 | **The local interpreter (3.14) differs from CI (3.11/3.12)**, so a zero bind count reads as "the code is dead" when it means "your environment differs". | Record the interpreter version beside every bind count and input count. | A zero bind count locally with the same code green on CI. |
| R-14 | **The gate is quietly moved back to `_build_engine`** by a later reader, because it produces no egress and therefore looks harmless. | C-018 records what the move reintroduces: a machine-global credential-store read and a `TrackerSqliteStore` construction that `mkdir`s and creates a SQLite file with three tables; and it re-breaks the unparseable-config unit pin (C-021). Guard G3 pins the gate as the **first executable statement** of exactly the three methods. | G3 failing; **NFR-002 clause (b)** — the unseeded pair's db-path existence assertion — failing. |
| R-15 | **The tracker path stops being operator-invoked.** If any daemon, sweep, hook or `next`-loop reaches `LocalTrackerService`, the attribution precondition at `tracker/egress_consent.py:64-129` is violated — a **valid** root for the **wrong** project. | Prose only (C-006 precondition 3); no executable guard exists for this. **Re-check required of any Mission adding an automatic caller.** | None automated. This is a named residual, not a mitigated risk. |
| R-16 | **Severity of Gap B is unestablished.** Whether `bd`/`fp` themselves make network calls is **UNVERIFIED and unresolvable from this repository** — neither binary is installed or vendored, and the name is operator-overridable from a machine-global credential file. | The gate is defensible either way; the design does not depend on the answer. **No task may attempt to "prove" Gap B's severity from this repo** — it cannot succeed. | n/a — carried as a stated limit (C-019 (1)). |

---

## Coordination with Sibling Bundles

### Bundle A — `#3115`, `#3113` — a scheduling dependency, **not** a technical prerequisite

Bundle A has landed **nothing**: `git diff --stat upstream/main...HEAD` on its branch is dossier-only
and both issues are open. Its `pytest.ini` timeout and the egress guard's positional-call fix are
unlanded.

**The previous revision called A a hard prerequisite. That was overstated, and the correction
matters because a false prerequisite is a false excuse.** `#3115`'s only affected test under
`tests/sync/tracker/` is `test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`,
which this Mission does not touch. The pollution is **CI-shard-only** and is **explicitly not
locally reproducible**. And the `519 passed, 1 warning` baseline was measured **serially, with A
unlanded** — i.e. the red-first proofs this Mission depends on have already been shown to run
cleanly on an A-less base. **Waiting on Bundle A is therefore not a technical prerequisite for this
Mission's local red-first proofs.**

**And, equally plainly: implementation is deferred by operator instruction regardless.** This
correction is a correction to a *claim*, not a change to the *schedule*. It is not permission to
begin. The two sentences are placed together deliberately so a successor cannot quote one without
the other.

**Resolving an internal contradiction the previous revision carried.** `#3113`'s guard fix was cited
in one place as part of the gate rationale for waiting on A, while this section said it was
irrelevant. The second statement is the correct one and the first is withdrawn: `local_service.py`
holds **no transport call** for the egress guard to match, and the guard's own Limit 4 scopes
`subprocess` out by design. **This Mission neither depends on `#3113` nor is blocked by its
absence.** What `#3113` *does* affect is a **baseline**: it modifies
`tests/architectural/test_egress_consent_boundary.py`, which is why the `154` and `27` baselines
carry a *movement expected* prediction and the `519` and `15` do not.

### Bundle B — `#3110` — designed to be a rename in either order

Bundle B **deletes** `tracker/egress_consent.py` and `saas_client/egress_consent.py` and moves
`project_egress_refusal` into a new `src/specify_cli/egress/` package. This Mission adds a **third**
call site for that symbol — in `local_service.py`, a file whose docstring says *"No SaaS imports live
here"* and which can never appear in the egress allowlist because it holds no HTTP sink.

**The design decision that makes the ordering cheap:** `local_service.py` imports
**`tracker_egress_verdict`, never `project_egress_refusal`**. The only module-level import of
`project_egress_refusal` this Mission adds is a **single statement in `tracker/egress_verdict.py`**.
So the local gate is immune to B's move, and B's move touches one import line plus the location of
one file.

| Landing order | What it requires |
|---|---|
| **B lands first** | `tracker/egress_verdict.py`'s single import points at `specify_cli.egress` instead of `specify_cli.tracker.egress_consent`. Nothing else in this Mission changes. Consider whether `egress_verdict.py` should be created inside `specify_cli/egress/` from the start — a tasks-phase decision, not a plan-phase one. |
| **This Mission lands first** | The import points at `specify_cli.tracker.egress_consent`. **B must carry `tracker_egress_verdict`, `EgressDestination`, Channel 2's resolver, the module-local sentinel and all five call sites with it**, and must **update FR-015 G4's expected membership and G5's literal set** rather than let the counts fall to zero (C-009). G4 asserting `== 5` / `== 6` rather than `<=` is what makes B's omission visible instead of silent. |

**B's Q3 stays closed.** Nothing in this Mission widens `EgressConsent` or the `Callable[[Path], bool]`
resolver contract. The Channel-1 three-way state is a **reporting-only** classifier reading
`ConsentDecision.level` **for a message**, structurally pinned non-authoritative (C-004, `data-model.md`
§3). B may finish its consolidation on the four-member enum. **Bundle B is not blocked by this
Mission.**

**But B owns this Mission's debt retirement, and should know it.** The classifier exists *only*
because the resolver port returns a bool and discards *why* a project is refused. **If and when Q3
gives that contract a decision return value, the classifier and both of its non-authoritativeness
pins are deleted, not migrated.** It is also an **unregistered runtime consumer** of
`specify_cli.sync.consent` — it reaches around the registry indirection that keeps the package
boundary clean, via a call-time guarded import — and that exception retires on the same condition.
Recorded here rather than only in `data-model.md` so it appears in B's field of view.

### `saas_client/egress_consent.py:92` is a second definition, not a re-export

Measured: different `id`, different `__module__` from `tracker/egress_consent.py:147`. This Mission
adds **no third definition** and does **not touch** the `saas_client/` package (C-008). Recorded
because conflating a second definition with a re-export produces a patch-site table that is wrong for
one of the two.

---

## Out of Scope, and the Follow-Ups to File

### Filed as issues, not absorbed — **all of them before implementation starts**

**1. Finish `#3030` FR-031's migration at the two remaining enforcement sites** (C-014).

**The framing is the deliverable here.** Filed as *"consolidate the two consent chains"* this is
large, unbounded, and will be deferred indefinitely — which is what happened last time. Filed as
*"finish FR-031's migration at the two remaining sites"* it is small, bounded, and gets done. Write
the title that way.

The issue must carry, at minimum:

- **The three already-migrated modules and their in-source rationale**, so the pattern is not
  re-derived: `sync/body_upload.py:66-88`, `sync/emitter.py:65`, `invocation/adapters.py:51`, with
  the supporting argument at `sync/__init__.py:346`.
- **The two remaining enforcement sites**: `sync/batch.py:338` (`_is_checkout_sync_enabled_for_batch`,
  reached from the drain gate at `sync/batch.py:1070`) and `sync/runtime.py:106`.
- **The two display-only reads** of `routing.effective_sync_enabled`: `cli/commands/sync.py:1964`
  and `:2081`. They are display-only and should be labelled as such, so nobody treats them as gates
  or skips them as noise.
- **The named canonical replacement**: `sync/body_upload.py::project_consents_to_hosted_sync`
  (`body_upload.py:54`, rationale `:60-88`) — the uuid-keyed question the migrated sites ask.
- **The `repo_defaults` keying objection**: `is_sync_enabled_for_checkout` honours the
  **repo-slug-keyed** `[sync.repo_defaults]` record that `consent.py:99-103` explicitly refuses
  (*"One was added on 2026-07-30 and removed the same day"*), because a git remote is mutable and
  cannot speak for a project.
- **The reachability sentence, verbatim, because it is what makes this urgent rather than tidy:**
  `_build_checkout_sync_routing` falls through to
  `SyncConfig().get_repository_sync_enabled(repo_slug)` (`routing.py:194-200`) when both the
  project-local and the checkout-local records are `None`, and `enable_checkout_sync` writes that
  repo-slug record on **every** opt-in (`routing.py:325`) — **so a fresh clone of an already-opted-in
  repository drains events that Chain A denies.**

**Not touched here** — it answers hosted-sync fan-out rather than tracker egress, its blast radius is
the drain and the daemon, and folding it in would be a second Mission wearing this one's branch.

**2. `LocalTrackerService.sync_publish` raises an uncaught `AttributeError`** (C-015).
`TrackerService.sync_publish` (`service.py:202-203`) delegates unconditionally and
`LocalTrackerService` has no such method, so `spec-kitty tracker sync publish` on a `beads`/`fp`
binding raises `AttributeError` — which `_run_or_exit` (`tracker.py:346-351`) catches only for
`RuntimeError`/`ValueError` (confirmed: `isinstance(e, (RuntimeError, ValueError))` → `False`). A live
bug, **incidental to this Mission**. The issue must carry the reproduction command and both line
references.

**3. A Windows sibling for the tracker acceptance recorder.** The harness's recorder is a
`#!`-script and `subprocess.run` takes no shell, so the acceptance suite is POSIX-only and ships
with a documented `skipif(os.name == "nt")`. The target platform includes Windows 10+. The issue
must carry: the recorder's contract (a credential-named executable that appends its argv to a file),
the `.cmd`/`.bat` shape needed, and the fact that it needs a **Windows CI runner** to be worth
anything — which is why it is not absorbed here.

### Explicitly out of scope, recorded rather than forgotten

- An **audit of `_extra`'s consumers** (C-019 (3)). Promoting `egress` to a known field is the
  mitigation, not the answer.
- **Establishing whether `bd`/`fp` are network clients** (C-019 (1), R-16). Unresolvable from this
  repository.
- **Unifying the two refusal exception hierarchies** (FR-012). The *verdict* is unified; the
  exceptions are not.
- **Adding tracker-egress state to `tracker status`** (C-015). No longer deferred because a second
  verdict would drift — FR-003 makes one verdict available to any caller — but deferred because the
  `tracker` group is **conditionally registered** and is therefore the wrong surface for a diagnostic
  an operator needs precisely when the group is unavailable.
- **The server-side half of anything.**
- **`SPEC_KITTY_ENABLE_SAAS_SYNC` remains arming and never a grant.** This Mission neither strengthens
  nor weakens it.
- **Reconstructing `#3030`'s "seven independent places"** (C-019 (4)) and **whether E20 was accurate
  against an earlier commit** (C-019 (2)).
- **Any `_baselines.yaml` bump.** `egress_allowlist_files: 28` stays. `local_service.py` and the new
  `egress_verdict.py` hold no HTTP sink, cannot be allowlisted, and must not be added (C-010).

---

## Open Items — things the spec leaves underspecified or mis-sequenced

Recorded here so the implementer resolves them deliberately rather than by accident. Each names the
reading this plan adopts.

1. **FR-012's "byte-identical across the two paths for the same verdict" is vacuous as written.**
   Binding kind is a field of the verdict, and the local gate only ever sees `local` while the SaaS
   gate only ever sees `saas`, so no single verdict value can be produced by both paths. **Reading
   adopted:** one message-composition function, no path-local message strings anywhere; plus SC-016's
   independently checkable pin that the three measured Channel-1 outcomes on the SaaS path reproduce
   **byte-identically to today's**. A tasks-phase test should assert the message text is produced by
   the verdict object and never re-composed at a raise site.

2. **`tracker_egress_verdict` must accept `root: Path | None`.** `SaaSTrackerClient._request` passes
   `self._project_root`, which is `Path | None` (`saas_client.py:~240`), and today
   `project_egress_refusal(None)` returns `UNDETERMINED_PROJECT_REFUSAL`. **Resolved in `spec.md`
   FR-005/FR-016:** the signature is `root: Path | None, *, destination: EgressDestination`; `None`
   is reachable **only** from `_request`, so it is always `HOSTED_SERVICE` with Channel-2 value
   `absent` (no file to read), and a message byte-identical to `UNDETERMINED_PROJECT_REFUSAL`. The
   `none` binding kind that the previous revision needed for this case no longer exists.

3. **US5 sc1's red cannot be the HTTP count.** `_request` raises at `_fetch_access_token_sync()`
   before any HTTP is attempted, so "0 HTTP attempts" is **already green on the base** for a `jira`
   binding with a committed `tracker: {egress: refused}`. **Reading adopted:** the red-first pin for
   the SaaS half is the **exception type and message** (`TrackerEgressRefusedError` naming Channel 2,
   versus today's `No valid access token`); the HTTP count is retained as a supporting non-vacuity
   assertion, proven to bind by US5 sc3's control.

4. **The brief and `spec.md` disagree about `test_sync_doctor_consent_health_3030.py:366`.** The brief
   lists it as blast radius that "will move"; `spec.md` FR-014, US7 sc5 and SC-014 require
   `flat.count("REPAIR THE FILE'S SYNTAX")` to remain **exactly 4**. **Reading adopted: the spec.** The
   test is a **detection signal**, not a planned edit — if it moves, the new block routed through the
   fault renderer, which is the defect FR-014 exists to prevent.

5. **FR-009's red does not exist on the base.** On `bb2020fea`, `egress` is an unknown key handled by
   `_extra`, so a "bind plants no null" pin is vacuously green. The defect is **created** by FR-002's
   promotion to `_KNOWN_KEYS`. **Reading adopted:** the pin is written with FR-002, observed red on
   the FR-002-only tree, and only then closed by FR-009. An implementer who lands FR-002 and FR-009
   in one commit ships FR-009 untested.

6. **The `TestSyncOperations` repair is order-dependent on FR-011, and C-012 does not say so.** The
   `repo` fixture creates only `.kittify/` with no `config.yaml`, and `_setup_bound_service` calls
   `svc.bind(...)`, which builds a **fresh** `TrackerProjectConfig` — so a pre-seeded `tracker:
   {egress: permitted}` is erased by the `bind()` unless FR-011 has landed. **Reading adopted:** FR-011
   lands before FR-001 (Stage 2 before Stage 4); the repair is then a genuine one-line committed
   config change and SC-020's claim holds. **Correction to how this was argued:** the previous
   revision said the alternative repair (patching the gate out in that test) was *"forbidden"* by
   FR-018 H2. It is not — `TestSyncOperations` is a **pre-existing unit test**, H2 is scoped to the
   new **acceptance** tests and their named seams, and SC-020 explicitly permits `_build_engine` to
   stay patched there for its own delegation assertions. The argument that holds is the *criterion*:
   gate-first makes *"the repair is one committed config line in the fixture repo"* **unsatisfiable**.
   The other two Stage-2 reasons stand untouched and are independently sufficient.

7. **FR-015 G3 says the gate call must be the "first statement" of each method body.** An AST check
   must tolerate a docstring as the first *node* while still requiring the gate to be the first
   *executable* statement. Minor, but a naive implementation will either reject a docstring or accept
   a statement before the gate.

8. **FR-018 H2's patching prohibition needs a scope statement.** It is scoped to the acceptance tests
   and to the named seams. The unit pins that force the Channel-1 classifier's three labels (C-004)
   must patch that classifier by name; reading H2 as a blanket ban would make C-004's
   non-authoritativeness proof unwritable.

9. **`_extra`'s consumers remain unaudited** (C-019 (3)). Carried unresolved. The known-field
   placement is the mitigation, not the answer. **Sharpened by this revision:** two of `_extra`'s
   consumers are now *known* — `saas_service.py:219` and `:316` — and they are consumers this
   Mission's own field promotion **breaks**. The unaudited remainder is what is left after those two.

10. **Two hazards are sequenced only implicitly by the FR numbering**: item 5 above (FR-009's red is
    manufactured by FR-002) and item 6 (FR-011 gates FR-001's blast-radius repair criterion). Both
    are made explicit in *Sequencing* because an implementer following the FR numbering alone would
    hit them in the wrong order. **A third has been added by this revision**: FR-002's promotion
    breaks FR-011's class-B sites, which is why IC-02 and IC-03 land as one change set.

11. **The doctor renderer's call count versus G4's membership count.** `spec.md` FR-014 requires one
    row per destination, and FR-003/G4 pin the call sites. These are reconciled by counting **two
    different things**: G4 asserts the set of **enclosing functions** is exactly five *and* the number
    of **call expressions** is exactly six. An implementer who reads "five call sites" as "five call
    expressions" will write a doctor renderer that loops over `EgressDestination`, which **G5 then
    rejects** because the loop variable is a `Name`, not a literal member. Both assertions are
    deliberate and both are exact; do not collapse them into one number.

12. **The upstream `#3108` issue text and `egress-inventory.md` entry E20 remain wrong** and this
    Mission does not correct them in place. The Problem section of `spec.md` states the correction
    with its measurement. Whether to comment on the issue is a tasks-phase call.
