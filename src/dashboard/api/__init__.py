"""FastAPI subpackage for the dashboard transport.

Public surface:

    from dashboard.api import create_app

`create_app(project_dir, project_token)` returns a FastAPI app with every
dashboard route registered. The legacy BaseHTTPServer stack remains in tree
under `src/specify_cli/dashboard/handlers/` until a separate retirement
mission removes it. The strangler boundary in
`src/specify_cli/dashboard/server.py` selects between the two stacks via
the `dashboard.transport` config flag.

See `architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md` for
the architectural decision record.
"""
from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
