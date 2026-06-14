"""Plugin bundle projection and pre-publish validation (WP09).

This sub-package projects the canonical tool surfaces into plugin package
layouts for release/staging distribution targets (Claude Code plugin, Copilot
CLI / VS Code extension) and validates the resulting bundles before they are
published.

**Hard scope limit (FR-015, FR-016, C-006):** this is *projection +
validation only*. Nothing in this package auto-installs a plugin bundle, pushes
to a marketplace, or replaces a project-local installation. The projectors emit
a declarative :class:`~specify_cli.tool_surface.bundles.model.PluginBundle`
descriptor and write staging files under an explicit ``output_dir``; they never
register, enable, or publish anything.
"""

from __future__ import annotations
