# Research & Design Decisions: Frozen-baseline toll reduction

Design decisions settled by an architect-alphonso pass, grounded in the live tree (HEAD `bec70135f`) and re-verified against `main` (the June audit was found stale once). This resolves the two C-002 deferrals plus the FR-002 strategy, the `_baselines.yaml` merge-coupling, and the NFR-002 unit.

## Re-verified live values (fixtures MUST key off these)

| Value | Live (verified) | Source |
|---|---|---|
| `skip_marker_blocks` baseline | **13** | `_baselines.yaml:173` |
| `category_1_auto_discovered_migrations` baseline | **100** | `_baselines.yaml:34` = `len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` |
| `m_*.py` file count | **105** | glob `src/specify_cli/upgrade/migrations/m_*.py` |
| dead-migration count (glob ∩ no-static-importer) | **100** | 105 − 5 statically-imported (`m_0_9_1_complete_lane_migration`, `m_2_1_3_restore_prompt_commands`, `m_3_1_2_globalize_commands`, `m_3_2_0rc35_sync_state_gitignore`, `m_unify_charter_activation`) |
| duplicate `bare_name`s in dead-symbol allowlist | **10** (3 already collision-tier, **7 content-tier**) | 354 `SymbolKey` entries (329 content + 25 collision) |
| `test_ratchet_baselines` slowest call (warm) | **0.32 s** | live timing |
| `test_ratchet_positional_anchor_ban` slowest call (warm) | **0.52 s** | live timing |
| transitive `test_example_round_trip` corpus walk (warm) | **0.147 s**, deferred to execution | not module-scope |

The **105→100 delta of 5** is exactly the over-count FR-004's edge case warns against — derivation MUST use the gate's predicate, not a raw glob.

## Decision 1 — C-002a: FR-003 reviewable-with-teeth mechanism

- **Decision**: Extract `skip_marker_blocks` from the shared `single_baselines` growth-fail loop into a **dedicated `fast`-tier test that does not `pytest.fail` on growth** (baseline as a shrink-tracked high-water mark). The **teeth are structural**: adding a skip requires committing a co-located `# round-trip: skip: <mandatory reason>` line (reason enforced by the existing `_SKIP_MARKER_RE`) that is always in the PR diff. Growth is also routed through `record_property` as a report backstop. Anti-silencing (US2-AC2) is preserved by leaving `_classify_yaml_block`'s frontmatter-wins/neither-fails rules and the `legacy_contract_allowlist` tuple untouched.
- **Rationale**: The count hard-fail's only function was to force a human to look; the mandatory co-located reason is a *stronger* reviewer signal (on the block, states why, rides the diff) and needs no new CI job or external service. Anti-silencing is inherently human judgment; the mechanism's job is to keep it visible, which the diff line does.
- **Alternatives rejected**: derive the skip count (kills growth *and* shrinkage signal — self-heals silently); auto-generate the baseline bump (still blocks CI, hides reason in a machine edit); `record_property`/`warnings.warn` as the *primary* teeth (spec forbids "only stderr").

## Decision 2 — C-002b: FR-004 frozenset disposition

- **Decision**: **KEEP** `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` as a load-bearing change-detector; derive **only** the redundant `category_1` **count** in `_baselines.yaml` as **`len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)`** (the frozenset, already imported at `test_ratchet_baselines.py:270/:405`). The residual one-line frozenset edit per new migration is retained deliberately. **[Post-plan correction] Do NOT derive from a re-globbed `glob ∩ no-static-importer` predicate — there is no exposed accessor, so re-implementing it creates a `_has_caller` split-brain; `len(frozenset)` is the single authority. The count-check thereby becomes non-load-bearing, which is correct: its change-detection role always lived in the untouched `test_no_dead_modules`.**
- **Rationale**: The frozenset is the actual change-detector — adding an `m_*.py` forces the author to *name* it, distinguishing "expected auto-discovered migration" from "accidentally-orphaned real module." Deriving its *contents* would make `test_no_dead_modules` a tautology (Edge Case "Frozenset vacuity"). The **count** is pure double-charge (equals `len(frozenset)`); deriving it moves the expected in lockstep with the frozenset add — satisfying SC-001 (zero count-baseline edits; the frozenset acknowledgment is the only edit).
- **Alternatives rejected**: convert/derive the frozenset (vacuous, out of scope); keep both manual (status-quo double-charge); delete the count key entirely (loses the audit surface + reverse-containment registration — prefer derive over delete for continuity with `_REQUIRED_NO_DEAD_MODULES_CATEGORIES`).

