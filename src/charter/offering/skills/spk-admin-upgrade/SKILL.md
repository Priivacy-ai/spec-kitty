---
name: spk-admin-upgrade
description: "Upgrade Spec Kitty installations and repair generated commands, skills, migrations, and compatibility shims."
---

# spk-admin-upgrade

Use this skill when the user asks to upgrade Spec Kitty or repair stale
generated assets after a version change.

## Flow

1. Identify installed version and project version.
2. Run the supported upgrade command.
3. Review migration output for command and skill repairs.
4. Re-run setup/doctor checks with `spk-admin-setup-doctor`.
5. Do not edit generated installed skills directly; update source skills or
   command templates.

## Rule

Treat upgrade output as a migration report. Fix the underlying source only when
the migration reveals a real product defect.
