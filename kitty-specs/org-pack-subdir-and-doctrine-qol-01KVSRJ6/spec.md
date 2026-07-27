# Mission Specification: Org-Pack Subdir Source & Doctrine QoL

**Mission ID**: 01KVSRJ628XHMZQTXPBC567R2X
**Slug**: org-pack-subdir-and-doctrine-qol-01KVSRJ6
**Created**: 2026-06-23
**Type**: software-dev
**Target branch**: feat/doctrine-qol-2083

## Purpose (stakeholder-facing)

**TL;DR**: Let git-sourced doctrine packs live in a subdirectory, stop the governance layer from silently dropping doctrine, clarify which YAML library to use, and give tiered (core-vs-glue) coding standards a canonical home in doctrine.

Teams that ship a doctrine pack inside a larger repository (alongside tools, docs, CI) currently cannot consume that pack directly from its git source: the git source clones the **repo root** and there is no way to say "the pack actually lives in `pack/`". Separately, the governance layer silently filters out doctrine artifacts that try to declare "applies to all languages", reporting them as missing with no authoring-time signal. This mission fixes both reliability gaps and bundles two adjacent doctrine-stack quality improvements so the governance surface is easier to operate and reason about.

> **This spec was revised after a post-spec adversarial squad** (see `research/post-spec-squad-findings.md`). The squad falsified the original "single resolution seam" claim and surfaced fakeable doctrine deliverables; the requirements below reflect the corrected design.

## Scope Threads

- **Thread A — #2083 (driver, P1 bug)**: org-pack `source_type: git` cannot consume a pack in a subdirectory.
- **Thread B — #707 (docs)**: clarify ruamel.yaml vs PyYAML usage in charter/doctrine docs.
- **Thread C — #1843 (P2, bounded doctrine-only slice)**: codify tiered coding standards by domain importance in doctrine. *Enforcement (CI gates, agent-effort routing) is explicitly deferred to epic #1843.*
- **Thread D — #2092 (P1 bug)**: doctrine catalog silently drops artifacts declaring `applies_to_languages: [any]` / `[all]` (treated as literal language tokens). Fail loud at authoring time.

**Deliberately NOT folded**: #2080 (daphne-led DRG/doctrine audit epic — its deliverable is a remediation plan; it is a separate curator-owned mission). The Thread-C orphan-styleguide finding from the squad is recorded as input to that future mission.

## User Scenarios & Testing

### Scenario A1 — Consume a pack that lives in a subdirectory (primary, #2083)

- **Primary actor**: An operator configuring `.kittify/config.yaml` for a project that pulls an org doctrine pack from a monorepo.
- **Trigger**: The operator declares a git-sourced org pack whose `org-charter.yaml` is at `pack/org-charter.yaml` and sets `subdir: pack`.
- **Happy path**: `spec-kitty doctrine fetch` clones the repo into the cache location and reports the artifact count **from the effective root** (`<cache>/pack`); `spec-kitty doctor doctrine` loads the pack's DRG fragment and org-charter from `<cache>/pack` and reports the pack healthy.
- **Exception (wrong subdir)**: The operator sets `subdir: wrong/`. `doctrine fetch` reports **zero artifacts at the effective root** (actionable signal at fetch time), and `doctor doctrine` reports the pack unhealthy with a structured reason.
- **Exception (escape)**: The operator sets a subdir that escapes the cache location (absolute path or `../`). The system refuses at config-load with a **structured, operator-visible error** (not a swallowed warning that degrades to "no org packs").

### Scenario A2 — Existing configs keep working (regression, #2083)

- **Trigger**: An operator with an existing org-pack config that has **no** `subdir` runs any doctrine command.
- **Happy path**: The effective pack root equals the (repo-root-normalized) `local_path` — identical to pre-change behavior across every consumer.

### Scenario B1 — Choosing a YAML library (#707)

- **Primary actor**: A developer adding a YAML read/write path in the doctrine/charter stack.
- **Trigger**: They must decide between the round-trip library (ruamel.yaml) and the plain loader (PyYAML).
- **Happy path**: They open the docs, find a rule that names the deciding criterion AND honestly flags the known mixed-usage sites, and proceed without reading source.

### Scenario C1 — Finding the tiered-standards rule (#1843)

- **Primary actor**: A developer/agent about to modify code, unsure how much rigour applies.
- **Trigger**: They want the expected coverage/duplication/smell/lint/typing bar for the tier of code they touch.
- **Happy path**: They locate one canonical, DRG-resolvable doctrine styleguide naming the tiers (core vs glue) mapped to concrete existing code areas, with a per-tier rigour table.

### Scenario D1 — Authoring an always-applicable doctrine artifact (#2092)

- **Primary actor**: A doctrine author writing a directive/tactic/styleguide that should apply to all languages.
- **Trigger**: They write `applies_to_languages: [any]` (a natural way to say "all").
- **Happy path**: `spec-kitty doctrine validate` **fails loud** with an actionable message ("omit the field to mean always-applicable; `any`/`all` are not language tokens"), so the artifact is never silently scope-filtered at runtime.
- **Diagnostic path**: If a scope-filtered artifact is referenced, the `MISSING_ARTIFACT` diagnostic names "present but scope-filtered" rather than implying the file is absent.

