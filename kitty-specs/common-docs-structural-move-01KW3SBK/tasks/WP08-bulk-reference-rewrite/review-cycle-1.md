# WP08 Review — Cycle 1 (reviewer-renata)

**Verdict: CHANGES REQUESTED.** The tool, completeness teeth, forbidden-surface
discipline, and targeted-ref-updates are all excellent. One blocking defect: the
rewrite routed era-deduped ADRs to the **wrong era subdirectory**, turning 11
previously-working ADR cross-references into dead links — and the completeness
grep was structurally blind to it.

---

## ✅ What passed

1. **Tool is occurrence-map-driven + correct.** `bulk_ref_rewrite.py` reads
   `moves:` as the substitution table, enforces `do_not_change`
   (`kitty-specs/`, `docs/1x|2x/`, `docs/adr/`, `docs/changelog/`, serialized
   basenames, frontmatter split, inventory lockfile), is idempotent via the
   `(?<!docs/)` lookbehind, and dry-run-able. 16 tool tests green; all 4
   mandated cases present and non-synthetic (drive real `run()`).
2. **Forbidden surfaces untouched** (WP08-only range `6e65bff84..HEAD`):
   `kitty-specs/` = **0 files**, `docs/adr/` = **0 files**, `architecture/**/adr`
   bodies = **0 files**. C-002 held.
3. **Targeted-ref-updates:** `ci-quality.yml` markdown-consistency glob
   re-pointed onto `docs/**/*.md` and **still fires** (not silent-dead) —
   invokes `test_architecture_docs_consistency.py` + `test_versioned_docs_integrity.py`,
   both present. Glossary refs re-pointed to the **real** landed
   `docs/architecture/04_implementation_mapping/code-patterns.md` (the prompt's
   flatter hint was wrong; the tool correctly resolved the on-disk path).
   CHANGELOG root alias intact (0 changes to root `CHANGELOG.md`).
4. **Dual-read drop (T046)** is the authorized change: `compat/registry.py`
   removed the legacy `architecture/2.x/shim-registry.yaml` fallback, canonical
   `docs/migrations/` only. `test_runtime_read_resolution.py` green (15).
5. **manual_review src/cli files are doc-path-strings only** — sampled
   `upgrade.py` (docstring "See also:"), `deprecation.py` (docstring +
   `_DOCS_URL` string literal), `wp_state.py` (docstring "See ADR:"),
   `charter/bundle.py` (docstring), `agent/README.md` (markdown link). No
   symbol, import, or command-surface change.
6. **ruff** clean; **terminology guard** green. (mypy's lone `yaml` stub error
   is a missing `types-PyYAML` in the standalone invocation — environment
   artifact, not a code defect.)

---

## ❌ BLOCKING — Issue 1: 11 ADR cross-references rewritten to a dead era subdir

**What happened.** Several late-2.x ADRs existed on the mission base in **both**
`architecture/2.x/adr/` and `architecture/3.x/adr/` (duplicated across eras).
The structural move (WP03/WP06) **deduped them to a single `docs/adr/3.x/`
copy** — the `docs/adr/2.x/` copy was dropped. WP08's prefix rewrite mapped
`architecture/2.x/adr/<file>` → `docs/adr/2.x/<file>` (the declared move pair),
producing references to files that **no longer exist at that era**.

**Evidence (WP08-only diff):**
- WP08 **removed** 11 working `architecture/2.x/adr/...` refs.
- WP08 **added** 31 `docs/adr/2.x/...` lines across those 11 distinct ADRs.
- **All 11 resolved on the mission base** (file existed under
  `architecture/2.x/adr/`) and are **dead now** (`docs/adr/2.x/<file>` absent).
- **All 11 have a resolving `docs/adr/3.x/<file>` twin** — the correct rewrite
  target. The fix is fully deterministic.

The 11 (and reference-site counts):

| ADR (basename) | dead `docs/adr/2.x/` | correct `docs/adr/3.x/` | sites |
|---|---|---|---|
| 2026-04-25-1-shared-package-boundary.md | dead | exists | 5 files / 7 lines |
| 2026-04-26-3-e2e-hard-gate.md | dead | exists | 2 / 5 |
| 2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md | dead | exists | 3 |
| 2026-04-26-2-auth-transport-boundary.md | dead | exists | 2 / 3 |
| 2026-04-26-1-contract-pinning-resolved-version.md | dead | exists | 2 / 3 |
| 2026-05-16-1-doctrine-layer-merge-semantics.md | dead | exists | 2 |
| 2026-05-10-1-deterministic-historical-mission-state-repair.md | dead | exists | 1 / 2 |
| 2026-04-20-1-mutation-testing-as-local-only-quality-gate.md | dead | exists | 1 / 2 |
| 2026-04-04-2-mission-type-...-terminology-boundary.md | dead | exists | 2 |
| 2026-04-07-1-global-slash-command-installation.md | dead | exists | 1 |
| 2026-04-06-1-wp-state-pattern-for-lane-behavior.md | dead | exists | 1 (`src/specify_cli/status/wp_state.py` docstring) |

**Why the completeness teeth missed it.** The post-sweep grep counts residual
`architecture/` refs. These refs now read `docs/adr/2.x/...` — they look
successfully rewritten, so the 938→57 grep is **structurally blind** to wrong-era
routing. The "0 in-scope misses" claim is vacuous for this class.

**This is not the relative-link debt (Issue note below).** These are
occurrence-map path references the tool **owns and rewrote** — to a dead target
it had the on-disk information to get right.

### Fix (deterministic)

Make the rewrite land on the surviving era. Preferred: extend
`resolve_destination` (or add a post-substitution file-existence fallback) so
that when the rewritten `docs/adr/<era>/<file>` does **not** exist but a twin
`docs/adr/<other-era>/<file>` does, route to the surviving era. Add a tool test
pinning this (an era-deduped ADR ref resolves to the surviving era). Then re-run
the sweep and **add a teeth check that the post-sweep doc-link targets actually
resolve on disk** (not just "no `architecture/` residual"), so this class can't
recur. Alternatively, add per-file overrides for the 11 to the occurrence map
and surface the dedup as the IC-01 gap it is.

---

## Note (NON-blocking) — relative-link debt is genuinely out of scope

The implementer's flagged broken **bare-relative intra-doc links**
(`../2.x/adr/...`, `../../3.x/adr/...`, `../00_landscape/README.md`) are
**correctly out of WP08's scope**: they carry no `architecture/`/`docs/` anchor
and are resolved from each file's own location, so the prefix-matching tool
rightly does not own them. The directory restructure broke many (rough order:
hundreds of relative `.md` links across `docs/`). **This needs a follow-up** —
a dedicated relative-link-fixer WP (a "WP17") or a ticket. It does **not** gate
WP08, and should not be conflated with Issue 1.

---

## Anti-pattern checklist

1. Dead code — N/A (migration tool; `run`/helpers exercised by 16 tests). PASS
2. Synthetic-fixture test — PASS (tests drive real `run()` against a synthetic repo).
3. Silent empty return — PASS (no swallowing handlers in new paths).
4. FR coverage — FR-005/FR-009 exercised; but **FR-005 "no reference breaks"
   regressed** by Issue 1. FAIL.
5. Frozen surface — PASS (kitty-specs/docs-adr/arch-adr bodies 0 changed).
6. Locked decision — PASS.
7. Shared-file ownership — PASS (occurrence-map category partition holds; no
   `toc.yml`/`docfx.json` serialized or frontmatter-field edits by WP08).
8. Production fragility — PASS.

**Blocking item: #1 (FR-005 dead-link regression).**
