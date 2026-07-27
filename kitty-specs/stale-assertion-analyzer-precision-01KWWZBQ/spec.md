# Mission Specification: Stale-assertion analyzer precision — cross-file move detection + generic-literal noise suppression

**Status**: Draft
**Issues**: Closes [#2031](https://github.com/Priivacy-ai/spec-kitty/issues/2031) + [#2343](https://github.com/Priivacy-ai/spec-kitty/issues/2343) (M3 of epic #1931)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor whose behavior-preserving refactor (an extraction) triggers a false-positive storm from the post-merge stale-assertion analyzer.

**Grounding**: `src/specify_cli/post_merge/stale_assertions.py` (686 lines) is **intra-file only** — `_extract_changed_symbols` defines "removed" as *present in base_ref but absent in head_ref **for a given file*** (`:146`; `removed_ids = base_id_names - head_id_names`, `removed_lits = base_lit_vals - head_lit_vals`). So when a behavior-preserving extraction **relocates** a symbol from module A to module B (re-exported / aliased back), the analyzer reads it as "removed from A" and flags every test asserting on it. Witnessed on PR #2028 (mission `01KVCGQC`): WP05's extraction of the `baseline_merge_commit` cluster into a new `merge/baseline.py` produced **180 findings (all false)** and tripped the analyzer's own drift ceiling (`9.4 > 5.0`). A second **~108 false findings** in the same PR were **removed short/generic string literals** in reformatted regions — the #2343 noise class. **(Correction, verified against the code):** the analyzer already strips `lineno` *before* the set-difference (`base_id_names = {name for name, _ in base_ids}`, `:185`) and `_extract_identifiers` only captures `def`/`class` names — so a **pure in-file line-shift is already NOT flagged**, and a module-level assignment like `mission_id = …` (an `ast.Assign`) is never in the identifier set at all. So this mission's two real engines are (1) **cross-file relocation** (`#2031`) and (2) **generic-literal noise** (`#2343`) — not line-shift. The analyzer is **heuristic-by-design** (never claims "definitely_stale") — dev-ex NOISE, not a correctness bug (P3/tech-debt).

### User Story 1 - An extraction refactor doesn't storm (Priority: P1)
As a contributor, I want a symbol relocated A→B (re-exported/aliased) recognized as **moved, not removed**, so my behavior-preserving extraction doesn't flag every test on it.

**Independent test**: reproduce the WP05 case (extract a symbol cluster into a new re-exported module in the same diff) → the analyzer emits ~0 "removed" findings for the relocated symbols (was 180).

### User Story 2 - Generic literals don't add noise (Priority: P2)
As a maintainer, I want short/generic removed string literals down-ranked or suppressed so they don't dominate the report.

### User Story 3 - A GENUINE stale assertion is still caught (Priority: P1)
As a maintainer, I want a truly-removed symbol (deleted, not relocated) to still be flagged — the precision fix must not blind the analyzer.

### Edge Cases
- Symbol relocated AND renamed → the origin file's head no longer re-exports the OLD name → **NOT** suppressed (a rename is a real change).
- **Name collision (the trap):** a genuine deletion of `X` in file C while an UNRELATED `X` is defined in another changed file B → C's head does not re-export `X` → **still flagged** (why suppression keys on head-importability, not "bare name appears somewhere in the diff").
- Re-export via `__init__.py` vs `from X import Y as _Y` shim vs a same-qualname new-module def — all three should count as "still present".
- A genuinely SHORT assert-critical literal (e.g. an error code `"E001"`) → **NOT suppressed**, because the rule keys on **genuineness** (a pinned generic-token/all-punctuation set), not length. Since all literal findings are literals-in-asserts, genuineness — not length or assert-context — is the discriminator.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Relocation/re-export → SUPPRESS, keyed on HEAD-IMPORTABILITY (not bare-name-anywhere) | As a maintainer, I want a removed identifier **suppressed only when it is still importable from its ORIGIN file in head** — i.e. the origin file's head re-exports/imports the name (`from .b import X`, `X` in `__all__`/an `__init__` re-export, `import X as _X`). **Substrate reality:** the analyzer has NO qualname primitive — `_extract_identifiers` captures **bare names** (`node.name`) and `ast.walk` flattens nested methods, so "the same name appears in another changed file" is **too loose**: it would falsely suppress a genuine deletion of a common name (`run`/`main`/`setup`) whenever an unrelated same-name def exists in another changed file, blinding the analyzer (FR-005/SC-003). Head-importability is the precise signal: it catches the WP05 extraction (symbols re-exported back → suppress) and does NOT fire for a genuine deletion (origin head no longer imports it → still flagged) or an unrelated collision. **Suppress (don't emit)**, not `info`-downgrade (info is mislabeled by `merge/executor.py`, dropped by the CLI, yet still FP-ceiling-counted). | High | Open |
| FR-002 | Head-importability detection | As a maintainer, I want the head-importability check to cover the real shim forms: `from <mod> import X` (incl. `as _X`), `X` listed in `__all__`, and `__init__`/module re-exports of `X`. A relocate-**and-rename** (origin head does not import the old name) is NOT suppressed — it's a real change. | High | Open |
| FR-004 | Suppress GENERIC removed literals (by genuineness, NOT length) | As a maintainer, I want a removed string literal **suppressed (not emitted)** only when it is **generic** by an explicit rule: value ∈ a **pinned generic-token set** (common English words / format fragments) OR all-punctuation/whitespace/empty. **Do NOT suppress by length alone** — a genuinely short literal can be assert-critical (e.g. an error code `"E001"`), and since ALL literal findings are by construction literals-in-asserts, length cannot separate noise from signal. The pinned token set goes in the impl (not "e.g."). Suppress (don't emit), not downgrade-to-`info` (same render/ceiling reason as FR-001). | Medium | Open |
| FR-005 | Non-vacuous proof (incl. the collision case) | As a maintainer, I want: the extraction case reproduced (symbols re-exported back → ~0 findings); a generic-literal case → ~0; a **genuine** deletion still flagged high/medium; AND — critically — **the name-collision case: a genuine deletion of `X` in file C while an UNRELATED `X` is defined in another changed file B (with C's head NOT re-exporting `X`) MUST still be flagged** (proving head-importability, not bare-name-anywhere, is the key — the fix must not blind the analyzer on common names). | High | Open |
| FR-006 | Drift-ceiling no longer trips on refactors | As a maintainer, I want the analyzer's own drift monitor (`9.4 > 5.0`, `FP_CEILING=5.0`, `findings_per_100_loc`) to not trip on a behavior-preserving extraction — suppressed (not-emitted) relocation/generic findings are not counted. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Heuristic honesty preserved | The analyzer still never claims "definitely_stale"; relocation-aware findings downgrade, they don't fabricate certainty. | Correctness | High | Open |
| NFR-002 | Bounded added cost | Same-diff cross-file symbol resolution reuses the already-parsed diff/AST set; no full-repo scan per finding. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Same-diff scope only | Relocation detection considers only files **in the same diff** (`base..head`), not the whole repo — a symbol that vanished entirely is still "removed". | Technical | High | Open |
| C-002 | No new suppressions | `ruff` + `mypy --strict` clean; no new `# noqa`/`# type: ignore`. | Technical | High | Open |

### Key Entities
- **`src/specify_cli/post_merge/stale_assertions.py`** — `_extract_changed_symbols` (`:139`, per-file removed sets), `_extract_identifiers` (`:121`, **BARE names** — no qualname primitive; `ast.walk` flattens nested methods → the collision surface), `_extract_string_literals` (`:130`), the confidence grading (`:392`+, `:532`+), `findings_per_100_loc`/`FP_CEILING` (`:664`). The new **head-importability** check parses the origin file's head imports / `__all__` / re-exports. Relocation/generic literals are **suppressed here (not emitted)**.
- **`src/specify_cli/merge/executor.py`** `_render_stale_findings` (`:864`) — buckets by confidence + hardcodes "message-content assertion(s) skipped" for `info`. **Verified NOT to need changes** because FR-001/004 *suppress* (don't emit) rather than downgrade to `info` — so nothing new reaches this renderer.
- **`src/specify_cli/cli/commands/agent/tests.py`** — the `stale-check` render (`:100`, high/medium/low only, drops `info`) + FP-ceiling warning (`:73`). Same rationale: suppression avoids the drop + the miscount.
- Tests under `tests/post_merge/` (or `tests/specify_cli/post_merge/`) — the analyzer's own suite.

## Success Criteria *(mandatory)*
- **SC-001**: A reproduced extraction (symbol → new re-exported module in the same diff) yields ~0 "removed" findings for the relocated symbols (regression fixture from the WP05 shape).
- **SC-002**: A reproduced generic-literal case is a **paired before/after** — suppression disabled produces the noisy findings, enabled yields ~0; and a genuinely SHORT assert-critical literal (`"E001"`-shape) is still emitted (proves genuineness-not-length).
- **SC-003**: A GENUINE deletion (removed, origin head not re-exporting it) is still flagged high/medium — INCLUDING the **name-collision** case (deletion of `X` in C while an unrelated `X` is defined in changed file B); the fix doesn't blind the analyzer on common names.
- **SC-004**: The FP-ceiling is proven by a **paired before/after on the SAME extraction fixture** (sized so it genuinely storms): suppression **disabled** → `findings_per_100_loc > FP_CEILING (5.0)` (reproduces the 9.4>5.0 storm); **enabled** → `≤ 5.0`. A `0.0`-on-empty fixture does NOT satisfy this — FR-006.
- **SC-005**: `ruff` + `mypy --strict` clean; the analyzer's own test suite green; no new suppressions.

## Out of Scope
- Whole-repo (cross-diff) move detection — only same-diff relocation (C-001).
- Reworking the confidence taxonomy beyond the literal down-rank rule.

## Assumptions
- #2031 and #2343 fold into one mission (same file, same precision concern).
- The witnessed PR #2028 shapes are reproducible as regression fixtures without needing that exact PR.
