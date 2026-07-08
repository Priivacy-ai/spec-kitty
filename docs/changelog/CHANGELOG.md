---
title: Changelog
description: Canonical changelog for the Spec Kitty CLI and templates, following Keep a Changelog and Semantic Versioning, with added, breaking, and fixed entries per release.
doc_status: active
updated: '2026-07-08'
---
# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the Spec Kitty CLI and templates are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 3.2.6

_The 3.2.6 development cycle is open. Entries land here as missions merge._

### ✨ Added

### 🐛 Fixed

### ♻️ Changed

## [3.2.5] - 2026-07-08

### ✨ Added

- **Coord/primary placement-partition lock — one topology-aware seam owns where
  every mission artifact is stored and read (#1716, #1878/G2).** Formalizes
  `PlacementSeam.write_target(kind)` / `read_dir(kind)` as the single thin
  authority over the existing `resolve_action_context` SSOT and routes every
  remaining write site through it — **fail-closed** via `PlacementResolutionRequired`
  (a real resolution failure raises rather than silently committing to the
  operator's checkout). An architectural ratchet forbids the
  `CommitTarget(ref=<checkout>)` grammar (a self-test proves it bites), and an
  end-to-end characterization test locks the behaviour. Canonical partition:
  coord branch = lifecycle (status/notes/trace/issue-matrix/move-task); primary
  = stable planning (spec/plan/WP outlines); no-coordination topology → all
  primary. RETROSPECTIVE delegates to the existing `resolve_retrospective_home`
  (no second authority). Also **fixes #2091** (an empty `mid8` no longer builds a
  malformed `kitty/mission-<slug>-` coordination branch → `git worktree add`
  exit-128; the `CoordinationWorkspace` composition seam fail-loud-guards it) and
  **#2250** (a never-coordinated mission no longer reports
  `COORDINATION_BRANCH_DELETED`). **The read side is now locked too (#1716
  closeout):** every remaining coordination-surface *read* — the kind-blind
  `resolve_feature_dir_for_mission` sweep (#2453) and the inline `meta.json`
  reads (#2100) — routes through the same topology-aware seam kind-correctly, so
  `spec-kitty accept` no longer reads a stale `-coord` acceptance matrix (#2404)
  and planning artifacts always resolve to their canonical surface regardless of
  the working directory. A non-vacuous architectural ratchet keeps the routed
  read classes from silently regrowing. Closes epic **#1716** and #2453 / #2100
  / #2088 / #2404.
- **Doctrine/charter pack paths support environment-variable indirection
  (#2437).** Pack-location fields (e.g. an org-pack's `local_path`) previously
  had to be hardcoded absolute paths, so a shared, committed `.kittify` config
  resolved only on the machine of the developer who wrote it and broke for every
  teammate and CI runner. Pack-path templates now expand `${VAR}`/`$VAR` and `~`
  at read time (via `os.path.expandvars` + `expanduser`), so a portable form
  like `${SPEC_KITTY_PACK_HOME}/acme-doctrine` can be committed once and each
  environment resolves it against its own base. Expansion is **fail-closed**: an
  unset/empty env token raises rather than silently collapsing to a wrong path
  (e.g. `${UNSET}/acme` → repo root). Purely additive — literal absolute paths
  keep working.
- **Review-time regression gate at `move-task --to for_review` (#572).** When a
  work package moves to `for_review`, Spec Kitty now auto-scopes the CI shards
  that cover the WP's changed files and re-runs them, so a WP that broke a
  shared contract pinned by a test *outside* its `owned_files` is caught at
  review time instead of only at merge. Warn-only by default; opt in to a hard
  block with `review.fail_on_pre_review_regression` (enforced only when
  `review.test_command` is set; `move-task --force` overrides), and override the
  scope per-WP via frontmatter `pre_review_test_scope`. See
  [review-gates.md](../guides/review-gates.md).
- **`spec-kitty review --check-residual` + environment-parity preflight
  (#2283).** The new `--check-residual` flag runs CI's always-on
  `unit-contract-residual` `-m` selection over `tests/` locally — the `-m`
  expression is read **live** from `.github/workflows/ci-quality.yml`, so a
  previously CI-only marker-orphan failure can be reproduced before pushing. The
  `spec-kitty review` preflight also detects local-vs-CI environment skew
  (installed package versions diverging from `uv.lock`, plus typer/click
  lock-parity), warning by default and failing closed under
  `SPEC_KITTY_ENV_SKEW_FAIL_CLOSED`.

### 🐛 Fixed

- **Post-merge stale-assertion analyzer stops false-positive storms on
  behavior-preserving refactors (#2031, #2343).** A relocation/re-export (a
  WP05 extraction produced 180 false findings and tripped the drift ceiling)
  and generic-literal noise both flagged as stale assertions. The analyzer now
  (a) suppresses a removed identifier only when the origin file's **module-level
  head** still re-exports/imports it (keyed on head-importability — not
  bare-name-anywhere, so a genuine deletion of a common name like `run`/`main`
  is still flagged; a nested `import parse` does not mask a real `def parse()`
  deletion), and (b) suppresses literal-only noise by **genuineness** (a pinned
  generic-token set / all-punctuation), never by length (a short literal like
  `"E001"` can be assert-critical). Both paths suppress rather than
  info-downgrade, so render surfaces and the FP ceiling are unchanged.
- **Review-prompt files no longer accumulate unbounded; coverage-allowlist
  repointed off a removed module (#2439, #2443).**
  `write_review_prompt_with_metadata()` now prunes review-prompt files to a
  newest-preserving cap after each write — fail-safe, and never pruning the
  current invocation's own file — closing the LC-7 retention residual of #1842.
  Separately, the `diff-coverage` critical-path `--include` allowlist still
  referenced the stale `src/specify_cli/core/mission_detection.py` (removed in a
  rename); it is repointed to `src/specify_cli/lanes/branch_naming.py` in **both**
  the CI workflow and its test authority in lockstep, with a glob-aware existence
  guard so a phantom allowlist entry reds instead of silently covering nothing.
- **`spec-kitty agent mission finalize-tasks` accepts glob-only `owned_files`
  (#2446).** A work package whose `owned_files` used a filename glob (e.g.
  `src/foo/*.py`) with no explicit `authoritative_surface` was rejected because
  `infer_authoritative_surface` produced an invalid `src/foo/*.py/` path. It now
  reduces a glob-bearing final path segment to its directory, so glob-only
  ownership infers a valid authoritative surface. (Fix landing via PR #2454.)
- **A retired skill's projected files are now drained by surface repair instead
  of orphaned forever (#2409).** When a skill was retired from the registry,
  `spec-kitty upgrade --project` could not reconcile its leftover projections:
  the repair path warned `Cannot repair … skill not found in registry` on every
  subsequent upgrade and left the files in place (committed, where the repo
  tracks skill surfaces; a dangling symlink, where the global root had dropped
  the skill). Repair now reconciles retirements **manifest-driven**: entries in
  `.kittify/skills-manifest.json` whose skill no longer exists in a *live*
  registry have their projected files removed — symlinks unlinked, hash-clean
  copies deleted, user-**modified** copies archived to
  `.kittify/.migration-backup/agent-skills/` instead of deleted — emptied skill
  dirs pruned, and the manifest entries dropped, silencing the repeat warning.
  Only ledger-recorded paths are ever touched (a user-authored skill sharing
  the projection root is never scanned), and an **empty** registry never
  retires anything (a broken canonical source must not mass-drain the
  manifest).
- **Test-session state leaks closed: per-mission prompt-tmp namespace +
  workspace-context tombstone (#1842, #2032).** Runtime prompt files are now
  written under a per-repo/per-mission namespaced temp directory
  (`<tmp>/spec-kitty-prompts/<repo-id>/…`) instead of a shared flat `/tmp`
  path, and a lane's workspace-context sidecar is now tombstoned when its
  worktree is torn down at merge (or when the lane is canceled) — clearing the
  stale-context and prompt-litter residue flagged by the #1931 `/tmp`-hygiene
  audit. A session-scoped pytest reaper (controller-gated, run-uid-scoped, and
  never touching the real `~/.spec-kitty`) now fails the suite if a test leaks
  repo-root residue, so new leaks are caught at their source.
- **Dashboard: PR-bound missions planned on a feature branch are visible again
  (#2430).** The dashboard scanner resolved ONE directory per mission,
  coord-worktree-first — but under coordination topology the two partitions
  live on different surfaces: `spec-commit` lands planning artifacts
  (`spec.md`/`plan.md`/`tasks.md`/`tasks/`/`meta.json`) on the **primary**
  surface, while the live event log lives on the **coordination** branch. The
  scanned `-coord` copy therefore held only status writes, so the legacy
  existence filter (numeric prefix or `tasks/` present) silently dropped any
  in-flight post-083 mission from `/api/features`, and artifact viewers/kanban
  read the wrong surface. The scanner now splits the read per partition —
  planning artifacts primary-first through the same kind-aware read seam the
  #2331 identity fix uses (`resolve_planning_read_dir`), live lane state from
  the gather-resolved coord surface — so an in-flight coordination mission
  lists with its real spec/plan/tasks AND live kanban lanes. Same
  coord-shadows-primary class as #2331; the accept-side sibling is #2404.
- **Session banner no longer recommends a downgrade (#2413).** The
  session-presence health check decided "upgrade-available" with a bare
  inequality (`avail != current`), so any machine whose installed CLI was
  *newer* than the cached PyPI latest — a fresh release not yet in the 1-hour
  cache, or an rc/dev install — got "⚠ Upgrade available: 3.2.2" while running
  3.2.4. Both health branches now use `packaging.Version` ordering
  (`avail > current`); unparseable versions are treated as no-upgrade so
  session start never breaks on a weird cache value.
- **The shared Agent-Skills projection root and the per-machine skill install
  ledger are now gitignored (#2412).** The skills installer projects global
  canonical skills into `.agents/skills/` (codex/vibe/pi/letta) preferring
  **absolute symlinks** into the user-global root — machine-local content by
  construction — but unlike `.claude/` and the other agent dirs (gitignored
  wholesale at init), bare `.agents/` was never covered by any init path,
  registry entry, or migration, so the `/Users/<name>/...` symlink blobs were
  committable (and the upgrade auto-commit would land them automatically).
  `.kittify/skills-manifest.json` (per-machine timestamps/hashes/delivery
  modes) had the same gap. Both are now registered `IGNORED` state surfaces
  (fresh `spec-kitty init` gitignores them, and `spec-kitty doctor`'s
  present-but-not-gitignored warning covers them), and a sibling backfill
  migration (`3.2.5_agents_skills_gitignore_backfill`) adds the entries on
  `spec-kitty upgrade` for already-initialised projects. The symlink-vs-copy
  delivery question (ask 3 of #2412) is tracked separately on the issue.
- **`spec-kitty upgrade` now commits worktree churn on every checkout, not just
  main (#2392, closes #2385/#1873, pins #2105).** The upgrade auto-commit
  captured a porcelain baseline for the main checkout only, so migration writes
  it made in sibling worktrees were left uncommitted — dirtying them and
  blocking coordination-topology merges (NFR-002). The porcelain-baseline commit
  routine is extracted into a canonical per-checkout seam
  (`upgrade/autocommit.py::commit_touched_checkout`); the migration runner now
  snapshots each worktree *before* its writes and commits only that new churn on
  the worktree's own branch (in-flight WP edits are never swept in;
  `manual_review_required` migrations skip the commit with a warning;
  detached-HEAD skips instead of guessing a ref; `--dry-run` stays a strict
  no-op). #1873's self-healing path is restored (metadata synthesized from
  `None` is marked dirty so it's saved even when detected version == target).
- **Legacy-topology warning no longer over-fires on intentional
  coordination-less missions (#2351).** The once-per-mission warning keyed on
  `coordination_branch` absence, so it fired for genuinely deliberate
  `single_branch`/`lanes` shapes (#2218) as well as truly pre-SSOT missions. A
  new warning-only classifier gates just the emit on the canonical stored
  `MissionTopology` + flattened flag (warn iff coordination branch absent AND
  stored topology null AND not flattened; malformed still warns); the shared
  `_is_legacy_mission` predicate that drives worktree routing and write-contract
  selection is left byte-for-byte unchanged.
- **`.kittify/migrations/` and `.kittify/logs/` are gitignored and backfilled
  (#2384, completes the #2369 sweep).** Two more generated `.kittify/` subtrees
  (mission-state repair manifests + quarantine backups; orchestrator per-WP
  logs) were neither IGNORED state surfaces nor backfilled, so they dirtied the
  tree and failed `accept`'s git-dirty check. Both are now registered IGNORED
  local-runtime surfaces (fresh `init` gitignores them) with a sibling
  backfill migration for already-initialised projects on upgrade.
- **`saas_client` no longer defaults to a hardcoded `api.spec-kitty.io`; it
  fails closed (#2248).** `load_auth_context` fell back to a baked-in SaaS URL
  when neither `SPEC_KITTY_SAAS_URL` nor `.kittify/saas-auth.json` supplied one,
  risking silently pointing the client at the wrong server. With the #2146
  target-authority decision in place, the default is removed and a no-URL
  resolution now raises `SaasAuthError` (caught where the no-token path already
  was).
- **Sync runtime callers route through the canonical resolved target authority
  (#2146).** The tracker client, sharing client, and background sync read the
  raw `SyncConfig.get_server_url()` (config-only, hardcoded default) instead of
  `resolve_runtime_target().resolved_server_url`, so with `SPEC_KITTY_SAAS_URL`
  set, auth/readiness hit the env target while these surfaces silently posted to
  the config target (the SC-008 split-brain). All three now resolve the same
  target as auth/readiness, and `sync status`/`sync doctor` report the resolved
  URL. Separately, `sync server <url>` now accepts loopback HTTP
  (`http://localhost`/`127.0.0.1`/`::1`) for the documented local-Docker-SaaS
  dev workflow while still requiring HTTPS for remote hosts.
- **compat-planner contract checks are revived (#2419).** Two test surfaces
  validated `upgrade`/`render_json` payloads against the committed
  `compat-planner.json` contract but silently no-op'd in CI since 2026-04-27
  (each resolved the contract via a maintainer-worktree-only path, so it was
  `None` and validation was skipped). Both now anchor on the repo root, load
  unconditionally, and fail hard on a missing/unreadable contract — which caught
  one real drift (a migration description trimmed to satisfy `maxLength`).
- **migration_id contract pattern widened to admit the dotted convention
  (#2339).** The `compat-planner.json` `migration_id` pattern
  (`^[a-z0-9_]{1,128}$`) rejected 83 of 89 real dotted ids (e.g.
  `3.2.0rc45_...`) — a contract-authoring bug that let #2339-class drift slip
  through unnoticed. Widened to `^[a-z0-9_.]{1,128}$` (a backward-compatible
  widening; no shipped `migration_id` renamed, so persisted per-project ledgers
  keep validating).

### ♻️ Changed

- **Internal: version-comparison primitives consolidated into one canonical module (#2417, landing via PR #2414).**
  Landing the #2413 fix surfaced three independent "is version A newer than
  version B" implementations that had drifted apart in edge-case handling:
  `cli/commands/upgrade.py::_version_is_newer` (caught the broad `Exception`
  instead of the specific parse failure), `core/upgrade_probe.py::_classify`'s
  inline comparison, and the `_upgrade_is_available` helper #2413 had just
  added to `session_presence/manager.py`. All three now delegate to a new
  pure module, `specify_cli.core.version_compare`
  (`try_parse_version` / `is_version_newer`), with no CLI/click/typer
  imports so it is safe to import from any layer; the two duplicate boolean
  helpers are deleted outright, no aliases left behind. No user-facing
  behavior change.
- **Internal: CI-topology census freshness gate is now LOC-insensitive
  (#2416).** The gate compared each worklist entry's exact line count and an
  LOC-derived sort order, so any PR that shifted the line count of a worklist
  directory went red regardless of touching CI routing — a maintenance tax two
  PRs paid inside 24h. It now checks membership + committed routing plan only
  (an order/LOC-insensitive index at the shared derivation), fixing both the
  pytest gate and the `--verify-census` CLI by construction. Zero `src` changes.
- **Internal: test-suite `/tmp` hygiene sweep (#1842, epic #1931).** 97
  grandfathered test files were converted off literal `/tmp` paths to
  `tmp_path`/sentinels, and the empty-`/tmp` ratchet was flipped to a
  self-consistent hard gate so new literal-`/tmp` leaks fail fast. Also fixed a
  test-only `--output=` parser leak that could write an invalid Windows filename
  (breaking the Windows critical CI job), with a new arch guard blocking
  Windows-illegal names and shell-expansion-leak telltales across tracked files
  (#2169).

### 💥 Breaking Changes

- **Pre-3.2.x legacy (meta-less) missions are no longer supported for
  coordination operations (#2091 / #2462).** A mission with no resolvable
  mission identity — no `mission_id`/`mid8` in `meta.json`, the pre-3.2.x
  mission-identity model — can no longer drive coordination operations (status
  transitions, `move-task`, review/merge coordination writes). Such a mission
  now **fails loud** with a customer-actionable error instead of silently
  composing a malformed `kitty/mission-<slug>-` ref (the old #2091 defect that
  surfaced only as an opaque `git worktree add` exit-128). This intentionally
  drops the dual-era legacy-bridge fallback: legacy missions are dwindling and
  the dual-support path was a persistent source of split-brain routing bugs.
  **Migration:** run `spec-kitty migrate backfill-identity` to mint a ULID
  `mission_id` (and derive its `mid8`) for any affected mission — audit first
  with `spec-kitty doctor identity`. See
  [mission-id-canonical-identity.md](../migrations/mission-id-canonical-identity.md).

## [3.2.4] - 2026-07-05

Spec Kitty 3.2.4 is a reliability-and-trust release. It fixes a batch of
everyday mission-lifecycle friction points, closes a real gap in the bulk-edit
safety net, makes SaaS sync reporting honest, and — behind the scenes —
reshapes the CI pipeline and decomposes a large internal command module for
faster feedback and lower regression risk going forward.

- **Smoother day-to-day mission lifecycle.** A batch of guard/gate fixes
  removes friction from the implement-review-accept loop: a subtask guard no
  longer misattributes a later work package's unchecked boxes to an earlier
  one, a mission fully implemented by `spec-kitty-orchestrator` can now pass
  `spec-kitty accept` (two false-positive blockers removed), `move-task --to
  for_review` recovers a killed implementer's uncommitted work instead of
  dead-ending, closing a mission now reliably commits its auto-captured
  retrospective, the dashboard no longer hides an in-flight coordination
  mission behind a synthetic "orphan" entry, and a stale `.kittify/derived/`
  view or Op-index cache file can no longer dirty `git status` or block
  `accept`. `map-requirements` also now explains exactly *why* a requirement
  reference is stale instead of looking like data corruption.
- **Mission-state repair no longer risks data loss.** `doctor mission-state
  --fix` (and the automatic repair `spec-kitty upgrade` runs) previously could
  empty a healthy mission's event log of its canonical lifecycle history; it
  now preserves every reader-canonical event class and anchors on the primary
  checkout so repairs actually take effect.
- **Bulk-edit safety net closed.** The `occurrence_map.yaml` gate that blocks
  an incomplete bulk-edit classification at finalize-tasks now covers *both*
  finalize-tasks command surfaces, not just one — closing a path where a
  bulk-edit mission could slip through with an inadmissible occurrence map.
- **Honest SaaS sync reporting.** `sync opt-in` no longer implies remote
  enablement it didn't perform, and `sync status --check --json` reports real
  (or honestly `unknown`) remote/import state instead of staying silent.
- **New `orchestrator-api` capability.** A read-only `resolve-workspace`
  command lets an external orchestrator recover a work package's lane
  workspace without accidentally re-triggering a lifecycle transition.

_Behind the scenes:_ the CI pipeline was reshaped — path-filtered job groups, a
split core-misc shard, and an always-on, de-serialized architectural-adversarial
pole — so most PRs get faster, more targeted feedback without losing any
coverage; and the sprawling `agent tasks` command module was decomposed into
small, independently-tested, behavior-preserving pieces. Neither changes any
user-visible behavior, but both reduce the odds of the next regression and
speed up how fast we catch one.

### 💥 Breaking Changes

- **Deprecated compatibility shim packages removed (mission `unshim-wave2-01KWMCAX`, #2291 / #2290 / #2326 under #1797).** The following re-export shim import paths are **deleted** — code that imported them must switch to the canonical path:
  - `specify_cli.next` → **`runtime.next`** (the canonical `spec-kitty next` runtime/control-loop package; antecedent #612)
  - `specify_cli.glossary` → **`glossary`** (antecedent #613)
  - `specify_cli.charter_lint` → **`specify_cli.charter_runtime.lint`**
  - `specify_cli.charter_freshness` → **`specify_cli.charter_runtime.freshness`**
  - `specify_cli.charter_preflight` → **`specify_cli.charter_runtime.preflight`**

  All in-tree callers were re-pointed to the canonical modules before deletion. The shim registry (`docs/migrations/shim-registry.yaml`, the file read by `spec-kitty doctor shim-registry`) is drained to `shims: []`, and the ownership manifest (`docs/architecture/05_ownership_manifest.yaml`) mirrors the drain for these slices. The user-facing CLI surface is unchanged — `spec-kitty next` and `spec-kitty charter lint/preflight/freshness` behave identically. **No version bump accompanies this entry:** `src/specify_cli/__init__.py` is untouched by the mission (verified against the mission lane history), so the public CLI package version is unaffected; only internal deprecated import paths are removed.

### ♻️ Changed

- **CI health: charter-path doc hotfix + arch-adversarial matrix shard (mission `ci-health-charter-path-and-arch-shard-01KWRTB2`, closes #2397).** Two independent CI-health fixes bundled by operator decision: (a) `docs/guides/contributing.md` still published the retired legacy charter path `memory/charter.md`, redding `fast-tests-docs` on every open PR — replaced with the canonical `.kittify/charter/charter.md`; (b) the `arch-adversarial` job (already de-serialized from the core-misc critical path by the CI-topology-shrink mission above) remained a single unsharded ~14.4-min bottleneck — matrix-sharded into always-on, group-less shards (same pattern as `fast-tests-core-misc`), still running on 100% of source changes with no test dropped or double-counted across shards, dropping the slowest shard below the ~13.6-min sub-target.
- **One canonical `MissionCreated` payload builder (#2270, PR #2398).** Three independent code paths derived `MissionCreated` defaults and had drifted apart: `core/mission_creation.py`, a verbatim-duplicate helper in `sync/emitter.py`, and a third, divergent inline fallback in `status/lifecycle_events.py` (raw slug vs. titleized `friendly_name`, absent vs. now `created_at`, differing None-field wire shape). A new pure CORE module, `core/mission_payload.py::build_mission_created_payload`, is now the single source; both the local lifecycle-event path and the SaaS `EventEmitter` route through it, preserving the CORE↛INTEGRATION boundary (no sync import in core). **Behavioral note:** the local mission log's default `friendly_name` (when not passed explicitly) now titleizes the slug instead of using it raw, matching what the SaaS emitter already produced.
- **CI topology shrink + shard split + always-on architectural pole (mission `ci-topology-shrink-01KWQAVX`, #2378 / #1933 / #2383 under #1931).** The `ci-quality.yml` PR pipeline is reshaped so a single-area PR runs only its focused shard(s) plus the always-on gates, not a full-matrix run:
  - **Group-side shrink (#1933).** The previously-unmapped `src/specify_cli/*` directories are folded into six named composite `dorny/paths-filter` groups (`auth_audit_git`, `lifecycle`, `agent_surface`, `closeout`, `governance`, `platform`), each registered atomically across all five surfaces (filters block, `changes.outputs.*`, the `unmatched` enumeration, and the `JOB_GROUPS` needs-lists). All 32 worklist dirs are now routed. This is the **shrink** interpretation of #1933 (fast, targeted PR CI), not the literal nightly-scheduled full suite (deferred per C-006); the escape hatches (`workflow_dispatch` `run_all`/`run_extended`, the nightly `schedule` cron, the `unmatched` fail-closed catch-all) and the nightly `run_all` over-cover of every worklist dir remain intact — no new blind spot (FR-009).
  - **Shard-side split (#2378).** `fast-tests-core-misc` is subdivided into two disjoint, non-empty matrix shards (ignore-mirror kept consistent), so a core-misc change no longer drags the whole misc bucket.
  - **Architectural un-blind, de-serialized (#2383, NFR-002).** The architectural + adversarial guard job (`arch-adversarial`) runs always-on (`if: always()`, group-less) over 100% of `src/`, and is **de-serialized** from `fast-tests-core-misc` (its `needs` edge is dropped) so it no longer sits on the core-misc critical path — the path collapses from `sum` to `max`, structurally under the ≤13.6-min next-lane ceiling (NFR-001; live `measured_source_run_id` backfilled by the operator from the PR's first post-shrink CI run).
  - **Coverage-consumer integrity by construction (C-005).** New architectural invariants assert coverage-emitting jobs ⊆ `sonarcloud.needs` and critical-path emitters ⊆ `diff-coverage.needs`; in the process the pre-existing production **`mission-loader-coverage` coverage-drop is fixed** — it emits `--cov=src/specify_cli/mission_loader` yet was absent from `sonarcloud.needs`, so its coverage XML was silently dropped from the Sonar gate. The full 8-invariant #2368 substrate suite plus the new NFR-002/003/005 and C-005 relations stay green (NFR-007), and the gate-coverage ratchet baseline is refreshed (`orphan_test_count` 0; `total_tests` rises with the added invariants; `duplicate_test_count` falls with the same-tier consolidation).
- **Root `CHANGELOG.md` is now a symlink to the canonical `docs/changelog/CHANGELOG.md` — the generated mirror is retired.** The two-file model (canonical + frontmatter-stripped root copy kept in sync by `scripts/docs/sync_changelog.py`) made contributors edit the root copy and trip docs-freshness on every external PR. There is now exactly one changelog file; `sync_changelog.py --check` guards the symlink (and `--write` restores it), and release tooling (`extract_changelog.py`, `validate_release.py`) reads the canonical text through the link — both scan `## [...]` headings and tolerate the YAML frontmatter.
- **`orchestrator-api` contract 1.1.0 → 1.2.0: new read-only `resolve-workspace` command (#2337).** `resolve-workspace --mission --wp` returns a work package's lane `workspace_path` / `prompt_path` / `lane_branch` for its **existing** lane, resolved via the canonical naming seams **without** allocating, creating, validating-clean, or transitioning. It's the read-only companion of `start-implementation` (which does a `planned→claimed→in_progress` composite transition): an external orchestrator resuming a WP already past implementation (e.g. one parked in `for_review` after an interrupted run) can obtain its workspace to dispatch a reviewer without mis-transitioning it. Purely additive — existing commands and payloads are unchanged.
- **Internal: the `agent tasks` god-command is decomposed into pure decision cores behind injected ports (mission `tasks-py-degod-01KWF08S`, #2116 under #2173).** Behavior-preserving — the full `agent tasks` CLI contract (all subcommands, flags, exit codes, `--json` envelopes, including the coord skip-exit-0 arm and the refuse-exit-1 arms) is **byte-identical**, frozen by a golden characterization harness. The decision/aggregation logic of the five fat command bodies (`move_task`, `map_requirements`, `status`, `mark_status`, `finalize_tasks`) now lives in pure, independently-tested sibling modules (`tasks_transition_core`, `tasks_mapping_core`, `tasks_status_view`) behind an injected `TasksPorts` seam (`FsReader` coord-READ authority + a two-capability `CoordCommitRouter` coord-WRITE authority); each command body is a ≤150-LOC thin orchestrator. Also folds the pre-3.0 coord read-authority split-brain onto the kind-aware authority (guard-only sites) and drains the resolution-authority census (shrink-only). **No user-facing behavior change.** The Render-seam unification and the whole-file `tasks.py` shim relocation are deferred to a follow-up mission (see `docs/plans/tasks-py-degod-followup-mission-debrief.md`).

### 🐛 Fixed

- **Bulk-edit occurrence-map gate now also enforced on the legacy `agent tasks finalize-tasks` command (#2345, PR #2386).** The PR that gates `occurrence_map.yaml` at finalize-tasks (rather than at first `implement WP##`) only wired the check into `agent mission finalize-tasks`; the older, still-live `agent tasks finalize-tasks` command family could complete finalize-tasks for a bulk-edit mission with a missing, schema-invalid, or inadmissible occurrence map with zero gate friction — found by the pre-merge adversarial squad during landing. `_ft_validate_occurrence_map_ready` mirrors the mission-command gate and runs first in `_ft_validate` (fail-fast, before dependency parsing); the shared error message and JSON payload are de-duplicated into `bulk_edit/gate.py` (`finalize_tasks_gate_error_payload`) so the two command surfaces can't drift apart again.
- **Honest SaaS sync opt-in reporting + typed `remote_sync` status fields (#2264 slice, PR #2396).** `sync opt-in` printed `✓ Enabled SaaS sync for this checkout` even though it only writes local routing flags — implying remote enablement that never happened; the message now states only that a local preference was recorded. `sync status --check --json` gains a typed `remote_sync` block (`remote_project_state` / `materialized_at` / `historical_import_state` / `last_blocker_sample`), honestly `unknown`/null until the import engine (#2262) populates it — `ok` semantics are unchanged, so existing consumers are unaffected and new consumers read remote state from `remote_sync`, not `ok`. Also folded in: `opt-in` now exits non-zero (was a dim exit-0 message) when the SaaS-sync rollout flag is disabled, since opt-in cannot take effect with the flag off.
- **`.kittify/migrations/` and `.kittify/logs/` are now gitignored — completing
  the #2369 derived-views fix (#2384).** Two more generated `.kittify/` subtrees
  of the same class as `.kittify/derived/` were neither registered `IGNORED`
  state surfaces nor added by any backfill, so they showed up untracked and
  failed `spec-kitty accept`'s `git_dirty` check: `.kittify/migrations/`
  (mission-state repair manifests + quarantine backups) and `.kittify/logs/`
  (orchestrator per-WP implementation/review logs). Both are now registered
  `IGNORED` surfaces (fresh `spec-kitty init` gitignores them), and a sibling
  backfill migration (`3.2.4_runtime_dirs_gitignore_backfill`) adds them on
  `spec-kitty upgrade` for already-initialised projects.
- **Upgrade-worktree coherence: one canonical per-checkout auto-commit seam
  (epic #2392 spine — closes #2385, #1873; regression-pins #2105).** The
  `spec-kitty upgrade` commit routine (porcelain-baseline-derived commit-set,
  directory expansion, eligibility filter) is extracted from the CLI into
  `specify_cli.upgrade.autocommit.commit_touched_checkout()` and applied
  symmetrically to **every checkout the run touches** over the runner's single
  worktree enumeration:
  - **#2385** — worktree migration churn was never committed (auto-commit ran on
    the main checkout only), so each coord/lane worktree was left dirty and a
    later `spec-kitty merge` tripped the #1826/NFR-002 guard. The runner now
    captures a per-worktree porcelain baseline before that worktree's writes and
    commits its *new* churn on its own branch; pre-existing uncommitted work
    (e.g. in-flight WP edits) is never swept in, and per-worktree
    `manual_review_required` migrations skip that worktree's commit with a
    warning. Root `.gitignore` churn — exactly what the gitignore-backfill
    migrations write — is now commit-eligible instead of being dropped by the
    root-level-file filter.
  - **#1873** — freshly synthesized worktree metadata is persisted (and
    committed) even when the detected version already equals the target,
    restoring the #1857 self-healing path.
  - **#2105** — already porcelain-derived in this tree; now regression-pinned by
    a test asserting manifest updates and newly-installed skills land in the
    commit-set (guards against regressing to a hardcoded file list).
  - A detached-HEAD checkout skips the auto-commit with a warning instead of
    guessing a ref. `--dry-run` remains a strict no-op per checkout. An
    invariant test asserts that after `upgrade`, no touched checkout carries
    porcelain dirt beyond what pre-existed. **#2367's two mechanisms are
    deliberately NOT routed through this seam** (per the #2392 architect
    design): the implement-claim VCS-lock policy (#2222/C-003 race decision)
    and the merge-rollback snapshot capture set are separate seams sharing the
    same invariant.
- **Guard/gate friction hotfixes (#2346 / #2324, #1834).**
  - **Subtask guard no longer misattributes a later WP's checkboxes (#2346, also closes #2324).** `_check_unchecked_subtasks` entered a WP's section on *any* heading that merely mentioned its id, so a dependent heading like `### WP03 — … (depends: WP01, WP02)` re-entered WP01/WP02's section and harvested WP03's unchecked `- [ ] T0xx` rows as the earlier WP's blockers — spuriously blocking that WP's lane transition. A heading now belongs to the WP named by its **first** `WPxx` token, not any mention.
  - **`grep_absence` negative invariants accept an optional path-scope (#1834).** The acceptance gate ran `grep -r <pattern> .` over the whole repo, so a negative-invariant pattern that a mission's own spec/plan/WP prose mentioned false-positived as `still_present`. `NegativeInvariant` now carries an optional `scope` (whitespace-separated repo-relative search roots); when set, the grep runs only under those paths. Default (unscoped) preserves the whole-repo search, and `scope` is omitted from serialization when unset so existing matrices are untouched.
  - **Documented merge-before-accept for merged-post-state invariants (#1834).** The accept runbook (`docs/guides/accept-and-merge.md`) now records that the accept gate re-runs each negative-invariant `verification_command` **live** (so a hand-set `overall_verdict` does not stick), and that a mission whose invariants assert the *merged* post-state must run `spec-kitty merge` (local) before `spec-kitty accept`.
- **A mission fully implemented by `spec-kitty-orchestrator` can now pass
  `spec-kitty accept` — two mechanical false-positives removed (#2369).** The
  accept gate is the mission-level readiness check (all-done, subtasks,
  clarifications, artifacts, clean tree, paths), but two checks always failed on
  orchestrator-completed missions, forcing operators to bypass accept entirely:
  (a) the strict-metadata check required `shell_pid` on **every** WP, including
  terminal ones — but `shell_pid` is an interactive-`spec-kitty next` artifact the
  orchestrator never stamps; it is now **lane-gated to active lanes exactly like
  `assignee`**, so a done/approved WP no longer needs it (an active WP still does).
  (b) `spec-kitty materialize` writes regenerable views to `.kittify/derived/`,
  which was **not** in the runtime gitignore set (unlike sibling `.kittify/`
  paths), so it dirtied the tree and failed accept's `git_dirty` check — the
  `derived/` views are now a registered `IGNORED` state surface (so fresh
  `spec-kitty init` gitignores it), and a dedicated backfill migration
  (`3.2.4_derived_mission_views_gitignore_backfill`) adds `.kittify/derived/`
  to `.gitignore` on `spec-kitty upgrade` for already-initialised projects
  (the runtime-hygiene migrations previously only knew a hardcoded subset of
  entries). The six meaningful accept checks still gate.
- **Mission-state repair no longer empties `status.events.jsonl` of a healthy
  mission (#2376).** The repair (run by `spec-kitty upgrade` via the TeamSpace
  mission-state gate, and by `doctor mission-state --fix`) quarantined *every*
  `event_type` row except retrospective ones — including the canonical lifecycle
  events (`MissionCreated`, `SpecifyStarted`, `WPCreated`, …) that
  `status/lifecycle_events.py` writes and whose **only** per-mission home is
  `status.events.jsonl`. A completed mission whose log was all lifecycle events
  was emptied to 0 bytes. Repair now **preserves every reader-canonical non-lane
  class** in place — canonical lifecycle events (those in
  `LIFECYCLE_EVENT_TYPES`), retrospective lifecycle rows (the `type` envelope),
  **and the `retrospective.*` (`event_name` envelope) stream written by
  `emit_retrospective_event`** — so the repair predicate matches the durable
  reader (`status/store.py::is_non_lane_event`) exactly. Before this, a mixed log
  containing a `retrospective.completed` row still silently stripped it (the same
  #2376 data-loss class in a different event format). A backstop also refuses to
  write a 0-byte log when the source was non-empty. Decision-Moment
  (`DecisionPoint*`) rows are still pruned: their canonical store is
  `decisions/index.json` / `DM-*.md`, so the copy here is a mirror (unchanged,
  tested behavior). Rows preserved verbatim in the quarantine dir remain
  recoverable.
  - **Repair now anchors on the primary checkout so `SNAPSHOT_DRIFT` actually
    converges and stale coordination worktrees are left untouched (#2320).**
    `doctor mission-state --fix` already re-materializes `status.json` from
    `status.events.jsonl`, but when invoked from inside a worktree the
    invocation root pointed at that worktree, so the materialize landed there:
    the **primary** `status.json` stayed frozen (a re-`--audit` reported the
    same `SNAPSHOT_DRIFT` blocker) and uncommitted repairs were written into a
    possibly-stale coordination worktree. Repair now re-anchors to the canonical
    primary main-checkout via the single worktree-pointer parser
    (`resolve_canonical_root`), so it always targets the primary
    `kitty-specs/<slug>` (drift converges) and never dirties `.worktrees/`. The
    read-only `--audit` path is now anchored on the **same** authority at the
    `run_mission_state` dispatch seam, so audit and fix resolve to the identical
    canonical root from any cwd (a worktree-invoked `--audit` reads the primary,
    matching `--fix`) instead of diverging onto a stale worktree.
- **The Op-index performance cache is now gitignored (#2341).**
  `kitty-ops/ops-index.jsonl` — the machine-local reverse-scan cache that powers
  `spec-kitty invocations list` — was never added to `.gitignore`, so a
  freshly-generated index showed up in `git status` indefinitely (and could be
  accidentally committed). It is now registered as an `IGNORED` `LOCAL_RUNTIME`
  surface in the state contract (`op_invocation_index`), which flows into fresh
  `spec-kitty init` protection automatically. Existing projects are repaired by
  the runtime git-hygiene migration, which also `git rm --cached`s a
  previously-committed index. Durable per-Op audit records
  (`kitty-ops/<op_id>.jsonl`, the new `op_invocation_record` surface) stay
  **tracked** — only the index is ignored.
- **The dashboard no longer orphans a valid in-flight (mid-orchestration)
  mission (#2331).** While a coordination-topology mission had live worktrees
  checked out, `spec-kitty dashboard` registered it under a synthetic
  `orphan:<slug>` key — hiding it from the mission dropdown — because the
  registry read mission identity (`meta.json`) from the coordination worktree,
  which lacks it (`meta.json` is a PRIMARY-partition artifact that lives on the
  primary checkout). Identity now resolves through the kind-aware
  `resolve_planning_read_dir(..., PRIMARY_METADATA)` seam, so a mission mid-run
  shows under its real title and canonical ULID; status/board display still uses
  the coordination surface. `lifecycle.json` now also carries `mission_id`. No
  change for merged/idle missions.

- **`move-task --to for_review` recovers a killed implementer's uncommitted lane
  deliverables instead of dead-ending (#2335).** When an implementer finished its
  files but was interrupted before committing, moving the work package to
  `for_review` failed with a message demanding a manual `git add`/`git commit`
  *inside the lane worktree* — violating the "spec-kitty drives commits" rule. On
  the `for_review` transition, when the auto-commit policy is enabled (the
  default), spec-kitty now commits the finished lane deliverables via the tool
  (`safe_commit` on the lane branch) before the readiness guard runs, so recovery
  completes without touching lane git by hand. Scoped to `for_review` only
  (`approved`/`done` deliverables are already committed); `--force` still
  bypasses, and `--no-auto-commit` defers to the existing guard.

- **`mission close` / `spec-kitty merge` now commit the retrospective they
  auto-generate, instead of leaving the durable event log dirty.** Closing a
  mission that was merged via the legacy plain-git/GitHub path (so merge-time
  teardown never ran) auto-captured `retrospective.yaml` and appended a
  `RetrospectiveCaptured` event to `status.events.jsonl`, but left both
  uncommitted with no notice — violating the atomic-event-log discipline
  (FR-016), since an uncommitted append can be lost. The shared post-merge
  retrospective postcondition now commits the captured record + its event-log
  append via the merge-bookkeeping commit path, so `merge` and `mission close`
  behave identically and the working tree is left clean. If the commit cannot be
  made (detached HEAD / not a worktree), it fails open but reports the
  uncommitted artifacts and the exact command to commit them. `mission close
  --help` no longer describes the non-`--discard` path as a pure "no-op".
- **`map-requirements` now explains *why* a WP `requirement_refs` entry is stale
  instead of looking like data corruption (#2066).** When the stale/invalid-refs
  gate trips, the `--json` payload (and console output) now surface the FR-ID set
  parsed from `spec.md` (`parsed_spec_ids`), classify each offending ref per WP into
  `malformed` (violates the `FR-NNN` / `NFR-NNN` / `C-NNN` format — e.g. a
  letter-suffixed `FR-003a` or an unfilled `<FR-XXX>` placeholder) vs
  `unknown_spec_id` (well-formed but not declared in the spec), and the hint names
  the format rule. A one-character ID-format mismatch is now obvious rather than
  reading like invented/orphaned IDs.

## [3.2.3] - 2026-06-29

Spec Kitty 3.2.3 is a stabilization-and-foundations release. It hardens how the
toolkit behaves under non-trivial branch topologies, smooths the day-to-day
planning and implementation loop, and lands a governed documentation and doctrine
foundation for the upcoming 3.3.x developer-experience focus.

- **Improved branch topology support.** Coordination-topology missions now read
  and write every artifact from the correct surface — planning artifacts
  (`lanes.json`, work-package `tasks/`, `meta.json` identity) on the primary
  branch, status on the coordination worktree — through a single kind-aware
  resolution seam, backed by single-authority resolution gates. The orchestrator,
  the accept gate, merge/lane logic, and `spec-kitty next` no longer stall,
  mis-route, or report phantom early state on coordination missions.
- **Usability upgrades.** A batch of mission-lifecycle tooling-loop friction
  fixes, clearer global-install guidance, and safer everyday operation:
  `SPEC_KITTY_HOME` now isolates *all* local state, `--json` output is safe to
  capture with `2>&1`, worktree discard can no longer delete a sibling mission,
  and a stale tool environment can no longer brick the CLI.
- **Doctrine additions.** The Common Docs consolidation lands a governed
  documentation foundation — a documentation directive, a styleguide, and
  curation / scaffold / write / find tactics wired into the doctrine graph —
  alongside the structural move to a 13-section Divio `docs/` tree: 117
  architecture decision records converted to metadata-in-file records under
  `docs/adr/`, redirect coverage for every moved page, and documentation rulers
  promoted to blocking gates.
- **Doctrine/charter extension improvements.** Charter activation now gates
  org-pack agent availability across dispatch, context, and projection; the
  generated charter interpolates the project documentation policy; and
  `spec-kitty doctor` reports unsanctioned built-in doctrine-graph overrides.

### ✨ Added

- **Retrospectives now have a durable home and survive coordination teardown (#2119).**
  A new `RETROSPECTIVE` primary-artifact kind routes `retrospective.yaml` to the
  tracked `kitty-specs/<slug>/` mission folder for every topology, instead of the
  ephemeral coordination worktree that is deleted on teardown.
- **Governed documentation foundation — the Common Docs doctrine (#2210, #2165).**
  A built-in documentation directive (`DIRECTIVE_042`), a documentation styleguide,
  and `curation` / `scaffold` / `write` / `find` tactics are now wired into the
  doctrine graph, plus three documentation rulers (a `related:` link validator, a
  page-inventory lockfile generator, and an anti-sprawl ratchet), each shipped with
  its own self-test.
- **Common Docs structural move — a 13-section Divio `docs/` tree (#2165, #2054).**
  The split-brain `architecture/` + `docs/` trees are consolidated into one Divio
  layout. 117 unique architecture decision records are converted from the legacy
  table/bold/dash formats into metadata-in-file (MADR) records under
  `docs/adr/<era>/` with byte-invariant decision bodies; redirect stubs preserve
  every moved published URL; page frontmatter is the single source of truth for the
  page-inventory lockfile; and the documentation rulers are promoted to blocking
  gates. The canonical changelog now lives at `docs/changelog/CHANGELOG.md` with
  root `CHANGELOG.md` retained for release tooling.
- **Charter-activation-gated org-pack agents (#2211, #2156, #2166).** Agents
  contributed by an organization doctrine pack are surfaced in dispatch, context,
  and projection only when their charter artifact is active — org overlays are
  applied through the charter, never raw `org_dirs`.
- **Single-Authority Resolution Gates — Phase 1 (#2181, #2173).** New architectural
  gates enforce a single resolution authority for surface placement, preventing
  kind-blind or primary-anchored resolvers from re-introducing split-brain reads.

### 💥 Breaking Changes

- **Removed**: Hidden `--feature` alias hard-removed from 8 user-facing CLI commands
  (`implement`, `merge`, `next`, `research`, `context`, `accept`,
  `lifecycle plan`, `lifecycle tasks`, `mission-type current`).
  Passing `--feature` on any of these commands now yields exit code 2 with
  "No such option: --feature". Use `--mission` instead. (#1060)
- **Fixed**: No-selector guard on all 8 commands now exits with code 2 and a readable
  error message instead of a potential `TypeError` traceback.

### 🐛 Fixed

- **`SPEC_KITTY_HOME` now isolates *all* local Spec Kitty state, not just runtime
  assets (fixes #2171).** Previously the variable governed runtime/Mission assets
  while global sync state — sync `config.toml`, hosted-auth session and refresh
  lock, event queues and the active queue scope, the Lamport clock, the sync
  daemon (state/log/lock), and tracker credentials/cache — still resolved to the
  shared default home (`~/.spec-kitty` on POSIX). An operator who exported
  `SPEC_KITTY_HOME` to target a separate hosted environment would silently read
  and write their everyday dev session. Every global-state surface now derives
  from a single authoritative root (`specify_cli.paths.get_runtime_root`) that
  honors `SPEC_KITTY_HOME` on Linux, macOS, and Windows. When the variable is
  unset the POSIX default (`~/.spec-kitty`) is byte-identical to prior releases;
  on Windows the surfaces that previously leaked to `~/.spec-kitty` are
  normalized onto the platformdirs app-data base. No automatic migration of
  existing `~/.spec-kitty` data is performed — setting the variable selects a
  (possibly fresh) separate root and leaves existing default-home data in place.
- **`--json` output is now safe to capture with `2>&1`.** The CLI correctly puts
  the JSON object on stdout and diagnostics on stderr, but agents commonly invoke
  `spec-kitty … --json 2>&1` and parse the *merged* stream — so any warning/log line
  on stderr (e.g. `CharterCatalogMissWarning`, deprecation notices) corrupted the
  JSON. In `--json` mode the logging bootstrap now runs in a silent mode: every root
  log handler is raised above real records and a `NullHandler` is installed when none
  exist, so Python's `lastResort` WARNING→stderr fallback never fires and
  `captureWarnings`-routed warnings are dropped too. A successful `--json` run emits
  only the JSON object on both stdout and the merged `2>&1` stream; genuine command
  errors are still emitted as JSON on stdout by the commands themselves. (Typer
  *usage* errors for genuinely malformed invocations still print to stderr — a
  separate, pre-dispatch surface.)
- **`spec-kitty accept` no longer false-positives on a mission's `contracts/` path
  convention.** The accept gate's path-convention check (`validate_mission_paths`)
  resolved every mission-declared path against the repo root, so a mission-artifact
  path like software-dev's `deliverables: contracts/` (also an `artifacts.optional`
  entry) was sought at `<repo_root>/contracts/` and reported missing — telling the
  operator to `mkdir -p contracts/` even though `contracts/` existed and was committed
  at `kitty-specs/<mission>/contracts/`. A declared path that is a mission artifact
  (member of `mission.config.artifacts`) is now resolved against the mission's primary
  feature dir via the canonical `planning_read_dir` surface (the same one
  `_missing_artifacts` uses) — no repo-root fallback; build paths (`src/`/`tests/`/
  `docs/`) stay repo-root. A residual of the #1716 / #2113 "no resolution to the repo
  primary for mission artifacts" cluster.
- Retired the unsupported `specify_cli.mission_read_path` backcompat import path (#2048),
  after its last production caller had moved to `specify_cli.missions._read_path_resolver`.
  Supported callers should use `resolve_handle_to_read_path` /
  `resolve_feature_dir_for_mission`; white-box tests that need the 3-argument worker may
  import `_resolve_mission_read_path` directly.
- **Retrospectives are persisted before any coordination teardown (#2119, #1771).**
  The merge and `close --discard` paths now write the retrospective to its durable
  home *before* destroying the coordination worktree (persist-before-destroy, run
  outside the best-effort swallow), via one shared `coordination/teardown.py` seam
  that consolidates the previously-duplicated teardown call sites. The 6 retrospective
  home-resolution sites are unified onto a single primary-anchored authority.
- **Handle-blind PRIMARY reads are canonicalized at the seam entry (#2136).**
  `resolve_planning_read_dir` now canonicalizes a bare `mid8`/`slug` handle on the
  caller side (keeping the `primary_feature_dir_for_mission` primitive blind to avoid
  recursion), so a bare handle no longer resolves to a different directory than a
  pre-resolved `<slug>-<mid8>` one; ambiguous handles raise rather than silently pick.
- **Phantom `spec-kitty agent worktree repair` recovery guidance replaced with the
  real `spec-kitty doctor workspaces --fix` (#1890)**, enforced by a `src/`-scoped,
  count-agnostic grep-guard.
- **Coordination-topology missions read and write every artifact from the correct
  surface (#2160, #2226, #2212, #2194).** Identity reads (`meta.json`), merge/lane
  reads (`lanes.json`, work-package `tasks/`), and the implement / review / merge
  loop now resolve coordination-topology planning artifacts on the primary surface
  through the kind-aware resolution seam, while status stays on the coordination
  worktree (closes #2185, #2186, #2187, #2115, #2140, #2183). Gate-authority
  hardening stops a coordination mission from reading early/empty state and routing
  an agent to the wrong next step (closes #2197, #2198, #2199, #2214).
- **`mission close --discard` now actually tears down coordination-topology
  missions (#2121)** instead of leaving the coordination worktree and branch behind.
- **`mission close --discard` targets worktrees by exact name, not a `<slug>-*`
  prefix (#2129)** — a sibling mission whose slug shared a prefix could previously be
  discarded too (data loss).
- **The accept gate resolves `mid8` / ULID mission handles for its primary-partition
  reads (#2126)** instead of only the fully-qualified `<slug>-<mid8>` form.
- **The generated charter now interpolates the project documentation policy into its
  directive (#2153)** rather than emitting an unresolved placeholder.
- **`spec-kitty doctor` reports unsanctioned built-in doctrine-graph overrides
  (#2082)** and the dead override-policy symbol debt is retired.
- **Tooling robustness:** `uv tool upgrade` is no longer pinned to a stale rc release
  (#2143); `tomli_w` is imported lazily so a stale environment can no longer brick the
  CLI (#2132); `run_tests` detects the host Python interpreter (#2137); and lane
  auto-rebase restores managed-artifact (`lanes.json` / `tasks/` / `WP*`) take-theirs
  classification (#2147).

### ♻️ Changed

- **Extracted a shared atomic-YAML writer in `retrospective/writer.py` (#2125)**,
  de-duplicating the write-temp-then-rename logic across the record-write sites, and
  hoisted the `retrospective.yaml` filename to a single named constant.

- **Orchestrator no longer stalls on a coord/`pr_bound` mission rooted on a writable
  target branch (#2118).** Continuing the split-brain remediation: the `#2090`
  write-surface change routes planning artifacts (`lanes.json` → `LANE_STATE`, WP
  `tasks/` → `WORK_PACKAGE_TASK`) to the primary `target_branch`, but the
  `orchestrator-api` read path still read them off the coordination worktree (which
  carries only status). Under coordination topology the dependency graph came back
  empty, so `list-ready`/`mission-state` saw no schedulable work and the orchestrator
  stalled with every WP stuck at `lane=planned`. The orchestrator's PRIMARY-partition
  reads (`require_lanes_json`, `read_lanes_json`, `build_dependency_graph`, WP
  `tasks/` lookup) now resolve through the kind-aware `resolve_planning_read_dir`
  seam (primary surface for all topologies), mirroring the existing `meta.json`
  treatment in `_resolve_merge_target_branch`; STATUS reads (`read_events` /
  `materialize`) stay on the coordination worktree. Related: #2115 (the
  implement/review/merge read-surface twin), #1716 / #1878 (coordination-topology
  coherence).

- **Mission-lifecycle tooling friction batch (#2224, #2217–#2223).** A set of
  fixes to the planning and implementation loop's tooling surfaces, sliced from the
  Doctrine-Fidelity retrospective follow-ups.
- **Clearer global CLI install guidance (#2231)** for installing `spec-kitty` as a
  global tool.
- **Internal maintainability.** Several god-modules were decomposed into focused
  seams — `cli/commands/doctor.py` (#2059), `agent/mission.py` (#2056),
  `cli/commands/merge.py` (#2057), and `agent/tasks.py` (#2058); the dead-symbol
  architectural gate was hardened with a parser fix, detectors, and a teeth
  self-test (#2158); and the pre-3.0 read-path shims were retired (#1057, #2048).

## [3.2.2] - 2026-06-24

Patch release continuing the post-3.2.0 stabilization, focused on the
**coordination/primary surface-resolution ("split-brain" / file-location)
remediation**. Remediation of these recent file-location issues is **ongoing**, but
progress is significant enough to warrant a new release — we will continue stabilizing
the functionality. This release also adopts a coherent test-flakiness policy, hardens
CI test coverage, and decomposes the `agent/tasks.py` god-module.

### ✨ Added

- **Single, kind- and topology-aware artifact-surface authority (split-brain remediation).**
  Mission planning artifacts and reads/writes now resolve through one canonical surface
  authority instead of drifting between the coordination worktree and the primary checkout:
  - `MissionTopology` SSOT + `routes_through_coordination` route every decision site through
    one classifier; a single read-surface resolver and a single **write-surface** authority
    replace the parallel derivations (#2070, single-authority topology cleanup).
  - Planning + identity artifacts are placed by a kind-aware `MissionArtifactKind` partition —
    planning/identity kinds land on the primary `target_branch` for all topologies; status/
    bookkeeping stays on coordination (#2090 write-surface coherence; ADR for kind- and
    topology-aware placement, #2101).
  - The planning-lifecycle **gate/verify commands** (`setup-plan`, `accept`, `map-requirements`,
    `record-analysis`, `research`, and the `finalize-tasks` commit) now read/commit planning
    artifacts via that seam — closing the case where a coord-topology mission authored on
    primary but verified from coordination (#2113; closes #2107, #2085, #2102). A default-deny
    architectural literal-ban ratchet prevents the class from regrowing.
- **CI test-coverage hardening.** A static gate-coverage checker + orphan ratchet flags tests
  selected by zero CI gates and ratchets the backlog down (#2067, folds #1933); hot
  churn-magnet orphans and `tests/runtime/` are now gated and run on every PR (#2108, #2109, #2111).
- **Maintainability:** the 4633-LOC `agent/tasks.py` god-module is decomposed into five cohesive,
  one-way-import seam modules with a byte-identical CLI surface; the three planning-commit tails
  are centralized through `commit_for_mission` (#2058 / #2114; follow-up body-thinning + FR-007
  consolidation tracked in #2116).
- **Test-flakiness handling policy (#2038):** a suite-wide policy (`docs/guides/testing-flakiness.md`)
  — never retry-to-green; three tiers (budget / correctness / environmental), each with one sanctioned
  response — plus an env-gated, **non-blocking** `quarantine` pytest marker (held out of every normal/
  blocking run unless `SPEC_KITTY_RUN_QUARANTINE=1`), distinct from the mutmut-deselection `flaky` marker.

### 🐛 Fixed

- **Surface-resolution "split-brain" / file-location fixes (coordination vs primary).**
  - Mission-identity reads (mid8 / `mission_id`) are anchored on the **primary** surface, so a
    coord-topology mission no longer builds a malformed coordination branch from an empty mid8 (#2091).
  - `finalize-tasks` aligns on the primary planning surface and the ownership-overlap validator is
    **lane/dependency-aware** — dependency-ordered WPs that legitimately share `owned_files` are no
    longer falsely rejected (#2087, #2088).
  - The read path no longer returns a stale coordination "husk" for a flattened/single-branch mission:
    the stored topology gates the husk short-circuit (#2062); `map-requirements` and `finalize-tasks`
    share one WP-frontmatter read surface (#2064).
  - Write-branch resolvers (`get_feature_target_branch`, `resolve_target_branch`, the `finalize-tasks`
    commit) read `meta.json` on the **primary** surface, so commits no longer silently fall back to the
    repo default `main` under coordination topology.
- **Coord-topology orchestration: WPs reached `done` with nothing committed or integrated.** Three fixes,
  all on the external `orchestrator-api` path for coordination-topology missions:
  - `start-implementation` no longer crashed with `TypeError: transactional status batch only supports one
    feature/mission/wp` — the transactional batch guard now anchors the per-request consistency check on the
    first request's canonicalized dir (matching the non-transactional sibling) instead of the resolved primary
    anchor, which legitimately differs from the coord-worktree request surface.
  - `append-history` now commits the WP prompt file from the coordination worktree (via the canonical
    `resolve_placement_only` target) instead of the primary checkout, fixing a `SAFE_COMMIT_PATH_POLICY`
    refusal that stalled the orchestrate loop.
  - `start-implementation` now allocates the **real lane worktree** (lane branch on the coordination branch,
    with dependency-lane tips merged) instead of returning a bare legacy path, so `merge-mission` has a lane
    branch to integrate and dependent WPs see their dependencies' code. Its response now carries `lane_id`,
    `lane_branch`, and `lane_base_ref`, and `workspace_path` now means that lane worktree. The `for_review`
    transition is gated on a real commit existing beyond the lane base (shared with the native `move-task`
    gate), so "done without a commit" is impossible via the API too.
  - Both `spec-kitty merge` and `orchestrator-api merge-mission` now resolve the target branch from the
    **primary-checkout** meta.json (`merge_target_branch` then `target_branch`) via one shared resolver
    (`core.paths.resolve_merge_target_branch`), instead of the coord-aware read surface — which under
    coordination topology has no meta.json and made the resolver silently fall back to the repo default
    (`main`), merging the mission into the wrong branch (and tripping a downstream `SafeCommitHeadMismatch`).
    Explicit `--target` still wins; the repo default is only used when no mission target is set.
- **Non-deterministic xdist collection in `tests/specify_cli/shims/test_registry.py` (#2038):** the
  frozenset-derived parametrize sets are now `sorted()`, so workers collect an identical order
  (root-cause fix — no retry).

### ⚠️ Contract

- `orchestrator-api` `CONTRACT_VERSION` bumped to **1.1.0**: additive `start-implementation` response fields
  (`lane_id`, `lane_branch`, `lane_base_ref`) and a changed meaning for `workspace_path` (now the lane
  worktree). New error code `LANE_ALLOCATION_FAILED`.

## [3.2.1] - 2026-06-18

Patch release stabilizing the scaffolds around the functionality introduced in 3.2.0. Remediates
blocking issues witnessed after 3.2.0; not every discovered issue is remediated here, and further
patch releases are expected in quick succession.

### 🐛 Fixed

- **Orchestrator coord-read of coord-only missions (#2016):** `orchestrator_api` now resolves a mission that
  exists only as a coordination worktree (no primary `meta.json`) by adopting the canonical mid8 cascade
  (`meta.mid8` → declared `mission_id` → `<slug>-<mid8>` tail) instead of a strict-only reimplementation that
  returned `None`. Legacy non-coord missions keep their primary-read path; genuinely unresolvable handles still
  fail closed.
- **Charter status/sync/preflight coherence (#2009, epic #2007/C2):** `charter status --json` no longer crashes on
  a non-JSON-safe `datetime` in the bundle metadata; the DRG "`built_in_only` + stale `graph.yaml` residue" state
  is now a non-blocking read-time diagnostic instead of a preflight-blocking `invalid`; and a BOM/CRLF hash
  divergence between `sync` and `status`/freshness (which produced a `noop`-despite-stale `charter sync`) is fixed
  by canonicalizing line endings/BOM in the single `charter.hasher.hash_content` seam. Regression tests pin the
  already-landed status side-effect-free and hash-unification fixes.
- **Green the architectural CI gate (#2025):** corrected pytest markers on a subprocess/git test, removed a
  mission-diff-scoped test that did not belong on `main`, and made the architectural ratchet composite keys
  interpreter-stable (Python 3.11 ↔ 3.12 f-string tokenization), re-greening the `tests/architectural/**` shard
  that went red when 3.2.0's gate-un-mask first ran on `main`.

### 🔧 Changed

- **merge.py decomposition, slice 1 (#2027, epic #2026):** extracted the `baseline_merge_commit` record/verify
  cluster from the oversized `cli/commands/merge.py` into a dedicated `specify_cli/merge/baseline.py`,
  behavior-preserving with back-compat re-exports (public + legacy private names).
- **Charter constant single-sourced:** the `_GRAPH_FILENAME` value, previously duplicated across three modules,
  now resolves from one leaf `charter.synthesizer._constants`.

### 🐛 Fixed (security follow-up)

- **SonarCloud + Dependabot:** re-exported the charter package helper named in `__all__`, hardened merge
  bookkeeping projection so status-surface paths cannot resolve outside trusted repo roots, and refreshed locked
  crypto/tooling dependencies to patched releases (`cryptography 49.0.0`, `pip 26.1.2`) so the security gates stay
  clean.

## [3.2.0] - 2026-06-16

### ✨ Added / 🔧 Changed

- Stable 3.2.0 release of the mission-runtime, profile-invocation, tool-surface,
  branch-authority, and coordination-worktree line after the rc45 validation cycle.
  This promotes the accumulated 3.2.0 release-candidate fixes to the default PyPI
  channel.

## [3.2.0rc45] - 2026-06-15

### 🐛 Fixed

- **Agent profile projection plugin production follow-through (PR #1975):** Claude Code plugin bundles now emit
  strict-validator-compatible `skills`/`agents` component paths and a valid empty hooks record; init/upgrade
  auto-repair no longer builds optional disabled plugin bundle artifacts or silently writes Amazon Q user-global
  agent profiles; docs inventory, lockfile, and Roo-deprecation test expectations are refreshed for the CI gates.

## [3.2.0rc44] - 2026-06-14

### ✨ Added

- **ToolSurfaceContract unified registry (mission `tool-surface-contract-01KV2K2P`, PR #1948):**
  `src/specify_cli/tool_surface/` is now the bounded context for configured tool surface policy.
  `spec-kitty doctor tool-surfaces --json` reports stable findings and repair commands across command
  skills, doctrine skills, session/context surfaces, native agent profile projections, and plugin
  bundle surfaces. `doctor skills --json` remains backward-compatible, legacy `agent config` flows
  still work through the new contract, and fresh clones now get actionable generated-surface repair
  plans instead of silent missing `.agents/skills/` drift.
- **Branch-strategy recommendation in `/specify` (issue #765):** `spec-kitty agent mission branch-context`
  now resolves the repository's primary branch and emits a recommendation payload (`primary_branch`,
  `current_is_primary`, `recommended_strategy`, `reason`). The software-dev specify prompt consumes it to
  **proactively** recommend starting on a dedicated feature branch; `mission create --start-branch` now
  creates/switches before any mission artifacts are written when the operator is on the primary branch and
  expects a later PR; staying on the current branch remains an explicit, supported choice (wiring `--pr-bound`
  branch-strategy gate into the operator flow). The recommendation fields are additive and opt-in: callers
  that do not resolve a primary branch receive the byte-identical legacy branch contract.

### 🐛 Fixed

- **Docs: corrected the retired `spec-kitty agent workflow implement` command (issue #1874):** the
  `agent workflow` command group no longer exists (the canonical form is `spec-kitty agent action
  implement` / `… review`). Updated the user-facing `docs/how-to/implement-work-package.md` and the
  `AGENTS.md` testing note. (The same stale command also appears in the PowerShell toolguide and the
  documentation/research per-WP task-prompt templates; those are rendered into the twelve-agent command
  snapshots, whose baselines are already drifted on `main`, so that replacement is left to the
  cli-reference-audit sweep which can regenerate the baselines in one pass.)
- **`spec-kitty upgrade` no longer churns `metadata.yaml` on a no-op (issue #1871):** the "stamp
  `last_upgraded_at` only on material change" rule lived in three divergent idioms, and the migrations-applied
  root path plus `_stamp_schema_version` rewrote `metadata.yaml` (and advanced the timestamp / mtime) even when
  every migration was already recorded. `ProjectMetadata.save()` now does a **masked compare-before-write**
  (skipping the write when only the volatile `last_upgraded_at`/`schema_version` would change) and
  `_stamp_schema_version` skips its re-dump when the rendered bytes already match disk. A genuine
  version/migration/environment change still writes with a fresh timestamp; a no-op upgrade — including across a
  fully-recorded version range, on both the root and worktree paths — is now zero writes. This closes the class
  at the write boundary for upgrade/doctor/regeneration instead of adding a fourth per-path guard.
- **`agent tasks map-requirements --json` no longer crashes on auto-commit (issue #1891, Finding 1):** the
  command stored the `CommitResult` returned by `safe_commit()` directly in the `--json` payload, so on the
  auto-commit success path `json.dumps` failed with *"Object of type CommitResult is not JSON serializable"* —
  the mapping succeeded but agents got an unparseable error instead of the result. `committed` is now a bool
  and the resulting `commit_sha` (or `null`) is exposed alongside it. (Findings 2 and 3 — `agent action
  implement --json` and `setup-plan`/`finalize-tasks` JSON preamble — are tracked separately.)
- **`accept --lenient` now relaxes mission path conventions (issue #1892):** `spec-kitty accept` / `agent
  mission accept` validated a mission's declared `paths` (`src/`, `tests/`, `contracts/` for software-dev)
  unconditionally, so repos with a non-default layout (e.g. a Go service using `internal/` with no top-level
  `tests/`) failed acceptance even with `--lenient` — the only workaround was creating throwaway empty
  directories. Path conventions now block only in strict mode; under `--lenient` an unmet convention is
  surfaced as a non-blocking warning. (A per-project `paths` override remains a possible follow-up.)
- **Name-vs-authority remediation (mission #133; closes #1889, #1860, #1865, #1866, #1867, #1863, #1896, #1898, #1904, #1684, #1906):** (#1884/#1883/#1885 were independently fixed by PR #1910 and are verified-already-fixed here, not re-closed)
  binds the two remaining "a name/string shape is trusted as authority without cross-checking the declared authority"
  seams and ratchets them closed, and clears the live 3.2.0 release-blocker P0s rooted in that class. Topology
  authority seam (`WorktreeTopology` + `classify_worktree_topology` + `is_registered_coord_worktree` in
  `coordination/surface_resolver.py`, wrapping the `git worktree list --porcelain` registry) and branch-identity
  authority seam (`mission_branch_name_required` + structured `BranchIdentityUnresolved` in `lanes/branch_naming.py`,
  dual-era: legacy `\d{3}-` AND mid8 names both resolve) replace the convention predicates at their consumer sites;
  the `(slug.replace('-','')+"00000000")[:8]` mid8-fabrication idiom is eradicated (routed through
  `resolve_transaction_mid8`, fail-closed). **P0s fixed:** `setup-plan`'s committed-spec gate verifies against the
  placement authority's ref not primary HEAD (#1884); the accept gate is idempotent across all modes via
  accept-owned-path exclusion (#1883); unresolvable mission handles raise a structured `MissionNotFoundError`
  (code + next_step, #1911) instead of a silent `mission=unknown` stub (#1885 residual). #1889's coordination-branch-deleted
  case becomes a distinct loud `CoordinationBranchDeleted` (decision-table row R3). An architectural ratchet
  (`test_topology_resolution_boundary.py`) keeps coord predicates, unbackstopped `kitty/mission-{slug}` composes, and
  the fabrication idiom from regrowing outside the blessed seam modules. Doctrine refinements (#1865/#1866/#1867) and
  the DRG extractor styleguide/toolguide `references` walk (#1863) ride along; the authority-path default flips
  `architecture/2.x/adr` → `3.x/adr`. **Cross-lane dependency code propagation (#1684):** `allocate_lane_worktree`
  now merges approved dependency-lane tips (fresh creation + lane re-entry) so a dependent WP in a sibling lane sees
  its approved dependency's code, instead of branching from the bare mission branch.
- **`_branch_exists`/`ref_exists` consolidation (#1904):** the duplicated `git rev-parse --verify` branch/ref
  existence idiom across `coordination/status_transition.py`, `missions/_create.py`, `lanes/worktree_allocator.py`,
  and `lanes/merge.py` is unified into `lanes/_git.py` (env-parameterized so the merge path's environment composes).

### 🧹 Maintenance

- **SonarCloud hygiene on mission #133 surfaces:** raised new-code coverage on the authored seam/allocator/query
  files; reduced cognitive-complexity (extract-method) and duplicate-literal smells across `doctrine.py`,
  `sync/daemon.py`, `sync/owner.py`, `drg/validator.py`, `org_charter.py`, `_read_path_resolver.py`, `core/worktree.py`,
  `agent/workflow.py`, and `upgrade.py` (all behavior-preserving); regenerated stale codex/vibe command-skill
  snapshots to match the advanced templates (PR #1897 finding).

- **Upgrade no longer re-records not-applicable migrations (issue #1872):** a migration whose `detect()`
  is `False` was re-appended as a `skipped` / "Not applicable" `MigrationRecord` on every `spec-kitty upgrade`
  run over the same version range, growing `applied_migrations` without bound and — for worktrees, after
  #1857 — bumping `last_upgraded_at` on no-op runs. `ProjectMetadata.record_migration()` is now idempotent
  (an identical `(id, result)` record is not re-appended) and the worktree upgrade path only marks metadata
  dirty when a new record was actually written, restoring stable `last_upgraded_at` for no-op re-runs. A
  genuine `failed → success` transition still records the new result.
- **Coordination & Merge stabilization (mission 131; closes #1826, #1861 Part 1, residuals of #1833/#1814/#1736/#1735):**
  merge-pipeline ref advances now resync any worktree checked out on the advanced branch (shared
  `git/ref_advance.py` helper with a no-raw-`update-ref` architectural ratchet), refusing loudly — never
  resetting — when the worktree holds uncommitted state; the safe-commit backstop message names the diverged
  worktree/ref/state; `finalize-tasks --validate-only` no longer switches the git checkout; task finalization
  cleans its own primary-checkout residue (operator files untouched); workspace resolution treats non-worktree
  "husk" directories under `.worktrees/` as structured failures instead of silently running git against the
  primary repo, with a new `spec-kitty doctor workspaces [--fix]` check for self-serve recovery — **note:**
  pre-existing husks that previously failed silently now produce explicit errors; run
  `spec-kitty doctor workspaces --fix` once to clean them; retrospective gating reads route through the
  canonical status surface (AC10 ratchet); `upgrade --dry-run` no longer prints a success line implying
  changes were applied; merge-driver hardening (single `_make_merge_env()` authority, narrowed exception
  mask, deterministic mixed-timestamp event-log sort).
- **Protected-branch guard capability honesty (PR #1850 review):** the bool→capability conversion had
  re-opened protected-ref commits from production flows — three sites asserted `GuardCapability.TEST_MODE`
  (legacy workflow commit, baseline-artifact commit, finalize-tasks bootstrap) and six non-merge flows
  borrowed `MERGE_BOOKKEEPING` (move-task, mark-status, map-requirements, decision-log, op-record). All
  now assert `STANDARD`; protected destinations refuse, and refusals degrade gracefully (decision events
  and Op records are preserved on disk, nothing lands on the protected ref). `SPEC_KITTY_TEST_MODE` no
  longer waives the command-level protected-branch prechecks — only the documented operator hatch
  `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` does — and the coordination gate now computes the same
  hatch-aware `ProtectionState` as `safe_commit`, so the two can no longer disagree. Ratcheted by
  `tests/architectural/test_guard_capability_call_sites.py` (capability→flow allowlist; `TEST_MODE` has
  zero `src/` callers) and `tests/git/test_guard_capability_regression.py`.
- **Mission handle canonicalization completes at every CLI write boundary (PR #1850 review):** bare mid8,
  numeric-prefix, and full-ULID handles now resolve to the identical canonical `mission_slug`,
  `mission_id`, status surfaces, and placement (ref and kind) as the full slug — across
  `resolve_status_surface_with_anchor`, `resolve_placement_only`, `MissionStatus.load`,
  `_find_mission_slug` (agent tasks/status/workflow), `agent decision open`, `merge --mission`,
  `spec-kitty next --mission`, `plan --mission`, `mission run/close --mission`,
  `research --mission`, and `context resolve` (persisted `authoritative_ref`). No more
  wrong-but-plausible `kitty-specs/<mid8>/` paths, `legacy-<mid8>` identities, split-brain runtime
  runs or SaaS sync namespaces keyed by the raw handle, or `close --discard` silently leaving lane
  branches/worktrees behind. Pinned by
  `tests/specify_cli/missions/test_handle_equivalence_matrix.py` (78 parity tests).
- **Sync daemon reaper is scoped to its daemon root, not just the interpreter (PR #1850 review):** the
  spawner embeds the resolved daemon state root and spawn-time interpreter identity as inert argv markers;
  the reaper kills only on marker + spawn-signature + interpreter-identity match and conservatively skips
  unmarked or unidentifiable processes. Fixes both the cross-`$HOME` over-kill and the macOS
  framework-Python inertness (where the re-exec rewrites `exe()` and `argv[0]` to the `Python.app` stub).
- **CI `next` filter covers the canonical runtime:** `src/runtime/next/**` and `src/mission_runtime/**`
  now trigger the next suites and count toward diff-coverage critical paths (previously only the
  deprecated `src/specify_cli/next/` shim was mapped, so `integration-tests-next` skipped on
  canonical-runtime changes).
- **`StatusReadPathNotFound` no longer escapes `mission_runtime`'s single-error contract:** the fail-closed
  refusal is translated to `ActionContextError` (error code and message preserved) at all three resolution
  boundaries and handled in the transactional status path; `MissionStatus.load` keeps its established
  `CoordAuthorityUnavailable` shape for every handle form in the fail-closed coordination window.
- **Repo hygiene:** per-machine `.kittify/legacy-warning-shown-*` marker files untracked and gitignored.

## [3.2.0rc43] - 2026-06-11

### ✨ Added / 🔧 Changed

- **Tooling stability & guard coherence (mission 01KTRC04, slice of #1619, closes the #1796 cluster):**
  the safe-commit / protected-branch guard is ONE mechanism — a pure Shared-Kernel policy module
  (`core/commit_guard.evaluate(target, protection_state, capability) -> GuardVerdict`) behind the single
  `git/commit_helpers.safe_commit` facade. The five legacy privilege channels (message-prefix allowlist,
  `allow_protected_branch_in_test_mode`, `allow_completed_op_on_protected_branch`, op-record file-content
  exception, env hatches) are DELETED; protected flows assert an explicit `GuardCapability` at the call
  site (never derived from message/file/env). Operator escape hatch `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`
  retained. Permanently ratcheted by `tests/architectural/test_safe_commit_import_boundary.py` (#1355).
- **Planning placement single authority (#1777/#1784/#1631/#1334):** `mission_runtime.resolve_placement_only`
  is the one commit-destination authority for planning paths; `_resolve_planning_branch` destination
  authority retired. Legit spec/plan commits on protected branches route to the resolved destination with
  ZERO guard relaxation; the finalize-tasks branch catch-22 is gone (idempotent re-runs).
- **safe-commit ergonomics (#1820/#1330):** directory arguments expand to contained dirty files with a
  per-file report; explicit `--to-branch` honored; `SPEC_KITTY_INFER_DESTINATION_REF` retired.
- `record-analysis` verdict derived from the structured `analysis-findings/v1` frontmatter table — prose
  substring counting removed (#1819); severity vocabulary reuses `SEVERITY_ORDER` (no parallel model).
- Carried `StatusSurfaceFragment` threaded through `MissionStatus.load` + `status_transition` (#1821).
- `doctor.py` doctrine profile-health rendering extracted to `_profile_health_render.py` (#1623 slice).
- DRG provenance is a declared typed field on `DRGNode`/`DRGEdge`; the `object.__setattr__` sidecar is
  deleted; `graph.yaml` byte-stable (#1624).
- ADR 2026-06-03-2 addendum: Strangler **Step 7 delivered** (CommitTarget consumed by safe_commit).

## [3.2.0rc42] - 2026-06-11

### 💥 Changed

- **Op record schema v2 (WP01, do-dispatch-open-op-lifecycle)**: the dual-purpose
  `InvocationRecord` model is split into frozen `OpStartedEvent` /
  `OpCompletedEvent` Pydantic v2 models. Completed events now require `outcome`
  and `closed_by` and carry no started-only fields; blank-default records are
  unrepresentable. Readers of `kitty-ops/*.jsonl` warn-and-skip legacy (pre-v2)
  lines, pointing at `spec-kitty upgrade`; `parse_op_event` raises a catchable
  `LegacyRecordError` for them. `spec-kitty invocations list` now shows
  `outcome` and `closed_by` for closed Ops. `artifact_link`, `commit_link`, and
  `glossary_checked` event shapes are unchanged.
- **Breaking — standalone dispatch no longer auto-closes its Op as `done`
  (dispatch-open-op-lifecycle)**: `spec-kitty dispatch` opens the Op and loads
  governance context; the working agent closes it via
  `spec-kitty profile-invocation complete --invocation-id <id>
  --outcome <done|failed|abandoned>` (completed-event schema v2: `outcome`
  required, new `closed_by` field). New `spec-kitty doctor ops --close-stale`
  sweeps stale open Ops closed as `abandoned` (`closed_by: doctor_sweep`).
  Legacy `kitty-ops` records are migrated (rewrite-or-delete) by
  `spec-kitty upgrade`. Claude Code session presence now lists open Ops at
  session start, a new `Stop` hook (`spec-kitty session-stop`) reminds at
  session end, and the doctrine skill pack / standalone command templates
  document the open→work→close contract.

### 🐛 Fixed

- Hardened the v2 Op migration and readers: `spec-kitty invocations list` skips
  dangling `ops-index.jsonl` rows after unsalvageable Op files are deleted, and
  migration idempotency now treats only v2-parseable `mode_of_work` / `closed_by`
  values as already migrated.
- Preserved machine-readable output for standalone dispatch `--json` by
  suppressing post-payload inline glossary notices on JSON paths; rich output
  still shows the notices.
- Updated the rich standalone-dispatch close hint to include the now-required
  `--outcome <done|failed|abandoned>` flag.
- Replaced stale short profile aliases in shipped mission-runtime templates
  (`researcher`, `architect`, `planner`, `implementer`, `reviewer`) with the
  canonical shipped profile IDs, preventing fresh `software-dev` runs from
  blocking on missing invocation profiles.
- `spec-kitty merge` now skips empty post-merge bookkeeping commits after a
  successful lane merge instead of failing the command after the target branch
  has already been updated.

### ✨ Added / 🔧 Changed

- **Execution-context unification (mission 01KTPKST, slice of #1619/#1666):** structurally drained the
  coord-vs-primary split-brain class. One `MissionExecutionContext` (doc-09 fragment/op-composite +
  `CommitTarget`) resolved once and threaded through all command surfaces; status owned by the
  Mission-Management OHS facade. Collapsed the duplicate read-path resolver, the two worktree-pointer
  parsers, and the three sync-daemon orphan-reapers; `materialize_if_stale` now skips during git ops
  (no status clobber on rebase); dashboard reads are write-free (`materialize_snapshot`); sync-daemon
  singleton enforced one-per-host/auth-scope; occurrence-map gained multi-path `moves:` (backward-compatible);
  retrospect record relocated to a tracked home (committable). Adds a dual-CWD + flattened-topology parity
  ratchet (`tests/architectural/test_execution_context_parity.py`).
- Drains #1814, #1816, #1789, #1071, #1062, #1572, #1737, #1357, #1735, #1771, #1736, #1770, #1764, #1815,
  #1622 (partial); follow-ups #1819/#1820/#1821 filed.

## [3.2.0rc41] - 2026-06-08

### ✨ Added

- Introduced canonical `mission_runtime` umbrella package (`src/mission_runtime/`) as the sole
  sanctioned execution-state resolver; `resolve_action_context` is now the single entry point
  for all mission/WP context resolution (epic #1666 slice 2, ADR `2026-06-07-1-execution-state-canonical-surface.md`).
- Added `_branch_trees_equal` predicate in merge command for content-based squash-resume
  idempotency (FR-037); replaces ancestry-based `rev-list` check that failed after squash merges.
- Added `path_is_under_worktrees` guard to `_stage_finalize_artifacts_in_coord_worktree`
  (FR-035); finalize/implement can no longer stage sources already under `.worktrees/`, preventing
  nested-worktree path pollution on coord-topology missions (#1772 Bug 0).
- Added `rebuild_mission_event_log` canonical rebuild entry point for migration paths (#1754).
- New ADR `2026-06-07-1-execution-state-canonical-surface.md` documenting the sole-resolver
  boundary and migration contract.

### 🔧 Changed

- `status/` facade now enforced repo-wide: ~219 deep `specify_cli.status.<sub>` imports
  collapsed to 21 across `src/specify_cli` and `src/runtime` (724 files covered by boundary test).
- `mission_read_path.py` converted to a thin compatibility shim over the canonical
  `specify_cli.missions._read_path_resolver`; duplicate resolver implementation eliminated.
- `mission_runtime.__all__` trimmed to the 4-symbol public contract; historical first-party
  names (`ActionContext`, `ActionName`, `ACTION_NAMES`, `_resolve_mission_slug`) served via
  `__getattr__` without appearing in the public surface.
- `resolve_action_context` top-level imports moved to deferred (inside function bodies),
  breaking the `mission_runtime → dependency_graph → status → uninitialized_hint → dependency_graph`
  circular import; cold `import mission_runtime` now works without prior status initialization.
- `FrontmatterSource` and `resolve_wp_manifests` routed through single ownership ports (#1757).
- Mission-identity snapshot carry-through added to `runtime_bridge.py` (#1663).
- Full-sequence parity ratchet (`test_execution_context_parity.py`) extended to cover
  `next → implement → move-task → review → status` across three execution modes plus a
  negative control (#1672).

### 🐛 Fixed

- Coord-topology merge hardening (#1772): `path_is_under_worktrees` predicate applied at
  staging; `_lane_already_integrated` tree-diff gate (fail-loud on zero-diff squash); in-branch
  status validation; `doctor` check for tracked `.worktrees/` content.
- Cold import of `mission_runtime` no longer raises `ImportError: cannot import name
  'detect_cycles' from partially initialized module` (circular import via status facade).
- `mission_runtime_api.md` contract corrected to match actual `resolve_action_context` signature
  (`action`/`feature` keyword args, not positional `mission`).
- `status_boundary.md` updated to document `workspace/context.py` as a permanent third
  exemption (import-time cycle breaker); contract and test allow-list now in sync.
- Raw `kitty-specs/` path construction eliminated from call sites; all paths go through the
  single resolver (FR-009).
- Closed: #1673, #1664, #1672, #1663, #1757, #1754, #1772.

## [3.2.0rc40] - 2026-06-07

### ✨ Added

- Introduced `Lane.GENESIS` pseudo-state and a canonical `WPState` State-pattern FSM in
  `specify_cli.status.wp_state`, making the FSM the single source of truth for WP lanes,
  edges, and transitions (mission `wp-lane-state-machine-fsm-01KTGZAZ`).
- Added ADR `2026-06-07-1-wp-lane-fsm-genesis-and-finalize-clobber.md` documenting the
  genesis-lane bootstrap and the finalize event-log clobber fix.

### 🔧 Changed

- Routed all WP lane validation and mutation through the single FSM transition primitive;
  callers no longer reconstruct transition authority from derived constants (#1666).

### 🐛 Fixed

- `implement` and `finalize` no longer overwrite the coordination branch's canonical
  status event log (`status.events.jsonl`/`status.json`) with the primary checkout's
  stale copies, preserving seeded lane state on coordination-topology missions (#1589).
- Reconciled the genesis gate and `spec_kitty_events` 6.0.0 expectations for CI.

## [3.2.0rc39] - 2026-06-07

### ✨ Added

- Added `session_presence` package with `SessionPresenceManager`, `InstallResult`,
  `ClaudeCodeWriter`, `MarkdownRulesWriter`, `ClaudeCodeHookRegistrar`, `UpgradeChecker`,
  `SessionPresenceContent`, and supporting writer/hook infrastructure.
- Added `spec-kitty session-start` CLI command (invoked by the Claude Code `SessionStart`
  hook) that emits an orientation block to stdout when run inside a spec-kitty project.
  The command always exits 0 and never blocks a Claude Code session start.
- `spec-kitty init` now calls `SessionPresenceManager.install()` after saving agent
  configuration, writing the orientation block and registering the `SessionStart` hook for
  Claude Code projects automatically.
- Added Phase 1 upgrade migration (`3_3_0_session_presence_claude_code`) that detects
  existing Claude Code projects missing the orientation section or `SessionStart` hook and
  backfills both artefacts on `spec-kitty upgrade`.

### 🐛 Fixed

- Work packages can now declare `scope: codebase-wide` so cross-cutting/refactor
  WPs are exempt from `owned_files` overlap validation, end-to-end through
  `finalize-tasks` (#1753). Two coupled defects were fixed: (1) the strict
  (`extra="forbid"`) `WPMetadata` parser rejected the `scope` key at parse time,
  and (2) `OwnershipManifest.from_frontmatter` hard-coded `scope = None` on its
  `WPMetadata` branch — the exact path `finalize-tasks` uses — silently dropping
  the exemption even when the key parsed. The adapter now propagates `scope`, and
  acceptance tests assert that narrow WPs claiming the same files still fail
  regardless of lane/dependency structure, while a codebase-wide WP is exempt.
  Also removed redundant `@overload` stubs on `from_frontmatter` that tripped
  strict mypy (`overload-cannot-match`).

### 📝 Docs

- AGENTS.md: added "Use Canonical Sources, Never Improvise" guidance and a
  ruff/mypy-clean (no disabled checks) code-style rule.
- `tasks-finalize` doctrine prompt: documented ownership-overlap handling for
  domain/refactor missions (linearize shared surfaces; declare codebase-wide).

## [3.2.0rc38] - 2026-06-06

### ✨ Added

- Added Implementation Concern Map terminology and work-package traceability
  across planning artifacts, generated task prompts, validation checks, docs,
  ADRs, glossary context, and agent snapshots.
- Added tracked Op record storage under `kitty-ops/`, including
  `ops-index.jsonl`, `lifecycle.jsonl`, propagation-error records, best-effort
  `op(...)` auto-commit support, and `spec-kitty doctor ops` orphan reporting.
- Added DocFX publishing polish, all-contributors normalization, and updated
  CLI/reference documentation for the 3.2 release candidate line.

### 🔧 Improved

- Moved Op record storage from its previous gitignored event directory to
  git-tracked `kitty-ops/`, including `ops-index.jsonl`, `lifecycle.jsonl`, and
  propagation errors. Pre-existing records in the retired location are
  abandoned and not migrated.
- Consolidated software-dev template source resolution and rejected stale
  template-root environment overrides so runtime fixtures and package defaults
  cannot silently diverge.
- Tightened release workflow ownership around downstream consumer validation,
  release metadata, path filters, and GitHub Pages publishing support.

### 🐛 Fixed

- **Merge done-marking surface divergence** (`merge.py`, `coordination/surface_resolver.py`):
  After `spec-kitty merge`, WPs that were `approved` would show as `Completed: 0 (80.0%)`
  instead of `Completed: 1 (100%)` when the mission carried a `coordination_branch` in
  `meta.json`. Root cause: `_mark_wp_merged_done` wrote done events to the coordination
  branch surface via `BookkeepingTransaction` (coord-branch-aware), while
  `_assert_merged_wps_reached_done` read back from the primary checkout via
  `resolve_feature_dir_for_mission` (topology-unaware). The two functions resolved to
  different filesytem paths — write never landed where read looked. Fix: introduced
  `coordination.surface_resolver.resolve_status_surface(repo_root, mission_slug)` as the
  single canonical surface resolver; `_assert_merged_wps_reached_done` now calls it instead
  of the topology-unaware resolver, eliminating the divergence. A full merge-path audit
  (inline comment in `merge.py`) confirms no other DIVERGENT sites. Parity ratchet added
  (four regression tests). Class recurrence of issue
  [#1589](https://github.com/Priivacy-ai/spec-kitty/issues/1589) facet 3.
  Closes [#1726](https://github.com/Priivacy-ai/spec-kitty/issues/1726).
  ([#1672](https://github.com/Priivacy-ai/spec-kitty/issues/1672) parity ratchet)

- Completed Op records are now best-effort auto-committed with `op(...)`
  commit messages, and `spec-kitty doctor ops` reports started-only orphan
  records.

- `spec-kitty merge` (without `--push`) no longer checks or requires origin
  sync before performing local lane integration. A local target branch that
  is ahead of, behind, or diverged from its remote tracking branch does not
  block a local-only merge. This resolves issue #1706 where users with
  accumulated orchestration commits on local `main` could not run
  `spec-kitty merge` until they pushed to origin first.

- Push-safety checks now fire only when `--push` is requested. The
  `"behind"` and `"diverged"` states block before local merge mutation with
  remediation guidance, while `"ahead"` remains push-safe.

- `MergeState` now persists `push_requested` for correct resume semantics:
  a resumed merge respects the original invocation's push intent without
  requiring re-specification of `--push`.
- `spec-kitty next` now preserves query startup latency behavior while runtime
  template-source cleanup is in effect.

## [3.2.0rc37] - 2026-06-04

### Added

- Added execution-state domain remediation artifacts, ADRs, and glossary
  context covering ExecutionContext ownership, command targets, effector
  actors, mission/MissionRun boundaries, and status aggregate behavior.
- Added architectural ratchets for execution-context parity, status module
  boundaries, and raw `kitty-specs/<mission>` path construction.

### Changed

- Routed command and runtime path handling through shared execution-context and
  feature-directory resolution so raw mission spec paths consistently resolve
  through the active action context.
- Refreshed Contextive execution glossary and doctrine skill metadata while
  removing the retired `spk-integrate-ci` skill from the bundled doctrine pack.
- Hardened release-candidate CI ownership and release workflow checks around
  path filters, candidate metadata, and downstream compatibility validation.

### Fixed

- Fixed 3.1.10 acceptance and move-task regressions across transactional
  coordination, protected branch bypass handling, and clean-tree acceptance
  fixtures.
- Suppressed SaaS ingress warnings when SaaS sync is disabled.
- Addressed low-risk Sonar cleanup findings and mission-review follow-up
  issues from execution-state domain remediation.

## [3.2.0rc36] - 2026-06-03

### Changed

- Polished 3.2 CLI UX around init next steps, scaffold state, widen guidance,
  and charter preflight output.
- Updated agent harness installation guidance and snapshots for Codex, Kiro,
  Antigravity, and public harness docs.
- Added execution-state/runtime architecture notes covering mission vs.
  MissionRun boundaries and context decomposition.
- Hardened release-candidate CI around charter checks, workflow status
  coordination, and Next runtime task parsing.

## [3.2.0rc35] - 2026-06-02

### Added

- Added agent upgrade prompts and slash-command repair diagnostics so project
  upgrades can detect and repair stale agent command surfaces.
- Added doctrine/profile activation closure work, including canonical kind
  resolution, DRG-backed profile lineage, layered charter listing, template
  discovery, and single-source doctrine health reporting.

### Changed

- Reworked parent-mission acceptance docs and charter boundary documentation
  around status-commit terminology and profile integrity closeout.
- Tightened coordination topology handling across runtime prompts, decision
  logs, dependency gates, move-task transitions, and orchestrator API paths.

### Fixed

- Fixed slash-command install and audit gaps that left generated command files
  stale after upgrades.
- Fixed coordination-topology edge cases that could read stale checkout state,
  miss decision logs, or proceed across topology gaps without failing closed.
- Fixed charter activation and closeout CI instability, including layer-aware
  activation and clean-install latency recalibration.

## [3.2.0rc34] - 2026-06-02

### Changed

- Clarified that live canary and cross-repo end-to-end runs remain required
  release-candidate hygiene under the charter, but are run locally before
  tagging instead of as tag-time PyPI publish workflow blockers.
- Transactional mission status reads now resolve the coordination worktree
  without creating or mutating checkout state, keeping lane views aligned with
  the coordination branch.

### Fixed

- Planning-artifact commits now preserve append-only coordination event logs
  instead of clobbering lane history with stale primary-checkout copies.
- Planning-artifact claim commits now parse git porcelain status structurally,
  fail closed on unrelated structural changes, and skip idempotent
  already-on-coordination content.
- Move-task transitions now derive source and target lanes from transactional
  coordination status so review handoffs do not fail after coordination/feature
  branch desync.
- `.kittify/sync-state.json` is treated as local relay state, while charter
  synthesis provenance can be tracked with the required commit reminder.

## [3.2.0rc33] - 2026-06-01

### Changed

- Tag-time PyPI publishing now stays focused on release-local checks. Live
  canary evidence and the cross-repo end-to-end consumer scenario are no longer
  blocking jobs in `.github/workflows/release.yml`; they remain required local
  release-candidate hygiene before tagging.
- Release metadata now aligns `.kittify/metadata.yaml` with `pyproject.toml`
  for `3.2.0rc33`.

## [3.2.0rc32] - 2026-06-01

### Added

- Charter governance references: `governance_references` declarations in `charter.md`
  now surface supporting public governance docs in `charter context` text/JSON and
  `charter status` diagnostics, with repo-root-scoped path safety.
- Release authority now has a machine-readable shared-package compatibility
  manifest, plus gates that validate CLI ranges, `uv.lock`, SaaS consumer
  contracts, and exact PyPI installability for published artifacts.

### Changed

- Release metadata now aligns `.kittify/metadata.yaml` with `pyproject.toml`
  for `3.2.0rc32`.
- Glossary runtime modules are packaged under canonical top-level `glossary`
  while `specify_cli.glossary` remains a registered compatibility shim.

### Fixed

- `spec-kitty agent decision open --json` now emits exactly one parseable JSON
  object on stdout. The response includes a retry-safe idempotency key so callers
  can rerun the same logical open by mission slug and recover the same
  `decision_id` after wrapper parse/process failures. Idempotent retries repair
  a missing opened event when local decision files were persisted before event
  emission failed, and dry-run output no longer advertises persisted recovery.
- `charter generate --force` now refuses to overwrite symlinked `charter.md` paths,
  preventing silent writes through symlink targets.
- Sync WebSocket connections now send ephemeral `ws_token` credentials in the
  `Authorization: Bearer` upgrade header instead of an ignored `?token=` query
  parameter, restoring authenticated live event delivery.
- Prerelease PyPI publishing no longer waives downstream consumer evidence; the
  release workflow now requires the private consumer suite before any PyPI
  promotion.
- A circular work-package dependency in `tasks.md` no longer leaves the canonical
  status uninitialized with a misleading, looping error (#1589). `finalize-tasks`
  aborts on the cycle before bootstrapping status; `spec-kitty next`/`move-task`
  and lane reads now name the dependency cycle as the root cause instead of an
  infinite "run finalize-tasks to bootstrap the event log" hint.
- `spec-kitty agent status doctor` no longer reports a mission as "Healthy" when
  it has work-package definitions but no canonical status (e.g. after a
  cycle-aborted `finalize-tasks`); it now emits an `uninitialized_status` warning
  naming the cycle when present (#1589).
- CI: the shared-package drift check now skips gracefully when
  `SPEC_KITTY_SAAS_READ_TOKEN` is unavailable (fork PRs) instead of hard-failing;
  the cross-repo drift is still enforced by the push-to-main CI that holds the
  secret.

### Documentation

- Clarified that `.kittify/charter/charter.md` is the Spec Kitty runtime governance
  center, while public docs such as `spec/constitution.md` are supporting context
  rather than alternate authoritative charter paths.
- Added migration guidance for constitution-era `.kittify/memory/constitution.md`
  and `.kittify/constitution/*` layouts.

## [3.2.0rc31] (rolled into rc32)

### Fixed

- Legacy `specify_cli.charter_lint.checks.*` shim imports now preserve canonical
  `specify_cli.charter_runtime.lint.checks.*` module identity and fail loudly if a
  nested alias is missing, preventing duplicate checker module instances.

## [3.2.0rc30] - 2026-05-29

### Added

- **ADR 2026-05-28-1**: Documents CI dependency resolution and test surface consistency —
  five structural gaps identified from CI run 26558837157, chosen remediations, and
  confirmation criteria.
  (`architecture/adrs/2026-05-28-1-ci-dependency-resolution-and-test-surface-consistency.md`)
- Typer-surface smoke test (`tests/agent/test_json_group_typer_surface.py`) that exercises
  the `_JSONErrorGroup` / JSON-envelope contract end-to-end using `typer.Exit` (not
  `click.exceptions.Exit`). Acts as a canary for the typer 0.26+ vendored-click regression.
- `agent` pytest marker for orchestrator-api / agent-facing contract surface tests.

### Changed

- **CI: all test and lint jobs now use `uv sync --frozen --all-extras`** instead of
  `pip install -e .[test]`. The lockfile is the single environment contract for both
  local and CI, eliminating resolver drift between `uv.lock` and `pyproject.toml` bounds.
  Three infrastructure jobs (`uv-lock-check`, `build-wheel`, `clean-install-verification`)
  are unaffected.
- Python version pinned to `3.11.15` in `.python-version` for reproducibility.

### Fixed

- `_JSONErrorGroup` exception handlers now use `_CLICK_USAGE_ERRORS` / `_CLICK_ABORTS`
  tuples that include both `click.exceptions.*` and `typer._click.exceptions.*` variants,
  fixing silent miss of all exceptions raised by typer 0.26+ which vendors click
  internally as `typer._click`.
- Charter-preflight test fixtures (`tests/specify_cli/charter_preflight/_fixtures.py`)
  now use `charter.hasher.hash_content()` instead of raw `hashlib.sha256(bytes)`,
  aligning with the production algorithm and eliminating hash-format divergence.
- E2e conftest synthesises `.kittify/charter/metadata.yaml` after `copytree` using
  the production `charter.hasher.hash_content()` helper, making fixtures self-contained
  and reproducible on clean clones without gitignored runtime state.
- Missing `import click` in `orchestrator_api/commands.py` that caused `NameError` in the
  `except ImportError` fallback when importing the module on typer < 0.26.
- Restored `doctrine` CLI group registration (incorrectly removed when a stale regression
  test was treated as a contract); narrowed the curation-excision guard to `curate`/`promote`
  only; restored `spec-kitty doctrine` sections in `docs/reference/cli-commands.md`.

### Security / Lint

- `TID251` (`flake8-tidy-imports` banned-api) added to ruff: `hashlib.sha256` usage in
  `tests/` must go through `charter.hasher.hash_content()`; `click.exceptions.Exit`,
  `UsageError`, and `Abort` in tests must use `typer.*` equivalents instead.
- `TID251` is now **enforced**, not advisory: a dedicated `[ENFORCED] banned-API lint
  gate (TID251)` step in `ci-quality.yml` runs `ruff check src tests --select TID251`
  without `continue-on-error`, so an unannotated banned call fails the build. The
  previous whole-directory `per-file-ignores` (which silently exempted 10 test trees and
  defeated the "new sha256 still needs a `# noqa`" policy) were removed; every legitimate
  raw `hashlib.sha256` now carries an inline `# noqa: TID251 — <justification>`. A guard
  test (`tests/architectural/test_tid251_enforcement.py`) pins the enforcement so it
  cannot silently regress to advisory. (Closes the adversarial review block on #1395.)

## [3.2.0rc29] - 2026-05-29

3.2.0rc29 rerolls the coordination branch atomic event-log candidate after
PR review and publishes the launch-readiness hardening merged after the yanked
3.2.0rc28 candidate.

### Added

- Added mission coordination branches, sparse coordination worktrees,
  `BookkeepingTransaction`, and `WorkflowMutationPolicy` so mission status
  mutations are staged, audited, and committed away from protected target
  branches.
- Added regression, integration, stress, and architectural coverage for
  coordination worktree creation, safe-commit branch assertions, legacy mission
  fallback, workflow rollback, post-merge indexing, and concurrent status
  emission.
- Added `mission close --discard` and doctor diagnostics for coordination
  workspace health, restart-daemon timing, command/skill manifest drift, and
  upgrade remediation provenance.
- Added external-orchestrator install and compatibility documentation, including
  PyPI installation paths, orchestrator API JSON-error guidance, host-surface
  governance docs, and environment-variable references.

### Changed

- **BREAKING (CLI)**: `spec-kitty safe-commit` now requires
  `--to-branch <ref>`. The temporary `SPEC_KITTY_INFER_DESTINATION_REF=1`
  compatibility path lets the CLI resolve and pass the destination explicitly
  during rollout; the helper itself never infers it.
- **BREAKING (internal)**: `safe_commit()` now requires keyword-only
  `worktree_root`, `destination_ref`, and `paths`, and structurally verifies
  that the worktree HEAD matches the declared destination before staging.
- Removed Spec Kitty internal protected-branch commit exceptions for planning
  artifacts and merged-WP done records. Remaining exceptions are limited to
  documented non-Spec-Kitty upgrade/release workflows.
- Hardened release CI ownership by deduplicating release-readiness checks,
  adding installed-entrypoint smoke coverage, and preserving clean-install
  latency evidence.
- Documented the host-surface parity matrix and Mode of Work governance layer
  so standalone dispatch behavior has a visible README entry point.
- Clarified correlation link and projection policy / read-model policy coverage
  for the 3.2.0 trail-model tranche, including deferred Tier 2 items.

### Fixed

- Migrated remaining production `safe_commit()` call sites to the
  destination-ref-aware API so agent task, mission, merge, upgrade, and
  orchestrator paths no longer crash on the removed legacy signature.
- Fixed protected-branch leakage from `agent action implement` by routing
  planning artifacts and workflow status writes through coordination-owned
  commit paths instead of target-branch bypasses.
- Serialized first-time coordination worktree creation under the feature
  status lock to prevent concurrent emitters from racing on `git worktree add`.
- Fixed idempotent squash-merge retry behavior, finalize-tasks dependency
  source precedence, safe-commit recovery reporting, workflow path mirroring,
  configured command execution on Windows, charter JSON error envelopes, and
  command/skill manifest repair drift.
- Restored upgrade-readiness preference preservation and compatibility hints,
  including uv-tool pytest remediation provenance fallbacks.
- Restored compatibility for older unit-test fakes that do not expose the new
  coordination branch or commit-result fields.

### Deferred

- Continued tracking deferred follow-up work such as
  [#534](https://github.com/Priivacy-ai/spec-kitty/issues/534) outside the
  3.2.0 readiness tranche.

## [3.2.0rc28] - 2026-05-27

3.2.0rc28 fixes acceptance lane ownership and a clean-install dependency gap.

### Changed

- `accept` and orchestrator-api `accept-mission` now keep `approved` and
  `done` distinct: acceptance reports accepted-ready, approved,
  merge-pending, and already-merged WPs without closing approved WPs. Merge
  remains the owner of the `approved -> done` integration transition.
- Software-dev mission guards now treat `approved` and `done` as
  accepted-ready for mission advancement.

### Fixed

- Declared `click` as a direct runtime dependency because CLI modules import it
  directly. This fixes pipx/Windows clean-install import failures.

## [3.2.0rc27] - 2026-05-26

3.2.0rc27 fixes a charter freshness/preflight false positive found in the
post-rc26 mainline checks.

### Fixed

- Charter freshness now uses the same canonical hash semantics as
  `charter sync`, so whitespace-normalized stored hashes do not falsely mark a
  project stale.
- Fresh built-in doctrine seeds now produce the charter synthesis manifest
  expected by preflight, preventing new projects from failing with
  `charter_source stale` before any local charter exists.
- Synced charter bundles no longer become stale from source mtime drift when
  metadata hashes and required bundle files already prove the source is fresh.

## [3.2.0rc26] - 2026-05-26

Rolls up the charter preflight, built-in vocabulary, and CI stabilization
guardrails merged after rc25.

### Breaking changes

- **`shipped` → `built-in` vocabulary rename.** Public CLI JSON surfaces that
  previously emitted `"shipped"` as a doctrine layer label now emit `"built-in"`.
  This aligns user-facing terminology with the on-disk `built-in/` directory
  layout that already existed. Affected commands:
  - `spec-kitty charter status --json`
  - `spec-kitty charter lint --json`
  - `spec-kitty charter preflight --json` (new in this release)
  - `spec-kitty agent profile list --json`
  - `spec-kitty doctrine pack validate --json`

  External tooling that pattern-matched the string `"shipped"` MUST be updated.
  No deprecation period: the rename is mechanical and the architectural test
  `tests/architectural/test_no_shipped_layer_label.py` prevents regression.

  Related: ADR `architecture/3.x/adr/2026-05-24-3-shipped-to-built-in-cutover.md`.

### Changed

- **Deprecated paths:** `specify_cli.charter_lint`, `specify_cli.charter_freshness`,
  and `specify_cli.charter_preflight` now re-export from
  `specify_cli.charter_runtime.{lint,freshness,preflight}` under a shared
  charter-runtime umbrella (LD-5 / FR-014). The old paths emit no
  `DeprecationWarning` yet; they will in the next minor release. External
  importers should update to the new paths during this deprecation window
  (spec C-008). The `charter_runtime.facade` slot is reserved for a future
  charter-facade consolidation.

### Added

- **`spec-kitty charter preflight` command.** Caller-facing preflight contract
  for governance freshness (FR-006, FR-007, FR-008). Returns a structured JSON
  report that `next`, `implement`, and the dashboard consume to decide whether
  to proceed, prompt for `charter synthesize`, or block. See
  `docs/reference/charter-commands.md` and ADR
  `architecture/3.x/adr/2026-05-24-1-charter-freshness-ux-contract.md`.

- Pre-launch and launch-readiness operator docs for hosted SaaS
  sync (#1095). Public docs remain local-first; hosted readiness
  stays opt-in via `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. The new
  `docs/how-to/internal-hosted-readiness.md` covers the dogfooding
  workflow for internal / pre-launch operators, and the new
  `docs/explanation/launch-readiness-future.md` stages the launch-day
  behavior shift behind an explicit "Status: pre-launch" banner.

## [3.2.0rc25] - 2026-05-23

Rolls up the post-rc24 static-analysis and upgrade UX type-boundary fixes.

- Tightens acceptance package imports, compatibility cache typing, and
  readiness upgrade UX helper boundaries after the overnight Sonar sweep.
- Keeps the 3.2.0 stable release candidate line current with `main`
  after `#1293`.

## [3.2.0rc24] - 2026-05-22

Ships the canonical SaaS-bound producer refactor for CLI lifecycle,
sync, decision, glossary, and migration emitters.

- Routes known SaaS-bound CLI payloads through the `spec-kitty-events`
  5.2 canonical models where those contracts exist, while preserving
  transitional legacy wire payloads required by current SaaS consumers.
- Preserves local `artifact_path` metadata on artifact-phase Started
  events and projects those payloads to the strict canonical SaaS wire
  shape before queueing.
- Adds producer conformance coverage, strict lifecycle validation,
  handler-reset isolation, and a documented canonical-producer lint
  baseline for remaining local-only/test producers.

## [3.2.0rc23] - 2026-05-21

Rolls up the autonomous-runtime safety sweep needed before the 3.2.0
stable cut, plus the documentation and CI guardrails merged after rc22.
The candidate focuses on removing operator-required workarounds from
fully autonomous local missions.

- Closes `#1255`: retrospective files written by `retrospect create`
  are now accepted by `retrospect synthesize`, with regression coverage
  for both dry-run and apply flows.
- Closes `#1256`: decisions deferred during planning can be resolved
  cleanly at terminus, and `decision verify` no longer reports resolved
  clarification markers as drift.
- Closes `#1235` and `#1257`: task finalization rejects
  `kitty-specs/` paths in WP `owned_files` with a clear WP/path error,
  while bulk-edit preflight treats WPs that author planning artifacts
  such as `occurrence_map.yaml` as informational.
- Closes `#1236`: lane computation now preserves parallel lanes for
  upstream WPs with disjoint `owned_files`; fan-in WPs remain the
  synchronization point.
- Closes `#1258`: autonomous local mission docs now include the
  focused-PR fallback for `TARGET_BRANCH_NOT_SYNCHRONIZED` when local
  `main` contains orchestration commits.
- Adds the 3.2 documentation refresh, harness/install lifecycle pages,
  docs freshness checks, drift-detector CI, canonical-producer linting,
  acceptance-matrix extension preservation, and charter-context envelope
  repair merged after rc22.

## [3.2.0rc22] - 2026-05-21

Ships the `sync diagnose` canonical-allowlist fix so canary diagnostic
output stops flagging known event types (`TasksCompleted`,
`PlanCompleted`, `GatePassed`, etc.) as unknown. The `sync diagnose`
allowlist is replaced with delegation to
`spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` — the
canonical registry shared with the SaaS strict validator. A
drift-detector regression test asserts the union remains in sync, so
future events releases self-validate. The CLI's outbound emission
gate (`emitter.VALID_EVENT_TYPES`) is intentionally untouched.

- Fixes `spec-kitty sync diagnose` false-positive "unknown event"
  warnings by sourcing recognised types from the canonical events
  registry (`Priivacy-ai/spec-kitty#1222`).
- Adds a drift-detector regression test that fails when the events
  package adds or removes an event type without the registry being
  re-imported.

## [3.2.0rc21] - 2026-05-20

Rolls up the minor issue-queue cleanup selected before the 3.2.0
stable release, plus the post-merge test hardening needed to keep
`main` green after those fixes landed.

- Fixes tasking help assertions to validate Typer option metadata
  instead of Rich-rendered, platform-truncated help text, restoring
  the full main test sweep after the task command cleanup.
- Refreshes the rc20 lockfile metadata so branch and release
  validation agree on the packaged dependency graph.
- Improves task finalization and review-state behavior: rejected
  review overrides are described with the canonical tasking language,
  finalize-tasks dependency prose no longer produces false positives,
  and the main test sweep covers those edge cases.
- Tightens CI and repository hygiene by requiring PR suffixes in the
  protect-main check and tracking research evidence logs.
- Hardens sync, acceptance, retrospective, and dashboard edges found
  during the pre-3.2.0 issue sweep: doctor daemon health checks are
  isolated, acceptance clarification markers match the canonical
  contract, retrospective event emission is materialized, and the
  dashboard exposes the glossary shell.

## [3.2.0rc20] - 2026-05-20

Closes the next dormant mask from epic `#1198`, surfaced by the
rc19 canary now that the `#1202` observability fix is in place.

- Closes `#1203` mask 1: `EventEmitter.emit_wp_created` in
  `src/specify_cli/sync/emitter.py` now constructs the payload
  matching the canonical events 5.1.0 `wp_created_payload` schema.
  Four simultaneous violations are closed in a single change:
  `title` renamed to `wp_title` at the payload boundary,
  `dependencies` renamed to `depends_on`, required `actor`
  parameter added (default `"cli"`) and placed in the payload,
  and `mission_id` removed from the payload (the parameter is
  still accepted for backward compatibility but is no longer
  written to the wire — it isn't in the schema's allowed set).
  The local emitter's per-event-type validator table is updated
  to match the canonical required-fields contract; the
  singleton-level `emit_wp_created` mirror in
  `src/specify_cli/sync/events.py` gains an `actor` parameter and
  passes it through; and the production caller in
  `src/specify_cli/cli/commands/agent/mission.py:2448` passes
  `actor="spec-kitty agent mission finalize-tasks"`.

This was the four-violation drift P4 predicted in the differential
matrix and that the rc19 canary surfaced in full detail thanks to
the per-event-violation observability restored in `#1202`. The
structural follow-up `#1200` (construct payloads via pydantic
models across every `emit_*` site) still pending; this surgical
close prevents the immediate canary blocker while that work
proceeds.

## [3.2.0rc19] - 2026-05-20

Ships the combined `#1199` + `#1202` surgical fix from epic `#1198`:
the immediate Phase 4 canary blocker plus the observability fix that
restores the SaaS's per-event violation diversity to operators.

- Closes `#1199`: `emit_mission_created_local` in
  `src/specify_cli/status/lifecycle_events.py` now accepts
  `mission_type` (required) and `wp_count` (default 0) and places
  both in the payload. The canonical events 5.1.0 schema for
  `mission_created_payload` lists both as required; the deployed
  SaaS jsonschema gate rejects payloads without them with
  `'mission_type' is a required property`. The sibling call site in
  `src/specify_cli/core/mission_creation.py:412` now passes both
  fields, matching the sync-events path at `:468-470`.
- `_validate_lifecycle_payload` widened from `extra_forbidden`-only
  to fail on ALL model violations (extras + missing-required +
  every other `violation_type`). The historical comment block that
  rationalised the narrow scope as matching SaaS tolerance was
  based on the SaaS-side `_should_validate_strict_envelope` hole
  (`Priivacy-ai/spec-kitty-saas#217`) and is no longer true. The
  widened validator catches MissionCreated, WPStatusChanged,
  MissionDossierArtifactIndexed, and every other event type the
  events package recognises, preventing the next analogous drift
  from reaching the offline queue.
- Closes `#1202`: `_parse_error_response` in
  `src/specify_cli/sync/batch.py` now reads `details[*].detail`
  (the key the SaaS actually ships) before falling back to
  `.error` / `.reason`. Without this fix, every per-event line
  in a SaaS rejection collapsed to the outer `error_msg` —
  hiding the SaaS's full per-event violation diversity for the
  entire `rc12 → rc18` drift-chain investigation. With the fix,
  the next failed batch surfaces every distinct violation per
  event, dramatically compressing any remaining mask-peeling.

Sequenced first per epic `#1198`. The structural follow-up
`#1200` (pydantic-construct payloads across all `emit_*` sites +
CI conformance gate) and `#1203` (dormant masks sweep) are next,
with `spec-kitty-saas#217` (close the strict-envelope hole)
sequenced after.

## [3.2.0rc18] - 2026-05-20

Ships the final observed Phase 4 launch-gate payload drift fix after the
rc17 `WPStatusChanged` envelope cleanup.

- Closes `#1190` via `#1191`: `emit_mission_created_local` no longer writes
  `actor` into the `MissionCreated` payload. The canonical
  `spec-kitty-events` 5.1.0 schema declares `additionalProperties: false` for
  `mission_created_payload` and does not allow `actor`, so deployed SaaS batch
  ingest rejected every batch containing one of these events.
- Refactors `_validate_lifecycle_payload` to delegate to
  `spec_kitty_events.conformance.validate_event`, replacing the previous
  hand-maintained lifecycle payload map that missed `MissionCreated` and other
  known event types. The local guard now catches extra-property drift before
  queue fan-out while still tolerating currently accepted missing-field
  violations.
- Adds regression coverage for the cleaned `MissionCreated` payload, the
  conformance guard's extra-field rejection, valid-payload pass-through, and
  graceful fallback for event types not recognised by the installed events
  package.

## [3.2.0rc17] - 2026-05-20

Ships the third Phase 4 launch-gate fix: the actual SaaS-side schema
violation that was hiding behind the parser and canary issues fixed in
rc16.

- Closes `#1188`: `emit_wp_status_changed` in
  `src/specify_cli/sync/emitter.py` no longer passes
  `envelope_fields=` to `_emit`. The payload-only keys (`from_lane`,
  `to_lane`, `actor`, `force`, `reason`, `review_ref`,
  `execution_mode`, `evidence`) were being duplicated at the envelope
  level alongside the canonical envelope keys, and the SaaS schema at
  `/api/v1/events/batch/` rejected every batch containing a
  `WPStatusChanged` event with
  `Additional properties are not allowed ('actor' was unexpected)`
  (HTTP 400). On rc16 this surfaced as scenarios 1, 2, and 4 of the
  deployed-dev identity-boundary canary failing with
  `Synced: 0 Duplicates: 0 Errors: N (unknown: N)`; scenario 3 passed
  because it never emits events through the batch endpoint.
- Extends `envelope.forbidden_fields` in
  `src/specify_cli/core/upstream_contract.json` to include the
  payload-only keys, so the existing
  `test_no_forbidden_fields_in_envelope` contract test now guards
  against regressions.
- Updates the unit tests in `tests/sync/test_events.py` that
  previously asserted the top-level duplicates; the new assertions
  pin the contract that those keys live in `payload` only.

The bug has been on `main` since commit `533e47d2` (2026-04-14,
"Harden SaaS auth and restore build sync emission"). It was masked on
earlier RCs by the audit-predicate gap fixed in rc15
(`#1142`), the parser misclassification fixed in rc16 (`#1182`), and
the canary-command shape fixed in
`spec-kitty-end-to-end-testing#45` (`#1141`). With those three out of
the way, the underlying envelope drift was finally visible end-to-end
and could be fixed.

## [3.2.0rc16] - 2026-05-20

Ships the Phase 4 canary launch-gate unblock: the actual root-cause fix for
`#1141` and the parser/classification fix for `#1182`.

- Closes `#1182`: `_parse_event_results` in `src/specify_cli/sync/batch.py`
  now routes per-event `status="queued"` / `status="pending"` responses to a
  new `pending_count` bucket on `BatchSyncResult` instead of folding them
  into the rejected catch-all with `category=unknown`. `sync now` previously
  reported durably-queued events as `Errors: N (unknown: N)` and exited
  non-zero when the in-process final-sync hit its 5s timeout; pending-only
  drains now exit 0 and surface as `Pending: N` in the summary. Queue
  mutation policy unchanged (pending rows are left for the next daemon tick,
  same disposition as `failed_transient`).
- Closes `#1141` (companion fix in `spec-kitty-end-to-end-testing#45`): the
  canary scenario 4 `move-task --to planned` invocation was omitting
  `--review-feedback-file`, so the CLI hard-rejected the command at the
  argument-validation layer before reaching `emit_status_transition`. The
  rc15 diagnostic breadcrumb in `fire_saas_fanout` could never fire because
  the codepath never reached fan-out. The e2e fix passes a structured
  feedback markdown so the backward emit actually lands. No CLI change is
  required; the events #32 force-required contract and the CLI's
  review-feedback hardening are both intentional and remain in force.
- New unit coverage in `tests/sync/test_batch_error_surfacing.py` pins the
  contract: per-event `queued` / `pending` are not errors, never count
  toward `success_count` (they are durable in-flight, not terminal), but
  do count toward sync activity so the "no progress" guard does not fire
  on a pending-only drain.

## [3.2.0rc15] - 2026-05-19

Ships the Phase 4 canary unblock work landed via PR `#1180`:

- Closes `#1142`: broadens `is_mission_lifecycle_row` in
  `src/specify_cli/audit/shape_registry.py` to accept all four canonical
  aggregate types (`Project`, `Mission`, `WorkPackage`, `MissionDossier`)
  rather than `Mission` alone. Fresh missions no longer trip the
  `FORBIDDEN_KEY` TeamSpace gate when `sync now` runs.
- Closes `#1141`: adds a diagnostic breadcrumb at `fire_saas_fanout` entry in
  `src/specify_cli/status/adapters.py` plus regression coverage that the
  backward `in_review → planned` rollback reaches fanout with the expected
  shape. **Note**: this is a diagnostic landing, not the full root-cause fix
  — the silent replacement that the canary scenario 4 peek catches likely
  lives downstream in `OfflineQueue.queue_event` and is expected to be
  chased on a follow-up RC if it reproduces.
- Bundles the +30 targeted audit / status-emit-sequence tests from `#1180`.

## [3.2.0rc14] - 2026-05-19

Ships the next 3.2 release candidate after the doctrine/charter and
sync-boundary follow-up window:

- Adds the three-layer doctrine and charter DRG work: org-pack loading across
  every configured pack, project/org/built-in precedence diagnostics,
  org-charter interview pre-fill, collision warnings, and the related
  workflow/governance payload hardening.
- Closes the org-pack and charter-scope safety follow-ups by blocking archive
  traversal, unsafe server-provided filenames, symlink/hardlink extraction, and
  scope roots that escape the repository.
- Documents recovery from partially installed command namespace packages for
  `spec-kitty-events`, including the concrete import error signature and
  reinstall path.
- Keeps local workflow test suites honest under the hosted sync preflight:
  e2e workflow tests now opt out of `SPEC_KITTY_ENABLE_SAAS_SYNC` the same way
  integration and tasks suites do, while sync/auth suites retain hosted-sync
  coverage.
- Restores strict mission-step-contract type checking by making ambiguous DRG
  URN matches explicitly typed.
- Carries review and release hygiene fixes for unsafe target-branch merge
  guidance, retrospective workflow wording, doctrine language-bias lint, fresh
  sync Sonar findings, and Windows/main CI health.
- Aligns the release checklist with the main-branch protection workflow:
  release PRs should be squash-merged so the resulting commit retains the PR
  marker that `Protect Main Branch` recognizes.

## [3.2.0rc13] - 2026-05-19

Ships a focused sync-boundary hotfix for pipx-style CLI installs:

- Fixes `#1120`: daemon owner records now canonicalize
  `executable_path` at the `DaemonOwnerRecord` boundary, and foreground
  sync identity uses the same canonicalization helper. Pipx-installed CLIs
  whose `sys.executable` flows through a symlink no longer report a spurious
  `daemon_executable_path` mismatch during `sync status --check` or
  sync-producing command preflight.
- Adds adversarial coverage for owner-record dataclass canonicalization,
  resolve-failure fallback behavior, and the asymmetric one-sided resolve
  failure class that could reintroduce false split-brain detection.

## [3.2.0rc12] - 2026-05-18

Ships the MVP CLI sync-boundary preflight surface required by the Teamspace
auth-boundary hardening launch gate:

- Includes `#1115`: `specify_cli.sync.owner` daemon owner record with
  mismatch / orphan detection, `specify_cli.sync.preflight` read-only
  auth/daemon/queue boundary preflight, and the new identity-boundary rows
  exposed by `sync status --check` / `sync doctor`.
- Closes `#1087` (sync status/doctor expose auth/queue/daemon split brain),
  `#1088` (sync daemon coherent machine-global owner), `#1089` (setup-plan
  evidence enqueued in one sync scope), and `#1090` (scoped queue migration
  does not strand authenticated work).
- Unblocks the deployed-dev sync identity-boundary canary
  (`spec-kitty-end-to-end-testing#42` / `#41`) by providing a packaged CLI
  whose `sync status --check` output is parseable by the canary harness.

## [3.2.0rc11] - 2026-05-17

Closes the planning#16 backward-transition follow-up across the CLI release
surface:

- `spec-kitty backwards --note ...` now preserves the canonical
  `backward rewind:` transition-reason prefix when callers supply a note,
  keeping emitted `WPStatusChanged` events accepted by the shared contract and
  SaaS ingestion.
- The resolved lockfile moves to `spec-kitty-events==5.1.0`, which ships the
  review-rejection replay conformance fixture used to verify forced backward
  transition handling.

## [3.2.0rc10] - 2026-05-17

Rolls forward `3.2.0rc9` (never tagged) and adds the Teamspace MVP
canonical-lifecycle / sync-daemon launch-gate followups:

- **#1067 follow-up.** `core/mission_creation.py:create_mission_core`
  now emits the canonical `SpecifyStarted` event immediately after
  `MissionCreated`, referencing the freshly scaffolded `spec.md`
  artifact path. Previously the constant was defined but never emitted,
  so the canonical lifecycle stream skipped straight from
  `MissionCreated` to `SpecifyCompleted` at setup-plan time — leaving
  TeamSpace replay and the local dashboard blind to in-progress
  specifying. Regression coverage in
  `tests/specify_cli/core/test_mission_creation_specify_started.py`.
- **#1071 follow-up.** `sync status --check` and `sync doctor` now
  surface the daemon PID/port and any orphan `run_sync_daemon`
  processes (via the existing `scan_sync_daemons` helper), so operators
  see cross-checkout daemon divergence without grepping `ps`.
  `_kill_and_cleanup` now waits for the killed PID to actually exit
  before clearing `DAEMON_STATE_FILE` — closing the AC bullet that
  required version-mismatch replacement not leave older daemons live.
  Module docstring updated to be honest about state-file-scoped
  singleton semantics. Regression coverage in
  `tests/cli/commands/test_sync_status_singleton_diagnostics.py` and
  `tests/sync/test_daemon_replace_on_version_mismatch.py`.

Everything previously slated for rc9 (below) is included in rc10.

## [3.2.0rc9] (rolled into rc10)

The `quality-devex-hardening-3-2-01KRJGKH` mission closes six epic-#822
tickets and lands the doctrine tactics, canonical-terminology glossary,
and code-patterns catalog that underpin the 3.2.0 stable release. Push-time
Sonar restoration (#825) is the only remaining operator-action gate.

### Added

- **Stale-lane auto-rebase with conflict classification** (#771). New
  `specify_cli.merge.conflict_classifier` rule pipeline (Validator-flavor;
  5 conflict shapes — pyproject deps union, `__init__.py` import-block
  union, urls.py URL list union, `uv.lock` regenerate, default manual)
  and `specify_cli.lanes.auto_rebase` orchestrator. `spec-kitty merge`
  now attempts `git merge <mission-branch>` inside a stale lane worktree
  before halting, auto-resolves additive-only conflicts via a union-merge
  driver, regenerates `uv.lock` under a global file lock, runs
  `ruff --fix --select I001` on touched `__init__.py` files, and reports
  auto-resolved vs manual lanes. Semantic conflicts still halt with the
  current actionable error. ADR
  `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md`
  documents the fail-safe-default policy.
- **No-upgrade UX notification** (#740). New `core/upgrade_probe.py`
  (PyPI probe + 2 s timeout-bounded channel classification:
  ALREADY_CURRENT / AHEAD_OF_PYPI / NO_UPGRADE_PATH / UNKNOWN) and
  `core/upgrade_notifier.py` (cache-aware emitter). Distinguishes
  "already on the latest supported version" from "build/channel with no
  upgrade path"; never blocks the CLI on network failure; rate-limited
  to once per 24 h with `SPEC_KITTY_NO_UPGRADE_CHECK=1` opt-out; reuses
  `should_check_version()` rather than introducing a parallel gate.
  Cache-warm budget < 100 ms.
- **`secure-regex-catastrophic-backtracking` doctrine tactic** codifying
  the four dangerous regex shapes, the rewrite ladder, and the escape
  hatches. Every regex change now requires a wall-clock regression test
  asserting linear runtime on adversarial input (default budget: < 100 ms
  for 100 000 chars) per FR-008.
- **`chain-of-responsibility-rule-pipeline` doctrine tactic** with three
  flavors (Validator / Transformer / Scorer) and the typed
  `CanonicalRule` Protocol at
  `src/specify_cli/migration/canonicalization.py` as the canonical
  Transformer-flavor implementation.
- **Core code-patterns catalog** at
  `architecture/2.x/04_implementation_mapping/code-patterns.md` listing
  the recurring shapes used across the codebase (Rule-Based Pipeline,
  Append-Only Event Log + Reducer, etc.) with doctrine cross-references.
- **Canonical-terminology glossary entries** for `characterization test`,
  `pipeline-shape`, `rule pipeline`, `catastrophic backtracking`,
  `structural debt`, `deliberate linearity`, and `Sonar quality gate`
  in `.kittify/glossaries/spec_kitty_core.yaml`, each cross-referencing
  the doctrine tactic or architectural document that codifies it
  (FR-013).
- **Targeted symlink-fallback test** for the
  `m_0_8_0_worktree_agents_symlink` migration's `OSError -> shutil.copy2`
  fallback (#629). Runs on every CI pass via `monkeypatch`, not gated
  by `windows_ci`. Covers both happy-fallback and dual-failure arms.
- **Behavior-driven coverage tests** for `cli/commands/charter.py`,
  `cli/commands/charter_bundle.py`, `cli/commands/agent/config.py`,
  `next/_internal_runtime/engine.py`, and `core/file_lock.py`
  (Bucket A/B/C split; `CliRunner` + `tmp_path` real I/O; no
  `mock.patch` on Path methods) per the `function-over-form-testing`
  tactic (#595 workstream A).
- **Wall-clock regression guard** at
  `tests/regressions/test_changelog_regex_redos.py` (20 tests; < 100 ms
  on 100 000-line adversarial input) against future re-introduction of
  the three Sonar-flagged patterns in `release/changelog.py` (pre-fixed
  in PR #592) (#595 workstream B / FR-008).
- **`dev` dependency-group type stubs** (`types-jsonschema`,
  `types-psutil`, `types-PyYAML`, `types-requests`, `types-toml`) in
  `[dependency-groups] dev` so `uv run --with mypy mypy --strict`
  resolves stubs from the default env.

### Changed

- **mypy strict baseline** is now green for `src/specify_cli`,
  `src/charter`, `src/doctrine` per decision moment
  `DM-01KRJHT7QD7XQMY33Y5TDTQ80V` (option A — fix the existing target;
  #971). Includes `doctor.py::_print_overdue_details` annotation fix
  (typed `ShimRegistryReport` under `TYPE_CHECKING`) and
  `_resolve_fail_on` return-type tightening to
  `tuple[Severity | None, bool]`.
- **`_canonicalize_status_row` and `rebuild_state.py`** refactored onto
  the typed `CanonicalRule` Protocol with characterization-test coverage
  preceding the refactor commits (NFR-003 / `tdd-red-green-refactor`).
- **`doctor.py::mission_state`** refactored from cognitive complexity 57
  to a CC 3 thin orchestrator plus per-mode runners
  (`_validate_modes`, `_resolve_fail_on`, `_resolve_audit_root`,
  `_emit_mission_state`, `_run_audit_mode`, `_run_mission_repair`,
  `_run_teamspace_dry_run_mode`), with 17 characterization tests
  guarding behavior across all three dispatch arms (`--audit`, `--fix`,
  `--teamspace-dry-run`) (#595 workstream C).
- **`review.py` split into `cli/commands/review/` package** with sibling
  files for cleaner ownership boundaries.

### Fixed

- **`doctor.py:1092` `MissionRepairResult.findings` real-branch bug**:
  `report` variable was dual-typed as `RepairReport` /
  `RepoAuditReport` across mutually exclusive branches; runtime correct
  but typing broken. Now closes mypy strict on `doctor.py`.
- **Pre-existing YAML scanner error** in
  `.kittify/glossaries/spec_kitty_core.yaml` line 484: the `unsafe bypass`
  definition contained an unquoted backtick-wrapped `bypass_used: true`
  literal that `yaml.safe_load` interpreted as a nested mapping. The
  definition value is now double-quoted; semantic content unchanged.
  File now parses cleanly under `yaml.safe_load` and `ruamel.yaml`.

### Documentation

- **Mission-review report** at
  `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/mission-review.md`
  citing every doctrine tactic applied per WP and linking the
  code-patterns catalog (NFR-006 / FR-012).
- **Post-merge audit report** at
  `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/post-merge-review.md` —
  independent adversarial review confirming PASS WITH NOTES (no code
  defects; release-readiness gated on three operator-action items:
  Sonar hotspot rationale application, NFR-001 smoke execution, and the
  push-time Sonar workflow flip). Documents FR coverage matrix, drift
  findings, silent-failure scan, and security notes. All four
  post-merge stale-assertion findings classified as false alarms.
- **NFR-001 release-stability smoke recipe** at
  `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/nfr-001-smoke-recipe.md`
  for operator execution post-merge.
- **SonarCloud hotspot rationales** at
  `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-hotspot-rationales.md`
  documenting the 4 encrypt-data hotspots for operator application in the
  Sonar UI before push-time CI restoration (#825).
- **ADR `2026-05-14-1-stale-lane-auto-rebase-classifier-policy`** for #771.

### Deferred

- **Push-time SonarCloud restoration** (#825 / FR-004): gated on the
  operator applying the four hotspot rationales in the Sonar UI and the
  Sonar quality gate flipping to `OK` (at audit time: ERROR —
  `new_coverage` 58.9% vs threshold 80%; `new_security_hotspots_reviewed`
  0% vs threshold 100%). The
  `.github/workflows/ci-quality.yml::sonarcloud` conditional remains on
  `schedule || workflow_dispatch` until gate is OK. See
  `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-pre-flip-verification.txt`.

### Removed

## [3.2.0rc8] - 2026-05-14

3.2.0rc8 rolls up the post-rc7 TeamSpace launch fixes and compatibility
cleanup needed before the final 3.2.0 cut. It includes defensive sync batching
for real edge-proxy limits, the Mission Dossier event-envelope migration for
`spec-kitty-events>=5.0.0`, and the small compatibility/quality fixes that
landed after rc7.

### Changed

- Reduced the CLI's default sync batch decompressed byte budget to 256 KiB and
  added a 512 KiB hard ceiling for over-generous server-advertised limits, so
  large TeamSpace queue drains split into safe requests instead of relying on
  HTTP 413 retry shrinkage.
- Migrated all four Mission Dossier event emitters to the namespaced envelope
  required by `spec-kitty-events>=5.0.0`, including `namespace`,
  `artifact_id`/`expected_identity`, content refs, and schema-compatible
  diagnostics.
- Preserved legacy queued Mission Dossier events by migrating flat queued
  payloads on drain when namespace data is available, and kept queue coalescing
  scoped correctly across both legacy and namespaced payload shapes.

### Fixed

- Restored agent profile list compatibility after the rc7 candidate.
- Reduced SonarCloud noise in path helper and charter synthesizer code without
  changing runtime behavior.
- Fixed the deployed-dev TeamSpace sync canary failure where a 1200-event
  backlog could cascade into 1000 HTTP 413 failures.
- Fixed SaaS ingestion rejection of CLI-emitted Mission Dossier artifact events
  caused by the old flat payload shape being rejected with
  `Additional properties are not allowed`.

## [3.2.0rc7] - 2026-05-12

3.2.0rc7 lands the `review-merge-gate-hardening-3-2-x-01KRC57C` mission
covering the remaining 3.2.x P1 release blockers plus a narrowed slice of the
charter encoding chokepoint, with post-merge remediation, SonarCloud
new-code gate cleanup, and CI portability fixes folded in.

### Added

- New canonical `KittyInternalConsistencyError` base under
  `src/kernel/errors.py`, with `CharterEncodingError` now inheriting from it
  so any UI/CLI/TUI surface can render structured remediation uniformly.
- Reusable SonarCloud branch-review snippet at
  `work/snippets/sonarcloud_branch_review.sh` (qualitygates/project_status +
  measures/component_tree + issues/search via REST API).
- Architectural decision record
  `architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md`
  deferring still-open `#391` sub-tickets (`#612` / `#613` / `#614`) from
  3.2.x scope, on top of the shared-package-boundary cutover precedent.

### Changed

- Refactored `_bake_mission_number_into_mission_branch` in
  `src/specify_cli/cli/commands/merge.py` from cognitive complexity 22 down
  to a flat coordinator backed by six named predicate / effect helpers, with
  no behavior change.
- Narrowed broad `except` clauses in `src/charter/_io.py`,
  `src/charter/compiler.py`, and `src/charter/interview.py` so charter
  encoding errors propagate to the canonical handler instead of being
  swallowed.
- Wired `assert_pytest_available()` into the production review preflight in
  `src/specify_cli/cli/commands/review/__init__.py`.

### Fixed

- Pre-merge mission-review remediation of findings `D1`, `D2`, `D3`, `S1`,
  and `S2` against the canonical issue matrix at
  `kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/issue-matrix.md`.
- Repaired 18 pre-existing test failures by extracting a shared
  `setup_mocked_env()` context manager to `tests/mocked_env.py` and rewiring
  the affected sites onto it.
- CI portability: `tests/integration/test_pytest_venv_concurrency.py` now
  invokes pytest through `sys.executable` instead of relying on a bare `uv`
  on `$PATH`, which is not guaranteed inside slow-test CI shards.
- Cleared the SonarCloud new-code coverage gate for the branch by adding 26
  focused coverage tests under `tests/kernel/`, `tests/charter/`, and
  `tests/core/test_paths_coverage_supplements.py`.
- Repaired dead links to the deleted `kitty-specs/_drafts/` directory in the
  3.2.x deferral ADR and the mission spec after the pre-PR cleanup pass.

## [3.2.0rc6] - 2026-05-11

3.2.0rc6 includes the post-rc5 TeamSpace migration enforcement and dry-run
compatibility fixes needed before publishing the next TeamSpace-ready CLI
candidate.

### Changed

- Surface pending TeamSpace mission-state migration during `spec-kitty upgrade`
  and require a clean migration before hosted TeamSpace connection flows.
- Allow the release compatibility gate to prove SaaS-supported dependency
  versions when the candidate CLI declares a compatible range instead of an
  exact pin.

### Fixed

- Render user-friendly TeamSpace migration gate failures when mission-state
  repair raises unexpected payload or filesystem errors.
- Preserve SaaS-disabled sync opt-in behavior while still enforcing
  mission-state readiness for hosted sync paths.
- Synthesize historical approval evidence during TeamSpace dry-run conversion
  so approved/done mission-state rows can validate against the canonical event
  contract.

## [3.2.0rc5] - 2026-05-11

3.2.0rc5 closes the remaining CLI-side TeamSpace migration readiness gaps found
while rechecking the historical mission-state migration parent issue.

### Changed

- Documented the deterministic historical mission-state repair contract and
  safe release sequencing used before any repository-wide repair is required.

### Fixed

- Block TeamSpace dry-run/import envelope synthesis when audit findings still
  contain TeamSpace blockers, so legacy mission-state rows cannot bypass the
  readiness audit.
- Reject historical mission-state sync batches with legacy status fields before
  network submission, preserving the local queue and returning remediation.

## [3.2.0rc4] - 2026-05-11

3.2.0rc4 tightens the TeamSpace release candidate against the published
`spec-kitty-events` 5.0.0 contract and includes the latest migration rehearsal
diagnostics.

### Changed

- Tightened the CLI `spec-kitty-events` dependency to `>=5.0.0,<6.0.0` now
  that the 5.0.0 TeamSpace canonical event contract is published to PyPI
  (#978).
- Included the TeamSpace dry-run row mapping diagnostics merged after rc3 so
  migration rehearsals can trace source rows to synthesized TeamSpace envelopes
  (#1014).

## [3.2.0rc3] - 2026-05-06

3.2.0rc3 fixes a TeamSpace dry-run compatibility gap found during the
historical mission-state migration rehearsal.

### Fixed

- Synthesized minimal repo evidence for historical done rows that only
  preserved review evidence, allowing `doctor mission-state --teamspace-dry-run`
  to validate those rows against the `spec-kitty-events` 5.0.0 payload contract
  (#997).

## [3.2.0rc2] - 2026-05-05

3.2.0rc2 adds the TeamSpace mission-state repair and validation surface needed
before public TeamSpace import. The repair command is available now; the
TeamSpace dry-run path requires `spec-kitty-events>=5.0.0` once that contract
package is published.

### Added

- Added deterministic `doctor mission-state --fix` repair for historical
  `kitty-specs/` state, including Git safety checks, migration manifests, legacy
  key cleanup, typed-row quarantine, lane normalization, and production
  `status.json` rematerialization (#980).
- Added `doctor mission-state --teamspace-dry-run` to synthesize canonical
  TeamSpace envelopes in memory and validate them with the 5.0.0 event contract
  when available (#980).
- Documented the distributed Git repair workflow for coordinated repository
  migration before TeamSpace launch (#980).
- Added `doctor mission-state --include-fixtures` and the packaged
  mission-state survey fixture pack used by the TeamSpace readiness audit
  contract (#920, #922, #929).
- Added an opt-in `TeamSpace Mission-State Readiness` GitHub Actions workflow
  that runs `doctor mission-state --audit --fail-on teamspace-blocker` and
  uploads the JSON audit artifact (#920, #934).

### Changed

- Aligned CLI sync emission for `WPStatusChanged` and `MissionClosed` with the
  canonical TeamSpace event payload shape while keeping launch dry-run gated on
  the published events contract (#980).
- `doctor mission-state --audit` JSON reports now expose TeamSpace blocker
  counts, and `--fail-on teamspace-blocker` gates import/sync readiness
  without requiring network access (#920, #934).

## [3.2.0rc1] - 2026-05-05

3.2.0rc1 is the first release candidate for the 3.2.0 line. It rolls up the
workflow stabilization work from the alpha series and the final release
confidence missions.

### Fixed

- Hardened the mission status, review, and merge surfaces that block reliable
  implement-review-retrospect loops, including stale review verdict handling,
  finalized-board routing, canonical review feedback pointers, and first-class
  retrospective synthesis paths.
- Fixed task-board progress semantics so done-only counts are no longer paired
  with unlabeled weighted readiness percentages; JSON status output now exposes
  explicit progress semantics and weighted readiness fields (#966).
- Added an installed dependency drift guard for shared packages so release and
  review evidence fail when the active environment disagrees with `uv.lock` for
  `spec-kitty-events` or `spec-kitty-tracker` (#848).
- Addressed final mission-review regressions around machine-facing contract
  output, sync-control side effects, and the charter golden-path E2E assertion.

### Release Validation

- Closed the stale ruff blocker after `uv run ruff check src tests` passed on
  current `main` (#869).
- Re-ran final local release gates from fresh `origin/main`: dependency sync,
  lock validation, installed shared-package drift guard, ruff, and the
  contract/architectural/release pytest batch all passed.
- GitHub Actions on the release candidate base commit passed `CI Quality`,
  `ci-windows`, and `Protect Main Branch`.

### Known Limitations

- The broad strict mypy gate remains tracked for follow-up in #971 and is not a
  blocking gate for this release candidate.
- Hosted sync drain reliability has a known SaaS-sync limitation tracked in
  #889; do not treat this release candidate as proof of full hosted drain
  reliability until that issue is fixed.

## [3.2.0a10] - 2026-05-04

3.2.0a10 is a prerelease that stabilizes the implement-review-retrospect
control loop after the 3.2.0 release-blocker triage.

### Fixed

- Rejection transitions from `in_review` now derive or require structured
  rejected review results before mutating task state, closing the gap where
  reviewer feedback could fail without a durable review result (#960).
- Review feedback pointers are canonicalized to `review-cycle://...` URIs and
  legacy `feedback://` references are normalized or resolved with a warning,
  preserving focused fix-mode context across rejection cycles (#962).
- Written `review-cycle-N.md` artifacts now include required YAML frontmatter
  before they can be referenced, and invalid review artifacts fail closed
  instead of leaving dangling status pointers (#963).
- `spec-kitty next` now treats finalized task boards and work-package lane
  state as authoritative in query mode without bypassing mutating runtime
  composition or retrospective terminus handling (#961).
- Completed missions now have a usable `agent retrospect synthesize` path when
  `retrospective.yaml` is missing, with JSON output that distinguishes created,
  synthesized, insufficient-artifacts, and mission-not-found outcomes (#965).

### Internal

- Added targeted regression coverage for the shared review-cycle domain,
  rejection transitions, canonical feedback resolution, finalized routing,
  retrospective synthesis, and the focused implement-review-retrospect smoke
  path.

## [3.2.0a9] - 2026-05-03

3.2.0a9 is a prerelease that adds mission-state audit diagnostics and hardens
the 3.2.0 workflow reliability path for implementation, review, merge, and
release-blocker triage.

### Added

- Added a read-only mission-state audit engine for inspecting mission status,
  work package state, review artifacts, and lifecycle consistency without
  mutating project state.
- Added reliability fixture coverage for branch, mission, review prompt, and
  sync workflows used by the 3.2.0 release-blocker tranche.

### Fixed

- Implementation start is now idempotent across planned, claimed, and
  in-progress task states, preventing duplicate or inconsistent lifecycle
  transitions (#946).
- Merge preflight now refreshes the target branch tracking ref before enforcing
  target-branch synchronization, so stale local `origin/main` state cannot
  allow an unsafe merge (#959).
- Merge, review prompt, worktree ownership, sync finalization, and review
  artifact consistency checks now have tighter diagnostics and regression
  coverage for the 3.2.0 workflow reliability tranche (#959).
- Command JSON output now avoids leaking non-serializable status event mocks in
  covered move-task paths, preserving strict JSON command contracts.

### Internal

- Recorded the atomic work-package start lifecycle ADR and expanded regression
  coverage around status persistence, bootstrap seeding, merge preflight, and
  test sync isolation.
- Restored CI release confidence by covering the previously failing
  `fast-tests-core-misc`, `integration-tests-merge`, `integration-tests-cli`,
  and `diff-coverage` gates.

## [3.2.0a8] - 2026-05-01

3.2.0a8 is a prerelease that hardens direct SaaS sync ingress around the
Private Teamspace boundary. CLI sync side effects now resolve a canonical
Private Teamspace target, rehydrate session membership once when needed, and
skip direct ingress with a diagnostic instead of falling back to a shared team.

### Fixed

- Direct sync ingress for `/api/v1/events/batch/` and `/api/v1/ws-token` now
  uses a strict Private Teamspace resolver and refuses shared-team fallbacks
  from stale `default_team_id`, `teams[0]`, or websocket state (#943).
- Auth refresh and session rehydration now update team membership from
  `/api/v1/me`, recomputing `default_team_id` from the refreshed private team
  list instead of preserving stale shared defaults (#943).
- `--json` command stdout remains parseable when SaaS sync cannot connect or
  cannot resolve a Private Teamspace; sync diagnostics route to stderr or
  structured logs rather than contaminating stdout (#943).

### Internal

- Added strict resolver, sync call-site, websocket, offline queue, and
  strict-JSON regression coverage for the Private Teamspace ingress boundary.
- Added mission review evidence for
  `private-teamspace-ingress-safeguards-01KQH03Y`.

## [3.2.0a7] - 2026-05-01

3.2.0a7 is a focused prerelease that bounds WebSocket sync startup and
shutdown behavior. Short-lived agent commands now fail over to batch sync
instead of hanging indefinitely when a local sync socket accepts the
connection but never emits the initial snapshot.

### Fixed

- WebSocket sync startup now has bounded open, initial snapshot, and close
  deadlines so `spec-kitty agent mission setup-plan` and other short-lived
  commands degrade to batch sync instead of blocking forever on a stalled
  sync socket (#936).

### Internal

- Added regression coverage for a WebSocket connection that never sends the
  initial snapshot and for shutdown paths where the close handshake stalls.
- Aligned existing Bandit suppressions in touched sync/readiness callsites so
  local and CI security scans recognize the intended safe dynamic SQL and
  localhost URL patterns.

## [3.2.0a6] - 2026-04-30

3.2.0a6 is a prerelease hardening sweep that restores the documented
fresh-project golden path (`init` → charter `setup`/`generate`/
`synthesize` → `next`), locks in strict JSON for covered `--json` commands
under any SaaS state, fixes agent identity parsing and review-cycle
accounting, adds paired profile-invocation lifecycle observability for
`spec-kitty next`, and tightens merge/review/status recovery paths. The
release introduces the new top-level `spec-kitty review` mission-review
command and no new top-level runtime dependencies.

### Fixed

- `charter bundle validate --json` now fail-closes on incomplete Charter
  synthesis state while preserving strict JSON stdout. Sidecar-only bundles,
  manifest-only bundles, incompatible bundle versions, missing provenance
  sidecars, dangling sidecar references, and synthesis manifest integrity
  failures all produce parseable failure envelopes with actionable
  `synthesis_state` details (#914, closes the final Phase 7 release gap for
  #469/#515).
- Stamp `schema_version` and a `schema_capabilities` block in
  `.kittify/metadata.yaml` on `spec-kitty init` so a fresh project no
  longer requires hand-edits before subsequent CLI commands; existing
  schema fields are preserved (additive, idempotent) (#840, WP01).
- Strict JSON envelope contract for covered `--json` commands: stdout is
  parseable by `json.loads` regardless of SaaS sync state (disabled,
  unauthorized, network-failed, success); sync/auth diagnostics route to
  stderr or nest inside the envelope (#842, WP02).
- `WPMetadata.resolved_agent()` parses 4-segment colon-delimited agent
  strings (`tool:model:profile:role`) and preserves every supplied field
  through implement and review prompt rendering, with deterministic
  fallback for partial strings (#833, WP03).
- Review-cycle counter advances exactly once per genuine reviewer
  rejection; reclaim/regenerate of an `implement` prompt no longer
  inflates the counter or writes a spurious `review-cycle-N.md`
  artifact (#676, WP04).
- `spec-kitty next` writes paired `started`/`completed` profile-invocation
  lifecycle records keyed to the canonical mission step + action it
  issued, observable via `spec-kitty doctor invocation-pairing` (#843,
  WP05).
- `charter generate` auto-tracks the produced `charter.md` and ensures
  the required `.gitignore` entries exist; `charter bundle validate`
  succeeds immediately afterwards with no operator `git add` between
  the two commands. Outside a git working tree, `generate` fails fast
  with an actionable error that names `git init` as the remediation
  (#841, WP06).
- `charter synthesize` succeeds on a fresh project via the public CLI
  with no hand-seeded `.kittify/doctrine/`; the bounded fresh-project
  path materialises a minimal doctrine tree (`PROVENANCE.md`) so the
  shipped doctrine layer can supply content (#839, WP06).
- `spec-kitty merge --abort` now clears the global merge lock, removes
  legacy merge-state files, aborts an in-progress Git merge when present,
  and remains idempotent when no merge is active (#903).
- Approved/done work packages with stale `verdict: rejected` review
  artifacts are now surfaced across status views, including
  `spec-kitty agent tasks status` and `show_kanban_status()`. Review
  artifact lookup follows the real `tasks/<WP-slug>/review-cycle-N.md`
  layout, and `in_review` work packages now warn when reviewer movement
  stalls beyond the configured threshold (#904, #909).
- Review lane-guard failures now name the planning branch and include a
  concrete `git show <planning-branch>:<path>` command for the first
  contaminated path, instead of a placeholder path (#905).
- Work-package review definition-of-done coverage now includes real error
  path and artifact-deletion regressions, not only happy-path review
  behavior (#906).
- Broad `except Exception` / BLE001 suppressions in touched runtime paths
  were audited and now carry inline justification where fail-open behavior
  is intentional (#907).
- `spec-kitty review <mission>` is now a first-class mission-review CLI
  command with structured status/exit behavior for post-merge mission
  fidelity checks (#908).

### Internal

- Consolidated golden-path E2E (`tests/e2e/test_charter_epic_golden_path.py`)
  rewritten to drive the fresh-project chain through the public CLI
  only — no hand seeding of `.kittify/doctrine/`, no edits to
  `.kittify/metadata.yaml`, no manual `git add` of charter artifacts
  between `generate` and `bundle validate`. Runs in well under the
  120-second NFR-007 budget. Also exercises strict JSON parsability of
  `mission branch-context --json` (WP02 spot-check) and the `started`
  lifecycle record (WP05 spot-check) (WP07).
- Governance setup docs (`docs/how-to/setup-governance.md`) note that
  `charter generate` now auto-tracks `charter.md`, removing any
  expectation that operators run `git add` between `generate` and
  `bundle validate` (WP07).
- Added regression coverage for merge abort cleanup, stale rejected review
  artifacts, stalled in-review work packages, lane-guard remediation text,
  mission-review command behavior, review DoD deletion/error cases, and
  agent-shard coverage for status warning paths (#903-#909).

### Tranche-2 acceptance pass (SC-001..SC-008)

- **SC-001 (Fresh-path completion)** — `tests/e2e/test_charter_epic_golden_path.py::test_charter_epic_golden_path` walks `init → charter interview → generate → bundle validate → synthesize → mission create → setup-plan → finalize-tasks → next` against a fresh project with no `.kittify/` hand-edits and no `git add` of charter artifacts. Passes locally in <20s.
- **SC-002 (JSON parsability)** — `tests/integration/test_json_envelope_strict.py` (WP02) covers the SaaS state matrix; the consolidated E2E spot-checks `mission branch-context --json` via `json.loads(stdout)`.
- **SC-003 (Identity preservation rate)** — WP03 unit + integration tests cover colon arities 1–4 and assert `model`/`profile_id`/`role` in rendered prompts.
- **SC-004 (Review-cycle precision)** — WP04 tests assert the counter is unchanged across ≥3 reclaim/regenerate runs and advances by exactly 1 on a real rejection.
- **SC-005 (Lifecycle observability)** — `tests/integration/test_next_lifecycle_records.py` (WP05) covers ≥5 issuances with mid-cycle orphan; the consolidated E2E asserts at least one `started` record after `next` issues an action and that the `canonical_action_id` matches the issued step id.
- **SC-006 (Charter parity rate)** — `tests/specify_cli/cli/commands/test_charter_generate_autotrack.py` (WP06) covers the auto-track + non-git fail-fast contract; the consolidated E2E exercises `generate → bundle validate` with no intervening git ops.
- **SC-007 (Documentation/CLI agreement)** — `docs/how-to/setup-governance.md` updated; no documented governance-setup flow contains a `git add charter.md` step between `charter generate` and `charter bundle validate`.
- **SC-008 (Release-surface discipline)** — Diff inventory: one new top-level public CLI command, `spec-kitty review`, added for mission-review fidelity checks (#908); one new `spec-kitty doctor invocation-pairing` subcommand under the existing `doctor` group for lifecycle observability; zero new top-level runtime dependencies in `pyproject.toml` `[project.dependencies]`.

## [3.2.0a5] - 2026-04-27

### Fixed

- CLI auth now consumes the server Tranche 2 contract end to end: logout posts refresh tokens to `/oauth/revoke`, local credential cleanup failures are reported truthfully, refresh handles benign 409 replay without resubmitting a spent token, and `auth doctor --server` checks `/api/v1/session-status` with safe re-authentication guidance (#902).
- Fix `spec-kitty upgrade` silently leaving projects in PROJECT_MIGRATION_NEEDED state by stamping `schema_version` after metadata save (#705, WP01).
- `spec-kitty init` in a non-git directory now prints an actionable "run `git init`" message (#636, WP05).
- Suppress misleading "shutdown / final-sync" red error lines after a successful `spec-kitty agent mission create --json` payload (#735, WP06).
- Deduplicate "Not authenticated, skipping sync" / "token refresh failed" diagnostics to at most once per CLI invocation (#717, WP06).
- Fix `read_events()` raising `KeyError('wp_id')` on `DecisionPointOpened` / `DecisionPointResolved` events that share `status.events.jsonl` with lane-transition events. Restores `finalize-tasks` / `materialize` / dashboard for any mission that uses the Decision Moment Protocol (#830, WP08).

### Changed

- Loosen `.python-version` from a hard `3.13` pin to `3.11` (the floor declared by `pyproject.toml`) and restore `mypy --strict` cleanliness on `mission_step_contracts/executor.py` (#805, WP03).

### Removed

- Retire the deprecated `/spec-kitty.checklist` command surface from every supported agent's rendered output. The canonical requirements checklist at `kitty-specs/<mission>/checklists/requirements.md` is unaffected (#815, supersedes #635, WP04).

### Internal

- Add regression tests confirming `--feature` aliases stay hidden from `--help` while remaining accepted (#790, WP07).
- Add regression test confirming `spec-kitty agent decision` command shape stays consistent across docs / help / skill snapshots (#774, WP07).

### Added

- **Frontend Freddy agent profile** — browser-side implementer specialising in HTML/CSS/JavaScript/TypeScript, component frameworks (React, Vue, Svelte), WCAG 2.1 accessibility, Core Web Vitals performance, and frontend testing (vitest, Playwright). Specialises from `implementer-ivan`. Self-review protocol enforces lint, type-check, unit/component tests, e2e smoke, axe accessibility gate, and bundle budget. Avoidance boundary explicitly names Node Norris's server-side domain.
- **Node Norris agent profile** — server-side Node.js implementer specialising in HTTP APIs (Express/Fastify/NestJS), async/Promise discipline, streaming, npm security (`npm audit`), and integration testing (supertest). Specialises from `implementer-ivan`. Avoidance boundary explicitly names Frontend Freddy's browser-rendering domain. The two profiles are mutually exclusive by design.
- **BDD paradigm** (`behaviour-driven-development`) — encodes BDD as a three-phase collaboration practice: Discovery (Three Amigos conversations), Formulation (Given/When/Then specifications), and Automation (executable living documentation). References `DIRECTIVE_034` and `DIRECTIVE_037`.
- **BDD Scenario Lifecycle procedure** (`bdd-scenario-lifecycle`) — covers the Formulation → Automation → Maintenance phases that follow an Example Mapping Workshop. Toolchain-agnostic (Cucumber-JVM, Cucumber-JS, Behave, SpecFlow). Encodes four anti-patterns: imperative Gherkin, rubber-stamp scenarios, shared mutable state, and orphaned step definitions.
- **New tactics:**
  - `reference-architectural-patterns` — structured selection of named reference patterns (Layered, Hexagonal, Event-Driven, CQRS, Microservices, Modular Monolith) scored against coupling, scalability, and operational complexity constraints.
  - `development-bdd` — architecture-level BDD tactic for expressing observable behavioral contracts at system boundaries before implementation; distinct from the existing `behavior-driven-development` technique tactic.
  - `bug-fixing-checklist` — language-agnostic test-first defect resolution: write a reproduction test before touching production code.
  - `test-readability-clarity-check` — dual-perspective reconstruction check: read only tests, reconstruct system understanding, compare against spec to surface documentation gaps.
  - `code-documentation-analysis` — brownfield boundary discovery by extracting and clustering domain terminology from code and documentation artifacts. Contributes foundational analysis tactics toward the brownfield investigation skill described in [#666](https://github.com/Priivacy-ai/spec-kitty/issues/666).
  - `terminology-extraction-mapping` — systematic extraction and relationship mapping of domain terms across multiple sources to produce a maintainable glossary. Complementary artifact to the bounded-context linguistic discovery approach targeted by [#666](https://github.com/Priivacy-ai/spec-kitty/issues/666).
- **Tactic directory normalization** — shipped tactics reorganised into four category subdirectories: `testing/` (15 tactics), `analysis/` (14), `communication/` (7), `architecture/` (14). Cross-cutting tactics remain in the `shipped/` root. The existing `rglob` loader requires no changes.
- **`tasks-finalize` command skill** — added to `CANONICAL_COMMANDS` in the agent skills pipeline and deployed to `.agents/skills/spec-kitty.tasks-finalize/`. Closes the gap where this command was missing from Codex/Vibe skill packages. <!-- tool-surface: ignore -->

### Changed

- **Profile enrichment** — four existing profiles updated with additive tactic and paradigm references:
  - `implementer-ivan`: `bug-fixing-checklist` tactic reference (propagates to all specialist profiles via `resolve_profile()` union merge).
  - `reviewer-renata`: `test-readability-clarity-check` and `bdd-scenario-lifecycle` tactic references; `behaviour-driven-development` paradigm in context sources.
  - `architect-alphonso`: `development-bdd` tactic reference; BDD paradigm, example-mapping-workshop, and bdd-scenario-lifecycle in additional context sources.
  - `java-jenny`: `behavior-driven-development` and `bdd-scenario-lifecycle` tactic references; `bdd-scenarios` self-review step (Cucumber-JVM + Serenity BDD gate).
- **`behavior-driven-development` tactic enriched** — extended `notes` with a toolchain landscape section (Cucumber family, Playwright, Selenium, Serenity BDD, custom DSLs; source: `patterns.sddevelopment.be/primers/toolchain-and-automation/bdd`); three new `failure_modes` (rubber-stamp scenarios, shared mutable state between scenarios, orphaned step definitions); cross-references to the new BDD paradigm and procedure.
- **`tactic-references` union-merged in `resolve_profile()`** — `tactic-references` added to `_LIST_FIELDS` in `src/doctrine/agent_profiles/repository.py`. Specialist profiles now inherit base-profile tactic references via `_union_merge` at resolution time rather than overriding them.
- **Tactic compliance test extended** — `test_tactic_compliance.py` `ARTIFACT_DIRS` now includes `procedure` and `paradigm` types, enabling cross-type reference validation for tactics that reference procedures or paradigms.
- **Shared package boundary cutover** (mission `shared-package-boundary-cutover-01KQ22DS`) — `spec-kitty-runtime` is no longer a dependency of `spec-kitty-cli`. The CLI now owns its own runtime internally under `src/specify_cli/next/_internal_runtime/`; `spec-kitty next` works from a clean install of `spec-kitty-cli` alone. `spec-kitty-events` and `spec-kitty-tracker` are external PyPI dependencies consumed via their public import surfaces (`spec_kitty_events`, `spec_kitty_tracker`). The vendored events tree under `src/specify_cli/spec_kitty_events/` has been removed (~23 kLoC). Developers who relied on editable cross-package overrides should consult [`docs/development/local-overrides.md`](../guides/local-overrides.md); operators upgrading from a pre-cutover release should consult [`docs/migration/shared-package-boundary-cutover.md`](../migrations/shared-package-boundary-cutover.md). Decision rationale recorded in [ADR 2026-04-25-1](../adr/3.x/2026-04-25-1-shared-package-boundary.md).

### Removed

- **`constraints.txt`** — the file existed solely to paper over a transitive pin conflict with the retired `spec-kitty-runtime` package and is no longer needed.

### Fixed

- `spec-kitty agent config list/status` now checks global command roots for slash-command agents instead of reporting missing project-local command directories after `init`.
- `spec-kitty agent config add/sync --create-missing` no longer recreates retired project-local command directories for globally managed slash-command agents.
- `spec-kitty agent config remove/sync` now removes only the managed command surface for project-local agent directories, preserving unrelated files such as `.github/workflows/`.

### Added — Documentation mission composition rewrite (#502, #461, Phase 6 WP6.4)

- Documentation mission now runs on the StepContractExecutor composition substrate, mirroring research (#504) and software-dev (#503). The runtime resolves the new composed step contracts ahead of the legacy `mission.yaml` workflow via the existing `_resolve_runtime_template_in_root` precedence — no loader changes were required.
- New runtime sidecar templates: `src/specify_cli/missions/documentation/mission-runtime.yaml` and `src/doctrine/missions/documentation/mission-runtime.yaml`.
- Six shipped step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-{discover,audit,design,generate,validate,publish}.step-contract.yaml`.
- Six action doctrine bundles under `src/doctrine/missions/documentation/actions/{discover,audit,design,generate,validate,publish}/` (governance guidelines + directive/tactic indices).
- DRG action nodes and edges for `action:documentation/{discover,audit,design,generate,validate,publish}` in `src/doctrine/graph.yaml`.
- Composition wiring in `src/specify_cli/next/runtime_bridge.py`: `_COMPOSED_ACTIONS_BY_MISSION["documentation"]` and a fail-closed guard branch in `_check_composed_action_guard()` raising a structured error for unknown documentation actions. `src/specify_cli/mission_step_contracts/executor.py` adds six `_ACTION_PROFILE_DEFAULTS` entries (`researcher-robbie` for discover/audit, `architect-alphonso` for design, `implementer-ivan` for generate, `reviewer-renata` for validate/publish).
- Real-runtime integration walk at `tests/integration/test_documentation_runtime_walk.py` proving SC-001 / SC-003 / SC-004 from a freshly initialized temp repo.

#### Backward compatibility

- The legacy `src/specify_cli/missions/documentation/mission.yaml` and `src/doctrine/missions/documentation/mission.yaml` files remain on disk for backward reference. Existing documentation-mission projects that authored against the legacy workflow continue to work; runtime template resolution prefers the new `mission-runtime.yaml` ahead of the legacy file via the existing precedence in `_resolve_runtime_template_in_root` (no loader changes in this PR).

### Added

- **Upgrade compatibility planner** — `spec-kitty upgrade` now separates CLI
  update guidance from current-project schema compatibility. New flags
  `--cli`, `--project`, `--yes`, and `--no-nag` support CLI-only guidance,
  project-only migrations, non-interactive confirmation, and explicit nag
  suppression. `spec-kitty upgrade --dry-run --json` emits the stable
  compatibility-plan contract for automation.
- **Host-surface parity matrix** at `docs/host-surface-parity.md` — authoritative record of how each of the 15 supported host surfaces teaches the standalone dispatch governance-injection contract. Closes the remaining `#496` host-surface breadth rollout.
- **Mode of work runtime derivation** — every standalone dispatch invocation records its `mode_of_work` (`task_execution`, `mission_step`, or `query`) on the `started` event. Derivation is from the CLI entry command.
- **Correlation links** — `spec-kitty profile-invocation complete` accepts `--artifact <path>` (repeatable) and `--commit <sha>` (singular); each appends an additive event to the invocation JSONL for single-file request→artifact/commit correlation.
- **SaaS read-model policy** at `src/specify_cli/invocation/projection_policy.py` — typed module mapping `(mode, event)` to projection rules. Documented in `docs/trail-model.md`.
- **Tier 2 SaaS projection decision** — decisively documented as deferred in `docs/trail-model.md`. Tier 2 evidence stays local-only in 3.2.x.
- **README Governance layer subsection** — entry point for operators discovering standalone dispatch.
- **Decision Moment Ledger (V1)** — new `spec-kitty agent decision` subgroup with five
  subcommands: `open`, `resolve`, `defer`, `cancel`, `verify`. Mints ULID `decision_id`s
  at interview ask-time, writes paper trail under `kitty-specs/<mission>/decisions/`
  (`index.json` + `DM-<id>.md`), and appends `DecisionPointOpened(interview)` /
  `DecisionPointResolved(interview)` events to `status.events.jsonl`. Local-only;
  no SaaS sync required.
- **Charter integration** — `spec-kitty charter interview` now calls `decision open`
  before each question and the appropriate terminal command after each answer.
  `answers.yaml` behavior is unchanged.
- **Specify + Plan template updates** — `specify.md` and `plan.md` source templates
  gain a Decision Moment Protocol section instructing the LLM to call decision
  subcommands at ask/resolution time and write `<!-- decision_id: <id> -->` anchors
  for deferred decisions.
- **`decision verify` gate** — scans `spec.md` / `plan.md` for
  `[NEEDS CLARIFICATION: ...] <!-- decision_id: <id> -->` sentinels and
  cross-checks against the decisions index. Exits non-zero on drift
  (`DEFERRED_WITHOUT_MARKER`, `MARKER_WITHOUT_DECISION`, `STALE_MARKER`).
- **Widen Mode (#758)** — `spec-kitty agent decision widen` + `resolve --from-widen`
  lifecycle. Writes `widen-pending.jsonl`, emits `DecisionPointWidened` events,
  integrates with charter/specify/plan widen affordances. Surfaces decision
  write-back errors explicitly instead of silently suppressing them.

### Changed

- Project schema compatibility is now enforced by the centralized compat
  planner. Out-of-date CLI notices are passive and throttled; incompatible
  project schemas block unsafe commands with exit codes 4, 5, or 6 and exact
  remediation guidance.
- `spec-kitty profile-invocation complete --evidence` is now mode-gated: rejected on non-evidence-eligible invocations with `InvalidModeForEvidenceError`. Rejection occurs before any write; the invocation stays open.
- `_propagate_one` consults the new projection policy after the sync-gate and authentication lookup. Existing `task_execution` / `mission_step` projection behaviour is preserved exactly.
- Dashboard user-visible wording: the mission selector, current-mission header, overview heading, analysis heading, and empty-state prompt now read "Mission Run" / "mission" instead of "Feature". Backend identifiers (CSS classes, HTML IDs, cookie keys, API route segments, JSON field names) are unchanged.
- **`spec-kitty-events` bumped to `==4.0.0`** — vendored copy at
  `src/specify_cli/spec_kitty_events/` refreshed. Introduces
  `DecisionPointOpenedInterviewPayload`, `DecisionPointResolvedInterviewPayload`,
  `OriginSurface.PLANNING_INTERVIEW` (`origin_surface: planning_interview`),
  `OriginFlow` enum (values `specify`, `plan`), `DecisionPointWidened`, and
  `TerminalOutcome` enum.
- **`[tool.uv.sources]`** redirects `spec-kitty-events` to `../spec-kitty-events/`
  in editable mode for monorepo development. Dev-only; ignored by pip / PyPI.

### Deferred

- `spec-kitty explain` (issue #534) remains deferred to Phase 5 pending DRG glossary addressability (#499, #759).

### Out of scope (tracked separately)

- SaaS sync projection for widened decisions — tracked in spec-kitty-saas#110, #111.
- Tasks-phase interview support — future mission.

### Migration notes

**No operator action required for routine upgrade.** The trail model is additive:

- Pre-mission invocation records (no `mode_of_work`) continue to accept `--evidence` and project under legacy `task_execution` rules.
- Existing SaaS dashboards see no change for `task_execution` / `mission_step` traffic.
- New standalone dispatch events now appear in the SaaS timeline as minimal entries without body — this is a deliberate behaviour change documented in the SaaS Read-Model Policy table.

### Added (Phase 4 trail follow-on)

- `docs/trail-model.md`: Formal operator documentation for the Phase 4 trail contract,
  mode-of-work taxonomy, tier promotion rules, SaaS projection policy, intake positioning,
  and explain deferral (WP04).
- "Governance context injection" section in `.agents/skills/spec-kitty/SKILL.md` <!-- tool-surface: ignore -->
  for Codex/Vibe hosts, enabling Tier 1 trail recording without host-side SaaS auth (WP03).
- "Standalone invocations (outside missions)" section in
  `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` for Claude Code and gstack hosts,
  covering when to open an invocation record outside the mission workflow (WP04).
- End-to-end invocation integration tests in
  `tests/specify_cli/invocation/test_invocation_e2e.py` covering Tier 1 JSONL write,
  complete-event append, local-only list read, and sync-gate suppression (WP05).

### Fixed

- `propagator.py` (`_propagate_one`): Invocation events are now suppressed when
  `effective_sync_enabled = False`, even when the user is authenticated. Previously,
  sync-disabled checkouts could still emit SaaS events if a WebSocket client was
  connected (WP01).
- `executor.complete_invocation` now calls `promote_to_evidence()` when the
  `--evidence` flag is supplied, enabling correct Tier 2 artifact promotion (WP03).

### Changed

- Issue #496: Priority-surface slice complete in 3.2.x (Claude Code via
  `spec-kitty-runtime-next` doctrine skill, Codex CLI via SKILL.md governance context
  injection). Remaining 9 surfaces tracked in #496 for a follow-on patch or Phase 5.
- Issue #534: `spec-kitty explain` explicitly deferred to Phase 5 (requires DRG
  glossary addressability, issue #499). A partial implementation without glossary
  citations would be misleading.

## [3.2.0a4] - 2026-04-21

### Added

- **Mutation-aware test suites** — kill-the-survivor passes for `doctrine.resolver`, `doctrine.agent_profiles`, `doctrine.missions`, `doctrine.shared`, and `specify_cli.compat.registry`. Achieves 75–85 % kill rates per module; residuals documented as trampoline-equivalent, unloadable, or functionally equivalent in `docs/development/mutation-testing-findings.md`.
- `_OPTIONAL_KEYS` / `_ALL_KNOWN_KEYS` constants in `specify_cli.compat.registry._validate_entry` — unknown YAML keys now raise `RegistrySchemaError` before `ShimEntry(**entry)` can raise `TypeError`.
- `model_dump(mode="json")` on WP frontmatter serialization in `finalize_tasks` — prevents `Path` objects from reaching YAML serialization.

### Added

## [3.2.0a3] - 2026-04-21

### Fixed

- Release publish no longer hard-fails when the private `SPEC_KITTY_SAAS_READ_TOKEN` secret is absent. The pipeline still enforces runtime drift and exact wheel installability, and it runs the SaaS consumer-contract check whenever the private compatibility reference can actually be fetched.

## [3.2.0a2] - 2026-04-21

### Changed

- `spec-kitty-runtime` is now pinned to `0.4.4`, matching the corrected published runtime line rather than the broken `0.4.3` metadata.
- Release readiness and tag-time publish pipelines now verify shared-package drift, candidate-wheel installability with plain `pip`, and candidate compatibility against the SaaS consumer contract before publish.

### Removed

- Temporary `tool.uv.override-dependencies` masking for `spec-kitty-events`. Release validation now requires the published runtime metadata to resolve cleanly without local overrides.

## [3.2.0a1] - 2026-04-20

### Added

- **Mutation testing** — `mutmut` 3.5.0 added to `[project.optional-dependencies.test]` and configured in `[tool.mutmut]` as a **local-only** quality gate. Includes a curated doctrine set: `tactic:mutation-testing-workflow`, `styleguide:mutation-aware-test-design`, and language-specific toolguides for Python (`mutmut`) and TypeScript (`stryker`), all anchored to `DIRECTIVE_034` in the DRG graph. ADR `2026-04-20-1-mutation-testing-as-local-only-quality-gate.md` records the decision, the sandbox constraints, and the two-marker exclusion taxonomy.
- **`non_sandbox` / `flaky` pytest markers** — registered in `pytest.ini` and `pyproject.toml[tool.pytest.ini_options].markers`. Per-file `--ignore=` entries for sandbox-incompatible tests have been migrated to module-level `pytestmark` declarations; `[tool.mutmut].pytest_add_cli_args` now deselects via `-m "not non_sandbox and not flaky ..."`. Directory-level ignores remain only where tests fail during pytest *collection* (import errors that markers cannot intercept). 1 test is currently marked `flaky` as debt to be root-caused.
- **`docs/how-to/run-mutation-tests.md`** — Contributor how-to covering local `mutmut run` invocation, the kill-the-survivor workflow, equivalent-mutant suppression, and the `non_sandbox` / `flaky` marker taxonomy.
- Charter synthesizer now has a real harness-owned operator path: the new generated-artifact adapter reads agent-authored YAML from `.kittify/charter/generated/` and promotes validated doctrine into the live `.kittify/doctrine/` tree.
- `spec-kitty charter resynthesize --list-topics` now lists valid project-artifact selectors, DRG URNs, and interview-section selectors, including hyphenated aliases for section names.
- `spec-kitty charter status --provenance` now reports synthesis generation state, evidence summary, manifest health, and per-artifact provenance visibility alongside the older charter sync surface.
- ADR `2026-04-19-6-harness-owned-generated-artifact-charter-handoff.md` now records the host-side charter handoff contract: exact file layout, identity rules, and CLI sequence.
- **`architecture/2.x/06_migration_and_shim_rules.md`** — Authoritative compatibility shim lifecycle
  rulebook covering 4 rule families: schema/version gating, bundle/runtime migration authoring contract,
  shim lifecycle (with copy-paste template), and removal plans/registry contract. Required reading for
  all future extraction missions (#615).
- **`architecture/2.x/shim-registry.yaml`** — Machine-readable registry of all known compatibility
  shims. Starts empty (zero-shim baseline confirmed at mission-615 start). Future shims must be
  registered here before merging. Validated by `spec-kitty doctor shim-registry` (#615).
- **`spec-kitty doctor shim-registry`** — New CI enforcement subcommand that classifies each
  registered shim as `pending`, `overdue`, `grandfathered`, or `removed`. Exits 1 when any shim
  is overdue; exits 2 on configuration error. Supports `--json` for machine-readable CI output (#615).

### Changed

- `spec-kitty charter synthesize` and `spec-kitty charter resynthesize` now default to the generated-artifact adapter. `--adapter fixture` remains available only for deterministic offline regression runs.
- `spec-kitty charter synthesize --dry-run` is now a real stage-and-validate pass: it writes the staged artifact set, runs project DRG validation and neutrality gating, and only skips the final promote step.
- Shared contract-library pins now align with the current released pair consumed across the CLI and SaaS surfaces: `spec-kitty-events==3.2.0` and `spec-kitty-tracker==0.4.2`.
- Release pipeline now generates and attaches a CycloneDX SBOM (`sbom.cdx.json`) to every GitHub Release. The SBOM is an environment-snapshot of the fully resolved dependency tree at build time, making it straightforward for enterprise users to ingest the inventory into tools like Dependency-Track for continuous CVE monitoring without rescanning the package themselves.

### Fixed

- Directive provenance now records canonical URNs (`directive:PROJECT_<NNN>`) instead of slug-based placeholders, which restores correct directive filenames, provenance reload, and `directive:PROJECT_<NNN>` resynthesis.
- Bounded resynthesis now preserves evidence inputs end-to-end, so regenerated provenance entries keep the correct `evidence_bundle_hash` and `corpus_snapshot_id`.
- Generated-artifact synthesis errors now point to the exact expected file path and exact expected artifact id, which makes harness handoff mistakes easier to diagnose.
- Charter neutrality lint now scans mission `templates/` directories in addition to `command-templates/`, so banned terms in generic mission prompt files are caught by the default repo scan (#653 tripwire).
- Bump `requests` floor to `>=2.33.0` (CVE-2026-25645).
- Bump `pytest` floor to `>=9.0.3` (CVE-2025-71176).
- Pin `pygments>=2.20.0` explicitly to resolve CVE-2026-4539 in the transitive dependency pulled in via `rich`.
- `auth refresh` now treats `HTTP 401` responses with `invalid_grant` or `session_invalid` error codes identically to `HTTP 400`, and clears the locally stored session on server-side refresh rejection so `auth status` no longer reports stale credentials as authenticated.

### Removed

- **`specify_cli.charter` compatibility shim** — The re-export shim at `src/specify_cli/charter/` has been
  removed. External code importing `specify_cli.charter.*` must migrate to the canonical package:
  `from charter import <name>`. See
  [docs/architecture/05_ownership_map.md](../architecture/05_ownership_map.md) for the full
  charter slice entry and the reference exemplar pattern. Closes #611.

## [3.1.8] - 2026-04-29

### Fixed

- Dashboard feature polling now tolerates `/api/features` error responses and
  malformed payloads without crashing on an undefined `features` array, so the
  UI no longer gets stuck loading when feature scanning fails.
- OpenCode global command installation now targets OpenCode's config command
  directory, honoring `OPENCODE_CONFIG_DIR` and `XDG_CONFIG_HOME` before
  falling back to `~/.config/opencode/commands`.

## [3.1.7] - 2026-04-28

### Fixed

- Compact charter context now preserves charter section anchors, directive IDs,
  and tactic IDs so follow-on agent prompts keep project charter rules in LLM
  context after bootstrap load.
- Review claims now enter the canonical `in_review` lane while still
  recognizing legacy review-claim events, avoiding review-loop false blocks.
- Merge completion now keeps post-merge status transitions stable and avoids
  duplicate done/approved emissions.
- `spec-kitty intake` now caps oversized plan files, ignores out-of-repo and
  symlinked auto-detected plans, and writes mission brief/provenance files
  atomically.
- `auth refresh` now treats `HTTP 401` responses with `invalid_grant` or
  `session_invalid` error codes like `HTTP 400`, and clears locally stored
  sessions after server-side refresh rejection.
- Local dashboard mission selectors now sort by mission recency instead of
  lexical slug order.
- `agent config list/status/add/sync/remove` now respects global command roots
  for slash-command agents and avoids recreating retired project-local command
  directories.
- Status event readers now ignore non-lane mission events in
  `status.events.jsonl` while still failing loudly for malformed lane events.
- Sync shutdown diagnostics are deduplicated within a process and suppressed
  after successful JSON mission creation.

### Changed

- `spec-kitty-tracker` is pinned to `0.4.3` for the latest tracker-side
  stability fixes.
- The local `.python-version` pin now uses `3.13` instead of a patch-specific
  interpreter version.

## [3.1.6] - 2026-04-20

### Fixed

- `spec-kitty agent action implement` now exposes and forwards
  `--acknowledge-not-bulk-edit` to the underlying workspace-allocation command,
  allowing non-bulk-edit missions to suppress false-positive bulk-edit inference
  warnings during workspace creation.

### Docs

- Spec Kitty's internal maintainer charter now records the ownership boundary
  for user-authored custom commands, custom skills, and project overrides, with
  an explicit proof trail showing that package-owned mutation flows must preserve
  files whose ownership is not proven by managed-path or manifest data.

## [3.1.5] - 2026-04-16

### Changed

- Keep `main` on the stable `3.x` release line. Release docs, install guidance,
  and README messaging now point new users at `3.1.x` on GitHub Releases and PyPI,
  while keeping `1.x-maintenance` explicitly maintenance-only.

### Fixed

- Make `spec-kitty upgrade` auto-commit safely through the charter rename migration.
  The `safe_commit` backstop now disables rename collapsing during its staged-path
  probe, and upgrade auto-commit expands changed directories into concrete paths
  before validating the staging area. This closes the false-positive abort reported
  in [#643](https://github.com/Priivacy-ai/spec-kitty/issues/643).
- Remove pytest/junit prompt bias from charter defaults, plan templates, and doctrine
  guidance. Packaged defaults now start from neutral selections, language inference
  flows through explicit repo signals, and language-scoped doctrine artifacts remain
  available when no active language filter is provided.

### Docs

- Align README and user-facing release docs around swim-lane terminology and the
  `3.1.x` stable release line.

## [3.1.4] - 2026-04-15

### Fixed

- Make `/spec-kitty.plan` stop instructing agents to update imaginary
  agent-specific context files or hunt for non-existent `agent context update`
  commands. Planning now stays focused on the actual mission artifacts it owns.
- Clarify `/spec-kitty.specify` mission-handle timing and non-blocking charter
  behavior so creation-time flows do not assume a mission already exists or stop
  on missing charter state.
- Tighten generated `/spec-kitty.implement`, `/spec-kitty.review`, and
  `/spec-kitty.merge` wrappers so they use the canonical `--mission <handle>`
  language and explicitly avoid redundant context rediscovery, including
  separate charter loads.

## [3.1.3] - 2026-04-15

### Fixed

- Make `/spec-kitty.charter` use an LLM-led interview by default, with better
  repo-scan guidance for greenfield/bootstrap repos, explicit doctrine-gap
  handling, natural-language questioning, depth scaling, and commit-after-generate
  behavior.
- Preserve explicit empty `selected_paradigms`, `selected_directives`, and
  `available_tools` during charter compilation instead of broadening them to
  packaged defaults.

### Docs

- Add ADR recording that explicit empty charter selections must remain empty and
  must not silently expand to shipped defaults.

## [3.1.2] - 2026-04-15

### Fixed — CI recovery & release readiness

- **`release-readiness` workflow now filters `windows_ci` tests** on the Linux runner. The job was running the full suite with no marker filter, failing 10 Windows-only tests (auth file-fallback, kernel paths, sync daemon paths, tracker credentials, migrate messaging, keyring packaging, lock contention, Windows home path). Those tests continue to run on the native `ci-windows.yml` job.
- **Kiro agent registration completed**: added `.kiro/` to `gitignore_manager.AGENT_DIRECTORIES`, regenerated 11 canonical command baselines under `tests/specify_cli/regression/_twelve_agent_baseline/kiro/`, and updated the four count constants that had drifted after PR #626 (13 slash-command agents, 15 `AGENT_DIRECTORIES` entries).
- **Auth test fixtures aligned with the hardened HTTP transport** introduced in `Harden SaaS auth and restore build sync emission`. Tests for `AuthorizationCodeFlow`, `TokenRefreshFlow`, `WebSocketTokenProvisioner`, and the browser-login/refresh-transport integration paths now patch `PublicHttpClient` in each flow module's own namespace (matching the production call graph) instead of raw `httpx.AsyncClient`. Network-error paths raise `NetworkError` from the client mock rather than `httpx.ConnectError` to match the new `except NetworkError` contract.
- **`ResolutionTier` unified across `doctrine.resolver` and `specify_cli.runtime.resolver`**. `specify_cli.runtime.resolver` is now a thin re-export shim, as its own docstring had claimed. Tests assert tier equivalence via `.name` to stay robust against `pytestarch`'s filesystem-walk loader, which can load the same source file under alternate module names during `pytest --import-mode=importlib`.
- **Post-`unified-charter-bundle-chokepoint` test fixture hardening**: three pre-existing tests (`test_local_support_declarations_end_to_end`, `test_template_prompt_bootstrap_context_first_load`, `test_all_pass_with_healthy_setup`) now `git init` their tmp directories to satisfy the new `resolve_canonical_repo_root` precondition that calls `git rev-parse --git-common-dir`.
- **Codex / Vibe Agent Skills migration test alignment**: five tests that pre-dated mission 083 were updated to assert the new `.agents/skills/spec-kitty.<cmd>/SKILL.md` layout rather than the retired `.codex/prompts/` layout. Invariants preserved (direct `spec-kitty agent action` CLI calls, per-agent argument handling, agent assets generation); only the probe path changed to match the post-083 architecture.
- **Contract handoff fixture** updated to include `BuildRegistered` and `BuildHeartbeat` event types added on the emitter side by the SaaS-auth hardening.
- **Miscellaneous tails**: redacted a dev-machine path literal in an architecture review doc (caught by `test_command_template_cleanliness`); fixed `test_rewrite_shims.py::test_result_counts` to use two slash-command agents since codex is no longer one; marked `test_home_unit.py::TestGetKittifyHomeWindows::test_windows_default_path` `windows_ci` since DRIFT-3 of the Windows Compatibility Hardening mission made `get_kittify_home()` delegate to `specify_cli.paths.get_runtime_root().base`, which the monkeypatch-based simulation no longer drives reliably on non-Windows runners.
- **Kiro regenerated baselines** for all 12 canonical commands, closing the `tests/specify_cli/regression/test_twelve_agent_parity.py` baseline-missing cluster introduced by PR #626.

### Added

- **Unified charter bundle manifest v1.0.0** at `src/charter/bundle.py` declaring the three `sync()`-produced derivatives (`governance.yaml`, `directives.yaml`, `metadata.yaml`) as the authoritative bundle contract. `references.yaml` and `context-state.json` are explicitly out of v1.0.0 scope; they are produced by other pipelines.
- **Canonical-root resolver** at `src/charter/resolution.py` (`resolve_canonical_repo_root()`). Readers running inside a git worktree now transparently observe the main-checkout charter bundle without per-worktree materialisation. Closes Priivacy-ai/spec-kitty#339.
- **`spec-kitty charter bundle validate [--json]`** CLI surface for operator and CI bundle-health checks.
- **Migration `m_3_2_3_unified_bundle`** advances 3.x projects to the unified bundle layout. On a populated project it validates the bundle against the v1.0.0 manifest, invokes `ensure_charter_bundle_fresh()` to regenerate any missing derivatives, and emits a structured JSON report (see `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/migration-report.schema.json`). Idempotent — the second apply against an already-upgraded project is a clean no-op. Refs Priivacy-ai/spec-kitty#464, #479.

### Changed

- **`SyncResult` extended with `canonical_root: Path`** — `files_written` remains a list of file names relative to `canonical_root / .kittify/charter/`. Existing readers were rewired in lockstep; no compatibility shim.
- **`ensure_charter_bundle_fresh()` is now the sole chokepoint** for readers of `governance.yaml`, `directives.yaml`, and `metadata.yaml`. Direct reads of those files are forbidden and are enforced by an AST-walk coverage test (`tests/charter/test_chokepoint_coverage.py`). Refs Priivacy-ai/spec-kitty#461, #464.

### Unchanged (explicitly)

- **`.kittify/memory/` and `.kittify/AGENTS.md` symlinks in worktrees** remain as-is — they provide project-memory and agent-instructions sharing, documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179`. They are NOT part of the charter bundle; the canonical-root resolver fixes the worktree charter-visibility story without touching `src/specify_cli/core/worktree.py` (C-011).
- **Files under `.kittify/charter/` that are not v1.0.0 manifest files** (`references.yaml`, `context-state.json`, `interview/answers.yaml`, `library/*.md`) are unchanged. The migration lists them under `bundle_validation.unexpected` for operator visibility but does not delete, move, or rewrite them (C-012).
- **Project `.gitignore` is not reconciled** by the migration. The v1.0.0 manifest's required entries already match the repository `.gitignore` verbatim; the migration performs no read or write against `.gitignore` (D-12).

### Refs

- EPIC: Priivacy-ai/spec-kitty#461 (Charter as Synthesis & Doctrine Reference Graph).
- Phase 2 tracking: Priivacy-ai/spec-kitty#464.
- Closes on merge: Priivacy-ai/spec-kitty#339, #451.

### Fixed

- **`mission merge` no longer silently loses content when the repository carries legacy sparse-checkout state** — the stash/merge/stash-pop cascade used by the merge driver previously recorded phantom deletions for paths filtered out by a sparse-checkout pattern, and the subsequent housekeeping commit silently reverted content the preceding merge had introduced. Merge and `agent action implement` now run a sparse-checkout preflight and fail closed unless the operator passes `--allow-sparse-checkout`, `safe_commit` now aborts commits whose staging area contains paths outside the intended scope, and `mission merge` performs a post-merge refresh and invariant check before leaving the integration branch. Closes Priivacy-ai/spec-kitty#588.
- **`move-task --to approved` and `--to planned` on a lane-worktree review no longer require `--force` when the only untracked content is `.spec-kitty/`** — the review-lock uncommitted-changes guard now treats the execution lane's own `.spec-kitty/` scratch directory as expected content rather than an unexplained untracked path, so operators stop being trained to pass `--force` reflexively. Closes Priivacy-ai/spec-kitty#589.
- **Retry guidance emitted by the uncommitted-changes guard now names the actual target lane** rather than hardcoded `for_review`, so operators see the transition they were attempting instead of a misleading default.

### Added

- **`spec-kitty doctor sparse-checkout --fix`** — detection and one-command migration for repositories upgraded from pre-3.0 spec-kitty that still carry `core.sparseCheckout=true` and a `.git/info/sparse-checkout` pattern file. The fix removes the git-config entry, clears the pattern file, and verifies post-fix state.
- **`--allow-sparse-checkout` flag on `mission merge` and `agent action implement`** — explicit escape hatch for users with intentional sparse configurations. Use of the flag emits a `WARNING`-level structured log record (`spec_kitty.override.sparse_checkout`) at the CLI layer. Durable cross-repo audit event support is tracked as Priivacy-ai/spec-kitty#617.
- **Commit-time backstop inside `safe_commit`** — fail-closed check that aborts commits whose staging area contains paths outside the intended scope, independent of the preflight. This is the universal defence that catches sparse-stash-pop phantom-deletion cascades regardless of which command initiated them.
- **Per-worktree `.spec-kitty/` exclude entry** — every lane worktree now receives a local git exclude entry for `.spec-kitty/` at worktree creation, so lane scratch content stays invisible to the working-tree guard even in worktrees initialised before the fix.
- **Session-scoped sparse-checkout warning** at review-lock and task-command entry points — surfaces detected legacy sparse-checkout state once per process before an operator wastes a commit cycle, without blocking.
- **ADR `2026-04-14-1-sparse-checkout-defense-in-depth`** — documents the four-layer hybrid defence (merge/implement preflight, `safe_commit` backstop, session warning, `doctor --fix`) and the alternatives considered.

### Recovery for users already affected

If a prior `mission merge` landed on your target branch with a silent content
reversion (symptoms: a follow-up `chore: record done transitions` commit that
deleted content merged in the preceding commit), restore the content from the
merge commit that introduced it:

```bash
# Identify the merge commit
git log --merges --oneline -- <affected-file>

# Restore content from that merge
git checkout <merge-sha> -- <affected-file> [...]

# Commit the restoration
git add <affected-file> [...]
git commit -m "fix: restore content reverted by phantom-deletion bug"
```

Then run the migration to prevent recurrence:

```bash
spec-kitty doctor sparse-checkout --fix
```

Root-cause diagnostic trail: [Priivacy-ai/spec-kitty#588 (comment)](https://github.com/Priivacy-ai/spec-kitty/issues/588#issuecomment-4242179946).

## [3.1.2a4] - 2026-04-14

### Added

- **Kiro CLI as first-class agent** — `spec-kitty init --ai kiro` registers the Kiro CLI (Amazon Q Developer CLI's rebrand) with its own `.kiro/prompts/` directory and `kiro-cli` binary check. Legacy `--ai q` (→ `.amazonq/prompts/`) remains supported for backwards compatibility. README and `docs/reference/supported-agents.md` now document the shell-quoting requirement for `$ARGUMENTS` pass-through (see kirodotdev/Kiro#4141). Closes #246.

### Fixed

- **`diff-coverage` CI job no longer fails with "no merge base"** — the base-branch fetch was passing `--depth=1` after `actions/checkout@v6` had already fetched full history, which truncated `origin/<base>` back to a single commit and broke `diff-cover`'s merge-base computation. Dropped `--depth=1`.
- **`test_mission_v1_guards_unit.py::test_registry_keys` now matches the guard registry** — synchronised the `EXPECTED_GUARDS` set with the `occurrence_map_complete` guard added in #616.

## [3.1.2a3] - 2026-04-12

### Fixed

- **Merge-time numbering lock and retry safety** — `mission_number` assignment now acquires a file lock before scanning existing prefixes, MergeState uses `mission_id` as its canonical key, and interrupted merges no longer risk duplicate or skipped numbers on retry. Closes #601.
- **CLI no longer hangs 15–20 min when offline queue is full and session expired** — the offline queue drain path now respects a bounded timeout instead of blocking indefinitely on expired-session retries. Closes #598, #602.
- **Sonar readiness and parser findings addressed** — actionable maintenance issues flagged by SonarCloud (code smells, complexity, minor bugs) are resolved. Closes #599, #600.

## [3.1.2a2] - 2026-04-11

### Added

- **Hosted readiness control surfaces** — the CLI now exposes the canonical SaaS rollout/readiness module, a six-state hosted readiness evaluator, and a background-daemon policy/intent model that keeps stealth rollout behavior explicit while making enabled-mode failures actionable.

### Changed

- **Tracker command classification is corrected for first-run flows** — `tracker discover` no longer requires an existing mission binding, `tracker providers` remains available as static output without hosted prerequisites, and hosted/manual-daemon checks are applied according to command intent rather than indiscriminately.
- **Tracker dependency advances to the hardened hosted-discovery release line** — the CLI now targets `spec-kitty-tracker==0.4.1`, aligning the prerelease with the published runtime validation and canonical discovery contract shipped in the tracker SDK.

### Fixed

- **Background-daemon policy no longer blocks local-provider sync flows** — local tracker providers continue to execute direct sync operations even when hosted SaaS daemon startup is set to manual.

## [3.1.2a1] - 2026-04-10

### Added

- **Browser-mediated CLI auth preview** — `spec-kitty auth login` now supports browser-based OAuth with Device Authorization Flow fallback, centralized token management, secure storage, and WebSocket token provisioning against the SaaS contract.

### Changed

- **Human CLI auth now flows through the new auth subsystem** — HTTP transport, sync runtime, and tracker SaaS callers now refresh through the shared token manager instead of the legacy password/JWT credential path.

### Fixed

- **Browser auth CI coverage gaps** — test dependencies and stale tracker refresh patch targets were corrected so the new auth stack passes the core and integration suites reliably in CI.

## [3.1.1] - 2026-04-09

### Added

- **Semantic status-event merge driver** — `kitty-specs/**/status.events.jsonl` now uses a Spec Kitty merge driver that unions append-only event logs by `event_id`, rejects conflicting payloads, and fails closed when merged WPs do not reach `done` in the canonical event log.
- **Forward-safe mission identity** — newly created missions now mint a ULID `mission_id` at creation time, persist it to `meta.json`, and emit it through mission-created event payloads.
- **Release hygiene guardrail** — release validation now enforces `pyproject.toml` and `.kittify/metadata.yaml` version sync before a cut can proceed.

### Changed

- **`spec-kitty init` now produces a minimal file scaffold** — init no longer initializes git, creates bootstrap commits, or seeds `.agents/skills/`. The generated next steps now point users at `spec-kitty next` plus `spec-kitty agent action implement/review` as the canonical workflow.
- **Planning-artifact WPs are first-class lane-owned items** — the canonical planning lane is now `lane-planning`, and it resolves to the main repository checkout instead of an ad hoc special-case path.
- **Top-level `implement` is de-emphasized** — onboarding and command docs now treat `spec-kitty implement` as internal infrastructure rather than the primary user-facing flow.

### Fixed

- **Merge conflict recovery for `status.events.jsonl`** — append-only status events are no longer silently dropped during merge conflict resolution, and fresh repositories now self-heal the local git merge-driver config when running merge flows. Closes #574.
- **Planning/query consistency after PR #555** — mixed planning/code review-context resolution no longer crashes when a dependency resolves to the repo-root workspace, and fresh-run query mode now returns `run_id: null` instead of leaking a deleted temporary run id.
- **Dependency parser trailing-prose bleed** — the final WP section is now bounded at non-WP `##` headings so trailing prose does not get misread as dependency declarations.
- **Concurrent auth refresh race** — stale 401 responses during token rotation no longer wipe valid shared credentials from active CLI sessions.

## [3.1.1a3] - 2026-04-07

### Added

- **Global slash command installation** — all 16 spec-kitty slash commands are now installed globally to `~/.<agent-dir>/` (e.g. `~/.claude/commands/`, `~/.gemini/commands/`, `~/.codex/prompts/`, etc.) at every CLI startup, for all 13 supported agents. No `spec-kitty init` or per-project `spec-kitty upgrade` is required for commands to be available. Commands update automatically when the CLI is upgraded.
- **Migration `3.1.2_globalize_commands`** — removes existing per-project `spec-kitty.*` command files from `.claude/commands/`, `.gemini/commands/`, and equivalent directories in all configured agents. Runs automatically on `spec-kitty upgrade`.
- **ADR `2026-04-07-1-global-slash-command-installation`** — documents the decision to install commands globally, the full 13-agent table with global roots, and the rationale.

### Changed

- `spec-kitty init` no longer writes per-project command files. Commands are managed exclusively by the global startup hook.

## [3.1.1a2] - 2026-04-07

### Fixed

- **`spec-kitty init` / any CLI command no longer dirties the git repo** — every CLI invocation that touched status was unconditionally rewriting `kitty-specs/*/status.json`, even when nothing had changed, leaving ~60 files modified in `git status`. Root cause: `materialize()` stamped a fresh `datetime.now(UTC)` into `materialized_at` on every call. Fixed in `reducer.py` (3.1.1a1): `materialized_at` is now derived deterministically from the last event's `at` timestamp (or `""` for features with no events), and a content-equality guard skips the write when the file is already up to date. Closes #524.

### Added

- **Migration `3.1.1_normalize_status_json`** — one-shot upgrade migration that normalises all existing `kitty-specs/*/status.json` files to the new deterministic format. Runs automatically on `spec-kitty upgrade` for any project where the committed files still carry old wall-clock timestamps or the legacy `feature_slug` field. After the migration the skip-write guard in `materialize()` keeps all status snapshots stable indefinitely.

### Changed

- **`StatusSnapshot` and `ProgressResult` serialisation no longer emits `feature_slug`** — `with_tracked_mission_slug_aliases` previously injected a redundant `feature_slug` alias into every serialised snapshot. Now only `mission_slug` is written. Reading still accepts both keys for backward compat with existing files.

## [3.1.1a1] - 2026-04-07

### Added

- **Typed `WPMetadata` Pydantic model** (`src/specify_cli/status/wp_metadata.py`) — immutable, validated work package metadata with `update()` builder API; replaces all raw `frontmatter.get()` dict access across consumer files. Closes #410.
- **`Lane` enum state machine** — valid lane transitions enforced at the type level; all runtime consumers migrated from string comparisons to `Lane` enum values.
- **Typed dashboard API contracts** (`src/specify_cli/dashboard/handlers/api.py`) — Pydantic response models replace untyped dicts.
- **RE2 shim** (`src/kernel/_safe_re.py`) — `types.ModuleType`-based shim backed by `google-re2`; exposes the full `re` API and mitigates Sonar DOS hotspot findings. `google-re2>=1.1` added as a core runtime dependency.
- **CI status-layer test stages** — new `fast-tests-status` and `integration-tests-status` jobs run the `tests/status/` and `tests/specify_cli/status/` suites in parallel with existing core/doctrine jobs; their coverage outputs feed the `diff-coverage` gate.
- **`WPMetadata.display_title` property** — safe fallback for missing or empty WP titles.

### Changed

- All `frontmatter.get()` calls outside `frontmatter.py` migrated to typed `WPMetadata` access. Migration scripts retain raw dict access annotated `# MIGRATION-ONLY`.
- `WPMetadata.title` is now optional; WP read errors propagate gracefully via `read_wp_frontmatter()`.
- `OwnershipManifest.from_frontmatter()` accepts `WPMetadata` directly.
- `diff-coverage` job wired to consume `coverage-kernel.xml`, `coverage-fast-status.xml`, and `coverage-integration-status.xml` in both enforced (critical-path 90%) and advisory (full-diff) steps.
- GitHub Actions upgraded to Node.js 24 compatible versions (`actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`) across all workflow files.

### Fixed

- `ValidationError` caught in phase-1 status mirror (`status/emit.py`) — prevents NoneType crashes on malformed WP files.
- Ruff and mypy violations cleaned up in all files touched by the migration.
- Sonar false-positive NOSONAR suppressions added in `arbiter.py` and `dashboard/handlers/api.py`.
- WP03 validation report (mission 068) decision corrected from `close_with_evidence` to `tighten_workflow` to reflect the CI logic additions; `test_tighten_workflow_passes_large_pr_sample` implemented to verify the advisory-only contract.

## [3.1.0] - 2026-04-07

### Added

- **Planning pipeline integrity (mission 069)** — four structural fixes eliminating fragilities discovered during mission 068:
  - **Dirty-git reads fix (WP01)** — `materialize()` now derives `materialized_at` from the last event timestamp (deterministic) and skips the write when content is byte-identical. `materialize_if_stale()` returns a read-only `reduce()` call. All read-only commands leave zero modified files in `git status`. Fixes #524.
  - **Structured WP manifest — `wps.yaml` (WP02, WP03, WP04)** — new `src/specify_cli/core/wps_manifest.py` with Pydantic model, YAML loader, and `generate_tasks_md_from_manifest()`. JSON Schema at `src/specify_cli/schemas/wps.schema.json`. When `wps.yaml` is present, `finalize-tasks` derives dependencies exclusively from the manifest; `tasks.md` is regenerated as a derived artifact. `/spec-kitty.tasks-outline` and `/spec-kitty.tasks-packages` templates updated to produce/consume `wps.yaml`. Migration `m_3_2_0_update_planning_templates` propagates changes to existing installations. Fixes #525.
  - **`spec-kitty next` query mode (WP05)** — bare `spec-kitty next` (no `--result`) enters query mode: returns current step with `[QUERY — no result provided, state not advanced]` prefix without advancing the state machine. Prevents ghost completions when agents call `next` while disoriented. Fixes #526.
  - **Slug validator digit-prefix support (WP06)** — `KEBAB_CASE_PATTERN` updated to accept `NNN-*` slugs following spec-kitty's own naming convention. Fixes #527.

## [3.1.0a8] - 2026-04-07

### Added

- **Post-merge reliability and release hardening (mission 068)** — 5 work packages closing the workflow-stabilization track:
  - **Stale-assertion analyzer (WP01)** — new `src/specify_cli/post_merge/` package: stdlib `ast`-based tool that detects test assertions likely invalidated by merged source changes. CLI: `spec-kitty agent tests stale-check --base <ref> --head <ref> [--json]`. Integrated into the merge runner. No new dependencies, no network calls.
  - **Merge strategy + safe-commit + linear-history hint (WP02)** — `MergeStrategy` enum (MERGE/SQUASH/REBASE) in new `src/specify_cli/merge/config.py` with `--strategy` CLI flag (resolves: flag → `.kittify/config.yaml` → squash default). `safe_commit()` called after `_mark_wp_merged_done` before worktree removal (FR-019). Linear-history rejection hint guides users past protected-branch push failures. Closes #456.
  - **Diff-coverage policy validation (WP03)** — validation report confirms the enforce/advisory split already satisfies the policy intent. CI step names tightened to `diff-coverage (critical-path, enforced)` and `diff-coverage (full-diff, advisory)`. Closes #455.
  - **Release-prep CLI (WP04)** — new `src/specify_cli/release/` package: `propose_version()`, `build_changelog_block()`, `ReleasePrepPayload`. CLI: `spec-kitty agent release prep --channel {alpha,beta,stable} [--json]`. Zero network calls. Closes #457.
  - **Recovery extension + mission close (WP05)** — `scan_recovery_state()` extended with `consult_status_events=True` to detect merged-and-deleted WPs via event log; new `RecoveryState.ready_to_start_from_target` field. `spec-kitty implement` gains `--base <ref>` flag for explicit worktree branching. Closes #415.

### Fixed

- **`implement --base` Typer pattern** — changed to Annotated pattern, fixing test isolation failures where direct Python calls received `OptionInfo` objects instead of `None`
- **`implement` console capsys isolation** — `_json_safe_output` wrapper now resets `console._file = None` in `finally` to prevent "I/O operation on closed file" when tests run in sequence with pytest capsys
- **Replay parity test** — corrected `reduced.mission_key == "replay-mission"` (was wrong field name and wrong value)

## [3.1.0a7] - 2026-04-06

### Added

- **Runtime recovery and audit safety (mission 067)** -- 6 work packages delivering resilience and audit infrastructure:
  - **Merge resume recovery (WP01)** -- `spec-kitty merge --resume` recovers from interrupted merges with persistent state tracking in `.kittify/merge-state.json`
  - **Implementation crash recovery (WP02)** -- `spec-kitty implement --recover` restores execution context after agent crashes, rebuilding worktree state and resuming from last known checkpoint
  - **Stale-claim doctor checks (WP03)** -- `spec-kitty doctor` detects orphaned claims, stale locks, and zombie worktrees with structured diagnostic output
  - **Audit-mode scope relaxation (WP04)** -- ownership validation supports `scope: codebase-wide` for audit/cutover WPs; new `validate_audit_coverage()` warns on uncovered audit targets
  - **Shim-to-canonical migration (WP05)** -- all `spec-kitty agent shim <action>` calls replaced with direct `spec-kitty agent action <action>` across 48 agent command files
  - **Finalize-tasks audit wiring (WP06)** -- `validate_audit_coverage()` integrated into finalize-tasks ownership validation pipeline as a soft warning check

### Fixed

- **Agent command files** -- regenerated all 48 agent command files to use canonical `spec-kitty agent action` instead of deprecated `spec-kitty agent shim`
- **Post-merge test regressions** -- fixed 4 stale test assertions after mission 067 merge (implement template content, merge resume behavior, --recover flag default)

## [3.1.0a6] - 2026-04-06

### Added

- **Review loop stabilization (mission 066)** — new `src/specify_cli/review/` module with 6 submodules:
  - `artifacts.py` — persisted review-cycle artifacts at `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md` with YAML frontmatter. Replaces ephemeral `.git/spec-kitty/feedback/` storage. Backward-compatible `feedback://` pointer resolution retained (#432, #433).
  - `fix_prompt.py` — focused fix-mode prompt generation from review-cycle artifacts. Rejected WPs get ~40-line targeted prompts instead of replaying 400-500 line full WP prompts (#430).
  - `dirty_classifier.py` — dirty-state classification for review handoff. Partitions `git status --porcelain` output into blocking (WP-owned files) vs benign (status artifacts, other WP files, metadata). External reviewers no longer need `--force` for unrelated dirtiness (#439).
  - `baseline.py` — baseline test capture at implement time via `pytest --junitxml` + JUnit XML parsing. Review prompts include "Baseline Context" section distinguishing pre-existing failures from regressions. Configurable `review.test_command` for non-pytest projects (#444).
  - `lock.py` — concurrent review serialization via `.spec-kitty/review-lock.json`. Stale lock detection via PID check. Opt-in env-var isolation for projects that configure `review.concurrent_isolation` in config.yaml (#440).
  - `arbiter.py` — structured arbiter checklist with 5 standard rationale categories (pre-existing failure, wrong context, cross-scope, infra/environmental, custom). Override detection on forward `--force` from planned after rejection event. Decisions persisted in review-cycle artifact frontmatter (#441).
- **147 new tests** across the review module (avg 93% coverage, range 91-99%)
- **Implement-review skill update** — parallel sprint pattern, merge/conflict resolution guide, dead-code detection warning, post-merge validation steps
- **Tasks template handoff** — `/spec-kitty.tasks` now offers to invoke `/spec-kitty-implement-review` skill at completion for automated full-sprint execution

### Fixed

- **ReviewLock wired into live command path** — `ReviewLock.acquire()` called in `workflow.py review()` after workspace resolution; `ReviewLock.release()` called in `tasks.py move-task` on review completion
- **Removed dead `wp_prompt_path` parameter** from `generate_fix_prompt()` and all callers

## [3.1.0a5] - 2026-04-06

### Fixed

- **Dependency parsing in finalize-tasks** — new shared parser (`core/dependency_parser.py`) recognizes inline, colon-header, and bullet-list dependency formats. Both `agent mission finalize-tasks` and `agent tasks finalize-tasks` use the same parser. Non-empty disagreement between tasks.md and WP frontmatter triggers a diagnostic error instead of silently overwriting (#406).
- **validate-only is genuinely non-mutating** — all file writes gated behind `if not validate_only`. JSON output reports `would_modify`/`unchanged`/`preserved` without touching disk (#417).
- **Lane computation completeness** — every executable WP must appear in `lanes.json` or lane computation fails with a diagnostic error. Missing ownership manifests are a hard failure. Planning-artifact WPs surfaced in diagnostic summary. Zero-match globs and `src/**` fallback emit warnings (#422).
- **Parallelism collapse reporting** — new `CollapseReport` records every union-find merge with rule name and evidence. Rule 3 (surface heuristics) now gated on `_are_disjoint()` — WPs with provably disjoint owned files are not collapsed by keyword matches alone (#423).
- **Pipe-table mark-status support** — column-aware parser recognizes `[P]` in Parallel column (not corrupted), updates Status column or appends one. Checkbox format remains canonical for new generation (#438).
- **Agent command guidance** — all error messages, shim templates, and command-template examples now use `--mission` consistently. Five `require_explicit_feature()` callers fixed from `--feature` to `--mission`. Error messages include complete copy-pasteable example commands (#434).
- **Full --feature → --mission sweep** — 12 typer.Option declarations, 4 argparse declarations, 11 error messages, and 5 docstrings updated. `--mission` is the primary displayed flag name; `--feature` retained as hidden backward-compatibility alias (#448).

### Added

- `src/specify_cli/core/dependency_parser.py` — canonical shared dependency parser
- `CollapseEvent` and `CollapseReport` data models in `lanes/models.py`
- `LaneComputationError` exception for diagnostic lane failures
- `validate_glob_matches()` in ownership validation
- `planning_artifact_wps` field on `LanesManifest`
- Charter regression vigilance rules for `--mission` terminology canon

## [3.1.0a4] - 2026-04-06

### Fixed

- **Mission-era host surface cleanup** — removed remaining feature-era host command references from shipped templates, agent-facing prompts, and smoke-test scaffolding so new missions no longer regenerate `create-feature`, `feature_slug`, or `--feature` guidance on canonical paths.
- **Runtime mission metadata normalization** — mission resolution now prefers canonical `mission_type` metadata and rehydrates mission identity consistently in diagnostics, verification, and rebuild-state migrations.
- **Release-readiness regressions after host cutover** — updated cross-cutting, orchestrator, parity, body-sync, gitignore-isolation, and e2e smoke coverage to validate the mission-era CLI and contract instead of the removed feature-era host surface.

## [3.1.0a3] - 2026-04-05

### Fixed

- **Doctrine artifact discovery in subdirectories** — all 7 doctrine repositories now use `rglob()` instead of `glob()`, so artifacts in subdirectories of `shipped/` are no longer silently skipped (#396).
- **Dashboard `/api/features` empty response** — `StatusEvent.from_dict()` now accepts both `feature_slug` and `mission_slug` field names and normalizes the legacy `in_review` lane to `for_review`.
- **Stale `patch()` targets caught at lint time** — new `scripts/check_patch_targets.py` validates every `@patch()` target string resolves, added as an `[ENFORCED]` CI lint step (#394).
- **Architectural layer coverage guards** — meta-tests fail when a `src/` package has no layer assignment or a defined layer matches no module (#395).
- **Sonar reliability bugs** — resolved 7 findings: unreachable code (S1763), identical branches (S3923), premature async task GC (S7502), always-true condition (S2583), tautological assertion (S3981), CSS shorthand override (S4657), parameter shadowing (S1226).
- **Async task GC in event emitter** — `asyncio.ensure_future()` results held in `_pending_tasks` set with done-callback cleanup, preventing premature garbage collection.
- **`check-readiness` CI gate unblocked** — post-release version bump missed after tagging v3.1.0a2 (#408).

### Changed

- **CI test parallelization** — `fast-tests` and `integration-tests` split into `doctrine` + `core` phases running in parallel (#397).
- **`--mission-run` as canonical CLI flag** — added as alias for `--feature` across all CLI commands. `--feature` remains accepted as legacy alias.
- **Node.js 20 → 22** in CI workflows (current LTS).
- **Mutation testing CI job disabled** — too slow to run reliably.
- **Ruff max line length** increased from 120 to 164.
- **Defunct `tests/legacy` references removed**.

### Added

- **RTK search tooling toolguide** — new shipped doctrine artifact documenting RTK interception patterns and correct search tooling for worktree sessions.
- **`last_updated` field** on Toolguide model and schema.
- **Integration tests for nested artifact discovery** — 281-line test suite covering all 8 doctrine repository types.
- **`integration` pytest marker** registered in `pyproject.toml`.

## [3.1.0a2] - 2026-04-05

### Changed

- **Prerelease publishing is now first-class** — tag-mode release validation accepts matching prerelease tags such as `v3.1.0a0`, GitHub Releases are marked as prereleases automatically for those tags, and maintainer docs now document the end-to-end prerelease PyPI/GitHub publish path.
- **Rebased doctrine-stack work onto `main`'s execution architecture** — carry forward the doctrine, constitution, and template-repository work from PR #305 into PR #348 while preserving `main`'s context, ownership, event-log, merge-engine, and shim foundations instead of reviving deleted subsystems.
- **Kernel established as the shared dependency floor** — `src/kernel/` now owns shared path, atomic-write, and glossary-boundary primitives; doctrine no longer reaches back into `specify_cli`, and the package boundary is documented by ADRs and enforced by architectural tests.
- **Constitution now acts as the local routing layer for governance assets** — project-local mission path construction flows through `ProjectMissionPaths`, while doctrine-backed mission/template access is routed through `MissionTemplateRepository` and constitution-facing resolvers instead of scattered path assembly.
- **Mission terminology split clarified as the architectural answer to issue #241** — a direct `--feature` → `--mission` rename would have collided with the existing mission-type concept, so the branch now separates `mission type` (`--mission-type`) from `mission run` (`--mission-run`) and keeps legacy `--feature` compatibility where required during the deprecation window.
- **CI flows extended for the new package layout** — quality workflows now cover doctrine and kernel explicitly, including dedicated kernel coverage enforcement and updated readiness/release paths.
- **Fork-safe SonarCloud targeting via repository variables** — CI now resolves SonarCloud settings from `SONAR_ORGANIZATION`, `SONAR_PROJECT_KEY`, and optional `SONAR_HOST_URL`, with upstream-safe defaults and a fallback project-key convention of `<organization>_<repo-name>` when `SONAR_PROJECT_KEY` is unset.

### Fixed

- **Dashboard loading regressions on shared mission installs** — repaired the shared dashboard JavaScript syntax error, made feature scanning tolerate unreadable legacy event logs, hardened `/api/features` error handling, and marked the scanner regressions as part of the `fast` suite so CI/Sonar coverage reflects the new branches.
- **Narrow exception handlers in doctrine repositories** — Replace 21 bare `except Exception` handlers across `src/doctrine/` with specific exception tuples (`YAMLError`, `ValidationError`, `OSError`, `ModuleNotFoundError`, `TypeError`, `UnicodeDecodeError`) matching actual failure modes. Addresses PR #305 review finding M1.
- **Fix `spec-kitty --help` crash** — Add missing `Optional` import to `workflow.py` and `tasks.py`. `from __future__ import annotations` defers annotation evaluation; Typer's `eval()` of `Optional[str]` annotations raised `NameError` at app construction time.
- **Address PR #305 architectural review gaps in the rebased branch** — resolve the core review findings by removing doctrine→`specify_cli` dependency leakage, bringing doctrine into CI coverage, lifting shared glossary/path primitives into kernel, and documenting the resulting boundary in the architecture corpus.

### Documentation

- **Doctrine inclusion assessment** — `docs/development/doctrine-inclusion-assessment.md` evaluates the current state of the three Doctrine+Kitty merger pillars (agent profiles ~80%, mission type customization ~45%, ad-hoc experimentation ~25%) with gap analysis, dependency violation status, and phased recommendations.
- **Doctrine skills README** — `src/doctrine/skills/README.md` documents the skills-vs-mission-composition boundary, the iterative context loading pattern, and the skill inventory. Captures the architectural distinction from the PR #305 review.
- **Updated skill: spec-kitty-runtime-next** — new "Doctrine-Aware Step Execution" section teaches agents to load agent profiles at init, apply action-scoped constitution context at step boundaries, and pull specific tactics/directives on demand instead of dumping all doctrine upfront.
- **Updated skill: spec-kitty-constitution-doctrine** — new "Programmatic Doctrine Access", "Doctrine Artifact Kinds", and "Iterative Context Loading Pattern" sections document `DoctrineService` entry points, explain all 8 artifact kinds (directives, tactics, paradigms, styleguides, toolguides, procedures, agent profiles, step contracts) with access patterns, and teach the anti-pattern of upfront context dumps.
- **Updated skill: spec-kitty-mission-system** — new "Doctrine Composition Layer" section documents `MissionStepContract`, `Procedure`, and action index artifacts as the structured primitives backing mission behavior.
- **New skill: ad-hoc-profile-load** — teaches agents how to load a profile on demand for interactive sessions outside the mission loop: resolve by ID or task context, adopt identity/boundaries/governance scope, maintain role throughout the session, and persist to tool context.
- **Recorded the remaining follow-on work after the PR #305 -> PR #348 transition** — the compiler-backed mission-bundle follow-up remains relevant, the skills-vs-mission-composition boundary still needs to stay explicit, constitution-local routing should expand beyond mission-path centralization, issue #241 still has compatibility/documentation cleanup left on older `--feature`-based surfaces, and residual runtime/test debt remains outside this rebase-focused integration.

## [3.0.3] - 2026-04-01

### Added

- **Ticket-first mission origin binding** (feature 061): Service-layer workflow for starting a mission from an existing Jira or Linear ticket. Adds `search_origin_candidates()`, `bind_mission_origin()`, and `start_mission_from_ticket()` in `tracker/origin.py`. Persists durable `origin_ticket` provenance in `meta.json` with 7-field validation. Emits `MissionOriginBound` observational telemetry event. SaaS-first write ordering ensures local metadata never runs ahead of the authoritative control plane.
- **Reusable feature-creation API**: Extracted `create_feature_core()` from the CLI command into `core/feature_creation.py` — a stable, programmatic API returning `FeatureCreationResult` with domain exceptions instead of `typer.Exit()`.
- **SaaS tracker client extensions**: `search_issues()` and `bind_mission_origin()` transport methods on `SaaSTrackerClient` with full retry, auth refresh, and error handling.

## [3.0.2] - 2026-04-01

### Fixed

- **Missing prompt-driven slash commands**: `rewrite_agent_shims()` (3.0.0 migration step 6) deleted 9 prompt-driven template files (specify, plan, tasks, etc.) leaving only 7 CLI shims. Now regenerates all 16 command files per the hybrid architecture (feature 058). Added `m_3_0_2` migration to restore prompt files for already-affected projects.
- **Event log not created at feature birth**: `status.events.jsonl` was only bootstrapped during `finalize-tasks`, causing `CanonicalStatusNotFoundError` when the dashboard scanned features in the specify/plan phase. Now initialized when `create-feature` runs.
- **Dashboard scanner crash on pre-finalization features**: `_count_wps_by_lane()` and `_process_wp_file()` propagate `CanonicalStatusNotFoundError` (hard-fail contract); callers `scan_all_features()` and `scan_feature_kanban()` catch at feature level with actionable error messages.
- **Stale `/spec-kitty.clarify` references**: Removed 14 remaining references to the deleted clarify command across kitty-specs checklists, coverage tables, and `pyproject.toml`.
- **Missing `.gitignore` entries**: Added `.kittify/workspaces/` and `.kittify/merge-state.json` to match `state_contract.py` expectations.

## [3.0.1] - 2026-03-31

### Fixed

- **Canonical status hard cutover completed.** Work-package lane state is now consistently sourced from `status.events.jsonl` across active CLI commands, packaged task tooling, templates, docs, and standalone helpers. Frontmatter lane fallbacks and `lane=` body-log writes are removed from active 3.0 flows.
- **Canonical bootstrap and hard-fail behavior hardened.** `finalize-tasks` now seeds canonical `planned` state for generated WPs, while runtime commands fail explicitly when canonical status is missing instead of silently reconstructing it from abandoned frontmatter state.
- **Release automation updated for 3.x.** GitHub release validation, maintainer docs, and workflow tag handling now use semantic `vX.Y.Z` tags generically, so `v3.0.1` publishes correctly to GitHub Releases and PyPI.

## [3.0.0] - 2026-03-30

### Breaking Changes

- **Event log is sole authority for mutable WP state.** Frontmatter `lane`, `review_status`, `reviewed_by`, and `progress` fields are no longer written or read at runtime. Status is read from `status.events.jsonl` via the reducer.
- **`feature_detection.py` deleted.** All commands require explicit `--feature <slug>` in multi-feature repos. No branch scanning, no env var detection, no cwd walking.
- **Legacy worktree file filtering removed.** `planning_artifact` WPs work in-repo; `code_change` WPs use standard full worktrees.
- **Command templates restored as hybrid.** Planning commands (specify, plan, tasks, etc.) install as full prompts; execution commands (implement, review, merge, etc.) install as thin CLI-dispatch shims.

### Added

- **MissionContext** — opaque token-based bound identity for all workflow commands (`src/specify_cli/context/`)
- **WP Ownership Manifest** — `execution_mode`, `owned_files`, `authoritative_surface` per WP (`src/specify_cli/ownership/`)
- **Lane-weighted progress** — `planned=0.0`, `in_progress=0.3`, `for_review=0.6`, `done=1.0` (`src/specify_cli/status/progress.py`)
- **`spec-kitty materialize`** command for CI/debugging regeneration of derived views
- **Dedicated merge workspace** at `.kittify/runtime/merge/` with per-mission state and atomic lock
- **Merge conflict auto-resolution** for event logs (append-merge) and metadata (take-theirs)
- **Thin agent shims** for CLI-driven commands with `spec-kitty agent shim <command>` entrypoints
- **Schema version gate** (disabled until 3.0.0 migration ships to consumers)
- **One-shot migration framework** — `backfill_identity`, `backfill_ownership`, `rebuild_state`, `strip_frontmatter`
- **`--validate-only`** flag on `finalize-tasks`
- **`spec-kitty next`** hint in `tasks status` output
- **Integration Verification** section in WP prompt template
- **Doctor `command-files`** check — detects stale/missing/wrong-type agent command files
- **Version markers** in generated command files (`<!-- spec-kitty-command-version: X.Y.Z -->`)
- **Migration `m_2_1_4`** — unconditionally enforces correct hybrid command file state

### Removed

- `feature_detection.py` (668 lines) — replaced by MissionContext tokens
- `status/legacy_bridge.py`, `status/phase.py`, `status/reconcile.py`, `status/migrate.py`
- `merge/executor.py`, `merge/forecast.py`, `merge/status_resolver.py`
- `core/agent_context.py` — tech-stack parsing no longer needed
- ~56 command template files (replaced by 9 canonical prompts + 7 thin shims)
- Sparse checkout policy enforcement
- Frontmatter lane/review_status read/write throughout codebase
- Dual-write (event log + frontmatter) behavior

### Fixed

- "planning repository" → "project root checkout" terminology (migration included)
- Template path references removed from agent prompts (agents no longer search for `.kittify/missions/` files)
- Workflow `implement`/`review` now emit status events (was silently failing)
- Merge reconciliation marks ALL ancestor WPs as done (not just effective tips)
- `require_explicit_feature()` lists available features in error message
- YAML parse errors in frontmatter now logged as warnings (not silently swallowed)
- Merge engine uses `git reset --hard` on detached HEAD (not `git checkout` which fails when branch is checked out elsewhere)
- Migration backup covers `kitty-specs/` and `.gitignore` (not just `.kittify/`)
- `rebuild_state.py` uses max timestamp (not last file line) for terminal state
- Merge lock uses atomic `open('x')` (not TOCTOU `exists()` + `write_text()`)
- `merge --resume` errors when multiple paused merges exist (not silently picks first)

## [2.1.4] - 2026-03-27

### Added

**Enforce correct command file state**: Version markers and migration to guarantee all agent command files are always in the correct state.

- `<!-- spec-kitty-command-version: X.Y.Z -->` marker added as the first line of every generated command file (both full prompts and thin shims)
- Migration `m_2_1_4_enforce_command_file_state` unconditionally writes all 16 command files per configured agent; idempotent on subsequent runs when version markers match
- `spec-kitty doctor command-files` subcommand checks all agent command files for missing files, stale version markers, and wrong file type (full prompt vs thin shim)

## [2.1.3] - 2026-03-27

### 🐛 Fixed

**Preserve explicit WP args in workflow prompts**: Slash-command arguments passed to `/spec-kitty.implement` and `/spec-kitty.review` are now forwarded into the resolver-first flow instead of being silently dropped. Agents receiving explicit WP selectors (e.g., `WP03`, `--base WP01`) will correctly pass them to `spec-kitty agent context resolve` via `--wp-id` and `--base` flags.

- `implement.md` and `review.md` mission templates now include an `{ARGS}` placeholder with conditional forwarding instructions
- Public slash-command docs updated: `/spec-kitty.implement` documents `[--base WP_ID]` support; `/spec-kitty.review` is now WP-only (removed stale "or prompt path" syntax)
- Regression tests added across Markdown and TOML agent formats to ensure argument placeholders survive rendering

## [2.1.2] - 2026-03-23

### 🔧 Improved

**Skills audit and expansion**: All 6 distributed skills audited, command-verified, and expanded with full architecture documentation. Skills now document internal systems (glossary pipeline, constitution extraction, runtime DAG, git workflow boundary) so agents can operate effectively.

- setup-doctor: Fixed wrong CLI commands (`verify` → `verify-setup`, `status` → `agent tasks status`), added `--remove-orphaned` safety warning
- runtime-review: Added discovery step, `--feature` flags, empty-lane guidance
- glossary-context: Added 5-layer middleware pipeline, extraction methods, checkpoint/resume, step config
- constitution-doctrine: Added extraction rules, governance.yaml schema, interview profiles, answers.yaml schema
- runtime-next: Added decision algorithm, WP iteration logic, 6 guard primitives, agent loop pattern
- orchestrator-api: Added JSON output examples, error code catalog, idempotency behavior, preflight details

### ✨ Added

**2 new skills**: `spec-kitty-mission-system` (explains missions, 4 types, template resolution, guards) and `spec-kitty-git-workflow` (documents Python vs agent git operation boundary).

**Reusable skill update utility**: `src/specify_cli/upgrade/skill_update.py` for finding and patching skill files across all 13 agent skill roots.

**10 upgrade migrations** for consumer projects: 6 skill fixes, 1 release skill removal, 2 new skill installations, 1 glossary skill expansion.

**Documentation parity sprint (Feature 056)**: DocFX build now includes all 4 Divio categories (was only building 1x/ and 2x/). 5 new user guides distilled from skills, 4 existing docs expanded, 22 fact-check corrections across 20 files.

### 🐛 Fixed

**DocFX build gap**: 56 docs files (tutorials, how-to, reference, explanation) were in the repo but excluded from the docs.spec-kitty.ai build. Now included via updated `docfx.json`.

**8-lane state machine documentation**: All docs updated from outdated 4-lane model (planned/doing/for_review/done) to correct 8-lane model (planned/claimed/in_progress/for_review/approved/done/blocked/canceled) with 24 allowed transitions.

**CLI reference completeness**: Added 12 missing commands to cli-commands.md, 7 missing subcommands to agent-subcommands.md. Fixed `spec-kitty sync` (documented as flat command, actually a group with 6 subcommands).

### 🧹 Maintenance

- Removed `release` skill from distribution (spec-kitty development only, not for consumers)
- Removed obsolete `docs/how-to/upgrade-to-0-11-0.md`
- Fixed all cross-reference links in new docs (0 new DocFX build warnings)

## [2.1.1] - 2026-03-21

### 🐛 Fixed

- **Bundled doctrine payload in wheels**: the PyPI wheel now includes the full `doctrine/` package tree, including the canonical skill pack under `doctrine/skills/`, so `spec-kitty init` and `spec-kitty upgrade` can install managed skills for shipped builds.
- **2.1.0 repair migration**: added `2.1.1_repair_skill_pack` so projects that already upgraded on broken `2.1.0` wheels reinstall the canonical managed skill pack on `spec-kitty upgrade`.
- **Release verification guard**: the release workflow now fails if the built wheel omits doctrine files or bundled skills, and distribution tests now assert that a wheel-installed `spec-kitty init` produces the managed skill manifest and installed skill files.

## [2.1.0] - 2026-03-21

### ✅ Added

- **Agent Skills Pack (`#330`)**: added canonical bundled skills, registry/installer/verification flow, manifest support, and upgrade migration `m_2_0_11_install_skills`.
- **Structured requirement mapping (`#329`)**: added requirement-to-work-package mapping support with CLI integration for tracing delivery intent into execution planning.

### 🔧 Changed

- **Deterministic planning branch intent (`#328`)**: `specify` and `plan` commands now inject explicit target-branch metadata into templates to reduce ambiguity in downstream execution.
- **Primary release line promotion**: `2.x` becomes the stable `main` line, with GitHub Releases and PyPI publication starting at `2.1.0`.

### ⚠️ Deprecated

- **`1.x` overall**: the former `1.x` line is now deprecated and moves to `1.x-maintenance` for critical fixes only. No new `1.x` PyPI releases are planned.

### 🗑️ Removed

- **Public `/spec-kitty.clarify` slash command (`#322`)**: removed the legacy clarify command, template, and migration path in favor of the current planning/discovery flow.

## [2.0.11] - 2026-03-20

### 📄 Documentation

- **2.x release metadata refresh**: updated the README's current-release banner so the branch advertises the active GitHub-only 2.x release line instead of the initial `v2.0.0` placeholder.

## [2.0.10] - 2026-03-20

### ✅ Added

- **Project-level `auto_commit` setting (`#321`)**: repos can now configure automatic commit behavior directly in project config.
- **Sync queue resilience and diagnostics (`#320`)**: offline queue now supports FIFO eviction, coalescing, configurable caps, and sync doctor coverage for failure recovery.

### 🐛 Fixed

- **Merge target resolution (`#272`)**: merge target branch is now resolved from feature `meta.json`, preventing merges from targeting the wrong branch.
- **Acceptance and state persistence hardening (`#319`)**: state writes are now centralized around canonical metadata/state handling to reduce drift across acceptance, mission, and status flows.
- **Feature context fallback restored**: ambiguous agent/task resolution now falls back to the latest incomplete feature instead of stopping on a stale explicit-selection error.
- **Upgrade downgrade protection**: `spec-kitty upgrade` now refuses older targets instead of silently rewriting project metadata backwards.
- **Migration discovery fail-fast**: broken `m_*.py` modules now fail discovery immediately instead of being skipped with a stderr warning.
- **Upgrade metadata durability**: successful and failed migration records are now persisted immediately so retries can resume from an accurate state after mid-run failures.
- **Safe auto-commit stash isolation**: `safe_commit()` now restores only the stash entry it created, preventing unrelated user stashes from being popped during upgrade/status auto-commits.
- **Embedded task script compatibility**: copied `.kittify/scripts/tasks` helpers now fall back cleanly when the host `specify_cli` install is older than the copied templates.

### 🔧 Changed

- **State architecture cleanup phase 2 (`#319`)**: consolidated atomic-write and state-contract handling across runtime, acceptance, and feature metadata paths.
- **Test and quality isolation follow-ups**: retained the refactors that separated policy/test churn from release-critical behavior on the 2.x line.

## [2.0.9] - 2026-03-15

### ✅ Added

- **Mutation testing CI integration (feat #047)**: mutmut toolchain setup, CI integration, and targeted kill sessions for `status/` reducer and transitions.
- **Agentic mutation testing remediation workflow**: GitHub Agentic Workflow (gh-aw) replaces the legacy Claude workflow for mutation testing remediation.
- **SonarCloud integration**: added SonarCloud config; `develop` branch recognized as 2.x-equivalent in CI quality gates.
- **Architecture corpus restructure**: versioned architecture docs under `architecture/1.x/` and `architecture/2.x/`, 45 ADRs, glossary contexts across 10 bounded domains, Contextive integration, and stakeholder persona definitions.
- **`meta.json` schema example in specify template**: documents `"target_branch"` and `"vcs"` as required explicit fields.

### 🐛 Fixed

- **Post-rebase quality fixes**: resolved unmatched `)` syntax error, `gap_analysis_path` undefined name (F821), `timezone` → `UTC` reference, unused `type: ignore` comments, and `toml` import-untyped mypy errors.
- **Test isolation**: moved misplaced test package; fixed 3 test failures and Pydantic V1 deprecation warnings.
- **Sync offline queue**: redirect offline queue warning to stderr instead of stdout.
- **CI branch detection**: `develop` now recognized as a 2.x branch for branch-contract guards.

### 🔧 Changed

- **Ruff lint compliance**: full ruff clean pass across `src/` and `tests/`; added ruff lint config to `pyproject.toml`.
- **Documentation site updates**: 2.x docs site refresh with Contextive IDE integration guide.
- **Test suite restructuring**: migrated to vertical-slice layout; redesigned CI quality workflow; annotated suite with fast/slow/git_repo markers; deleted tests/legacy/ after extracting unique behaviours.

## [2.0.8] - 2026-03-11

### 🐛 Fixed

- **Dashboard approved lane**: WPs with `lane: "approved"` no longer silently fall back to the "planned" column. Added "Approved" as a 5th kanban column between For Review and Done, with `claimed`→planned and `in_progress`→doing lane normalization in the scanner.
- **Slim FEATURE_CONTEXT_UNRESOLVED payload**: reduced error payload size for LLM consumption to stay within agent context budgets.

## [2.0.7] - 2026-03-11

### ✅ Added

- **Mutation testing CI integration (feat #047)**: mutmut toolchain setup, CI integration, and targeted kill sessions for `status/` reducer and transitions (#275).
- **Agentic mutation testing remediation workflow**: GitHub Agentic Workflow (gh-aw) replaces the legacy Claude workflow for mutation testing remediation.
- **SonarCloud integration**: added SonarCloud config; `develop` branch recognized as 2.x-equivalent in CI quality gates.
- **Architecture corpus restructure**: versioned architecture docs under `architecture/1.x/` and `architecture/2.x/`, 45 ADRs, glossary contexts across 10 bounded domains, Contextive integration, and stakeholder persona definitions.
- **Google Antigravity as first-class agent (#266)**: added Google Antigravity to the supported agent roster with directory, templates, and migration coverage.
- **Commands own workflow context (#261)**: commands now carry their own workflow context rather than relying on ambient state.
- **Tracker snapshot publish payload (feat #048)**: resource routing in publish path (WP01) and batch API contract for tracker snapshot publish (WP02).

### 🐛 Fixed

- **Stale overrides from upgrade version-skew (#285)**: `classify_asset()` now compares project `.kittify/` files against immutable package-bundled defaults (`get_package_asset_root()`) instead of the mutable `~/.kittify/` directory. This prevents old managed templates from being misclassified as user customizations and permanently shadowing newer templates in `.kittify/overrides/` during upgrades.
- **New `SUPERSEDED` disposition**: managed files that differ from the current package default are now correctly classified as `SUPERSEDED` (removed) rather than `CUSTOMIZED` (moved to overrides). Only files with no package counterpart are treated as genuine user customizations.
- **Repair migration for already-affected users**: new `2.0.7_fix_stale_overrides` migration scans `.kittify/overrides/` for files byte-identical to current package defaults and removes them. Genuine user customizations are preserved.
- **Constitution: resolve_doctrine_root fallback for pip-installed users (#278)**: `resolve_doctrine_root()` no longer crashes when the `doctrine` package directory is missing from pip wheels; falls back to `specify_cli` package root.
- **Merge: worktree/branch cleanup when feature is already integrated (#271)**: `spec-kitty merge` now runs worktree removal and branch deletion when all WP branches are already merged, instead of exiting with "Nothing to merge" and leaving cleanup to the user.
- **Post-rebase quality fixes (#273)**: resolved unmatched `)` syntax error, `gap_analysis_path` undefined name (F821), `timezone` → `UTC` reference, unused `type: ignore` comments, and `toml` import-untyped mypy errors.
- **Test isolation**: moved misplaced test package; fixed 3 test failures and Pydantic V1 deprecation warnings.
- **Sync offline queue**: redirect offline queue warning to stderr instead of stdout.
- **CI branch detection**: `develop` now recognized as a 2.x branch for branch-contract guards.
- **Tracker publish path normalization (feat #048)**: normalize provider in publish path and document auth token resolution.

### 🔧 Changed

- **Ruff lint compliance**: full ruff clean pass across `src/` and `tests/`; added ruff lint config to `pyproject.toml`.
- **Documentation site updates**: 2.x docs site refresh with Contextive IDE integration guide.

## [2.0.6] - 2026-03-10

### 🐛 Fixed

- **Upgrade consistency sweep**: added a new `2.0.6_consistency_sweep` migration that backfills missing or blank feature `meta.json`, infers `target_branch` from feature docs or the repo primary branch, reconstructs missing `status.events.jsonl`, regenerates `status.json` and generated `tasks.md` status blocks, normalizes legacy WP frontmatter lane aliases/quoting, rewrites stale prompt paths, and archives orphan empty `status.json` snapshots before rebuilding canonical state.
- **Worktree upgrade coverage**: `spec-kitty upgrade` now upgrades worktrees that have `kitty-specs/` or legacy `.specify/` state even when `.kittify/` has not been created yet.
- **Detector false positives**: runtime-managed 2.x installs no longer trip legacy project-local mission migrations, and the constitution migration only flags the legacy `.kittify/memory/constitution.md` path.
- **Target-branch backfill correctness**: the `0.13.8_target_branch` migration now uses repo-aware branch inference instead of the obsolete hardcoded Feature 025 exception.

## [2.0.5] - 2026-03-10

### ✅ Added

- **Namespace-aware artifact body sync (Feature 047)**: Full offline-first pipeline for pushing spec artifact bodies (markdown content) to the SaaS backend, including `NamespaceRef` typed identifiers, `OfflineBodyUploadQueue` SQLite persistence, body upload preparation and filtering, HTTP transport with response classification, dossier pipeline orchestration with partial failure handling, background sync queue drain, and end-to-end diagnostics/logging.

### 🐛 Fixed

- **Init default directory (`#258`)**: `spec-kitty init` now defaults to the current directory when project name is omitted on the 2.x line.
- **Sync integration**: Completed namespace artifact body sync wiring for end-to-end operation.

### 📄 Documentation

- **Connector auth binding ADR**: Added architectural decision record for connector authentication binding and installation model gap analysis.
- **Command-owned action context ADR**: Defined command-owned action context pattern.

## [2.0.4] - 2026-03-06

### 🐛 Fixed

- **Upgrade JSON machine-parseability hardening (`#254`)**: `spec-kitty upgrade --json` now emits raw JSON output without Rich console wrapping.
- **Upgrade migration status consistency (`#256`)**: non-applicable migrations are reported as `skipped` instead of incorrectly marked as applied.

### 🔧 Changed

- **Contract hardening closeout (`#213`-`#218`)**: merged deterministic branch/runtime contracts, typed artifact-path payloads, merge/preflight JSON enrichment, and banner suppression in agent contexts.
- **Codex/Copilot slash-flow reliability (`#128`)**: integrated slash-command output stability improvements via deterministic JSON/banners/template alignment.
- **Worktree/preflight stability (`#226`)**: released preflight and command-contract hardening on the 2.x line for end-to-end spec→implement→review runs.

## [2.0.2] - 2026-02-27

### ✅ Added

- **Flag-gated tracker command group**: added `spec-kitty tracker ...` commands behind `SPEC_KITTY_ENABLE_SAAS_SYNC`, including provider listing, bind/unbind, mapping, local sync pull/push/run, and snapshot publish.
- **Tracker host-local persistence + credentials support**: added CLI-owned tracker SQLite cache/checkpoints and provider credential handling consistent with existing Spec Kitty host persistence patterns.

### 🔧 Changed

- **Dependency floor hardening for 2.x installs**: added explicit lower bounds for previously unbounded core CLI direct dependencies to reduce resolver drift in fresh environments.
- **Workflow review lane guard**: review start now requires a valid `for_review` lane state before progressing.

## [2.0.1] - 2026-02-26

### 🐛 Fixed

- **Main bias fix**: `resolve_primary_branch()` now checks the current branch before the hardcoded `[main, master, develop]` list. Repos on non-standard primary branches (e.g., `2.x`) no longer get blocked by `spec-kitty specify`.
- `create_feature()` records the current branch as `target_branch` in `meta.json` instead of guessing via heuristics. Added `--target-branch` CLI option for explicit override.
- `guards.py` uses `resolve_primary_branch()` instead of hardcoded `{"main", "master"}` set.
- `merge-feature --target` auto-detects from `meta.json` when not specified.
- Template references to "main" replaced with "target branch" throughout command templates.

### 🔧 Changed

- **Dashboard `--open` flag**: Browser auto-open is now disabled by default. Pass `--open` to open the dashboard URL in your browser. Prevents browser windows from spawning during tests or CI.
- Consolidated 3 ad-hoc branch-check functions into `_show_branch_context()` for consistent branch banners across all planning commands.

## [2.0.0] - 2026-02-22

### 🔧 Changed

- Start semantic versioning for `2.x` GitHub-only releases using `v2.<minor>.<patch>` tags.
- `2.x` release automation now publishes GitHub Releases only (no PyPI publish step).

### 🐛 Fixed

- `spec-kitty next` no longer short-circuits `--result failed|blocked` in the CLI bridge; both now flow through `spec-kitty-runtime` `next_step(...)`, preserving canonical runtime lifecycle behavior and run metadata.
- Runtime mission template selection for `next` now follows deterministic precedence tiers (`explicit`, `env`, `project override`, `project legacy`, `user global`, `project config`, `builtin`) when resolving `mission-runtime.yaml`.
- `--answer --json` integration coverage now exercises a real pending-decision success path (runtime `requires_inputs`) instead of fake decision IDs.
- Added replay-parity integration coverage in `spec-kitty` against `spec-kitty-events` canonical fixture stream (`mission-next-replay-full-lifecycle`).
- **WP prompt tracking reliability**: removed stale `kitty-specs/**/tasks/*.md` from tracked `.gitignore`, migrated existing projects away from that rule, and hardened workflow status commits to fail loudly if claim commits cannot be written.

## [2.0.0a5] - 2026-02-14

### 🐛 Fixed

**Backported orchestrator deadlock fixes from v0.15.3**:

- **Orchestrator deadlock**: Fixed false "No progress possible" detection when WP tasks raise exceptions or complete but leave WPs in intermediate states (IMPLEMENTATION/REVIEW). The orchestrator now properly marks failed WPs as FAILED and restarts orphaned WPs, preventing deadlock cascades. (Backport of #137 by @tannn)
- **Exception handling**: Task exceptions now properly mark WPs as FAILED with error details, allowing dependent WPs to recognize failure instead of blocking indefinitely
- **WP restart logic**: Added restart counter to prevent infinite restart loops if WP repeatedly fails to advance state. Restarts are now capped at `max_retries` (default: 3)
- **State recovery**: Improved detection of interrupted implementations (IMPLEMENTATION status without `implementation_completed` timestamp) to automatically reset and retry

### 🧹 Maintenance

- **Test coverage**: Added 8 new orchestrator tests covering exception handling, restart scenarios, deadlock detection, and state persistence
- **Test quality**: Reorganized test suite with proper markers (`@pytest.mark.orchestrator_exception_handling`, `@pytest.mark.orchestrator_deadlock_detection`) and class grouping following project conventions

## [2.0.0a4] - 2026-02-13

### 🐛 Fixed

**Backported v0.15.2 hotfix from main branch**:

- **Branch detection**: Replaced single `rev-parse --abbrev-ref HEAD` with dual-strategy
  approach (`git branch --show-current` primary, `rev-parse` fallback). Fixes unborn branch
  detection and detached HEAD handling. Updated all inline callers in tasks.py, workflow.py,
  and vcs/git.py.

- **Subprocess encoding safety**: Added `encoding="utf-8", errors="replace"` to all ~135
  `subprocess.run(text=True)` calls across 36 files. Prevents crashes on non-UTF-8 git output (Windows, locale mismatches).

- **Pre-commit hook safety**: Removed `set -e` from encoding check hook, expanded Python
  interpreter detection (loops through python3/python/py with smoke test), fixed exit code
  handling to distinguish encoding errors (exit 2) from execution failures.

- **Init fail-fast**: `spec-kitty init` now raises RuntimeError immediately after git init
  failure instead of falling through to "project ready" success message.

- **PowerShell templates**: Added PowerShell equivalent blocks to implement.md templates
  for software-dev, research, and documentation missions.

## [2.0.0a3] - 2026-02-11

### 🐛 Fixed

**Complete Bug #119 cherry-pick**:
- Fixed missing update to `scripts/tasks/acceptance_support.py` (root-level test helper)
- This file was missed in the original Bug #119 cherry-pick, causing test failures
- Now all acceptance_support.py copies correctly exclude 'done' lane from assignee requirement

## [2.0.0a2] - 2026-02-11

### 🐛 Fixed

**Cherry-picked 7 critical bug fixes from v0.15.0 (main branch)**:

- **Bug #95**: Enforce kebab-case validation for feature slugs
  - Rejects slugs with spaces, underscores, uppercase, or leading numbers
  - Prevents invalid directory structures and broken workflow commands
  - Added 8 comprehensive validation tests

- **Bug #120**: Use local git exclude for worktree ignores
  - Worktree-specific ignores now written to `.git/info/exclude` instead of `.gitignore`
  - Prevents `.gitignore` pollution when merging worktrees
  - VCS abstraction layer handles legacy worktree filtering consistently

- **Bug #117**: Improve dashboard lifecycle and error diagnostics
  - Dashboard process detection no longer reports false failures
  - Distinguishes between health check timeout (process running) vs actual failure
  - Provides specific error messages for missing metadata, port conflicts, permission errors

- **Bug #124**: Unify branch resolution, stop implicit master fallback
  - Respects user's current branch instead of auto-checkout
  - Shows notification when current branch differs from feature target
  - No more surprise checkouts during `spec-kitty implement` or `move-task`
  - Consistent branch resolution across all commands

- **Bug #119**: Relax strict assignee gate in acceptance validation
  - Assignee now optional for completed work packages in 'done' lane
  - Strict validation still enforces assignee for 'doing' and 'for_review'
  - Required fields (lane, agent, shell_pid) still mandatory

- **Bug #122**: Prevent staged files from leaking into status commits
  - New `safe_commit()` helper explicitly stages only intended files
  - Status commits no longer capture unrelated staged changes
  - Preserves user's staging area across workflow operations

- **Bug #123**: Call lane transition before status update (atomic state)
  - Lane transitions now happen BEFORE internal state updates
  - Prevents inconsistent state when operations fail mid-transition
  - Applies to orchestrator implementation and review phases

All fixes include comprehensive test coverage (54+ new tests) and maintain backward compatibility.

## [0.13.26] - 2026-02-04

### 🛠️ Refactored

**Consolidated workflow implement workspace creation**:
- `spec-kitty agent workflow implement` now delegates workspace creation to `spec-kitty implement` when needed
- Removes duplicated worktree setup in the agent command
- Prevents agents from creating worktrees from inside another worktree

### 🐛 Fixed

**Clearer recovery guidance for multi-parent merge failures**:
- When auto-merge fails, instructions now show concrete recovery steps
- Explicitly warns there is no `spec-kitty agent workflow merge` command
- Points agents to the correct `spec-kitty agent feature merge` command

## [0.13.25] - 2026-02-04

### 🐛 Fixed

**`spec-kitty upgrade` not bumping version when no migrations needed**:
- When `spec-kitty upgrade` found no applicable migrations, it returned early without updating the version in `.kittify/metadata.yaml`
- This left the project stuck at its old version (e.g., 0.13.21) even though the CLI was newer (0.13.24)
- The dashboard then blocked with a version mismatch error
- Fixed both `upgrade.py` (CLI command path) and `runner.py` (programmatic path) to stamp the version even when no migrations are needed

## [0.13.24] - 2026-02-04

### 🔧 Improved

**Review workflow shows git context for reviewers**:
- `spec-kitty agent workflow review` now displays the WP's branch name, base branch, and commit count
- Reviewers see exactly which commits belong to the WP vs inherited history
- Provides ready-to-use `git log <base>..HEAD` and `git diff <base>..HEAD` commands
- Base branch auto-detected from WP dependencies (tries dependency branches first, then main/2.x)
- Prevents reviewers from accidentally diffing against the wrong base (e.g., `main` instead of `2.x`)

## [0.13.20] - 2026-01-30

### 🐛 Fixed

**Merged Single-Parent Dependency Workflow Gap** (ADR-18):
- Fixed `spec-kitty implement` failing when single-parent dependency has been merged to target branch
- Issue: WP01 merged to 2.x → WP02 can't implement (looks for non-existent WP01 workspace branch)
- Root cause: Implement command didn't distinguish between in-progress vs merged dependencies
- Solution: Auto-detect when dependency lane is "done" and branch from target branch instead
- Behavior:
  - If `base_wp.lane == "done"`: Branch from target branch (e.g., 2.x) - merged work already there
  - If `base_wp.lane != "done"`: Branch from workspace branch (e.g., 025-feature-WP01) - work in progress
- Eliminates need for manual frontmatter editing (remove dependencies, update base_branch)
- Complements ADR-15 (multi-parent all-done suggestion) for single-parent case
- **Impact**: Critical fix for normal workspace-per-WP workflow where dependencies complete before dependents start
- **Technical Story**: Feature 025-cli-event-log-integration WP02/WP08 blocked on merged WP01

## [0.13.7] - 2026-01-27

### 🐛 Fixed

**Activity Log Parser Failing on Hyphenated Agent Names** ([#111](https://github.com/Priivacy-ai/spec-kitty/pull/111)):
- Fixed `activity_entries()` regex in `tasks_support.py` to handle hyphenated agent names
- Parser was using `[^–-]+?` pattern which treated hyphens as field separators
- Agent names like `cursor-agent`, `claude-reviewer`, `cursor-reviewer` now parse correctly
- Acceptance validation no longer fails with "Activity Log missing entry for lane=done" for hyphenated agents
- Changed pattern to `\S+(?:\s+\S+)*?` (matches non-whitespace), aligning with `task_helpers.py`
- Added comprehensive test suite with 11 test cases covering hyphenated names, backward compatibility, and edge cases
- **Contributors**: Rodrigo D. L. (bruj0)

**Workflow Completion Instructions Missing Git Commit Step** ([#104](https://github.com/Priivacy-ai/spec-kitty/pull/104)):
- Fixed agents not committing implementation files before marking tasks done
- Issue caused cascading failures where dependent work packages started from empty branches
  - WP02 worktree had HTML + CSS ✅
  - WP03 worktree had HTML only (missing WP02's CSS) ❌
  - WP04 worktree had HTML only (missing CSS and JS from WP02 and WP03) ❌
- Root cause: "WHEN YOU'RE DONE" instructions in `workflow implement` command didn't include git commit step
- Fix: Added explicit git commit instruction as step 1 in completion checklist
- Updated both in-prompt instructions (shown twice) and terminal output summary
- Added warning: "The move-task command will FAIL if you have uncommitted changes! Commit all implementation files BEFORE moving to for_review. Dependent work packages need your committed changes."
- **Impact**: Critical fix for multi-agent parallel development workflows using workspace-per-WP model (v0.11.0+)
- **Contributors**: Jerome Lacube

**Dashboard Command Template Generating Python Code Instead of Running CLI** ([#94](https://github.com/Priivacy-ai/spec-kitty/issues/94), [#99](https://github.com/Priivacy-ai/spec-kitty/pull/99)):
- Fixed `/spec-kitty.dashboard` command template to use `spec-kitty dashboard` CLI command
- Removed outdated Python code that manually checked dashboard status and opened browsers
- Dashboard now properly:
  - Starts automatically if not running
  - Opens in default browser
  - Handles worktree detection automatically
- Updated all three dashboard template files:
  - `.kittify/missions/software-dev/command-templates/dashboard.md`
  - `src/specify_cli/missions/software-dev/command-templates/dashboard.md`
  - `src/specify_cli/templates/command-templates/dashboard.md`
- Reduced template code from ~264 lines to ~47 lines
- **Contributors**: Jerome Lacube

## [0.13.6] - 2026-01-27

### 🐛 Fixed

**Critical JSON Mode Corruption Fix** (Release Blocker):
- Fixed JSON output corruption in `spec-kitty implement --json` mode (GitHub Issue #72 follow-up)
  - **Bug**: Warning messages from empty branch detection were written to stdout, corrupting JSON output
  - **Impact**: Automated workflows using `--json` flag would fail with JSON parse errors
  - **Fix**: Changed warning messages to use `file=sys.stderr` to separate warnings from JSON output
  - **File**: `src/specify_cli/core/multi_parent_merge.py:142-144`
  - **Tests**: Updated 5 tests in `test_multi_parent_merge_empty_branches.py` to check stderr instead of stdout

**Missing Migration Fix** (Existing Users Affected):
- Fixed missing migration for commit workflow section (GitHub Issue #72 follow-up)
  - **Bug**: New projects got commit workflow section in implement.md, but existing projects didn't after upgrade
  - **Impact**: Existing users remained vulnerable to agents forgetting to commit work
  - **Fix**: Created migration `m_0_13_5_add_commit_workflow_to_templates.py` to update all agent templates
  - **Coverage**: Updates both software-dev and documentation mission templates for all 12 agents
  - **Migration**: Automatically runs on `spec-kitty upgrade` for projects missing commit workflow

**Subprocess Error Handling** (Defensive Programming):
- Added timeout and error handling to multi-parent merge git commands
  - **Bug**: Git commands in empty branch detection lacked timeout parameters and try/except blocks
  - **Impact**: Function could hang forever or crash on git errors (corrupted repo, permission issues)
  - **Fix**: Added 10-second timeouts and exception handling to all git subprocess calls
  - **File**: `src/specify_cli/core/multi_parent_merge.py:117-144`
  - **Errors handled**: TimeoutExpired (>10s git commands), general exceptions with warning

### Added

- Git commit validation for "done" status transitions - prevents completing WPs with uncommitted changes
- Empty branch detection in merge-base creation - warns when dependencies have no commits
- Git commit workflow section in documentation mission template (consistency with software-dev/research)
- Comprehensive troubleshooting guide for empty branch recovery in the legacy workspace-model documentation
- Migration to add commit workflow section to existing projects (`m_0_13_5_add_commit_workflow_to_templates.py`)

### Changed

- `move-task --to done` now validates git status (same checks as "for_review")
- Use `--force` flag to bypass validation (not recommended)
- Warning messages in multi-parent merge now output to stderr instead of stdout (preserves JSON output integrity)

### Fixed (Non-Critical)

- WP agents can no longer mark tasks as "done" without committing implementation files
- Multi-parent merge-bases no longer silently accept empty dependency branches
- Documentation mission now instructs agents to commit work before review
- Stale WP detection now correctly detects default branch name (main/master/develop) instead of hardcoding "main"
  - **Bug**: Fresh worktrees incorrectly flagged as stale when repository used non-standard default branch
  - **Root Cause**: Code hardcoded "main" as default branch; when `git merge-base HEAD main` failed, it fell through to using parent branch's old commit timestamp
  - **Fix**: Added `get_default_branch()` helper to dynamically detect default branch via origin HEAD or local branch existence
  - **Impact**: Prevents false staleness warnings for fresh worktrees in repos using "master", "develop", or other default branches

## [0.13.5] - 2026-01-26

### 🐛 Fixed

**Fixed /spec-kitty.clarify Command Template**:
- Fixed broken placeholder in clarify template that prevented agents from running clarification workflow
  - **Bug**: Template contained `(Missing script command for sh)` placeholder instead of actual command
  - **Impact**: Agents couldn't get feature context, invented non-existent commands like `spec-kitty agent feature get-active --json`
  - **Fix**: Replaced manual detection logic with `spec-kitty agent feature check-prerequisites --json --paths-only`
  - **Consistency**: Now matches pattern used in specify.md, plan.md, and tasks.md templates
  - Migration `m_0_13_5_fix_clarify_template.py` automatically updates all 12 agent directories on upgrade
  - Source template: `src/specify_cli/missions/software-dev/command-templates/clarify.md`

**Testing**:
- Added comprehensive test suite with 34 tests covering all scenarios
  - Parametrized tests for all 12 agents (claude, copilot, gemini, cursor, qwen, opencode, windsurf, codex, kilocode, auggie, roo, q)
  - Tests for detection, application, agent config respect, idempotency, dry-run
  - Template content validation (ensures no broken placeholders, matches tasks.md pattern)
  - End-to-end integration test verifying migration actually runs and fixes templates

## [0.13.4] - 2026-01-26

### 🐛 Fixed

**Critical Dependency Validation Fix**:
- Fixed `spec-kitty agent workflow implement` not validating WP dependencies before creating workspaces
  - **Bug**: WP with single dependency could create workspace without `--base` flag
  - **Impact**: Workspace branched from main instead of dependency branch (silent correctness bug)
  - **Fix**: Added shared validation utility that errors when single dependency but no `--base` provided
  - **Example**: `WP06` depends on `WP04` → command now errors and suggests `--base WP04`
  - Created `src/specify_cli/core/implement_validation.py` with `validate_and_resolve_base()`
  - Agent commands now delegate to top-level commands (no more legacy script calls)

**Fixed Broken Agent Commands**:
- Fixed `spec-kitty agent feature accept` calling non-existent `scripts/tasks/tasks_cli.py`
  - Now delegates to top-level `accept()` command
- Fixed `spec-kitty agent feature merge` calling non-existent `scripts/tasks/tasks_cli.py`
  - Now delegates to top-level `merge()` command
  - Parameter mapping: `keep_branch` → `delete_branch` (inverted logic)

**Critical Merge Workflow Fix**:
- Fixed merge failing when main branch lacks upstream tracking (Issue reported post-0.13.2 release)
  - 0.13.2 only checked if remote EXISTS, but not if branch TRACKS it
  - Added `has_tracking_branch()` function to check upstream tracking
  - Merge now skips pull if: (1) no remote OR (2) no upstream tracking
  - Affects users with local-only repos or repos where main doesn't track origin/main

**Testing & Prevention**:
- Added 22 new tests for dependency validation and agent command wrappers
  - Unit tests: `test_implement_validation.py` (11 tests)
  - Integration tests: `test_agent_command_wrappers.py` (11 tests)
- Added `TestMigrationRegistryCompleteness` test (prevents 0.13.2-style release blocker)
  - Verifies all `m_*.py` migration files are imported in `__init__.py`
  - Prevents silent bugs where migrations exist but never run
- Added integration tests for merge with untracked branches
- Added unit tests for `has_tracking_branch()` function

**Documentation**:
- Added `src/specify_cli/cli/commands/agent/README.md` (wrapper pattern documentation)
  - Dependency validation best practices
  - Parameter mapping guidelines
  - Common pitfalls and examples
- Updated RELEASE_CHECKLIST.md with mandatory migration registry verification

## [0.13.2] - 2026-01-26

### 🐛 Fixed

**Critical Windows Compatibility Issues**:
- Fixed UTF-8 encoding errors causing Windows crashes (Issue #101)
  - Added `encoding='utf-8'` to all `write_text()` and `read_text()` calls
  - Affected files: feature.py, worktree.py, agent_context.py, doc_generators.py, gap_analysis.py
  - Completes PR #100 which missed several locations
- Fixed hardcoded `python3` breaking Windows installations (Issue #105)
  - Replaced with `sys.executable` in Python code (feature.py)
  - Added dynamic Python detection in git hooks (tries python3, falls back to python)
  - Windows users no longer need to create python3 hardlinks/aliases

**Workflow Improvements**:
- Added `--base` parameter to `spec-kitty agent workflow implement` (Issue #96)
  - Enables agents to create dependent WP worktrees via workflow command
  - Provides feature parity with top-level `spec-kitty implement` command
  - Example: `spec-kitty agent workflow implement WP02 --base WP01 --agent claude`

**Template and Documentation Fixes**:
- Fixed broken `/spec-kitty.clarify` skill (Issue #106)
  - Removed unresolved `{SCRIPT}` and `{ARGS}` placeholders
  - Replaced with auto-detection instructions for feature paths
- Fixed outdated template path references (Issue #102)
  - Updated 6 references from `.kittify/templates/` to `src/specify_cli/missions/`
  - Templates now reference correct bundled locations
- Fixed upgrade version detection for modern projects (Issue #108)
  - Added detection for versions 0.7.0-0.13.0
  - Prevents unnecessary migrations on modern projects
- Regenerated all 12 agent constitution templates (Issue #97)
  - All agents now correctly suggest `/spec-kitty.specify` as next step (not `/spec-kitty.plan`)

### 📚 Documentation

- Added GitHub CLI authentication troubleshooting to CLAUDE.md
  - Documents `unset GITHUB_TOKEN` technique for organization repos

**Issues Closed**: #96, #97, #101, #102, #105, #106, #108, #103 (not a bug), #107 (not a bug)

## [0.13.1] - 2026-01-25

### ✨ Added

**Adversarial Test Suite for 0.13.0 Release**:
- **Distribution tests**: Validate PyPI user experience without SPEC_KITTY_TEMPLATE_ROOT bypass (prevents 0.10.8-style packaging failures)
- **Path validation security tests**: Test directory traversal, symlink attacks, case-sensitivity bypasses, and path injection prevention
- **CSV schema attack tests**: Validate handling of formula injection, encoding errors, duplicate columns, and empty files
- **Git state detection tests**: Verify accuracy of uncommitted work, merge state, and branch divergence detection
- **Migration robustness tests**: Test UTF-8 encoding, idempotency, and partial/corrupted file handling
- **Multi-parent merge tests**: Validate dependency-order merging and conflict resolution
- **Context & config tests**: Test non-interactive modes, agent configuration, and workspace validation

**Test Infrastructure**:
- New `tests/adversarial/` directory with shared fixtures and attack vectors
- `@pytest.mark.distribution` and `@pytest.mark.slow` markers for CI optimization
- Session-scoped `wheel_install` fixture for efficient testing
- Platform-specific skip conditions for cross-platform compatibility

### 📚 Documentation

**Testing**:
- Comprehensive adversarial test documentation in feature 024 spec
- Attack vector catalog with prevention strategies
- CI integration guidance for slow/distribution tests

## [0.13.0] - 2026-01-25

### ✨ Added

**Deterministic CSV Schema Enforcement for Research Missions**:
- **Canonical schema documentation**: Research CSV schemas now documented in all 12 agent implement.md templates
- **Two schemas enforced**:
  - `evidence-log.csv`: `timestamp,source_type,citation,key_finding,confidence,notes`
  - `source-register.csv`: `source_id,citation,url,accessed_date,relevance,status`
- **Schema visibility**: Agents see schemas before editing (in "Research CSV Schemas" section with examples)
- **Detection migration**: `m_0_13_0_research_csv_schema_check.py` scans existing features for schema mismatches (informational only, no auto-fix)
- **Template propagation**: `m_0_13_0_update_research_implement_templates.py` updates all agent templates with schema documentation
- **Reusable validator**: `src/specify_cli/validators/csv_schema.py` provides `CSVSchemaValidation` dataclass for exact schema matching
- **Exported constants**: `EVIDENCE_REQUIRED_COLUMNS` and `SOURCE_REGISTER_REQUIRED_COLUMNS` now importable from `research.py`
- **ADR #8**: Documents architecture decision for documentation-based enforcement vs runtime enforcement/auto-migration

**Problem Solved**: Agents were modifying CSV schemas during implementation, creating different schemas in parallel WPs, causing merge conflicts and validation failures at review time.

**Solution Approach**: Document schemas where agents can see them (prevention) rather than runtime enforcement or auto-migration (data loss risk).

**Fully Non-Interactive Init Support**:
- Added `--non-interactive` / `--yes` and `SPEC_KITTY_NON_INTERACTIVE` to disable prompts
- Added `--agent-strategy`, `--preferred-implementer`, and `--preferred-reviewer` to expose all selection options via CLI
- Non-interactive mode now avoids arrow-key menus and requires `--force` for non-empty `--here` directories
- Updated documentation for automation and CI usage

### 🐛 Fixed

**Windows UTF-8 Encoding Crashes**:
- Fixed all `write_text()` calls to include `encoding='utf-8'` parameter
- Affects feature creation, worktree setup, gap analysis, doc generators, agent context, and test fixtures
- Windows users can now create features without charmap encoding errors
- Fixes #101, incorporates PR #100

**Constitution Template Workflow**:
- Fixed incorrect next-step suggestion after creating constitution
- Now correctly suggests `/spec-kitty.specify` instead of `/spec-kitty.plan`
- Propagated fix to all 12 agent directories via migration
- Fixes #97 (inspired by PR #98)

**Research Mission Detection**:
- Fixed `spec-kitty mission current` to show feature-level missions
- Now auto-detects feature from current directory (kitty-specs or worktree)
- Added `--feature` flag for explicit feature specification
- No longer always defaults to software-dev for research features
- Fixes #93

### 🎉 Closed

**Agent Configuration Feature**:
- Closed #51 as completed (already implemented in v0.12.0)
- Feature: `spec-kitty agent config add/remove/list`

### 📚 Documentation

**Release Management**:
- Added `RELEASE_CHECKLIST.md` - Comprehensive release preparation checklist with version-specific sections for research missions, agent management, and workspace-per-WP changes

### Migration Notes

**For users with existing research features**:
1. Run `spec-kitty upgrade` to trigger detection migration
2. See informational report with schema diffs and migration tips
3. Use LLM agent to help migrate data:
   - Read canonical schema in `.claude/commands/spec-kitty.implement.md`
   - Create new CSV with correct headers
   - Map old columns → new columns
   - Replace old file and commit to main

**For new research features (0.13.0+)**:
- Templates already have correct schemas
- Agents see schema documentation before editing
- Follow append-only pattern to avoid overwrites
- Validation passes at review

## [0.12.1] - 2026-01-24

### 🐛 Fixed

**kitty-specs/ in .gitignore Blocking Feature Creation**:
- Fixed issue where users with `kitty-specs/` in their `.gitignore` couldn't create features
- Error manifested as: "Issue Detected: The spec-kitty agent feature create-feature command failed to commit because .gitignore contains kitty-specs/"
- New migration `m_0_12_1_remove_kitty_specs_from_gitignore` automatically removes blocking entries
- Only removes patterns that block the entire `kitty-specs/` directory
- Preserves worktree-specific patterns like `kitty-specs/**/tasks/*.md` (used to prevent merge conflicts)

### Migration Notes

**For users experiencing this bug:**
1. Run `spec-kitty upgrade` to apply the fix automatically
2. Or manually remove `kitty-specs/` from your `.gitignore`

The migration will detect and remove entries like:
- `kitty-specs`
- `kitty-specs/`
- `/kitty-specs`
- `/kitty-specs/`

It will NOT remove specific subpath patterns that are intentionally used in worktrees.

## [0.12.0] - 2026-01-23

### ✨ Added

**Config-Driven Agent Management** (Feature 022):
- **Single source of truth**: `.kittify/config.yaml` now controls which agents are configured
- **New CLI commands**: `spec-kitty agent config list|add|remove|status|sync`
  - `list`: Show configured agents
  - `add <agents...>`: Add agents to configuration
  - `remove <agents...>`: Remove agents from configuration
  - `status`: Show configured vs orphaned agents
  - `sync`: Synchronize filesystem with configuration
- **Migrations respect config**: `get_agent_dirs_for_project()` helper only processes configured agents
- **Orphan detection**: Identifies agent directories not in config (from manual deletions)
- **ADR #6**: Documents architectural decision for config-driven approach

**Smarter Feature Merge with Pre-flight** (Feature 017):
- **Pre-flight validation**: Checks all WP worktrees for uncommitted changes, missing worktrees, and target branch divergence before any merge starts
- **Conflict forecasting**: `--dry-run` predicts which files will conflict and classifies them as auto-resolvable (status files) or manual
- **Smart merge order**: WPs merged in dependency order based on frontmatter `dependencies` field
- **Status file auto-resolution**: Conflicts in WP prompt files (`kitty-specs/*/tasks/*.md`) automatically resolved by taking advanced lane status
- **Merge state persistence**: Progress saved to `.kittify/merge-state.json` for recovery
- **Resume/abort flags**: `--resume` continues interrupted merges, `--abort` clears state and starts fresh
- **Auto-cleanup**: Worktrees and branches removed after successful merge (configurable with `--keep-worktree`, `--keep-branch`)

### 📚 Documentation

**Merge Preflight Documentation** (Feature 018):
- Added `docs/how-to/merge-feature.md` - Complete merge workflow guide with pre-flight, dry-run, strategies, and cleanup options
- Added `docs/how-to/troubleshoot-merge.md` - Comprehensive troubleshooting guide with error reference table
- Updated CLAUDE.md with Merge & Preflight Patterns section documenting MergeState dataclass and public API

**Agent Management Documentation Sprint** (Feature 023):
- Added `docs/how-to/manage-agents.md` - Complete guide to adding, removing, and managing AI agent integrations
- Added `docs/how-to/upgrade-to-0-12-0.md` - Migration guide for config-driven agent management
- Updated `docs/reference/cli-commands.md` with comprehensive `agent config` subcommand documentation
- Updated `docs/reference/agent-subcommands.md`, `docs/reference/configuration.md`, `docs/reference/supported-agents.md` with accurate cross-references
- Updated `docs/how-to/install-spec-kitty.md` with agent configuration guidance

### 🐛 Fixed

**Merge Resume Bug**:
- Fixed `merge_workspace_per_wp()` missing `resume_state` parameter causing `TypeError` when using `--resume`

**Agent Workflow Output Truncation** (GitHub Codex compatibility):
- Fixed workflow commands (`implement`, `review`) outputting 300+ lines which got truncated by agents like GitHub Codex
- Prompts now written to temp file with concise 15-line summary to stdout
- Added directive language (`▶▶▶ NEXT STEP: Read the full prompt file now:`) so agents automatically read the file
- Agents no longer miss work package requirements due to output truncation

**False Staleness for Newly-Created Worktrees**:
- Fixed stale detection flagging new worktrees as stale immediately
- Previously, `git log -1` returned parent branch's commit time (could be hours old)
- Now checks if branch has commits since diverging from main
- Worktrees with no new commits are NOT flagged as stale (agent just started)

## [0.11.1] - 2026-01-16

### 🐛 Fixed

**Merge Template Improvements**:
- Added explicit preflight validation code using `python3 -c` with `validate_worktree_location()`
- Added clear visual "⛔ Location Pre-flight Check (CRITICAL)" section to prevent agents running merge from wrong location
- Fixed contradictory instructions in software-dev mission merge template (was incorrectly saying "run from main")
- Fixed empty Python code block in research mission merge template that confused agents
- Added workspace-per-WP model (0.11.0+) documentation vs legacy pattern in worktree strategy section

**Documentation Accuracy** (Feature 014):
- Rewrote `multi-agent-orchestration.md` for the 0.11.0+ isolated-WP worktree model:
  - Planning happens in main repo (not worktrees)
  - Each WP gets its own worktree (not shared)
  - Removed references to non-existent scripts
  - Updated lane tracking to frontmatter (not directories)
  - Added parallelization patterns and status monitoring
- Fixed the legacy isolated-worktree guide merge command syntax (runs from worktree without feature argument)
- Fixed `documentation-mission.md` broken source links
- Fixed `reference/README.md` - replaced outdated "Planned Content" with actual content links
- Fixed `kanban-workflow.md` - clarified `/spec-kitty.accept` works on features, not individual WPs

### 📚 Added

**Comprehensive End-User Documentation** (Feature 014):
- Complete Divio 4-type documentation suite:
  - **Tutorials**: Getting Started, Your First Feature, Claude Code Integration, Claude Code Workflow, Multi-Agent Workflow, Missions Overview
  - **How-To Guides**: 14 task-oriented guides covering installation, specifications, planning, implementation, review, dependencies, parallel development, dashboard usage, and migration
  - **Reference**: CLI Commands, Slash Commands, Agent Subcommands, Configuration, Environment Variables, File Structure, Missions, Supported Agents
  - **Explanations**: Spec-Driven Development, Divio Documentation, legacy isolated worktree model, Git Worktrees, Mission System, Kanban Workflow, AI Agent Architecture, Documentation Mission, Multi-Agent Orchestration
- Cross-references between all documentation types
- DocFX-compatible structure with `toc.yml` navigation

## [0.11.0] - 2026-01-12

### 🚨 BREAKING CHANGES - Workspace Model Changed (Feature 010)

**Old (0.10.x)**: One worktree per feature
- `/spec-kitty.specify` created `.worktrees/###-feature/`
- All WPs worked in same worktree
- Sequential development (one agent at a time)

**New (0.11.0)**: One worktree per work package
- Planning commands (specify, plan, tasks) work in main repository (NO worktree created)
- `spec-kitty implement WP##` creates `.worktrees/###-feature-WP##/`
- Each WP has isolated worktree with dedicated branch
- Enables parallel multi-agent development

### ⚠️ Migration Required

**You MUST complete or delete all in-progress features before upgrading to 0.11.0.**

See docs/upgrading-to-0-11-0.md for complete migration guide.

### 🔒 Security (IMPORTANT) - Feature 011

- **Comprehensive adversarial review framework**
  - Expanded review template from 3 bullets (109 lines) to 12 scrutiny categories (505 lines)
  - **Security scrutiny now mandatory**: 10 detailed security subsections
  - **Mandatory verification**: 7 security grep commands must be run on EVERY review
  - **Automatic rejection** if any security check fails
  - **Impact**: All future features will have security-first reviews

### ✨ Added

**Legacy isolated-WP worktree features (010)**:
- **New command**: `spec-kitty implement WP## [--base WPXX]` - Create workspace for work package
  - `--base` flag branches from another WP's branch (for dependencies)
  - Automatically moves WP from `planned` → `doing` lane
- **New command**: `spec-kitty agent feature finalize-tasks` - Finalize WP generation
  - Parses dependencies from tasks.md
  - Generates `dependencies: []` field in WP frontmatter
  - Validates dependency graph (cycle detection, invalid references)
- **Dependency tracking**: WP frontmatter includes `dependencies: []` field
- **Dependency graph utilities**: `src/specify_cli/core/dependency_graph.py`
- **Review warnings**: Alert when dependent WPs need rebase

**Constitution Features (011)**:
- **Interactive constitution command** (Phase-based discovery)
  - 4-phase discovery workflow (Technical, Quality, Tribal Knowledge, Governance)
  - Two paths: Minimal (Phase 1 only) or Comprehensive (all phases)
  - Skip options for each phase
  - Truly optional - all commands work without constitution

### ♻️ Refactored - Feature 011

- **Template source relocation** (Safe dogfooding - Critical)
  - Moved ALL template sources from `.kittify/` to `src/specify_cli/`
  - Updated template manager to load from package resources
  - Removed `.kittify/*` force-includes from `pyproject.toml`
  - **Impact**: Developers can now safely dogfood without packaging risk

- **Mission-specific constitutions removed**
  - Single project-level constitution model (`.kittify/memory/constitution.md`)
  - Migration removes mission constitutions from user projects

### 🐛 Fixed - Feature 011

- **Windows dashboard ERR_EMPTY_RESPONSE** (#71)
  - Replaced POSIX-only signal handling with cross-platform psutil
  - Added `psutil>=5.9.0` dependency
  - Dashboard now works on Windows 10/11

- **Upgrade migration failures** (#70)
  - Fixed multiple migrations to handle missing files gracefully
  - All migrations now idempotent
  - Upgrade path from 0.6.4 → 0.10.12 completes without intervention

### 🐛 Fixed - Feature 012

- **`/spec-kitty.status` template instructed agents to run Python code**
  - AI agents cannot execute arbitrary Python - they use CLI tools
  - Updated template to use CLI command as primary method
  - Python API now documented as alternative for Jupyter/scripts

### 📖 Documentation - Feature 010

- **New docs**: legacy isolated-worktree workflow guide with examples
- **New docs**: `docs/upgrading-to-0-11-0.md` - Migration instructions

### 🎯 Why These Changes?

**Feature 010 (Workspace-per-WP)**:
- Enables parallel multi-agent development
- Better isolation per work package
- Explicit dependencies with validation
- Scalability for large features (10+ WPs)

**Feature 011 (Constitution & Packaging Safety)**:
- Safe dogfooding (no packaging contamination)
- Cross-platform dashboard support
- Optional, interactive constitution setup
- Smooth upgrade migrations

## [0.10.13] - 2026-01-12

### 🐛 Fixed

- **CRITICAL: Missing migration in PyPI v0.10.12 package**
  - Migration `m_0_10_12_constitution_cleanup.py` was missing from PyPI package uploaded on 2026-01-07
  - File existed in source repository but was not included in distributed wheel
  - Caused constitution cleanup to not run during upgrades from v0.10.11
  - v0.10.13 includes the missing migration file
  - Users who installed v0.10.12 should run `spec-kitty upgrade` again after upgrading to v0.10.13
  - **Root cause**: PyPI package was built before migration file was committed to repository
  - **Prevention**: Added migration file count verification to release workflow

### ♻️ Improved

- **Release workflow hardening**
  - Added verification step to count migration files in built wheel
  - Release now fails if migration count doesn't match source repository
  - Prevents future packaging bugs where files are missing from distribution

### 📋 Migration for v0.10.12 Users

If you installed v0.10.12 from PyPI and upgraded from v0.10.11:
```bash
pip install --upgrade spec-kitty-cli
spec-kitty upgrade  # Run again to apply missing migration 0.10.12
```

The migration will remove mission-specific constitution directories:
- `.kittify/missions/software-dev/constitution/` → removed
- `.kittify/missions/research/constitution/` → removed
- Single project-level constitution: `.kittify/memory/constitution.md` (kept)

## [0.10.12] - 2026-01-12

### 🔒 Security (IMPORTANT)

- **Comprehensive adversarial review framework**
  - Expanded review template from 3 bullets (109 lines) to 12 scrutiny categories (505 lines)
  - **Security scrutiny now mandatory**: 10 detailed security subsections
  - **Mandatory verification**: 7 security grep commands must be run on EVERY review
  - **Automatic rejection** if any security check fails
  - **Impact**: All future features will have security-first reviews
  - **Rationale**: Prevents systematic quality issues (TODOs in prod, mocked implementations, security vulnerabilities)
  - See spec footnote and commit `61d7d01` for complete rationale

### 🐛 Fixed

- **Windows dashboard ERR_EMPTY_RESPONSE** (#71)
  - Replaced POSIX-only signal handling with cross-platform psutil library
  - `signal.SIGKILL` and `signal.SIGTERM` don't exist on Windows
  - Added `psutil>=5.9.0` dependency for cross-platform process management
  - Refactored `src/specify_cli/dashboard/lifecycle.py`:
    - `os.kill(pid, 0)` → `psutil.Process(pid).is_running()`
    - `signal.SIGKILL` → `psutil.Process(pid).kill()` (6 locations)
    - `signal.SIGTERM` → `psutil.Process(pid).terminate()` with timeout
  - Added proper exception handling (NoSuchProcess, AccessDenied, TimeoutExpired)
  - Dashboard now starts, serves HTML, and stops cleanly on Windows 10/11
  - All 41 dashboard tests passing

- **Upgrade migration failures** (#70)
  - Fixed `m_0_7_3_update_scripts.py` to handle missing bash scripts gracefully
  - Fixed `m_0_10_6_workflow_simplification.py` to copy templates before validation
  - Fixed `m_0_10_2_update_slash_commands.py` to explicitly remove legacy .toml files
  - Fixed `m_0_10_0_python_only.py` to explicitly remove `.kittify/scripts/tasks/`
  - Created `m_0_10_12_constitution_cleanup.py` to remove mission constitutions
  - All migrations now idempotent (safe to run multiple times)
  - Upgrade path from 0.6.4 → 0.10.12 now completes without manual intervention

- **Upgrade migration parameter mismatch** (#68 follow-up)
  - Fixed `m_0_10_9_repair_templates.py` migration calling `generate_agent_assets()` with wrong parameter name
  - Changed `ai=ai_config` to `agent_key=ai_config` to match function signature

### ♻️ Refactored

- **Template source relocation** (Safe dogfooding - Critical)
  - Moved ALL template sources from `.kittify/` to `src/specify_cli/`
  - Templates: `.kittify/templates/` → `src/specify_cli/templates/`
  - Missions: `.kittify/missions/` → `src/specify_cli/missions/`
  - Scripts: `.kittify/scripts/` → `src/specify_cli/scripts/`
  - Updated `src/specify_cli/template/manager.py` to load from `src/` not `.kittify/`
  - Removed ALL `.kittify/*` force-includes from `pyproject.toml`
  - **Impact**: Spec-kitty developers can now safely dogfood spec-kitty without risk of packaging their filled-in constitutions
  - **Verification**: Building wheel produces ZERO `.kittify/` or `memory/constitution.md` entries
  - Package now only contains `src/specify_cli/` (proper Python packaging)

- **Mission-specific constitutions removed**
  - Removed `mission.constitution_dir` property from `src/specify_cli/mission.py`
  - Removed constitution scanning from `src/specify_cli/manifest.py`
  - Deleted all `missions/*/constitution/` directories
  - **Impact**: Single project-level constitution model (`.kittify/memory/constitution.md`)
  - **Migration**: `m_0_10_12_constitution_cleanup.py` removes mission constitutions from user projects
  - Eliminates confusion about which constitution applies

## [0.10.11] - 2026-01-07

### 🐛 Fixed

- **Upgrade migration parameter mismatch** (#68 follow-up)
  - Fixed `m_0_10_9_repair_templates.py` migration calling `generate_agent_assets()` with wrong parameter name
  - Changed `ai=ai_config` to `agent_key=ai_config` to match function signature
  - Corrected parameter order to match function definition
  - **Root cause**: Migration was using deprecated parameter name, blocking users from upgrading to 0.10.11
  - **Impact**: Users unable to run `spec-kitty upgrade` to get template fixes from 0.10.11

## [0.10.11] - 2026-01-07

### 🐛 Fixed

- **Deprecated script references in mission templates** (#68)
  - Fixed `.kittify/missions/software-dev/templates/task-prompt-template.md` to use workflow commands instead of deprecated `python3 .kittify/scripts/tasks/tasks_cli.py`
  - Fixed `.kittify/templates/task-prompt-template.md` with same update
  - Fixed `.kittify/missions/software-dev/command-templates/tasks.md` to reference workflow commands
  - Updated `.kittify/templates/POWERSHELL_SYNTAX.md` to document spec-kitty CLI instead of obsolete PowerShell scripts
  - **Root cause**: Migration 0.10.9 fixed agent command templates but missed mission-specific templates
  - **Impact**: Agents were executing users' local `cli.py` files instead of spec-kitty CLI on Windows

### ✨ Added

- **Template compliance tests** - Prevent deprecated script references
  - `test_no_deprecated_script_references()` - Detects old `.kittify/scripts/` paths in templates
  - `test_templates_use_spec_kitty_cli()` - Ensures templates reference spec-kitty CLI commands
  - Tests run on all mission templates and global templates
  - Prevents regression of issue #68

## [0.10.10] - 2026-01-06

### 🐛 Fixed

- **Windows UTF-8 encoding error in agent commands** (#66)
  - Fixed `'charmap' codec can't encode characters` error on Windows
  - `spec-kitty agent feature create-feature` now works correctly on Windows
  - Added UTF-8 stdout/stderr reconfiguration in main() entry point
  - Handles Unicode characters in git output and error messages
  - Gracefully falls back for Python < 3.7

## [0.10.9] - 2026-01-06

### 🐛 Fixed

- **CRITICAL: Wrong templates bundled in PyPI packages** (#62, #63, #64)
  - Fixed pyproject.toml to bundle .kittify/templates/ instead of outdated /templates/
  - Removed outdated /templates/ directory entirely to prevent confusion
  - All PyPI installations now receive correct Python CLI templates
  - No more bash script references in command templates
  - Migration 0.10.0 now handles missing templates gracefully
  - Added package bundling validation tests to prevent regression

- **Template divergence eliminated**
  - 10 of 13 command templates were outdated in /templates/
  - implement.md was 199 lines longer in old location (277 vs 78 lines)
  - Git hooks were missing (1 vs 3)
  - claudeignore-template was missing

- **All 12 AI agent integrations fixed**
  - Claude Code, GitHub Copilot, Cursor, Gemini, Qwen Code, OpenCode, Windsurf,
    GitHub Codex, Kilocode, Augment Code, Roo Cline, Amazon Q
  - All agents now receive correct Python CLI slash commands

### ✨ Added

- **Repair migration (0.10.9_repair_templates)** - Automatically fixes broken installations
  - Detects projects with broken template references
  - Regenerates all agent slash commands from correct templates
  - Runs automatically during `spec-kitty upgrade`
  - Verifies repair was successful

- **Package bundling validation tests** - Prevents future regressions
  - Validates correct templates are bundled in sdist and wheel
  - Checks for bash script references before release
  - Tests importlib.resources accessibility

### 📚 Migration & Upgrade Path

**For users with broken installations (issues #62, #63, #64):**

1. **Upgrade spec-kitty package:**
   ```bash
   pip install --upgrade spec-kitty-cli
   spec-kitty --version  # Should show 0.10.9
   ```

2. **Run upgrade to apply repair migration:**
   ```bash
   cd /path/to/your/project
   spec-kitty upgrade
   ```
   This will automatically detect and fix broken templates.

3. **Verify repair:**
   ```bash
   # Check for bash script references (should return nothing)
   grep -r "scripts/bash" .claude/commands/
   ```

**For new projects:**
- Automatically get correct templates from package
- No action needed

**For existing healthy projects:**
- Run `spec-kitty upgrade` to stay current
- No breaking changes

### 🔒 Breaking Changes

None - Fully backwards compatible. Existing projects will upgrade smoothly.

## [0.10.8] - 2025-12-30

### 🐛 Fixed

- **Critical: Constitution not copied to worktrees** (#46)
  - Moved `memory/` directory from root to `.kittify/memory/` where code expects it
  - Removed broken circular symlinks (`.kittify/memory` → `../../../.kittify/memory`)
  - Fixed `.kittify/AGENTS.md` to be real file instead of broken symlink
  - Fixed worktree.py symlink handling (check for symlink before trying rmtree)
  - Added migration to automatically fix existing projects
  - Worktrees now correctly access constitution from main repo

- **Migration system** (v0.10.8_fix_memory_structure)
  - Automatically moves `memory/` to `.kittify/memory/` in existing projects
  - Removes broken symlinks and creates proper structure
  - Updates worktrees to use correct paths
  - Handles both Unix symlinks and Windows file copies

### 🔧 Changed

- **Directory structure standardization**
  - `memory/` → `.kittify/memory/` (matches `.kittify/scripts/`, `.kittify/templates/`)
  - `.kittify/AGENTS.md` is now a real file (not symlink)
  - All `.kittify/` resources now follow consistent pattern

## [0.10.7] - 2025-12-30

### 🐛 Fixed

- **Critical: Copilot initialization bug** (#53, fixes #61, #50)
  - Fixed NameError when running `spec-kitty init --ai copilot`
  - Changed `commands_dir` to `command_templates_dir` in asset_generator.py
  - Unblocks all users trying to initialize projects with Copilot

- **Critical: Dashboard contracts and checklists missing** (#59, fixes #52)
  - Restored contracts and checklists handlers that were lost in Nov 11 dashboard refactoring
  - Added generic `_handle_artifact_directory()` helper method
  - Both contracts and checklists now display correctly in dashboard
  - Fixed frontend to use full filepath instead of filename only

- **Critical: Windows UTF-8 encoding errors** (#56)
  - Added explicit `encoding='utf-8'` to read_text() calls
  - Fixes dashboard diagnostics showing "undefined" on Windows
  - Affects manifest.py and migration files
  - Windows defaults to cp1252, causing UnicodeDecodeError with UTF-8 content

- **Plan.md location validation** (#60)
  - Improved validation messaging in plan.md template
  - Added prominent ⚠️ STOP header for AI agents
  - Clearer examples of correct vs wrong worktree locations
  - Template-only change (no code modifications)

### 🔄 Closed

- PR #58 - Obsolete (PowerShell scripts deleted in v0.10.0)
- PR #57 - Obsolete (PowerShell scripts deleted in v0.10.0)
- PR #49 - Superseded by #59 (better architecture)
- PR #43 - Obsolete (PowerShell scripts deleted in v0.10.0)

## [0.10.6] - 2025-12-18

### ✨ Added

- **Workflow commands for simplified agent experience**
  - New `spec-kitty agent workflow implement [WP_ID]` command
  - New `spec-kitty agent workflow review [WP_ID]` command
  - Commands display full WP prompt directly to agents (no file navigation)
  - Auto-detect first planned/for_review WP when no ID provided
  - Auto-move WP to "doing" lane before displaying prompt
  - Show "WHEN YOU'RE DONE" instructions at top of output
  - Display source file path for easy re-reading
  - Prevents race conditions (two agents picking same WP)

### 🔧 Changed

- **Slash command template simplification**
  - implement.md: 78 lines → 11 lines (calls workflow command)
  - review.md: 72 lines → 11 lines (calls workflow command)
  - Templates now just run workflow commands instead of complex instructions
  - Agents see prompts immediately without navigation confusion

- **Consistent lane management**
  - Both implement and review workflows move WP to "doing" at start
  - Prevents ambiguity about which lane means "actively working"
  - Review workflow now supports auto-detect (no argument needed)

### 🐛 Fixed

- **Worktree path resolution**
  - Fixed `_find_first_planned_wp()` to work correctly in worktrees
  - Fixed `_find_first_for_review_wp()` to work correctly in worktrees
  - Auto-detect now finds WPs in worktree's kitty-specs/, not main repo

- **Legacy subdirectory cleanup**
  - Migrated features 007 and 010 from old subdirectory structure to flat structure
  - Moved 15 WP files from `tasks/done/phase-*/` to flat `tasks/`
  - All features now use proper flat structure with frontmatter-only lanes

## [0.9.4] - 2025-12-17

### 📚 Documentation & Validation

- **Prevent agent-created subdirectories in tasks/**
  - Added explicit warnings to tasks/README.md
  - Updated AGENTS.md with flat structure requirements
  - Updated /spec-kitty.tasks template to forbid subdirectories
  - Added runtime validation in check-prerequisites.sh
  - Blocks execution if phase-*, component-*, or any subdirectories found
  - Clear error messages with examples of correct vs wrong paths

This prevents Claude agents from creating organizational subdirectories like `tasks/phase-1/`, `tasks/backend/`, etc.

## [0.9.3] - 2025-12-17

### 🐛 Fixed

- **Critical symlink detection fix**
  - Now checks `is_symlink()` BEFORE `exists()` (exists() returns False for broken symlinks!)
  - Properly removes both working and broken symlinks from worktrees
  - Fixes remaining test failures in worktree cleanup migration
  - Handles all symlink scenarios correctly

This completes the fix for symlink removal in worktree cleanup.

## [0.9.2] - 2025-12-17

### 🐛 Fixed

- **Symlink handling in worktree cleanup**
  - Migration now properly detects and removes symlinks to command directories
  - Uses `unlink()` for symlinks instead of `shutil.rmtree()`
  - Fixes "Cannot call rmtree on a symbolic link" error during upgrade
  - Handles both symlinks and regular directories correctly

This fixes the upgrade failure when worktrees have symlinked agent command directories.

## [0.9.1] - 2025-12-17

### 🔧 Bug Fixes & Improvements

This release fixes critical issues found in v0.9.0 and adds version checking to prevent compatibility problems.

### 🆕 Added

- **Version compatibility checking**
  - CLI now checks for version mismatches between installed spec-kitty-cli and project version
  - Hard error with explicit instructions when versions don't match
  - Special critical warning for v0.9.0+ upgrade explaining breaking changes
  - Shows detailed before/after directory structure comparison
  - Version checks in all CLI commands and bash scripts
  - Graceful handling of legacy projects without metadata

- **Programmatic frontmatter management**
  - New `specify_cli.frontmatter` module for consistent YAML operations
  - Uses ruamel.yaml for absolute formatting consistency
  - No more manual YAML editing by LLMs or scripts
  - Prevents quoted vs unquoted value inconsistencies

### 🐛 Fixed

- **Migration improvements**
  - v0.9.0 migration now finds ALL markdown files (not just WP*.md)
  - Detects and removes empty lane subdirectories
  - Uses shutil.rmtree() for robust directory removal
  - Better detection of legacy format

- **Complete lane migration (v0.9.1)**
  - Migrates files missed by v0.9.0 (phase-*.md, task-*.md, etc.)
  - Removes ALL agent command directories from worktrees (.codex/prompts/, .gemini/commands/, etc.)
  - Removes .kittify/scripts/ from worktrees (inherit from main repo)
  - Normalizes all frontmatter to consistent YAML format
  - Fixes issue where worktrees had old command templates referencing deprecated scripts

- **Flat structure in new features**
  - Fixed create-new-feature.sh to create flat tasks/ directory (not subdirectories)
  - Updated README.md documentation to reflect v0.9.0+ structure
  - New features now work correctly with frontmatter-only lanes from day one

- **Lane validation**
  - tasks_cli.py update command now validates lane values
  - Rejects invalid lanes before processing
  - Clear error messages for invalid input

### 🔧 Changed

- Added `ruamel.yaml>=0.18.0` dependency for consistent YAML handling
- Updated success messages to reflect flat structure

### 🚀 Migration

If you upgraded to v0.9.0 and still have issues, run `spec-kitty upgrade` again to apply v0.9.1 fixes:
- Completes any remaining lane migrations
- Cleans up worktree command directories
- Normalizes all frontmatter for consistency

## [0.9.0] - 2025-12-17

### 🎯 Major Release: Frontmatter-Only Lane Management

This release fundamentally changes how Spec Kitty manages work package lanes, eliminating directory-based lane tracking in favor of a simpler, conflict-free frontmatter-only system.

### ⚠️ Breaking Changes

- **Lane system completely redesigned**
  - Work packages now live in a flat `kitty-specs/<feature>/tasks/` directory
  - Lane status determined **solely by `lane:` frontmatter field** (no more subdirectories)
  - Old system: `tasks/planned/WP01.md`, `tasks/doing/WP02.md` ❌
  - New system: `tasks/WP01.md` with `lane: "planned"` ✅

- **Command renamed: `move` → `update`**
  - Legacy `tasks_cli.py move` command removed
  - Use `tasks_cli.py update <feature> <WP> <lane>` instead
  - Semantic clarity: command updates metadata, doesn't move files
  - Legacy format detection: `update` command refuses to work on old directory-based structure

- **Direct frontmatter editing now supported**
  - You can now directly edit the `lane:` field in WP frontmatter
  - Previous "DO NOT EDIT" warnings removed from all templates
  - System recognizes manual lane changes immediately
  - No file movement required for lane transitions

### 🆕 Added

- **Migration command: `spec-kitty upgrade`**
  - Automatically migrates features from directory-based to frontmatter-only format
  - Preserves all lane assignments during migration
  - Idempotent: safe to run multiple times
  - Cleans up empty lane subdirectories after migration
  - Migrates both main repo and worktree features

- **Legacy format detection**
  - `is_legacy_format()` function detects old directory-based structure
  - CLI commands display helpful warnings when legacy format detected
  - Dashboard shows migration prompt for legacy features
  - Non-blocking: legacy features remain functional until migrated

- **Enhanced status command**
  - Better formatted output with lane grouping
  - Auto-detects feature from branch/worktree when not specified
  - Shows work packages organized by current lane
  - Works with both legacy and new formats

### 🔧 Changed

- **Work package location logic**
  - `locate_work_package()` now searches flat `tasks/` directory first
  - Falls back to legacy subdirectory search for backwards compatibility
  - Exact WP ID matching (WP04 won't match WP04b)

- **Lane extraction utilities**
  - New `get_lane_from_frontmatter()` function extracts lane from YAML
  - Defaults to "planned" when `lane:` field missing
  - Validates lane values against allowed set
  - Available in both `task_helpers.py` and `tasks_support.py`

- **Dashboard scanner updates**
  - Reads lane from frontmatter instead of directory location
  - Displays legacy format warnings
  - Works seamlessly with both formats during transition

- **Activity log behavior**
  - Lane transitions still append activity log entries
  - Captures agent, shell PID, and timestamp
  - No file movement logged (because no movement occurs)

### 📚 Documentation

- **Updated all templates**
  - `.kittify/templates/task-prompt-template.md` - Removed "DO NOT EDIT" warnings
  - `.kittify/templates/tasks-template.md` - Updated for flat structure
  - `.kittify/templates/AGENTS.md` - New lane management instructions
  - `tasks/README.md` - Rewritten for flat directory layout

- **Updated mission templates**
  - All mission-specific templates updated (software-dev, research)
  - Command templates updated (`implement.md`, `review.md`, `merge.md`)
  - Examples updated to show new workflow

- **Updated main documentation**
  - `README.md` - Updated quick start examples
  - `docs/quickstart.md` - New lane management workflow
  - `docs/multi-agent-orchestration.md` - Updated collaboration examples
  - All `examples/` updated with new commands

### 🧪 Testing

- 286 tests passing (0 failures)
- New tests for frontmatter-only lane system
- Legacy format detection tests
- Migration command tests
- Dual-format compatibility tests

### 🚀 Migration Guide

**For existing projects:**

1. **Back up your work** (commit changes, push to remote)
2. **Run migration**: `spec-kitty upgrade`
3. **Verify**: `spec-kitty status --feature <your-feature>`
4. **Update workflows**: Replace `move` with `update` in scripts/docs

**Key benefits of upgrading:**

- ✅ No file conflicts during lane changes (especially in worktrees)
- ✅ Direct editing of `lane:` field supported
- ✅ Better multi-agent compatibility
- ✅ Simpler mental model (one directory, not four)
- ✅ Fewer git operations per lane change

**Legacy format still works** - You can continue using old directory structure until ready to migrate. All commands detect format automatically.

### 🐛 Fixed

- File conflicts during simultaneous lane changes by multiple agents
- Git staging issues with lane transitions
- Race conditions in worktree-based parallel development
- Lane mismatch validation errors (no longer possible with frontmatter-only)

### 🔗 Related

- Feature implementation: `007-frontmatter-only-lane`
- All 6 work packages completed and reviewed
- Comprehensive test coverage added

---

## [0.8.2] - 2025-12-17

### Added

- **Task lane management documentation** - Added clear instructions to AGENTS.md and task templates warning agents never to manually edit the `lane:` YAML field
  - Lane is determined by directory location, not YAML field
  - Editing `lane:` without moving the file creates a mismatch that breaks the system
  - All templates now include YAML comment: `# DO NOT EDIT - use: workflow commands` (legacy note)
  - Added "Task Lane Management Rule" section to project AGENTS.md

## [0.8.1] - 2025-12-17

### Fixed

- **Work package move race conditions** - Multiple agents can now work on different WPs simultaneously without blocking each other
  - Conflict detection now only blocks on changes to the same WP, not unrelated WP files
  - Agents working on WP05 no longer block moves of WP04

- **Exact WP ID matching** - `WP04` no longer incorrectly matches `WP04b`
  - Changed from prefix matching to exact boundary matching
  - Pattern now requires WP ID to be followed by `-`, `_`, `.`, or end of filename

- **Cleanup no longer leaves staged deletions** - Stale copy cleanup uses filesystem delete instead of `git rm`
  - Prevents orphaned staged deletions from blocking subsequent operations
  - Automatically unstages any previously staged changes to cleaned files

## [0.8.0] - 2025-12-15

### Breaking Changes

- **Mission system refactored to per-feature model**
  - Missions are now selected during `/spec-kitty.specify` instead of `spec-kitty init`
  - Each feature stores its mission in `meta.json` (field: `"mission": "software-dev"`)
  - `.kittify/active-mission` symlink/file is no longer used
  - Run `spec-kitty upgrade` to clean up existing projects

- **Removed commands**
  - `spec-kitty mission switch` - Missions are now per-feature, not per-project
  - Running this command now shows a helpful error message explaining the new workflow

- **Removed flags**
  - `--mission` flag from `spec-kitty init` - Use `/spec-kitty.specify` instead
  - Flag is hidden but shows deprecation warning if used

### Added

- **Mission inference during `/spec-kitty.specify`** - LLM analyzes feature description and suggests appropriate mission:
  - "Build a REST API" → suggests `software-dev`
  - "Research best practices" → suggests `research`
  - User confirms or overrides the suggestion
  - Explicit `--mission` flag bypasses inference

- **Per-feature mission storage** - Selected mission stored in feature's `meta.json`:
  - All downstream commands read mission from feature context
  - Legacy features without mission field default to `software-dev`

- **Mission discovery** - New `discover_missions()` function returns all available missions with source indicators

- **Updated `spec-kitty mission list`** - Shows source column (project/built-in) for each mission

- **Migration for v0.8.0** - `spec-kitty upgrade` removes obsolete `.kittify/active-mission` file

- **AGENTS.md worktree fix** - New worktrees get AGENTS.md symlink, and `spec-kitty upgrade` fixes existing worktrees

### Changed

- All downstream commands (`/spec-kitty.plan`, `/spec-kitty.tasks`, `/spec-kitty.implement`, `/spec-kitty.review`, `/spec-kitty.accept`) now read mission from feature's `meta.json`
- `create-new-feature.sh` accepts `--mission <key>` parameter to set mission in meta.json
- Common bash/PowerShell scripts updated to resolve mission from feature directory
- `spec-kitty mission current` shows current default mission (for informational purposes)
- Dashboard template now includes dynamic AGENTS.md path discovery instructions

### Deprecated

- `set_active_mission()` function - Shows deprecation warning, will be removed in future version

### Migration Guide

1. Run `spec-kitty upgrade` to remove `.kittify/active-mission`
2. Existing features without `mission` field will use `software-dev` by default
3. New features will have mission set during `/spec-kitty.specify`

## [0.7.4] - 2025-12-14

### Added

- **Script Update Migration** – `spec-kitty upgrade` now updates project scripts:
  - Copies latest `create-new-feature.sh` from package to project
  - Fixes worktree feature numbering bug in existing projects
  - Previously, projects kept old scripts from when they were initialized

## [0.7.3] - 2025-12-14

### Fixed

- **Duplicate Feature Numbers with Worktrees** – Script now scans both `kitty-specs/` AND `.worktrees/` for existing feature numbers:
  - Previously only scanned `kitty-specs/` which was empty when using worktrees
  - This caused new features to get `001` even when `001-*` worktree already existed
  - Now correctly finds highest number across both locations

## [0.7.2] - 2025-12-14

### Fixed

- **Duplicate Slash Commands in Worktrees (Corrected)** – Fixed the fix from v0.7.1:
  - v0.7.1 incorrectly removed commands from main repo (broke `/` commands there)
  - v0.7.2 removes commands from **worktrees** instead (they inherit from main repo)
  - Claude Code traverses UP, so worktrees find main repo's `.claude/commands/`
  - Main repo keeps commands, worktrees don't need their own copy

## [0.7.1] - 2025-12-14 [YANKED]

### Fixed

- ~~Duplicate Slash Commands in Worktrees~~ – **Incorrect fix, replaced by v0.7.2**

## [0.7.0] - 2025-12-14

### Added

- **`spec-kitty upgrade` Command** – Automatically migrate existing projects to current version:
  - Detects project version via metadata or directory structure heuristics
  - Applies all necessary migrations in order (0.2.0 → 0.6.7)
  - Auto-upgrades worktrees alongside main project
  - Supports `--dry-run`, `--verbose`, `--json`, `--target`, `--no-worktrees` options
  - Tracks applied migrations in `.kittify/metadata.yaml`
  - Idempotent - safe to run multiple times

- **Migration System** – Five automatic migrations for project structure updates:
  - `0.2.0`: `.specify/` → `.kittify/` directory rename
  - `0.4.8`: Add all 12 agent directories to `.gitignore`
  - `0.5.0`: Install encoding validation git hooks
  - `0.6.5`: `commands/` → `command-templates/` rename
  - `0.6.7`: Ensure software-dev and research missions are present

- **Broken Mission Detection** – `VersionDetector.detect_broken_mission_system()` identifies corrupted mission.yaml files

- **Migration Registry Validation** – Duplicate migration IDs and missing required fields now raise `ValueError`

### Fixed

- **Test Timeout in Dashboard CLI Tests** – Reduced port cleanup from 763 ports to 8 specific test ports
- **Playwright Window Handling** – Tests now open new windows (not tabs) and close properly on exit

## [0.6.7] - 2025-12-13

### Fixed

- **Missing software-dev Mission in PyPI Package** – Fixed build configuration to include all missions:
  - Added explicit sdist include patterns to pyproject.toml
  - The `software-dev` mission was missing from v0.6.5 and v0.6.6 wheel builds
  - Root cause: `force-include` only applied to wheel target, not sdist (wheel was built from sdist)
  - Now both `software-dev` and `research` missions are correctly packaged

## [0.6.6] - 2025-12-13

### Fixed

- **Test Suite Updated for 12 Agent Directories** – All tests now expect 12 agents (added `.github/copilot/`):
  - Updated `test_init_flow.py`, `test_gitignore_management.py`, `test_gitignore_manager_simple.py`
  - Updated `tests/unit/test_gitignore_manager.py` to expect 12 agents
  - Fixed template manager tests to use new `.kittify/` source paths

### Changed

- **Template Source Paths** – Tests now use correct `.kittify/templates/command-templates/` paths

## [0.6.5] - 2025-12-13

### Added

- **Pre-commit Git Hooks** – Automatic protection against committing agent directories:
  - Blocks commits containing `.claude/`, `.codex/`, `.gemini/`, etc.
  - Warns about `.github/copilot/` (nested in `.github/` which is usually committed)
  - Installed automatically during `spec-kitty init`

- **GitHub Copilot Directory Protection** – Added `.github/copilot/` as 12th protected agent directory

- **.claudeignore Generation** – Optimizes Claude Code token usage by excluding templates

### Fixed

- **Worktree Constitution Symlinks** – Feature worktrees now share constitution via symlink
- **Git Hooks Installation Timing** – Hooks now install after `.git/` is created

## [0.6.4] - 2025-11-26

### Fixed

- **Agent Commands Missing in Worktrees** – Slash commands now work in all feature worktrees for all AI agents:
  - `create-new-feature.sh` now symlinks agent command directories from main repo to worktrees
  - Supports all 12 agent types: Claude, Gemini, Copilot, Cursor, Qwen, OpenCode, Windsurf, Codex, KiloCode, Auggie, Roo, Amazon Q
  - Fixes `/spec-kitty.research`, `/spec-kitty.plan`, and all other slash commands in worktrees
  - Existing worktrees get symlinks added when reused (backward compatible)
  - Root cause: worktrees are separate working directories that don't share `.claude/commands/` etc.

## [0.6.3] - 2025-11-25

### Fixed

- **Mission Directory Not Copied During Init** – Projects initialized with `spec-kitty init` now correctly receive mission templates:
  - Fixed `copy_specify_base_from_package()` to look at correct path `specify_cli/missions` (matching pyproject.toml)
  - Previously looked at wrong paths: `.kittify/missions` and `template_data/missions`
  - `software-dev` mission was missing from initialized projects, breaking `/spec-kitty.plan` and other commands
  - Root cause: pyproject.toml packages missions to `specify_cli/missions` but code looked elsewhere

## [0.6.2] - 2025-11-18

### Fixed

- **PowerShell Wrapper Parameter Handling** – Windows lane transitions now work correctly:
  - Fixed legacy `tasks-move-to-lane.ps1` to properly parse named PowerShell parameters
  - Translates Spec Kitty's named params (`-FeatureName`, `-TaskId`, `-TargetLane`) to `tasks_cli.py` positional args
  - Resolves `unrecognized arguments` error that broke `/spec-kitty.review` on Windows
  - Maintains backward compatibility with positional argument usage
  - Fixes #34

## [0.6.1] - 2025-11-18

### Fixed

- **Untracked Task File Moves** – Task move workflow now handles untracked files:
  - Added `is_file_tracked()` helper to detect if file is in git index
  - Move command automatically stages untracked source files before moving
  - Fixes `/spec-kitty.implement` failures when `/spec-kitty.tasks` doesn't commit
  - Provides clear feedback: `[spec-kitty] Added untracked file: ...`
  - Defensive fix works with both existing untracked files and future workflows

## [0.6.0] - 2025-11-16

### Fixed

- **Dashboard Constitution Tracking** – Feature-level constitution.md files now tracked and displayed:
  - Added constitution to scanner artifact list
  - Constitution appears in overview with ⚖️ icon
  - Frontend properly detects constitution.exists property

- **Dashboard Modification Detection** – Dashboard now detects file modifications, not just existence:
  - Scanner returns {exists, mtime, size} for each artifact instead of boolean
  - Frontend updated to use .exists property with optional chaining
  - Overview auto-reloads when artifacts change during polling
  - No manual refresh required to see new/modified files

- **Dashboard Project Constitution Endpoint** – Project constitution now loads in dashboard:
  - Added /api/constitution endpoint to serve .kittify/memory/constitution.md
  - Sidebar Constitution link now displays file content instead of "not found"
  - Separate from feature-level constitution tracking

- **Work Package Conflict Detection Too Strict** – Moving WP no longer blocked by unrelated WP changes:
  - Conflict detection now scoped to same work package ID only
  - Moving WP04 no longer fails if WP06/WP08 have uncommitted changes
  - Reduces false positives from ~90% to ~5%
  - Agents don't need --force for unrelated work packages
  - Still catches real conflicts (same WP in multiple lanes)

- **Accept Command Over-Questioning** – Acceptance workflow now auto-detects instead of asking:
  - Feature slug auto-detected from git branch
  - Mode defaults to 'local' (most common)
  - Validation commands searched in git log
  - Only asks user if auto-detection fails
  - Reduces user questions from 3-4 to 0 in typical case

- **Init Command Blocking on Optional Tools** – Project init no longer fails on missing agent tools:
  - Changed from red error + exit(1) to yellow warning + continue
  - Gemini CLI and other tools are optional
  - Users can install tools later without re-init
  - --ignore-agent-tools flag still available but rarely needed

- **Encoding Normalization Incomplete** – Unicode smart quotes now properly normalized to ASCII:
  - Added character mapping for 12 common Unicode characters
  - Smart quotes (U+2018/U+2019) → ASCII apostrophe
  - Em/en dashes → hyphens
  - Ellipsis, bullets, nbsp → ASCII equivalents
  - --normalize-encoding now produces true ASCII output

### Changed

- **Mission Display Simplified** – Reduced verbose mission card to single line:
  - Removed domain label, version number, path display
  - Removed redundant refresh button (auto-updates every second)
  - Changed from card layout to inline text: "Mission: {name}"
  - Cleaner, less cluttered header

### Added

- **Mission System Architecture** – Complete mission-based workflow system (feature 005):
  - Guards module for pre-flight validation
  - Pydantic mission schema validation
  - Mission CLI commands (list, current, switch, info)
  - Research mission templates and citation validators
  - Path convention validation
  - Dashboard mission display
  - Comprehensive integration tests

## [0.5.3] - 2025-11-15

### Fixed

- **Dashboard Orphaned Process Cleanup** – Fixed dashboard startup failures caused by orphaned test processes:
  - Dashboard now detects and cleans up orphaned processes when health check fails due to project path mismatch
  - Added retry logic after successful orphan cleanup
  - Orphan cleanup triggers on health check failure (not just port exhaustion)
  - Eliminates false "Unable to start dashboard" errors when orphaned test dashboards occupy ports

- **Dashboard Subprocess Import Failure** – Fixed ModuleNotFoundError in complex Python environments:
  - Dashboard subprocess now always inserts spec-kitty path at sys.path[0]
  - Fixes import failures when user's PYTHONPATH or .pth files contain spec-kitty path at lower priority
  - Ensures correct spec-kitty installation takes precedence over environment paths
  - Resolves "ModuleNotFoundError: No module named 'specify_cli.dashboard'" in subprocesses

### Changed

- **Test Suite Cleanup Improvements** – Enhanced dashboard test cleanup to prevent orphaned processes:
  - Module-level cleanup fixture kills all orphaned dashboards before and after test runs
  - Expanded cleanup port range from 9992-9999 to 9237-10000 (covers default and test ranges)
  - Added `kill_all_spec_kitty_dashboards()` helper using pgrep/pkill
  - Two-tier cleanup strategy: module-level (all processes) + function-level (specific ports)

### Added

- **Testing Guidelines for Agents** (`docs/testing-guidelines.md`) – Comprehensive testing best practices:
  - Required cleanup patterns for dashboard tests (pytest fixtures, autouse fixtures)
  - Anti-patterns to avoid (cleanup in test body, shared directories, no exception handling)
  - Impact analysis of orphaned processes on local development and CI/CD
  - Examples of proper test isolation and resource management

### Changed

- **Command Consolidation** – Merged `spec-kitty check` and `spec-kitty diagnostics` into `spec-kitty verify-setup`:
  - Removed redundant `spec-kitty check` and `spec-kitty diagnostics` commands
  - Tool checking now integrated into `verify-setup` with `--check-tools` flag (default: enabled)
  - Diagnostics mode with dashboard health available via `--diagnostics` flag
  - Removed ASCII banner from verify-setup for cleaner output
  - Simplifies CLI interface - single command for all environment verification
  - JSON output includes tool availability when `--check-tools` is enabled

### Removed

- **`spec-kitty check` command** – Functionality moved to `verify-setup --check-tools`
  - Migration: Use `spec-kitty verify-setup` instead of `spec-kitty check`
  - Tool checking enabled by default, disable with `--check-tools=false`
- **`spec-kitty diagnostics` command** – Functionality moved to `verify-setup --diagnostics`
  - Migration: Use `spec-kitty verify-setup --diagnostics` instead of `spec-kitty diagnostics`
  - Shows Rich panel-based output with dashboard health, observations, and issues

## [0.5.2] - 2025-11-14

### Fixed

- **Dashboard Startup Race Condition** – Fixed root cause of dashboard health check timing out prematurely:
  - Increased health check timeout from 10 to 20 seconds with exponential backoff
  - Retry pattern: 10×100ms, 40×250ms, 20×500ms for adaptive performance
  - Removed workaround fallback check that was masking the real issue
  - Eliminated false "Unable to start dashboard" errors on slower systems

### Changed

- **Dashboard Health Check Strategy** – Improved reliability with exponential backoff:
  - Quick initial checks (100ms) for fast systems
  - Gradual slowdown (250ms then 500ms) for slower systems
  - Total timeout increased to ~20 seconds for adequate startup time
  - Cleaner error handling without port-scanning fallback

### Added

- **Symlinked kitty-specs Test Coverage** – New test validates dashboard works with worktree structure:
  - Tests scenario from bug report (symlinked `kitty-specs/` to `.worktrees/`)
  - Ensures dashboard starts correctly with symlinked directories
  - Prevents regression of false error reporting

## [0.5.1] - 2025-11-14

### Added

- **Task Metadata Validation Guardrail** – Prevents workflow failures when file locations don't match frontmatter:
  - Auto-detects lane mismatches (file in `for_review/` but `lane: "planned"`)
  - CLI command: `spec-kitty validate-tasks --fix`
  - Integrated into `/spec-kitty.review` workflow (auto-runs before review)
  - Adds activity log entries documenting all repairs
  - Validates required fields (work_package_id, lane) and formats
- **Task Metadata Validation Module** (`src/specify_cli/task_metadata_validation.py`) – Core validation:
  - `detect_lane_mismatch()` - Finds directory/frontmatter inconsistencies
  - `repair_lane_mismatch()` - Auto-fixes with audit trail
  - `validate_task_metadata()` - Comprehensive field validation
  - `scan_all_tasks_for_mismatches()` - Feature-wide scanning

### Changed

- **Version Reading** – Now reads dynamically from package metadata instead of hardcoded value:
  - Uses `importlib.metadata.version()` to get actual installed version
  - `spec-kitty --version` always shows correct version
  - No manual updates needed in `__init__.py`
- **Review Workflow** – Added automatic task metadata validation before review:
  - Runs `spec-kitty validate-tasks --fix` automatically
  - Prevents agents getting stuck on lane mismatches
  - Documented in `.claude/commands/spec-kitty.review.md`

### Fixed

- **Dashboard CLI False Error** – CLI no longer reports "Unable to start dashboard" when dashboard actually started successfully. Added fallback verification to check if dashboard is accessible before reporting failure. Handles race condition where health check times out but server is functional.
- **Review Workflow Blocking** – Review command no longer fails when file locations don't match frontmatter metadata. Auto-validation repairs inconsistencies before review.
- **Hardcoded Version** – `spec-kitty --version` now reads from package metadata, always shows correct installed version.

### Documentation

- **task-metadata-validation.md** (350 lines) – Auto-repair workflow:
  - Lane mismatch detection and repair
  - CLI usage examples
  - Python API reference
  - Integration with review workflow

### Testing

- Added version detection tests to prevent future hardcoded version bugs
- Task metadata validation tested with real frontmatter/directory mismatches
- All tests passing (13/13)

## [0.5.0] - 2025-11-13

### Added

- **Encoding Validation Guardrail** – Comprehensive 5-layer defense system to prevent Windows-1252 characters from crashing the dashboard:
  - **Layer 1**: Dashboard auto-fixes encoding errors on read (server-side resilience)
  - **Layer 2**: Character sanitization module with 15+ problematic character mappings
  - **Layer 3**: CLI command `spec-kitty validate-encoding` with `--fix` flag
  - **Layer 4**: Pre-commit hook that blocks commits with encoding errors
  - **Layer 5**: Enhanced AGENTS.md with real crash examples and character blacklist
- **Plan Validation Guardrail** – Prevents agents from skipping the planning phase:
  - Detects 11 template markers in plan.md (threshold: 5+ markers = unfilled)
  - Blocks `/spec-kitty.research` command when plan is unfilled
  - Blocks `/spec-kitty.tasks` via check-prerequisites.sh
  - Clear error messages with remediation steps
- **Character Sanitization Module** (`src/specify_cli/text_sanitization.py`) – Core module for encoding fixes:
  - Maps smart quotes (`' ' " "`) → ASCII (`' "`)
  - Maps plus-minus (`±`) → `+/-`, multiplication (`×`) → `x`, degree (`°`) → `degrees`
  - Supports dry-run mode and automatic backup creation
  - Directory-wide sanitization with glob patterns
- **Plan Validation Module** (`src/specify_cli/plan_validation.py`) – Template detection:
  - Configurable threshold (default: 5 markers)
  - Line-precise error reporting
  - Strict and lenient validation modes

### Changed

- **Version Reading** – Now reads dynamically from package metadata instead of hardcoded value:
  - Uses `importlib.metadata.version()` to get actual installed version
  - `spec-kitty --version` always shows correct version
  - No manual updates needed in `__init__.py`
- **Review Workflow** – Added automatic task metadata validation before review:
  - Runs `spec-kitty validate-tasks --fix` automatically
  - Prevents agents getting stuck on lane mismatches
  - Documented in `.claude/commands/spec-kitty.review.md`
- **Dashboard Scanner** – Now resilient to encoding errors:
  - Auto-fixes files on read with backup creation
  - Creates error cards instead of crashing on bad files
  - Logs encoding issues with clear error messages
- **Research Command** – Added plan validation gate before allowing research artifact creation
- **Prerequisites Check Script** – Added bash-based plan validation (35 lines)
- **AGENTS.md Template** – Enhanced with encoding warnings:
  - Real crash examples from production
  - Explicit character blacklist with Unicode codepoints
  - Auto-fix workflow documentation

### Fixed

- **Dashboard Blank Page Issue** – Dashboard no longer crashes when markdown files contain Windows-1252 smart quotes, ±, ×, ° symbols. Auto-fix sanitizes files on first read.
- **Agents Skipping Planning** – Research and tasks commands now blocked until plan.md is properly filled out (not just template).
- **Review Workflow Blocking** – Review command no longer fails when file locations don't match frontmatter metadata. Auto-validation repairs inconsistencies before review.
- **Hardcoded Version** – `spec-kitty --version` now reads from package metadata, always shows correct installed version.

### Documentation

- **encoding-validation.md** (554 lines) – Complete guide covering:
  - Problem description with real examples
  - 5-layer architecture explanation
  - Testing procedures and troubleshooting
  - Migration guide for existing projects
  - API reference and performance considerations
- **plan-validation-guardrail.md** (202 lines) – Implementation details:
  - Problem and solution overview
  - Configuration instructions
  - Testing procedures
  - Benefits and future enhancements
- **task-metadata-validation.md** (350 lines) – Auto-repair workflow:
  - Lane mismatch detection and repair
  - CLI usage examples
  - Python API reference
  - Integration with review workflow
- **TESTING_REQUIREMENTS_ENCODING_AND_PLAN_VALIDATION.md** (1056 lines) – Functional test specifications:
  - 35+ test cases across 6 test suites
  - Coverage targets (85-95%)
  - Performance requirements
  - Edge case testing requirements

### Testing

- Added 7 unit tests for plan validation (all passing)
- Verified on real project (battleship): fixed 9 files with encoding issues
- Dashboard now loads successfully after encoding fixes
- Character mapping tests: smart quotes, ±, ×, ° all converted correctly

## [0.4.13] - 2025-11-13

### Fixed

- **CRITICAL: verify-setup ImportError (Issue #28)** – Fixed ImportError in `verify-setup` command caused by incorrect import statement in `verify_enhanced.py`. Changed `from . import detect_feature_slug, AcceptanceError` to `from .acceptance import detect_feature_slug, AcceptanceError`. This was a blocking bug that prevented users from running the diagnostic command.

## [0.4.12] - 2025-11-13

### Added

- **Version Flag** – Added `--version` and `-v` flags to display installed spec-kitty-cli version.
- **Dashboard Health Diagnostics** – Enhanced `spec-kitty diagnostics` to detect dashboard startup failures, test if dashboard can start, and report specific errors. Now catches issues like corrupted files, health check timeouts, and background process failures.

### Changed

- **Diagnostics Output** – Added Dashboard Health panel showing startup test results, PID tracking status, and specific failure reasons.

## [0.4.11] - 2025-11-13

### Fixed

- **PowerShell Python Quoting Bug (Issue #26)** – Fixed SyntaxError in PowerShell scripts caused by double-quote conflicts in embedded Python code. Changed all Python strings in `common.ps1` to use single quotes to avoid PowerShell string parsing conflicts.

### Added

- **PowerShell Syntax Guide** – Created comprehensive `templates/POWERSHELL_SYNTAX.md` with bash vs PowerShell syntax comparison table, common mistakes, and debugging tips for AI agents.
- **Conditional PowerShell Reference** – Enhanced `agent-file-template.md` to conditionally include PowerShell syntax reminders only for PowerShell projects, keeping bash contexts clean.

### Changed

- **AI Agent Context** – PowerShell-specific guidance now provided via separate reference document instead of cluttering bash-focused templates.

Fixes #26
Addresses #27

## [0.4.10] - 2025-11-13

### Fixed

- **CRITICAL: Missing missions directory in PyPI package** – Added `.kittify/missions/` to `pyproject.toml` force-include list. Previous release (0.4.9) was missing this directory, causing "Active mission directory not found" errors for all fresh installations.

## [0.4.9] - 2025-11-13

### Added

- **Diagnostics CLI Command** – New `spec-kitty diagnostics` command with human-readable and JSON output for comprehensive project health checks.
- **Dashboard Process Tracking** – Dashboard now stores process PID in `.dashboard` metadata file for reliable cleanup and monitoring.
- **Feature Collision Detection** – Added explicit warnings when creating features with duplicate names that would overwrite existing work.
- **LLM Context Documentation** – Enhanced all 13 command templates with location pre-flight checks, file discovery sections, and workflow context to prevent agents from getting lost.

### Changed

- **Dashboard Lifecycle** – Enhanced `ensure_dashboard_running()` to automatically clean up orphaned dashboard processes on initialization, preventing port exhaustion.
- **Feature Creation Warnings** – `create-new-feature.sh` now warns when git is disabled or features already exist, with clear JSON indicators for LLM agents.
- **Import Safety** – Fixed `detect_feature_slug` import path in diagnostics module to use correct module location.
- **Worktree Documentation** – Updated WORKTREE_MODEL.md to accurately describe `.kittify/` as a complete copy (not symlink) with disk space implications documented.

### Fixed

- **CRITICAL: Dashboard Process Orphan Leak** – Fixed critical bug where background dashboard processes were orphaned and accumulated until all ports were exhausted. Complete fix includes:
  - PIDs are captured and stored in `.dashboard` file (commit b8c7394)
  - Orphaned processes with .dashboard files are automatically cleaned up on next init
  - HTTP shutdown failures fall back to SIGTERM/SIGKILL with PID tracking
  - Port range cleanup scans for orphaned dashboards without .dashboard files (commit 11340a4)
  - Safe fingerprinting via health check API prevents killing unrelated services
  - Automatic retry with cleanup when port exhaustion detected
  - Failed startup processes are cleaned up (no orphans from Ctrl+C during health check)
  - Multi-project scenarios remain fully isolated (per-project PIDs, safe port sweeps)
  - Handles all orphan types: with metadata, without metadata, deleted temp projects
  - Prevents "Could not find free port" errors after repeated uses

- **Import Path Bug** – Fixed `detect_feature_slug` import in `src/specify_cli/dashboard/diagnostics.py` to import from `specify_cli.acceptance` instead of package root.

- **Worktree Documentation Accuracy** – Corrected WORKTREE_MODEL.md which incorrectly stated `.kittify/` was symlinked; it's actually a complete copy due to git worktree behavior.

### LLM Context Improvements

All command templates enhanced with consistent context patterns:
- **Location Pre-flight Checks**: pwd/git branch verification with expected outputs and correction steps
- **File Discovery**: Lists what files {SCRIPT} provides, output locations, and available context
- **Workflow Context**: Documents before/after commands and feature lifecycle integration

Templates updated:
- merge.md: CRITICAL safety check preventing merges from wrong location
- clarify.md, research.md, analyze.md: HIGH priority core workflow commands
- specify.md, checklist.md: Entry point and utility commands
- constitution.md, dashboard.md: Project-level and monitoring commands

### Testing

- ✅ Dashboard comprehensive test suite (34 tests, 100% coverage)
- ✅ All CLI commands validated
- ✅ Import paths verified
- ✅ Worktree behavior confirmed across test scenarios
- ✅ LLM context patterns applied consistently

### Security

- Dashboard process cleanup prevents resource exhaustion attacks
- Explicit warnings when creating duplicate features prevent silent data overwrite
- Git disabled warnings ensure users know when version control is unavailable

### Backward Compatibility

All changes are fully backward compatible:
- PID storage is optional (old `.dashboard` files still work)
- Feature collision detection is advisory (doesn't block creation)
- LLM context additions don't change command behavior
- Dashboard cleanup is automatic (users don't need to do anything)

## [0.4.12] - 2025-11-11

### Added

- **Core Service Modules** – Introduced `specify_cli.core.git_ops`, `project_resolver`, and `tool_checker` packages to host git utilities, project discovery, and tool validation logic with clean public APIs.
- **Test Coverage** – Added dedicated suites (`tests/specify_cli/test_core/test_git_ops.py`, `test_project_resolver.py`, `test_tool_checker.py`) covering subprocess helpers, path resolution, and tool validation flows.

### Changed

- **CLI Import Surface** – `src/specify_cli/__init__.py` now imports git, resolver, and tool helpers from the new core modules, slimming the monolith and sharing the implementations across commands.
- **Versioning Compliance** – `pyproject.toml` bumped to v0.4.12 to capture the core-service extraction and accompanying behavior changes.

## [0.4.11] - 2025-11-11

### Added

- **Template Test Suite** – New `tests/test_template/` coverage exercises template manager, renderer, and agent asset generator flows to guard the init experience.

### Changed

- **Template System Extraction** – Moved template discovery, rendering, and asset generation logic out of `src/specify_cli/__init__.py` into dedicated `specify_cli.template` modules with shared frontmatter parsing.
- **Dashboard Reuse** – Updated the dashboard scanner to consume the shared frontmatter parser so Kanban metadata stays in sync with CLI-generated commands.

## [0.4.10] - 2025-11-11

### Added

- **Core Modules** – Introduced `specify_cli.core.config` and `specify_cli.core.utils` to centralize constants, shared helpers, and exports for downstream packages.
- **CLI UI Package** – Moved `StepTracker`, arrow-key selection, and related utilities into `specify_cli.cli.ui`, enabling reuse across commands.
- **Test Coverage** – Added dedicated unit suites for the new core modules and CLI UI interactions (12 new tests).

### Changed

- **Package Structure** – Created foundational package directories for `core/`, `cli/`, `template/`, and `dashboard/`, including structured `__init__.py` exports.
- **Init Command Dependencies** – Updated `src/specify_cli/__init__.py` to consume the extracted modules, reducing monolith size and improving readability.
- **File Utilities** – Replaced ad-hoc directory creation/removal with safe helper functions to prevent duplication across commands.

## [0.4.8] - 2025-11-10

### Added

- **GitignoreManager Module** – New centralized system for managing .gitignore entries for AI agent directories, replacing fragmented approach.
- **Comprehensive Agent Protection** – Auto-protect ALL 12 AI agent directories (.claude/, .codex/, .opencode/, etc.) in .gitignore during init, not just selected ones.
- **Duplicate Detection** – Smart duplicate detection prevents .gitignore pollution when running init multiple times.
- **Cross-Platform Support** – Line ending preservation ensures .gitignore works correctly on Windows, macOS, and Linux.

### Changed

- **init Command Behavior** – Now automatically protects all AI agent directories instead of just selected ones, ensuring no sensitive data is accidentally committed.
- **Error Messages** – Improved error messages for permission issues with clear remediation steps (e.g., "Run: chmod u+w .gitignore").

### Fixed

- **Dashboard Markdown Rendering** – Fixed issue where .md files in Research and Contracts tabs were not rendered, now properly displays formatted markdown content.
- **Dashboard CSV Display** – Fixed CSV files not rendering in dashboard, now displays as formatted tables with proper styling and hover effects.

### Security

- **Agent Directory Protection** – All 12 known AI agent directories are now automatically added to .gitignore during init, preventing accidental commit of API keys, auth tokens, and other sensitive data.
- **Special .github/ Handling** – Added warning for .github/ directory which is used both by GitHub Copilot and GitHub Actions, reminding users to review before committing.

### Removed

- **Legacy Functions** – Removed `handle_codex_security()` and `ensure_gitignore_entries()` functions, replaced by comprehensive GitignoreManager class.

## [0.4.7] - 2025-11-07

### Added

- **Dashboard Diagnostics Page** – New diagnostics page showing real-time environment analysis, artifact location mismatches, and actionable recommendations.
- **CLI verify-setup Command** – New `spec-kitty verify-setup` command for comprehensive environment diagnostics in the terminal.
- **Worktree-Aware Resolution** – Added `resolve_worktree_aware_feature_dir()` function that intelligently detects and prefers worktree locations.
- **Agent Location Checks** – Standardized "CRITICAL: Location Requirement" sections in command templates with bash verification scripts.
- **Test Coverage** – Added comprehensive test suite for gitignore management and Codex security features with 9 test cases covering all edge cases.

### Changed

- **Command Templates** – Enhanced plan.md and tasks.md with explicit worktree location requirements and verification scripts.
- **Error Messages** – Improved bash script errors with visual indicators (❌ ERROR, 🔧 TO FIX, 💡 TIP) and exact fix commands.
- **Research Command** – Updated to use worktree-aware feature directory resolution.
- **Refactored Codex Security** – Extracted Codex credential protection logic into a dedicated `handle_codex_security()` function for better maintainability and testability.

### Fixed

- **Artifact Location Mismatch** – Fixed issue where agents create artifacts in wrong location, preventing them from appearing in dashboard.

## [0.4.5] - 2025-11-06

### Added

- **Agent Guidance** – Bundled a shared `AGENTS.md` ruleset that is copied into `.kittify/` so every generated command has a canonical place to point agents for path/encoding/git expectations.
- **Encoding Toolkit** – Introduced `scripts/validate_encoding.py` and new documentation to scan/fix Windows-1252 artifacts, plus a non-interactive init guide in `docs/non-interactive-init.md`.
- **Dashboard Assets** – Split the inline dashboard UI into static CSS/JS files and committed them with the release.

### Changed

- **CLI Help & Docs** – Expanded `spec-kitty init`, `research`, `check`, `accept`, and `merge` help text and refreshed README/index links to render correctly on PyPI.
- **Dashboard Runtime** – Hardened the dashboard server/CLI handshake with health checks, token-gated shutdown, and more resilient worktree detection.
- **Mission Handling** – Improved mission activation to fall back gracefully when symlinks are unavailable (e.g., Windows w/out dev mode) and aligned shell helpers with the new logic.

### Security

- **Codex Guardrails** – Automatically append `.codex/` to `.gitignore`, warn if `auth.json` is tracked, and reiterate the `CODEX_HOME` workflow to keep API credentials out of source control.

## [0.4.6] - 2025-11-06

### Fixed

- **PyYAML Dependency** – Added `pyyaml` to the core dependency list so mission loading works in clean environments (CI no longer fails installing the package).
- **PyPI README Links** – Restored absolute documentation links to keep images and references working on PyPI.

## [0.4.4] - 2025-11-06

### Security

- **Credential Cleanup** – Removed the committed `.codex` directory (OpenAI credentials) from the entire Git history and regenerated sanitized release assets.
- **Token Rotation** – Documented that all compromised keys were revoked and environments refreshed before reissuing packages.

### Changed

- **Release Artifacts** – Rebuilt GitHub release bundles and PyPI distributions from the cleaned history to ensure no secrets are present in published archives.

## [0.3.2] - 2025-11-03

### Added

- **Automated PyPI Release Pipeline** – Tag-triggered GitHub Actions workflow automatically builds, validates, and publishes releases to PyPI using `PYPI_API_TOKEN` secret, eliminating manual publish steps.
- **Release Validation Tooling** – `scripts/release/validate_release.py` CLI enforces semantic version progression, changelog completeness, and version/tag alignment in both branch and tag modes with actionable error messages.
- **Release Readiness Guardrails** – Pull request workflow validates version bumps, changelog entries, and test passage before merge; nightly scheduled checks monitor drift.
- **Comprehensive Release Documentation** – Complete maintainer guides covering secret management, branch protection, troubleshooting, and step-by-step release workflows.
- **Changelog Extraction** – `scripts/release/extract_changelog.py` automatically extracts version-specific release notes for GitHub Releases.
- **Release Test Suite** – 4 pytest tests validate branch mode, tag mode, changelog parsing, and version regression detection.

### Changed

- **GitHub Actions Workflows** – Updated `release.yml` with pinned dependency versions, proper workflow ordering (PyPI publish before GitHub Release), and checksums stored in `dist/SHA256SUMS.txt`.
- **Workflow Reliability** – Fixed heredoc syntax error in `protect-main.yml` that was causing exit code 127 failures.

### Security

- **Secret Hygiene** – PyPI credentials exclusively stored in GitHub Actions secrets with rotation guidance; no tokens in repository or logs; workflows sanitize outputs.
- **Workflow Permissions** – Explicit least-privilege permissions in all workflows (contents:write, id-token:write for releases; contents:read for guards).

## [0.3.1] - 2025-11-03

### Changed

- **Worktree-Aware Merge Flow** – `/spec-kitty merge` now detects when it is invoked from a Git worktree, runs the actual merge steps from the primary repository checkout, and surfaces clearer guidance when the target checkout is dirty.

### Documentation

- **Merge Workflow Guidance** – Updated templates and Claude workflow docs to describe the primary-repo hand-off during merges and reinforce the feature-worktree best practice.

## [0.3.0] - 2025-11-02

### Added

- **pip Installation Instructions** – All documentation now includes pip installation commands alongside uv, making Spec Kitty accessible to users who prefer traditional Python package management.
- **Multiple Installation Methods** – Documented three installation paths: PyPI (stable), GitHub (development), and one-time usage (pipx/uvx).

### Changed

- **Documentation Consistency** – Updated README.md, docs/index.md, docs/installation.md, and docs/quickstart.md to provide both pip and uv commands throughout.
- **Installation Recommendations** – PyPI installation now marked as recommended for stable releases, with GitHub source for development versions.

### Fixed

- **Packaging Issues** – Removed duplicate `.kittify` force-include that caused "Duplicate filename in local headers" errors on PyPI.
- **Test Dependencies** – Added `pip install -e .[test]` to workflows to ensure all project dependencies available for tests.

## [0.2.20] - 2025-11-02

### Added

- **Automated PyPI Release Pipeline** – Tag-triggered GitHub Actions workflow automatically builds, validates, and publishes releases to PyPI using `PYPI_API_TOKEN` secret, eliminating manual publish steps.
- **Release Validation Tooling** – `scripts/release/validate_release.py` CLI enforces semantic version progression, changelog completeness, and version/tag alignment in both branch and tag modes with actionable error messages.
- **Release Readiness Guardrails** – Pull request workflow validates version bumps, changelog entries, and test passage before merge; protect-main workflow blocks direct pushes to main branch.
- **Comprehensive Release Documentation** – Complete maintainer guides covering secret management, branch protection, troubleshooting, and step-by-step release workflows in README, docs, and inline help.
- **Enhanced PyPI Metadata** – Added project URLs (repository, issues, docs, changelog), keywords, classifiers, and license information to improve PyPI discoverability and presentation.
- **Changelog Extraction** – `scripts/release/extract_changelog.py` automatically extracts version-specific release notes for GitHub Releases.
- **Release Test Suite** – 4 pytest tests validate branch mode, tag mode, changelog parsing, and version regression detection.

### Changed

- **GitHub Actions Workflows** – Replaced legacy release workflow with modern PyPI automation supporting validation, building, checksums, GitHub Releases, and secure publishing.
- **Documentation Structure** – Added dedicated releases section to docs with readiness checklist, workflow references, and troubleshooting guides; updated table of contents.

### Security

- **Secret Hygiene** – PyPI credentials exclusively stored in GitHub Actions secrets with rotation guidance; no tokens in repository or logs; workflows sanitize outputs.
- **Workflow Permissions** – Explicit least-privilege permissions in all workflows (contents:write, id-token:write for releases; contents:read for guards).

## [0.2.3] - 2025-10-29

### Added

- **Mission system assets** – Bundled Software Dev Kitty and Deep Research Kitty mission definitions (commands, templates, constitutions) directly in the CLI package so `spec-kitty init` can hydrate missions without a network call.

### Changed

- Synced mission templates between the repository and packaged wheel to keep `/spec-kitty.*` commands consistent across `--ai` choices.

## [0.2.2] - 2025-10-29

### Added

- **Phase 0 Research command** – `spec-kitty research` (and `/spec-kitty.research`) scaffolds `research.md`, `data-model.md`, and CSV evidence logs using mission-aware templates so Deep Research Kitty teams can execute discovery workflows without leaving the guided process.
- **Mission templates for research** – Deep Research Kitty now ships reusable templates for research decisions, data models, and evidence capture packaged inside the Python wheel.

### Changed

- Updated `spec-kitty init` guidance, plan command instructions, and README workflow to include the new research phase between planning and task generation.

## [0.2.1] - 2025-10-29

### Added

- **Mission picker in init** - `spec-kitty init` now prompts for a mission (or accepts `--mission`) so projects start with Software Dev Kitty, Deep Research Kitty, or another bundled mission and record the choice in `.kittify/active-mission`.

### Changed

- Highlight the active mission in the post-init guidance while keeping the Codex export step as the final instruction.

## [0.2.0] - 2025-10-28

### Added

- **New `/spec-kitty.merge` command** - Completes the workflow by merging features into main branch and cleaning up worktrees automatically. Supports multiple merge strategies (merge, squash, rebase), optional push to origin, and configurable cleanup of worktrees and branches.
- **Worktree Strategy documentation** - Added comprehensive guide to the opinionated worktree approach for parallel feature development.
- **Dashboard screenshots** - Added dashboard-kanban.png and dashboard-overview.png showcasing the real-time kanban board.
- **Real-Time Dashboard section** - Added prominent dashboard documentation "above the fold" in README with screenshots and feature highlights.
- **Mission management CLI** - `spec-kitty mission list|current|switch|info` for inspecting and activating domain-specific missions inside a project.
- **Deep Research Kitty mission** - Research-focused templates (spec, plan, tasks, findings, prompts) and command guardrails for evidence-driven work.
- **Mission packaging** - Missions are now bundled in release archives and Python wheels so project initialization copies `.kittify/missions` automatically.

### Changed

- Updated command list in init output to show workflow order and include merge command.
- Updated `/spec-kitty.accept` description to clarify it verifies (not merges) features.
- Reordered slash commands documentation to reflect actual execution workflow.
- Updated maintainers to reflect fork ownership.
- Updated all repository references from `spec-kitty/spec-kitty` to `Priivacy-ai/spec-kitty`.
- Updated installation instructions to use GitHub repository URL instead of local directory.

### Fixed

- Removed invalid `multiple=True` parameter from `typer.Option()` in accept command that caused TypeError on CLI startup.
- Fixed "nine articles" claim in spec-driven.md to "core articles" (only 6 are documented).

### Removed

- Removed SECURITY.md (GitHub-specific security policies).
- Removed CODE_OF_CONDUCT.md (GitHub-specific contact information).
- Removed video overview section from README (outdated content).
- Removed plant emoji (🌱) branding from all documentation and code.
- Replaced logo_small.webp and logo_large.webp with actual spec-kitty cat logo.

## [0.1.3] - 2025-10-28

### Fixed

- Removed invalid `multiple=True` parameter from `typer.Option()` in accept command that caused TypeError on CLI startup.

## [0.1.2] - 2025-10-28

### Changed

- Rebranded the CLI command prefix from `speckitty` to `spec-kitty`, including package metadata and documentation references.
- Migrated template directories from `.specify` to `.kittify` and feature storage from `/specs` to `/kitty-specs` to avoid namespace conflicts with Spec Kit.
- Updated environment variables, helper scripts, and dashboards to align with the new `.kittify` and `kitty-specs` conventions.

## [0.1.1] - 2025-10-07

### Added

- New `/spec-kitty.accept` command (and `spec-kitty accept`) for feature-level acceptance: validates kanban state, frontmatter metadata, and artifacts; records acceptance metadata in `meta.json`; prints merge/cleanup instructions; and supports PR or local workflows across every agent.
- Acceptance helper scripts (`accept-feature.sh` / `.ps1`) and expanded `tasks_cli` utilities (`status`, `verify`, `accept`) for automation and integration with AI agents.
- Worktree-aware bootstrap workflow now defaults to creating per-feature worktrees, enabling parallel feature development with isolated sandboxes.
- Implementation prompts now require operating inside the feature’s worktree and rely on the lane helper scripts for moves/metadata, eliminating `git mv` conflicts; the dashboard also surfaces active/expected worktree paths.

### Changed

- `/spec-kitty.specify`, `/spec-kitty.plan`, and `/spec-kitty.clarify` now run fully conversational interviews—asking one question at a time, tracking internal coverage without rendering markdown tables, and only proceeding once summaries are confirmed—while continuing to resolve helper scripts via the `.kittify/scripts/...` paths.
- Added proportionality guidance so discovery, planning, and clarification depth scales with feature complexity (e.g., lightweight tic-tac-toe flows vs. an operating system build).
- `/spec-kitty.tasks` now produces both `tasks.md` and the kanban prompt files in one pass; the separate `/spec-kitty.task-prompts` command has been removed.
- Tasks are grouped into at most ten work packages with bundled prompts, reducing file churn and making prompt generation LLM-friendly.
- Both shell and PowerShell feature bootstrap scripts now stop with guidance to return `WAITING_FOR_DISCOVERY_INPUT` when invoked without a confirmed feature description, aligning with the new discovery workflow.

## [0.1.0] - 2025-10-07

### Changed

- `/spec-kitty.specify` and `/spec-kitty.plan` now enforce mandatory discovery interviews, pausing until you answer their question sets before any files are written.
- `/spec-kitty.implement` now enforces the kanban workflow (planned → doing → for_review) with blocking validation, new helper scripts, and a task workflow quick reference.
- Removed the legacy `specify` entrypoint; the CLI is now invoked exclusively via `spec-kitty`.
- Updated installation instructions and scripts to use the new `spec-kitty-cli` package name and command.
- Simplified local template overrides to use the `SPEC_KITTY_TEMPLATE_ROOT` environment variable only.

## [0.0.20] - 2025-10-07

### Changed

- Renamed the primary CLI entrypoint to `spec-kitty` and temporarily exposed a legacy `specify` alias for backwards compatibility.
- Refreshed documentation, scripts, and examples to use the `spec-kitty` command by default.

## [0.0.19] - 2025-10-07

### Changed

- Rebranded the project as Spec Kitty, updating CLI defaults, docs, and scripts while acknowledging the original GitHub Spec Kit lineage.
- Renamed all slash-command prefixes and generated artifact names from `/speckit.*` to `/spec-kitty.*` to match the new branding.

### Added

- Refreshed CLI banner text and tagline to reflect spec-kitty branding.

## [0.0.18] - 2025-10-06

### Added

- Support for using `.` as a shorthand for current directory in `spec-kitty init .` command, equivalent to `--here` flag but more intuitive for users.
- Use the `/spec-kitty.` command prefix to easily discover Spec Kitty-related commands.
- Refactor the prompts and templates to simplify their capabilities and how they are tracked. No more polluting things with tests when they are not needed.
- Ensure that tasks are created per user story (simplifies testing and validation).
- Add support for Visual Studio Code prompt shortcuts and automatic script execution.
- Allow `spec-kitty init` to bootstrap multiple AI assistants in one run (interactive multi-select or comma-separated `--ai` value).
- When running from a local checkout, `spec-kitty init` now copies templates directly instead of downloading release archives, so new commands are immediately available.

### Changed

- All command files now prefixed with `spec-kitty.` (e.g., `spec-kitty.specify.md`, `spec-kitty.plan.md`) for better discoverability and differentiation in IDE/CLI command palettes and file explorers