## Requirements

### Functional Requirements

| ID | Requirement | Thread | Status |
|----|-------------|--------|--------|
| FR-001 | A single canonical **effective pack root** is computed at the `OrgPackConfig`/registry level (e.g. an `effective_root(repo_root)` property/helper) that (a) normalizes `local_path` relative to the repository root and (b) joins the optional `subdir`. This is the one seam all consumers use. | A #2083 | Planned |
| FR-002 | When no `subdir` is declared, the effective root equals the repo-root-normalized `local_path` (full backward compatibility across every consumer). | A #2083 | Planned |
| FR-003 | `subdir` is validated as a relative path **contained within** the effective `local_path`, using the existing `ensure_within_directory()` helper. String-level escapes (absolute paths incl. Windows/UNC, any `..` component) are rejected at config-load with a **structured, operator-visible error**; the error must NOT be swallowed by the registry's warning-and-degrade path. `.`/empty are normalized to "no subdir". | A #2083 | Planned |
| FR-004 | Every consumer that reads a pack root consumes the effective root, so a subdir-rooted pack loads everywhere — **specifically including** the `doctor doctrine` health path (`load_org_drg` → `load_org_pack`), the charter DRG load (`charter/drg.py`), `PackContext` (`charter/pack_context.py`), org-charter policy load (`doctrine/org_charter.py`), the doctor pack-health renderer (`doctor.py` `_build_pack_entries`), charter context (`charter/context.py`), and the org-layer lint (`charter_runtime/lint/checks/org_layer.py`). No consumer may re-derive the root from raw `local_path`. | A #2083 | Planned |
| FR-005 | Persisting the pack registry round-trips `subdir` through **both** the canonical `doctrine.org.packs[]` shape (`_pack_to_yaml_dict`) and the legacy inline single-pack shape; absence emits **no** `subdir:` key. | A #2083 | Planned |
| FR-006 | The legacy inline single-pack config shape (`doctrine.org` with inline `local_path`, via `_build_legacy_single_pack`) reads and honors a declared `subdir`. | A #2083 | Planned |
| FR-007 | `spec-kitty doctrine fetch` reports the artifact count at the **effective root** (not the clone root), so a wrong/empty `subdir` surfaces as "0 artifacts" at fetch time rather than only failing later at `doctor doctrine`. | A #2083 | Planned |
| FR-008 | The org-pack config-schema contract (`kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml`, `additionalProperties: false`) is updated to include the `subdir` field so the documented contract matches behavior. | A #2083 | Planned |
| FR-009 | Charter/doctrine documentation states the rule for choosing between ruamel.yaml (round-trip: comment/quote/format preservation, frontmatter) and PyYAML (read-only simple data). The doc **declares whether it is current-true or aspirational**, is verified against ≥3 named call sites, and explicitly names the known mixed-usage sites (e.g. `config.yaml` read both ways) rather than implying a clean invariant that does not exist. | B #707 | Planned |
| FR-010 | Doctrine contains one canonical **styleguide** artifact defining domain-importance tiers (core vs glue) mapped to **named, currently-existing** `src/` areas, with a per-tier rigour table covering coverage, duplication, smell, lint, and typing expectations. | C #1843 | Planned |
| FR-011 | The tiered-standards styleguide is registered in the doctrine DRG via the graph generator AND is **non-orphan**: at least one inbound DRG edge from a resolvable consumer (a `suggests`/`requires` edge from a directive/paradigm — doctrine-only, no CI/agent-effort change). A test asserts non-orphan status. | C #1843 | Planned |
| FR-012 | `spec-kitty doctrine validate` rejects `applies_to_languages: [any]` / `[all]` with an actionable message ("omit the field to mean always-applicable; `any`/`all` are not language tokens"), failing loud at authoring time so such artifacts are never silently scope-filtered at query time. | D #2092 | Planned |
| FR-013 | The `MISSING_ARTIFACT` diagnostic (`charter/context.py`) gains a "present-but-scope-filtered" branch so a scope-filtered artifact is named as such rather than implying the file is absent or malformed. | D #2092 | Planned |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Subdir support is behavior-additive: configs without a `subdir` resolve identically to pre-change behavior. | All pre-existing org-pack tests pass unchanged; a no-subdir config resolves to exactly the repo-root-normalized `local_path` in a regression test across the FR-004 consumer set. | Planned |
| NFR-002 | Path-escape inputs are rejected; the check is applied at the correct lifecycle stage. | String escapes (absolute incl. Windows/UNC, `..`) rejected at config-load with a structured error (100% of a curated set); symlink-escape — if in scope — is checked at effective-root **resolution** time against the realpath of `local_path` (validation cannot see a not-yet-cloned symlink); 0 inputs resolve outside `local_path`. | Planned |
| NFR-003 | New and changed code meets the repo quality bar. | `ruff` and `mypy` report zero issues; cyclomatic complexity ≤ 15 on touched functions; every new branch/helper has a focused test in the same change. | Planned |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | #1843 is a **doctrine-only** slice: no CI gate changes and no agent-effort routing. Enforcement is deferred to epic #1843. | Accepted |
| C-002 | Canonical field name is `subdir`; do **not** introduce a `pack_path` alias (Terminology Canon). Add a glossary disambiguation note: the org-pack `subdir` field is distinct from the resolver's existing `subdir` parameter (`resolver.py`). | Accepted |
| C-003 | Behavior-additive for Thread A: `GitSource` still clones the repo root into the cache location; `subdir` affects **resolution**, not the clone target. Sparse-checkout is out of scope. | Accepted |
| C-004 | The doctrine DRG `graph.yaml` is generated and freshness-tested; the new styleguide must be registered via the generator (`spec-kitty doctrine regenerate-graph`), not by hand-editing. | Accepted |
| C-005 | `OrgPackConfig` uses `extra="forbid"`; the `subdir` field must be added to the model or configs declaring it break. | Accepted |
| C-006 | #2092 is fixed as a **validate-time fail-loud guard** (preferred over silent query-time wildcard filtering), so authors see the error where they write it. | Accepted |
| C-007 | The effective-root seam (FR-001) must **retire**, not duplicate, the pre-existing inconsistency where `resolve_org_roots` returns raw `local_path` while other readers resolve relative-to-repo_root. Normalization happens once, at the seam. | Accepted |

