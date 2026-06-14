"""VS Code extension plugin bundle projection and validation.

The VS Code bundle layout is identical to Copilot's (root ``plugin.json``,
``agents/<profile-id>.agent.md`` agent files, root ``hooks.json`` and
``.mcp.json``); only the ``distribution_target`` label differs. The projector
therefore reuses :class:`CopilotBundleProjector` and overrides the target key.

**Scope guard (FR-016, C-006):** projection writes only staging files under the
caller-supplied ``output_dir`` and returns an inert :class:`PluginBundle`. No
install or marketplace-publish logic is present.
"""

from __future__ import annotations

from .copilot import CopilotBundleProjector
from .model import TARGET_VSCODE


class VsCodeBundleProjector(CopilotBundleProjector):
    """Project + validate VS Code extension bundles (staging only).

    Inherits the Copilot package layout verbatim and only re-labels the
    distribution target.
    """

    distribution_target = TARGET_VSCODE
