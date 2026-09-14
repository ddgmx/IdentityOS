"""Capability-acquisition provider contract and runtime binding registry.

Capability surfaces can request durable acquisition without importing the
Executive implementation. Bindings retain and compare the actual storage
object so a recycled ``id(storage)`` can never resolve an unrelated provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
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


class AcquisitionProviderRegistry:
    """Thread-safe, identity-based registry for acquisition providers.

    Bindings are strongly held to preserve the existing active-Executive
    contract. Runtime owners must call ``shutdown``; exact-instance removal and
    referent checks prevent one runtime or a recycled object ID from affecting
    another binding.
    """

    def __init__(self) -> None:
        self._bindings: dict[int, _ProviderBinding] = {}
        self._lock = RLock()

    def register(self, storage: Any, provider: AcquisitionProvider) -> None:
        key = id(storage)
        with self._lock:
            self._bindings[key] = _ProviderBinding(
                storage=storage,
                provider=provider,
            )

    def get(self, storage: Any) -> AcquisitionProvider | None:
        key = id(storage)
        with self._lock:
            binding = self._bindings.get(key)
            if binding is None:
                return None
            if binding.storage is not storage:
                self._bindings.pop(key, None)
                return None
            return binding.provider

    def unregister(self, storage: Any, provider: AcquisitionProvider) -> None:
        key = id(storage)
        with self._lock:
            binding = self._bindings.get(key)
            if (
                binding is not None
                and binding.storage is storage
                and binding.provider is provider
            ):
                self._bindings.pop(key, None)


_PROVIDERS = AcquisitionProviderRegistry()


def register_acquisition_provider(
    storage: Any,
    provider: AcquisitionProvider,
) -> None:
    _PROVIDERS.register(storage, provider)


def get_acquisition_provider(storage: Any) -> AcquisitionProvider | None:
    return _PROVIDERS.get(storage)


def unregister_acquisition_provider(
    storage: Any,
    provider: AcquisitionProvider,
) -> None:
    _PROVIDERS.unregister(storage, provider)
