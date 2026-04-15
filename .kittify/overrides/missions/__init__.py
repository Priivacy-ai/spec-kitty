"""Mission framework package."""

from .action_index import ActionIndex, load_action_index
from .primitives import PrimitiveExecutionContext
from .glossary_hook import execute_with_glossary
from .repository import MissionTemplateRepository, TemplateResult, ConfigResult

# Backward-compat alias for shipped migrations and existing imports
MissionRepository = MissionTemplateRepository

__all__ = [
    "ActionIndex",
    "load_action_index",
    "PrimitiveExecutionContext",
    "execute_with_glossary",
    "MissionTemplateRepository",
    "MissionRepository",  # alias
    "TemplateResult",
    "ConfigResult",
]
