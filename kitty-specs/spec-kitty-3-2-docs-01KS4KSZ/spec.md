# Feature Specification: Spec Kitty 3.2 Documentation Refresh

**Mission ID:** `01KS4KSZ67PMNRJ057BGT0Z8AW`
**Mission Slug:** `spec-kitty-3-2-docs-01KS4KSZ`
**Mission Type:** software-dev
**Branch Contract:** current=`main`, planning_base=`main`, merge_target=`main` (`branch_matches_target: true`)
**Created:** 2026-05-21
**Status:** Draft — planning only per `start-here.md`

---

## Purpose

**TLDR:** Make Spec Kitty 3.x/3.2 docs the complete current source of truth, archive 1.x/2.x, rebuild the CLI reference from the live command tree, and cover every supported AI harness end-to-end.

**Context:** End users install Spec Kitty into real projects and operate it through AI harnesses such as Claude Code, Codex, OpenCode, Cursor, Gemini, and Pi TUI. Today the public docs mix 1.x, 2.x, 3.1, and 3.2 material, the CLI reference lags the live Typer tree (only 113 of 192 visible paths are covered per `cli-audit-3-2.md`), and there is no consistent install/upgrade/uninstall guidance across pip, pipx, and uv on macOS, Linux, and Windows. This mission produces a Divio-structured 3.2 documentation set, a methodology decision and reference plan for the CLI surface, harness research with explicit support classification, and version-leakage validation so that adopters and existing users land on accurate, version-correct guidance for the upcoming 3.2 releases.

---

## User Scenarios & Testing

### Primary Actors

1. **New adopter** — discovers Spec Kitty 3.2, installs it on their workstation, initializes their first project inside an AI harness, and runs their first mission.
2. **Existing 2.x/3.1 user** — already runs Spec Kitty; needs to upgrade to 3.2, understand what changed, and migrate any 1.x/2.x-shaped state.
3. **Multi-harness operator** — drives Spec Kitty across two or more harnesses (e.g., Claude Code at desk, Codex in CI, Cursor when pairing) and needs consistent slash-command and skill behaviour.
4. **CLI consumer / integrator** — calls `spec-kitty` directly from scripts, CI, or external orchestrators and must rely on accurate CLI reference and option documentation.
5. **Docs reviewer / release engineer** — verifies before a 3.2 release that no archival content leaks into current navigation and that every visible command is documented.

### Primary Scenario (Happy Path)

> A new adopter on macOS hears about Spec Kitty 3.2, opens
> `https://docs.spec-kitty.ai`, lands on a clearly labeled **3.2 (current)**
> entry page, follows the install how-to using `uv tool install
> spec-kitty-cli`, runs `spec-kitty init` in a real repo from inside Claude
> Code, and finishes their first mission by following the **first 3.2
> mission using `spec-kitty next`** tutorial. They never encounter a 1.x
> or 2.x example that contradicts what they just installed.

### Acceptance Scenarios

1. **Version separation at the entry page.** Loading the docs site, the user immediately sees a 3.2 (current) landing experience; 1.x and 2.x material is either hidden from current navigation or visibly framed as archive/migration content with a banner.
2. **CLI reference parity.** Every visible command path emitted by the live Typer app (192 paths per `cli-audit-3-2.md`) is either present in the reference or explicitly classified as deprecated, internal, hidden, or compatibility-only with rationale.
3. **CLI help truthfulness.** Where live help text disagrees with code behaviour or with tests, the inaccuracy is recorded in `docs/development/3-2-cli-reference-audit-meta-issues.md` rather than silently fixed in docs.
4. **Divio coverage for the end-user journey.** A reader can find a tutorial, a how-to, a reference, and an explanation for each of: first install, first mission, charter-governed workflow, multi-harness operation, mission recovery.
5. **Per-harness reachability.** For each first-class harness, there is a setup+usage page that maps the harness's canonical mechanism (slash command, prompt, workflow, skill, command file) to Spec Kitty's installed surface and cites the harness's own current docs.
6. **Cross-platform install lifecycle.** A user can locate authoritative install, upgrade, and uninstall instructions for pip, pipx, and uv on macOS, Linux, and Windows, including PATH and PowerShell concerns.
7. **No mixed-version leakage in current pages.** Pages tagged `current` (3.2) do not link to archival 1.x/2.x examples without a migration banner; navigation under "3.2 current" never contains an archival page.
8. **Plan-only gate respected.** During the specify/plan/tasks phases of this mission no live docs page outside `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/` is edited, no Typer code is changed, no docs nav is reflowed, and no site is published.
9. **Workspace operating-rule compliance.** No SaaS DB / tracker / hosted-auth / sync execution occurs during planning; if such flows are later exercised, they run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

