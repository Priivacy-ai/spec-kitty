# Issue matrix — glossary-pack-doctrine-kind-01KY30SW

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1418 | Promote glossary to a first-order doctrine artefact (GLOSSARY_PACK kind) | fixed | Mission A delivered #1418's full stated scope (glossary packs + activation slices + built-in pack): WP01 GLOSSARY_PACK ArtifactKind/NodeKind + underscore URN (b6cf1eb6b); WP02 repository/schema/`DoctrineService.glossary_packs`; WP03 built-in `spec-kitty-core` pack (104 terms) generated + resolves as a loaded DRG node; WP04 charter activation + default-on (three-way drift-guard); WP05 doctor observability. Merged (ec2e050ea), base-divergence reconciled (c4985d5a9), arch gates green (62ce9a093). The broader glossary-as-doctrine program (enforcement, runtime retirement, cleanup) continues under **separate** tickets #2822/#2727/#2830/#2823/#2599 (Missions B/C/D per docs/plans/glossary-doctrine-overhaul-program.md) — not #1418 follow-up. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
