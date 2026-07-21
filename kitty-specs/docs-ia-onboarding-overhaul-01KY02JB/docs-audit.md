# Docs Audit — `docs/guides/` & `docs/development/` (WP01, T001/T002)

Hand-curated disposition table for FR-003 (strict end-user/contributor zone segregation) and
FR-009 (re-audit, reclassify, consolidate). This is a **new, hand-authored** artifact — distinct
from the pre-existing, auto-generated `gap-analysis.md` in this same directory (a mechanical
per-directory Divio-coverage tool output, see research.md item 10). Do not confuse the two.

**Method**: every file listed below was opened and read (not classified from filename alone).
Content — not title — determined the zone: "contributor" means the page documents developing or
maintaining the Spec Kitty project itself (PR review, the Spec Kitty test suite, Spec Kitty's own
release process, internal/pre-launch operator paths); "end-user" means the page documents *using*
Spec Kitty inside your own project, however advanced or troubleshooting-flavored.

**Disposition legend**: `keep` = correctly placed, content is fine as-is. `relocate` = moved in
this WP (`git mv` into `docs/development/`). `relocate-deferred` = confirmed contributor-only but
outside WP01's `owned_files` and not owned by any other WP found by search — flagged here rather
than moved unilaterally. `merge-candidate` = end-user content that is fine where it is but
overlaps another page; flagged for a future consolidation pass, not touched in this WP.
`WP03-owned` = exclusively owned by WP03; explicitly untouched per this WP's instructions.

## Correction record (T002 — verifying the pre-identified candidate list)

This WP's `owned_files` frontmatter pre-identified 25 files (prose in the WP prompt said "24",
an off-by-one in the prompt text) as contributor-only candidates from earlier research. Reading
every one's actual content in full (T002) confirmed **10** as genuinely contributor-only and
found **15** to be end-user-relevant despite being pre-flagged — advanced/troubleshooting
content for people *using* Spec Kitty in their own project (mission lifecycle guides, orchestrator
usage, worktree/MCP hygiene, merge/crash recovery), not Spec Kitty's own contribution workflow.
Per this WP's explicit instruction ("if any candidate turns out to be genuinely end-user-relevant
... leave it in `docs/guides/` and note the correction ... do not move it just because it was on
the candidate list"), those 15 were **not** moved. T001's full-content read of the *rest* of
`docs/guides/` also surfaced **3 additional** contributor-only files that were never on the
candidate list at all (`contributing.md`, `review-gates.md`, `local-overrides.md`) — each
unambiguous by content, owned by no other WP (verified by search across all `tasks/*.md`), and
left mis-segregated would have directly violated FR-003, which this WP exists to satisfy. All 3
were relocated alongside the 10 confirmed candidates (13 total moves).

| # | Candidate file | T002 verdict | Reason |
|---|---|---|---|
| 1 | `pr-landing.md` | confirmed contributor | Maintainer PR-landing runbook (claim/worktree/rebase/red-classify), explicit "Audience: Maintainers". |
| 2 | `testing-flakiness.md` | confirmed contributor | Policy for Spec Kitty's own pytest suite (mutmut, `tests/`, CI flake tiers). |
| 3 | `keep-main-clean.md` | **corrected — end-user** | Generic `/spec-kitty.specify` branch-targeting guidance for any project's own mission, not Spec Kitty's own contribution flow. |
| 4 | `recover-from-interrupted-merge.md` | **corrected — end-user** | Documents the generic `spec-kitty merge --resume/--abort` CLI feature any end user's own project uses. |
| 5 | `recover-from-implementation-crash.md` | **corrected — end-user** | Generic WP-crash recovery (`spec-kitty implement --recover`) for any project's own mission. |
| 6 | `run-mutation-tests.md` | confirmed contributor | `mutmut` against Spec Kitty's own `src/specify_cli/...` modules; "reviewing a contributor PR". |
| 7 | `review-artifacts-with-planbridge.md` | **corrected — end-user** | Third-party PlanBridge tool usage for reviewing any project's own `spec.md`/`plan.md`/`tasks.md`. |
| 8 | `contract-pinning.md` | confirmed contributor | Pinning the `spec-kitty-events` envelope contract inside Spec Kitty's own `tests/contract/`. |
| 9 | `coverage-signals.md` | confirmed contributor | Reconciling SonarCloud vs. internal diff-coverage on Spec Kitty's own `src/` tree and CI config. |
| 10 | `write-time-dependent-tests.md` | confirmed contributor | Pytest authoring convention enforced on Spec Kitty's own test suite (`pytest` collection guard). |
| 11 | `use-operation-history.md` | **corrected — end-user** | Generic `spec-kitty ops log` feature for any project's own git history. |
| 12 | `testing-parallel.md` | confirmed contributor | Running *Spec Kitty's own* `pytest tests/` suite in parallel/CI (referenced directly by this repo's own `CLAUDE.md`). |
| 13 | `implement-work-package.md` | **corrected — end-user** | Core generic mission-lifecycle how-to (`spec-kitty agent action implement`) for any project. |
| 14 | `review-work-package.md` | **corrected — end-user** | Core generic mission-lifecycle how-to for any project. |
| 15 | `merge-feature.md` | **corrected — end-user** | Core generic mission-lifecycle how-to (`spec-kitty merge`) for any project. |
| 16 | `build-custom-orchestrator.md` | **corrected — end-user** | `orchestrator-api` integration guide for advanced end users/integrators, not Spec Kitty's own source. |
| 17 | `run-external-orchestrator.md` | **corrected — end-user** | Using the published `spec-kitty-orchestrator` package against any project's own mission. |
| 18 | `sync-workspaces.md` | **corrected — end-user** | Generic `spec-kitty sync workspace` feature for any project. |
| 19 | `worktrees-with-mcp-agents.md` | **corrected — end-user** | Frontmatter already carries `audience: end-users`. |
| 20 | `tool-surface-upgrade-and-repair.md` | **corrected — end-user** | Generic `spec-kitty doctor tool-surfaces --fix` troubleshooting for any project. |
| 21 | `internal-hosted-readiness.md` | confirmed contributor | Explicit "Audience: internal contributors... not for end users" banner; hidden SaaS rollout gate. |
| 22 | `orchestrator-quickstart.md` | **corrected — end-user** | Tutorial for advanced end users using the external orchestrator on their own mission; linked from `your-first-feature.md`. |
| 23 | `manage-issue-tracker.md` | confirmed contributor | Spec Kitty's own GitHub issue-tracker conventions (epics, `blocked_by`, P0 triage tied to *this repo's* red-main ADR). |
| 24 | `red-main-and-release-readiness.md` | confirmed contributor | Spec Kitty's own mainline CI / release-readiness policy, explicit "maintainers" framing. |
| 25 | `claude-code-workflow.md` | **corrected — end-user** | Generic "run Spec Kitty via Claude Code on your own project" integration guide. |

