# Post-Merge Mission Review — `layered-doctrine-org-layer-01KRNPEE`

**Reviewer:** Claude Opus 4.7 (1M context), spec-kitty-mission-review skill
**Reviewed at:** 2026-05-16
**Mission ID:** `01KRNPEE69Q0T540T7PRWSZ6CB` (display number 118)
**Mission slug:** `layered-doctrine-org-layer-01KRNPEE`
**Friendly name:** Layered Doctrine Resolution — Org Layer
**Target branch:** `feat/org-doctrine-layer`
**Squash merge commit:** `9c2c26a0f5b9ba47338aab7aacded763d027253f`
**Pre-merge baseline:** `5e18955b609a59311170b6d1b3d9b001da479092`
**Current HEAD at review:** `64e27783`

---

## Verdict

**PASS WITH NOTES**

The mission delivers a coherent, well-tested, end-to-end three-layer doctrine
resolution surface. Architectural boundaries are respected (`charter` does not
import `specify_cli`), security posture for the new network-touching code is
sound, and the new test pyramid (144 mission-new tests) is green. NFR-005
(existing tests pass) is satisfied: 2,358 doctrine + charter tests pass after
deselecting the single pre-existing failure in
`tests/charter/test_neutrality_lint.py::test_generic_artifacts_are_neutral`,
which was already failing on `main` from commit `b134bac5` before this mission
started (verified — that file was last touched by mission 117).

However, there are two **HIGH-severity drifts** from the spec that operators
will hit in real use, and both deserve an explicit follow-up mission. Neither
is a security or reliability defect, both are spec/code mismatches in the live
operator surface that the unit tests do not catch because they target the
underlying API instead of the live CLI flow.

The mission is releasable as a **preview / behind-config-flag** capability.
Calling it "general availability" without addressing the two notes below would
mislead operators who configure multiple org packs or rely on `charter
interview` to surface org defaults.

---

## Step 1 — Mission state snapshot

* `spec-kitty agent tasks status` reports 10 / 10 WPs in **done** lane,
  100% weighted readiness.
* `kitty-specs/layered-doctrine-org-layer-01KRNPEE/meta.json` confirms
  `mission_id=01KRNPEE69Q0T540T7PRWSZ6CB`, `mission_number=118`, target
  branch `feat/org-doctrine-layer`, `vcs_locked_at=2026-05-15T12:53:52Z`.
* `status.events.jsonl` carries 75 events (one append-only line per
  state transition).
* Mission spec directory contains: `spec.md`, `plan.md`, `tasks.md`,
  `data-model.md`, `research.md`, `lanes.json`, `status.json`,
  `contracts/{config-schema.yaml, org-doctrine-source-api-contract.md,
  pack-layout.md}`, `checklists/requirements.md`, and 10 WP review folders.
* No `issue-matrix.md` is present (Gate 4 N/A by absence).

---

## Step 2 — Spec mental model

The spec defines **29 FRs**, **6 NFRs**, **7 Constraints (C-001–C-007)**, and
**13 Key Entities**. Notable locked decisions and non-goals derivable from the
constraints:

* **C-001** — *No runtime remote calls.* Network is allowed only inside
  `doctrine fetch`. Verified: all `requests` / `subprocess` use sites are in
  `src/specify_cli/doctrine/sources/*` and `snapshot.py`, never in the
  resolution path.
* **C-002** — *No background auto-update.* No cron / daemon code introduced.
* **C-003** — *Shipped layer is read-only.* Verified: org/project layers
  override but never mutate shipped on disk.
* **C-004** — *Multi-pack ordered list.* Internal model **claims** to be
  `org_roots: list[Path]`. **See HIGH-1 below.**
* **C-005** — *Resolution always reads local files.* Verified.
* **C-006** — *Project-layer behavior unchanged.* Verified by 2,358 passing
  pre-existing tests.
* **C-007** — *`pack assemble` reports, never auto-resolves conflicts (without
  --force).* Verified in `pack_assembler.py` and `test_pack_assembler.py`.

---

## Step 3 — Coverage map

The squash commit changes `8,777` lines added across `307` files. Coverage by
WP scope (mapped via owned_files frontmatter and the diff):

