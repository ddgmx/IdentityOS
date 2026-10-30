# Permission state snapshots

`PermissionManager` owns its authorization state. It copies a supplied
`PermissionPolicy` at construction, copies input to `from_dict`, and returns
detached values from `to_dict` and `list_permissions`. Editing any of those
external objects will not grant or revoke a permission on a running manager.

Use `grant`, `deny`, `revoke`, `assign_role`, and `unassign_role` to change live
authorization. Code that previously mutated a source policy or serialized
dictionary after constructing the manager must switch to those methods.

The small scope lists are copied directly; metadata is deep-copied because it
can contain nested mutable values. Large metadata structures therefore incur a
copy cost during construction and serialization. Keep authorization metadata
small and move large records to ordinary storage.
