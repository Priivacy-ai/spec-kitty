# Research: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 0 output** of `/spec-kitty.plan` · **Date**: 2026-08-21
**Base**: repository root checkout on `feat/retire-doctrine-term` (all evidence gathered live at this base, 2026-08-21)

Every item below is a resolved unknown: **Decision / Rationale / Alternatives considered**. No `NEEDS CLARIFICATION` items remain — the three specify-phase decision moments are resolved (`spec-kitty agent decision verify`: clean), and the one plan-phase decision (stack shape) was resolved with the operator as `01M0JWDEMKXQ5CMAE9PFEK8GF9`.

---

## R1 — ADR conventions: template, naming, index mechanism

**Decision**: Author the new ADR from `docs/architecture/adr-template.md`, dated name `2026-08-21-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md` under `docs/adr/3.x/` (N = next free number at creation; latest existing is `2026-08-20-1`), and register it with `python -m scripts.docs.freshen_adr_inventory` (module form per C-002).

**Rationale**: Verified live: the template exists; `docs/adr/3.x/index.md` carries only `Date | Title` columns (no status column — status lives in each ADR's frontmatter, per the five existing `status: Superseded` ADRs); the freshen script updates **both** the era index table row and the `docs/development/3-2-page-inventory.yaml` lockfile in one command, and the `docs-freshness` CI gate enforces both (`LEAK-MISSING-INVENTORY`, `INVENTORY-INCOMPLETE`, `INVENTORY-LOCKFILE-DRIFT` failure modes are documented in the script's own docstring).

**Alternatives considered**: Hand-editing index + lockfile — rejected (the script exists precisely because agents repeatedly trip the gate by forgetting one of the two). Adding a status column to the index — rejected (squad finding 4: no such convention exists; frontmatter is the mechanism).

## R2 — Terminology guard mechanics (what wave 0 must build)

