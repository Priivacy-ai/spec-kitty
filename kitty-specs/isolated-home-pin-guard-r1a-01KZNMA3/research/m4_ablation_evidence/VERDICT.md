# WP01 — Pre-convergence pin-ablation verdict (SC-012, amendment A19)

> **VERDICT: `|P| = 5` → THE MISSION HALTS**, pending explicit operator sign-off.
> Halt ceremony: `spec.md:219` / `plan.md` §IC-01. A `blocked` WP status alone is **not**
> sufficient — see §8.

Pre-convergence commit SHA: **`509f3ff850c01b4b83dd136c094e731af1f42011`** (branch
`spike/isolated-home-3121`). Environment fingerprint and C-008 baseline: [`anchor.md`](anchor.md).

---

## 1. The four A19 elements (SC-012)

| # | Element | Where |
|---|---|---|
| (i) | **Recorded raw instrument output**, actual captured output | `baseline/raw-output.txt`, `arm1/raw-output.txt`, `repeated/raw-output.txt`, `arm2/raw-output.txt`, `arm2/control/raw-output.txt`, `baseline/seamB/raw-output.txt`, `nfr005/raw-output.txt`, `arm2/demo/raw-*.txt`, and superseded runs under `superseded/` |
| (ii) | **Per-member node-ID outcome sets**, all three arms | `*/records/record-master.json` → `outcomes` (node ID → `pass/fail/error/skip/xfail`), `fired_for`, `execution_order`, `body_entry`, `suppressed_mkdirs` |
| (iii) | **Exact invocation per arm** including `-p`, `-n`, `--dist` | §7 below, and `*/INVOCATION.txt` |
| (iv) | **Reviewer can re-run and reproduce the same set** | §7 (verbatim commands) + §9 (independent reproduction by a different actor) |

