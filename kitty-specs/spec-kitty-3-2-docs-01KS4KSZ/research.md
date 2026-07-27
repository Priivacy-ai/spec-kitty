# Research: Spec Kitty 3.2 Documentation Refresh

**Mission**: `spec-kitty-3-2-docs-01KS4KSZ` | **Phase**: 0 (Outline & Research) | **Date**: 2026-05-21

This document consolidates research decisions and the evidence that supports them. Where the planning gate forbids touching the live docs tree, research rows record the planned method and the evidence the tasks phase will gather. Each row follows the `Decision / Rationale / Alternatives` shape.

---

## R-001 — Prior CLI reference methodology

**Decision**: The 3.2 CLI reference is rebuilt with a small generator (`scripts/docs/build_cli_reference.py`) that imports `specify_cli.app` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and `SPEC_KITTY_NO_UPGRADE_CHECK=1` set before import and walks `registered_commands` and `registered_groups` (preferring `group.name`, falling back to `group.typer_instance.info.name`). Hand-authored prose lives outside HTML-comment-delimited generated blocks. Final hand-vs-generator-vs-hybrid choice defers to decision `01KS4KTM69EG2KVX5MQ54FQ939`; plan default is hybrid.

**Rationale**: `cli-audit-3-2.md` already demonstrated this walker against the live Typer app and recovered the full 192-visible / 5-hidden / 2-deprecated set. The audit explicitly recommends this approach and identifies the existing precedent in `tests/architectural/test_safety_registry_completeness.py`. Reusing that pattern keeps the generator tiny and avoids a new dependency.

**Alternatives considered**:
- Hand-author every entry as in `a14769e7a` — rejected: the current reference covers only 113/192 paths because hand-authoring drifts.
- Generate every line including prose — rejected: harness setup, examples, and rationale are editorial content not derivable from `--help` output.
- Use `typer-cli`'s `utils.docs` — rejected: an unmaintained third-party path that would introduce a new dependency for marginal benefit.

**Evidence**:
- `cli-audit-3-2.md` §"Source Evidence" lists prior reference commits `a14769e7a`, `81b3d6c3e`, `514106af2`, `deee8d7f3`.
- `cli-audit-3-2.md` §"Recommended Reference Generation Method" details the env-flag/import contract.
- `tests/architectural/test_safety_registry_completeness.py` walks `group.typer_instance.info.name` — the exact pattern the new generator extends.

---

## R-002 — Doc-site generator confirmation

**Decision**: Treat the site generator as DocFX for planning purposes (the repo contains `docs/docfx.json` per starting observations). The tasks phase confirms with file inspection; if a different generator is found, version-tag implementation in FR-003 pivots to that generator's frontmatter or include mechanism.

**Rationale**: `start-here.md` §"Starting Observations" names `docs/toc.yml`, `docs/*/toc.yml`, and `docs/docfx.json` as the navigation files. DocFX supports YAML frontmatter and nav groups, which fits the five-tag taxonomy.

**Alternatives considered**:
- MkDocs Material — rejected pending confirmation; `mkdocs.yml` is not in the starting observation list.
- Custom static-site script — rejected pending confirmation; not indicated by the starting observations.

**Evidence**: `start-here.md` §"Starting Observations". Tasks-phase WP confirms via direct read of `docs/docfx.json` (read-only inspection allowed once the plan is approved).

---

## R-003 — Harness directory inventory

**Decision**: The candidate harness set for the 3.2 support matrix is the union of (a) directories present in the repo (`.claude/`, `.codex/` (if present), `.cursor/`, `.gemini/`, `.opencode/`, `.qwen/`, `.amazonq/`, `.augment/`, `.kiro/`, `.kilocode/`, `.roo/`, `.windsurf/`, `.agent/`, `.agents/`, `.vibe/` if present), (b) entries in `CLAUDE.md`'s slash-command and Agent Skills tables, and (c) entries in `start-here.md` §"Supported Harness Research" (which adds Pi TUI, GitHub Copilot via `.github/prompts`, and conditional Vibe/Letta Code).

