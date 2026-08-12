# WP10 Arbiter Decision

**Decision:** approve after the third and final review cycle.

The sanitation itself is accepted: the package removes 304 collected nodes (`841 → 537`), terminalizes all 54 owned paths, preserves 42 live guard families, and splits the three previously heterogeneous deletion files into 26 exact causal/no-authority families. Independent cycle-3 review confirmed the `10 / 7 / 9` family partition, sampled successor commands, scope, ownership, and absence of production or cycle-3 test edits.

The remaining disagreement is evidence bookkeeping, not test validity: 42 KEEP rows reference the prior content-addressed probe blob (`b91073…`) while the rewritten current artifact hashes to `de8354…`; the results summary hash is likewise stale. A fourth implementation/review cycle is prohibited. WP08 therefore owns mandatory mechanical closure: reconcile every WP10 retained-row evidence reference to the current artifact or an explicit immutable historical git blob, recompute the results hash, and fail its aggregate validator if any stale reference remains. This is an assigned acceptance gate, not a waiver.

No WP10 test deletion or restoration is deferred. The implementation is approved on substantive correctness; mission acceptance remains blocked until WP08 closes the hash references.
