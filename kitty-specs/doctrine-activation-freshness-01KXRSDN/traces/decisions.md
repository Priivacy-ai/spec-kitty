# Decision Log — Doctrine-activation freshness integrity

Tracer (seeded at planning; append as decisions are made/revised during implement; assess at close).

| ID | Decision | Status | Note / revisit-if |
|----|----------|--------|-------------------|
| DD-01 | Option (c) read-path parity (Q2=a), writer-agnostic; NOT eager-always regen; write-side marker rejected | LOCKED | Revisit only if a concrete case shows `run_consistency_check` cannot see a real activation writer. `merge_defaults` bypass is the proof it must be read-path. |
| DD-02 | Sequence #2758→#2759→#2157a; #2770 early-standalone | LOCKED | #2770 first (release-sensitive). If IC-03 turns out to need IC-04, re-order — not expected. |
| DD-03 | Q1 = fail-closed preflight (decision 01KXRVT2KA1Y3M4XQAYVQ3HHXF); keep 4-file hash | LOCKED | Coordinated with #2773 (no references.yaml stopgap). Revisit if #2773 lands first and deprecates references.yaml mid-mission. |
| DD-04 | Fences: #2760→#2721, #2157b OUT, broader #2519 OUT, Family 2 OUT | LOCKED | File #2760/#2157b as explicit follow-ups at close. |
| DD-05 | Preserve #2732 content-identity (compose, never replace) | LOCKED | NFR-002/SC-006. Any new invalidation marker must layer on content-identity. |
| DD-06 | Campsite folded in-WP (no separate campsite WP) | LOCKED | 3 SAFE-to-fold items in the edit targets (paula). |
| — | (append implement-time decisions here) | | |