The instrument is `scripts/mutants/ablate_home_pin_3121.py` (this WP's only `create_intent`).

---

## 2. FR-017's null hypothesis — stated PER PARTITION

FR-017 requires this emitted verbatim:

> `SPEC_KITTY_HOME` is consulted **first** and returned unchanged
> (`src/specify_cli/runtime/home.py:33`, `src/kernel/paths.py:47`); with it popped, POSIX
> resolution falls through to `Path.home() / ".kittify"`, and `Path.home()` reads `HOME`, which
> the root-conftest autouse `_isolated_worker_home` (`tests/conftest.py:253`) has **already**
> pointed at the **per-worker** isolated home.

**That hypothesis is TRUE for 17 of the 28 and FALSE for 11.** Re-derived here by binding-resolving
AST, independently reproducing the figures in the WP prompt:

| Partition | n | `HOME` at test-body entry | Fallback with the pin popped | Hypothesis true? |
|---|---|---|---|---|
| **A** — does not re-pin `HOME` | **17** | per-worker isolated home | `<per-worker home>/.kittify` — **shared across tests on that worker** | **yes** |
| **B1** — re-pins `HOME` → `tmp_path/"home"` | **9** | `tmp_path/"home"` | `tmp_path/"home"/".kittify"` — **still per-test** | **no** |
| **B2** — re-pins `HOME` → `tmp_path/"user-home"` | **2** | `tmp_path/"user-home"` | `tmp_path/"user-home"/".kittify"` — **still per-test** | **no** |

`monkeypatch.setenv` is last-write-wins and the member's fixture runs *after* the root autouse
queue, so for partition B the root conftest's value is overwritten and the stated fallback never
happens.

### Partition treatment: **(ii), the DEFAULT — recorded with its cause (DIR-003)**

**Partition B (11 members) is excluded from `P` by construction.** Cause, in full:

1. The repeated/interleaved arm is **structurally incapable of reding partition B**. Its premise is
   *shared worker home ⇒ cross-test interference*; partition B's fallback home is **per-test**, so
   there is no interference to detect. The corrective arm would be **green-by-construction on
   exactly the members it is least able to vouch for**.
2. A partition-B pass licenses only *"redundant **given this module's own `HOME` pin**"* — and
   **FR-003 and FR-014 require that `HOME` pin to stay local**. It therefore supports nothing about
   deletion.
3. Treatment (i) measures a counterfactual **FR-003/FR-014 prevent the Mission from ever
   realising** (a tree with neither pin), which is why it is a diagnostic and not the default.

**Treatment (i) was NOT taken.** No `HOME` or `USERPROFILE` was re-pointed and — decisively —
**none was ever REMOVED**. See §6.

**The `|P| ≥ 5` trigger is evaluated against partition A, the partition actually measured.**

Robustness note, stated honestly as an **argument, not a measurement**: the repeated/interleaved arm
was **not** run over partition B (treatment (ii) excludes it), so no measured partition-B verdict
exists. The argument is set-theoretic — `P ⊆ P_including_B` by construction, and arm 1 alone already
leaves `|P1| = 15` — so **including partition B could only increase `|P|`**, and the halt cannot be
escaped by changing the partition treatment. That is sound but it is a bound, not evidence, and it
is labelled as such at an independent reviewer's insistence.

---

## 3. Verdict routing

`P` = members passing **arm 1** *and* the **repeated/interleaved arm**, computed under treatment (ii).

**`|P| = 5`.**

| Verdict | Consequence | Applies? |
|---|---|---|
| `P = ∅` | Proceed | no |
| `1 ≤ \|P\| < 5` | Nothing converges until each member of `P` is individually adjudicated (WP03) | no |
| **`\|P\| ≥ 5`** | **The Mission HALTS pending explicit operator sign-off** | **YES** |

`N = 5` is not a tunable knob: `plan.md` §0.6 rejected a deletion prize of **4 of 28** as not worth
its risk, and 5 is the smallest prize strictly larger than the one the Mission already refused.
`|P| = 5` lands exactly on that threshold.

**No count gates anything (C-002).** `|P|` is a routing trigger over a **published set** (§4);
`27/28 = 96%` appears nowhere as a gate.

---

## 4. `P`, published as a set

<!-- TABLES:BEGIN -->
See [`TABLES.md`](TABLES.md) for the full per-member table over all 28 and the `P` table, both
generated directly from the raw records (never transcribed). Machine-readable: [`P.json`](P.json).
<!-- TABLES:END -->

`P` keyed `(file, qualified_name)`, each with its partition:

| # | file | qualified_name | partition |
|---|---|---|---|
| 1 | `tests/delivery/test_body_queue_purge_differential_3030.py` | `_isolated_home` | A |
| 2 | `tests/delivery/test_purge_all_body_uploads_3030.py` | `_isolated_home` | A |
| 3 | `tests/delivery/test_purge_all_events_3030.py` | `_isolated_home` | A |
| 4 | `tests/specify_cli/identity/test_identity_value_faults_3030.py` | `TestThePolicyGateAnswersInsteadOfCrashing._isolated_home` | A |
| 5 | `tests/sync/test_daemon_publish_consent_3030.py` | `_isolated_home` | A |

**Scope caveat on member 4, for WP03's adjudication.** `test_identity_value_faults_3030.py` holds
147 tests, but its member is a `self`-bound **class-method** fixture, so it governs only the **6**
tests inside `TestThePolicyGateAnswersInsteadOfCrashing`. The module-level "passes under arm 1"
verdict is therefore carried by 147 nodes while the **ablation itself touched 6**. Those 6 were
individually confirmed: pin **present** at body entry in baseline, **absent** under arm 1,
`home_ok=True`, all `pass`. The other 141 nodes are not evidence about this pin either way.

This is also the member whose `baseid` is class-qualified
(`…test_identity_value_faults_3030.py::TestThePolicyGateAnswersInsteadOfCrashing`), and the one an
earlier revision of this instrument silently failed to bind — see `RESIDUALS.md` R5.

---

## 5. Arm 1 — and the proof it was not merely broken

Arm 1 lets each member's real fixture run, then removes **only** `SPEC_KITTY_HOME` (C-001: zero
source edits). Over **all 28**: **491 pass / 35 fail / 0 error** (526 nodes).