## Decision 3 — FR-002: refresh match-identity strategy

- **Decision**: The helper iterates **existing allowlist entries only** (never the live dead-set) and rewrites hashes in place — it never appends. Per entry `E`: recover identity-minus-hash (`bare_name` always; `module_path` from `E.module_path` for collision-tier, or from the `# <module>::<Name>` provenance comment for content-tier — as a **fail-closed hint only**, never for hashing). Candidate set = live `__all__` locations with matching `bare_name`. **[Post-plan correction] The still-dead authority is `_compute_offenders(..., allowlist=frozenset())` + `_resolve_final_key` (in `test_no_dead_symbols.py`), NOT "`classify_collisions` filtered to still-dead" — `classify_collisions` returns all live locations and has no deadness notion.** Resolve candidates through that authority, filter to still-dead, then to `E`'s recovered `module_path`. **Refresh iff exactly one still-dead candidate; else fail closed** (0 → dangling, leave red; ≥2 → `bare_name` ambiguity, refuse). **Unrecoverable/ambiguous `module_path` ⇒ refuse — never fall back to a bare-name-only corpus-wide match (that path silently admits a new dead symbol).** Preserve the entry's tier on refresh (a collision-tier entry keeps `module_path`).
- **Confirmed separations**: "refresh still-dead" vs "admit new dead symbol" is *structural* — the loop only rewrites existing entries, so a new dead symbol (no entry) cannot be admitted regardless of the location-free key. **US1-AC2**: `X::Foo` dangling + new `Y::Foo` dead → `E`'s `module_path=X`, only still-dead `Foo` at `Y≠X` → 0 candidates → refuse; `Y::Foo` never admitted, gate reds. **Body-edited-AND-gained-a-caller**: **[Post-plan correction] a body edit changes the content key so `_compute_stale` does not match — the gate emits a `dangling` finding, NOT `stale`.** Pure gained-a-caller (body unchanged) → `stale`; gained-a-caller **plus** body edit → `dangling`. Either way not refreshed. An AC3 fixture must assert the correct finding type per variant.
- **Rationale**: Across a body edit the hash is useless and the content-tier key is location-free, so `module_path` is the *only* discriminator for AC2; recovering it is non-negotiable. Fail-closed makes the worst case a refused legitimate refresh (safe), never a silent wrong admit.
- **Alternatives rejected**: match content-tier by unique corpus-wide `bare_name` ignoring `module_path` (**fails AC2**); derive domain from the live dead-set (the admit path FR-002 forbids); trust the provenance comment as contract (keep it a fail-closed hint).

## Decision 4 — `_baselines.yaml` merge-coupling / lane allocation

- **Decision**: **Co-locate FR-003/FR-004/FR-005/FR-006 on one "baseline-file" lane, sequenced internally**; keep FR-001/FR-002/NFR-001 (the helper) on a **separate parallel lane** (file-disjoint).
- **Rationale**: FR-003/04/05/06 all mutate `test_ratchet_baselines.py` and three mutate `_baselines.yaml` — no logical conflict but guaranteed textual collisions; parallel worktrees would three-way-collide on merge (a known repo footgun). The helper lane touches only `test_no_dead_symbols.py` + the new module — fully parallel, no collision.
- **Alternatives rejected**: one WP per FR across four lanes (3–4-way merge conflicts); everything on one lane (needlessly serializes the file-disjoint helper).

## Decision 5 — NFR-002 measurement unit