**Rationale**: The tasks-phase WP for D1 cannot author research notes without an authoritative starting list. The three sources reconcile through D1's inventory step (planning artifact only; no host directory mutations).

**Alternatives considered**:
- Use only `CLAUDE.md` table — rejected: misses harnesses listed in `start-here.md` (Pi TUI, Vibe, Letta Code) and any harness directory that may have appeared after the CLAUDE.md table was written.
- Use only `start-here.md` list — rejected: misses any host added to `CLAUDE.md` after that brief was authored.

**Evidence**:
- `CLAUDE.md` §"Supported AI Agents" (13 slash-command agents + 2 Agent Skills agents).
- `start-here.md` §"Supported Harness Research" (16 candidate subjects including conditional ones).

---

## R-004 — External harness doc accessibility

**Decision**: NFR-004 (current external citations per harness) is enforced at publication via the freshness check. Harnesses for which no current public citation can be located are classified at `partial` or lower until evidence lands. The tasks phase produces a `citation_refs` map in the harness research method document.

**Rationale**: Public host docs change frequently; pinning evidence in the page-inventory citation map keeps the support classification verifiable.

**Alternatives considered**:
- Skip citations and treat host-installed files as sufficient evidence — rejected: NFR-004 requires external-doc citation.
- Require citations only at first-class — rejected: ambiguous classification at `supported` level is more dangerous than absent classification.

**Evidence**: `spec.md` NFR-004; `start-here.md` §"Supported Harness Research" §"Research method".

---

## R-005 — Install-platform commands

**Decision**: The 3.2 install lifecycle docs cover three tools (`pip`, `pipx`, `uv tool`) across three platforms (macOS, Linux, Windows). The PyPI package name is `spec-kitty-cli` per `pyproject.toml` (`spec-kitty = "specify_cli:main"` is the entry point, not the distribution name). Verification commands use `spec-kitty --version`.

**Rationale**: `start-here.md` §"Install, Upgrade, and Uninstall Documentation" enumerates the three-by-three matrix and the PyPI command examples. `CLAUDE.md` §"PyPI Release" confirms `spec-kitty-cli` as the package name.

**Alternatives considered**:
- Add `conda-forge` install — rejected: not indicated by the brief and not currently published per `CLAUDE.md`.
- Add `homebrew` install — rejected: not indicated by the brief; would require additional research and packaging.

**Evidence**: `start-here.md` §"Install, Upgrade, and Uninstall Documentation"; `CLAUDE.md` §"PyPI Release (Quick Reference)".

---

## R-006 — Version-tag mechanism

**Decision**: Use YAML frontmatter on each docs page (`version_tag: current | supported | archival | migration | internal`) **plus** a manifest at `docs/development/3-2-page-inventory.yaml`. The leakage check (FR-005) consults both — frontmatter as authoritative, the manifest as the source of truth for what *should* be tagged and where it should sit in nav. Where the site generator does not surface frontmatter natively (decided in R-002), the navigation plan adds explicit nav groups for "3.2 current", "3.1 supported", "Archive (2.x)", "Archive (1.x)", and "Migration".

**Rationale**: Frontmatter alone leaks if a page is added without it; manifest alone drifts if a page is moved without updating the manifest. Cross-checking the two catches both failure modes.

**Alternatives considered**:
- Frontmatter only — rejected: silent gaps when frontmatter is missing; the leakage check cannot distinguish "untagged-by-design" from "untagged-by-accident" without a manifest.
- Manifest only — rejected: bulk-edit-shaped rollout becomes harder to review because reviewers can't see version status inline on the page they're editing.
- Filename-based version prefix (e.g., `3-2-foo.md`) — rejected: prefix renames cascade through internal links and break search indexers.

**Evidence**: `spec.md` FR-001/FR-002/FR-003/FR-005; `start-here.md` §1.

---

## R-007 — Existing freshness/testing patterns

**Decision**: The new architectural test `tests/architectural/test_docs_cli_reference_parity.py` mirrors `tests/architectural/test_safety_registry_completeness.py`: it imports the Typer app with the SaaS env flag set, walks the registered tree, and asserts that the set of non-hidden command paths equals the set discovered in `docs/reference/cli-commands.md`. Hidden paths are excluded; deprecated paths must be classified.

