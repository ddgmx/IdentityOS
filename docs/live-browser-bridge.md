# Live Browser Bridge

The Live Browser Bridge lets an IdentityOS agent drive the **user's real,
running Firefox session** instead of the isolated automated browser.

## Architecture

```
IdentityOS  ──spawns──▶  native_host.py (RELAY)
                              │  Unix socket
Firefox     ──spawns──▶  native_host.py (SERVER) ◀── WebExtension (browser_extension/)
```

- The Firefox-spawned host (**SERVER** role) owns the live tab state pushed
  by the WebExtension and binds a per-user Unix socket.
- The IdentityOS-spawned host (**RELAY** role) forwards capability requests
  over that socket to the server.
- Messages are length-prefixed JSON frames
  (`<4-byte little-endian length><json>`). All pipe/socket reads and writes
  use exact-read/exact-write helpers because `read(n)`/`recv(n)` may return
  fewer bytes than requested for frames that exceed the OS buffer.

Socket path: `$TMPDIR/identityos_live_bridge_<uid>.sock`.
Override with `IDENTITYOS_BRIDGE_SOCKET`.

## Installation

1. Run `browser_extension/install.sh` to install the native messaging host
   into `~/.mozilla/native-messaging-hosts/` and build a zip for loading.
2. In Firefox, open `about:debugging` → **This Firefox** → **Load Temporary
   Add-on** and select the built zip.
3. Click the IdentityOS extension icon and **Connect to IdentityOS**.
4. The extension auto-reconnects if the native host restarts.

## Usage

Ask an agent about the live session, for example:

```
identity chat --id comet
# "Which tabs do I have open in my browser?"
```

Live skills are exposed under `browser.live.*` and require the
`browser:live_read` / `browser:live_tabs` / `browser:live_write` scopes,
which are granted by default. The generic `browser.*` skills target the
isolated automated session and are intentionally distinct.

## Credential safety

Credential-sensitive arguments are brokered as `secret-ref://` references
and may only be resolved by credential-aware skills such as `browser.login`.
Generic automation skills (fill/type/eval_js) reject secret references.
See `runtime/sensitive.py` and `docs/architecture/pr-102-changes.md`.

## Configuration

Multiple OpenAI-compatible providers may be configured purely through the
environment; the runtime builds a deterministic fallback chain
(`adapters/configuration.py`):

```bash
OPENAI_API_KEY=...                                  # legacy OpenAI
OPENAI_GEMINI_API_KEY=... OPENAI_GEMINI_BASE_URL=...# named provider
GROQ_API_KEY=... OPENROUTER_API_KEY=...             # other providers
IDENTITY_ADAPTER=openai                             # explicit selection
```

Existing single-provider setups keep working unchanged.