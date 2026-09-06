# Acceptance and Anti-Vacuity Contract

Audience: agentic-framework-core-team. Updated: 2026-09-06.
Planned checks, not executed evidence. Instantiates Renata's G/B/P matrices.

## Harness Boundary

Invoke the real source console entrypoint through a subprocess, resolving the
absolute .venv/bin/spec-kitty before changing child HOME. Record source commit,
module/distribution location and package version. No replacement Typer app,
root-callback patch, mocked provider/installer or bootstrap suppression.
Closed stdin, bounded timeout, capture complete stdout/stderr. Healthy output
and expected semantic result must accompany purity; a startup crash is not pass.

Prepare every cell independently in a disposable Git repo/home. Canonical
setup/manifest writers establish realistic fixtures before the measured
snapshot; inject each deliberate defect afterward. For cold homes, prepare
project assets using another setup home, then attach a genuinely untouched home.
No init/profile/doctor call may prewarm the measured cold home.

Explicit child environment binds HOME, USERPROFILE, XDG_CONFIG_HOME,
XDG_CACHE_HOME, XDG_DATA_HOME, XDG_STATE_HOME, APPDATA, LOCALAPPDATA,
SPEC_KITTY_HOME and temporary roots inside sandbox. Clear/rebind inherited
asset/config/source overrides that could escape it. SaaS sync=0 set last.
All symlink targets/sentinels remain in sandbox. No production network.
PYTHONDONTWRITEBYTECODE=1 for source runs. Git observations use
GIT_OPTIONAL_LOCKS=0. Keep CI=1 normal cells plus non-CI/TTY cells below;
CI suppression must not be the reason preview is pure.

Independent lstat oracle records every node, normalized root/path, kind,
SHA-256 bytes, exact readlink target, permission bits and mtime_ns. Include
ignored/untracked files, empty dirs, dangling links, runtime/cache/locks,
manifests, custom configs and third-party sentinels. No broad .kittify/.git/cache
exclusion. Record HEAD/refs/index separately from asset effect equality.
Read access times excluded. Across separate copies, compare content/type/mode/
target and normalized effects, not raw mtimes; within each preview/idempotent
apply cell, mtimes must remain unchanged too.

Oracle controls must detect, independently: ignored-file edit; empty-directory
creation/removal; dangling-link deletion; retarget; chmod; same-bytes rewrite
with changed mtime. A version which deliberately omits each observation must
fail its control. Production effect-building helpers cannot implement the oracle.

Snapshot equality proves persistent purity, not transient write/delete absence.
In addition, instrument the real process's assessment boundary using a recording/
denying audit hook or platform filesystem tracer covering create/open-for-write,
mkdir, unlink/rename, chmod, utime and link operations. Do not stub the owners.
Install the hook before CLI imports in a test-only entry wrapper calling the
real main; retain ordinary unwrapped subprocess snapshots as the primary witness.
Record any unsupported syscall coverage explicitly, and test attempted
write-then-delete as a negative control. Do not claim zero syscalls from snapshots.

## A: Global Purity Matrix

| ID | Home state |
| --- | --- |
| G0 | Runtime and all global tool roots absent |
| G1 | Real populated runtime, skills and commands all stale |
| G2 | Only runtime stale marker and recognizable managed bytes |
| G3 | Only global skills stale marker/content |
| G4 | Only global commands stale marker/content |
| G5 | Fully healthy/current, no cleanup candidates |
| G6 | Current markers but required command missing or stale file marker |
| G7 | Current markers plus a proven-owned retired skill cleanup candidate |

Run all 8 against a same-version healthy project, in human --dry-run --verbose
and legacy --dry-run --json, each with/without --project; all --no-worktrees.
32 independent public cells. Run --plan-json on G0/G1/G5/G6/G7 (5 more);
legacy strict-schema checks remain in every legacy cell. Require G0/G1 human
and full plan to describe real pending global preparation, no startup mutation.
Legacy summary must disclose pending work and point to the full plan.

## B: Target Matrix

Healthy G5, current supported schema, explicit metadata version 3.2.7rc1.
These numbers are historical test fixtures, not release decisions.

| Requested | Relation / target validity |
| --- | --- |
| 3.2.6 | lower / reject |
| 3.2.7rc0 | lower / reject |
| 3.2.7rc1 | equal / valid |
| 3.2.7rc2 | higher / valid |
| 3.2.7 | higher / valid |
| 3.2.8 | higher / valid, no invented future migrations |

