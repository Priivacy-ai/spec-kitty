# Issue matrix — tmp-literal-offender-burndown-01KWWRW2

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1842 | Test-suite state leaks: the existing-offender /tmp sweep | fixed | WP01–07 converted all 97 offenders (reviewer-approved semantics) + WP08 `5b5917f2` (baseline emptied, ratchet flipped to a self-consistent literal-free hard gate); full `tests/` grep `/tmp/` = 0; all 8 WPs approved |
| #2181 | Frozen /tmp ratchet (deferred its remediation to #1842) | verified-already-fixed | The ratchet + `tmp_ratchet_baseline.txt` landed via #2181; this mission completes its explicitly-deferred existing-offender remediation (WP08 empties the baseline + flips to a hard gate) |
| #2429 | Sibling structural PR (reaper + /tmp namespacing + tombstone) | verified-already-fixed | The structural-prevention half of #1842 ships separately in draft PR #2429 ("Part of #1842"); out of scope here, referenced as context |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
