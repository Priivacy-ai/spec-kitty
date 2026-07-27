# Design-Decisions Trace — Mission-Lifecycle Tooling Friction

- **Lane A (#2220+#2221)**: code is the path authority (whole ownership subsystem is
  repo-relative); fix the doctrine TEXT (both copies) + complete the template frontmatter
  (+ `owned_files`, which #2221 under-lists). SSOT ratchet = one golden template→validator→
  finalize round-trip test (paula). Reject "teach the validator to accept absolute" (env leakage).
- **Lane B (#2218)**: NOT a flag — make `mission_creation.py:416` coord-branch minting
  CONDITIONAL on the topology value; classify via the existing `classify_topology` SSOT.
  Requires an end-to-end `single_branch` implement+merge proof (the coord-or-legacy fallbacks
  must handle the create-time non-coord shape). Default coord (backward-compat).
- **Lane C (#2222)**: the vcs lock is one-time VCS-TYPE selection state, NOT a concurrency
  mutex (claim concurrency is the status event log). Exclude the lock-only meta write from
  the dirty-tree guard; bites only on auto_commit=False non-coord missions. No race introduced.
- **Lane D (#2217)**: extend the existing ingestor seam (`generator.py` `_build_ingestor_findings`,
  which already ingests workflow-failures-log/analysis-report/mission-review) with a tracer reader;
  make the data-model gap conditional on domain entities. Do NOT fork the generator.
- **Lane E (#2223)**: extract the matrix rule-engine (`review/_issue_matrix.py`) to ONE validator
  with TWO callers (approve-gate blocking + finalize-tasks advisory). Do NOT reimplement rules.
- **Lane F (#2219)**: verify the upstream fix; add the 203-file blast-radius regression test; close.
- **B↔C coupling**: land C with/before B so create-time non-coord missions don't hit the lock friction.