| WP | Scope expected | Files actually changed | Conclusion |
|---|---|---|---|
| WP01 | `src/doctrine/drg/loader.py`, `__init__.py`, charter DRG call sites, `tests/doctrine/drg/test_loader_multifile.py` | All present (8 tests in loader, charter `_drg_helpers.py` rewritten, all 4 synthesizer pipelines updated) | ✅ in scope |
| WP02 | `src/doctrine/base.py`, all 8 repository subclasses, `tests/doctrine/test_base_org_layer.py` | All 8 subclasses now route `org_dir` through `__init__`; provenance dict wired | ✅ in scope |
| WP03 | `src/doctrine/service.py`, `src/charter/_drg_helpers.py`, `tests/doctrine/test_service_org_layer.py` | Done; `_resolve_org_root()` is intentionally inert (architectural-correctness deviation, see Notes) | ✅ in scope, deviation documented |
| WP04 | `src/specify_cli/doctrine/sources/{protocol,git_source,https_source,api_source}.py`, `snapshot.py`, tests | All 4 source modules + snapshot.py + 21 source tests + 6 snapshot tests | ✅ in scope; added `tests/specify_cli/__init__.py` (test infra fix, accepted) |
| WP05 | `config.py`, `cli/commands/doctrine.py` (fetch + stubs), tests | All present | ✅ in scope |
| WP06 | `pack_validator.py`, `pack_assembler.py`, plus `org-charter.yaml` validate/assemble extension | All present; touched `cli/commands/doctrine.py` and `tests/specify_cli/doctrine/test_config.py` outside owned_files (replaced WP05 stubs with real impls — accepted at WP-review) | ✅ in scope, deviation documented |
| WP07 | `charter/context.py`, `cli/commands/doctor.py`, `cli/commands/charter.py`, `charter_lint/checks/org_layer.py` | All present; `doctor doctrine` registered, `OrgOverridesBuiltinChecker` + `OrgCharterDeviationChecker` registered in lint engine | ✅ in scope |
| WP08 | `docs/how-to/`, `docs/migration/`, `docs/explanation/`, `docs/toc.yml` | All 3 docs (274 + 434 + 252 lines), per-section TOCs updated | ✅ in scope |
| WP09 | `src/specify_cli/doctrine/org_charter.py`, `src/charter/interview.py`, tests | `apply_org_charter_pre_fill_to_answers` lives in `charter/interview.py`, `OrgCharterPolicy` in `specify_cli/doctrine/org_charter.py`, fully tested. **Not wired to live `spec-kitty charter interview` command.** See HIGH-2 below. |
| WP10 | Rename `shipped/` → `built-in/` for all 8 artifact dirs, update `_shipped_dir()` | All 175+ rename diff entries present; `service.py:38` returns `artifact / "built-in"`; `base.py:225` provenance tag is `"builtin"` (no hyphen) | ✅ in scope |

---

## Step 4 — Rejection cycle resolution (WP08)

WP08 cycle 1 (`review-cycle-2.md`, 2026-05-15T15:17Z) flagged a docs/code
literal mismatch: docs claimed `source` field value was `built-in` (with
hyphen) but code emits `builtin` (no hyphen).

* `src/charter/context.py:775` constrains: `"source": source if source in
  {"builtin", "org", "project"} else "builtin"`.
* `src/doctrine/base.py:225` sets `self._provenance = {k: "builtin" for k in
  self._items}`.
* Doc fixes landed in commit `7a01910e` (per cycle-3 approval): two literal
  occurrences corrected at `docs/explanation/org-doctrine-layer.md:135` and
  `docs/how-to/create-an-org-doctrine-pack.md:389`.
* Cycle 3 verdict: **approved** (`review-cycle-3.md`, 2026-05-15T15:19Z).
* Verified at HEAD: targeted grep for `` `built-in` `` in the three new docs
  returns zero hits in literal-tag positions; English prose mentions of
  "built-in layer" are preserved (out of scope per cycle-1).

**Resolution: clean. The fix is consistent with code at the squash commit.**

---

## Step 5 — FR Trace

Tests do not cite `FR-NNN` strings (the project uses behavior-named tests).
Trace below maps FR → constraining test(s) → implementing code.

