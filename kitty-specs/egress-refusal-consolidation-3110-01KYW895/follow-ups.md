# Follow-ups — `egress-refusal-consolidation-3110-01KYW895`

Everything here was **found and deliberately not folded in**. Each entry says what
it is, why it was left, and what would make it worth doing — because a follow-up
without a reason reads as an oversight, and the next reader cannot tell which.

The spec's own follow-up table (FU-1…FU-8) is the design-phase set. This file is
the **implementation-phase** set: what the five review rounds surfaced.

---

## Filed for upstream — not this mission's code

**FU-A — `active_job_keys` does not gate on `on.pull_request.branches`.**
`tests/architectural/_gate_coverage.py` checks the trigger only for `push`
(`if event_name == PUSH_EVENT and not workflow_runs_on_push(...)`). For
`pull_request` every workflow's jobs are considered regardless of whether that
workflow triggers on `pull_request` at all. Harmless for every assertion this
mission makes — all conclusions are keyed to `('ci-quality.yml', <job>)` tuples and
that workflow does trigger on `pull_request` — and it errs toward
**over-approximating** selection, the direction that makes a positive assertion
easier to pass. Pre-existing; noted so a successor does not rediscover it as a
WP02 defect. *Worth doing when:* anyone relies on `active_job_keys` for a workflow
whose `pull_request` trigger is conditional.

**FU-B — the dead qualname comparison in both `invocation/adapters.py` registrars.**
`register_egress_consent_resolver` and `register_saas_client_factory` both compute
`existing_key == new_key` and then assign `fn` in **both** arms, so the comparison
changes only the control flow taken to reach an identical assignment. Measured: a
callable with a *different* `__qualname__` replaces the entry just as completely.
WP05 corrected the docstring that misdescribed it (LOW-2) but left the code:
removing it from both registrars is a behaviour-preserving simplification in a
seam this mission was scoped to *keep and pin*, not to refactor. *Worth doing when:*
anyone revisits the `#3109` seam — see D-1's falsifiers.

**FU-C — the upstream ownership-validator defect** (carried from the handoff §9).
The validator documents a helper for "a planning-artifact WP that legitimately owns
nothing", with a docstring and a regression test saying so — but the manifest
builder silently drops any WP with an empty ownership list, and the lane computer
then treats the missing manifest as a hard error. The documented intent has no path
to a green run.

---

## Carried residuals — recorded, not fixed

**FU-D — `#3113`'s all-positional blind spot remains, by non-adoption.**
`_transmits_a_body` in `tests/architectural/test_egress_consent_boundary.py` derives
kwargs from `node.keywords` only, so a fully positional `poster(url, data, headers)`
is not classified as a sink. `#3113` is **CLOSED** — the matcher tightening was
*declined* at a measured cost and two positional shapes are pinned as
`xfail(strict=True)`. **Non-adoption is the resolution, not a deferral.** This does
**not** bound this mission's attribution guards, which match by class name and count
every match regardless of call form. Do not credit any coverage claim here to `#3113`.

**FU-E — bind mounts are invisible to path-based containment.**
`mount --bind B/kitty-specs A/kitty-specs` is transparent to `realpath`, so WP04's
containment checks cannot see it. Requires root to arrange and is indistinguishable
from a copy at the VFS layer, so there is no second path to compare against. An
inherent limit of the approach rather than a defect. *Worth doing when:* a
requirement appears for ownership to survive a hostile local filesystem — which
would need a different mechanism entirely, not a stricter path check.

**FU-F — SC-015's scan scope diverged from the spec and was reconciled toward the
spec.** SC-015's POST-ACCEPTANCE CORRECTION mandates a scan over `src/`; WP03's
T021(a) narrowed it to `src/specify_cli/**`. The narrower form shipped first, then
was widened. Recorded because the **spec and the WP contract still disagree in
text** — reconcile SC-015's wording next time it is touched, rather than leaving a
future implementer to pick.

