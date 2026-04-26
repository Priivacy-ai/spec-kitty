# Output Action — Governance Guidelines

These guidelines govern the quality and publication-readiness standards for the **output** phase of a research mission. The deliverable is a published research artifact (findings report, literature review, ADR, or equivalent) that is faithful to the evidence and ready for peer review.

---

## Publication Readiness

- The output phase ends with the **publication approval gate** (`gate_passed("publication_approved")`). This is the runtime predicate, declared in `src/doctrine/missions/research/mission.yaml` and enforced by `src/doctrine/mission_step_contracts/shipped/research-output.step-contract.yaml`, that gates advancement from `output` to `done`. Treat publication as a review event, not a rendering step — the host harness records `publication_approved` only after the operator has verified the readiness checks below.
- A reader who arrives at the output without the source register or evidence log must still be able to evaluate the rigor of the work.
- The published artifact and the underlying evidence base must be **consistent**: every claim in the output traces to an evidence row, and every high-confidence evidence row that informs a finding is reflected in the output.

---

## Citation Completeness

- Every citation referenced in the output must appear in the source register, in the chosen format (BibTeX or APA).
- DOIs and URLs in the output match those in the register; access dates are preserved.
- Inline citations, footnotes, and bibliography are consistent — reviewers cross-check these and inconsistencies erode trust.

---

## Methodology Clarity for Peer Review

- The output describes the methodology in enough detail that a peer reviewer can assess whether the conclusions are warranted by the design.
- Inclusion and exclusion criteria, search strategy, and quality assessment approach appear in the output (or in a clearly-linked appendix).
- Limitations and threats to validity from the synthesis phase are carried forward into the output. Suppressing them is a fidelity violation.

---

## Specification Fidelity (DIRECTIVE_010)

- The output must be **faithful** to the underlying research artifacts. Do not introduce findings that are not supported by the evidence log.
- Do not soften limitations or omit alternative interpretations to make the narrative cleaner.
- If late edits change a finding, the supporting evidence row must change with it — drift between findings and evidence is a fidelity break.

---

## What This Phase Does NOT Cover

The output action publishes the research. It does **not**:

- Re-scope the question (locked at scoping).
- Re-design methodology (locked at methodology).
- Add new sources or evidence (that is the gathering action's job; if late discovery is needed, route through the proper phase).
- Re-synthesize findings from raw evidence (that is the synthesis action's job; output consumes synthesis, it does not redo it).

If preparing the output reveals that synthesis is incomplete or unfaithful to evidence, hand back to synthesis — do not patch over it during formatting.

---

## Quality Gates

- All citations in the output appear in the source register and resolve.
- Methodology is described at peer-review fidelity.
- Limitations and threats to validity are present, not hidden.
- Findings in the output are consistent with the evidence log; no claim is unsupported.
- The artifact is in a form a peer reviewer would accept (proper structure, citations, abstract, conclusions).