| FR | Test evidence | Implementation site | Status |
|---|---|---|---|
| FR-001 (3-layer order) | `tests/doctrine/test_base_org_layer.py::TestProjectOverridesOrg`, `TestOrgOverridesShipped` | `src/doctrine/base.py:219-229` (`_load`) | ✅ shipped → org → project enforced |
| FR-002 (8 artifact types support org layer) | `tests/doctrine/test_service_org_layer.py::TestOrgRootArtifactsResolved` + repository subclass tests | All 8 repos in `src/doctrine/{directives,tactics,styleguides,toolguides,paradigms,procedures,agent_profiles,mission_step_contracts}/repository.py` | ✅ |
| FR-003 (full-replace, no field merge) | `tests/doctrine/test_base_org_layer.py::TestOrgOverridesShipped` | `_apply_org_overrides` and `_merge` (note: `_merge` is field-level, but per item only) | ✅ at item level |
| FR-004 (DRG single file or directory) | `tests/doctrine/drg/test_loader_multifile.py` (8 cases) | `src/doctrine/drg/loader.py:34` `load_graph_or_dir` | ✅ |
| FR-005 (org graph extensions are additive) | `tests/doctrine/drg/test_loader_multifile.py::test_directory_multiple_fragments` | `merge_layers()` in `loader.py` | ✅ |
| FR-006 (multi-pack ordered list, declaration precedence) | `tests/specify_cli/doctrine/test_config.py::TestLoadPackRegistry::test_load_packs_list` | `src/specify_cli/doctrine/config.py:93-122` (`PackRegistry`) | ⚠️ Config supports it. **Resolution does not — see HIGH-1.** |
| FR-007 (`doctrine fetch` is the only network-touching command) | `tests/specify_cli/doctrine/test_config.py::TestDoctrineFetchCLI` | `src/specify_cli/cli/commands/doctrine.py:47` | ✅ |
| FR-008 (git source, persistent clone, ref pin) | `tests/specify_cli/doctrine/test_sources.py` (multi GitSource cases) | `src/specify_cli/doctrine/sources/git_source.py` | ✅ |
| FR-009 (HTTPS bundle source) | `tests/specify_cli/doctrine/test_sources.py` HttpsBundleSource cases | `src/specify_cli/doctrine/sources/https_source.py` | ✅ |
| FR-010 (HTTP API source) | `tests/specify_cli/doctrine/test_sources.py` ApiSource cases | `src/specify_cli/doctrine/sources/api_source.py` | ✅ |
| FR-011 (validation; existing snapshot preserved on failure) | `tests/specify_cli/doctrine/test_snapshot.py::test_atomic_write_fetch_failure_preserves_existing` | `snapshot.py::write_snapshot` (atomic rename) | ✅ |
| FR-012 (`pack validate`) | `tests/specify_cli/doctrine/test_pack_validator.py` (12 tests) | `pack_validator.py::validate_pack` | ✅ |
| FR-013 (`pack assemble` with conflict reporting) | `tests/specify_cli/doctrine/test_pack_assembler.py` (11 tests) | `pack_assembler.py::assemble_pack` | ✅ |
| FR-014 (`charter context --json` `source` field) | `tests/specify_cli/test_provenance_integration.py::TestProvenanceServiceIntegration` | `src/charter/context.py:775` | ✅ literal value is `builtin/org/project` |
| FR-015 (`doctor doctrine` per-pack listing) | `tests/specify_cli/test_provenance_integration.py::TestDoctorDoctrineCommand` | `src/specify_cli/cli/commands/doctor.py:1376` | ✅ |
| FR-016 (`charter lint` advisory on org-overrides-built-in) | `tests/specify_cli/test_provenance_integration.py::TestLintOrgOverridesAdvisory` | `src/specify_cli/charter_lint/checks/org_layer.py::OrgOverridesBuiltinChecker` | ✅ |
| FR-017 (base class as documented extension point) | n/a (documentation-only requirement) | `src/doctrine/base.py` docstring | ✅ docstring documents the contract |
| FR-018 (graceful no-org fallback) | `tests/doctrine/test_service_org_layer.py::TestNoOrgRoot` | `service.py:45-54`, `_drg_helpers.py:84` | ✅ |
| FR-019 (deterministic resolution) | `tests/doctrine/test_service_org_layer.py::TestDeterminism` | reducer-style merge in `base.py::_load` | ✅ |
| FR-020 (`--pack <name>` flag) | `tests/specify_cli/doctrine/test_config.py::test_fetch_single_pack_flag` | `cli/commands/doctrine.py:84-92` | ✅ |
| FR-021 (`git describe` version, manifest fallback for non-git) | `tests/specify_cli/test_provenance_integration.py::TestDoctorDoctrineCommand::test_pack_version_from_manifest`; `git_source.py::_describe` | `git_source.py:117`, `snapshot.py::write_pack_manifest` | ✅ |
| FR-022 (assemble output is itself a valid pack) | `tests/specify_cli/doctrine/test_pack_assembler.py::test_assembled_pack_is_validated` | `pack_assembler.py` end-to-end validation | ✅ |
| FR-023 (zero effect on legacy projects) | `tests/specify_cli/doctrine/test_config.py::test_load_config_no_file`, `test_load_config_absent_key` | `config.py::load_pack_registry` (returns empty registry) | ✅ |
| FR-024 (`doctor doctrine` unified listing) | `TestDoctorDoctrineCommand::test_no_org_configured`, `test_artifact_counts` | `doctor.py:1376` | ✅ |
| FR-025 (org-charter.yaml composition order) | `tests/specify_cli/doctrine/test_org_charter.py::TestLoadOrgCharterPolicies::test_merge_*` | `specify_cli/doctrine/org_charter.py` | ✅ |
| FR-026 (`charter interview` pre-fills from org charter) | `tests/specify_cli/doctrine/test_org_charter.py::TestApplyOrgCharterPreFill` (5 tests) | `charter/interview.py:324` `apply_org_charter_pre_fill_to_answers` | ⚠️ **Function exists and is tested in isolation, but is NOT invoked by the live `spec-kitty charter interview` command — see HIGH-2** |
| FR-027 (`charter context` includes org charter elements) | `tests/specify_cli/doctrine/test_org_charter.py::TestContextJsonOrgCharter` (2 tests) | `org_charter_loader.py::load_org_charter_json_block`, wired in `charter.py:1505` | ✅ |
| FR-028 (`charter lint` advisory on charter deviation) | `tests/specify_cli/test_provenance_integration.py::TestLintEngineWithOrgChecksOnly` | `charter_lint/checks/org_layer.py::OrgCharterDeviationChecker` | ✅ |
| FR-029 (`doctor doctrine` per-pack org-charter status) | `TestDoctorDoctrineCommand` covers presence; org-charter counts surfaced in `doctor.py:1317-1340` | `doctor.py:1317` lazy-loads `OrgCharterPolicy` | ✅ |