### Edge Cases

- A visible command path exists in the live Typer tree but is intentionally hidden from public docs (e.g., `agent decision widen`, `merge-driver-event-log`). The reference must classify it, not silently omit it.
- A live command renders help with exit 0 but the command itself is deprecated/removed in behaviour (e.g., `mission switch`, `mission-type switch`, `validate-tasks`, `agent status migrate`). These must be classified as deprecated/legacy and never appear in active-workflow guidance.
- A command's tree only materializes when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (e.g., `tracker`, `issue-search`). The CLI reference generation method must capture the SaaS-flagged surface and must not silently drop it.
- The repo currently exposes `agent profile` as hidden while `agent profile list` shows as visible. The audit and reference must take an explicit position on this asymmetry.
- A harness directory exists in the repo (e.g., `.qwen`, `.kiro`, `.kilocode`, `.roo`, `.windsurf`, `.augment`, `.amazonq`, `.agent`) but the harness's external usage docs may have changed; the harness page must cite current external docs and reflect what Spec Kitty actually generates.
- A previously documented command was renamed in code (e.g., `agent workflow implement` → `agent action implement`; `agent context update-context` → `agent context resolve`). Stale references in tutorials and how-tos must be updated or moved to archive.
- The public site may host 3.1 docs that are still partially valid. The mission must decide whether to expose 3.1 as a supported version with its own nav group or fold it into 3.2 as migration notes (see deferred decision `01KS4KTGTN4DBE60JFWKEA2FJB`).

---

## Domain Language

Canonical terms for this mission (avoid synonyms in spec, plan, tasks, and docs unless quoting archival material):

| Canonical term | Definition | Avoid |
|----------------|------------|-------|
| **current** | Version-relevance tag for pages that describe 3.2 behaviour. | "latest", "the new docs" |
| **supported** | Version-relevance tag for 3.1-relevant pages still useful but not 3.2-complete. | "old current", "previous-but-ok" |
| **archival** | Version-relevance tag for 1.x or 2.x material kept for historical record. | "deprecated docs", "legacy" (without qualification) |
| **migration** | Version-relevance tag for pages explaining how to move from an earlier version to 3.2. | "transition guide" (without tag) |
| **internal** | Version-relevance tag for development-only or non-public material. | "dev notes", "private" |
| **harness** | The AI tool that hosts Spec Kitty (Claude Code, Codex, OpenCode, Cursor, Gemini, Pi TUI, Qwen, Amazon Q, Copilot, Augment, Roo, Kilo Code, Kiro, Windsurf, Vibe, Letta Code). | "agent" (overloaded), "IDE" (too narrow) |
| **slash command** | Host-surface mechanism that maps `/spec-kitty.<action>` to a command template. | "prompt" (host-specific synonym) |
| **command template** | Source markdown in `src/specify_cli/missions/*/command-templates/`. | "agent doc", "skill md" |
| **Divio type** | One of {tutorial, how-to, reference, explanation}. | "doc kind" |
| **meta issue** | Entry in `docs/development/3-2-cli-reference-audit-meta-issues.md` recording CLI/help/code/test mismatch surfaced during the audit. | "ticket", "bug" (without record) |
| **visible command path** | A non-hidden Typer command/group leaf reachable from `spec-kitty --help` (with SaaS sync enabled where applicable). | "command", "subcommand" (without scope) |

---

## Functional Requirements

> Status legend: **Planned** = required for mission acceptance. **Optional** = include if scope permits.