A broken hookwrapper would red all 28 as **setup errors**, record 28 non-passes, yield `P = ∅` and
**greenlight the Mission** — the direction that also makes this WP's three most expensive
obligations vacuous. FR-011's zero-ablation refusal catches *"bound nothing"*; it cannot catch
*"bound and broke everything"*. Four independent gates close that:

| Gate | Result |
|---|---|
| Outcome kind recorded per node ID incl. `error`; **any `error` voids the run** | **0 errors** across 526 nodes |
| Sites actually bound (`expected` vs `observed`) | **28 / 28**, `missing_sites: []` |
| Every red **attributed** to a fired-for node ID of the ablated site | **0 unattributed reds** |
| **Runtime effect confirmation** | **28/28 members** |

### Runtime effect confirmation (T004 step 4)

For **all 28 members**, every fired-for node had `SPEC_KITTY_HOME` **present** at test-body entry in
the baseline and **absent** under arm 1. Named example:

```
member : _consent@tests/delivery/test_liveness_predicate_before_limit_3030.py
node   : tests/delivery/test_liveness_predicate_before_limit_3030.py::test_a_delivered_prefix_must_not_starve_the_undelivered_tail
baseline : SPEC_KITTY_HOME = /tmp/pytest-of-.../test_a_delivered_prefix_must_n0/home   (present=True)
arm1     : SPEC_KITTY_HOME = None                                                       (present=False)
arm1     : Path.home()     = /tmp/spec-kitty-test-homes/serial-<pid>/master   home_ok=True
```

`P1` (arm-1 passers) = **15** members: 5 in partition A, 10 in partition B.
Under treatment (ii) only the **5 partition-A** members are candidates for `P`.

### C-008 subtraction

The baseline-red set is **empty** (543/543 pass across the 33 touched modules), so nothing was
subtracted and nothing was green-washed. See [`anchor.md`](anchor.md).

### NFR-005 / DoD 5 — `-n0` vs `-n auto --dist loadfile`, and a finding

Arm 1 was re-run over all 28 under `-n auto --dist loadfile` (`nfr005/raw-output.txt`, banner
`created: 8/8 workers`). Two different things must be separated here, and only the first is what
NFR-005 binds on the plugin:

**The plugin's own verdict is IDENTICAL under both.**

| plugin verdict field | `-n0` | `-n auto --dist loadfile` | identical |
|---|---|---|---|
| `member_count` | 28 | 28 | yes |
| `expected_sites` | 28 | 28 | yes |
| `observed_sites` | 28 | 28 | yes |
| `missing_sites` | 0 | 0 | yes |
| `verdict_refused` | False | False | yes |
| `home_violations` | 0 | 0 (all workers) | yes |

The controller merged **28/28** sites from `workeroutput` and did **not** refuse — i.e. the parallel
run does not report zero suppressions, which is exactly what NFR-005 asks for. The `-n0` arm does
not crash on the absent `workeroutput`, because the access is guarded with
`getattr(config, "workeroutput", None)`.

**But the ABLATED SUITE's outcome set is parallelism-dependent — 7 nodes differ.**

| | `-n0` | xdist |
|---|---|---|
| arm-1 outcomes | 491 pass / **35 fail** | 498 pass / **28 fail** |
| `P1` | **15** | **16** |

All 7 differing nodes go the **same way — red under `-n0`, pass under xdist** — across
`test_body_drain_consent_3030.py` (3), `test_ws_publish_consent_3030.py` (2) and
`test_consent_resolver_3030.py` (2). `P1` symmetric difference =
`{tests/sync/test_ws_publish_consent_3030.py}` (partition A).

This is **not** an instrument defect; it is the phenomenon under measurement. Arm 1 pops the pin, so
resolution falls back to `Path.home()/".kittify"` — the **per-worker** home. Under `-n0` a single
home is shared by all 526 tests; under 8 workers with `--dist loadfile` there are 8 homes and a
file's tests share with far fewer others. Less sharing ⇒ less cross-test interference ⇒ fewer reds.
That parallelism-sensitivity *is* FR-017's premise showing up directly.

**`-n0` is taken as authoritative for `P`**, for two reasons: T005 mandates `-n0` for the corrective
arm, and `-n0` is the strictly **more conservative** measurement — it is more red, therefore yields
the **smaller** `P1`, therefore is the **least** likely to trigger the halt. The halt is reported on
the measurement least favourable to it.