NFR coverage:
* **NFR-001** (fetch < 30s) — not benchmarked in tests; design (atomic rename, no full re-extract) makes it plausible. **No regression risk; advisory only.**
* **NFR-002** (resolution adds < 50ms) — not benchmarked in tests. The org layer adds one filesystem walk per artifact type per repository instance. With caching in `DoctrineService._cache`, the actual hit is bounded. **Not formally validated.**
* **NFR-003** (`pack validate` < 5s) — not benchmarked.
* **NFR-004** (one bad artifact does not abort load) — covered by `tests/doctrine/test_base_org_layer.py::TestBadOrgFileSkipped`. ✅
* **NFR-005** (existing tests pass) — verified: 2,358 pass, 1 skipped, 1 deselected (pre-existing). ✅
* **NFR-006** (offline after one fetch) — by C-001 + design; resolution path has no network code. ✅

---

## Step 6 — Drift / Gap analysis

### Anti-pattern walk

1. **Synthetic-fixture tests** — Not detected. The new tests use real
   filesystem fixtures and exercise `BaseDoctrineRepository._load()`
   end-to-end.
2. **Code that no test constrains** — `_resolve_org_root()` in
   `_drg_helpers.py` is intentionally inert (always returns `None`); its
   non-trivial behavior lives in `specify_cli/cli/commands/charter.py`
   (`_build_doctrine_service_with_org_layer`), which **is** test-covered.