**FU-G — `#3115`'s sync half is still open** (deferred to `#3136`). Every green on
this mission's test surface was taken as an **isolated single-file run**; a
full-suite red here is not attributable. This is a standing condition on the whole
mission's evidence, not a defect in it.

---

## Post-merge obligations — these have owners, not just notes

**FU-H — SC-006's `[one-off]` half.** Structurally unobtainable in-mission:
`.github/workflows/ci-quality.yml` is itself the first entry of the `core_misc` glob
list, so any PR editing it selects `fast-tests-core-misc` **for that reason** — a
tautology that looks exactly like proof. Carrier is **folded into the repo**, in the
docstring of `test_ci_quality_workflow_file_is_itself_a_core_misc_glob`, which reds
if the confound ever disappears. It states what is owed, why the mission PR cannot
supply it, why the stacked-PR substitute is inoperative, the procedure
(`packs/built-in/procedures/post-merge-arch-gate-adjudication.procedure.yaml`) and
an accept/reject condition checkable by a stranger.

**FU-I — observe the `specify-cli-rest` shard actually execute.** Every claim that
WP03's discriminating module *runs* rests on `_gate_coverage`'s parse of the workflow
YAML plus a reading of the job's `if:`. They agree, and the model uses pytest's own
expression evaluator — but **no CI run has been observed**. WP07 watching that shard
execute closes the last inch.

---

## Implementation-phase follow-ups, round 2 — residual remediation

Recorded under an explicit operator decision to **freeze residual work** so the
mission could finish WP06 and WP07. Each was found by review, graded LOW, and is
fail-closed. None is a fix-round item.

**FU-J — the LOW-4 re-key prescribes `chmod` for a MALFORMED ledger. This is a
regression I introduced, not a pre-existing defect.**
`src/specify_cli/decisions/ownership.py:661` — `if outcome.unreadable_ledgers:`

LOW-4 widened the remedy's key from a conjunction to `unreadable_ledgers` alone,
which correctly fixed the likelier EACCES-mixed row. But that tuple **conflates two
causes**, and the module's own docstring says so at `:87-89`: malformed
(`JSONDecodeError` / `ValidationError`) and unreadable (`OSError`) both set the same
flag. So a corrupt-ledger operator is now told to `chmod u+rx`, where no mode bit
is wrong — the file's *contents* are. Measured on both the corrupt-JSON and
schema-invalid rows.

Before the re-key that row got bare `git pull`, which is at least defensible
(`git checkout --` does restore a corrupt tracked file). Now it gets an instruction
that is never right. **Same wrong-operator-action class as LOW-6 / LOW-7 / LOW-1,
moved rather than removed** — which is worth stating plainly, because "I fixed the
diagnosis" was the claim and it was only two-thirds true.

Net still a win: the row it fixed is both likelier and more actionable, the verdict
is correct, and nothing transmits. *Fix:* carry the cause per entry the way
`specs_root_fault` does one level up — split `_LedgerRead.unreadable` into
`unreadable` vs `malformed`. Cheaper interim: name both possibilities in the
remedy. Either way add the two measured rows as controls, since nothing currently
distinguishes them. *Falsifier:* if `_read_ledger` set the flag only for `OSError`.
It does not — `:450` catches all three into one `unreadable=True`.

**FU-K — the AST guard's try-context rule ignores the handler type.**
`tests/specify_cli/decisions/test_ownership_3111.py:1089-1095`. `try: p.stat()` /
`except ValueError:` satisfies the rule while `OSError` still escapes — the failure
mode the rule exists to prevent. No live defect: all three real handlers catch
`OSError`. Left deliberately, and the docstring states what is implemented rather
than overclaiming, which was the original objection. *Fix if it matters:* require
the enclosing `ast.Try` to carry a handler of `OSError`/`Exception`/`BaseException`
or a bare `except`.

