# Data Model: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 1 output** of `/spec-kitty.plan` · **Date**: 2026-08-21

This mission is docs-only (C-001): there are no runtime entities, databases, or API models. The "data model" here is the **artifact schema** — the entities that must be well-defined so the four deliverables interlock and downstream missions can consume them mechanically:

1. **Surface category** — the fixed taxonomy of user-facing surface classes (FR-006).
2. **Occurrence class (OC-##)** — the stable, trackable unit of work: a set of occurrences in one surface category matching defined path patterns (FR-007).
3. **Stacked mission** — one downstream spec-kitty mission retiring a set of occurrence classes (FR-009).
4. **Inventory artifact** — the named audit record tying every tracked-file hit to an occurrence class or a classification-out (NFR-001).
5. **Stack-level invariant** — the state that must hold after each stack level (FR-008).

---

## 1. Surface category (fixed taxonomy)

Nine categories, fixed by this plan; the inventory assigns every in-scope hit to exactly one. (Categories are *surface* classes, not file types — a single file can contribute to several.)

| ID | Category | What it covers (evidence at base) | Verification mechanism (C-004 assignment) |
|----|----------|-----------------------------------|-------------------------------------------|
| S1 | `cli-executable` | `spec-kitty doctrine` group (8 subcommands), `spec-kitty doctor doctrine`; help text, errors, emitted output | Guard (scan roots) + per-subcommand alias tests (M2) |
| S2 | `docs-glossary` | `docs/context/doctrine.md` (685 lines / 124 doctrine lines) + cross-references | Guard (scan roots) — file leaves baseline at zero |
| S3 | `docs-prose` | Remaining `docs/` prose (430 files contain the term; ADRs excluded as legacy) | Guard (scan roots) — file leaves baseline at zero |
| S4 | `prompts-skills-agent-artifacts` | Skills at `src/doctrine/skills/` (55 dirs, 7 `spk-doctrine-*`), generated agent dirs (`.claude/`, `.agents/skills/`, …), `.github/prompts/spec-kitty-standalone.md` | Mixed-root (see note below): in-root `src/doctrine/skills/` → guard baseline; out-of-root `.github/prompts/` → NFR-001 audit + migration/upgrade flow for generated copies |
| S5 | `charter-bundle` | `.kittify/charter/` — `charter.yaml` (53 lines), `charter.md` (13), `graph.yml` (2), `interview/answers.yaml` (9) | NFR-001 audit + bundle regeneration check (`charter sync`) |
| S6 | `packs-source` | `packs/built-in/` — canonical YAML source for all artifact kinds (103 files contain the term) | NFR-001 audit + upgrade-flow verification (agent copies derive from packs) |
| S7 | `generated-output` | Runtime-emitted strings: "Action Doctrine" heading (`src/charter/context_renderers/bootstrap_text.py`), pack paths in `charter context` output, `scripts/generate_schemas.py:548` | Mixed-root (see note below): in-root source strings → guard; out-of-root `scripts/` + emitted text → NFR-001 audit |
| S8 | `scripted-consumers` | `.github/workflows/ci-quality.yml:4055` (`doctor doctrine --json` + assertion), 3 workflow filenames, `uses:` references | NFR-001 audit + same-wave CI update requirement (hard) |
| S9 | `root-docs` | Root-level operator docs: `AGENTS.md` (10 doctrine lines, case-insensitive), `README.md`, `CONTRIBUTING.md` | NFR-001 audit (outside guard roots) |

**Mixed-root classes (S4, S7)**: these span both sides of the guard's scan roots (`src`, `tests`, `docs`). The in-root portion is verified by the guard itself (frozen baseline at arming, shrinks to zero); only the out-of-root portion needs a C-004 named mechanism — S4: `.github/prompts/` (NFR-001 audit) + generated agent copies (migration/upgrade flow); S7: `scripts/` source strings and emitted text (NFR-001 audit).

**Classification-out categories** (not surface classes — recorded in the inventory as classified out, with reason):

| ID | Category | Rule |
|----|----------|------|
| X1 | `internal-identifier` | Code identifiers: the `src/doctrine/` package, module names, import paths, variable/function/class names (C-005). String-level rule: user-facing *strings* inside `src/` are in scope (S1/S7); identifiers are not. |
| X2 | `legacy-marked-historical` | ADR titles/bodies (10 in `docs/adr/3.x/`, except the amended one), archived missions, `kitty-specs/` snapshots, `kitty-ops/` Op event journals (15 files contain the term as quoted event content) (C-003). Immutable; explicitly marked legacy. |
| X3 | `quoted-data` | Glossary-pack data at `src/doctrine/glossary_packs/built-in/` (documents deprecated terms as data; already guard-exempt). |

## 2. Occurrence class (OC-##)

The stable unit of work, trackable inventory → mission → completion.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `OC-##` (stable, assigned at inventory time) | Never reused; downstream missions cite IDs, not descriptions |
| `surface_category` | S1..S9 (exactly one) | From the fixed taxonomy above |
| `path_patterns` | list of glob/path patterns | What the audit matches; e.g. `packs/built-in/directives/*.yaml` |
| `occurrence_count` | int (line-based, at base commit) | From the mechanical audit; re-baselined per wave |
| `representative_examples` | ≤ 3 quoted lines with file:line | Evidence, not the full list (the audit record holds that) |
| `classification` | `in-scope` \| `internal-identifier (X1)` \| `legacy-marked-historical (X2)` \| `quoted-data (X3)` | Every audit hit lands in exactly one; 0 unclassified is the pass condition (SC-002) |
| `operator_typed` | bool | True if operators/harnesses type this identifier (profile IDs, directive IDs, skill names) — the ADR's classification decision applies |
| `assigned_mission` | mission slug \| `deferred:<milestone>` | Exactly one assignment or an explicit deferral with rationale (SC-003) |

**Invariants**:
- **OC-I1 (exhaustiveness)**: every tracked-file hit from the mechanical audit belongs to exactly one OC-## or a classification-out category. No silent drops (NFR-001).
- **OC-I2 (stability)**: OC IDs are immutable once published; waves may *split* a class (new child IDs) but never reassign an ID's meaning.
- **OC-I3 (string-level scope)**: classification is decided per occurrence string, not per file path — user-facing artifacts inside `src/doctrine/` (skills) are in scope; identifiers anywhere are out (R7).

## 3. Stacked mission

One downstream spec-kitty mission retiring a set of occurrence classes.

| Field | Type | Notes |
|-------|------|-------|
| `slug` | kebab slug (proposed in this plan; finalized in `stacked-plan.md`) | M1 `charter-authority-flip`, M2 `charter-cli-surface`, M3 `charter-packs-source`, M4 `charter-skills-artifacts`, M5 `charter-docs-prose`, M6 `charter-removal-audit` (deferred to 4.0) |
| `purpose` | one line | What flips, in operator terms |
| `inputs` | list of artifacts from this mission (ADR / inventory classes / methodology invariants) | FR-010: M1's inputs must be fully determined here — 0 new decisions |
| `outputs` | list of flipped surfaces + verification evidence | What the next mission can rely on (invariant I2..I6) |
| `depends_on` | prior mission slugs (stack order M1→M5; M6 after 4.0 milestone) | Explicit, no implicit ordering |
| `retires` | list of OC-## IDs | Union over M1..M6 = all in-scope classes (SC-003) |
| `change_mode` | `bulk_edit` for M1–M5 (each with its own scoped `occurrence_map.yaml`, 8 categories); M1's map covers the glossary + bundle renames — its guard-arming WP is additive code, not a rename occurrence; M6 is removal | R9: rename waves are bulk-edit missions by definition |
| `invariant_after` | I1..I6 (from §5) | The state that must hold when the mission merges |

**Invariants**:
- **SM-I1 (single assignment)**: every in-scope OC-## is retired by exactly one mission or explicitly deferred with rationale (SC-003).
- **SM-I2 (spec-readiness of M1)**: M1 can be specified from this mission's artifacts alone — ADR (vocabulary + canon line content), inventory (S2/S5 classes with counts and examples), methodology (atomic-flip design + guard baseline spec) — with 0 new operator decisions (FR-010/SC-004).
- **SM-I3 (same-wave consumers)**: any mission retiring an S1/S8 class updates its scripted CI consumers in the same PR (C5).

## 4. Inventory artifact (`inventory.md`)

The named audit record (NFR-001). Schema contract: `contracts/inventory-schema.md`.

Structure:
- **Frontmatter**: `base_commit` (SHA), `date`, `audit_command` (the exact mechanical procedure — case-insensitive search over all tracked files excluding `.git`, worktrees, vendor dirs), `total_hits`.
- **Raw audit record**: per-file hit counts (the mechanical output — evidence before conclusion, ATDD-first analog).
- **Class table**: one row per OC-## (fields from §2) + classification-out rows (X1/X2/X3 with counts and the rule applied).
- **Completeness statement**: `total_hits = sum(class rows) + sum(classification-out rows)` — the arithmetic check that 0 hits are unclassified (SC-002).
- **Out-of-repo surfaces** (spec assumption 5): known sibling-repo user-facing surfaces (e.g. spec-kitty-saas dashboard) recorded as deferred with rationale — outside the audit arithmetic (out-of-repo, not unclassified).

**Invariant INV-I1**: the inventory is a **per-wave snapshot**, not one-time — each wave re-runs the audit at its base and records drift (expected: concurrent catfooding missions add `kitty-specs/` hits, which self-classify as X2 at merge).

## 5. Stack-level invariants (FR-008)

The state that must hold at each level of the stack — the methodology's core content:

| Level | State (must hold when true) |
|-------|------------------------------|
| **I0** — pre-M1 (status quo) | Zero terminology friction for concurrent missions: guard does not forbid "doctrine"; old vocabulary canonical everywhere; no half-renamed surface exists. |
| **I1** — post-M1 (authority flip) | New vocabulary canonical in glossary + charter bundle; Terminology Canon line loads at every session start (self-correcting lever); guard armed with file-level frozen baseline (shrink-only + self-mutation test); new `src/tests/docs` content outside the baseline containing "doctrine" fails CI; `kitty-specs/` drift expected and re-baselined per wave. |
| **I2** — post-M2 (CLI) | `spec-kitty doctrine` subcommands are hidden aliases with deprecation warnings; canonical names work; per-subcommand alias tests green; CI consumers (`ci-quality.yml:4055`, workflow filenames) updated same-wave. |
| **I3** — post-M3 (packs) | `packs/built-in/` user-facing strings/titles use the new vocabulary; agent copies regenerate via upgrade flow from packs (no hand-edited generated dirs). |
| **I4** — post-M4 (skills) | `spk-doctrine-*` renamed with legacy alias skills during the window; old→new map recorded in M4's artifacts (alias skills are its executable form); harness routing works on both names until 4.0; generated agent dirs updated via migration/upgrade flow. |
| **I5** — post-M5 (docs prose) | `docs/` prose + root docs use the new vocabulary; ADR titles/bodies remain legacy-marked (C-003); guard baseline for `docs/` at or near zero. |
| **I6** — 4.0 end state (post-M6) | Aliases removed; NFR-001 audit finds **zero** user-visible "doctrine" outside X2 (legacy-marked) + X1 (internal identifiers); the 4.0 hard rule verified by audit, not assumption. |

**Invariant INV-I2 (no conflict window)**: at no point between I0 and I6 may a surface exist where the old word is forbidden *and* the replacement term is not yet canonical (C1) — this is what makes M1 atomic.