| ID | Description | Acceptance | Status |
|----|-------------|------------|--------|
| **FR-001** | Define a version-relevance taxonomy with exactly the five tags (`current`, `supported`, `archival`, `migration`, `internal`) used as the single classification axis across every docs page. | Taxonomy document exists in `kitty-specs/<mission>/` artifacts and is referenced by every workstream deliverable. | Planned |
| **FR-002** | Produce a complete page inventory of `docs/`, `architecture/`, `README.md`, and site navigation files (`docs/toc.yml`, `docs/*/toc.yml`, `docs/docfx.json`) with each page assigned exactly one version-relevance tag. | Inventory table covers 100% of discoverable docs pages; tag distribution by version is reported. | Planned |
| **FR-003** | Decide and document how version filtering is represented in the site generator: frontmatter, generated indexes, or explicit nav groups for 1.x archive, 2.x archive, 3.1, and 3.2-current. | Decision recorded with rationale; planning artifact specifies the implementation mechanism the plan phase will adopt. | Planned |
| **FR-004** | Produce a navigation update plan for `docs/toc.yml` and child TOCs that separates 1.x archive, 2.x archive, 3.1 supported, 3.2 current, and migration content. | Navigation plan covers every TOC file and identifies removals, adds, and moves; no nav edits land during planning. | Planned |
| **FR-005** | Specify a validation mechanism that prevents archival pages from appearing in 3.2-current navigation without an explicit archive or migration banner. | Validation rule documented with a test or check proposal; ties to FR-002 inventory. | Planned |
| **FR-006** | Reconstruct the prior CLI reference methodology from git commits `a14769e7a`, `81b3d6c3e`, `514106af2`, `deee8d7f3` and record whether it was hand-authored, generated, semi-generated, or test-validated. | Methodology note exists with commit-by-commit evidence and identifies any extant freshness check. | Planned |
| **FR-007** | Define a repeatable 3.2 CLI reference build process that captures root help, recursively discovers subcommands, captures each `--help`, normalizes for docs, compares with Typer registration and command tests, and writes source-evidence links. | Process documented; works against `SPEC_KITTY_ENABLE_SAAS_SYNC=1` so SaaS-gated commands (`tracker`, `issue-search`) are included. | Planned |
| **FR-008** | Decide hand-maintained vs generator-backed vs hybrid CLI reference for 3.2 and record a freshness-validation proposal (test, CI gate, or doc-check). | Decision tied to deferred `[NEEDS CLARIFICATION]` resolution and to FR-006 evidence. | Planned |
| **FR-009** | Plan the audit of every visible Typer command path (192 per `cli-audit-3-2.md`) against Typer registration, help text, defaults, examples, deprecations, and tests under `tests/cli`, `tests/agent`, `tests/init`, `tests/upgrade`, `tests/sync`, and contract tests. | Audit plan specifies the matrix columns, evidence sources, and execution gating; no audit execution occurs during planning beyond what `cli-audit-3-2.md` already captures. | Planned |
| **FR-010** | Specify the structure of `docs/development/3-2-cli-reference-audit-meta-issues.md` (fields: command path, source file/function, observed help, observed behaviour or test evidence, problem type, recommended fix, owner area, blocking status). | Meta-issue schema documented in the plan artifact; will be the only place CLI/help mismatches are recorded during execution. | Planned |
| **FR-011** | Plan a 3.2 Divio information architecture covering tutorials, how-to, reference, and explanation, mapped to the end-user journey across supported harnesses. | IA document lists every planned page, its Divio type, its target audience, and its place in navigation. | Planned |
| **FR-012** | Produce a gap list comparing the IA against current `docs/tutorials`, `docs/how-to`, `docs/reference`, and `docs/explanation` so every needed page is either reused, rewritten, or new. | Gap list table covers all four directories with disposition per page. | Planned |
| **FR-013** | Plan a migration/archive plan for pages that are no longer current, including which 1.x/2.x pages move to archive folders and which 3.1 pages convert to migration notes. | Archive/migration plan covers every page tagged `archival` or `migration` from FR-002 inventory. | Planned |
| **FR-014** | Plan harness research for every supported harness (Claude Code, Codex, OpenCode, Cursor, Gemini, Pi TUI, Qwen, Amazon Q, GitHub Copilot, Augment/Auggie, Roo, Kilo Code, Kiro, Windsurf; plus Vibe and Letta Code if still supported) including external-doc citation requirements and inventory of Spec Kitty's generated files for each. | Research method document lists subjects, evidence sources, and per-harness deliverables. | Planned |
| **FR-015** | Plan a harness support matrix with explicit classification (first-class, supported, partial, experimental, archived/removed) and the criteria each level requires. | Matrix design and classification criteria documented; ties to deferred `[NEEDS CLARIFICATION]` resolution for which harnesses ship in each tier. | Planned |
| **FR-016** | Plan one user-facing setup-and-usage page per major harness family that maps the harness's canonical mechanism to Spec Kitty's installed surface. | Per-harness page outline exists for every harness classified at `partial` or higher. | Planned |
| **FR-017** | Plan install/upgrade/uninstall documentation for pip, pipx, and uv across macOS, Linux, and Windows, including PATH/PowerShell/py-launcher considerations. | OS × tool command matrix is drafted and includes verification commands. | Planned |
| **FR-018** | Plan project-lifecycle documentation for `spec-kitty init` and `spec-kitty upgrade`, including idempotent init, non-interactive init, supported host selection, and reviewing generated file changes. | Lifecycle outline exists with required topics enumerated. | Planned |
| **FR-019** | Plan uninstall and rollback documentation, including CLI uninstall, generated-file removal, mission-history archival, and rollback from a failed upgrade. | Uninstall outline exists with explicit rollback flow. | Planned |
| **FR-020** | Plan a documentation freshness check that validates docs against the live Typer tree with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and reports any reference entry missing from the live tree or any visible path missing from the reference. | Freshness-check design exists; identifies whether it runs as test, CI step, or pre-publish script. | Planned |
| **FR-021** | Plan a final publication checklist covering site build, navigation review, link-check, version-leakage scan, and the meta-issue dispatch path. | Publication checklist drafted; aligns with acceptance criteria from `start-here.md`. | Planned |