**FU-L — `unreadable_ledgers` is a published field with mixed-kind contents.**
It now carries mission-*directory* names as well as ledger names, and is exposed in
the `--dry-run` payload under that key. LOW-2 corrected the prose; the field name
and its JSON key were not touched, so a machine consumer parsing it as ledger paths
still gets a wrong answer. Cosmetic, out of scope for WP04.

---

### A method note worth keeping

Three of this mission's invalid measurements shared one shape: **an exit status or
a path that was not the one the measurer believed**. `EXIT=$?` placed after a
`$(...)` reported the substitution's status. `pytest` "reds" that were `EXIT=4`
usage errors from a syntax-broken plant. A reviewer whose shell cwd defaulted to a
different lane than the one under review.

Each was caught the same way: by asserting the environment *in process* before
measuring — `assert LANE_C in ownership.__file__`, `git rev-parse HEAD` compared to
the expected commit, an anti-vacuity assertion placed **before** the value being
reported. That practice belongs in this mission's record, because the defects it
catches are indistinguishable from real results in the output.

**FU-M — the guards' single-source logic has a helper-bypass bound. Recorded as a
known limit, not as work.**

`_repo_relative` (report-path arithmetic) and `_saas_site_attribution` /
`_tracker_site_attribution` (attribution logic) are each **single-source by
construction**, which is what makes their pins able to fail. The bound: a future
edit that *re-implements* rather than *calls* one of them is outside what either
guard can observe. No runtime assertion can see which expression another line uses
— that is why the fix for F1b was collapsing the arithmetic to one call site rather
than pinning it harder.

Both helpers' docstrings state this. It is the same "one object, two callers" limit
the predicates have carried since WP01, and it is unavoidable at this level. **No
action implied** — recorded so a successor does not mistake the pins for coverage
of that case, and does not "strengthen" them in a way that cannot work.

Related, and stated so the pin is not over-read: the base pin's expected value is
the literal `"src/specify_cli/egress.py"`, so it pins the helper's base **and**
that `_SRC_TREE` ends in `src`. `_SRC_TREE` itself is anchored only by being a
literal. That is the right place to stop — anchoring the anchor is not a thing.

---

## WP06 discoveries — two the WP prompt did not enumerate

**FU-N — a SECOND docs lockfile, owned by nobody. WP07 must take it or the mission
lands red.**
`docs/development/3-2-docs-retrieval-index.yaml`

The WP prompts name `docs/development/3-2-page-inventory.yaml` and the ADR era
README as WP07's reconciliation work. There is a **second** 1:1 docs lockfile with
its own schema (`path` / `title` / `divio_type` / `abstract` / `anchors`), whose
drift is `severity=error` via `DOCS-INDEX-DRIFT` and therefore reds
`docs-freshness` exactly as the inventory does. **It is in no WP's `owned_files`
and not in lane-planning's `write_scope`**, and `freshen_adr_inventory.py` does
**not** reconcile it.

WP06 produces two rows: `added` for the new ADR, `changed` for `docs/context/identity.md`.
The `changed` row is forced and measured, not assumed — rebuilding it from the
pre-change body plus the new frontmatter yields a row identical to base, while HEAD
differs by exactly one added anchor (`engagement`), so the `updated`/`related` bump
contributes nothing and the anchor is required by FR-023.

Reconciled by `python scripts/docs/docs_index.py --write`. **Assign to WP07.**

**FU-O — the docs baseline in the WP prompts is stale.** WP06's prompt states
685/685 clean. Measured on this branch *before* WP06 wrote anything:
**689/689 clean** (`check_docs_freshness: exit=0 findings=0`). The number moved
upstream between design and implementation. Not a defect; recorded so a successor
does not read a 689 baseline as pre-existing drift.