3. **Punted FRs with zero test hits** — None. Every FR maps to at least one
   constraining test or a behavior trivially equivalent to one.
4. **Non-Goals violated** — None detected. C-002 (no auto-update) is
   honored — there is no daemon / cron / file-watcher code.
5. **Locked Decisions contradicted** — **YES, one:** C-004 declares the
   internal model is `org_roots: list[Path]` accumulating *all* configured
   pack paths. The `DoctrineService` accepts the list but only consults
   `self._org_roots[0]` (see HIGH-1). This is documented in
   `tests/doctrine/test_service_org_layer.py::test_only_first_org_root_used`
   ("future-proof") but is a measurable gap from the spec.
6. **Dead code** — None. Every new module
   (`org_charter`, `org_charter_loader`, `pack_validator`, `pack_assembler`,
   `sources/{git,https,api}_source`, `snapshot`, `config`) has at least one
   non-test live caller in `cli/commands/{doctrine,doctor,charter}.py` or
   `charter_lint/checks/org_layer.py`.
7. **Cross-WP integration gaps** — `apply_org_charter_pre_fill` (WP09)
   exists, is tested, and exposes a public function via
   `specify_cli.doctrine.org_charter.apply_org_charter_pre_fill`, but
   the live `charter interview` CLI command does not call it. See HIGH-2.
8. **Backward compatibility** — verified. Existing tests pass, Form-B
   legacy single-pack config still loads.

---

## Step 7 — Risk

* **`_resolve_org_root` boundary stub**: Correct architectural choice.
  Charter must not import specify_cli (`tests/architectural/test_layer_rules.py`
  enforces this; verified passing — 96 architectural tests pass with 1 skip).
  Callers in `specify_cli` resolve the path and pass it explicitly. No risk.
* **Source backends silent-empty returns**:
  * `git_source.py` — Errors are surfaced via `FetchResult.errors`; never
    returns `ok=True` on subprocess failure. ✅
  * `https_source.py` — All HTTP error classes (4xx/5xx, RequestException,
    archive parse failure) surface as non-ok FetchResult. ✅
  * `api_source.py` — 404 on individual artifact-type endpoints returns
    `(0, None)` as expected (FR-allowed: server may not expose every type).
    Auth failures (401/403) abort. ✅
* **Atomic-write race**: `snapshot.py::write_snapshot` stages into
  `<parent>/.tmp-<uuid>` then `shutil.rmtree(local_path)` + `shutil.move`.
  There is a brief window after `rmtree` and before `move` where `local_path`
  does not exist. A concurrent reader during that window would see a missing
  pack and fall through the optional-org code path. This is **acceptable per
  C-001 and FR-018** (graceful fallback when org snapshot is absent). Document
  as known limitation; not a defect.
* **DoctrineService cache invalidation**: `_cache` is per-instance; tests
  validate fresh instances pick up new state. ✅

---

## Step 8 — Security

| Surface | Finding | Status |
|---|---|---|
| `git_source._inject_token` | Token only injected for HTTPS URLs (`if not url.startswith("https://"): return url`); not echoed back to logs (only passed as argv). Tests assert SSH URLs are unaffected. | ✅ Sound |
| `https_source._headers` | `SPEC_KITTY_ORG_AUTH_HEADER` and `SPEC_KITTY_ORG_TOKEN` env vars; bearer token set as `Authorization: Bearer <token>`. Never logged. | ✅ Sound |
| `https_source._safe_extract_*` | Path-traversal protection via `resolve()` check before `extractall()`. Both tar.gz and zip paths validate every member. | ✅ Sound |
| `api_source._headers` | Same pattern as https_source; bearer token never logged. | ✅ Sound |
| `snapshot._strip_credentials` | Regex `^(https?://)[^/@]+@` strips userinfo before persisting `source_url` in `pack-manifest.yaml`. Verified by `test_manifest_strips_credentials`. | ✅ Sound |
| HTTP timeouts | All `requests` calls supply `timeout=30`. The `noqa: S113` is paired with an explicit `timeout` parameter in the same call. | ✅ Sound |
| YAML deserialization | Every load path uses `YAML(typ="safe")` or `yaml.safe_dump`; no `unsafe_load` anywhere in mission code. | ✅ Sound |
| Subprocess injection | `subprocess.run(argv, ...)` with constructed argv; no `shell=True`; no string concatenation into shell. | ✅ Sound |

