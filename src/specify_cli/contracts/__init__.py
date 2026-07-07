"""Contract Registry: the modeled, owned artifact for shared contracts (#2441).

A **Contract Record** models a shared contract — a fallback/compat name or a
retired literal a caller depended on — together with its **declared consumer
set** and its retirement obligations, in one schema-validated, owned manifest
(``docs/contracts/contract-registry.yaml``). It generalises the proven
shim-registry chain (:mod:`specify_cli.compat.registry`), which modeled only the
``fallback_name`` kind and carried no consumer set.

Public surface (re-exported for ergonomic ``from specify_cli.contracts import``
access; the enforcing well-formedness gate is ``spec-kitty doctor contracts``):

* :class:`~specify_cli.contracts.registry.ContractRecord` and its parts
  (``ContractAnchor`` / ``ContractRetirement`` / ``ContractConsumers`` /
  ``ContractVerification``)
* :func:`~specify_cli.contracts.registry.load_registry` /
  :func:`~specify_cli.contracts.registry.validate_registry` /
  :func:`~specify_cli.contracts.registry.check_contract_registry`
* :class:`~specify_cli.contracts.registry.ContractRegistryReport` /
  :class:`~specify_cli.contracts.registry.ContractRegistrySchemaError`
* :func:`~specify_cli.contracts.anchoring.composite_key` — the shared
  content-anchoring primitive (also re-exported by
  ``tests.architectural._ratchet_keys``).
"""

from __future__ import annotations

from specify_cli.contracts.anchoring import (
    composite_key as composite_key,
    is_file_line_anchor as is_file_line_anchor,
)
from specify_cli.contracts.registry import (
    ContractAnchor as ContractAnchor,
    ContractConsumers as ContractConsumers,
    ContractRecord as ContractRecord,
    ContractRegistryReport as ContractRegistryReport,
    ContractRegistrySchemaError as ContractRegistrySchemaError,
    ContractRetirement as ContractRetirement,
    ContractVerification as ContractVerification,
    check_contract_registry as check_contract_registry,
    load_registry as load_registry,
    resolve_contract_registry_path as resolve_contract_registry_path,
    validate_registry as validate_registry,
)
