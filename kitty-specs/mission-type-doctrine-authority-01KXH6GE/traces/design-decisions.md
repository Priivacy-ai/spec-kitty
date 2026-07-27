# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

- 2026-07-14 — Decision: unify onto one charter-mediated `doctrine → charter → core` resolver (`resolve_mission_type_context`); `MissionType` doctrine artefact becomes load-bearing. Alternatives: populate the inert `governance_refs` (no runtime reader; false freshness); fill `governance-profile.yaml` only (leaves the action-path leak). Rationale: subsumes three already-mission-type-keyed functions into one path both consumers read. (ADR `2026-07-14-2`.)
- 2026-07-14 — Decision (Q1): the `MissionType` artefact **references** the sibling `governance-profile.yaml` for type-grain governance. Alternative: absorb governance as a field on `mission_types/<type>.yaml`. Rationale: reuse the live, schema'd, hard-failing surface — lowest churn.
- 2026-07-14 — Decision (Q2): the per-type override **rides the `doctrine/base.py` overlay stack** (`id` on `MissionTypeProfile` + a `BaseDoctrineRepository` subclass in `charter/`). Alternative: a bespoke field-merge in the resolver. Rationale: canonical builtin→org→project + collision warnings + #832 support, no duplicate merge site.
- 2026-07-14 — Decision (Q3): slice 1 covers governance + gates + **steps**; templates + remaining `specify_cli/missions` readers + tree deletion + the mission-instance addendum defer. Rationale: makes the artefact load-bearing on three of four axes now; templates are the cleanest defer.
- 2026-07-14 — Decision: parity tests are **transitional** (added at each swap, deleted before merge); enduring verification is behavioural at doctrine-module + integration level; no code kept solely to avoid test churn. Alternative: a surviving byte-snapshot/parity ratchet. Rationale: a surviving ratchet entrenches the very split the swap removes (operator-mandated).
- 2026-07-15 — Decision (WP03): the resolver resolves governance **and** action eagerly; the shared hard-fail fires only when a type is neither registered nor override-covered; an override-tolerated-but-unregistered type resolves governance and degrades action to `[]`. Alternative: strict-raise on the action slot for that case. Rationale: strict-raising there would make the governance-tolerant policy dead (no usable bundle for an override-tolerated type). Reviewer judged sound.
- 2026-07-15 — Decision (WP04, under review): leave the resolver's `action_grain` empty; close the leak by keying the Surface-A DRG action-doctrine path off `meta.json` directly. Alternative: thread the live action grain into `ResolvedGovernance` and union it. Rationale: feeding DRG loading (repo_root/action/depth/pack_context) into `mission_type_profiles.py` risks a circular dependency; the leak is closed either way. Consequence: the FR-013 URN cross-grain disjointness guard fires only against synthetic (WP03) data, not live action-grain content — flagged for reviewer adjudication + a possible follow-up.