- **Decision**: **per-test-call, warm**, each `fast`-marked call < 1 s (verified 0.32 s / 0.52 s). One-time per-module setup (~0.43 s, sibling-gate imports) is not counted per-call. Apply `fast` at module level (`pytestmark`).
- **Corpus-walk confirmation**: `test_ratchet_baselines.py` imports `test_example_round_trip` only inside `_import_module_attr` (execution-time, deferred) — `-m fast` *collection* never touches it; at execution it costs 0.147 s warm and adds no new heavy dependency (`pydantic`/`yaml`/`specify_cli` already transitively imported via sibling gates). Module-level fast-marking honors NFR-002.
- **Alternatives rejected**: per-file wall-clock (conflates one-time import with per-test cost); marking only pure-logic tests (excludes the very baseline-red detector US5 exists to surface locally).

## WP decomposition (guidance for /spec-kitty.tasks)

- **Lane 1 (parallel, file-disjoint)** — split per post-plan feasibility (WP01 was oversized):
  - **WP01a — provenance normalization (mechanical, big diff, isolate for review)**: normalize every content-tier allowlist entry to a canonical trailing `# module::Name` (handle all 3 live formats: trailing `::Name`, preceding-line, `# mod`-only) + a test asserting every content-tier entry carries a parseable comment. Deps: none.
  - **WP01b — refresh helper + fail-closed match + NFR-001 regression**: pure core `refresh(corpus, decls, per_symbol, allowlist_source) -> rewritten_source` (injected corpus); reuse `_compute_offenders(..., frozenset())` + `_resolve_final_key` as the still-dead/hash authority; fail-closed match (Decision 3) incl. **unrecoverable-⇒-refuse**; tier-preserving rewrite via `tokenize`. **The non-fakeable NFR-001/SC-006 regression must, in one run:** (a) a body-edited still-dead `X` **is** refreshed (positive control proving the admit branch ran); (b) a new still-dead `Y::Foo` (same `bare_name`, different module) is present, **not** admitted, gate REDs on `Y`; (c) assert `E`'s candidate set held ≥2 `bare_name` matches narrowed to exactly `{X}`; (d) all four Contract-A refuse branches (incl. 0-candidate dangling) exercised by *running* the helper. Deps: WP01a (needs normalized comments).
- **Lane 2 (sequential internally) — WP02** FR-004: derive `category_1` as `len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` in **both** the growth (`:269`) and shrinkage-warns (`:405`) arms + a monkeypatch-the-frozenset derivation test (not `assert 100==100`) + optional decorative-YAML honesty assert. → **WP03** FR-003: remove `_SKIP_MARKED_BLOCKS` from **both** `single_baselines` lists (`:307` + `:441`); dedicated non-failing `fast`-tier test that **asserts the `record_property` growth record fires** (write-only channel otherwise); NFR-003 assertion that `legacy_contract_allowlist=151` stays a growth-fail. → **WP04** FR-005 (delete inert block + drain `_GRANDFATHERED_UNREGISTERED_KEYS`→`frozenset()` + coupled literal at `:530` + retire stale RL-030 prose) + FR-006 (fast markers + **verify the `arch-adversarial` `-m` selector does not exclude `fast`** + a `-m fast` collection import-hygiene test). Deps: internal WP02→WP03→WP04.
- **Cross-lane**: none.

## Supply-chain / adversarial evidence

- **Dependency change: NONE** (dependency-hygiene). Every mechanism reuses in-repo surfaces (`_symbol_key` resolver/classifier, `ast`/`hashlib`, `record_property`, the already-registered `fast` marker). No new CI job, no external service. If any implementer reaches for a new hashing/parsing library, that is a design violation. Supply-chain safety section: **not triggered** (no add/upgrade/remove).
- **Adversarial evidence**: a 4-lens post-spec squad (architect/renata/debbie/priti) already challenged the spec; all convergent findings were **accepted** and folded into the revised spec (`bec7013`). No contested finding was dropped. This plan's design decisions were produced under that hardened contract.

## Risks to escalate

