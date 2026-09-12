# Contract: Proportional CI Routing

Every changed narrow test class has exactly one `owner` route. Secondary execution in coverage, platform, or hard-gate routes is allowed and recorded by role. Narrow stable classes use an explicit path/manifest; whole-tree marker discovery is prohibited when the owned path set is known. Accepted P0 reproductions remain blocking owner-route reds under the red-main ADR until fixed.

Route changes must preserve a frozen mapping:

| Base route | Base universe | HEAD route | Mapping reason | Required |
|------------|---------------|------------|----------------|----------|

Validation must prove:

1. every expected node has exactly one owner in each changed narrow class, while documented secondary-role overlap remains valid;
2. no retained P0 reproduction self-skips, xfails, quarantines, or retries;
3. an empty route is explicit and green only when its owned manifest is empty;
4. deleted/renamed routes remain in performance denominators through the mapping;
5. base/HEAD commands use identical runner, Python, workers, environment, install, and cache policy;
6. summed compute and critical-path wall-clock are reported separately.