**The halt is robust to this discrepancy.** Under xdist `P1 ∩ A` = 6, so `|P|` could only be larger.
Under either distribution, and under either partition treatment, `|P| ≥ 5`.

---

## 6. `Path.home()` safety — DoD 2a

**`HOME` and `USERPROFILE` were never REMOVED by the instrument, on any arm.** The instrument
removes `SPEC_KITTY_HOME` and nothing else. Removal would not restore per-worker isolation, it
would **delete** isolation: with both unset, `Path.home()` falls through `os.path.expanduser` to
`pwd` and returns the operator's **real** home, and 26 of the 28 members reach production code that
calls `home.mkdir(parents=True, exist_ok=True)` (`src/specify_cli/runtime/bootstrap.py:170`).

Every test-body entry on every arm was checked (`home_ok`) against `tmp_path`, the per-worker
isolated base, and `SPEC_KITTY_REAL_HOME_FOR_TESTS`:

| Run | nodes | `home_violations` |
|---|---|---|
| baseline (28) | 526 | **0** |
| arm 1 (28) | 526 | **0** |
| repeated/interleaved | 392 | **0** |
| arm 2 (28) | 526 | **0** |
| arm 2 positive control | 101 | **0** |

**No run in this WP left `Path.home()` resolving outside `tmp_path` ∪ the per-worker base.** No run
was void; nothing was discarded on this ground.

---

## 7. Exact invocations (A19 element iii)

Copy-paste preamble — these two shell variables make every block below runnable **verbatim** from
the repository root (an independent reviewer flagged that the earlier abbreviated `evidence/…` paths
did not resolve from the root; they are now `$EV`-rooted):

```bash
cd /home/jeroennouws/dev/sk-missions/3121
EV=kitty-specs/isolated-home-pin-convergence-01KZCTWC/evidence/ablation
PY=<scratchpad>/venv3121/bin/python   # pytest 9.0.3, external venv, never inside the 3121 tree
```

Substitute `<PY>` with `$PY`. Every arm additionally has its own `INVOCATION.txt` beside its raw
output — including `arm1/` and `baseline/`, which an independent reviewer correctly flagged as
missing on the first pass. `-p ablate_home_pin_3121` is
load-bearing: without it the module is importable but never loaded, and the run reads as a clean
pass having ablated nothing.

```bash
# BASELINE (28) — also the C-008 classification and the effect-confirmation "present" side
PYTHONPATH=scripts/mutants <PY> -m pytest $(cat $EV/members-28.txt) \
  -p ablate_home_pin_3121 --ablate-mode=baseline \
  --ablate-out=$EV/baseline/records -n0 -p no:cacheprovider -rA

# BASELINE (5 Seam B) — C-008 completion over the 33 touched modules
PYTHONPATH=scripts/mutants <PY> -m pytest $(cat $EV/seamB-5.txt) \
  -p ablate_home_pin_3121 --ablate-mode=baseline \
  --ablate-out=$EV/baseline/seamB/records -n0 -p no:cacheprovider -rA

# ARM 1 (28)
PYTHONPATH=scripts/mutants <PY> -m pytest $(cat $EV/members-28.txt) \
  -p ablate_home_pin_3121 --ablate-mode=arm1 \
  --ablate-out=$EV/arm1/records -n0 -p no:cacheprovider -rA

# REPEATED / INTERLEAVED ARM over P1 ∩ partition A  — -n0, no --dist, no other -n
PYTHONPATH=scripts/mutants <PY> -m pytest $(cat $EV/repeated/P1-partitionA-members.txt) \
  -p ablate_home_pin_3121 --ablate-mode=arm1 \
  --ablate-only=<the 5 files, comma-separated> --ablate-interleave \
  --ablate-out=$EV/repeated/records \
  --count=2 --repeat-scope=session -n0 -p no:cacheprovider -rA

# ARM 2 POSITIVE CONTROL — run BEFORE arm 2 over P
PYTHONPATH=scripts/mutants <PY> -m pytest \
  tests/sync/test_consent_field_fault_3030.py tests/sync/test_consent_read_fault_3030.py \
  tests/cli/commands/test_sync_commands.py \
  -p ablate_home_pin_3121 --ablate-mode=arm2 --ablate-only=<those 3> \
  --ablate-out=$EV/arm2/control/records -n0 -p no:cacheprovider -rA

# ARM 2 (28, a superset of P)
PYTHONPATH=scripts/mutants <PY> -m pytest $(cat $EV/members-28.txt) \
  -p ablate_home_pin_3121 --ablate-mode=arm2 \
  --ablate-out=$EV/arm2/records -n0 -p no:cacheprovider -rA
```