## Success Criteria

- **SC-001**: An integration test fetches/resolves a fixture git-sourced pack whose root (`org-charter.yaml` + `drg/fragment.yaml`) is under `pack/`, and asserts `doctor doctrine` reports it **healthy** — exercising the real `load_org_drg` health path, not just a path-join unit.
- **SC-002**: Existing org-pack configurations (no `subdir`) resolve and validate identically — zero regressions across the FR-004 consumer set.
- **SC-003**: An operator who sets a wrong/empty `subdir` gets an actionable signal at `doctrine fetch` time (0 artifacts at effective root), not only a later `doctor` failure.
- **SC-004**: A developer can determine which YAML library to use from the docs alone; the documented rule is verifiable against ≥3 named call sites and honestly names the mixed-usage sites.
- **SC-005**: The tiered-standards styleguide is DRG-resolvable (non-orphan, asserted by a test) and its tier table maps to named existing `src/` areas — not an inert stub.
- **SC-006**: Authoring `applies_to_languages: [any]` fails at `spec-kitty doctrine validate` with an actionable message; no load-bearing artifact is silently dropped at query time.

## Key Entities

- **Org Pack Config** — declared pack entry: `name`, `local_path`, `source_type`, `url`, `ref`, + new optional `subdir`.
- **Effective Pack Root** — the canonical path all consumers treat as the pack root: repo-root-normalized `local_path` joined with `subdir` when present.
- **Tiered-Standards Styleguide** — a DRG-registered, non-orphan doctrine styleguide defining domain-importance tiers + per-tier rigour, mapped to named code areas.
- **Language Scope** — `applies_to_languages`; omission = always-applicable; `any`/`all` are rejected tokens (Thread D).

## Assumptions

- `subdir` is a relative POSIX-style path beneath the effective `local_path`; empty/absent/`.` means "pack root is `local_path`".
- Sparse-checkout of the subdirectory is a future optimization, not required for correctness (full clone retained).
- Thread B (#707) is documentation-only — no library swap, no code behavior change.
- Thread C (#1843) produces doctrine content + one DRG edge only — no runtime code, CI, or agent-routing change.
- The mission is executed entirely in the dedicated clone; the live/global CLI remains linked to the primary checkout (recorded for traceability).

## Out of Scope

- CI per-tier enforcement gates and agent-effort routing for tiered standards (epic #1843).
- The full daphne-led DRG/doctrine audit + remediation plan (#2080) — separate mission.
- Sparse-checkout / partial-clone optimization for git sources.
- Automated migration of existing pack configs.
- Changing `https`/`api` fetch semantics (the effective-root resolution applies uniformly; fetch transport is untouched).

## Traceability

| Issue | Thread | Disposition |
|-------|--------|-------------|
| #2083 | A | Driver — fully addressed (effective-root seam + all-consumer resolution + validation + round-trip + fetch reporting + contract update). |
| #707 | B | Docs clarification — fully addressed (honest current-vs-aspirational rule). |
| #1843 | C | Bounded doctrine-only slice (non-orphan styleguide + 1 DRG edge); CI/agent-effort deferred to epic. |
| #2092 | D | Fully addressed (validate-time guard + diagnostic). |
| #2080 | — | **Follow-up mission** (daphne-led audit epic); Thread-C orphan finding recorded as input. |
| #1799 | epic | Governance (Charter & Doctrine) parent epic for #707/#1843. |