**Rationale**: Reusing the existing pattern keeps the architectural-test surface uniform and makes the parity check easy to understand for any contributor already familiar with the safety-registry test.

**Alternatives considered**:
- A custom doc-side parser — rejected: redundant; the architectural pattern already exists.
- Pre-commit hook only — rejected: pre-commit hooks are bypassable; CI architectural tests are not.

**Evidence**: `tests/architectural/test_safety_registry_completeness.py`; `spec.md` NFR-001 freshness check requirement.

---

## R-008 — Bulk-edit blast radius for version-tag rollout

**Decision**: FR-001/FR-002 rollout (adding `version_tag` frontmatter across every docs page) qualifies as a bulk edit under the `spec-kitty-bulk-edit-classification` skill. The tasks phase invokes the skill for workstream A2 (page inventory + frontmatter rollout) and produces `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/occurrence_map.yaml` covering the 8 standard categories. Workstream C (archive/migration plan) also triggers the skill for the bulk move of 1.x/2.x pages.

**Rationale**: The version-tag rollout adds the same shape of frontmatter key (`version_tag`) to a large number of files. That fits the "same string in many files" definition exactly. The C-008 constraint in `spec.md` already anticipates this; this row makes it concrete.

**Alternatives considered**:
- Treat each workstream as ordinary edits — rejected: bulk-edit guardrails exist because exact this pattern fails review when occurrences drift between files.
- Skip the guardrail since the change is "obviously safe" — rejected: bulk-edit gate exists to catch silent cross-file breakage, not just obviously dangerous renames.

**Evidence**: `spec.md` C-008; bulk-edit skill description (8 categories: code_symbols, import_paths, filesystem_paths, serialized_keys, cli_commands, user_facing_strings, tests_fixtures, logs_telemetry).

---

## Resolved deferred-decision defaults (carried from spec.md)

| Decision ID | Default in plan | When to revisit |
|-------------|------------------|------------------|
| `01KS4KTGTN4DBE60JFWKEA2FJB` (3.1 classification) | Fold 3.1 into 3.2 as migration notes only. | Tasks-phase review; if user resolves to "3.1 as supported version", navigation plan and archive/migration plan add a 3.1 nav group and the migration page list shrinks. |
| `01KS4KTM69EG2KVX5MQ54FQ939` (CLI reference mode) | Hybrid generated body + hand-authored prose. | Tasks-phase review; if user resolves to "fully generated", `check_cli_reference_freshness.py` becomes stricter (no hand-authored prose between `<!-- BEGIN GENERATED -->` markers). |
| `01KS4KTS4V300M9MMTS1AJEGXY` (Harness tiers) | Matrix-first; promote per-harness pages based on evidence. | Tasks-phase review after research method completes; if user resolves to "all 15 first-class", every harness gets a setup-and-usage page regardless of coverage. |

---

## Open research items routed to tasks phase

These items are not blocking the plan but are recorded so the tasks phase executes them in the right order:

1. Confirm DocFX (R-002) by reading `docs/docfx.json` (read-only).
2. Run `git show` on the four prior CLI reference commits (R-001) to write the methodology note `docs/development/3-2-cli-reference-methodology.md`.
3. Inventory harness directories (R-003) by listing top-level dotfile directories; cross-reference with `CLAUDE.md` agent table.
4. Locate external harness docs for citation (R-004); cache citation URLs in the page-inventory manifest.
5. Verify current pip/pipx/uv command shapes (R-005) against PyPI distribution metadata.
6. Run a one-shot inventory of `docs/**/*.md` for the bulk-edit blast-radius estimate (R-008) before invoking the bulk-edit skill.

---

## References

- `spec.md` (this mission)
- `cli-audit-3-2.md` workspace file
- `start-here.md` workspace file
- `spec-kitty-mission-workflow.md` workspace file
- `tests/architectural/test_safety_registry_completeness.py`
- `CLAUDE.md` §"Supported AI Agents", §"PyPI Release (Quick Reference)"