### The `-n0` proof is on the OUTPUT, not on the string typed

`--dist loadfile` keeps a *file's* tests together but guarantees nothing about two **different**
files, so a silently non-interleaved run would report a clean pass that means nothing. Asserted on
the **captured output** of `repeated/raw-output.txt`:

* `created: N/N workers` banner — **absent** (0 matches)
* `gw0` / `gw1` node prefixes — **absent** (0 matches)
* recorded invocation contains `-n0`, and **no `--dist` and no other `-n`**

### Interleaving verified, not assumed

`--count=2 --repeat-scope=session` alone runs each test **twice back-to-back** and finishes one
module before starting the next — measured here; no other member ever runs between a member's two
runs, so the arm cannot observe cross-member interference at all. The instrument therefore
round-robins collected items across modules (`--ablate-interleave`), and the record carries an
**explicit `execution_order`** list (the JSON is serialised `sort_keys=True`, so insertion order is
not recoverable from it).

Verified from that explicit order:

* execution is round-robin across all 5 modules (`body_queue → purge_all_body_uploads →
  purge_all_events → identity_value_faults → daemon_publish`, repeating)
* **all 5 members**: re-run **≥2× in the same process**, and **interleaved** — another member's
  test executes between the member's first and last run
* per logical test, 85 of 196 have another member's test between their two repetitions (the
  largest module exhausts the smaller ones under round-robin; the **per-member** requirement is met
  for **5/5**)
* **outcome set identical each time**: 0 mismatches across repetitions
* 392 nodes, **0 errors**, **0 home violations**

---

## 8. Arm 2 — built and demonstrated FIRST, and SOUND

**Arm 2 = keep the pin, suppress the creation** (amendment A17) — orthogonal to arm 1, not a
superset of it. Its mechanism and scratch demonstration were completed **before `P` was computed**.

### The naive mechanism is physically defeated — demonstrated, not argued

The home is **re-created on demand by the code under test**: `get_kittify_home()` reads
`os.environ["SPEC_KITTY_HOME"]` — **the pin arm 2 deliberately keeps** — and
`bootstrap.py:170` calls `home.mkdir(parents=True, exist_ok=True)`. The tree says it in its own
words at `tests/sync/test_consent_fault_vocabulary_3030.py:59`: *"the resolver writes on read."*

Scratch demonstration (`<scratchpad>/demo`, raw output copied to `arm2/demo/`), on a fixture with
the exact member silhouette, **calling the real production entry point** `ensure_runtime()`:

| Test | baseline | arm 2 |
|---|---|---|
| `test_naive_rmtree_is_defeated_by_the_resolver` — `rmtree` the home, then call `ensure_runtime()`, assert it exists again | **PASS** — i.e. a post-setup `rmtree` **is undone**; naive arm 2 would report GREEN whatever the truth is | RED |
| `test_needs_the_directory_via_production` — `ensure_runtime()` → `get_kittify_home().mkdir(parents=True, exist_ok=True)` | PASS | **RED** — suppression held against production re-creation |
| `test_needs_the_directory_directly` — channel-B observer shape | PASS | **RED** |
| `test_touches_nothing` — provably never touches the directory | PASS | **GREEN** |

§3.7's arm-1 verification was **not** carried across; it measured arm 1 only.