All six x human/legacy JSON x with/without --project, --no-worktrees: 24 cells.
Add one full-plan cell per row and malformed targets empty string, not-a-version
and control-character input across human/legacy/full. Assert explicit bounded
errors and no traceback/mutation. Add omitted target, unknown current, malformed
known metadata, and current schema > MAX_SUPPORTED. Pair lower and higher
targets with stale, too-new and corrupt schema to prove independent reasons
and precedence. Do not exhaustively multiply unrelated axes.

For legacy lower-target compatible project: decision BLOCK_INCOMPATIBLE_FLAGS,
case none, payload exit_code 2, current/target reason, project.state compatible,
process 0 for --dry-run. Human exits 1; full exits 2. Too-new legacy dry-run
retains process 5. No target-validity test may assert migrations=[] means valid
or higher implies ALLOW in the presence of independent schema blockers.

## C: Same-Version Plan/Apply Matrix

G5 default, current version/schema, no pending migrations. Realistic configured
claude/codex/cursor baseline plus isolated native-config/bundle cases where
applicable; no forced activation just to manufacture repair counts.

| ID | Fixture / witness |
| --- | --- |
| P0 | Repaired baseline, first and second apply both no persistent effects |
| P1 | Missing managed command files, nonempty creation |
| P2 | Missing managed skills, nonempty creation |
| P3 | Missing profile projections, nonempty creation |
| P4 | Missing command/profile manifests, retained generated files; prove safe adoption or preserve ambiguity |
| P5 | Truncated/stale manifests plus stale managed orientation/config, nonempty appropriate updates |
| P6 | Combined commands/skills/profiles/manifests, all applicable families nonempty |
| P7 | P6 plus missing mission_type_activations, provisioning represented |
| P8 | Missing + drift + unknown custom command/skill + sandbox symlink sentinel |

Repeat P6 with G0/G1 (11 variants total). For each, on independent equivalents:
human preview, legacy JSON preview, full-plan preview, actual
upgrade --yes --no-worktrees; then on the resulting state repeat the three
previews and second actual apply. 8 processes per variant, 88 total excluding
fixture setup. Legacy remains strict; full plan supplies exact path effects.
Human output must disclose the same operations without parsing an internal API.
This extends Renata's six-process matrix for the chosen separate plan surface.

Derive actual net persistent delta independently, normalized per
owner-operations.md. Compare effect sets exactly on deterministic successful
fixtures: roots, paths, action and final type/mode; every supporting manifest,
directory, backup and pruning path included. Nonempty P1/P2/P3/P6 witnesses
prevent vacuous equality. Do not compare logical surface counts with file counts.
P8 permits known independent repairs while drift stays unchanged/reported with
existing noninteractive failure; second apply must still have zero new churn.

After hashes are per-assessment desired bytes, not promises of identical clocks
across separate processes. For cross-copy rendered manifests, normalize only
documented newly assigned installed_at/updated_at/last_upgraded_at timestamps
where the existing owner schema uses them; retain exact field paths and raw
copies in evidence. The sole additional creation-time allowance is root
`/created_at` of `.kittify/skills-manifest.json` newly created from an absent
manifest in both independent baselines; retain absence proof and raw hashes.
Do not normalize any pre-existing manifest creation time or mission-meta
created_at. Do not normalize entire manifests, identities, source
hashes, owner sets or substantive content. Within a single process, applied
bytes must equal its prepared bytes; unchanged manifests cannot refresh dates.

## Focused Boundary Cells

- Explicit empty mission_type_activations: [] remains untouched; missing key
  provisions. Retain existing provisioning/migration selector regression cases.
- Instantiate P7 for both legacy config and a commented pointer-based charter;
  public preview is complete/write-free and apply preserves comments/unrelated
  sections with bytes matching its preparation. Explicit empty is unchanged in
  both layouts; dangling pointer is an honest blocked assessment. Keep the
  charter layer gate rejecting imports of specify_cli operations.
- Clock cells: an ownership-proven, consent-permitted replacement assessed at
  T1 and applied at T2 retains exact prepared bytes/hashes and backup paths.
  Equivalent independent public preview/apply fixtures at different times
  select identical persistent backup paths/actions, including existing candidate
  and suffix collisions. Preserve every prior backup, verify exclusive creation
  race refusal, and repeat apply for no churn. Clock injection at an owner seam
  supplements rather than replaces public subprocess/snapshot witnesses.
  A writer that resamples manifest time and an allocator that uses current time
  are negative controls; both must fail. Never normalize persistent paths.