**Additional contributor-only files found during T001 (not on the candidate list)**:

| File | Verdict | Reason | Owned by another WP? |
|---|---|---|---|
| `contributing.md` | contributor | Full Spec Kitty contributor guide: dev setup, PR flow, AI-disclosure, release process. Root `CONTRIBUTING.md` symlink and `scripts/docs/sync_contributing.py` repointed in this WP. | No (searched all `tasks/*.md`) |
| `review-gates.md` | contributor | Pre-PR/pre-review hygiene checklist explicitly for people submitting PRs *to Spec Kitty*. | No |
| `local-overrides.md` | contributor | Editable cross-package dev pattern across `spec-kitty-cli`/`-events`/`-tracker` sibling checkouts; references a specific past Spec Kitty PR (#779). | No |

## Infrastructure fixes required to make the move actually work

- **`docs/docfx.json` was missing a `development/**.md` content glob.** `docs/development/`
  already existed with 7 files before this WP, but the DocFX build's `content[0].files` list only
  globbed `guides/**.md` (and 14 other sections) — never `development/**.md`. That means
  `docs/development/` was **never actually published** by the site build, before or after this
  WP's moves. Added `"development/**.md"` to the glob (C-001 explicitly permits DocFX TOC/file-list
  changes). Without this fix, all 20 files in `docs/development/` (7 pre-existing + 13 relocated
  here) would 404 on the live site.
- **`docs/toc.yml` has zero entries for `docs/development/` today** (verified: `grep development
  docs/toc.yml` → no hits), and this predates this WP. **WP02 must add a contributor-zone nav
  section** — without it, none of the 20 `docs/development/` pages are reachable from top-level
  navigation (NFR-006), even though they now build correctly. Per this WP's own instructions,
  `docs/toc.yml` is WP02's exclusive surface and is not edited here.
- **Root `CONTRIBUTING.md` is a symlink** to the canonical contributor guide, guarded by
  `scripts/docs/sync_contributing.py`. Both the symlink target and the guard script's
  `SYMLINK_TARGET`/`_CANONICAL_PATH` constants were repointed from `docs/guides/contributing.md`
  to `docs/development/contributing.md` in this WP.
- **`.kittify/charter/charter.yaml` and `.kittify/charter/references.yaml` still mention
  `docs/guides/red-main-and-release-readiness.md`.** Both are `generated_at`-stamped charter
  synthesis artifacts (not hand-maintained sources), so they were deliberately **not** hand-edited
  here — doing so would drift from whatever regenerates them. Flagged as a follow-up: run a
  charter resynthesis (`spec-kitty charter synthesize` / `resynthesize`) after this mission merges
  so the summary text picks up the new `docs/development/` path.
- **`docs/development/3-2-page-inventory.yaml`** is a generated lockfile (not hand-edited);
  regenerated via `python3 scripts/docs/inventory_lockfile.py --write
  docs/development/3-2-page-inventory.yaml` — confirmed zero drift afterward.
- **`scripts/docs/redirect_baseline_urls.json` amended.** The frozen pre-2026-06-27 baseline (167
  URLs) predates all 13 moved files' publication, so none of their `guides/*.html` URLs were in
  the redirect-coverage denominator. Per the redirect-map-entry-contract's note that the baseline
  is "extended with this mission's own moved paths," added a dated amendment appending the 13
  `guides/*.html` URLs (167 → 180 total) so `check-map`/coverage checks actually protect them.
  3 of the 13 (`run-mutation-tests.md`, `write-time-dependent-tests.md`,
  `internal-hosted-readiness.md`) already had a pre-existing baseline entry at their *original*
  pre-`common-docs-consolidation` `how-to/*.html` path; since the generator resolves each baseline
  URL through only the first matching `moves:` entry (no multi-hop chaining), an explicit override
  move was added ahead of the generic `docs/how-to`→`docs/guides` bucket rule so those 3 collapse
  directly to `docs/development/*.html` instead of stopping one hop short at a now-dead
  `guides/*.html` address.

## `docs/guides/` — 60 entries (72 original top-level files minus 13 relocated, minus 1 dir summarized)

