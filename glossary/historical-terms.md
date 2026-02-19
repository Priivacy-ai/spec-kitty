## Historical Terms

Terms from pre-integration origins that may appear in older documentation. Use the canonical terms above in all new work.

| Historical term                                             | Canonical term               | Notes                                                                                                                    |
|-------------------------------------------------------------|------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `doing` (lane)                                              | `in_progress`                | Legacy alias retained for compatibility in status transitions                                                            |
| "Most done wins" merge conflict rule                        | Rollback-aware precedence    | Deprecated by ADR `2026-02-09-3` to preserve reviewer rollback authority                                                 |
| Iteration (batch execution)                                 | *(no equivalent)*            | Spec Kitty uses continuous lane progression per WP, not batch grouping                                                   |
| Cycle (TDD RED→GREEN→REFACTOR)                              | Phase                        | Related but different granularity                                                                                        |
| Run Container (ADR-048)                                     | Worktree                     | Same concept, different name                                                                                             |
| Bootstrap Protocol                                          | Bootstrap                    | Evolved from `spec-kitty init` post-step to full onboarding command wrapping vision + constitution + agent customization |
| Approach                                                    | Paradigm                     | `Paradigm` is the canonical term for the conceptual worldview layer; `Approach` retained as legacy alias during migration |
| Doctrine stack terminology from agent-augmented development | Spec Kitty canon terminology | Historical source only; avoid using legacy names in new glossary entries                                                 |

---

*Last updated: 2026-02-17*
