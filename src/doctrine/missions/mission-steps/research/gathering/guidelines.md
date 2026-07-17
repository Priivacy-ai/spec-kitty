# Gathering Action — Governance Guidelines

These guidelines govern the quality and discipline standards for the **gathering** phase of a research mission. The deliverable is a complete, citation-clean source register that downstream synthesis and output phases can rely on as their evidence base.

---

## Source Registration Discipline

- Document **every** reviewed source in `research/source-register.csv`. A source that is read but not registered is invisible to downstream review.
- Capture each source with citation, URL or DOI, relevance assessment, and status (reviewed / pending / excluded).
- Sources excluded by inclusion/exclusion criteria are still registered — with the exclusion reason. Reviewers need to see the search yield, not just the kept set.
- Capture each key finding extracted from a source in `research/evidence-log.csv`, with confidence level (high / medium / low) and contextual notes.

---

## Citation Standards

- Use **BibTeX** or **APA** format consistently. Pick one and stay with it across the source register.
- Include **DOI** when available; otherwise include a stable **URL**.
- Track **access dates** for all online sources. Web sources drift; an access date is what makes a citation auditable.
- Assign **confidence levels** commensurate with source quality (peer-reviewed > preprint > industry report > blog post — adjust for your domain).

---

## Minimum-Source Threshold

- The research mission step contract requires at least three sources to be documented before gathering can be considered complete (`event_count('source_documented', 3)`).
- This threshold is a floor, not a ceiling. Most missions need substantially more. Use the success criteria from scoping to set the actual target.
- Document the source count as it grows; do not delay registration to the end of the phase.

---

## What This Phase Does NOT Cover

The gathering action produces a clean evidence base. It does **not**:

- Re-scope the research question or change inclusion criteria after gathering starts (that violates methodology discipline).
- Synthesize findings or draw cross-source conclusions (that is the synthesis action's job).
- Produce publication output (that is the output action's job).

Notes that begin to weave findings together belong in the synthesis phase, not in the source register.

---

## Quality Gates

- Source register is complete: every reviewed source has a row.
- Citation format is consistent across the register.
- Every online source has an access date.
- Confidence levels are assigned and justified.
- The minimum-source threshold from the step contract is met.
- Evidence rows are stable enough that later phases can cite them by ID.