**FU-P — a profile-wrapper contradiction, flagged rather than resolved silently.**
`curator-carla`'s generated wrapper carries a read-only "Hard boundary" clause that
contradicts WP06's own `role: implementer` / `execution_mode: code_change`. The
agent followed the dispatch and reported the drift instead of picking one silently.
Looks like a reviewer-slot default leaking into an implementer dispatch. Worth
filing upstream against the profile generator, not against this mission.

---

## FU-Q — the 3.13+ regression in LOW-8's own fix. FILED AS #3177.

**Tracker: https://github.com/Priivacy-ai/spec-kitty/issues/3177**

Filed because every other residual here is anchored to a number (#3113, #3115,
#3136) and this one was prose in a dossier that stops being anybody's inbox the
moment this PR merges — the same unowned-note problem SC-006's carrier exists to
avoid. A live regression in shipped code needs an owner, not a record.

`src/specify_cli/decisions/ownership.py:387-388`

`resolved.is_dir()` **raises** `PermissionError` on 3.11/3.12 and **returns `False`** on 3.14.
LOW-8's drop-recording (`unreadable.append(candidate.name)`) hangs off the
`except OSError` on the following line. So on 3.13+ control takes the bare
`continue`, the dropped candidate is never recorded, and the operator is told
*"no missions were found … run `git pull`"* for a permission problem — **LOW-8's
original defect, verbatim, reintroduced by LOW-8's fix.**

Measured with a control first: `test_ownership_3111.py` is **33 passed** on 3.11.15
and **2 failed, 31 passed** on 3.14.4. Full mechanism, both refusal strings and the
line-level trace are in
`docs/plans/engineering-notes/01KYW895-verification-evidence.md`.

**Fail-closed** — `owned=False`, nothing transmits — so this is a *diagnosis*
defect, not a leak. But `requires-python = ">=3.11"` makes 3.13/3.14 supported, and
**no CI job runs the test suite on 3.13+, so CI cannot see it.**

That sentence originally read *"CI runs only 3.11/3.12"*, which was **false and
understated**. CI provisions 3.13 in two jobs — `build-wheel` (`ci-quality.yml:3848`)
and `clean-install-verification` (`:3898`) — and **neither runs pytest** (both job
bodies parsed; census across 17 workflows: 3x`3.11`, 58x`3.12`, 2x`3.13`).
`clean-install-verification` imports `specify_cli` and runs `spec-kitty next` on 3.13,
so 3.13 is a **supported surface that no suite covers** — a stronger statement than the
one it replaces, and the sentence carries FU-Q's severity grade.

**3.12 was measured** and does NOT diverge: `33 passed` on 3.11.15 and 3.12.13 alike,
`2 failed, 31 passed` on 3.14.4, same `pytest 9.0.3` in venvs so the HOME/user-site trap
is excluded. The grading is confirmed rather than upset.

The module's own docstring is the sharpest evidence: it removes `Path.exists()`
three times *because* the call is EACCES-divergent, states the `is_dir()`
divergence explicitly — and then reads 3.14's non-raise as *"a clean refusal on
3.14"*. It is not a clean refusal.

*Fix:* record the drop on **both** exits, not only the handler — or route the
candidate through the same explicit-probe idiom `_read_ledger` already uses, which
is the module's own answer to this exact divergence. Add a 3.14 row to the control.

*Falsifier:* if `is_dir()` raised on 3.13+. It does not; probed with a readable
control in the same run.

---

## Addendum to the method note — a fifth instance, and it corrupted a record

The append-only `status.events.jsonl` note for WP07's `for_review` transition is
**corrupted**. Backticks inside a double-quoted bash string were executed as
command substitution: `` `except OSError` `` ran, `bash: except: command not
found`, and its empty output was substituted. The note now reads *"hangs off  under
resolved.is_dir()"* — the mechanism, the single most important phrase in it, silently
deleted. The event log cannot be rewritten, so **the evidence file above is
authoritative for FU-Q**, and it carries the mechanism in full.

Fifth instance of the one shape that has produced every invalid measurement on this
mission: **the tooling did something other than what the measurer believed.**
`EXIT=$?` after a `$(...)`. `EXIT=4` pytest usage errors read as kills. A shell cwd
defaulting to the wrong lane. `HOME` replacement moving pytest to the user site.
Now backticks in a quoted string.

None of these is a reasoning error. Each is an unexamined assumption about a tool,
and each produced output indistinguishable from a real result. The countermeasure is
unchanged and is the reason it is recorded rather than the incidents: **assert the
environment in process before measuring, and read the value you are about to report
rather than the one you expect.**

---

## Pre-merge gate findings carried forward

The gate returned **eleven** confirmed findings. Two HIGH were fixed (the dead-code
ratchet at `8996bbfe1`, FR-003's fakeable differential at `a038f56fb`), two
HIGH/MEDIUM were the stale `in-mission` verdicts now resolved to `fixed`, and two
were closed by filing #3177. These four remain, each measured by the gate.

**FU-R (MEDIUM, security) — the env-credential route survives #3111's laundering,
and spec.md's fold of FR-007 into FR-002 is false there.**

The destination team is resolved from ambient env vars **before** the per-project
auth file. So with ownership *legitimately* established, an operator carrying
`SPEC_KITTY_TEAM_SLUG` (or an env token) for a different team sends the acting
checkout's own decision identifier to **that** team. Ownership is not the defence
here — the destination is, and nothing checks it.

This is narrower than `#3111` (it needs env credentials for a team you do not own)
and it is **not** the closed defect: `#3111` was another project's record going to
your team; this is your record going to another team. The gate's own note that the
spec *folds* FR-007 into FR-002 is the part worth keeping — that fold reads as
discharged and is not.

*Fix, per the gate:* before `post_widen`, assert the resolved `team_slug`/token came
from the acting root's `.kittify/saas-auth.json`, or that an env-supplied
`SPEC_KITTY_TEAM_SLUG` matches the acting root's recorded team, and refuse otherwise.
*Or* state explicitly in the spec that FR-007 is not discharged by FR-002. Do not
leave the fold.

**FU-S (MEDIUM) — the AST guard passes on the code carrying FU-Q's defect, and that
is my fix's fault.**

`test_ownership_3111.py`'s standing guard bans `exists` outright and permits the rest
of the stat family **inside a `try`**. But a `try` does not make `is_dir()`
interpreter-independent: `ownership.py:387` is inside a `try`, and it is exactly the
line that returns `False` on 3.14 instead of raising. So the guard built to prevent
this EACCES class passes on the instance of it.

I shaped that guard to the *spelling* rather than the *hazard*. The try-context rule
was the right answer for a call whose raise is handled; it is the wrong answer for
one whose **non-raise** is the defect.

*Fix:* ban the family outright in favour of the module's own `open()`/`iterdir()`
probe idiom, or require that a guarded stat call's non-raising result be routed into
the same recording path. Add a controlled known-bad source — a try-wrapped `is_dir()`
whose `False` branch drops silently — and confirm the guard reds on it. Related to
FU-K, which is the same guard's handler-type blind spot.

**FU-T (LOW) — `ownership.py` republishes another module's private `_ULID_RE` as a
public `__all__` name**, creating a second public identity for an intentionally
private symbol. *Fix:* rename it to a public `ULID_RE` at
`src/specify_cli/invocation/record.py:30` and import that, so there is one public
spelling rather than a public alias for a private one. The module comment's "three
exist" count also omits `audit/`.

**FU-U (LOW) — FR-018's docstring-truth half (SC-023) has no standing assertion**
while its sibling FR-019 export half does, so the false sentence this mission removed
can silently return. *Fix:* three assertions beside the export pin in
`tests/invocation/test_adapters.py` — `request_text` present, "Called once at sync
package startup" absent from `register_saas_client_factory.__doc__` and present on
the sibling registrar, which is where it is true.
