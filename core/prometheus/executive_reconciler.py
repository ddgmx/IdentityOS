"""Reconcile durable Executive acquisition outcomes into Prometheus memory.

Executive establishes what actually ran. Prometheus consumes those terminal
facts and learns from them; it never upgrades a queued task or model claim to
an acquisition success.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.executive.models import Task, TaskStatus, TaskStepStatus
from core.prometheus.models import (
    AcquisitionMode,
    AcquisitionRecord,
    AcquisitionStatus,
    CapabilityNeed,
    RegistryCandidate,
)
from core.prometheus.stages.evidence_recorder import record_evidence
from core.prometheus.stages.learner import record_acquisition


def reconcile_executive_acquisitions(
    identity_id: str,
    executive: Any,
    storage: Any,
) -> list[str]:
    """Persist terminal Executive acquisition outcomes exactly once."""
    if executive is None or storage is None:
        return []
    reconciled: list[str] = []
    for task in executive.store.load_terminal(identity_id):
        if not task.capability_id:
            continue
        record = _record_from_task(task, executive)
        learned = record_acquisition(identity_id, record, storage)
        evidenced = record_evidence(identity_id, record, storage)
        if learned or evidenced:
            reconciled.append(task.task_id)
    return reconciled


def _record_from_task(task: Task, executive: Any) -> AcquisitionRecord:
    search = task.step_by_id("registry_search")
    manifest = (
        search.result.get("manifest", {})
        if search is not None and isinstance(search.result, dict)
        else {}
    )
    if not isinstance(manifest, dict):
        manifest = {}
    resolved_id = (
        search.result.get("candidate")
        if search is not None and search.result.get("candidate")
        else task.capability_id
    )
    installed_cap = None
    registry = getattr(executive, "capability_registry", None)
    if registry is not None:
        try:
            installed_cap = registry.get(task.identity_id, resolved_id)
        except Exception:
            installed_cap = None

    skills = manifest.get("skills", [])
    if not skills and installed_cap is not None:
        skills = [
            {
                "name": skill.name,
                "description": skill.description,
                "permission": skill.permission,
            }
            for skill in installed_cap.skills()
        ]
    permissions = manifest.get("permissions", {})
    if not isinstance(permissions, dict):
        permissions = {}
    candidate = RegistryCandidate(
        cap_id=resolved_id,
        name=manifest.get("name") or getattr(installed_cap, "name", resolved_id),
        version=manifest.get("version") or getattr(installed_cap, "version", "0.0.0"),
        author=manifest.get("author") or getattr(installed_cap, "author", "unknown"),
        description=manifest.get("description") or getattr(installed_cap, "description", ""),
        skills=skills,
        permissions=permissions,
        dependencies=manifest.get("dependencies", []),
        manifest_url=f"registry/capabilities/{resolved_id}/manifest.json",
    )

    trust = task.step_by_id("trust")
    if trust is not None:
        candidate.trust_score = float(trust.result.get("score", 0.0) or 0.0)
    proof_steps = [
        step for step in task.steps
        if step.action in ("invoke", "persist", "reload", "reuse", "verify")
    ]
    proof_complete = bool(proof_steps) and all(
        step.status in (TaskStepStatus.COMPLETED, TaskStepStatus.SKIPPED)
        for step in proof_steps
    )
    installed = installed_cap is not None
    succeeded = (
        task.status == TaskStatus.COMPLETED
        and installed
        and proof_complete
    )
    rolled_back = any(
        evidence.label == "acquisition_rolled_back" and evidence.success
        for evidence in task.evidence
    )
    if succeeded:
        status = AcquisitionStatus.SUCCEEDED
    elif rolled_back:
        status = AcquisitionStatus.ROLLED_BACK
    else:
        status = AcquisitionStatus.FAILED

    need = CapabilityNeed(
        capability_id=resolved_id,
        skill_keywords=[task.capability_id or resolved_id],
        confidence=1.0,
        source="executive_task",
        original_request=task.original_request or task.goal,
        suggested_capability_ids=[resolved_id],
    )
    return AcquisitionRecord(
        need=need,
        status=status,
        candidates_found=[candidate] if search and search.result.get("found") else [],
        chosen_candidate=candidate,
        trust_score=candidate.trust_score,
        installation_success=installed,
        validation_success=proof_complete,
        retry_success=succeeded,
        duration_ms=_duration_ms(task),
        error=None if succeeded else (task.error or "Executive acquisition did not establish a reusable capability."),
        identity_id=task.identity_id,
        mode=AcquisitionMode.AUTOMATIC,
        source_task_id=task.task_id,
    )


def _duration_ms(task: Task) -> float:
    try:
        start = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(task.last_updated.replace("Z", "+00:00"))
        return max(0.0, (end - start).total_seconds() * 1000)
    except (TypeError, ValueError):
        return 0.0
