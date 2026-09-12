# Tracer: Tooling Friction — Charter Authority Flip (M1)

- SaaS sync store locks on `mission create` (daemon boundary); ran with `SPEC_KITTY_ENABLE_SAAS_SYNC=0 SAAS_SYNC=0`. Scaffold committed regardless.
- `spec-kitty` subcommands require `--mission charter-authority-flip-01M14RB3` (433 missions in tree).
- Auth-2 glossary pack regen script (`scratchpad/migrate_glossary_pack.py`) is not git-tracked / gone → pack is hand-edited with `test_glossary_pack_parity` as the byte-parity net.
- Stale exemption path `src/doctrine/glossary_packs/built-in/` in `test_no_legacy_terminology.py:61,428` points at a non-existent dir (pack moved to `packs/built-in/glossary_packs/`).

## Implement log
- (append per friction)
