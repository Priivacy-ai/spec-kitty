# Phase 0 Research: CI Topology Shrink & Guard Un-Blinding

**Mission**: `ci-topology-shrink-01KWQAVX` | **Date**: 2026-07-04 | **Branch**: `tidy/ci-topology-shrink`
**Spec**: [`spec.md`](./spec.md) (FR-001..013, NFR-001..007, C-001..006, SC-001..006)
**Method**: LIVE re-derivation against the rebased tree (`.github/workflows/ci-quality.yml` @3307 lines,
`ci-windows.yml`, `tests/architectural/_gate_coverage.py` + `_gate_coverage_baseline.json`,
`test_src_filter_coverage.py`, `test_workflow_coherence.py`, `test_marker_job_completeness.py`,
`scripts/ci/quality_gate_decision.py`) plus one live CI-run timing probe (run `28705381819`).

---

## 1. NFR-006 — Construction-derived census (the critical deliverable)

### 1.1 Command (reproduced live)

```bash
for d in src/specify_cli/*/; do
  n=$(find "$d" -name '*.py' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
  echo "$n $d"
done | sort -rn
```

### 1.2 Mapping oracle (which dirs a named src-backed filter group already claims)

A dir `src/specify_cli/<D>/` is **MAPPED** iff a dorny `filters:` group glob matches
`src/specify_cli/<D>/**`. Parsed live from the `changes` job's filter block:

| Group | src/specify_cli globs it claims |
|-------|--------------------------------|
| `sync` | `sync/**`, `core/loopback_http.py` |
| `merge` | `merge/**` |
| `missions` | `missions/**` (+ `mission.py`, `mission_metadata.py` files) |
| `post_merge` | `post_merge/**` |
| `release` | `release/**` |
| `status` | `status/**`, `coordination/**` |
| `review` | `review/**` |
| `next` | `runtime/**` (+ `src/runtime/next`, `src/mission_runtime`) |
| `lanes` | `lanes/**` |
| `dashboard` | `dashboard/**` |
| `upgrade` | `upgrade/**` |
| `cli` | `cli/**` |
| `core_misc` | `core/**`, `coordination/**`, `delivery/**`, `event_journal/**`, `doctrine_synthesizer/**`, `saas/**`, `status/**`, `tool_surface/**` (+ `src/kernel`, `src/doctrine`) |
| `charter` | `charter_runtime/**` |
| `agent` | `agent_utils/**` |
| `execution_context` | `status/**`, `cli/commands/agent/**` (+ `src/mission_runtime`, `src/runtime/next`) |
| `acceptance` | `acceptance/**`, `state/**` |

**23 mapped dirs**: sync, core, merge, missions, post_merge, release, status, coordination,
review, runtime, lanes, dashboard, upgrade, cli, delivery, event_journal, doctrine_synthesizer,
saas, tool_surface, charter_runtime, agent_utils, acceptance, state.

### 1.3 The RULE (NFR-006 — derived, not hand-picked)

> **`D ∈ worklist ⟺`** `D` is a direct child directory of `src/specify_cli/`, **AND**
> `sum(LOC of *.py under D) ≥ T_LOC`, **AND** no src-backed dorny filter group glob matches
> `src/specify_cli/<D>/**`.

`T_LOC` is a **plan-time constant** committed in the census artifact so the SC-001 test measures
coverage, not the implementer's constant. Recommended `T_LOC = 500` (captures every dir the pre-spec
scope squad named; excludes only truly trivial dirs). The sub-500 tail (7 dirs) is **catch-all-safe**
(the FR-009 fail-closed alarm still covers them) and MAY be folded opportunistically into the `misc`
composite when it ships a dedicated test cone (e.g. `doctor`, `tasks`).

### 1.4 The concrete worklist it yields NOW (LIVE census, arch-blind flag + test cone)

**Arch-run** = the dir is already selected by the arch/adversarial suite because it belongs to one of
`{core_misc, execution_context, acceptance}`. **Arch-blind** = mapped but NOT in those three groups
(Mode B — the un-blind targets).

**A. UNMAPPED worklist (Mode A — trips `unmatched→run_all` on every touch), `T_LOC = 500`:**