The mechanism suppresses the creation seam (`Path.mkdir`, `os.makedirs`) **for the duration of the
test**, scoped to that member's `tmp_path/"home"` and installed **before** the fixture body runs —
because many members `mkdir` *before* they `setenv`, so an environment-keyed suppressor would miss
the fixture's own creation and **under-ablate**. It also covers the non-uniform creation call: 26
members use `Path.mkdir(parents=True, exist_ok=True)`, exactly one uses
`os.makedirs(tmp_path/"home", exist_ok=True)` (`test_identity_value_faults_3030.py:298`), and one
creates nothing.

### Mandatory positive control — PASSED

| Requirement | Result |
|---|---|
| Arm 2 must **RED** `tests/sync/test_consent_field_fault_3030.py` | **RED 50/50** |
| Arm 2 must **RED** `tests/sync/test_consent_read_fault_3030.py` | **RED 11/14** |
| Arm 2 must **GREEN** a case that provably never touches the directory | **GREEN** — `test_touches_nothing` (pure arithmetic, scratch demo). Among real members, 3 of 28 green, so the arm is **not systematically green** |

**155 `mkdir`/`makedirs` calls on the home were suppressed across 101 nodes** in the control run —
direct evidence the suppression stayed active through the test body while production repeatedly
tried to re-create the home.

Over all 28 members arm 2 gives **25 RED / 3 GREEN** — a discriminating result, not a systematic
green. **The arm is SOUND; the discharge is NOT refused.** `arm2: REFUSED` does not apply to any
member, and no member's discharge rests on refused evidence.

Asymmetry recorded: **over**-ablation biases toward *keeping* a member (the safe direction);
**under**-ablation biases toward deletion (not safe).

### Discharge for every member of `P`, in amendment A18's terms

| member | arm 2 | discharge |
|---|---|---|
| `test_body_queue_purge_differential_3030.py` | RED 1/8 | directory **is** load-bearing though the pin is not ⇒ **conversion candidate; member STAYS in the adopting set** |
| `test_daemon_publish_consent_3030.py` | RED 7/18 | as above ⇒ **member STAYS in the adopting set** |
| `test_purge_all_body_uploads_3030.py` | GREEN 12/12 | neither load-bearing ⇒ removed from the adopting set, cause recorded; **deletion is OUT of this Mission's scope**, filed as follow-on |
| `test_purge_all_events_3030.py` | GREEN 11/11 | as above |
| `test_identity_value_faults_3030.py::TestThePolicyGate…` | GREEN 147/147 | as above |

Neither struck discharge appears: *"the repeated/interleaved arm red"* is definitionally empty
(`P` is defined by passing it) and *"arm 2 red ⇒ depends on the pin"* inverts FR-016.

---

## 9. Independent reproduction of `P` — DoD 11

See [`REPRODUCTION.md`](REPRODUCTION.md): `P` reproduced **from this artifact alone, by a different
actor**, with its own raw output recorded, and the symmetric difference against the set above.

---

## 10. Halt routing — `|P| ≥ 5`

A `blocked` WP status is **not** sufficient. Verified in the FSM:
`src/specify_cli/status/wp_state.py:517-534` — `BlockedState.allowed_targets() == {IN_PROGRESS,
CANCELED}` and `BlockedState` **overrides no `guard_for`**, inheriting the default unguarded hook at
`:139-145`. So `blocked → in_progress` requires **no actor, no reason, no `review_ref`, no force and
no operator**, and `blocked → in_progress → for_review → approved` delivers exactly the `approved`
state every downstream WP gates on.

Therefore, additionally:

* the halt verdict is posted as a **comment on issue #3121**, naming SC-012 and citing this
  artifact:
  **https://github.com/Priivacy-ai/spec-kitty/issues/3121#issuecomment-5213143113**
  (see [`HALT.md`](HALT.md));
* any subsequent `blocked → in_progress` transition on WP01 **must cite that comment URL** in its
  reason;
* the unguarded `blocked → in_progress` edge is a **tooling gap**, filed to **WP14's residual ledger
  (T068)** rather than worked around silently — see [`RESIDUALS.md`](RESIDUALS.md).

**The implementer may not proceed on their own authority.** IC-03 does not begin; no WP02–WP14 work
may be claimed on the strength of this WP.