- Missing-manifest clock cell: independent public preview at T1 and apply at T2
  reach the real managed-skills owner with `.kittify/skills-manifest.json` absent
  in both baselines. Only its newly allocated root `/created_at` receives the
  added normalization above. Changed pre-existing manifest `/created_at` and
  changed mission-meta `created_at` must each fail negative controls. Preserve
  raw hashes, exact per-invocation prepared bytes, preview mtimes and unchanged
  second-apply mtimes; no per-invocation normalization.
- Truncated JSON/malformed manifest, corrupt agent config, missing package source:
  blocked/incomplete not ALLOW/empty, no all-agent fallback. A truly absent
  manifest is not treated as malformed; ownership of retained files is separate.
- Shared codex/vibe root and per-agent owners: one physical write, retained
  refcounts. Disabled agents/Amazon Q profile exception not auto-repaired.
- Profile deactivation with an owned prune candidate; drifted prune candidate
  preserved; stale full-agent bundle reports manifests and all changed members.
- Native orientation/settings/hook mixed file: preserve unowned bytes/keys;
  applicable staged bundle fixture covers output manifest and member files.
- Custom canonical-path content plus another missing command reproduces manifest
  adoption hazard; unknown spec-kitty.custom symlink is never deleted.
- Change destination or manifest/source between assess/apply, including parent
  symlink replacement: owner batch aborts before writes and reports conflict.
  A focused owner integration seam is appropriate for this race; do not replace
  the ordinary public subprocess acceptance with a mocked race test.
- Warm/cold non-CI TTY spot checks with cacheable version data: no network
  attempt or cache/show-time/preference persistence in preview.
- Reordered options, --target=value, redundant --plan-json --json --dry-run,
  --cli conflicts, preview plus hidden agent-choice: selected schema, purity
  and exit rules in upgrade-cli.md. Verify ordinary help/version/next/upgrade
  apply still work and are not accidentally made preview-only.
- Focused cold-home public hidden-intent cells: --project --json combined with
  each of --agent-choice (valid choice/latest pair), --agent-check and
  --agent-latest alone; explicit --cli --json plus hidden flags; no-project
  ordinary guidance plus hidden flags. Require one pinned legacy conflict
  payload and process 2, complete unchanged snapshots and no transient writes.
  Repeat a representative conflict with --plan-json for full-envelope precedence.
  Standalone hidden check and valid choice/latest operations are positive controls
  retaining their existing outputs/exits and legitimate preference behavior;
  run those only in disposable homes. No full Cartesian flag expansion needed.
- Default actual upgrade --json on too-new schema: full pinned legacy planner
  payload, BLOCK_CLI_UPGRADE, case project_too_new_for_cli, semantic/process 5,
  no bootstrap or other writes. Parse entire stdout and validate the schema.
  Pair with --plan-json too-new full-envelope/code-5 control; retain the distinct
  standalone invalid-target actual-outcome fixture. These are public source
  subprocess cells, not tests of the guard helper alone.
- One same-version worktree fixture: with --no-worktrees no changes/discovery
  in that root; without it planned metadata/stamp work and actual outcome agree.
  Add existing fatal/skipped worktree behavior and dirty baseline/manual-review
  auto-commit tests, without multiplying all G/P cells across worktrees.
- Blocked mission fixture: preview and upgrade --yes leave identity, events,
  snapshots and verdicts untouched absent separate consent. Retain existing
  explicit-positive-consent test proving repair remains reachable.

## Red, Green and Installed Witness