---

## Non-Functional Requirements

| ID | Description | Measurable Threshold | Status |
|----|-------------|----------------------|--------|
| **NFR-001** | The CLI reference must match the live command tree at the moment of publication. | Zero unclassified visible command paths (currently 79 of 192 unclassified per `cli-audit-3-2.md`); zero reference entries for paths absent from the live tree; freshness check passes in CI. | Planned |
| **NFR-002** | Version leakage in current pages must be zero at publication. | Pages tagged `current` link to `archival` content only when an explicit archive/migration banner is present; automated check or review gate enforces this. | Planned |
| **NFR-003** | Cross-platform install instructions must be exercisable. | For each (tool × OS) cell (pip/pipx/uv × macOS/Linux/Windows), the docs include a verifiable install command and a `spec-kitty --version` verification step. | Planned |
| **NFR-004** | Harness pages must cite current external host docs. | For each harness page, at least one citation to that harness's current public documentation; broken citations block publication. | Planned |
| **NFR-005** | Meta-issue capture must precede docs publication. | Every CLI/help mismatch surfaced during audit lands as a row in `docs/development/3-2-cli-reference-audit-meta-issues.md` with the required fields before the reference page is republished. | Planned |
| **NFR-006** | Planning-phase artifacts must not modify live docs. | Diff of any non-`kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/**` path during specify/plan/tasks is empty. | Planned |
| **NFR-007** | Operator readability of the support matrix. | Support matrix renders in a single page, displays the 5 classification tiers, and lists every harness in scope from FR-014. | Planned |
| **NFR-008** | Reference pages must be discoverable from the public URL. | `docs/reference/cli-commands.md` is reachable from the site nav at `https://docs.spec-kitty.ai/reference/cli-commands.html` after the docs build runs. | Planned |
| **NFR-009** | Plan artifacts honour charter policy. | Plan, tasks, and contracts comply with the active charter policy summary loaded via `spec-kitty charter context --action plan --json`, including typer/rich/ruamel.yaml/pytest/mypy constraints for any tooling proposed by the plan. | Planned |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| **C-001** | Planning only until plan is approved (per `start-here.md`). No live doc edits, no CLI changes, no site publishes, no generated-doc regeneration during specify/plan/tasks. | Active |
| **C-002** | Do not change Typer command code, generated command files, or `docs/toc.yml`/child TOCs during planning. | Active |
| **C-003** | Do not run SaaS, tracker, hosted-auth, or sync flows unless execution is explicitly approved. Any future execution on this host uses `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Active |
| **C-004** | Treat `docs/1x` and `docs/2x` as archival; 3.x/3.2 is current. Archival content moves only when the archive plan (FR-013) is approved. | Active |
| **C-005** | Live CLI tree (visible command paths discovered with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`) is the source of truth for the reference, not historical commits. Prior commits inform methodology only (FR-006). | Active |
| **C-006** | CLI help-text inaccuracies are captured in `docs/development/3-2-cli-reference-audit-meta-issues.md`, never silently fixed during the docs rewrite. | Active |
| **C-007** | Limit `[NEEDS CLARIFICATION]` markers to ≤ 3. Three open questions are deferred via decision IDs `01KS4KTGTN4DBE60JFWKEA2FJB`, `01KS4KTM69EG2KVX5MQ54FQ939`, `01KS4KTS4V300M9MMTS1AJEGXY`; the remaining two open questions are resolved in Assumptions with documented defaults. | Active |
| **C-008** | Bulk-edit workstreams (version frontmatter rollout, archive moves, navigation reflow) are flagged in risks. The plan phase decides per-workstream whether `change_mode: bulk_edit` plus `occurrence_map.yaml` are required under the `spec-kitty-bulk-edit-classification` skill. | Active |
| **C-009** | Charter policy summary applies: typer / rich / ruamel.yaml / pytest / mypy --strict / pytest 90%+ coverage / integration tests for CLI commands. Any tooling proposed by the plan (e.g., a CLI reference generator, a freshness check) honours this stack. | Active |