1. **(highest) Provenance-comment reliability** — content-tier `module_path` recovery depends on inconsistently-placed `# <module>::<Name>` comments. WP01 should normalize to a single trailing form and assert every content-tier entry carries a parseable comment, else legitimate refreshes silently degrade to "refuse."
2. **7 content-tier duplicate `bare_name`s** are permanently un-refreshable-by-name unless a comment disambiguates; if any pair shares the same `module::Name`, escalate that entry to collision-tier by hand. Caps helper coverage; fail-closed keeps it safe.
3. **NFR-003 surgical-extraction** — FR-003/FR-005 edit near the load-bearing `legacy_contract_allowlist=151`; the WP03 NFR-003 assertion mitigates.

## Post-plan squad fold (adversarial evidence, 2026-08-18)

A 4-lens post-plan squad (python-pedro / paula-patterns / debugger-debbie / reviewer-renata) challenged this design against the real code. Verdict: **design survives contact; no architectural blocker** — every mechanism is reachable, lanes are code-disjoint, load-bearing siblings are surgically separable, and FR-002's iterate-existing-only core structurally cannot admit a new dead symbol. All contested findings were **accepted and folded** (dispositions below); one root-cause item **deferred with rationale**. No finding was dropped.

| Finding (lens) | Disposition |
|---|---|
| FR-004 authority = `len(frozenset)`, not a re-globbed predicate (unanimous: pedro/paula/renata) | **accepted** — Contract C + Decision 2 corrected; both arms (`:269`/`:405`) |
| FR-004 no run-the-derivation test → tautology risk (renata HIGH) | **accepted** — monkeypatch-frozenset derivation test mandated |
| Provenance comment has 3 formats; unrecoverable-⇒-refuse unpinned; silent bare-name-only admit path (debbie HIGH, paula/pedro) | **accepted** — Contract A-norm mandatory; refuse-row pinned; parser handles 3 formats |
| NFR-001/SC-006 regression F1-vacuous without a positive control (renata + debbie HIGH) | **accepted** — WP01b regression strengthened (positive control + ≥2→{X} assertion) |
| FR-002 still-dead authority is `_compute_offenders(..., frozenset())`, not `classify_collisions` (pedro/debbie) | **accepted** — Contract A + Decision 3 corrected |
| `record_property` is write-only in this repo (`grep user_properties` empty) (renata + debbie) | **accepted** — Contract B mandates an emitted-property assertion |
| FR-003 dual-list (`:307`+`:441`) and FR-004 dual-arm (`:269`+`:405`) (pedro/paula) | **accepted** — both pinned |
| `research.md:35` stale→dangling mislabel (debbie) | **accepted** — corrected inline |
| FR-006 CI-routing blast radius (dual-mark could drop tests from arch job) (pedro NEW) | **accepted** — WP04 selector-verification pinned |
| WP01 oversized (pedro) | **accepted** — split into WP01a (normalization) + WP01b (helper) |
| Refresh must preserve entry tier (debbie) | **accepted** — Contract A invariant |
| **Root-cause: replace comment-parsing with an optional non-hashing `source_module` field on `SymbolKey`** (paula) | **deferred with rationale** — out of scope for this toll-reduction release; the fail-closed helper makes comment fragility cost only *coverage*, never *safety*. File as a follow-on architecture issue. Non-goals: do not escalate content-tier entries to collision-tier; do not let the field enter `body_hash`/`key_tier` (preserves relocation-tolerance). |

**Deferred follow-on (filed [#3552](https://github.com/Priivacy-ai/spec-kitty/issues/3552))**: "Optional non-hashing `source_module` provenance field on `SymbolKey` — stable machine identity for dead-symbol refresh without forfeiting relocation-tolerance" (root fix for the provenance-comment fragility; this mission ships the fail-closed helper instead).

Convergences confirmed by ≥2 independent lenses: FR-004 authority (3 lenses), provenance-comment (3), regression non-vacuity (2), `record_property` write-only (2). The lane-disjointness, single-hashing-authority seam, and `:530` coupled-literal catch were independently **conceded sound** by the lenses that checked them.
