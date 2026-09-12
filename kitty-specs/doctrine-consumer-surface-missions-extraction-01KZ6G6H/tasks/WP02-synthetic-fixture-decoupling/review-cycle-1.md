---
affected_files: []
cycle_number: 1
mission_slug: doctrine-consumer-surface-missions-extraction-01KZ6G6H
reproduction_command:
reviewed_at: '2026-08-04T20:30:13Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 review — Synthetic-fixture decoupling + daphne cleanup

Reviewer: reviewer-renata
Scope reviewed: `2c5a7ca2b..HEAD` (`0b8027893`, `7d39fe9c2`) in lane-a.
Verdict: **REJECT** — one blocking finding (B1), three non-blocking (N1–N3).

## What is verified good (do not redo)

Checked by execution, not by reading:

- `uv run --extra test --project . python -m pytest tests/architectural/test_no_dead_doctrine_paths.py tests/architectural/test_no_dead_cli_paths.py -q` → **22 passed**.
- `ruff check` on both touched test modules → clean. `mypy` on both → clean.
- `pytest tests/architectural/test_no_legacy_terminology.py` → 10 passed.
- Daphne cleanup: `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml` parses; the
  `src/doctrine/graph.yaml` mention is gone; live `scan_graph_monolith_shipped().forbidding_mentions`
  is now **empty** — and it is *not* pinned to `== []` anywhere, so the explicitly-rejected
  "loosen the live assertion to tolerate zero" shape (#3036) was correctly avoided.
- A1's neighbouring pin (`test_project_tier_graph_path_would_false_red_without_its_discriminator`)
  still holds with `forbidding_mentions` empty — no collateral from the cleanup.
- A2's fixture proof keeps a non-empty guard plus an exact effect-set pin, and the pre-existing
  `test_gate_a_discriminators_do_not_swallow_a_planted_violation` still proves A2 is not a blanket
  escape. FR-002's contract items 1–3 and the falsification criteria (a)/(b)/(c) all hold.
- No assertion was deleted anywhere in the diff.

The prior round's flag (C3's live effect invisible) was genuinely addressed by
`test_boundary_escape_live_count_has_a_floor`. That fold is accepted in principle; see N1 for a
docstring correction to fold in alongside B1.

## B1 (BLOCKING) — C3 excuses sites that are *wrong*, and it does so across the gate's own corpus

`_escapes_boundary()` is evaluated per scan root, and `scan_doctrine_cross_links_shipped()` calls
`scan_doctrine_cross_links()` once per root (`_DOCTRINE_ROOT`, then `_PACKS_ROOT`). Consequence: a
link from `src/doctrine/**` into `packs/built-in/**` (or the reverse) escapes the boundary of the
root it was scanned under — even though the same function merges both roots into one "shipped
doctrine" corpus two lines later.

Measured on this branch:

```
boundary_escapes: 33   (unresolved: 0)
  sibling-tree escapes (src/doctrine <-> packs/built-in): 15
  docs/ escapes:                                          18
```

Probed directly against `_classify_link` with the live roots:

```
src/doctrine/templates/diagrams/README.md
  ../../../../packs/built-in/toolguides/MERMAID_DIAGRAMMING.md -> boundary_escape   (real target)
  ../../../../packs/built-in/toolguides/TOTALLY_BOGUS.md       -> boundary_escape   (BROKEN, exempted)
  ./bogus-in-boundary.md                                       -> unresolved        (correctly caught)
packs/built-in/toolguides/CONTEXTIVE.md
  ../../../src/doctrine/templates/architecture/BOGUS.md        -> boundary_escape   (BROKEN, exempted)
```

So a genuinely broken cross-tree link is now silently exempted. Fifteen live sites that Gate C
verified before this WP are no longer verified by anything. Three problems with that:

1. It contradicts this module's own binding invariant, stated in its docstring and unchanged by
   this WP: *"Discriminators exclude sites that are correct; they never excuse a site that is
   wrong."* C1 (fenced code) and C2 (`{placeholder}`) exclude sites that are categorically not
   navigation. C3 as written excludes a whole class regardless of correctness.