---

## Open Questions (deferred via Decision Moments)

[NEEDS CLARIFICATION: Whether the public 3.x docs expose 3.1 as a separately navigable supported version, or fold 3.1 pages into 3.2 as migration notes only.] <!-- decision_id: 01KS4KTGTN4DBE60JFWKEA2FJB -->

[NEEDS CLARIFICATION: Whether the CLI reference is hand-maintained markdown, fully generator-backed with a committed script and freshness test, or hybrid (generated body with hand-authored prose).] <!-- decision_id: 01KS4KTM69EG2KVX5MQ54FQ939 -->

[NEEDS CLARIFICATION: Which AI harnesses ship as first-class vs supported vs opportunistic for 3.2, and whether the per-harness page set is canonical or only the support matrix is.] <!-- decision_id: 01KS4KTS4V300M9MMTS1AJEGXY -->

---

## Assumptions

> Defaults captured here for the two open questions not deferred as `[NEEDS CLARIFICATION]`; revise during plan if the user overrides.

1. **SaaS doc scope (open question from `start-here.md`).** Docs for SaaS-backed tracker/sync behaviour live in this repo and cross-link to `spec-kitty-saas` / `spec-kitty-tracker` only when an external concept is referenced. Rationale: keep the canonical UX docs adjacent to the CLI that exposes the surface; cross-link rather than copy.
2. **Release-label notation (open question from `start-here.md`).** Public docs use `3.2` as the umbrella label and reference specific tags only when behaviour differs (e.g., `3.2.0rc21+` for a feature gated by an RC); `pyproject.toml` currently reports `3.2.0rc21` and the live CLI reports `3.2.0rc22`.
3. **Mission scope is documentation planning, not docs publishing.** This mission produces planning artifacts (taxonomy, page inventory, IA, harness research method, install/upgrade/uninstall outline, meta-issue schema, freshness-check design, publication checklist) that the plan/tasks phases will turn into per-WP execution work.
4. **Live CLI evidence already captured.** The audit results in `cli-audit-3-2.md` (192 visible / 5 hidden / 2 deprecated / 113 covered) are the canonical starting evidence for FR-009 and FR-010; further live audit execution waits for plan approval.
5. **Charter context is already in scope.** `spec-kitty charter context --action specify --json` returned bootstrap context with charter at `.kittify/charter/charter.md` and the policy summary above; subsequent flows (`plan`, `tasks`) will refresh context with `--action <flow>`.
6. **Glossary discipline.** Project authority paths include `glossary/contexts/` (canonical terminology). The Domain Language table above is the working glossary for this mission; conflicts with `glossary/contexts/` get resolved via the `spec-kitty-glossary-context` skill during the plan phase.

---

## Success Criteria (user-facing, measurable, technology-agnostic)

1. A reader installing Spec Kitty 3.2 cold can run their first mission inside their chosen harness in under 30 minutes following only the new tutorials and how-tos.
2. A user upgrading from 3.1 or 2.x reaches a green `spec-kitty verify-setup` (or its current-3.2 equivalent) without consulting code or external chat.
3. A CLI consumer can find an accurate reference entry for every command they invoke; missing reference entries during the publication gate count as zero in the freshness check.
4. A docs reviewer can confirm version-leakage compliance in under 10 minutes using the validation mechanism from FR-005 and the publication checklist from FR-021.
5. A harness user finds documentation for their host that cites the host's own current docs and matches the files Spec Kitty installs into that host's directory.
6. After publication, the only place CLI/help mismatches live is `docs/development/3-2-cli-reference-audit-meta-issues.md`; no silent doc-side fixes exist.
7. Install, upgrade, and uninstall coverage is complete: at least one verified command path exists for every (pip / pipx / uv) × (macOS / Linux / Windows) cell.

---

## Key Entities

