# Durable Capability Acquisition

IdentityOS treats capability acquisition as durable work, not as an LLM claim
or a synchronous chat side effect. Registry Manager resolves a requested
capability and submits it through the implementation-neutral
`AcquisitionProvider` contract. Executive is the default provider.

## Runtime setup

`IdentityRuntime(storage=...)` constructs a `CapabilityRegistry`, constructs
Executive over the same storage object, and registers Executive as the
acquisition provider. Installing or reloading Registry Manager binds that same
storage object and the target identity ID.

Callers assembling these components directly must perform the equivalent
registration:

```python
storage = JSONFileBackend(root_dir=".identity_store")
registry = CapabilityRegistry(storage)
executive = ExecutiveRuntime(storage, capability_registry=registry)
register_executive(executive)
registry.install(identity_id, "registry_manager")
registry.grant(identity_id, "registry_manager", "capability:manage")
```

The binding compares the actual storage object, not only its Python object ID.
`executive.shutdown()` unregisters only that exact provider instance.

## Request and status contract

Calling `registry_manager.install_capability` returns one of two truthful
outcomes:

- With a registered provider: `task_id`, `status`, `created`, and the durable
  stage list. `created=false` means the existing active task or an installed,
  completed acquisition was reused.
- Without a provider: `status=ready_to_install` and an explanation that only
  registry resolution occurred. No installation is claimed.

The durable workflow is:

```text
registry_search -> trust -> dependencies -> generate -> validate -> publish
-> install -> activate -> invoke -> persist -> reload -> reuse -> verify_goal
```

Trust and dependency stages apply to marketplace candidates. Generation and
publication apply only when registry search finds no candidate. Validation
always runs. `invoke` and `reuse` execute only capability-declared safe probe
parameters through `CapabilityRegistry.call`, so input validation and permission
checks are identical to normal runtime use.

## Permission blocks

Sensitive permissions are never granted simply to make verification pass. If
the safe probe requires an ungranted scope, the task becomes `blocked` with an
`authorization_required` result. Blocked work is not eligible for scheduler
execution.

Inspect the step result to identify the exact permission, grant it explicitly,
then resume the task. For example:

```bash
identity cap grant command_exec --identity ID --permission process:execute
```

```python
executive.resume_task(identity_id, task_id)
```

An interruption during a non-replay-safe external effect is a different block:
it requires `resolve_interrupted_step` and cannot be resumed as if it were an
authorization wait.

## Failure, rollback, and learning

If a capability newly installed by the task exhausts activation or verification
retries, Executive uninstalls it and records rollback evidence. A capability
that existed before the task is not removed.

Prometheus reconciles only terminal Executive tasks. Success additionally
requires current installed state and completed behavioral proof. Records carry
`source_task_id`; learning and evidence persistence deduplicate that ID
independently, making reconciliation retry-safe across a process interruption.
Queued, running, blocked, stale-completed-without-installation, and model-claimed
successes are never learned as completed acquisitions.

## Troubleshooting

- `ready_to_install`: Registry Manager is not bound to a registered acquisition
  provider for the same storage object.
- `blocked` / `authorization_required`: grant the exact reported scope and
  resume; do not bypass the gateway.
- `failed` / `safe_probe_missing`: the capability must declare harmless
  `verification_params` on at least one skill before automated verification can
  establish behavior.
- `failed` / `dependencies_resolved`: install the reported dependencies; the
  current workflow fails closed rather than silently ignoring them.
- `failed` after install: inspect `acquisition_rolled_back` or
  `acquisition_rollback_failed` evidence before retrying.
