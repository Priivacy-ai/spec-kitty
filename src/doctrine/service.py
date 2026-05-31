"""Doctrine service for lazy access to all doctrine repositories."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from doctrine.shared.scoping import normalize_languages
from doctrine.agent_profiles import AgentProfileRepository
from doctrine.directives import DirectiveRepository
from doctrine.missions.step_contracts import MissionStepContractRepository
from doctrine.paradigms import ParadigmRepository
from doctrine.procedures import ProcedureRepository
from doctrine.styleguides import StyleguideRepository
from doctrine.tactics import TacticRepository
from doctrine.toolguides import ToolguideRepository


class DoctrineService:
    """Lazy aggregation service for doctrine repositories."""

    def __init__(
        self,
        built_in_root: Path | None = None,
        project_root: Path | None = None,
        org_roots: list[Path] | None = None,
        active_languages: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self._built_in_root = built_in_root
        self._project_root = project_root
        self._org_roots = org_roots or []
        self._active_languages = None if active_languages is None else normalize_languages(active_languages)
        self._cache: dict[str, object] = {}

    def _built_in_dir(self, artifact: str) -> Path | None:
        if self._built_in_root is None:
            return None
        return self._built_in_root / artifact / "built-in"

    def _project_dir(self, artifact: str) -> Path | None:
        if self._project_root is None:
            return None
        return self._project_root / artifact

    def _org_dirs(self, artifact: str) -> list[Path]:
        """Return per-pack org-layer directories for *artifact* in declaration order.

        Each configured org root contributes one directory: ``<org_root>/<artifact>``.
        Repositories iterate this list in order, so later packs override earlier ones
        for the same artifact ID (FR-006, C-004). Non-existent directories are
        retained in the returned list; existence checks happen at load time.
        """
        return [root / artifact for root in self._org_roots]

    @property
    def directives(self) -> DirectiveRepository:
        if "directives" not in self._cache:
            self._cache["directives"] = DirectiveRepository(
                built_in_dir=self._built_in_dir("directives"),
                org_dirs=self._org_dirs("directives"),
                project_dir=self._project_dir("directives"),
            )
        return cast(DirectiveRepository, self._cache["directives"])

    @property
    def tactics(self) -> TacticRepository:
        if "tactics" not in self._cache:
            self._cache["tactics"] = TacticRepository(
                built_in_dir=self._built_in_dir("tactics"),
                org_dirs=self._org_dirs("tactics"),
                project_dir=self._project_dir("tactics"),
                active_languages=self._active_languages,
            )
        return cast(TacticRepository, self._cache["tactics"])

    @property
    def styleguides(self) -> StyleguideRepository:
        if "styleguides" not in self._cache:
            self._cache["styleguides"] = StyleguideRepository(
                built_in_dir=self._built_in_dir("styleguides"),
                org_dirs=self._org_dirs("styleguides"),
                project_dir=self._project_dir("styleguides"),
                active_languages=self._active_languages,
            )
        return cast(StyleguideRepository, self._cache["styleguides"])

    @property
    def toolguides(self) -> ToolguideRepository:
        if "toolguides" not in self._cache:
            self._cache["toolguides"] = ToolguideRepository(
                built_in_dir=self._built_in_dir("toolguides"),
                org_dirs=self._org_dirs("toolguides"),
                project_dir=self._project_dir("toolguides"),
                active_languages=self._active_languages,
            )
        return cast(ToolguideRepository, self._cache["toolguides"])

    @property
    def paradigms(self) -> ParadigmRepository:
        if "paradigms" not in self._cache:
            self._cache["paradigms"] = ParadigmRepository(
                built_in_dir=self._built_in_dir("paradigms"),
                org_dirs=self._org_dirs("paradigms"),
                project_dir=self._project_dir("paradigms"),
            )
        return cast(ParadigmRepository, self._cache["paradigms"])

    @property
    def procedures(self) -> ProcedureRepository:
        if "procedures" not in self._cache:
            self._cache["procedures"] = ProcedureRepository(
                built_in_dir=self._built_in_dir("procedures"),
                org_dirs=self._org_dirs("procedures"),
                project_dir=self._project_dir("procedures"),
                active_languages=self._active_languages,
            )
        return cast(ProcedureRepository, self._cache["procedures"])

    @property
    def mission_step_contracts(self) -> MissionStepContractRepository:
        if "mission_step_contracts" not in self._cache:
            self._cache["mission_step_contracts"] = MissionStepContractRepository(
                built_in_dir=self._built_in_dir("mission_step_contracts"),
                org_dirs=self._org_dirs("mission_step_contracts"),
                project_dir=self._project_dir("mission_step_contracts"),
            )
        return cast(MissionStepContractRepository, self._cache["mission_step_contracts"])

    @property
    def agent_profiles(self) -> AgentProfileRepository:
        if "agent_profiles" not in self._cache:
            self._cache["agent_profiles"] = AgentProfileRepository(
                built_in_dir=self._built_in_dir("agent_profiles"),
                org_dirs=self._org_dirs("agent_profiles"),
                project_dir=self._project_dir("agent_profiles"),
                active_languages=self._active_languages,
            )
        return cast(AgentProfileRepository, self._cache["agent_profiles"])