| Dir | LOC | Test cone(s) | Already in an integration shard? |
|-----|-----|--------------|----------------------------------|
| retrospective | 6805 | `tests/retrospective`, `tests/specify_cli/retrospect{,ive}` | misc |
| migration | 5607 | `tests/migration` + `tests/specify_cli/migration` | specify-cli-heavy (`and not slow`) + misc |
| auth | 5140 | `tests/auth` | auth-audit-git |
| compat | 5072 | `tests/specify_cli/compat` | specify-cli-rest |
| tracker | 3966 | `tests/tracker` | specify-cli-rest |
| doctrine (code) | 3918 | `tests/specify_cli/doctrine` | specify-cli-rest |
| dossier | 3246 | `tests/dossier` + `tests/specify_cli/dossier` | **none (latent gap)** |
| invocation | 2916 | `tests/invocation` + `tests/specify_cli/invocation` | specify-cli-heavy |
| skills | 2865 | `tests/specify_cli/skills` | specify-cli-rest |
| git | 2770 | `tests/git`, `tests/git_ops`, `tests/specify_cli/git` | auth-audit-git |
| audit | 2104 | `tests/audit`, `tests/specify_cli/audit` | auth-audit-git |
| orchestrator_api | 1956 | `tests/specify_cli/orchestrator_api` | specify-cli-rest (nested) |
| doc_analysis | 1864 | (docs-scanning) | misc/none |
| widen | 1785 | `tests/specify_cli/widen` | specify-cli-rest |
| decisions | 1539 | `tests/specify_cli/decisions` | specify-cli-rest |
| readiness | 1453 | `tests/readiness`, `tests/specify_cli/readiness` | misc |
| mission_v1 | 1337 | `tests/specify_cli/mission_v1` | specify-cli-rest |
| mission_loader | 1297 | `tests/unit/mission_loader` | (own coverage job) |
| workspace | 1283 | `tests/specify_cli/workspace` | specify-cli-rest |
| bulk_edit | 1262 | `tests/specify_cli/bulk_edit` | specify-cli-rest (nested) |
| session_presence | 1226 | `tests/specify_cli/session_presence` | specify-cli-rest |
| policy | 1193 | `tests/policy` | misc |
| ownership | 1114 | `tests/specify_cli/ownership` | specify-cli-rest |
| context | 1056 | `tests/context`, `tests/specify_cli/context` | specify-cli-rest |
| validators | 770 | `tests/specify_cli/*` | specify-cli-rest |
| template | 748 | `tests/test_template` | (lint regression) |
| intake | 728 | `tests/specify_cli/test_intake_*` | specify-cli-rest |
| calibration | 634 | `tests/calibration` | misc |
| paths | 577 | `tests/paths` | specify-cli-rest/misc |
| events | 574 | `tests/specify_cli/events` | specify-cli-rest |
| saas_client | 552 | `tests/specify_cli/saas_client` | specify-cli-rest |
| task_utils | 505 | `tests/specify_cli/*` | specify-cli-rest |

**32 worklist dirs / ≈ 67.9k LOC** at `T_LOC = 500`.

**Sub-500 catch-all-safe tail (7 dirs, ≈ 2.0k LOC)**: identity (444), mission_step_contracts (418),
proof (401), shims (398), doctor (183), tasks (142), diagnostics (92). Not on the committed worklist;
FR-009 fail-safe still covers them; `misc` composite MAY absorb the ones with test cones.

> **Divergence from scope-doc/spec cited numbers**: the spec cites "~37 unmapped / 68.5k LOC". The live
> census yields **32 dirs ≥500 LOC / ≈68k**, or **39 dirs / ≈69.9k** with `T_LOC = 0`. The spec's ~37
> corresponds to a floor near `T_LOC ≈ 150` (drops only diagnostics + tasks). The exact `T_LOC` is a
> committed plan-time constant — the count moves with it; the RULE is invariant. **`cli` (57.8k),
> `sync` (17.7k), `upgrade` (15.9k)** are LARGER than any single worklist dir but are MAPPED — they are
> Mode-B (arch-blind), not Mode-A.

**B. MAPPED-but-ARCH-BLIND worklist (Mode B — arch/adversarial never fires):**

Mapped dirs NOT in `{core_misc, execution_context, acceptance}` — a change confined here merges green
with the dead-module / stale-symbol / terminology / status-boundary gates SKIPPED:

| Group | Arch-blind dirs | LOC |
|-------|-----------------|-----|
| cli | cli | 57 831 |
| sync | sync | 17 739 |
| upgrade | upgrade | 15 926 |
| merge | merge | 6 258 |
| lanes | lanes | 5 431 |
| charter | charter_runtime | 2 944 |
| missions | missions | 2 978 |
| review | review | 2 479 |
| next | runtime | 2 189 |
| post_merge | post_merge | 1 319 |
| dashboard | dashboard | 3 865 |
| release | release | 531 |
| agent | agent_utils | 714 |

