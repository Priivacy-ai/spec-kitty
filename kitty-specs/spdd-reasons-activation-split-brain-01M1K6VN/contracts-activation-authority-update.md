---
title: 'Contracts: SPDD/REASONS activation-authority update'
description: 'FR-009 correction of the activation-authority facts in the two frozen contracts/activation.md and contracts/charter-context.md docs, relocated here per NFR-002 (test_archive_root_byte_identical.py freezes those two files byte-identical).'
doc_status: active
updated: '2026-09-03'
related:
- kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md
- kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md
- docs/context/charter.md
---

# Contracts: SPDD/REASONS activation-authority update

This file supersedes/corrects the activation-authority facts stated in the two frozen contract docs
below, by their real repo-relative paths:

- `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md`
- `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md`

Both files predate the IC-04 triad-retirement and this mission's fix (`spdd-reasons-activation-split-brain-01M1K6VN`,
FR-009): they still name `governance.yaml`/`directives.yaml` as the read target, files already retired
independent of this mission. Both live under a byte-frozen archive root
(`tests/architectural/test_archive_root_byte_identical.py`, `_MISSION_BASE_REV = "fc4acaa897"`) and cannot be
edited directly without tripping that gate (confirmed via `git show fc4acaa897:<path>` for both — see this
mission's `tracer-tooling-friction.md`, item 1). Per the operator ruling
(`reviews/tasks.ruling.md`, "NFR-002 collision in WP05 — ruled from precedent, not escalated"), the
correction is delivered here instead: this file is the live, current-authority pointer a future reader
should trust over the two frozen originals for the facts named below. Neither frozen file is edited by this
mission; both remain byte-identical to their archived state.

## Corrects `contracts/activation.md`

### Failure modes

Corrects `contracts/activation.md`'s three rows ("Missing `.kittify/charter/`: returns `False`," "Malformed
governance.yaml: raises," "No paradigms section in governance.yaml: returns `False`"). The actual source and
failure modes per `is_spdd_reasons_active`'s landed rewrite
(`src/charter/offering/spdd_reasons/activation.py`, mission WP01, FR-001/FR-004/FR-005):

| Case | Behavior |
|---|---|
| Missing `.kittify/config.yaml` | Returns `False`. FR-004's explicit, evidence-based carve-out — stated as deliberate in the module's own code comment, not full `PackContext` parity. Confirmed safe: `command_renderer.py`'s `apply_spdd_blocks_for_project` is the one live call path reached before `.kittify/config.yaml` exists (during `spec-kitty init`), and the pre-rewrite body already returned `False` for its equivalent absent-`.kittify/charter/` case, so this preserves byte-for-byte behavior on that path. |
| Malformed top-level YAML in `.kittify/config.yaml`, or in the pointed `charter.yaml` | Raises (`_SpddActivationConfigError`, a module-local, `charter.activation`-import-free equivalent of `PackContext.from_config`'s `CharterPackConfigError`, FR-005). Never a silent `False`/`True`. |
| A dangling or unreadable `charter:` pointer target | Raises (FR-005). |
| A present-but-non-list `activated_<kind>` value (e.g. a bare scalar) | Raises, mirroring `PackContext._read_list_key`'s contract — never silently iterates a string character-by-character. |
| No `activated_<kind>` keys present at all (key absent, or present as YAML `null`) | Resolves to `None` per-kind, treated as "all built-ins available" (FR-001(d)) — a NEW row relative to the frozen doc's "no paradigms section → `False`": under the three-state semantics `PackContext.from_config` (and this rewrite's replication of it) uses, an absent key is NOT the same outcome as an explicitly-empty (`[]`) one. An explicit `[]` for a given kind means "opt that kind out"; an absent key means "no opinion, defer to built-in defaults" — the frozen doc's old reading collapsed both to `False`. |

### Performance

Corrects `contracts/activation.md`'s "Reads at most two YAML files (`governance.yaml`, `directives.yaml`).
Must complete in <50ms typical.":

Reads at most two YAML files — `.kittify/config.yaml`, and (when INV-2's `charter:` string pointer is
present) the pointed `.kittify/charter/charter.yaml`. Same file COUNT as the frozen doc stated, corrected
file NAMES. Must complete in <50ms typical (unchanged budget; no per-process cache is kept post-rewrite —
`PackContext.from_config` itself is always-fresh and reads at most two files at this same budget, so
retiring the cache stays within it while eliminating same-process cache-invalidation risk entirely).

### Tests (acceptance)

Corrects `contracts/activation.md`'s 7-case table, which predates the three-state semantics. The
`.kittify/config.yaml`/`activated_<kind>`-based fixture shape (mandatory parity test
`tests/charter/test_spdd_reasons_activation_parity.py`, FR-002) replaces the old unqualified "selected"
framing:

| Case | `.kittify/config.yaml` / pointed `charter.yaml` shape | Expected |
|---|---|---|
| 1 | No `.kittify/config.yaml` on disk | `False` (FR-004) |
| 2 | `activated_paradigms`/`activated_tactics`/`activated_directives` all absent (key not present at all) | `True` — absent resolves to `None` per-kind ("all built-ins available"), so all four selectors are satisfied |
| 3 | `activated_paradigms: []`, `activated_tactics: []`, `activated_directives: []` (all three explicitly empty) | `False` — explicit empty is a real opt-out, distinct from case 2's absence |
| 4 | `activated_paradigms: [structured-prompt-driven-development]` | `True` |
| 5 | `activated_tactics: [reasons-canvas-fill]` only | `True` |
| 6 | `activated_tactics: [reasons-canvas-review]` only | `True` |
| 7 | `activated_directives: [DIRECTIVE_038]` (or a `038-` numeric-hint slug) only | `True` |
| 8 | Malformed YAML in `.kittify/config.yaml` | Raises (not silently `False`) |
| 9 | `.kittify/config.yaml` carries a string `charter:` pointer to a missing/malformed target `charter.yaml` | Raises (FR-005) |
| 10 (new, explicit-empty-vs-absent) | `activated_directives: []` while `activated_paradigms`/`activated_tactics` are absent | `True` — the disjunction is per-kind independent; one kind's explicit opt-out does not suppress another kind's absent-defaults-to-available state (mirrors FR-002's fixture matrix / WP01's parity test) |

Case 2/3/10 are the load-bearing additions this correction makes over the frozen doc's original 7-case
table: they pin the absent-vs-explicit-empty distinction the split-brain bug this mission fixes depended on
collapsing.

## Corrects `contracts/charter-context.md`

### Implementation seam

Corrects `contracts/charter-context.md`'s "Implementation seam" section, which names the stale
`src/doctrine/spdd_reasons/charter_context.py` + `src/charter/context.py`'s `_append_action_doctrine_lines()`
call site. Re-verified live against the current tree: the real function is
`append_spdd_reasons_guidance(lines, mission, action)`, defined in
`src/charter/offering/spdd_reasons/charter_context.py` and re-exported from
`src/charter/offering/spdd_reasons/__init__.py`. Its real call site is inside
`src/charter/activation/context_renderers/bootstrap_text.py` — a module under
`charter.activation.context_renderers`, not `src/charter/context.py` (which no longer contains this call).
The call site gates on `is_spdd_reasons_active` before appending guidance, matching the "Behavior change"
contract below:

```python
if is_spdd_reasons_active(charter_path.parent.parent.parent):
    append_spdd_reasons_guidance(lines, doctrine_bundle.mission, action)
```

(`bootstrap_text.py`'s doctrine-bundle rendering block, symbol `append_spdd_reasons_guidance` — cited by
symbol per this mission's citation-discipline rule, in preference to a bare line number that would drift).

## Unaffected by this mission

`contracts/charter-context.md`'s "Behavior change"/"Inactive guarantee" sections (the byte-identical-when-
inactive contract — a pure read-path fix, spec.md C-002) and its "JSON shape (unchanged)" section are
**unaffected** by this mission and need no correction. Re-verified live: the cited test file
(`tests/charter/test_charter_context_spdd_reasons.py`) still contains the described "inactive baseline"
fixture after WP04's fixture-triage pass — `TestCharterContextInactive::test_inactive_output_omits_guidance`
is present and unmodified in its intent (asserts the inactive path emits zero `SPDD/REASONS Guidance` lines).
WP04 does not remove or alter this class; only the eight `True`-asserting fixture-construction cases named
in spec.md FR-010 were rewritten to build `.kittify/config.yaml`-shaped fixtures instead of
`charter.yaml` `governance:`/`directives:` ones.

## Pointer

The two frozen originals this file corrects, unchanged and byte-identical to their archived state by
design (NFR-002) — this file is the corrected reading, not a replacement artifact that retires them:

- `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md`
- `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md`
