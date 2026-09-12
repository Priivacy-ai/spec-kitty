# Audit Action — Governance Guidelines

These guidelines govern the quality and rigor standards for the **audit** phase of a documentation mission. The deliverable is an evidence-based gap analysis that another author could read, reproduce, and use to plan content work. Audit is the empirical step that distinguishes "we think docs are missing" from "here is the matrix of cells that are missing, ranked by user impact".

---

## Core Authorship Focus

- Treat the audit as **evidence-based**, not impressionistic. Every claimed gap must be traceable to either a missing artifact, a missing Divio type, or a documented mismatch between the docs and the code surface they describe.
- Build a **coverage matrix** keyed by `(area, Divio type)`. Areas come from the discover spec; Divio types are tutorial, how-to, reference, and explanation. Empty cells are gaps; populated-but-stale cells are debt.
- Classify each existing document by its Divio type using frontmatter when present and content heuristics when not. Document the classification confidence so reviewers know which entries to spot-check.
- Cross-reference the documentation against the actual source-of-truth surface (modules, endpoints, CLI commands, configuration keys). Drift between docs and code is itself a finding.

---

## Audit Components to Lock Down

- **Coverage matrix** — `(area × Divio type)` populated with `present`, `present-but-stale`, or `missing`. Stale is determined against an objective signal (last-modified, referenced symbol no longer exists, screenshot obsolete).
- **Source-of-truth alignment** — for reference content, every documented entity must exist in code; for tutorial content, every described step must succeed when followed verbatim.
- **Existing-doc inventory** — every file under the documentation root is accounted for. Ungoverned content is a finding, not a free pass.
- **Prioritization scheme** — gaps ranked by **user impact**: blocks-onboarding > blocks-task > blocks-discoverability > nice-to-have. Use the audience from discover to set the impact lens.

---

## Reproducibility Standards

- The audit must be **reproducible**: a later author re-running the analysis with the same inputs reaches the same matrix. Avoid one-off heuristics that cannot be re-applied.
- Capture the **classification rule** for every Divio-type assignment so a reviewer can challenge it. "I think this is a how-to" is not a finding; "frontmatter declares `type: how-to` and content matches the task-oriented heuristic" is.
- Where automated detection is uncertain, mark the cell `low-confidence` rather than silently guessing. The validate phase will revisit low-confidence cells.

---

## Prioritization Discipline

- Rank gaps by **user impact**, not author convenience. A missing tutorial for a core feature outranks a missing explanation for an edge case, even when the tutorial is harder to write.
- Tie each priority bucket to a **target audience and task** so a downstream author understands why the gap matters.
- Surface **drift findings** (docs exist but contradict the code) at high priority — wrong information is worse than missing information.

---

## What This Phase Does NOT Cover

The audit action produces the gap analysis and priority list. It does **not**:

- Re-open the documentation needs or scope (those are discover decisions, already locked).
- Design the documentation architecture (that is the design action's job).
- Write or fill any documentation cells (that is the generate action's job).
- Validate the produced content against quality gates (that is the validate action's job).

An audit document that already proposes new section trees or generator configurations is a leaked design. Keep the phases clean.

---

## Quality Gates

- The coverage matrix is complete: every `(area, Divio type)` cell carries a status.
- Every gap has a stated user impact and a target audience tied back to the discover spec.
- Drift findings cite the conflicting docs path and the contradicting source-of-truth location.
- Low-confidence classifications are flagged for the validate phase rather than silently promoted.
