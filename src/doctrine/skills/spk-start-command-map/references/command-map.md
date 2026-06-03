# Command Map

| User intent | Command | Operating skill |
|---|---|---|
| Start or revise a specification | `/spec-kitty.specify` | `spk-mission-specify` |
| Research before specification | `/spec-kitty.research` | `spk-mission-research` |
| Create an implementation plan | `/spec-kitty.plan` | `spk-mission-plan` |
| Create tasks or work packages | `/spec-kitty.tasks*` | `spk-mission-tasks` |
| Implement assigned work | `/spec-kitty.implement` or `next` output | `spk-run-next` |
| Review a work package | `/spec-kitty.review` or review lane output | `spk-run-review-wp` |
| Accept completed mission | `/spec-kitty.accept` | `spk-gate-accept` |
| Merge mission work | `/spec-kitty.merge` | `spk-gate-merge` |
| Inspect current state | `/spec-kitty.status` | `spk-run-next` or `spk-admin-dashboard` |
| Open mission dashboard | `/spec-kitty.dashboard` | `spk-admin-dashboard` |
| Charter/governance work | `/spec-kitty.charter` | `spk-doctrine-charter` |

Generated command skills are named `spec-kitty.<command>` for slash-command
compatibility. Operating skills are named `spk-*` for user discovery.
