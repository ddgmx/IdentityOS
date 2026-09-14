"""Capability-acquisition provider contract and runtime binding registry.

Capability surfaces can request durable acquisition without importing the
Executive implementation. Bindings retain and compare the actual storage
object so a recycled ``id(storage)`` can never resolve an unrelated provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class AcquisitionProvider(Protocol):
    def request_acquisition(
        self,
        identity_id: str,
        capability_id: str,
        goal: str,
        *,
        original_request: str | None = None,
        priority: int = 0,
        runtime: Any = None,
    ) -> tuple[Any, bool]: ...


@dataclass
class _ProviderBinding:
    storage: Any
    provider: AcquisitionProvider


_PROVIDERS: dict[int, _ProviderBinding] = {}


def register_acquisition_provider(
    storage: Any,
    provider: AcquisitionProvider,
) -> None:
    _PROVIDERS[id(storage)] = _ProviderBinding(storage=storage, provider=provider)


def get_acquisition_provider(storage: Any) -> AcquisitionProvider | None:
    binding = _PROVIDERS.get(id(storage))
    if binding is None:
        return None
    if binding.storage is not storage:
        _PROVIDERS.pop(id(storage), None)
        return None
    return binding.provider


def unregister_acquisition_provider(
    storage: Any,
    provider: AcquisitionProvider,
) -> None:
    binding = _PROVIDERS.get(id(storage))
    if (
        binding is not None
        and binding.storage is storage
        and binding.provider is provider
    ):
        _PROVIDERS.pop(id(storage), None)