**No security defects identified.**

---

## Step 8.5 — Hard Gates

| Gate | Result | Evidence |
|---|---|---|
| **1: Contract** | **PASS by absence of mission-introduced regressions** | `tests/contract/` exists. Running `pytest tests/contract/` shows 19 failures, but the same 17 of those (`test_event_envelope.py` + `test_packaging_no_vendored_events.py`) also fail at baseline `5e18955b` *before* this mission. The remaining 2 failures (`test_handoff_fixtures.py::TestFixtureValidation::test_fixture_payload_passes_emitter_rules[*]`) are also baseline-failing and not in mission scope. **No new contract-test regressions introduced by this mission.** |
| **2: Architectural** | **PASS** | `pytest tests/architectural/` → **96 passed, 1 skipped, 1 warning in 20.93s**. Includes `test_layer_rules.py` (8 cases) which enforces `charter` does not import `specify_cli`. |
| **3: Cross-repo E2E** | **N/A** | No `spec-kitty-end-to-end-testing` sibling checkout exists at `/home/stijn/Documents/_code/CLIENTS/regnology/forks/`. Gate is N/A by absence; this is consistent with mission scope (the org-layer feature is internal to spec-kitty and is not coupled to external e2e fixtures). |
| **4: Issue matrix** | **N/A** | `kitty-specs/layered-doctrine-org-layer-01KRNPEE/issue-matrix.md` does not exist; the mission did not adopt the issue-matrix protocol. |

---

## Step 9 — Findings table

### HIGH

#### HIGH-1: Multi-pack org layer collapses to single pack at resolution time

**Severity:** HIGH (spec drift, operator-visible)
**Spec contract violated:** FR-001, FR-003, FR-006, C-004, Spec Scenario 2.

**Evidence:**

* `src/doctrine/service.py:45-54` — `_org_dir()` returns `self._org_roots[0]
  / artifact`, ignoring entries 1..N.
* `src/doctrine/base.py:60` — `BaseDoctrineRepository.__init__` accepts a
  single `org_dir: Path | None`, not a list.
* `tests/doctrine/test_service_org_layer.py:104-110` — `test_only_first_org_root_used`
  documents the limitation: *"Only the first entry in org_roots is used by
  _org_dir (future-proof)."*
* `src/charter/_drg_helpers.py::load_validated_graph` — also takes a single
  `org_root: Path | None`, not a list, so multi-pack DRG merging in
  declaration order is also impossible at the live call site.
* `src/specify_cli/cli/commands/charter.py:1490-1491` — `org_root =
  org_roots[0] if org_roots else None` for `charter context`. Multi-pack
  is silently dropped.

