---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T18:39:50Z'
reviewer_agent: codex
wp_id: WP03
---

# WP03 Independent Full-Contract Review

## Verdict: REJECT

Reviewed final implementation `047dc8a69b32c39aa4309a6dcefe3af53855b169`.
Independent review, not implementation or canonical verdict capture. Parent owns
review decisions, transitions and follow-up ownership allocation.

## F1 - High: cold global preparations cannot compose through the approved owner seam

Location: [asset_preparation.py:224](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-c/src/specify_cli/runtime/asset_preparation.py:224),
supporting inventory/lock parents at line 322; retained preconditions at line 359.

Each of `assess_runtime()`, `assess_global_agent_commands()` and
`assess_global_agent_skills()` returns a complete, nonempty preparation from the
same real cold HOME. Each independently claims missing shared parents, including
`home/.kittify` and its cache, under a different executable owner. Commands and
skills also share agent ancestors. This is not merely duplicate reporting:
each opaque preparation retains its own parent writes and absence observations.

Fresh reviewer control, actual installed runtime/templates/skill catalog, actual
WP02 `SurfaceRepairService.apply_assessments`, automatic consent:
all three return `failed` with
`Owner effect conflict at .../home/.kittify`.
The independent WP01 snapshot proves no mutation before refusal.
The dispatcher is correctly enforcing the approved WP02 boundary at
[repair.py:240](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-c/src/specify_cli/tool_surface/repair.py:240);
it is not a WP02 regression to waive.

Sequential application is not a solution. Applying the retained runtime
assessment succeeds, then the retained command and skill assessments both return
`precondition_changed`, naming the newly created `home/.kittify`.
Their refusal is also byte/mode/mtime preserving.

The external control uses tiny protocol-validated dispatch adapters binding the
real recheck/apply functions; reassessment is an assertion failure. Each owner
also succeeds individually THROUGH THE SAME dispatcher on a separate cold home,
matches every independently observed persistent effect and has a no-churn
second apply. Thus the combined failure is neither an unavailable fake provider
nor a helper-import failure. See
[test_independent_wp03.py](/tmp/wp03-review.KdZx8s/test_independent_wp03.py),
[independent-controls-final.log](/tmp/wp03-review.KdZx8s/independent-controls-final.log).

**Contract impact:** T013's integration-ready preparation/apply interface,
T015/T016's single executable ownership and shared physical roots, T017's
non-vacuous plan/apply agreement; owner-operations.md Effect Semantics requires
one executable owner per effect and physical deduplication. FR-002/003 and C-001
cannot receive full-contract approval from isolated per-owner successes.

**Required correction:** coordinate one retained executable preparation boundary
for overlapping global infrastructure, retaining complete effects, logical
owners, exact bytes and observations. Add real cold multi-owner dispatch,
independent net-delta and repeat/no-churn regression evidence. Preserve WP02's
conflict guards. Do not concatenate opaque payloads, drop parent effects, or
silently reassess after the first write. Parent must coordinate any WP02/WP05/WP10
interface changes outside WP03 ownership.

This defect already exists among the three WP03 global owners. It is distinct
from the explicitly deferred WP10 public intent consumer.

## Other Gates and Limits

- **Pending WP10, not a requested unauthorized WP03 root edit:** fresh dead-module
  and dead-symbol gates fail only on `specify_cli.upgrade.intent` and
  `parse_upgrade_intent`. Production call-site search confirms no consumer.
  T012/T013/T017 intentionally prohibit wiring public startup here. These gates
  remain RED; no dummy import, rename, allowlist or exemption is justified.
- **Unresolved validation failure:** WP01
  `test_canonical_setup_leaves_cold_home_untouched` times out during actual
  `spec-kitty init --ai claude,codex,cursor --non-interactive` after its unchanged
  90-second deadline. The combined run and one diagnostic-only isolated-node run
  both fail. No third retry, timeout increase, stub, baseline waiver or claim
  of proven pre-existence. Concurrent host load was present, but causation and
  base-versus-final performance are unproven. The raw oracle controls pass;
  canonical fixture setup does not. Parent receives this unresolved evidence.
- Eight public WP01 RED witnesses remain pending WP10/WP13 according to the
  reviewed handoffs. This review does not rerun or close all eight and does not
  upgrade semantic parser tests to public CLI acceptance.
- T011's distinct tidy-first commit is not established: the worker explicitly
  records its proposed selective tidy commit failed and changes were folded into
  the functional delivery. Real existing-entry RED chronology is established,
  but that does not retrospectively satisfy a separate tidy-first step.
