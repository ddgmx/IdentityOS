"""Permission grants must change only through manager methods."""

from core.permissions import PermissionManager, PermissionPolicy


def test_deserialized_input_cannot_mutate_grants():
    source = {"allowed": [], "denied": [], "roles": [], "metadata": {"audit": []}}
    manager = PermissionManager.from_dict(source)
    source["allowed"].append("delete:records")
    source["roles"].append("admin")
    source["metadata"]["audit"].append("changed")
    assert not manager.check("delete:records")
    assert not manager.check("read:records")
    assert manager.to_dict()["metadata"] == {"audit": []}


def test_exported_views_cannot_mutate_grants():
    manager = PermissionManager()
    manager.grant("read:records")
    exported = manager.to_dict()
    summary = manager.list_permissions()
    exported["allowed"].append("delete:records")
    summary["allowed"].clear()
    assert manager.check("read:records")
    assert not manager.check("delete:records")


def test_policy_supplied_to_manager_is_snapshotted():
    policy = PermissionPolicy(allowed=["read:records"])
    manager = PermissionManager(policy)
    policy.allowed.append("delete:records")
    assert manager.check("read:records")
    assert not manager.check("delete:records")


def test_nested_metadata_is_detached_both_directions():
    source = {"metadata": {"audit": [{"details": ["original"]}]}}
    manager = PermissionManager.from_dict(source)
    source["metadata"]["audit"][0]["details"].append("input edit")
    exported = manager.to_dict()
    exported["metadata"]["audit"][0]["details"].append("output edit")
    assert manager.to_dict()["metadata"] == {"audit": [{"details": ["original"]}]}
