# Tooling Friction Issue Reconciliation

Reconciled on 2026-07-16 after opening [spec-kitty PR #2689](https://github.com/Priivacy-ai/spec-kitty/pull/2689) and [E2E PR #340](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/pull/340).

The scan covered the complete open and closed issue inventories in both repositories. A generic issue in the same subsystem was not treated as coverage unless its body described the same behavior or root cause. Result: 35 ledger entries map to pre-existing reports; 32 previously unreported entries are covered by 27 newly filed issues, grouping only shared root causes. TF-067 was added and reconciled immediately after the initial 66-row scan when PR CI exposed a new preview-environment prerequisite.

| Friction | Disposition | Issue |
|---|---|---|
| TF-001 | Existing report | [spec-kitty #1780](https://github.com/Priivacy-ai/spec-kitty/issues/1780) |
| TF-002 | New report | [spec-kitty #2691](https://github.com/Priivacy-ai/spec-kitty/issues/2691) |
| TF-003 | New report, shared root with TF-002 | [spec-kitty #2691](https://github.com/Priivacy-ai/spec-kitty/issues/2691) |
| TF-004 | Existing report | [spec-kitty #1951](https://github.com/Priivacy-ai/spec-kitty/issues/1951) |
| TF-005 | Existing report | [spec-kitty #2008](https://github.com/Priivacy-ai/spec-kitty/issues/2008) |
| TF-006 | Existing report; target-semantics rough edge is explicit in the issue body | [spec-kitty #1784](https://github.com/Priivacy-ai/spec-kitty/issues/1784) |
| TF-007 | Existing report | [spec-kitty #2533](https://github.com/Priivacy-ai/spec-kitty/issues/2533) |
| TF-008 | New report | [spec-kitty #2693](https://github.com/Priivacy-ai/spec-kitty/issues/2693) |
| TF-009 | Existing owner issue | [spec-kitty #2658](https://github.com/Priivacy-ai/spec-kitty/issues/2658) |
| TF-010 | New report | [spec-kitty #2695](https://github.com/Priivacy-ai/spec-kitty/issues/2695) |
| TF-011 | New report | [spec-kitty #2694](https://github.com/Priivacy-ai/spec-kitty/issues/2694) |
| TF-012 | Existing report | [spec-kitty #1617](https://github.com/Priivacy-ai/spec-kitty/issues/1617) |
| TF-013 | Existing report | [spec-kitty #2250](https://github.com/Priivacy-ai/spec-kitty/issues/2250) |
| TF-014 | New report | [spec-kitty #2696](https://github.com/Priivacy-ai/spec-kitty/issues/2696) |
| TF-015 | New report, shared doctor-contract root with TF-014 | [spec-kitty #2696](https://github.com/Priivacy-ai/spec-kitty/issues/2696) |
| TF-016 | Existing report | [spec-kitty #2090](https://github.com/Priivacy-ai/spec-kitty/issues/2090) |
| TF-017 | Existing report | [spec-kitty #1089](https://github.com/Priivacy-ai/spec-kitty/issues/1089) |
| TF-018 | Existing report | [spec-kitty #1310](https://github.com/Priivacy-ai/spec-kitty/issues/1310) |
| TF-019 | Existing report | [spec-kitty #2236](https://github.com/Priivacy-ai/spec-kitty/issues/2236) |
| TF-020 | Existing report | [spec-kitty #2566](https://github.com/Priivacy-ai/spec-kitty/issues/2566) |
| TF-021 | Existing report; same coordination-status commit root | [spec-kitty #2155](https://github.com/Priivacy-ai/spec-kitty/issues/2155) |
| TF-022 | Existing report | [spec-kitty #2101](https://github.com/Priivacy-ai/spec-kitty/issues/2101) |
| TF-023 | New report | [spec-kitty #2692](https://github.com/Priivacy-ai/spec-kitty/issues/2692) |
| TF-024 | New report | [spec-kitty #2690](https://github.com/Priivacy-ai/spec-kitty/issues/2690) |
| TF-025 | New report | [spec-kitty #2700](https://github.com/Priivacy-ai/spec-kitty/issues/2700) |
| TF-026 | New report, shared generated-bundle conformance root with TF-025 | [spec-kitty #2700](https://github.com/Priivacy-ai/spec-kitty/issues/2700) |
| TF-027 | Existing report | [spec-kitty #2643](https://github.com/Priivacy-ai/spec-kitty/issues/2643) |
| TF-028 | Existing report | [spec-kitty #2549](https://github.com/Priivacy-ai/spec-kitty/issues/2549) |
| TF-029 | New report | [spec-kitty #2702](https://github.com/Priivacy-ai/spec-kitty/issues/2702) |
| TF-030 | Existing report | [spec-kitty #1603](https://github.com/Priivacy-ai/spec-kitty/issues/1603) |
| TF-031 | Existing report; same split planning-artifact authority root | [spec-kitty #1816](https://github.com/Priivacy-ai/spec-kitty/issues/1816) |
| TF-032 | Existing report | [spec-kitty #2555](https://github.com/Priivacy-ai/spec-kitty/issues/2555) |
| TF-033 | Existing report | [spec-kitty #2570](https://github.com/Priivacy-ai/spec-kitty/issues/2570) |
| TF-034 | New report | [spec-kitty #2701](https://github.com/Priivacy-ai/spec-kitty/issues/2701) |
| TF-035 | Existing report; same missing test-extra/hermeticity root | [spec-kitty #987](https://github.com/Priivacy-ai/spec-kitty/issues/987) |
| TF-036 | New report | [spec-kitty #2703](https://github.com/Priivacy-ai/spec-kitty/issues/2703) |
| TF-037 | New report | [spec-kitty #2698](https://github.com/Priivacy-ai/spec-kitty/issues/2698) |
| TF-038 | New report | [spec-kitty #2699](https://github.com/Priivacy-ai/spec-kitty/issues/2699) |
| TF-039 | New report | [spec-kitty #2697](https://github.com/Priivacy-ai/spec-kitty/issues/2697) |
| TF-040 | Existing report | [spec-kitty #963](https://github.com/Priivacy-ai/spec-kitty/issues/963) |
| TF-041 | Existing report | [spec-kitty #2275](https://github.com/Priivacy-ai/spec-kitty/issues/2275) |
| TF-042 | Existing report; same acceptance-matrix authority split | [spec-kitty #2404](https://github.com/Priivacy-ai/spec-kitty/issues/2404) |
| TF-043 | Existing report | [spec-kitty #2275](https://github.com/Priivacy-ai/spec-kitty/issues/2275) |
| TF-044 | Existing report | [spec-kitty #2493](https://github.com/Priivacy-ai/spec-kitty/issues/2493) |
| TF-045 | Existing report; force-category handling explicitly covers hollow-review exclusion | [spec-kitty #1711](https://github.com/Priivacy-ai/spec-kitty/issues/1711) |
| TF-046 | New report | [spec-kitty #2711](https://github.com/Priivacy-ai/spec-kitty/issues/2711) |
| TF-047 | New report | [spec-kitty #2710](https://github.com/Priivacy-ai/spec-kitty/issues/2710) |
| TF-048 | Existing report | [spec-kitty #2343](https://github.com/Priivacy-ai/spec-kitty/issues/2343) |
| TF-049 | New report | [spec-kitty #2709](https://github.com/Priivacy-ai/spec-kitty/issues/2709) |
| TF-050 | New report | [spec-kitty #2705](https://github.com/Priivacy-ai/spec-kitty/issues/2705) |
| TF-051 | New report | [spec-kitty #2708](https://github.com/Priivacy-ai/spec-kitty/issues/2708) |
| TF-052 | New report | [spec-kitty #2704](https://github.com/Priivacy-ai/spec-kitty/issues/2704) |
| TF-053 | Existing report | [E2E #327](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/327) |
| TF-054 | Existing report | [E2E #326](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/326) |
| TF-055 | New report | [E2E #342](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/342) |
| TF-056 | New report; fixed on the mission branch | [spec-kitty #2707](https://github.com/Priivacy-ai/spec-kitty/issues/2707) |
| TF-057 | New report; fixed on the mission branch | [spec-kitty #2706](https://github.com/Priivacy-ai/spec-kitty/issues/2706) |
| TF-058 | Existing machine-readable auth owner | [spec-kitty #681](https://github.com/Priivacy-ai/spec-kitty/issues/681) |
| TF-059 | New report; fixed by E2E PR #340 | [E2E #343](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/343) |
| TF-060 | New report | [E2E #344](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/344) |
| TF-061 | New report; fixed by E2E PR #340 | [E2E #341](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/341) |
| TF-062 | Existing report | [spec-kitty #2157](https://github.com/Priivacy-ai/spec-kitty/issues/2157) |
| TF-063 | Existing report | [spec-kitty #2162](https://github.com/Priivacy-ai/spec-kitty/issues/2162) |
| TF-064 | Existing report | [spec-kitty #2162](https://github.com/Priivacy-ai/spec-kitty/issues/2162) |
| TF-065 | New report, shared missing-endpoint diagnostic root with TF-055 | [E2E #342](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/342) |
| TF-066 | New report, shared target-newer squash-reconciliation root with TF-049 | [spec-kitty #2709](https://github.com/Priivacy-ai/spec-kitty/issues/2709) |
| TF-067 | New report | [E2E #345](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/345) |

## Follow-through

- Product implementation and mission review: [spec-kitty PR #2689](https://github.com/Priivacy-ai/spec-kitty/pull/2689), assigned to `stijn-dejongh`.
- E2E harness repairs: [E2E PR #340](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/pull/340). GitHub does not expose `stijn-dejongh` as assignable in that repository.
- The remaining authenticated SaaS scenario still requires a configured endpoint or a valid human-authored environmental exception; no credential or waiver was fabricated.
