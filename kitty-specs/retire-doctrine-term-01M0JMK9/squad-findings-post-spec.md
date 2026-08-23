# Adversarial Squad Findings — Post-Spec Review

**Mission**: retire-doctrine-term-01M0JMK9
**Point-cut**: post-specify (spec review before `/spec-kitty.plan`)
**Question**: *Is this spec sound, complete, and implementable — what must be fixed before we plan?*
**Date**: 2026-08-21

## Squad & method

| Lens | Profile | Load status |
|------|---------|-------------|
| Structure / seams / topology | `architect-alphonso` | activated, loaded via CLI |
| Anti-laziness / contract-vs-implementation | `reviewer-renata` | activated, loaded via CLI |
| Doctrine integrity / DRG wiring | `doctrine-daphne` | **degraded** — not activated in this project's charter; inspected via `spec-kitty agent profile show doctrine-daphne --all` (no overlays/lineage applied) |
| Live evidence / coverage | `debugger-debbie` | activated, loaded via CLI |

All delegates read-only. Charter context loaded for action `review` (`--no-mark-loaded`).
**Harness note**: this harness (pi) has no subagent dispatch tool and 0 MCP servers, so the four
lenses ran as sequential structured passes with profiles loaded via CLI — not parallel subagents.
Each pass is grounded in live repo evidence gathered 2026-08-21 (cited inline).

---

## Lens 1 — Architect Alphonso (structure / seams / topology)

Applied: profile initialization (architect; design/evaluate/decide/model/specify; no implementation
code); charter context `review` (single canonical authority, architectural alignment).