**Impact:** An operator following Spec Scenario 2 ("A large organisation has
three independent doctrine repositories: one maintained by the security
team, one by the architecture team, and one by the compliance team... Resolution
merges all three org packs in declaration order") will configure three packs
in `.kittify/config.yaml`, run `doctrine fetch` (which DOES iterate all packs),
and discover that only the **first** pack's artifacts are loaded into
`charter context`, into the `DoctrineService`-backed lint, and into mission
context generation. Packs at index 1+ are invisible to resolution, even though
`doctor doctrine` will list them as configured.

**Where the gap is hidden by tests:** Mission-new tests at the repository
level (`tests/doctrine/test_base_org_layer.py`) test single `org_dir`, which
is the supported surface. The single test that covers multi-pack
(`test_only_first_org_root_used`) **encodes the limitation as expected
behavior** rather than the spec's promised multi-pack precedence.

**The two surfaces that DO support multi-pack:**

* `specify_cli.doctrine.org_charter_loader.load_org_charter_json_block` —
  iterates all packs and merges org-charter JSON blocks per pack. ✅
* `OrgCharterPolicy` merge logic in `specify_cli.doctrine.org_charter` —
  `interview_defaults`, `required_directives`, `governance_policies` all
  merge across packs. ✅

So the gap is specifically at the **artifact-resolution layer** (directives,
tactics, styleguides, toolguides, paradigms, procedures, agent_profiles,
mission_step_contracts), not at the charter-policy layer.

**Recommendation:** Open follow-up issue. Either:

* (a) Extend `BaseDoctrineRepository` to accept `org_dirs: list[Path]` and
  iterate them in declaration order with later-wins merge semantics, OR
* (b) Tighten the spec to "single org pack" as the supported model and
  reword `PackRegistry`'s `packs` list to be a discovery / fetch-only
  manifest. The current state straddles both interpretations.

---

#### HIGH-2: `charter interview` CLI does not invoke `apply_org_charter_pre_fill`

**Severity:** HIGH (FR-026 not delivered end-to-end)
**Spec contract violated:** FR-026, Spec Scenario 5, Spec Success Criterion 11.

**Evidence:**

* `src/charter/interview.py:324` — `apply_org_charter_pre_fill_to_answers`
  is implemented and 5 tests cover it.
* `src/specify_cli/doctrine/org_charter.py:185` —
  `apply_org_charter_pre_fill(repo_root)` is implemented as the public
  org-layer entry point and is tested
  (`tests/specify_cli/doctrine/test_org_charter.py::TestApplyOrgCharterPreFill`).
* `src/specify_cli/cli/commands/charter.py:893-1183` — the live `interview`
  command. A grep for `apply_org_charter_pre_fill` in this file returns
  zero hits.
* The mission's WP09 frontmatter explicitly notes this as a deferred
  follow-up.

**Impact:** A developer running `spec-kitty charter interview` on a machine
with org packs configured will NOT see org-mandated `interview_defaults` or
`required_directives` pre-filled in their interview, contradicting Spec
Scenario 5 ("During mission execution, org-layer governance is injected into
agent context automatically") and Success Criterion 11 ("`charter interview`
pre-fills answers from org charter policy"). The unit-tested helper
exists but the live operator command does not call it.

**Recommendation:** Open a small follow-up WP that:

1. Calls `apply_org_charter_pre_fill(repo_root)` near the top of `interview()`
   in `src/specify_cli/cli/commands/charter.py:933`, before `default_interview()`
   or after the answers file is first written.
2. Surfaces the messages it returns in the interview console output.
3. Adds an integration test that runs the live CLI with an org pack
   configured and asserts the answers file picks up the pack's
   `interview_defaults`.

---

### MEDIUM

#### MEDIUM-1: `BaseDoctrineRepository._merge` field-level merge contradicts FR-003

**Severity:** MEDIUM (technically a spec/code mismatch, but the test corpus
treats item-level full-replace as the contract)

**Evidence:**

* FR-003: *"the higher layer fully replaces the lower layer's artifact
  (full-replace semantics). Partial field merging is not applied across
  layers."*
* `src/doctrine/base.py:231-234` — `_merge(shipped, project_data)` does
  `{**shipped.model_dump(), **project_data}` — a **field-level** merge
  (project_data overlays shipped fields one-by-one). This is what the
  spec says NOT to do.
* The `_apply_org_overrides` and `_apply_project_overrides` methods both
  call `_merge`, so both org- and project-layer overrides inherit the
  shipped object's fields and only override the keys present in the
  override file.

**However:** The mission's WP02 risks section explicitly notes this:
*"the existing `_merge()` is field-level for project override of shipped,
which is preserved; org override of shipped is also full-replace at the
item level."* So the WP author treated "item-level full-replace" as the
guarantee FR-003 actually intends.

**Recommendation:** Reword FR-003 in the spec to clarify "the **item** is
fully replaced; field-level merge is preserved as today" — OR rewrite
`_merge` to do `type(shipped).model_validate(project_data)` (true
full-replace at the field level). The current behavior matches the
pre-mission `_merge` contract, so this is a **spec wording defect rather
than a code defect**, but it's worth flagging for the next mission to
choose explicitly.

#### MEDIUM-2: `doctor doctrine` wired-but-unverified for `git describe` against real clones

**Severity:** MEDIUM (FR-021 partially verified)

`git_source._describe()` invokes `git describe --tags --always` and is
covered for non-error paths. However, no integration test runs
`doctor doctrine` against an actual `.git/` directory created by `GitSource`
end-to-end. The closest test
(`tests/specify_cli/test_provenance_integration.py::TestDoctorDoctrineCommand::test_pack_version_from_manifest`)
exercises only the `pack-manifest.yaml` fallback (non-git source).

**Recommendation:** Add a single end-to-end test that:
1. Initializes a temp git repo with a tagged commit.
2. Runs `GitSource(url=...).fetch(target)` against it (file:// URL).
3. Runs `doctor doctrine` and asserts the version surfaces as the tag name.

### LOW

#### LOW-1: WP04 added `tests/specify_cli/__init__.py` outside its declared owned_files

Documented and accepted at WP04 review time. Was necessary to unblock pytest
package discovery for the new `tests/specify_cli/doctrine/` subpackage.
Mention only for completeness.

#### LOW-2: WP06 touched `cli/commands/doctrine.py` and `tests/specify_cli/doctrine/test_config.py` outside owned_files

Documented and accepted. Was necessary to replace the WP05 placeholder
`NotImplementedError` stubs with the real WP06 validate/assemble
implementations. Mention only for completeness.

#### LOW-3: `_apply_org_overrides` mutates `shipped` dict via aliasing

**Evidence:** `src/doctrine/base.py:223` — `self._items = shipped.copy()`
copies the dict but not the contained objects. Subsequent `_apply_org_overrides`
and `_apply_project_overrides` both pass `shipped` (the original) and write
into `self._items`. Because Pydantic models are immutable-by-convention and
`_merge` constructs new instances via `model_validate`, this is safe in
practice, but a future refactor that mutates a model in place would silently
leak across layers.

**Recommendation:** Defensive but not urgent. Either deep-copy or rename
`shipped` to `shipped_baseline` and document the immutability assumption in
the docstring.

---

## Cross-WP Consistency

* **`built-in` vs `builtin`** — clean across code and docs after the WP08
  cycle-1 fix. Code emits `builtin`; directories on disk are `built-in/`;
  English prose uses "built-in" freely.
* **Architectural boundary `kernel <- doctrine <- charter <- specify_cli`** —
  preserved; no `specify_cli` imports in `src/charter/` or `src/doctrine/`
  except one pre-existing exception in `src/charter/synthesizer/synthesize_pipeline.py:61`
  which is **not** part of this mission (last touched by mission-688 / 690).
* **All 8 artifact directories** are renamed consistently from
  `shipped/` → `built-in/` (175+ rename diff lines). `_shipped_dir()`
  returns `artifact / "built-in"`. Test fixtures updated.
* **All new modules have at least one non-test live caller**, verified by
  cross-package grep.
* **YAML loading is uniformly safe** (`YAML(typ="safe")` or
  `yaml.safe_dump`).

---

## Final Verdict: **PASS WITH NOTES**

The mission is internally consistent, well-tested at the unit and component
level, architecturally sound, and free of security defects in the new
network-touching code. The two HIGH findings are spec-vs-code mismatches in
the live CLI surface, both with documented test coverage of the underlying
machinery and at least one of the two (HIGH-2) explicitly noted as a
deferred follow-up by the mission's own WP09. They should be addressed in a
follow-up mission before this is described to operators as "ready for
multi-pack production use," but neither blocks merging or releasing this
mission as a preview / single-pack-supported capability.

**Recommended next actions:**

1. Open a follow-up issue to wire `apply_org_charter_pre_fill` into
   `spec-kitty charter interview` (HIGH-2). Small WP.
2. Open a follow-up issue to either implement true multi-pack precedence
   in `BaseDoctrineRepository` / `DoctrineService._org_dir` OR retighten the
   spec wording around FR-001/003/006 and `PackRegistry` (HIGH-1). Material
   WP.
3. Add the missing end-to-end `git describe` integration test (MEDIUM-2).
4. Decide whether to reword FR-003 or change `_merge` semantics
   (MEDIUM-1) — clarify spec intent.
5. The pre-existing `tests/charter/test_neutrality_lint.py::test_generic_artifacts_are_neutral`
   failure is unrelated to this mission and tracked separately.
