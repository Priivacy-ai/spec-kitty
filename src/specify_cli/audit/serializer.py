"""Deterministic JSON serializer for the audit engine (NFR-001).

Only one public function lives here: ``build_report_json()``.  It is a thin
wrapper around ``RepoAuditReport.to_dict()`` that enforces the formatting
contract — ``sort_keys=True, indent=2`` — so callers never need to remember it.
"""

import json

from .models import RepoAuditReport


def build_report_json(report: RepoAuditReport) -> str:
    """Return a deterministic JSON string for the full audit report.

    Guarantees (NFR-001):
    - ``sort_keys=True`` on all nested dicts
    - missions sorted by mission_slug (enforced by engine before calling this)
    - findings sorted by (artifact_path, code) (enforced by engine)
    - shape_counters sorted by key (enforced by ``RepoAuditReport.to_dict()``)
    - ``indent=2``
    - No timestamps or process-state values in output

    Calling this function twice on the same ``RepoAuditReport`` object must
    produce byte-identical output.
    """
    return json.dumps(report.to_dict(), sort_keys=True, indent=2)