**13 arch-blind groups / ≈ 120.2k LOC** — matches the spec's "13 blind / 120k". This is the correctness
root cause (Mode B) and the single highest-leverage change (US2). FR-013's arch-pole treatment closes
it for ALL of them at once (an always-on arch job selects every src dir by construction), so Mode B is
**not** a per-dir worklist to iterate — it is one structural fix.

---

## 2. NFR-001 — Baselines (LIVE-CONFIRMED, not provisional)

### 2.1 The serialization is real (confirmed live)

`ci-quality.yml`:
- `fast-tests-core-misc` → `needs: [changes, kernel-tests, fast-tests-doctrine]` (no arch dep), single
  **unsharded** job, `-m "fast and not windows_ci"` over the whole tree minus 20 `--ignore` roots.
- `integration-tests-core-misc` → **`needs: [changes, fast-tests-core-misc]`** (line 1433) — the arch
  matrix (shard `architectural` = `tests/adversarial tests/architectural tests/architecture tests/lint`,
  marker `not windows_ci and (git_repo or integration or architectural)`) is **serialized behind** the
  fast job.

### 2.2 Live timings (run `28705381819`, `probe/wp03-c-draftflip`, all green)

| Job | Start → End | Duration |
|-----|-------------|----------|
| `fast-tests-core-misc` | 12:00:08 → 12:17:11 | **17m 03s** |
| `integration-tests-core-misc (architectural)` | 12:17:13 → 12:29:30 | **12m 17s** |
| **core-misc critical path** (fast → arch, serialized) | 12:00:08 → 12:29:30 | **≈ 29m 22s** |
| `integration-tests-next` (next-longest independent lane) | 12:01:50 → 12:15:27 | **13m 37s** |
| `fast-tests-cli` | 12:01:51 → 12:09:17 | 7m 26s |

The arch shard **starts 2 seconds after** the fast job completes — proof of the `needs` serialization.

### 2.3 NFR-001 ceiling

Baseline core-misc critical path = **≈29.4 min**. Ceiling = **≤ 55% × 29.4 = ≤ 16.2 min AND ≤ the
next-longest independent lane (13.6 min)**. Both must hold ⇒ **effective ceiling ≈ 13.6 min**.

**Key architectural consequence**: de-serialization ALONE moves the arch tail from 29.4 → 12.3 min
(drop the 17-min serial prefix). 12.3 min already satisfies both arms (≤16.2 AND ≤13.6). So the wallclock
win is dominated by **de-serialization**; matrix-sharding `fast-tests-core-misc` (FR-003) is a
failure-isolation + over-cover-narrowing win, not strictly required to hit the ceiling — but it is
required by SC-003 ("no single shard collects the full catch-all universe") and NFR-004. Record the
29.4-min baseline in the committed timings artifact at plan time (NFR-001).

---

## 3. Routing table — worklist dir → group/shard/marker/--cov/cone (+ hazards)

**Design principle (strongest architecture): mirror the existing `integration-tests-core-misc` matrix.**
The 6 integration shards (`architectural`, `integration`, `specify-cli-heavy`, `specify-cli-rest`,
`auth-audit-git`, `misc`) already run most worklist dirs' tests — the hole is purely on the **filter
(dorny) side**: no `src/specify_cli/<D>` group routes a change TO those shards, so they run only via the
`core_misc` catch-all → any unmapped touch trips `unmatched→run_all`. The fix registers **composite
filter groups** whose members map to the SAME shard family, and splits `fast-tests-core-misc` into a
matrix mirroring the integration shards. Composites (FR-010) cap the job-count blow-up (NFR-005).

### Proposed composite groups (WP01 produces the authoritative artifact; this is the design)