- macOS/Python 3.11 only. No Windows locking proof, native-syscall firewall proof,
  whole-repo suite, full public matrices, or complete mission acceptance claim.

## Authority, Scope and Provenance

Read the entire 1078-line canonical prompt in chunks, PRIMARY WP03 task contract,
spec, plan, data model, research, all referenced mission contracts, WP03 handoff
and interface note, WP01 independent review and WP02 cycle-2 independent review
(the earlier rejected WP02 report is not current approval authority).
The supplied handoff was observed as 227 lines, not the requested description's
240; its entire current contents were read.

Resolved `reviewer-renata` via the actual CLI, exit 0, builtin source, no profile
warnings. Applied independent quality-gate/reverse-spec review, no self-approval
or implementation. Ran `charter context --action review --json` and applied the
actual charter, SHA256
`9da255dc22d42fd83b8f843ee1278a46bf3a58105e260d41c57da7fd61ccd82d`.
Its bytes match the full charter read earlier in this same review session.
Successful context JSON still reports unresolved governance (#3908), zero
resolved selected references and unavailable selected directives; it is not full
resolver approval. Explicit charter rules still bind.

Reviewer setup incident: profile and first charter calls were initially
concurrent against the same disposable HOME. Charter exited 1 with
`Global asset input changed: .../home/.claude`; profile completed. A serial
charter call after that completed exit 0 with the unresolved diagnostics above.
This corrects reviewer scheduling, not production guards; no claim that the
first run passed or that this concurrency incident proves F1.

Pins:
- BASE `3a47c8b705c9d4c677b2096a4e51258751f313a2`.
- Existing-entry RED `67bf0ef02b0b867fcb51e066a5f164b0f3b51ca0`.
- Initial GREEN `07bb21e17fc71494b8e9e42e24f521376e30fcfa`.
- Metadata RED `dbcffd7c8da4d1896ef18b0e2f780a225f3697a6`.
- Final implementation `047dc8a69b32c39aa4309a6dcefe3af53855b169`.
- Observed lane HEAD `701d77611f71ed92d96d2136654a0e6994b772ec`.
  Its merge at 20:12:26 +0200 changes only mission status.events.jsonl,
  status.json and WP07/WP09 review-cycle documents relative to final. No
  implementation/test/config/charter bytes differ. Worktree status is clean.
  Tests therefore cover the final implementation tree, not a claim that Git
  HEAD literally equals the worker's final commit.
- Parent-supplied for-review event `01M1VYHM70ZY2J90Y4RAECEBJ6` and terminal
  action-review handle 34048 establish dispatch, not test acceptance.

BASE-to-final diff is exactly the 13 paths below. Root CLI, public upgrade
command, WP02 operations/repair, project skills installer, charter, shared
conftest, markers, dependency pins and baseline gates are unchanged by WP03.
No source or Git state was edited by this reviewer.

## Contract-by-Contract Assessment

| Contract | Independent assessment |
| --- | --- |
| T011 | Five real old-entry RED assertions in committed test-only source; inspected historical five-failure log. Fresh in-memory BASE bootstrap replay again fails the missing mission.yaml assertion, not import/setup. Existing positive ensures are covered by final-source blast radius. Separate tidy-first chronology remains limited as above. |
| T012 | Actual Click definitions, immutable intent; reordered/alias/equals syntax, ordinary usage errors, callback/callable-default denial, hidden conflicts and full-plan precedence have real parser assertions. Target text remains uninterpreted. New option is an in-memory semantic test, not actual public registration. |
| T013 | Pure owner preparations and retained apply APIs work independently; no root wiring changes. Real all-catalog write-denial controls pass. FAIL integration-ready composition, F1. |
| T014 | Existing package/source and managed-directory authority retained. Full real cold runtime dispatch matches independent path/action/kind/bytes/link/mode delta including parents, inventory, lock, stamp. Healthy repeat preserves mtimes. Required-source failure, orphan preservation, source/destination/parent/env drift and partial failure have exercised assertions. |
| T015 | Real full-agent commands render and apply exact bytes, extensions and readonly modes; scoped ensure has no all-agent stamp churn. Unknown prefixed links preserved. Final metadata tests retain physical agent attribution, original provider instance objects and surface IDs. Shared cross-owner parents remain F1. |
| T016 | Actual installed skill catalog read under write denial and applied through dispatcher, not only reduced fixture registry. Exact retired/edited sibling, backup collision, owned link conversion, unchanged external target and current-marker missing content are asserted. WP05 project integration is not independently delivered here; cross-global-owner overlap remains F1. |
| T017 | WP01 raw oracle, deliberate physical mutation/omission controls, equivalent homes, advancing clock, exact preparation and recheck controls exercised. Final fast/static runs complete; final subsystem result below. Raw oracle suite has one unresolved canonical-setup timeout; two intent gates remain RED. |

FR-001/NFR-001: owner-level purity is exercised, public preview remains pending.
FR-002: nonempty real physical batches demonstrated, combined ownership fails.
FR-003: each owner independently equals raw net delta, combined application fails.
FR-004: individual repeated assessment/apply preserves bytes, modes and mtimes;
combined repair cannot be certified. NFR-004: unknown/custom assets, exact
retirement and consent/backups have concrete controls, not prefix ownership.
C-001: canonical renderers/registries/models are reused; F1 violates the
single-executable-owner composition boundary.

Review checklist:
1. Dead code: **FAIL**, the two exact pending WP10 consumer gates above.
2. Synthetic fixture: **PASS** for scoped parser/owner claims; fresh real full
   catalog controls supplement fixture-selected cases. No public integration claim.
3. Silent empty return: **PASS**; incomplete source/catalog errors are typed,
   deliberate healthy/no-selection cases are explicit dispositions/skips.
4. FR coverage: **FAIL full contract**; F1 and unresolved public integration
   prevent treating owner-only assertions as all FR-001..004 acceptance.
5. Frozen surface: **PASS** for BASE-to-final authored scope; parent merge
   metadata is separately identified, not attributed to this implementation.
6. Locked decision: **FAIL**, one physical path is claimed by multiple executable
   owners; no authorization to bypass WP02 or change observations after apply.
7. Shared-file ownership: **PASS** for the exact 13 authorized paths. No
   unauthorized neighboring/root edits found; interface correction requires parent.
8. Production fragility: **PASS for fail-loud rationale**; required source,
   unproven atomic artifacts and drift refuse explicitly before writes. The
   source-level conflicts in F1 are a contract defect, not an excuse to swallow them.

## Fresh Verification

Exact expanded isolation prefix and command arguments:
[commands.md](/tmp/wp03-review.KdZx8s/commands.md). Frozen direct venv, Python 3.11.15,
pytest 9.0.3, no uv sync/install. `env -i`, disposable HOME/XDG/AppData/runtime,
WP02 sitecustomize, no credentials or hosted traffic requested. Forced env
assignment and child-Popen control prints `parent 0`, `child 0`.
Where WP02 sitecustomize is loaded, Python non-loopback sockets are denied.
WP01's sealed child environments deliberately drop PYTHONPATH; their spawn
environment still has sync=0, but this is not universal child audit-hook or
OS-firewall coverage.

The /tmp pytest plugin binds only the supplied frozen test_venv and per-xdist
worker runtime root after shared conftest isolation. Shared conftest remains
active, no production guards/markers/baselines changed. Review outputs and
disposable fixtures are external to the lane. The worker plugin that writes
ROOT failure logs was NOT loaded.

| Run / log under /tmp/wp03-review.KdZx8s | Result |
| --- | --- |
| independent-controls-final.log | 5 passed, 1 failed, 307.42s; F1. |
| independent-controls.log | Earlier control version: 5 passed, 1 failed, 86.91s. Final version adds protocol validation and individual dispatcher-positive controls; earlier failure occurred in conflict detection before provider dispatch. Not an extra independent six-case gate. |
| old-runtime-red.log | Expected RED: 1 failed, 2.90s, missing current-marker runtime mission.yaml through BASE ensure_runtime. |
| fast-final.log | 1642 passed, 3 warnings, 383.82s; exact Makefile fast selection via direct binary, two workers. |
| architecture-oracle.log | 90 passed, 3 failed, 418.77s. Two exact intent gates; one oracle setup timeout. Includes all 30 oracle tests: 29 passed, 1 failed. |
| oracle-setup-diagnostic.log | 1 failed, 102.27s; same unchanged 90-second init timeout. Diagnostic repeat, not waiver. |
| ruff.log | All checks passed, exact 13 paths. |
| format.log | 13 files already formatted. |
| mypy.log | Strict: no issues in nine explicit source/test modules. |
| blast-radius.log | 1555 passed, 1 skipped, 6 warnings, 1132.45s. Full final-source runtime, specify_cli/runtime, tool_surface and generated-writer selection. The inherited skip is test_home_unit.py:41, Windows-only. Exit 0; handle 10865 completed. |

Tests overlap; counts must not be summed as unique coverage. Worker 805-runtime
and 1642-fast runs preceded the metadata correction and are not presented as
fresh final-source passes. Inspected worker metadata RED log has two actual
logical-owner assertion failures before its test-only commit; final tests
exercise the correction. Historical five-RED logs and their source changes were
read; the fresh BASE replay is separate confirmation, not a retroactive commit.

## Evidence Integrity

Fresh BASE bootstrap source replay SHA256:
`ed66af1efd71d0cee2da2cecf16608327c9a2d811cac2d4089e9bdc99aaee9fc`.

Full independently computed SHA256 values:
```text
13a26ec79b6f73808b1e9fc3f29cf6395afbca572d4decdb9b05c4ae30210eca blast-radius.log
97284be343fdaf5edb0b77b57fa3e0ae5931dcd8c2bffcdc3cc623658e707d3b test_independent_wp03.py
dbc8787c0e22baee30c0c511ef6a532f57722b49b3d5378bb5cd61ed2558a5a8 independent-controls-final.log
2a85b2935616542ea0f67c981124631f5b72c9e1c6d8cfe28f17c32aa1fb2279 old-runtime-red.log
c698ede3b93d3da4a280292fec128fbc5de22d3bcec34c8a37c314c5589a658b fast-final.log
767f31f56c43090b29424113467f5934c22abfd0692d2b929aa83bc0030d93de architecture-oracle.log
a2301ce821650b784ce03eae374758e20beb0fda06336c664263d5b275aae30f oracle-setup-diagnostic.log
ba674af2482952dbfabdd221b2ec3c2ee1ca4e31733c54602549e4bc9e54625a commands.md
ae1438d042b69e9e88684780ef40b1f16f4db1316702ec07f7971b3a68c3c3d3 review_policy.py
d5c9862368f056879cc80f3feded73d677cdc582e7f46eb260e8ed634669aa09 profile.json
b1cd7c65d3b2a497bbd8abb57f6da4b34f8c8a1b1b43a6036cb43bfeba479f45 charter-serial.json
e3cb093fd9faadc8b78bd4b6dc11a8db40fc6aca22fac4fa46d9a4bad42b232d ROOT/wp02-policy/sitecustomize.py
```

Exact implementation paths and independently verified SHA256:
```text
3f73fc27504d800e0612436bbe37178017ef2da5bf6d77a16ee1213e67db9ef8 src/specify_cli/runtime/agent_commands.py
23eacc339e18dd11247278a9adb4d0ab677f1d49a8d531435bb0fa6cb34a9a79 src/specify_cli/runtime/agent_skills.py
46b9575879c7e7c7b14cc8c318317ad4edc6a36331155c232d07df634a6d6911 src/specify_cli/runtime/asset_preparation.py
f1bc40aeb437214c098341f737ca23200e88eb1930bca8c4ddc6d7fe518b878a src/specify_cli/runtime/bootstrap.py
d919770703e4e86cd82bab960bd7ffd7f65e01edd775c5b59f9af5e097aa631f src/specify_cli/runtime/generated_writer.py
fe42915f8fed119686c064ccbe43842f945e387b3323ec2a8376cf0855708588 src/specify_cli/runtime/merge.py
1a56dff4d3ac4377beb7e1e1e2d8baacefd59ae41b4e52813235a65d404c5e13 src/specify_cli/tool_surface/providers/slash_commands.py
edb0a2c2a20d26a9401b65be96f2d70db17246ba83c81421986234249d79b07a src/specify_cli/upgrade/intent.py
8a15fe7c858d3bf49199a4420f8e5c19cc1bbc3fd01846ea66cb4059e2cbaec1 tests/runtime/test_agent_skills.py
e6b4fc2b34c0db1912ad8776b93c22768a8ab482ce9b2320fd10cf656705d31f tests/runtime/test_bootstrap_unit.py
87fa0645842719119fb1cc5305bb0cf599669c2fdc48a59543a38bb1b3d41cda tests/runtime/test_upgrade_preview_bootstrap.py
542f5b8eb16a46a4c29606940f9c9b6fe5f9f812d86424b7c9a41b792543959d tests/specify_cli/runtime/test_agent_commands.py
98ea1e546c62c1c110340fb9b575afe50a92a0d5198e9bfec780dd9dc859cddf tests/specify_cli/runtime/test_agent_commands_routing.py
```

No push, source fix, profile-invocation closure, task status mutation,
self-approval, baseline edit or scope waiver performed.
All review commands have completed. No live command handles remain.
