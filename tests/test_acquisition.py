"""Unit contracts for acquisition-provider registration."""

from __future__ import annotations

from core.acquisition import AcquisitionProviderRegistry
from runtime.persistence import InMemoryBackend


class _Provider:
    def request_acquisition(self, *args, **kwargs):
        raise AssertionError("Registration tests must not dispatch work")


def test_registry_registers_gets_and_unregisters_only_exact_provider():
    registry = AcquisitionProviderRegistry()
    storage = InMemoryBackend()
    first = _Provider()
    second = _Provider()

    registry.register(storage, first)
    assert registry.get(storage) is first

    registry.register(storage, second)
    registry.unregister(storage, first)
    assert registry.get(storage) is second

    registry.unregister(storage, second)
    assert registry.get(storage) is None


def test_registry_rejects_stale_binding_when_object_id_is_reused():
    registry = AcquisitionProviderRegistry()
    old_storage = InMemoryBackend()
    current_storage = InMemoryBackend()
    provider = _Provider()
    registry.register(old_storage, provider)

    # Simulate the only dangerous part of CPython ID recycling: a stale
    # binding now occupying the numeric key assigned to a different object.
    stale = registry._bindings.pop(id(old_storage))
    registry._bindings[id(current_storage)] = stale

    assert registry.get(current_storage) is None
    assert id(current_storage) not in registry._bindings