| Composite group | Member src dirs | Fast shard | Integration shard (existing) | Marker | `--cov` targets | Cone hazards |
|-----------------|-----------------|-----------|------------------------------|--------|-----------------|--------------|
| `auth_audit_git` | auth, audit, git | new `fast-tests-auth-audit-git` matrix entry | `auth-audit-git` | `fast and not windows_ci` / integ marker | `--cov=src/specify_cli/{auth,audit,git}` | git split across `tests/git`+`tests/git_ops`+`tests/specify_cli/git` |
| `lifecycle` | migration, invocation, compat, template | new matrix entry (heavy) | `specify-cli-heavy` | heavy adds **` and not slow`** | `.../{migration,invocation,compat,template}` | **migration double-root** (`tests/migration`+`tests/specify_cli/migration`) + **`@slow` perf test must stay `slow`-only** (FR-012) |
| `agent_surface` | orchestrator_api, tracker, dossier, bulk_edit, skills | new matrix entry (rest) | `specify-cli-rest` | rest marker | `.../{orchestrator_api,tracker,dossier,bulk_edit,skills}` | **nested `tests/specify_cli/<D>` roots** (orchestrator_api, bulk_edit) need integration-matrix `ignore_args` hand-update (FR-004; NOT covered by FR-012's whole-tree check); **dossier latent gap** (globbed in core_misc but in NO integration shard — carving FIXES it) |
| `closeout` | retrospective, readiness, decisions, doc_analysis, widen | misc entry | `misc` | misc marker | `.../{retrospective,readiness,decisions,doc_analysis,widen}` | retrospect vs retrospective cone dirs |
| `governance` | doctrine(code), policy, ownership, validators, calibration, context | misc entry | `misc` | misc marker | `.../{doctrine,policy,ownership,validators,calibration,context}` | **`doctrine` ambiguity**: `src/specify_cli/doctrine` (code) vs `src/doctrine` (templates, already `doctrine` group + `fast-tests-doctrine`) — disambiguate so a "promote doctrine" step does not collide with the existing group |
| `platform` | workspace, session_presence, mission_v1, mission_loader, events, paths, saas_client, task_utils, intake | rest/misc entry | `specify-cli-rest`/`misc` | rest marker | `.../<each>` | mission_loader already has `mission-loader-coverage` gate (keep, do not re-promote) |

Notes carried into the plan/tasks:
- **`src/runtime`** — already grouped (`next` group; `integration-tests-next` ≈13.6m). WP01's routing
  table CONFIRMS mapped/excluded; do NOT re-promote.
- **Real-port serial** — `tests/sync/test_orphan_sweep.py` (ports 9400-9449, `-n0`) is preserved by the
  existing `fast-tests-sync` serial step; any new shard touching daemon/real-port tests preserves its
  own `-n0` pass (FR-011, NFR pins it).
- **`--dist loadfile` never bare `load`; per-worker HOME isolation** on every new shard (FR-011).
- **`coverage-<D>.xml` naming** — every new shard emits `coverage-fast-<group>.xml` /
  `coverage-integration-core-misc-<shard>.xml`, matched by the aggregator's `coverage-*.xml` wildcard
  download → emit⇒consume by construction (FR-006).

---

## 4. FR-013 — Arch-pole: serialization confirmed + always-on mechanism (Option A)

### 4.1 Confirmed serialization (see §2.1) — the object shared by US2 (un-blind) and US3 (wallclock)

Un-blinding (arch runs on 100% of PRs) and the wallclock cut collide on the **same arch pole**. Today
the `architectural` shard (a) runs only when `core_misc|execution_context|acceptance` is touched (Mode-B
blindness) and (b) `needs: fast-tests-core-misc` (serialized). One move fixes both.

### 4.2 Option A mechanism (spec-preferred) — always-on arch job that adds NO filter group

Extract the `architectural` matrix shard into a standalone job (proposed `arch-adversarial`):

1. **Un-blind**: `if: always()` (unconditional, like `lint`) — it runs on every PR/push regardless of
   which dir changed. Because its `if:` references **no dorny filter output**, it does NOT enter
   `JOB_GROUPS`, does NOT join `src_backed_groups`, and does NOT touch the `unmatched` enumeration →
   the FR-010c / FR-010 / FR-011 parsed-relation invariants are **untouched** (C-001 additive; NFR-007).
   `test_every_named_group_gates_a_test_running_job_live` and `test_job_groups_table_equals_parsed_if_gating_live`
   both treat a group-less always-on job as legitimately absent ("always-run or event-gated").
2. **De-serialize**: drop `needs: fast-tests-core-misc` → runs in parallel with the fast lane; arch tail
   ≈12.3 min from t=0 (meets §2.3 ceiling).
3. **Bound** (optional, SC-003/NFR-004): the arch job may itself be sharded so its tail stays ≤ ceiling
   as the suite grows; not required at today's 12.3 min.
4. **Coverage-consumer wiring (C-005)**: `arch-adversarial` emits `coverage-*.xml` → MUST enter
   `sonarcloud.needs` and `diff-coverage.needs` (glob-consumed), NOT `slow-tests.needs` (fast-jobs-only;
   would red on arrival). Enters `quality-gate.needs` as a blocking job.
5. **NFR-002 differential-matrix**: a NEW `_gate_coverage` relation asserts the arch job selects 100% of
   `src/specify_cli/*` dirs (0 blind). Because the always-on job carries no path filter over `src/`, it
   selects every dir by construction — the invariant proves the job stays unconditional (a regression
   that re-adds a filter-group gate to it reds).

### 4.3 The 8 #2368 invariants that MUST stay green (NFR-007) — parsed live

From `test_src_filter_coverage.py` + `test_workflow_coherence.py` + `test_marker_job_completeness.py`:

1. **FR-010c enumeration** (`test_unmatched_refs_equal_parsed_filter_groups_live`) — catch-all
   `unmatched` loop == parsed src-backed filter groups. *New group ⇒ add to the `unmatched` loop.*
2. **FR-010c 2nd arm** (`test_every_named_group_gates_a_test_running_job_live`) — every group gates ≥1
   test job.
3. **FR-010 boolean** (`test_unmatched_boolean_semantics`) — `unmatched = any_src AND NOT any(group)`.
4. **FR-012 ignore-mirror** (`test_catch_all_ignore_lists_mirror_owned_roots_live`) — every catch-all
   `--ignore` root owned by a dedicated shard positional. *Carve a shard ⇒ add `--ignore=tests/<root>`
   to `fast-tests-core-misc` AND give the root a positional home, together.*
5. **FR-003b consume** (`test_every_filter_group_is_consumed_live`) — no unconsumed filter group.
6. **FR-003c glob-live** (`test_every_filter_glob_is_live`) — no dead filter glob (covers all 4
   workflows incl. `ci-windows.yml`).
7. **FR-011 JOB_GROUPS≡if** (`test_job_groups_table_equals_parsed_if_gating_live`) — new group in a job
   `if:` ⇒ new `JOB_GROUPS` row in the `quality_gate_decision` heredoc (`:3219-3258`).
8. **Marker completeness** (`test_unit_and_contract_are_routed_by_marker_live` +
   `test_residual_expression_excludes_every_routed_runnable_marker`) — unit/contract stay routed via the
   `unit-contract-residual` job.

Plus the ratchet: `_gate_coverage_baseline.json` — **total_tests 28 573, orphan_test_count 0**,
duplicate 3 550. NFR-003 (same-tier uniqueness) and SC-004 (orphan count stays 0, total selected
unchanged) are measured against this.

### 4.4 The **5-edit atomic group registration** (FR-002) — the per-group recipe

For each NEW composite filter group, ALL five surfaces change in one commit (else invariants 1/2/5/7 red):

1. dorny `filters:` block — the group + its `src/specify_cli/<members>/**` globs.
2. `changes.outputs.<group>` row — the exact `(inputs.run_all || …unmatched…) && 'true' || …filter…` shape.
3. `unmatched` enumeration loop (`:309-329`) — add `"${{ steps.filter.outputs.<group> }}"`.
4. ≥1 test-job `if:` — wire the group into the fast + integration shard gate.
5. `JOB_GROUPS` heredoc row (`:3219-3258`) — `"<job>": ["<group>", …]`.

### 4.5 Coverage-consumer needs-lists (C-005) — the sharpest latent hazard, parsed live

Only `quality-gate.needs` is invariant-bound. The other consumer needs-lists are HAND-maintained:
- `sonarcloud.needs` (`:2517-2552`) — full fast+integration+slow+e2e list.
- `diff-coverage.needs` (`:2370-2387`) — kernel + fast-charter + all integration + fast-core-misc.
- `slow-tests.needs` (`:2152-2168`) — **fast jobs ONLY** (do NOT add integration/arch jobs → would red).
- `mutation-testing.needs` (`:2485-2503`) — disabled (`if: false`), but consumes fast+slow+e2e.

C-005 (spec-CORRECTED): the new invariant binds **coverage-emitting jobs ⊆ `sonarcloud.needs`** and
**critical-path emitters ⊆ `diff-coverage.needs`** — NOT `slow-tests.needs`. A forgotten
`fast-tests-<group>` silently drops its `coverage-*.xml` from Sonar with NO red today → closed by
construction by the C-005 invariant.
