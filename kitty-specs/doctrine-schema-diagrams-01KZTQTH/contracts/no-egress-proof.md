# Contract: No-egress proof (NFR-002, C-001)
- (a) BEHAVIORAL: a diagram with !include/!includeurl fails-closed / performs no fetch under SANDBOX (negative test).
- (b) ISOLATION: the render runs green under `docker run --network=none` on the actual CI runners (portable; runners have Docker). unshare -rn only where unprivileged userns is permitted (with `ip link set lo up`). CI-Linux is the hard gate; a spike confirms the mechanism before the step is committed.
- URL-grep is a secondary lint. Local success alone is NOT accepted as proof.
