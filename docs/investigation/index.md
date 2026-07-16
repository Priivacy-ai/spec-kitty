---
title: 'Investigation notes'
description: 'Design investigations and proposals grounded before they become specs or ADRs.'
doc_status: active
updated: '2026-07-16'
related:
- docs/notes/index.md
- docs/adr/3.x/README.md
---

# Investigation notes

Working design investigations — proposals grounded by review before they graduate into a spec or an ADR. These
are living analysis documents, not governance records; once a decision lands, it is recorded in an ADR under
[`docs/adr/`](../adr/3.x/README.md) and the investigation is left as provenance.

## Pages

- [Mission-type step-model unification](mission-type-step-model-unification.md) — retire "template" as a
  mission-type discriminator; make recursive steps the building block. Grounded by a design + code + adversarial
  squad; formalized in ADR `2026-07-16-2`.
