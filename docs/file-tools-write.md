# File write result and failure behavior

`file_tools.write_file` writes UTF-8 text to an allowed workspace path. It stages
the complete content in the destination directory, flushes it, and replaces the
destination only after the staging write succeeds. If staging or replacement
fails, the previous destination remains intact and the staging file is removed.

Successful calls retain `status: "created"` for existing consumers. The new
`operation` field is `created` for a new path and `replaced` for an existing
path. `bytes_written` counts UTF-8 bytes, including multibyte characters.

The replacement requires a writable destination directory and a filesystem
that supports `os.replace`. A failed replacement returns a failed capability
result; callers should inspect `success` before trusting the result data.
