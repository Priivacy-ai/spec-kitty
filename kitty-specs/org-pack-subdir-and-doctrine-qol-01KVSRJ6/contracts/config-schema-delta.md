# Contract Delta — org-pack config schema (`subdir`)

Target contract file (FR-008): `kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml`
(currently `additionalProperties: false` on each pack item, with no `subdir`).

## `.kittify/config.yaml` — canonical shape (`doctrine.org.packs[]`)

```yaml
# round-trip: skip: canonical .kittify/config.yaml shape sketch — executable single-pack OrgPackConfig round-trip examples are in the "Round-trip example" section below
doctrine:
  org:
    packs:
      - name: my-pack
        source_type: git
        url: ssh://git@example.com/org/repo.git
        ref: main
        local_path: .doctrine-cache/repo   # clone root (unchanged)
        subdir: pack                        # NEW — effective pack root = .doctrine-cache/repo/pack
```

## Field contract

| Property | Type | Required | Rule |
|----------|------|----------|------|
| `subdir` | string | no | Relative path beneath `local_path`. Rejected: absolute (incl. Windows/UNC), any `..` component. `.`/empty ≡ absent. Effective pack root = `local_path / subdir`. Clone target stays `local_path` (C-003). |

## Behavioral contract (acceptance anchors)

- `OrgPackConfig.effective_root(repo_root)` returns `local_path/subdir` when set, else repo-root-normalized `local_path` (FR-001/FR-002).
- A git-sourced pack with `org-charter.yaml` + `drg/fragment.yaml` under `pack/` and `subdir: pack` → `doctor doctrine` reports **healthy** (SC-001).
- `doctrine fetch` reports artifact count at the effective root; a wrong `subdir` → "0 artifacts" at fetch (SC-003/FR-007).
- Round-trip: write→read preserves `subdir`; absent emits no `subdir:` key (FR-005), on both canonical and legacy inline shapes (FR-006).
- Escape inputs → structured operator-visible error, not "no org packs" degradation (FR-003).

## Round-trip example (FR-140)

A single pack entry is carried by the `OrgPackConfig` Pydantic model
(`doctrine.drg.org_pack_config.OrgPackConfig`). The frontmatter below pins the
contract example to that model for the round-trip gate. A pack that sets the new
`subdir` field round-trips as valid:

```yaml
# pydantic_model: doctrine.drg.org_pack_config.OrgPackConfig
# expect: valid
name: my-pack
source_type: git
url: ssh://git@example.com/org/repo.git
ref: main
local_path: .doctrine-cache/repo
subdir: pack
```

A `subdir` containing a `..` component escapes `local_path` and is rejected at
model-construction time (per the field contract above):

```yaml
# pydantic_model: doctrine.drg.org_pack_config.OrgPackConfig
# expect: invalid
# expect_message: subdir must not contain
name: my-pack
local_path: .doctrine-cache/repo
subdir: ../escape
```
