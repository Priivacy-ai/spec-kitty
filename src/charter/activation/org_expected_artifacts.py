"""Org-tier ``expected-artifacts.yaml`` override (FR-008, WP05).

``MissionTemplateRepository`` (``doctrine/missions/repository.py``) is a
bespoke, single-root reader with no org-tier or project-tier mechanism of any
kind (C-003 forbids restructuring it into a ``BaseDoctrineRepository``
subclass or adding a new method to it). This module is the free-function,
sibling-module seam that gives an org pack a way to override
``<mission_type>/expected-artifacts.yaml`` without touching that class.

Contract C-4 (``kitty-specs/up-org-doctrine-consumers-01M05YAB/contracts/org-tier-resolution-contract.md``):

* **Precedence within ``org_roots``**: last-EXISTING-match wins (the common
  ``org_dirs``-style later-wins convention, NFR-003) — the opposite of
  FR-002's first-match DRG ``org_root`` resolution. FR-008 is new surface
  with no pre-existing first-match precedent to inherit.
* **Precedence vs. built-in**: whole-file replacement, never a field-merge.
  When an org file resolves, callers must not read the built-in file at all
  for that mission type.
* **No built-in baseline required**: a wholly org-defined custom mission
  type is valid input — this helper never consults the built-in tree itself.

Both callers (``charter.activation.mission_type_profiles._resolve_expected_artifacts_slot``
and ``specify_cli.dossier.manifest.ManifestRegistry.load_manifest``) pass
**raw**, existence-filtered org roots (``resolve_org_roots(repo_root)``
filtered to ``.exists()``) — not ``resolve_org_dirs``-style subdir-joined
output — because ``mission_type`` varies per call and cannot be baked into a
fixed ``subdir`` string the way ``"mission_step_contracts"`` or
``"mission_types"`` can.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

__all__ = ["resolve_org_expected_artifacts"]

logger = logging.getLogger(__name__)

_EXPECTED_ARTIFACTS_FILENAME = "expected-artifacts.yaml"


def resolve_org_expected_artifacts(
    org_roots: list[Path], mission_type: str
) -> Mapping[str, Any] | None:
    """Return the parsed org-tier ``expected-artifacts.yaml`` for *mission_type*.

    Checks each *org_roots* entry (already existence-filtered by the caller,
    per this WP's Context section — this helper does not re-check
    ``org_root.exists()`` itself) for
    ``<org_root>/<mission_type>/expected-artifacts.yaml``, in the order
    given. The **last** entry with a parseable matching file wins (NFR-003
    declared-order precedence) — a later ``org_roots`` entry with no
    matching file does not clear an earlier match; only a later *match*
    overrides an earlier one.

    A present org file is a whole-file replacement: it is returned verbatim
    (as a parsed mapping), never merged with the built-in manifest or with
    an earlier org root's file for the same mission type — callers must not
    field-merge the result.

    Returns ``None`` when no *org_roots* entry has a matching, parseable
    file for *mission_type*. A file that exists but fails to parse as a YAML
    mapping is treated the same as "no matching file" for that root (mirrors
    ``MissionTemplateRepository.get_expected_artifacts``'s fail-closed
    behaviour, for consistency with the built-in-tier reader) rather than
    raising — an earlier root's good match, if any, still stands. Unlike
    that pre-existing built-in-tier silence (which covers a path with no
    operator-authored override to lose), a malformed *org* file hides a
    genuine misconfiguration an operator authored and expected to take
    effect — so this case logs a WARNING naming the offending file and the
    parse failure (``logging.warning``, not ``warnings.warn``: the latter
    deduplicates per call site and would drop the signal on repeat calls).
    """
    result: Mapping[str, Any] | None = None
    for org_root in org_roots:
        path = org_root / mission_type / _EXPECTED_ARTIFACTS_FILENAME
        parsed = _read_yaml_mapping(path)
        if parsed is not None:
            result = parsed
    return result


def _read_yaml_mapping(path: Path) -> Mapping[str, Any] | None:
    """Read *path* as a YAML mapping, or ``None`` on any read/parse failure.

    A present-but-unparseable (or non-mapping) file logs a WARNING naming
    *path* and the failure before falling through to ``None`` — see
    :func:`resolve_org_expected_artifacts`'s docstring for why this differs
    from the built-in-tier reader's unlogged fail-closed behaviour.
    """
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        yaml = YAML(typ="safe")
        parsed = yaml.load(content)
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        logger.warning(
            "Org-tier expected-artifacts file %s failed to parse (%s); falling back "
            "as if no org override were present for this mission type.",
            path,
            exc,
        )
        return None
    if not isinstance(parsed, Mapping):
        logger.warning(
            "Org-tier expected-artifacts file %s did not parse to a YAML mapping "
            "(got %s); falling back as if no org override were present for this "
            "mission type.",
            path,
            type(parsed).__name__,
        )
        return None
    return parsed
