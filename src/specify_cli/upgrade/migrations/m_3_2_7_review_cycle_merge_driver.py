"""Migration 3.2.7: install the review-cycle-*.md refuse-fail-closed merge driver.

Sibling of ``m_3_1_1_event_log_merge_driver.py`` (status.events.jsonl) and
``m_3_2_6_decisions_event_log_merge_driver.py`` (decisions.events.jsonl):
review-cycle-verdict-seam-rebuild-01KZ2W7W WP18/T079 registers
``spec-kitty-review-cycle`` for already-initialized (upgraded) consumer
clones, the same way those two migrations registered ``spec-kitty-event-log``.

**Module name vs. ``target_version`` (deliberately not the same number).**
This module is named ``m_3_2_7_...`` (the WP's prescribed filename/id), but
``target_version`` below is pinned to ``"3.2.6"`` -- the same reasoning
``m_3_2_6_issue_matrix_driver_repoint.py`` documents: the installed package
on this branch is still ``3.2.6`` (``pyproject.toml``,
``CHANGELOG.md``'s still-open "Unreleased - 3.2.6" section), and
``spec-kitty upgrade``/``test_discovered_migration_targets_do_not_exceed_
package_version`` skip/flag any migration whose ``target_version`` exceeds
the installed package version -- targeting the unreleased ``3.2.7`` would
mean this migration silently never runs for a user upgrading to the current
release.

Unlike its siblings, the driver this migration seeds does NOT union or
field-merge -- ``merge_driver_review_cycle`` (see that function's docstring
in ``cli/commands/merge_driver.py``) refuses fail-closed on a genuine
two-verdict collision under one ``review-cycle-N.md`` filename, embedding
both raw documents verbatim inside conflict markers rather than fabricating
a blended verdict. This migration only wires the *registration* surfaces
(``.gitattributes`` entry + local git config); the reconciliation semantics
live entirely in the driver command it points at.

**Command form (T079 design question -- what a real, non-dev-clone consumer
sees):** this migration writes the bare ``spec-kitty merge-driver-review-cycle
%O %A %B`` command, byte-identical in shape to every existing driver's
``command=`` string in ``specify_cli.lanes.merge._MERGE_DRIVERS``, and
deliberately does NOT hardcode a ``.venv``-relative or otherwise
environment-specific interpreter path. A migration cannot know a consumer's
install layout at write time, but it does not need to: a real consumer
installs Spec Kitty via ``pip``/``pipx`` (not as a sibling dev checkout of
this monorepo), so plain ``spec-kitty`` resolves correctly off that
consumer's own ``PATH`` -- there is no shadow-clone collision to route
around outside this repository's own multi-clone development setup. The
PATH-shadowing hazard this mission's own dev environment hit (a second local
clone's editable install pre-empting this one on ``PATH``) is addressed at
merge-execution time instead, by ``lanes/merge.py::_make_merge_env`` (which
prepends the CURRENT process's ``sys.executable``-derived venv ``bin/`` to
``PATH`` for every merge subprocess) -- not by this migration baking in an
absolute path that would be wrong on every machine except the one that
authored it.
"""

from __future__ import annotations

from ..registry import MigrationRegistry
from ._merge_driver_seeding import DriverSpec, MergeDriverSeedingMigration

_DRIVERS: tuple[DriverSpec, ...] = (
    DriverSpec(
        config_key="spec-kitty-review-cycle",
        name="Spec Kitty review-cycle verdict collision refusal",
        command="spec-kitty merge-driver-review-cycle %O %A %B",
        pattern="kitty-specs/**/tasks/*/review-cycle-*.md",
    ),
)


@MigrationRegistry.register
class ReviewCycleMergeDriverMigration(MergeDriverSeedingMigration):
    """Install the git merge driver for review-cycle-*.md (T017/T079)."""

    migration_id = "3.2.7_review_cycle_merge_driver"
    description = "Install a fail-closed git merge driver for review-cycle-*.md"
    target_version = "3.2.6"
    drivers = _DRIVERS
    dry_run_summary = "Would install the review-cycle-*.md merge driver and .gitattributes entry"