Before implementation, witness RED through unchanged public commands for G0/G1
purity, P6 human/legacy omission versus real apply, lower-target legacy JSON,
and original full corpus audit. A --plan-json unknown-option/import failure
cannot serve as #3901 red evidence; it tests a new API, not the old defect.
Each owner bugfix adds red behavior at its existing seam plus public blast radius.
Commit the appropriate failing test before implementation (parent's workflow).

Final source suite runs all matrices. One independently installed wheel then
replays G0/G1/G5 previews, lower/equal/higher/malformed legacy/full target cells,
P6 plan/apply/repeat and separate-consent control. Resolve its executable
absolutely and record wheel SHA/distribution/module provenance. Clear PYTHONPATH,
template/source overrides injected by conftest and any editable-install path.
Run from disposable projects outside source checkout; no source tree on sys.path.
Use existing isolated build/test dependencies; no production dependency change
or global tool install. Wheel build/install is future verification, not claimed
executed by this plan.

Mutation controls: restored unconditional bootstrap, omitted manifest effect,
downgrade ALLOW at process 0, omitted ignored-file observation, forced overwrite
of user sentinel, and transient write/delete all must fail their relevant
checks. Mutate only disposable test/source copies, never the shared checkout.
Architecture gate must cover concrete entry/owner floor and self-mutation;
green empty allowlists or zero discovered owners are failures.

## Gates and Reporting

Owners run changed tests + full affected subsystem tests + make test-fast.
Use direct warm .venv/bin/pytest, ruff and mypy with sync=0; no defensive uv sync.
Run changed-module lint/types and relevant layer/import/dead-code gates; full
tests/architectural for new architecture/shared-test changes under repo policy.
No broad make test-full in per-WP runs. Record commands, counts, red reason,
green result, commit/executable/wheel identity and snapshot hashes. Existing
failures are classified and reported under repository policy, never retried to
green or masked with skip/xfail. No tests or architecture/performance gates have
been executed in this planning turn.

Measure cold/warm planning performance against <2s typical-project budget
separately from expensive fixture creation/wheel build. Record baseline and
final p50/p95; use recorded wall time, not a fragile universal timing assertion.
Windows/macOS/Linux path/mode behavior needs evidence; capability-specific
symlink restrictions must be reported and covered on a capable platform, not
silently waived across all platforms.

## Parent-Owned Final Gate Table

These are consolidation prerequisites, not additional per-WP broad suites or
an authorization for this author to run tests. The runtime review CLI does not
execute these gates; its PASS cannot substitute for them. Evidence sources:
[readiness/provenance](../../../../pre-spec-reviewer-renata/gate-readiness.md),
[five-case current-source baseline](../../../../pre-spec-reviewer-renata/baseline-five-report.md)
and its preserved baseline-five-20260906-133810/ directory. CORE is this checkout;
E2E is sibling spec-kitty-end-to-end-testing, origin
git@github.com:spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing.git.

| Gate / parent owner | Required selection and pass evidence | Prerequisites / fail-closed disposition |
| --- | --- | --- |
| Full CORE contracts | .venv/bin/pytest -c pytest.ini tests/contract/ -v -ra -p no:cacheprovider; full collected selection, packaging/envelope/consumer witnesses | Effective fixture policy, isolated build/install and required dependencies established; missing imports or relevant importorskip are not a pass |
| Full CORE architecture | .venv/bin/pytest -c pytest.ini tests/architectural/ -v -ra -p no:cacheprovider; full suite including anti-vacuity/mutation evidence | Literal CI=true, reachable origin/main merge-base and efc0003b563d4a447e29bbfc726bf97c5179a209, formatter/pytestarch prerequisites; #3911 exact-operation remediation independently reviewed, no baseline shift/skip |
| Current cross-repo scenarios | E2E .venv/bin/pytest -c pyproject.toml scenarios/ -v -ra -p no:cacheprovider; all current cases plus the five identities below executed | Correct E2E interpreter/config/import path and explicit CORE bindings; baseline two failures resolved/tracked under owner policy; inner drift assertion plus unmutated green control mandatory |
| Terminal issue matrix / parent mission reviewer | #3900-3903 each has fixed, verified-already-fixed or explicitly accepted deferred-with-followup disposition, linked red/green/artifact and independent review evidence | in-mission/pending is not terminal; no deferral silently weakens approved FRs. Gate failures and external followups have distinct explicit dispositions |

Use SPEC_KITTY_ENABLE_SAAS_SYNC=0, CI=true, PYTEST_ADDOPTS cleared and
PYTHONDONTWRITEBYTECODE=1 at launch; these settings alone do NOT satisfy the
effective environment prerequisite. CORE tests/conftest.py:457-460 sets sync=1
in an autouse fixture. Parent must establish and record an approved harness
policy preserving the requested sync-off execution boundary without disabling
conftest wholesale or deselecting tests. This is an environment hazard, not
evidence of live SaaS/network activity. No recursive lock/firewall was proven
by the baseline's outer subprocess observer.

Parent has authorized isolated package installation; readiness's former
no-install blocker is superseded, not the isolation/provenance requirements.
Allow necessary package download/install only in disposable envs/caches under
that authorization; do not call those runs network-free. No live credentials,
hosted endpoints or SaaS actions. Record interpreter/pytest/dependency versions,
package sources and warnings. Baseline nested Python 3.13.9/pytest 9.1.1 differed
from outer E2E 3.13.1/8.4.2: resolve/record reproducibility, not a false root-cause
waiver for the missing diary module. No production dependency changes.

Bind SPEC_KITTY_REPO and SK_E2E_SPEC_KITTY_REPO to the same absolute CORE;
SK_E2E_SPEC_KITTY_BIN/PYTHON to its direct warm binaries. Ensure E2E package
importability and its declared pytest range; avoid implicit uv/PATH fallback.
Use disposable HOME/USERPROFILE/XDG/APPDATA/LOCALAPPDATA/runtime/temp roots,
no host credentials, and preserve fixture evidence. Run serial first; any
parent-authorized xdist CORE run uses --dist loadfile. Keep E2E configured
marker exclusions; clearing inherited PYTEST_ADDOPTS is not removing config.

### Five-Case Floor and Known Red

At CORE 6ada9613b8b8713809da4089bda11d9d35065a77 and E2E
1bc2a9b535a66ba27f2707e2344fc4284e896a26, Renata observed exactly
2 failed, 3 passed, 0 skipped, 0 deselected; exit 1, 329.07s.
Paths below are relative to E2E scenarios/:

| Exact node identity | Baseline / required followup |
| --- | --- |
| dependent_wp_planning_lane.py::test_dependent_wp_planning_lane_lifecycle_smoke | FAIL, child-0066: WP04 planning-artifact claim cannot establish approved lane-c ancestry. Tracked in [CORE #3912](https://github.com/Priivacy-ai/spec-kitty/issues/3912). Parent routes actual planning-workspace/self-heal semantics to existing core owner; no guard bypass or manual fixture merge |
| uninitialized_repo_fail_loud.py::test_uninitialized_repo_fails_loud[specify] | PASS, child-0074; rerun and retain real structured error witness |
| uninitialized_repo_fail_loud.py::test_uninitialized_repo_fails_loud[plan] | PASS, child-0082; rerun and retain real structured error witness |
| uninitialized_repo_fail_loud.py::test_uninitialized_repo_fails_loud[tasks] | PASS, child-0090; rerun and retain real structured error witness |
| contract_drift_caught.py::test_contract_drift_caught | FAIL, child-0096: fake events package missing spec_kitty_events.diary causes collection error, not intended envelope assertion. Tracked in [E2E #411](https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing/issues/411). Parent schedules existing harness owner; require realistic package surface, identified executed intended assertion and unmutated green control |

Track both baseline failures with source SHA, exact traceback, owner and linked
followup before any accepted pre-existing-failure disposition under the charter.
They are product/harness defects, not environmental skips. No unconditional
waiver and no duplicate harness-repair IC/WP here; parent controls separate
authorized repair and rerun. Passing only the three uninitialized cases or an
outer nonzero drift subprocess does not complete this floor. A tracked red
remains red until explicit authorized disposition; never label it passed.

### Retired SaaS Scenario and Evidence Closure

scenarios/saas_sync_enabled.py is RETIRED BY SOURCE, not skipped or passed.
E2E deletion e59564bd8b82f7912b8db67087712ec84fc47cf8 and CORE accepted ADR
docs/adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md
establish transport retirement; non-sync doctor coverage moved to
tests/test_agent_status_doctor_e2e.py. Parent records the stale skill/older ADR
selection mismatch with this provenance. Do not resurrect transport, enable
hosted traffic, or substitute unexecuted Docker successor lanes. This is not
a blanket Gate 3 exception or waiver of the surviving five cases.

For every final gate retain exact argv/cwd, source and wheel SHAs/dirty scope,
effective config/environment, runner/dependencies, start/end/exit, total
collected/executed/deselected/skipped with reasons, stdout/stderr and JUnit.
Preserve nested drift output and actual assertion identity, not just outer exit.
Parent adjudicates each relevant skip/failure independently and obtains reviewer
signoff; no summary green can conceal missing coverage. Gate execution and
terminal matrix evidence remain pending, not claimed by this planning document.

Additional parent gate-state evidence: golden-arity recurrence is recorded on
existing [CORE #3458](https://github.com/Priivacy-ai/spec-kitty/issues/3458).
Parent reports narrow Op 01M1V8WKCPN7KZT629FP57NA2X fix: 33 passed, Ruff/mypy
clean, with independent golden review APPROVE. Parent reports guard and golden
fixes integrated at c3657a86a; integrated tests and original next are running.
These parent-supplied results are not independently rerun here or full-gate
approval. Retain their review/disposition in final
evidence; do not create another architecture-source repair lane in this mission.
