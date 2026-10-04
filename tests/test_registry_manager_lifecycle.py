"""Direct contracts for Registry Manager's durable acquisition boundary."""

from __future__ import annotations

import importlib

from core.acquisition import (
    get_acquisition_provider,
    register_acquisition_provider,
    unregister_acquisition_provider,
)
from core.capabilities.registry import CapabilityRegistry
from core.capabilities.registry_manager import RegistryManagerCapability
from core.executive import ExecutiveRuntime
from core.executive.engine import (
    get_executive_for,
    register_executive,
)
from core.executive.models import Task, TaskStatus, TaskStep
from runtime.persistence import InMemoryBackend, JSONFileBackend


class _RecordingProvider:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def request_acquisition(
        self,
        identity_id: str,
        capability_id: str,
        goal: str,
        **kwargs,
    ) -> tuple[Task, bool]:
        self.requests.append({
            "identity_id": identity_id,
            "capability_id": capability_id,
            "goal": goal,
            **kwargs,
        })
        task = Task(
            task_id="recorded-task",
            goal=goal,
            identity_id=identity_id,
            capability_id=capability_id,
            status=TaskStatus.QUEUED,
            steps=[TaskStep(action="install", description="Install")],
        )
        return task, True


def test_bound_manager_without_provider_returns_truthful_resolution_only():
    storage = InMemoryBackend()
    manager = RegistryManagerCapability()
    manager.install("fallback-identity", storage)

    result = manager.call(
        "registry_manager.install_capability",
        cap_id="calc",
    )

    assert result.success is True
    assert result.data["status"] == "ready_to_install"
    assert "no durable Executive" in result.data["message"]
    assert "task_id" not in result.data


def test_bound_manager_requests_work_through_acquisition_provider():
    storage = InMemoryBackend()
    provider = _RecordingProvider()
    register_acquisition_provider(storage, provider)
    try:
        manager = RegistryManagerCapability()
        manager.install("provider-identity", storage)

        result = manager.call(
            "registry_manager.install_capability",
            cap_id="calc",
        )

        assert result.success is True
        assert result.data["status"] == "queued"
        assert result.data["task_id"] == "recorded-task"
        assert result.data["created"] is True
        assert provider.requests[0]["identity_id"] == "provider-identity"
        assert provider.requests[0]["capability_id"] == "calc"
    finally:
        unregister_acquisition_provider(storage, provider)


def test_provider_and_executive_unregister_only_exact_instance():
    storage = InMemoryBackend()
    first = ExecutiveRuntime(storage=storage)
    second = ExecutiveRuntime(storage=storage)
    register_executive(first)
    register_executive(second)

    first.shutdown()
    assert get_executive_for(storage) is second
    assert get_acquisition_provider(storage) is second

    second.shutdown()
    assert get_executive_for(storage) is None
    assert get_acquisition_provider(storage) is None


def test_registry_manager_completes_full_lifecycle(tmp_path):
    storage = JSONFileBackend(root_dir=str(tmp_path / "store"))
    registry = CapabilityRegistry(storage)
    executive = ExecutiveRuntime(storage=storage, capability_registry=registry)
    register_executive(executive)
    registry.install("durable-identity", "registry_manager")
    registry.grant(
        "durable-identity",
        "registry_manager",
        "capability:manage",
    )

    queued = registry.call(
        "durable-identity",
        "registry_manager.install_capability",
        cap_id="calc",
    )
    for _ in range(100):
        executive.process_ready("durable-identity")
        task = executive.get_task("durable-identity", queued.data["task_id"])
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED):
            break

    assert task.status == TaskStatus.COMPLETED, task.error
    assert registry.get("durable-identity", "calc") is not None
    assert task.step_by_id("invoke").result["invoked"] is True
    assert task.step_by_id("persist").result["persisted"] is True
    assert task.step_by_id("reload").result["reloaded"] is True
    assert task.step_by_id("reuse").result["reused"] is True
    executive.shutdown()


def test_acquisition_contract_imports_without_cycle():
    for module in (
        "core.acquisition",
        "core.capabilities.registry_manager",
        "core.executive.engine",
        "core.prometheus.engine",
        "runtime.orchestrator",
    ):
        assert importlib.import_module(module) is not None