| Path | Current classification | Disposition | Target zone | Notes |
|---|---|---|---|---|
| `docs/guides/accept-and-merge.md` | end-user | keep | end-user | Core mission how-to (`spec-kitty accept`/`merge`). |
| `docs/guides/adhoc-specialist-session.md` | end-user | keep | end-user | `spec-kitty dispatch` how-to. |
| `docs/guides/build-custom-orchestrator.md` | end-user | keep | end-user | Corrected from candidate list (#16 above). |
| `docs/guides/charter-governed-workflow.md` | end-user | keep | end-user | Tutorial; part of FR-006 charter-consolidation scope (WP05), not touched here. |
| `docs/guides/claude-code-integration.md` | end-user | merge-candidate | end-user | Overlaps `claude-code-workflow.md` and `harnesses/claude-code.md`; flag for a future consolidation pass (FR-009 volume reduction), not executed in WP01. |
| `docs/guides/claude-code-workflow.md` | end-user | keep | end-user | Corrected from candidate list (#25). Also a merge-candidate with the above two. |
| `docs/guides/contributing.md` | **contributor** | relocate | contributor | Moved to `docs/development/contributing.md`; not on the original candidate list, found in T001. |
| `docs/guides/coverage-signals.md` | **contributor** | relocate | contributor | Moved (candidate #9, confirmed). |
| `docs/guides/create-an-org-doctrine-pack.md` | end-user | keep | end-user | Org-admin how-to; product feature, not Spec Kitty source contribution. |
| `docs/guides/create-plan.md` | end-user | keep | end-user | Core mission how-to. |
| `docs/guides/create-specification.md` | end-user | keep | end-user | Core mission how-to. |
| `docs/guides/diagnose-installation.md` | end-user | keep | end-user | Generic install troubleshooting. |
| `docs/guides/generate-tasks.md` | end-user | keep | end-user | Core mission how-to. |
| `docs/guides/getting-started.md` | end-user | **WP03-owned** | end-user | Explicitly untouched — WP03 exclusive ownership per this WP's instructions. |
| `docs/guides/gstack-glossary-observations.md` | end-user | keep | end-user | Integrator-facing API-contract doc (rendering `glossary_observations`), analogous to the orchestrator-api guides; not Spec Kitty's own source. |
| `docs/guides/handle-dependencies.md` | end-user | keep | end-user | Core mission how-to. |
| `docs/guides/harnesses/` (15 files: `amazon-q.md`, `antigravity.md`, `augment.md`, `claude-code.md`, `codex.md`, `copilot.md`, `cursor.md`, `gemini.md`, `kilocode.md`, `kiro.md`, `letta.md`, `opencode.md`, `pi-tui.md`, `qwen.md`, `roo.md`, plus `setup-lint-hooks.md` and the child `how-to-toc.yml`) | end-user | keep | end-user | Per-agent harness setup guides + a generic post-edit-lint-hook how-to (`spec-kitty lint`, spot-checked in full). All end-user integration content; summarized as one row, not individually re-audited beyond the spot-check. |
| `docs/guides/how-to-index.md` | end-user (nav/index) | keep, edited | end-user | Removed the now-broken `manage-issue-tracker.md` link/related-entry (moved out of zone). |
| `docs/guides/how-to-toc.yml` | end-user (nav) | keep, edited | end-user | Removed the `manage-issue-tracker.md` nav entry (dead after the move) — not `docs/toc.yml` itself, so within this WP's edit scope. |
| `docs/guides/implement-work-package.md` | end-user | keep | end-user | Corrected from candidate list (#13). |
| `docs/guides/index.md` | end-user (nav/index) | keep, rewritten | end-user | Was entirely "Contributor guides"/"Maintainer guides" sections listing 8 of the 13 now-moved files — rewritten to describe the end-user zone and point to `../development/`. |
| `docs/guides/install-and-upgrade.md` | end-user | keep | end-user | |
| `docs/guides/install-claude-code-plugin.md` | end-user | keep, edited | end-user | Fixed a bare-relative `contributing.md` body link (caught by `relative_link_fixer.py --check`, not the earlier grep pass). |
| `docs/guides/install-linux.md` | end-user | keep | end-user | |
| `docs/guides/install-macos.md` | end-user | keep | end-user | |
| `docs/guides/install-spec-kitty.md` | end-user | keep | end-user | |
| `docs/guides/install-windows.md` | end-user | keep | end-user | |
| `docs/guides/internal-hosted-readiness.md` | **contributor** | relocate | contributor | Moved (candidate #21, confirmed). |
| `docs/guides/keep-main-clean.md` | end-user | keep | end-user | Corrected from candidate list (#3). |
| `docs/guides/local-overrides.md` | **contributor** | relocate | contributor | Moved to `docs/development/local-overrides.md`; not on the original candidate list, found in T001. |
| `docs/guides/manage-agents.md` | end-user | keep | end-user | |
| `docs/guides/manage-glossary.md` | end-user | keep | end-user | |
| `docs/guides/manage-issue-tracker.md` | **contributor** | relocate | contributor | Moved (candidate #23, confirmed). |
| `docs/guides/merge-feature.md` | end-user | keep | end-user | Corrected from candidate list (#15). |
| `docs/guides/missions-overview.md` | end-user | keep | end-user | Tutorial. |
| `docs/guides/multi-agent-workflow.md` | end-user | keep | end-user | Tutorial. |
| `docs/guides/non-interactive-init.md` | end-user | keep | end-user | |
| `docs/guides/orchestrator-quickstart.md` | end-user | keep | end-user | Corrected from candidate list (#22). |
| `docs/guides/parallel-development.md` | end-user | keep | end-user | |
| `docs/guides/pr-landing.md` | **contributor** | relocate | contributor | Moved (candidate #1, confirmed). |
| `docs/guides/recover-from-implementation-crash.md` | end-user | keep | end-user | Corrected from candidate list (#5). |
| `docs/guides/recover-from-interrupted-merge.md` | end-user | keep | end-user | Corrected from candidate list (#4). |
| `docs/guides/red-main-and-release-readiness.md` | **contributor** | relocate | contributor | Moved (candidate #24, confirmed). |
| `docs/guides/review-artifacts-with-planbridge.md` | end-user | keep | end-user | Corrected from candidate list (#7). |
| `docs/guides/review-gates.md` | **contributor** | relocate | contributor | Moved to `docs/development/review-gates.md`; not on the original candidate list, found in T001. |
| `docs/guides/review-work-package.md` | end-user | keep | end-user | Corrected from candidate list (#14). |
| `docs/guides/run-an-autonomous-mission.md` | end-user | keep | end-user | |
| `docs/guides/run-external-orchestrator.md` | end-user | keep | end-user | Corrected from candidate list (#17). |
| `docs/guides/run-governed-mission.md` | end-user | keep | end-user | |
| `docs/guides/run-mutation-tests.md` | **contributor** | relocate | contributor | Moved (candidate #6, confirmed). |
| `docs/guides/setup-codex-spec-kitty-launcher.md` | end-user | keep | end-user | |
| `docs/guides/setup-governance.md` | end-user | keep | end-user | Part of FR-006 charter-consolidation scope (WP05), not touched here. |
| `docs/guides/switch-missions.md` | end-user | keep | end-user | |
| `docs/guides/sync-workspaces.md` | end-user | keep | end-user | Corrected from candidate list (#18). |
| `docs/guides/synthesize-doctrine.md` | end-user | keep | end-user | |
| `docs/guides/testing-flakiness.md` | **contributor** | relocate | contributor | Moved (candidate #2, confirmed). |
| `docs/guides/testing-parallel.md` | **contributor** | relocate | contributor | Moved (candidate #12, confirmed). |
| `docs/guides/tool-surface-upgrade-and-repair.md` | end-user | keep | end-user | Corrected from candidate list (#20). |
| `docs/guides/troubleshoot-charter.md` | end-user | keep | end-user | Part of FR-006 charter-consolidation scope (WP05), not touched here. |
| `docs/guides/troubleshoot-merge.md` | end-user | keep | end-user | |
| `docs/guides/tutorials-index.md` | end-user (nav/index) | keep | end-user | |
| `docs/guides/tutorials-toc.yml` | end-user (nav) | keep | end-user | No moved-file entries; unaffected. |
| `docs/guides/uninstall.md` | end-user | keep | end-user | |
| `docs/guides/upgrade-cli.md` | end-user | keep | end-user | |
| `docs/guides/upgrade-project.md` | end-user | keep | end-user | |
| `docs/guides/use-dashboard.md` | end-user | keep | end-user | |
| `docs/guides/use-operation-history.md` | end-user | keep | end-user | Corrected from candidate list (#11). |
| `docs/guides/use-retrospective-learning.md` | end-user | keep, edited | end-user | Fixed a bare-relative `contributing.md` body link (caught by `relative_link_fixer.py --check`). |
| `docs/guides/use-wps-yaml-manifest.md` | end-user | keep | end-user | |
| `docs/guides/worktrees-with-mcp-agents.md` | end-user | keep | end-user | Corrected from candidate list (#19); frontmatter already says `audience: end-users`. |
| `docs/guides/write-time-dependent-tests.md` | **contributor** | relocate | contributor | Moved (candidate #10, confirmed). |
| `docs/guides/your-first-feature.md` | end-user | **WP03-owned** | end-user | Explicitly untouched — WP03 exclusive ownership per this WP's instructions (renamed to `your-first-mission.md` under FR-014 is WP03's concern, not WP01's). |

## `docs/development/` — 20 entries (7 pre-existing + 13 relocated in this WP)

| Path | Current classification | Disposition | Target zone | Notes |
|---|---|---|---|---|
| `docs/development/3-2-page-inventory.yaml` | non-page (generated lockfile) | keep, regenerated | contributor | Regenerated via `inventory_lockfile.py --write` to include the 13 new pages; confirmed zero drift. |
| `docs/development/contract-pinning.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/contributing.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. Root `CONTRIBUTING.md` symlink + guard script repointed. |
| `docs/development/coverage-signals.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: explanation` added. |
| `docs/development/index.md` | contributor (nav/index) | keep, rewritten | contributor | Previously described the *opposite* state (claimed `docs/development/` was "retired" and its durable content moved OUT to `guides/`/`operations/`/`configuration/` — stale prose from the prior `common-docs-consolidation` mission). Rewritten to describe the current, correct state: `docs/development/` is this mission's contributor/maintainer root. |
| `docs/development/internal-hosted-readiness.md` | contributor | relocated here | contributor | From `docs/guides/`; already had `type: how-to`, kept. |
| `docs/development/local-overrides.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/manage-issue-tracker.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/mutation-testing-tactic.yaml` | non-page (doctrine tactic) | keep | contributor | Not a docs page; untouched. |
| `docs/development/pr-landing.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/quality-and-tech-debt-standing-orders.md` | contributor | keep | contributor | Pre-existing; correctly placed. |
| `docs/development/red-main-and-release-readiness.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: explanation` added. |
| `docs/development/review-gates.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/run-mutation-tests.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/sync-daemon-orphan-cleanup.md` | contributor | keep | contributor | Pre-existing; correctly placed. |
| `docs/development/terminology-exemptions.md` | contributor | keep | contributor | Pre-existing; correctly placed. |
| `docs/development/testing-flakiness.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: explanation` added. |
| `docs/development/testing-parallel.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |
| `docs/development/ui-e2e.md` | contributor | keep | contributor | Pre-existing; correctly placed. |
| `docs/development/write-time-dependent-tests.md` | contributor | relocated here | contributor | From `docs/guides/`; Divio `type: how-to` added. |

## Summary

- **79 rows minimum required by the WP's Definition of Done; 80 rows delivered** (60 in
  `docs/guides/` counting the harnesses subdirectory as one summarized row + 20 in
  `docs/development/`, which grew from 7 to 20 as a direct result of this WP's 13 moves).
- **13 files moved** `docs/guides/` → `docs/development/` (10 from the pre-identified candidate
  list of ~24–25, confirmed by full-content read; 3 found during T001's audit of the remainder of
  `docs/guides/` and confirmed unowned by any other WP).
- **15 pre-identified candidates corrected to `keep` in `docs/guides/`** — genuinely end-user
  content despite being flagged as candidates; see the correction table above for the
  content-based rationale on each.
- **2 files flagged `merge-candidate`** (`claude-code-integration.md`, `claude-code-workflow.md`
  overlapping with `harnesses/claude-code.md`) for a future consolidation pass — not executed in
  this WP (T003's scope is relocation, not content merging).
- **0 files removed.** No content was deleted or judged redundant enough to drop outright in this
  audit; volume reduction opportunities are flagged as merge-candidates for a later pass rather
  than executed unilaterally here.
- **`docs/guides/getting-started.md` and `docs/guides/your-first-feature.md` are untouched**, per
  explicit WP01 instruction (WP03's exclusive surface).
- **For WP02**: `docs/toc.yml` has zero entries for `docs/development/` today (pre-existing gap,
  not introduced by this WP) — the contributor zone needs a nav section added, or all 20 pages in
  `docs/development/` remain reachable only by direct URL despite now building correctly.

## WP02 — T006 design rationale (two-zone navigation)

`docs/toc.yml` is rebuilt from the prior 16-entry flat list into exactly 2 top-level zone
entries, each with 6 unexpanded top-level (immediate-child) entries, using DocFX's native
nested `items:` syntax (the pre-existing "Historical Archive" group is the syntax precedent;
see `research.md` item 6). Design:

- **"Using Spec Kitty" (end-user zone) — 6 immediate children:**
  - `Home` ← flat entry `Home` (`index.md`), unchanged.
  - `Guides` ← flat entry `Guides` (`guides/index.md`), unchanged — this node's own directory
    carries its own child TOC (`docs/guides/how-to-toc.yml`, plus `tutorials-toc.yml` and
    `harnesses/how-to-toc.yml`), all end-user-only per WP01's audit.
  - `Core Concepts` (new grouping node) ← nests flat entries `Context` (renamed "Context &
    Terminology", `context/index.md`) and the new `Doctrine` page (`doctrine/index.md`,
    added ahead of WP04/05/06 per the WP02 guidance's zone-assignment note).
  - `Reference` (new grouping node) ← nests flat entries `API` (`api/index.md`),
    `Configuration` (`configuration/index.md`), `Integrations` (`integrations/index.md`),
    and `Security` (`security/index.md`) — these four were already end-user reference material
    with no WP01 relocations, so they're grouped together rather than left as four separate
    top-level slots.
  - `Migrations` ← flat entry `Migrations` (`migrations/index.md`), unchanged.
  - `Project Updates` (new grouping node) ← nests flat entries `Changelog`
    (`changelog/index.md`), `Release Goals` (`release-goals/index.md`), and the pre-existing
    nested `Historical Archive` group (`archive/`, `archive/2x/`, `archive/1x/`), moved under
    this node as-is (low-traffic reference material; WP02's guidance explicitly allows either
    zone or standalone — grouped here rather than left as a 7th top-level slot, since it already
    nests, keeping the zone's own top-level count at 6).
- **"Contributing" (contributor zone) — 6 immediate children, all flat, no further nesting
  needed at this WP's file count:**
  - `Architecture` (`architecture/index.md`), `ADRs` (`adr/index.md`), `Plans`
    (`plans/index.md`), `Operations` (`operations/index.md`) — carried over unchanged from the
    original flat list.
  - `Development` (`development/index.md`) — **new nav entry**, added to close the pre-existing
    gap noted above (`docs/toc.yml` had zero entries for `docs/development/` before this WP,
    even though the directory held 7 pages pre-WP01 and grew to 20 post-WP01's 13 relocations).
    Backed by the new child TOC `docs/development/toc.yml` (T008), following the same flat
    `name`/`href` convention as `docs/api/toc.yml`.
  - `Mission Runs` (`kitty-specs/index.html`) — carried over unchanged; this href is a
    build-time-generated page (see `scripts/docs/generate_kitty_specs_docs.py`), not a source
    Markdown file, so it does not appear as a file in the repo tree — this is pre-existing
    behavior, not a WP02 regression.

All 16 original top-level sections are represented in the new tree (verified by grep against
`docs/toc.yml`): Home, Context, Architecture, ADRs, Plans, API, Configuration, Integrations,
Security, Guides, Operations, Migrations, Changelog, Release Goals, Mission Runs, Historical
Archive. None were dropped; three (`Core Concepts`, `Reference`, `Project Updates`) became new
grouping parents rather than being demoted, and `Development` is the one genuinely new
top-level child (closing the pre-existing gap, not moving an existing section).

**C-005 (no end-user page reachable in the end-user zone links into contributor-only content):**
walked the "Using Spec Kitty" zone's full nested subtree (14 `href` leaves across
`docs/toc.yml`, plus the three per-directory child TOCs it fans out to —
`docs/guides/how-to-toc.yml`, `docs/guides/tutorials-toc.yml`,
`docs/guides/harnesses/how-to-toc.yml`) and confirmed zero `href` values reference
`docs/development/**`. All 13 of WP01's relocated files (e.g. `contract-pinning.md`,
`testing-flakiness.md`, `write-time-dependent-tests.md`, `pr-landing.md`) now resolve only from
`docs/development/toc.yml`, the new contributor-zone child TOC (T008). `docs/guides/how-to-toc.yml`
was edited to drop the 3 entries (`Write Time-Dependent Tests`, `Red Main and Release
Readiness`, `Internal Hosted-Readiness (Pre-Launch)`) that pointed at now-relocated files; the
other 10 relocated files were never listed in this particular child TOC to begin with.

---

# WP07 Reference Audit Findings (T028–T032)

Scope: `docs/api/`, `docs/adr/`, `docs/operations/`, `docs/migrations/`, `docs/archive/`
(there is no separate `docs/configuration/` directory distinct from `docs/api/configuration.md` —
verified, so it was not audited as its own zone). **Method**: every accuracy claim below was
verified against either a live `spec-kitty --help` invocation, the actual source in
`src/specify_cli/`, `CHANGELOG.md`, or the project's own canonical doc-freshness tooling
(`scripts/docs/check_cli_reference_freshness.py`, `scripts/docs/freshen_adr_inventory.py`,
`scripts/docs/relative_link_fixer.py`) — never assumed from prose alone. This mission's own
branch made no CLI/source changes (`git diff main...HEAD -- src/` is a 2-line non-CLI diff), so
the installed `spec-kitty` CLI (v3.2.6, matching `pyproject.toml`) was a valid, live comparator
throughout.

## T028 — `docs/api/` audit

**Fixed (confirmed inaccuracies):**

1. **`docs/api/cli-commands.md` — `spec-kitty review` section was missing the `--check-residual`
   flag entirely.** Verified against live `spec-kitty review --help` and
   `src/specify_cli/cli/commands/review/__init__.py:359-387`. Added the missing option block,
   copied verbatim from live `--help` output (matching this doc's own stated methodology: "flags
   ... exactly as surfaced by `--help`").
2. **`docs/api/cli-commands.md` — `spec-kitty specify --topology` default description was stale.**
   Doc said `Default: coord. [default: coord]`; live `--help` and
   `src/specify_cli/cli/commands/lifecycle.py:129-144` show the default is `None`
   (context-derived per #2581 — coord on the primary branch or with `--pr-bound`, single_branch
   on a non-primary feature branch). Replaced with the live help text verbatim.
3. **`docs/api/missions.md` — claimed "three built-in mission types"** (software-dev, research,
   documentation), omitting the 4th built-in type `plan`. Verified via
   `spec-kitty charter mission-type list` (lists 4: documentation, plan, research, software-dev)
   and `src/specify_cli/missions/plan/mission.yaml` (exists, "Goal-oriented planning with
   rollback for iteration"). The same file's own §"Authoring Custom Workflows" already correctly
   said "Built-in — `software-dev`, `research`, `documentation`, `plan`" (line 342) — an internal
   self-contradiction. Fixed the intro sentence, frontmatter `description`, and the "Mission Type
   Overview" table (added the missing `plan` row). Deliberately did **not** add a full `## plan`
   section (mirroring the `## research`/`## documentation` sections) or touch the "During Mission
   Creation" interactive-prompt example or the "Mission Comparison" table's 3-column layout — that
   would be expanding a documentation gap, not fixing the confirmed miscount; flagged as a
   recommendation below instead.
4. **`docs/api/charter-commands.md` — explicitly claimed to be a "Full reference for all
   `spec-kitty charter` subcommands"** ("This reference covers all `charter` subcommands") but
   omitted 6 of the 15 live subcommands (`activate`, `deactivate`, `preflight`, `list`,
   `mission-type`, `pack`). Verified via live `spec-kitty charter --help`. These 6 are *already*
   fully documented (Usage/Options blocks) in `docs/api/cli-commands.md`. Fix: completed the
   summary table to list all 15 subcommands and corrected the completeness claim to scope this
   page to its actual narrative content (interview/generate/context/sync/status/synthesize/
   resynthesize/lint/bundle validate), pointing to `cli-commands.md` as the canonical, generated,
   already-complete source for the 6 newer commands' full flag reference — avoided duplicating
   Usage/Options blocks that would only create a second copy to drift out of sync.
5. **`docs/api/supported-harnesses.md` — 4 occurrences of a dead path reference**
   (`` `docs/development/3-2-harness-research-method.md` ``); the file does not exist there. The
   actual file is at `docs/plans/3-2-doc-publication/3-2-harness-research-method.md` (confirmed
   by filesystem search). Not caught by `scripts/docs/relative_link_fixer.py --check` (0 findings
   repo-wide) because these are plain code-span text, not Markdown hyperlinks — the automated
   link checker only resolves `[text](path)` syntax. Fixed all 4 occurrences.

**Audited, no issues found:**

- `docs/api/agent-subcommands.md` — `agent action implement`, `agent action review`,
  `agent tasks mark-status`, `agent tasks move-task` (the four commands this mission's own
  agents invoke every WP cycle) verified byte-for-byte against live `--help` output. Zero
  discrepancies.
- `docs/api/cli-commands.md` — `mission create`, `implement`, `plan`, `tasks`, `specify`
  (arguments/description), `review` (description) sections verified against live `--help`
  beyond the two fixes above. No further discrepancies.
- `docs/api/supported-agents.md` / `docs/api/supported-harnesses.md` — agent/harness counts (16
  active surfaces: 12 slash-command/prompt-file + 4 command-skill-only; 17 total including
  deprecated Roo Cline) verified against the canonical `AGENT_DIRS` list in
  `src/specify_cli/agent_utils/directories.py` (Roo correctly removed with a `# ".roo" removed —
  Roo Code shut down on 2026-05-15 (C-007)` comment). Both pages already correctly document Roo
  as deprecated. Note: the root `/CLAUDE.md` (out of `owned_files`, not touched) still lists Roo
  Cline as a 13th active slash-command agent and says "19 agents total, 13 slash-command" — that
  file is stale relative to the canonical source, but it is out of this WP's scope to fix.
- `docs/api/environment-variables.md` — `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` already
  correctly documented as "**Inert** — `--feature` alias removed; no warnings emitted", matching
  the migrations fix below (cross-checked for consistency, not independently wrong).
- `docs/api/configuration.md`, `event-envelope.md`, `file-structure.md`, `init-lifecycle.md`,
  `upgrade-lifecycle.md`, `retrospective-schema.md`, `orchestrator-api.md`, `profile-invocation.md`,
  `terminology.md`, `agent-plan-artifacts.md`, `bulk-edit-gate.md`, `finalize-tasks-internals.md` —
  spot-checked for stale `--feature` references (none found beyond correctly-framed historical/
  removed-flag mentions) and cross-referenced paths; no confirmed inaccuracies found.
- Repo-wide `python3 -m scripts.docs.relative_link_fixer --check` → 0 dead bare-relative body
  links, before and after this WP's edits.
- `PYTHONPATH=src python3 -m scripts.docs.check_cli_reference_freshness --reference
  docs/api/cli-commands.md --agent-reference docs/api/agent-subcommands.md` → reports "clean"
  both before and after this WP's fixes (the tool has blind spots for flag-level diffing that
  don't catch findings #1/#2 above — this WP's fixes were verified independently against live
  `--help` and source, not solely via this tool).
- `docs/api/slash-commands.md` omits 3 non-canonical-sequence slash commands (`tasks-outline`,
  `tasks-packages`, `tasks-finalize` — auxiliary manual-invoke commands with
  `in_action_sequence: false` in their `step.yaml`, distinct from the canonical one-shot
  `/spec-kitty.tasks`). This page is explicitly framed as a "quick reference," not a claimed-
  exhaustive one (unlike `charter-commands.md` above), so this is **not** treated as a confirmed
  inaccuracy — recorded as a minor recommendation below instead.

## T029 — `docs/adr/`, `docs/migrations/`, `docs/operations/` audit

**Fixed (confirmed inaccuracies):**

6. **`docs/adr/3.x/README.md` — 29 of 83 ADR files (~35%) were missing their index-table row**,
   meaning those ADRs were unlinked from the era's own navigable index (a metadata/index error,
   not a content rewrite). Detected via a filesystem-vs-table diff, then confirmed with the
   project's own canonical tool: `python3 -m scripts.docs.freshen_adr_inventory --all --check`
   reported `missing_rows=29`. Fixed by running the same tool in write mode
   (`python3 -m scripts.docs.freshen_adr_inventory --all`), which is exactly the maintenance step
   `docs/adr/3.x/README.md` itself instructs authors to run after adding an ADR — this is the
   canonical, idempotent, zero-authorial-judgment remedy (per this repo's "use canonical sources,
   never improvise" doctrine), not a hand-authored rewrite. Verified the tool's inventory-
   regeneration side effect (`docs/development/3-2-page-inventory.yaml`, outside `owned_files`)
   was a no-op both before (`inventory_stale=False` in `--check` output) and after
   (`git diff --stat` shows only `docs/adr/3.x/README.md` changed, 29 insertions, 0 deletions).
7. **`docs/migrations/feature-flag-deprecation.md` — described `--feature` as still working**
   (hidden alias, deprecation warning, no conflict) on 8 top-level commands (`implement`, `merge`,
   `next`, `research`, `context`, `accept`, `lifecycle`, `mission-type`), pending a future
   removal "gated by #1059" with "no calendar date." Live-tested all 8: `spec-kitty implement
   --feature x`, `next --feature x`, `merge --feature x`, `research --feature x`,
   `context --feature x`, `accept --feature x`, `mission-type --feature x` all reject with
   "No such option: --feature" (exit 2). Cross-checked against `CHANGELOG.md` line ~902 (version
   `3.2.3`, 2026-06-29): "**Removed**: Hidden `--feature` alias hard-removed from 8 user-facing
   CLI commands ... (#1060)" — the exact same 8 commands. Full removal shipped 3 patch versions
   before the current 3.2.6, but the migration doc (`updated: 2026-06-15`) was never refreshed
   after. Rewrote the Status/Why-This-Change/What-Changed/Behavioral-Changes/
   Suppressing-the-Warning/Removal-Criteria sections to reflect the now-complete removal, while
   preserving the historical migration narrative, script, and references intact. This is the
   largest single fix in this WP by line count, but it corrects one cohesive, verifiably false
   premise (partial vs. full removal) repeated across several sections of the same page — not a
   style rewrite.

**Audited, no issues found:**

- `docs/migrations/mission-type-flag-deprecation.md` — spot-verified live:
  `spec-kitty charter interview --mission documentation --defaults` emitted exactly the
  deprecation warning text and doc-path reference (`docs/migrations/mission-type-flag-
  deprecation.md`) the page describes, confirming `--mission` is still a genuinely live hidden
  alias on `charter interview` (unlike the fully-removed `--feature`). Accurate as written.
- `docs/migrations/index.md` and the remaining 12 `docs/migrations/*.md` files not otherwise
  listed — spot-checked titles, `updated` dates, and referenced commands/paths (a repo-wide
  dead-code-span-path scan restricted to `owned_files`; see method note below). No further stale
  references found.
- `docs/operations/identity-boundary-ci-gate.md`, `docs/operations/ssh-deploy-keys.md`,
  `docs/operations/logged-out-teamspace.md` — spot-checked referenced commands
  (`spec-kitty auth login`, `spec-kitty sync doctor`, `spec-kitty sync routes`, etc.) against
  live `--help`; all exist and match.
- `docs/adr/1.x/README.md` and `docs/adr/2.x/README.md` have **no index table at all** (0 of 12
  and 0 of 37 ADRs listed). Investigated whether this is a defect: `freshen_adr_inventory.py`'s
  own `detect_missing_adrs()` explicitly and intentionally skips eras without a table — code
  comment: "legacy eras without a table (e.g. 1.x/2.x) are intentionally skipped rather than
  back-filled with a table they never carried." Confirmed **by design**, not a bug. Left
  untouched; recorded as a nav-placement observation, not a fix, below.
- ADR **bodies** — per this WP's explicit scope boundary (ADR bodies are immutable historical
  snapshots; only genuine non-historical factual errors are in scope, and none were found), zero
  ADR body content was rewritten. A dead-code-span-path scan (method: regex-scan every backtick-
  quoted `` `docs/**.md` `` reference in `owned_files` and check it resolves on disk) found 8 ADR
  bodies referencing now-nonexistent pre-restructure paths (e.g. `docs/explanation/...`,
  `docs/migration/...` singular, `docs/how-to/...` — `2026-06-11-1-op-as-first-class-execution-
  artifact.md`, `2026-05-18-1-monorepo-charter-scope.md`, `2026-05-16-1-doctrine-layer-merge-
  semantics.md`, `2026-04-25-1-shared-package-boundary.md`, `2026-04-20-1-mutation-testing-as-
  local-only-quality-gate.md`, `1.x/2026-01-25-8-cli-first-command-interface.md`,
  `2.x/2026-01-27-11-dual-repository-pattern.md`, `2.x/2026-03-25-1-glossary-type-ownership.md`).
  These are point-in-time historical decision records citing "current" paths as of their writing
  — exactly the kind of drift ADR immutability is meant to preserve, not "fix." Left untouched
  per the WP's own Risks & Mitigations guidance and this project's `test_docs_adr_exemption_is_
  narrow` precedent.

**Fixed (confirmed inaccuracy, filed under Operations rather than a duplicate heading):**

8. **`docs/operations/index.md` — `docs/operations/recovery-index.md` (and transitively
   `docs/operations/logged-out-teamspace.md`, only linked from `recovery-index.md`) were
   orphaned.** Root `docs/toc.yml` links only to `operations/index.md` (verified: `grep
   operations docs/toc.yml` → 1 hit), and `operations/index.md`'s own "## Pages" section and
   `related:` frontmatter listed only `ssh-deploy-keys.md` and `identity-boundary-ci-gate.md` —
   omitting 2 of the 4 actual files in the directory. This violates spec.md's own Success
   Criterion #3 ("Zero pages are reachable only by direct URL"). Fixed by adding a "Recovery
   guides" entry to `operations/index.md`'s "## Pages" list and `related:` frontmatter. This is a
   content edit to a page within `owned_files` (`docs/operations/**`), not an edit to the root
   `docs/toc.yml` (which remains untouched, per this WP's explicit constraint).

## T030 — `docs/archive/` nav-placement audit

**Audited, no issues found; placement confirmed reasonable.**

- Reachability: `docs/archive/` is nested under a "Historical Archive" group inside "Project
  Updates" within the end-user zone of the already-implemented (by WP02) `docs/toc.yml`
  (verified: `grep -B3 -A6 archive docs/toc.yml` shows `Historical Archive > {Archive Overview,
  Archive (2.x), Archive (1.x)}`, all with valid `href`s). Not orphaned.
- Placement sensibility: WP02's own prior notes in this file (see "WP02 — T006 design rationale"
  above) already explicitly considered and justified this placement ("low-traffic reference
  material; WP02's guidance explicitly allows either zone or standalone — grouped here rather
  than left as a 7th top-level slot"). No new evidence surfaced during this audit that would
  override that judgment call, so no override is recommended.
- Link integrity (accuracy-adjacent, not content-accuracy per T030's actual mandate): all
  `docs/archive/**` links into `docs/guides/*` (getting-started.md, run-external-
  orchestrator.md, build-custom-orchestrator.md, setup-governance.md, manage-agents.md,
  manage-glossary.md) verified to still exist — none of these were among WP01's 13 relocated
  `docs/guides/` → `docs/development/` files, so no archive links were broken by that move.

## T031 — Fixes applied (summary)

All 8 confirmed inaccuracies above (5 in `docs/api/`, 2 in `docs/migrations/`/`docs/adr/`, 1 in
`docs/operations/`) were corrected with minimal, targeted edits. No section was wholesale
rewritten; the largest single-file diff (`docs/migrations/feature-flag-deprecation.md`) corrects
one cohesive false premise repeated across several of that page's existing sections, not a
narrative rewrite. Zero ADR body content was altered. Verification after all fixes:
- `PYTHONPATH=src python3 -m pytest tests/architectural/test_no_legacy_terminology.py -q` → 3
  passed.
- `python3 -m scripts.docs.relative_link_fixer --check` → 0 dead bare-relative body links.
- `PYTHONPATH=src python3 -m scripts.docs.check_docs_freshness --link-check spot` → exit=0,
  0 errors, 3 pre-existing unrelated WARNING-level unreachable example URLs (localhost,
  `receiver.example`, a specific `.fly.dev` host used as a documentation example) in
  `docs/api/cli-commands.md`, not introduced by this WP.

## T032 — Nav-placement recommendations (recorded only, not applied to `docs/toc.yml`)

These are findings for WP02 or a future pass to consider — none were applied directly, per this
WP's explicit constraint that `docs/toc.yml` is WP02's exclusive surface:

1. **`docs/api/toc.yml`** (a child TOC *within* this WP's own `owned_files`, distinct from the
   root `docs/toc.yml`) has no entry for `docs/api/terminology.md`, even though it's linked from
   `docs/api/index.md`'s body text. Not fully orphaned (reachable in 2 clicks via `index.md`), but
   inconsistent with all 16 other API pages, each of which has both a body link and a sidebar
   `toc.yml` entry. Left unedited out of caution (treating "any `toc.yml`" as off-limits for
   direct WP07 edits, not just the root file, given the WP's stated highest-scope-creep-risk
   status) — recommend a future pass add the missing entry.
2. **`docs/api/README.md` and `docs/api/index.md` are two overlapping overview pages for the same
   directory** (`README.md` dated `2026-06-09`, `index.md` dated `2026-06-27`; `README.md`'s
   "Contents" list is missing several newer pages, e.g. `charter-commands.md`). Likely a leftover
   from a prior docs restructure. Recommend a future consolidation pass decide which is canonical
   and retire or merge the other — out of this WP's minimal-fix mandate.
3. **`docs/adr/1.x/README.md` and `docs/adr/2.x/README.md` have no index tables**, so 49 of 132
   total ADR files (12 + 37) are reachable only by directory browsing, not through a curated,
   date-ordered table (unlike `3.x/README.md`, now complete per fix #6 above). Confirmed
   intentional-by-design in the tooling (see T029 above), so this is a design-decision
   recommendation, not a bug report: a future pass could decide to backfill index tables for
   these two legacy eras, or explicitly document why they're intentionally table-less.
4. **`docs/api/slash-commands.md`** does not list `tasks-outline`, `tasks-packages`, or
   `tasks-finalize` (see T028 above) — not a confirmed inaccuracy since the page never claims
   exhaustiveness, but a future pass could add a short "Advanced: manual task-package authoring"
   note pointing to these three auxiliary commands for discoverability.

---

# WP10 — Terminology Sweep & Closing Report

This mission's final work package (T040–T044) ran the mission-wide terminology/glossary checks
(FR-014, Success Criterion 7), verified NFR-005's Divio frontmatter coverage, and filed the C-003
follow-up issue. Full closing record, including the pages moved/created/removed count, final nav
entry counts, terminology-check results (74 in-scope casing violations fixed across 21 files, 200
pre-existing/out-of-scope ones left untouched), NFR-005 fixes (16 `docs/guides/` pages given
Divio `type:` frontmatter), and both follow-up GitHub issue URLs:
[`docs/development/terminology-sweep-report.md`](../../docs/development/terminology-sweep-report.md).