- **[HIGH]** spec.md:127,96 (Key Entities / FR-002) — the first canonical sense of "charter",
  *"charter.md file"*, contradicts ADR `2026-07-18-1` ("charter.yaml is the authoritative
  structured source; charter.md is a curated companion"). Live topology: `.kittify/charter/` is a
  **bundle** — `charter.yaml` (117 KB, authoritative), `charter.md` (36 KB, companion),
  `graph.yml`, `interview/`, `synthesis-manifest.yaml`; both files are tracked as a pair
  (`src/charter/bundle.py:35,128`). An ADR that canonizes "the charter.md file" as a sense of the
  term either silently demotes `charter.yaml`'s authority or leaves it unmentioned — and the
  downstream glossary rewrite inherits the error. **Recommendation**: define sense 1 as *the
  charter bundle* (or explicitly name both files and their authority relationship) and have the ADR
  reconcile with `2026-07-18-1`.
- **[HIGH]** spec.md:139 (Domain Language) — the three-way distinction misses existing senses of
  "charter": (a) the `spec-kitty charter` CLI command group (`activate/deactivate/generate/
  synthesize/resynthesize/list/context/sync`), (b) the `.kittify/charter/` directory. A glossary
  table that defines exactly three senses cannot cover a fourth sense the ADR never enumerates.
  **Recommendation**: enumerate the command-group/directory senses or state explicitly that the
  umbrella covers them.
- **[MEDIUM]** spec.md:26 (US1-AS2) — the ADR being amended, `2026-07-15-1`, is
  `status: Proposed` (verified in frontmatter), not Accepted. Amending a proposed ADR's terminology
  portion is low-risk, but the spec should record that; its title ("Doctrine Offers, Charter
  Activates…") is itself a legacy-marked snapshot under C-003.
- **[MEDIUM]** spec.md:85,127 (edge case 1 / Assumption 4) — the `src/charter/` vs `src/doctrine/`
  disambiguation is acknowledged, but the spec never states which package owns user-facing strings.
  Live evidence: `src/charter/context_renderers/bootstrap_text.py` emits the "Action Doctrine"
  heading — user-facing doctrine strings live **inside** `src/charter/`. The inventory needs a
  string-level rule (user-facing strings in `src/` are in scope; identifiers are out), not a
  path-level rule.

**Verdict**: the stacked-mission structure and ADR-amendment mechanics are sound; the vocabulary
core (the three-way distinction) is mis-anchored against two existing ADRs and the actual bundle
topology. **Concession**: I do not judge the deprecation-alias mechanics (3.x hidden aliases +
warnings) — that is a compatibility-policy question outside my lens.

## Lens 2 — Reviewer Renata (anti-laziness / contract-vs-implementation)

Applied: profile initialization (quality gate; structured feedback); charter context `review`
(code-review checklist, regression-vigilance precedent — the `--feature`→`--mission` rename is
this repo's direct prior art for a terminology retirement).

- **[HIGH]** spec.md:26 (US1-AS2) — "the old ADR's status is updated accordingly **in the index**"
  is factually wrong: `docs/adr/3.x/index.md` has only `Date | Title` columns (verified, line 73).
  Status lives in each ADR's frontmatter; the repo has a `status: Superseded` convention (5 ADRs).
  As written the scenario is unimplementable as stated and invites a fakeable workaround (adding a
  status column to the index, or editing nothing). Worse: updating frontmatter means **editing an
  old ADR file**, which collides with C-003 ("historical artifacts immutable") unless the spec
  carves out status metadata. **Recommendation**: name the real mechanism (frontmatter
  `status: Superseded` + "superseded by" pointer) and explicitly exempt status frontmatter from
  C-003 immutability.
- **[HIGH]** spec.md:110,150 (NFR-001 / SC-002) — the completeness claim is circular as written:
  "a case-insensitive audit finds 0 unclassified occurrences **in in-scope user-facing surfaces**"
  — but "in-scope user-facing surfaces" is defined by the inventory itself. A lazy execution
  enumerates only the surfaces it found and declares 100%. **Recommendation**: pin a mechanical
  audit procedure — search space (all tracked files minus `.git`/worktrees/vendor), a
  classification rule for **every** hit (in-scope surface / internal identifier / legacy-marked
  historical artifact), and a named artifact recording the classification. Also: SC-002's
  "spot-check audit" is weaker than NFR-001's full audit — align the two.
- **[MEDIUM]** spec.md:59,85,121 (US3-AS3 / edge case / C-004) — "the guard is updated
  **shrink-only**" misdescribes the required first step: `tests/architectural/
  test_no_legacy_terminology.py` currently forbids only "ceremony" and "status-writing"
  (verified) — it does **not** forbid "doctrine". Wave 0 must add "doctrine" to
  `_FORBIDDEN_TERMS` with all in-scope surfaces exempted, then shrink exemptions. The spec should
  state this so a planner doesn't assume the guard already covers "doctrine".
- **[MEDIUM]** spec.md:121 (C-004 vs FR-006) — the guard's `_SCAN_ROOTS` are `src`, `tests`,
  `docs` (verified). In-scope surfaces outside those roots — `packs/built-in/` (275 hits),
  `.kittify/charter/` (374 hits), README/CHANGELOG/AGENTS — are not scanned at all. "Stays green
  at every stack level" is vacuous for them unless the methodology extends scan roots (a **grow**,
  contradicting "shrink-only") or assigns a separate verification mechanism per surface class.
  **Recommendation**: assign each surface class to exactly one verification mechanism.
- **[LOW]** spec.md:149 (SC-001) — "1/1 review pass" is single-sample; acceptable, but name who
  the independent reviewer is (squad or human) in this workflow.

**Verdict**: US3's scenarios (alias verification, guard discipline at wave boundaries, 4.0
zero-doctrine audit) and FR-010/SC-004 ("specify the first mission from artifacts alone") are
genuinely non-fakeable — good ATDD shape. The two HIGH findings are contract-vs-reality defects:
the spec cites mechanisms (index status, guard coverage) that do not exist as described.
**Concession**: I cannot judge whether the surface *categories* themselves are the right split —
that is an architecture question, not a review one.

## Lens 3 — Doctrine Daphne (doctrine integrity / DRG wiring) — degraded load

Applied: profile initialization via `--all` (pack curation, DRG registration discipline, kind
taxonomy); charter context `review`. **Caveat**: profile not activated in this project's charter —
overlays and `specializes_from` lineage were not applied.

- **[HIGH]** spec.md:97,122 (FR-004 / C-005) — the scope boundary "internal code identifiers out
  of scope" conflates two different things: (a) Python package/module/import names (`src/doctrine/`,
  `import doctrine…`) — genuinely internal; and (b) **operator-typed identifiers that are DRG node
  IDs**: `agent_profile:doctrine-daphne` (typed into `spec-kitty agent profile show
  doctrine-daphne`; file exists at `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`),
  directive IDs like `018-doctrine-versioning-requirement`, and skill names (`spk-doctrine-*`).
  Class (b) is user-facing language — operators type it, agents route on it. The spec's edge cases
  name skill names but **not** profile/directive IDs. As written, downstream missions will each
  classify these differently — exactly the drift this program exists to prevent.
  **Recommendation**: add an explicit "user-facing identifiers" decision (in scope with aliases, or
  out of scope as a named exception) to the ADR.
- **[HIGH]** spec.md:139 (Domain Language / FR-002) — the glossary page `docs/context/doctrine.md`
  defines **"Doctrine Domain"** as a DDD bounded context (the domain model structuring reusable
  governance knowledge; `Location: src/doctrine/`) — a sense of "doctrine" the three-way
  distinction (file/active/inactive) does not cover. If "doctrine" is retired from user-facing
  language, the ADR must say what replaces the *domain* sense ("Charter Domain"?) — otherwise the
  glossary rewrite has no canonical term for a concept other glossary pages link to.
- **[MEDIUM]** spec.md:98 (FR-003) — the kind vocabulary surviving is correct, but pack artifact
  *titles/IDs* surface in generated output (`charter context` prints pack file paths and the
  "Action Doctrine" heading). Surviving kinds ≠ the word "doctrine" disappearing from pack-derived
  output. The inventory must treat pack artifact IDs/titles as their own occurrence class (275
  hits in `packs/`).
- **[MEDIUM]** spec.md:84 (edge case 4) — the charter file is a bundle, and `charter.yaml`
  (53 doctrine hits) carries **more** occurrences than `charter.md` (13). Per ADR
  `2026-07-18-1`, `charter.yaml` is the authoritative source — "updating the charter file" means
  editing `charter.yaml` (and regenerating), not hand-editing `charter.md`. The edge case names
  only `charter.md`; the methodology must target the right file or it breaks on regeneration.

**Verdict**: the spec's instinct to preserve the kind vocabulary and DRG edge semantics is right;
its scope boundary is drawn through the middle of the identifier space and will split downstream.
**Concession**: my lens is weakest here due to the degraded load, and I cannot verify org-pack-side
doctrine surfaces (org packs live outside this repo).

## Lens 4 — Debugger Debbie (live evidence / coverage)

Applied: profile initialization (investigator; falsify/trace/converge); charter context `review`.

- **[HIGH]** spec.md:86 (edge case "Deprecation aliases must actually work") — the spec names
  `spec-kitty doctor doctrine` as *an example* of a deprecated executable, but the live CLI shows
  a full **top-level `spec-kitty doctrine` command group with 9 subcommands** (`fetch`,
  `regenerate-graph`, `new`, `validate`, `pack`, `org`, `mission-type`, `asset`), all with
  "doctrine" in help text. That is the largest single CLI surface for this term and it is named
  nowhere in the spec. The inventory will catch it under "CLI surfaces", but the edge-cases
  section — where the spec demonstrates awareness of tricky surfaces — misses it, and the alias
  design (hidden + warning) must cover a 9-command group, not one command.
- **[MEDIUM]** spec.md:38 (US2-AS1) — "Given the repository at this mission's base" limits the
  inventory to this repo, but user-facing surfaces also exist in sibling repos (spec-kitty-saas
  dashboard — not checked out locally, unverifiable). Assumption 3's default-out rule covers this
  implicitly; the spec should state it explicitly (cross-repo surfaces deferred, with rationale) so
  a downstream mission doesn't silently inherit the gap.
- **[MEDIUM]** spec.md:26,120 (US1-AS2 / C-003) — verified: the 3.x ADR index has no status
  column; **10** ADRs in `docs/adr/3.x/` carry "doctrine" in their titles (not just the one being
  amended). C-003's retain-as-legacy classification must cover all 10, and the spec should say
  that only ADRs whose *decisions* are amended get a status change.
- **[LOW]** spec.md:40 (US2) — live scale for planning: `src` 3899 / `tests` 7496 / `docs` 12291 /
  `packs` 275 / `.kittify` 374 / `kitty-specs` 29277 (legacy) matching lines. The "representative
  examples" requirement is proportionate to the docs/ volume.

**Verdict**: every factual claim in the spec I could check checked out (glossary page, referenced
ADR, ADR template, freshen script, `src/charter` + `src/doctrine` coexistence, Charter Resolution
Hints block at charter.md:548) — but the spec's awareness of *specific* tricky surfaces stops
short of the two biggest ones (the `spec-kitty doctrine` group; the charter bundle's yaml half).
**Concession**: counts are line-based, not occurrence-based — the inventory mission needs its own
counting methodology; and I could not verify SaaS-side surfaces (repo absent locally).

---

## Synthesis

**Convergent findings (≥2 lenses, adjudicated from source):**

| # | Finding | Lenses | Adjudication (source) |
|---|---------|--------|----------------------|
| 1 | Sense 1 of the three-way distinction is misnamed: it is a **bundle** (`charter.yaml` authoritative + `charter.md` companion), not "the charter.md file" | Alphonso (HIGH) + Daphne (MEDIUM, counts corroborate) | ADR `2026-07-18-1` frontmatter; `src/charter/bundle.py:35,128`; live file sizes |
| 2 | **User-facing identifiers** (profile IDs, directive IDs, skill names) are unclassified — the scope line cuts through operator-typed DRG node IDs | Daphne (HIGH) + Renata (circularity, same gap) | `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`; live CLI accepts the ID |
| 3 | **Guard mechanics misdescribed**: guard does not currently forbid "doctrine"; scan roots exclude `packs/`, `.kittify/`, root files — C-004 "shrink-only" needs a wave-0 grow + per-surface verification assignment | Renata (MEDIUM×2) + Debbie (live evidence) | `tests/architectural/test_no_legacy_terminology.py` (`_FORBIDDEN_TERMS`, `_SCAN_ROOTS`) |
| 4 | **US1-AS2 status mechanism is wrong**: index has no status column; real convention is frontmatter `status: Superseded`; editing old ADR frontmatter collides with C-003 without a carve-out | Renata (HIGH) + Debbie (MEDIUM) | `docs/adr/3.x/index.md:73` (`Date \| Title`); 5 ADRs with `status: Superseded` |
| 5 | **`spec-kitty doctrine` command group (9 subcommands) unnamed** in the spec; alias design must cover it | Debbie (HIGH) + Alphonso (string-level boundary) | live `spec-kitty doctrine --help` |
| 6 | **Three-way distinction under-inclusive in both directions**: misses existing "charter" senses (command group, directory) and says nothing about what replaces the "Doctrine Domain" sense | Alphonso (HIGH) + Daphne (HIGH) | `docs/context/doctrine.md` ("Doctrine Domain" entry); live CLI |

**Divergences**: none material — no two lenses disagreed on a consequential point. Daphne's
degraded load is the only caveat; her HIGH findings are independently corroborated by direct file
evidence, so no second-opinion dispatch was required.

## Overall verdict

**Not yet plan-ready.** The spec is structurally sound — good ATDD shape, non-fakeable US3
scenarios, correct edge-case instincts, and every checkable factual claim verified true. But four
HIGH findings must be folded into `spec.md` before `/spec-kitty.plan`:

1. Rename sense 1 to *the charter bundle* (or explicitly name `charter.yaml` + `charter.md` and
   their authority relationship); reconcile the ADR with `2026-07-18-1`.
2. Add an explicit **user-facing identifiers** decision (profile/directive/skill IDs: in scope
   with aliases, or out of scope as a named exception).
3. Fix US1-AS2: name the real status mechanism (frontmatter `status: Superseded` + pointer) and
   carve status frontmatter out of C-003 immutability.
4. Name the `spec-kitty doctrine` command group in edge cases; fix C-004 to state the wave-0 guard
   grow (add "doctrine" with full exemptions) and assign each surface class to exactly one
   verification mechanism.

**MEDIUMs to fold in the same pass**: enumerate existing "charter" senses (command group,
directory); define what replaces "Doctrine Domain"; pin the mechanical audit procedure for NFR-001
(search space + classify-every-hit rule + named artifact) and align SC-002 with it; state
cross-repo (SaaS) deferral explicitly; note that 10 ADRs carry "doctrine" in titles (all
retain-as-legacy except the one amended); note `2026-07-15-1` is `Proposed`.

*This document is a review artifact (adversarial-squad point-cut output). It does not gate the
mission and does not execute any rename (C-001).*

---

## Addendum 2026-08-21 — pack/bundle naming resolution (operator decision moment)

The operator proposed renaming sense 1 to **"charter pack"** (not "charter bundle") and then asked
whether packs and bundles are different things, and whether the glossary makes that clear.
Research (pack-composer repo + this codebase) resolved it as follows:

**Packs and bundles ARE different things:**

| | Pack (Doctrine Pack) | Bundle (charter bundle) |
|---|---|---|
| What | Versioned, distributable **catalogue** of governance artefacts (glossary terms, tactics, directives, profiles, styleguides, toolguides) | Per-project, sync-materialized **file set** under `.kittify/charter/` (v2: `charter.yaml` + derivatives) |
| Side of flow | **Offer** side — "Doctrine (packs) OFFER a catalogue" (ADR 2026-07-15-1) | **Consume** side — what `charter sync` materializes; validated by `CharterBundleManifest v2.0.0`; `spec-kitty charter bundle validate` |
| Identity | Doctrine Pack ID (`built-in`, `project`, org pack names) in `.kittify/config.yaml` | File set + freshness hash (`BUNDLE_CONTENT_HASH_FILES = ("charter.yaml",)`) |
| Lives in | `packs/built-in/`, org remotes / open-packs, `.kittify/doctrine/` | `.kittify/charter/` per project |
| Tooling | **pack-composer** (spec-kitty/spec-kitty-pack-composer) composes these; `spec-kitty doctrine pack validate/assemble`, `doctrine fetch` | `src/charter/bundle.py`, sync pipeline |

**The glossary does NOT make the distinction clear:**
- "Doctrine Pack" is defined (`docs/context/doctrine.md:297`) — matches what pack-composer composes.
- **"Charter Bundle" has no term entry anywhere in `docs/context/`** — used heavily as a word
  (charter-overview.md, governance-files.md "Bundle Validation") but never canonically defined.
- The "Doctrine Pack" definition itself uses "bundle" generically ("a versioned, distributable
  bundle of doctrine artefacts") — muddying the distinction.
- "Bundle" carries ≥3 other code senses, none glossary-defined: action-doctrine bundle
  (`src/charter/action_doctrine_bundle.py` — runtime resolution payload), prompt bundles
  (WP task files, `docs/context/spec-driven.md`), tool-surface bundles
  (`src/specify_cli/tool_surface/bundles/`).

**Decision**: sense 1 stays **"charter bundle"** — "charter pack" would collide with the existing
canonical *Doctrine Pack* term (conflating offer side with consume side). Spec updated: FR-002,
Key Entities, Domain Language (with "charter pack" listed as a do-NOT-use), new edge case, and
**new FR-011** (glossary gap closure: add Charter Bundle entry, disambiguate from pack + other
bundle senses, fix the Doctrine Pack definition's generic "bundle", define what replaces the
"Doctrine Domain" sense). All four HIGH findings + MEDIUMs from the main review were folded into
`spec.md` in the same pass.