**Decision**: The methodology's guard-arming design adds a **file-level frozen exemption baseline** to `tests/architectural/test_no_legacy_terminology.py`: every in-scope file under the scan roots (`src`, `tests`, `docs`) that currently contains "doctrine" is enumerated; the baseline is shrink-only (a file leaves it only when its in-scope count reaches zero); a self-mutation test pins the mechanism (Standing Order #5: concrete floor + shrink-only allowlist). M2's alias tests reference the old command names via **string-fragment construction** (the guard's existing self-flag defense) so they don't trip the term.

**Rationale**: Verified live: `_FORBIDDEN_TERMS = ("cere"+"mony", "status"-"writing")` — the guard does **not** currently forbid "doctrine"; `_SCAN_ROOTS = ("src", "tests", "docs")`; exclusions are **path-fragment** based (`kitty-specs/`, `docs/adr/`, `src/doctrine/glossary_packs/built-in/`, vendor/worktree paths, the test file itself) with **no per-file exemption mechanism for active surfaces** — so "exempt all in-scope surfaces" (C-004) is new machinery, not a config tweak. The string-fragment construction pattern already exists in the guard and is the proven way for tests to quote forbidden terms.

**Alternatives considered**: (a) Line-level exemptions — rejected: brittle under concurrent edits, and the guard's existing seam (`_line_is_excluded`) is path-fragment shaped. (b) Directory-level exemptions — rejected: would make the guard vacuous for `src/` and `docs/` (429 + 430 files contain the term; most are internal identifiers or legacy-adjacent prose). (c) Extending `_SCAN_ROOTS` to `packs/`, `.kittify/`, root docs — rejected as the primary mechanism (a *grow* contradicting C-004's shrink-only framing); those classes get the NFR-001 audit as their named verification mechanism instead (C-004's per-surface assignment).

## R3 — Charter bundle topology and update path

**Decision**: M1 updates the bundle by editing **`charter.yaml` (the authoritative structured source per ADR `2026-07-18-1`) and regenerating** via the canonical sync machinery — never hand-editing `charter.md`. The bundle update includes a new Terminology Canon line ("charter, not doctrine") whose exact content is fixed by this mission's ADR (IC-01), so M1 executes rather than re-decides.

**Rationale**: Verified live: `.kittify/charter/` is a bundle — `charter.yaml` (53 doctrine lines), `charter.md` (13), `graph.yml` (2), `interview/answers.yaml` (9); both files are tracked as a pair (`src/charter/bundle.py`). Hand-editing `charter.md` breaks on the next sync (spec edge case, corroborated by squad Lens 3).

**Alternatives considered**: Hand-editing `charter.md` — rejected (breaks on regeneration; violates ADR 2026-07-18-1 authority). Updating the bundle in a later wave — rejected (the bundle is the per-session instruction surface; flipping it early is what makes subsequent catfooding missions self-correct — see R8/C3).

## R4 — CLI executable surface: the `spec-kitty doctrine` group does not map 1:1 onto `charter`

**Decision**: This plan fixes only the **alias policy** (old names become hidden aliases with deprecation warnings during 3.x; per-subcommand alias tests; removal at 4.0 verified by audit). The **per-subcommand canonical naming** (which of the 8 `doctrine` subcommands maps onto the existing `spec-kitty charter` group vs. gets a new name under it) is a design decision owned by M2's spec, informed by the inventory. Same-wave CI consumer updates are a hard requirement of M2 (see R5).

**Rationale**: Verified live: `spec-kitty doctrine --help` shows 8 subcommands (`fetch`, `regenerate-graph`, `new`, `validate`, `pack`, `org`, `mission-type`, `asset`) plus `spec-kitty doctor doctrine`; the existing `charter` group has a different shape (`activate/deactivate/generate/synthesize/resynthesize/list/context/sync`). A 1:1 rename is impossible; forcing one here would pre-empt M2's design with an unreviewed choice.

**Alternatives considered**: Deciding the full command mapping in this plan — rejected (out of scope for a planning mission; the inventory + M2 spec are the right home). Hard break without aliases — rejected (operator decision moment `specify.compatibility.alias-policy` resolved to 3.x deprecation).

## R5 — Scripted consumers of doctrine-named surfaces (CI is a hard dependency)

**Decision**: "Scripted consumers" is a **distinct occurrence class** in the inventory with a same-wave update requirement: any wave that renames or aliases a command must update its CI consumers in the same PR.

**Rationale**: Verified live: `.github/workflows/ci-quality.yml:4055` runs `spec-kitty doctor doctrine --json` and asserts on the output (NFR-002 check); three workflow **filenames** carry "doctrine" (`doctrine-charter-tests.yml`, `module-doctrine-fast.yml`, `module-doctrine-integration.yml`) and are referenced via `uses:`; `.github/prompts/spec-kitty-standalone.md` is a Copilot prompt (agent artifact); `scripts/generate_schemas.py:548` carries a user-facing string. `.github/` is outside the guard's scan roots — its verification mechanism is the NFR-001 audit (C-004 assignment).

**Alternatives considered**: Treating CI files as ordinary docs prose — rejected (they execute; a rename that breaks them fails every PR, not just one doc page).

## R6 — Glossary gap (FR-011 content)

**Decision**: The ADR fixes the FR-011 decisions so M1's glossary rewrite executes rather than re-decides: (a) add a canonical **Charter Bundle** term entry; (b) disambiguate it from *Doctrine Pack* (offer side: versioned distributable catalogue — `packs/built-in/`, org packs) and from the other code senses of "bundle" (action-doctrine bundle, prompt bundles, tool-surface bundles); (c) fix the "Doctrine Pack" definition's use of "bundle" as a generic word; (d) define what replaces the **"Doctrine Domain"** sense (the DDD bounded-context entry, `Location: src/doctrine/`) — plan position: the domain sense retires with the term; the glossary entry is rewritten to name the governance-artefact layer without a "domain" re-brand (the ADR states the final wording).

**Rationale**: Verified live: `docs/context/doctrine.md` is 685 lines / 124 doctrine lines / 54 headings; "Doctrine Pack" is defined at line ~297 and uses "bundle" generically; **no "Charter Bundle" term entry exists anywhere in `docs/context/`** (the word is used heavily but never canonically defined); "Doctrine Domain" is a glossary sense the three-way distinction does not cover (squad Lens 3, HIGH).

**Alternatives considered**: Leaving the FR-011 wording decisions to M1 — rejected (FR-010/SC-004: the first stack mission must be spec-ready with 0 new decisions). Renaming sense 1 to "charter pack" — rejected (operator decision moment, addendum to `squad-findings-post-spec.md`: collides with the canonical *Doctrine Pack* term, conflating offer side with consume side).

## R7 — Canonical source locations for user-facing artifacts inside `src/doctrine/`

**Decision**: The inventory applies a **string-level scope rule**, not a path-level one: user-facing *artifacts* stored inside `src/doctrine/` are in scope even though the package path is not. Verified canonical sources: **skills** live at `src/doctrine/skills/` (55 skill directories, incl. 7 `spk-doctrine-*`; plus a README.md; names are operator/harness-routed identifiers and SKILL.md content is agent-facing prose); **artifact YAML** (directives, tactics, styleguides, toolguides, procedures, paradigms, agent profiles) lives at `packs/built-in/<kind>/` — the hatch build hook (`src/doctrine/hatch_build.py`) ships `packs/built-in` into site-packages as a sibling of the installed package, so `packs/` is the canonical source and `src/doctrine/<kind>/` is Python code (identifiers out of scope per C-005). **Glossary-pack data** at `src/doctrine/glossary_packs/built-in/` is already guard-exempt as quoted data (documents deprecated terms) and stays classified accordingly.

**Rationale**: Squad finding 1/Lens 1 (HIGH): the spec's scope boundary needs a string-level rule because user-facing doctrine strings live inside `src/charter/` (e.g. the "Action Doctrine" heading in `src/charter/context_renderers/bootstrap_text.py`) and user-facing artifacts live inside `src/doctrine/skills/`. A path-level rule would misclassify both.

**Alternatives considered**: Path-level exclusion of all of `src/doctrine/` — rejected (would silently drop the 55 skill directories from scope). Treating `src/doctrine/<kind>/` Python as in-scope — rejected (C-005: internal identifiers untouched).

## R8 — Catfooding conflict analysis (developing spec-kitty with spec-kitty during the program)

**Decision**: The methodology manages six identified conflicts (C1–C6), with the load-bearing one closed by construction:

- **C1 (sharp) — guard arming vs. uncanonical replacement vocabulary.** If the guard started forbidding "doctrine" in `src/tests/docs` before the glossary rewrite landed, concurrent catfooding missions would be trapped: old word fails CI; new terms not yet canonical (DIRECTIVE_048, required). **Closed by the atomic authority flip**: glossary + charter-bundle update + guard arming land in one mission/PR (M1, guard-arming WP last). Before M1: status quo. After: new vocabulary canonical *and* guard armed — no conflict window.
- **C2 — exemption snapshot vs. concurrent new occurrences.** File-level frozen baseline (R2): new files/lines outside the baseline containing "doctrine" fail CI — the intended pressure (new content must use the new vocabulary, which is canonical after M1). Known blind spot stated explicitly: count growth *inside* baseline files is invisible to the guard; per-wave NFR-001 re-baselining catches it.
- **C3 — instruction-surface lag.** AGENTS.md (10 doctrine lines, case-insensitive), the charter bundle (77 lines/4 files), and pack prompts/skills keep telling agents to say "doctrine" until their waves land. Consequence: new `kitty-specs/` artifacts keep generating "doctrine" — not guard-scanned, self-classifying as legacy-marked snapshots at merge (C-003); expected drift, re-baselined per wave. The charter-bundle flip (M1) is the self-correcting lever: it loads at every session start, so after M1 all new missions are instructed in the new vocabulary.
- **C4 — generated output.** `charter context` prints an "Action Doctrine" heading + pack paths with doctrine in the name until M2/M3. Noise, not breakage — but a trap: copying that output into a *new* `docs/` file fails the guard (new files aren't in the baseline). Methodology rule: quote pre-rename generated output only inside baseline files, or after the relevant wave.
- **C5 — scripted consumers.** R5: same-wave CI consumer updates are a hard requirement of any wave that renames a command.
- **C6 — this mission itself: zero friction.** C-001 means no surface is touched; our artifacts live in `kitty-specs/`, already in the guard's exclusion list. The program's own catfooding footprint is self-classifying as legacy at merge.

**Per-level invariants** (carried into `methodology.md`): **I0** pre-M1 — status quo, zero terminology friction for concurrent missions. **I1** post-M1 — new vocabulary canonical in glossary + bundle; guard armed with frozen baseline (shrink-only); new `src/tests/docs` content must use the new vocabulary; `kitty-specs/` drift expected and re-baselined per wave. **I2–I5** post each later wave — baseline shrinks; that surface's instruction output flips; CI consumers updated same-wave. **I6** at 4.0 — aliases removed; NFR-001 audit finds zero user-visible "doctrine" outside legacy-marked artifacts + internal identifiers.

**Rationale**: Operator question at plan phase ("will there be conflicts between what we've forbidden vs. what spec-kitty still tells the model to do?") — answered with live evidence (R2 guard mechanics, R3 bundle topology, R5 CI surface). The C1 hazard is the reason M1 is atomic rather than a separate guard wave 0.

**Alternatives considered**: Separate guard-wave-0 mission preceding the glossary — rejected (creates the C1 conflict window). Coarser 3-mission grouping — presented to operator; per-wave shape chosen (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`).

## R9 — Bulk-edit classification: this mission is NOT a bulk edit; downstream rename waves are

**Decision**: This mission does **not** set `change_mode: bulk_edit` and produces no `occurrence_map.yaml`: C-001 bounds it to planning artifacts — its diff creates new documents (which quote the term as subject matter) and changes one ADR's status frontmatter; it modifies no existing "doctrine" occurrence in any user-facing surface. If the implement-time `Bulk Edit Inference Warning` fires (the spec's subject matter matches rename keywords), the correct response is `--acknowledge-not-bulk-edit` with this rationale. **Each downstream rename wave (M2–M5) is a `change_mode: bulk_edit` mission** with its own scoped `occurrence_map.yaml` (all 8 standard categories, per the `spec-kitty-bulk-edit-classification` skill) — recorded as a methodology requirement in each stacked-plan entry.

**Rationale**: The bulk-edit skill's decision tree asks whether fulfilling the request requires changing the same existing string in more than one file — for *this* mission, no (C-001). The skill's own dismissal clause covers exactly this case: inference fired on a spec that describes a rename program the mission is forbidden from executing.

**Alternatives considered**: Pre-marking this mission `bulk_edit` "to be safe" — rejected (would force an occurrence map classifying surfaces this mission never touches, and the map's 8 code-oriented categories don't fit a docs-only diff; false-positive cost is real here because the gate would block implement over an artifact that misdescribes the mission).

## R10 — ADR `2026-07-15-1` amendment mechanics

**Decision**: Amend per US1-AS2: the new ADR explicitly supersedes the *terminology portion* of `2026-07-15-1` while leaving its resolution mechanics intact; the old ADR's frontmatter `status:` changes from `Proposed` to `Superseded` with a pointer to the new ADR; its body stays byte-for-byte untouched (C-003 carve-out for status frontmatter).

**Rationale**: Verified live: `2026-07-15-1` carries `status: Proposed` (amending a proposed ADR is low-risk — squad Lens 1, MEDIUM); the repo's `Superseded` convention is frontmatter-based (5 ADRs); 11 ADRs in `docs/adr/3.x/` carry "doctrine" in their titles — 10 retain-as-legacy under C-003 + the one amended (`2026-07-15-1`) (squad Lens 4; count corrected by the post-plan coverage squad, 2026-08-21).

**Alternatives considered**: Marking all 11 doctrine-titled ADRs `Superseded` — rejected (only an ADR whose *decision* is amended gets a status change; titles are immutable snapshots). Editing the old ADR's body to fix terminology — rejected (C-003: historical artifacts immutable).
