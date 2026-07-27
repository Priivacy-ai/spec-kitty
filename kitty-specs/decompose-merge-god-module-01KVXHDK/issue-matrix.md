# Issue matrix — decompose-merge-god-module-01KVXHDK

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2057 | Decompose merge.py god-module (3383 LOC, maxCC ~102) into seams + thin shim | fixed | merge.py 3383→559 LOC, maxCC≤15; 10 seams under specify_cli/merge/; squash-merge a25638955 on prog/2057-merge |
| #2026 | One-way-import seam pattern for cli/commands (epic) | fixed | every seam test asserts no `specify_cli.cli.commands.merge` import (AST-enforced); shim re-exports preserved |
| #1827 | Baseline record→commit→assert ordering invariant (INV-5/INV-6) | verified-already-fixed | ordering + restore-on-error preserved across the WP10 executor phase split; tests/merge/test_executor_phase_boundary.py + test_1827_baseline_regression.py green |
| #2056 | Top-of-file decomposition pointer-comment convention | fixed | WP11 installed the #2057 pointer comment + seam map (FR-002), matching the convention |
| #1623 | doctor.py god-module split convention (referenced precedent) | verified-already-fixed | precedent only; WP11 mirrors its pointer-comment / seam-map convention |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