- **DocsPage** — a markdown file under `docs/`, `architecture/`, or root (e.g., `README.md`). Attributes: path, version-relevance tag (FR-001), Divio type (when applicable), target audience, owning workstream.
- **VersionTag** — one of {`current`, `supported`, `archival`, `migration`, `internal`} (FR-001).
- **CommandPath** — a Typer command/group leaf reachable from `spec-kitty --help`. Attributes: path string, visibility (visible/hidden), classification (active/deprecated/internal/compatibility), source file, source function, owning surface (e.g., `agent`, `tracker`, `doctor`).
- **CommandTreeSnapshot** — the result of capturing the live tree with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Attributes: timestamp, CLI version, count of visible/hidden/deprecated paths.
- **MetaIssue** — a row in `docs/development/3-2-cli-reference-audit-meta-issues.md` (FR-010). Attributes: command path, source file/function, observed help, observed behaviour/test evidence, problem type (inaccurate/incomplete/stale/missing/confusing/version-leakage), recommended fix, owner area, blocking status.
- **Harness** — an AI host that runs Spec Kitty (per the `harness` glossary entry). Attributes: name, canonical mechanism (slash/prompt/workflow/skill/command-file/config), installed surface directory, support tier (first-class/supported/partial/experimental/archived), external doc citation.
- **HarnessSupportMatrix** — the FR-015 matrix mapping every Harness to a tier with classification criteria.
- **InstallTarget** — the cross product of tool (`pip`, `pipx`, `uv`) × OS (`macOS`, `Linux`, `Windows`). Attributes: install command, upgrade command, uninstall command, verification command, platform notes (PATH, PowerShell, py-launcher).
- **DivioPage** — a planned 3.2 docs page belonging to one of {tutorial, how-to, reference, explanation}. Attributes: target audience, prerequisites, success criterion.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Version-frontmatter rollout becomes an implicit bulk edit across hundreds of files without occurrence-map control. | Medium | High (cross-file breakage, silent leakage). | C-008 flags this; plan phase invokes `spec-kitty-bulk-edit-classification` skill for the version-tag workstream. |
| CLI generator scope creeps into modifying Typer code (renaming hidden commands, fixing help strings) during docs work. | Medium | High (mission-review failure on operating-rule compliance). | C-002 plus FR-010 force CLI/help findings into the meta-issue file, not silent edits. |
| Harness research blocks on flaky external sources or paywalled docs. | Low | Medium (delayed harness pages). | FR-014 requires explicit citation; missing-citation harnesses get classified `partial` or lower until evidence lands. |
| 3.1 ambiguity (deferred decision) blocks navigation design and migration plan from converging. | Medium | Medium (re-work in plan/tasks). | Decision `01KS4KTGTN4DBE60JFWKEA2FJB` is the gating clarification; plan phase resolves it before navigation work begins. |
| SaaS-gated commands (`tracker`, `issue-search`) get dropped from the reference because some envs run without `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Medium | High (incomplete reference). | FR-007 mandates the flag during capture; freshness check (FR-020) verifies SaaS-gated paths are present. |
| Live CLI gains/loses commands between planning and publication (`3.2.0rc21` → `3.2.0rcN`). | Medium | Medium (stale audit baseline). | NFR-001 freshness check runs at publication; mission-review gates compare against the live tree at that time, not at planning time. |

---

## Out of Scope (explicit)

- Editing live docs content during planning.
- Running the full CLI help audit beyond what is already captured in `cli-audit-3-2.md`.
- Changing CLI help text, Typer command code, or docs navigation.
- Publishing, deploying, or regenerating the public site.
- Running SaaS / tracker / hosted-auth / sync flows unless explicitly approved.
- Picking the final release label for `3.2` (kept as the umbrella label per Assumption 2 until a release-cut decision lands).

---

## References

- `/Users/robert/spec-kitty-dev/spec-kitty-20260521-072712-GA81Uy/start-here.md` — mission brief (verbatim source for goal, workstreams, acceptance criteria, open questions).
- `/Users/robert/spec-kitty-dev/spec-kitty-20260521-072712-GA81Uy/cli-audit-3-2.md` — live CLI audit (192 visible / 5 hidden / 2 deprecated; methodology, gaps, recommended generation method).
- `/Users/robert/spec-kitty-dev/spec-kitty-20260521-072712-GA81Uy/spec-kitty-mission-workflow.md` — standing workflow expectations for missions in this workspace.
- Charter: `.kittify/charter/charter.md` (loaded via `spec-kitty charter context --action specify --json`; policy summary in spec context above).
- Prior CLI reference commits (methodology investigation, FR-006): `a14769e7a`, `81b3d6c3e`, `514106af2`, `deee8d7f3`.
- Public docs URL: `https://docs.spec-kitty.ai/reference/cli-commands.html`.