2. It goes past what US2-AS3 asks. AS3 exempts links pointing *"outside the built-in-doctrine
   package boundary."* Gate C's own definition of that corpus is the **union** of the two shipped
   roots — `scan_doctrine_cross_links_shipped()` says so. The 18 `docs/` escapes are squarely
   inside AS3's ask and are correct to exempt: the package genuinely cannot guarantee `docs/`
   ships alongside it. The 15 sibling-tree links are not — both trees are in the same wheel today,
   and C-002 explicitly keeps the `packs/built-in` extraction (#3022) out of this mission's scope,
   so the "they will ship separately" premise is not yet true.
3. It is the exact failure mode your own floor-test docstring names: *"silently removing coverage
   rather than exercising the AS3 exemption."*

**What would clear this.** Make the in-boundary set for the shipped scan the union of the shipped
roots, so `src/doctrine <-> packs/built-in` links stay resolution-checked while `docs/` escapes
stay exempt. The fixture-driven tests must keep working unchanged with a single root — e.g. an
optional `boundary_roots` parameter defaulting to `(root,)` — so `scan_doctrine_cross_links(root)`
in the four `tmp_path` tests is untouched. Design is yours; the requirement is only that a broken
`src/doctrine -> packs/built-in` link reds Gate C.

Two follow-ons once that lands:

- Add a regression test for exactly this case: a planted broken sibling-tree link must land in
  `unresolved`, not `boundary_escapes`. Today
  `test_gate_c_boundary_discriminator_does_not_swallow_an_in_boundary_violation` only covers a
  broken link inside a *single* root, which is why the gap survived.
- Re-measure and re-pin `test_boundary_escape_live_count_has_a_floor` (33 will drop to ~18), and
  update its docstring's "Measured 2026-08-04: 33" line.

## N1 (non-blocking) — the floor test's docstring claims a property the assertion does not have

`test_boundary_escape_live_count_has_a_floor` says it fails *"if `_escapes_boundary` is ever
widened until this bucket balloons, or narrowed/refactored until it collapses toward zero."*
`assert len(scan.boundary_escapes) >= 20` catches only the collapse. Widening passes at any size.

This is not a coverage hole — the blanket-widening case is caught by
`test_gate_c_boundary_discriminator_does_not_swallow_an_in_boundary_violation` — but in a test
whose whole subject is anti-vacuity, attributing a guard to the wrong assertion is the kind of
comment that gets trusted later. Either drop the widening clause and point at the sibling test
that actually covers it, or add an upper bound. Please fold this with B1's re-pin.

## N2 (non-blocking) — NFR id inconsistency inside both modules

The two docstrings this WP wrote say *"NFR-002 proof for discriminator A2 / C3"*. Their siblings in
the same files — A1, C1, C2 — and both module docstrings say **NFR-003**, and NFR-003 is this
mission's "Gate split preserves existing coverage" while NFR-002 is "Layer direction preserved
through the relocation" (a WP04/WP05 concern with nothing to do with discriminator proofs). The
spec's US2/FR-001/FR-002 prose does use "NFR-002" loosely for the discriminator-proof discipline,
so this is inherited, not invented — but the module should not carry two ids for one discipline.
Align the two new docstrings with their neighbours.

## N3 (nit) — reflowed daphne line

`packs/built-in/agent_profiles/doctrine-daphne.agent.yaml:137` now runs ~110 chars where the
surrounding block scalar wraps at ~95. Cosmetic only; the YAML parses and the content is correct.

## Commands run

```
uv run --extra test --project . python -m pytest \
  tests/architectural/test_no_dead_doctrine_paths.py \
  tests/architectural/test_no_dead_cli_paths.py -q -p no:cacheprovider     # 22 passed
uv run --extra test --project . python -m pytest \
  tests/architectural/test_no_legacy_terminology.py -q -p no:cacheprovider # 10 passed
uv run --extra test --project . python -m ruff check <two touched test modules>  # clean
uv run --extra test --project . python -m mypy  <two touched test modules>       # clean
```

Shared-ratchet check (NFR-004): `test_gate_coverage.py` + `test_ci_architectural_gate_coverage.py`
→ 43 passed; `test_arch_shard_marker_completeness.py` → 7 passed. The three new tests land in an
already-covered file, and the ratchet keys on orphan *files*, not test counts — so
`_gate_coverage_baseline.json` needs no regeneration for this WP.

plus ad-hoc probes of `scan_doctrine_cross_links_shipped()`, `_classify_link()` and
`scan_graph_monolith_shipped()` against the live roots (outputs quoted above).
