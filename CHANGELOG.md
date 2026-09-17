# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- **Live Firefox bridge** (`browser.live.*`): identities can drive the user's
  real Firefox through the `@identityos/live-browser-bridge` WebExtension and
  native messaging host. See `docs/live-browser-bridge.md` for setup, usage,
  and security boundaries.
- **Named OpenAI-compatible providers**: configure multiple endpoints at once
  with `OPENAI_<NAME>_API_KEY`, `OPENAI_<NAME>_BASE_URL`, and
  `OPENAI_<NAME>_MODEL`. Providers are discovered side-effect-free from the
  environment. `list_configured_openai_providers()` returns the configured
  providers (name, display_name, base_url, model, is_local) for UI selection.
  See `docs/openai_providers.md`.

### Changed

- **Backward compatibility kept**: legacy `OPENAI_API_KEY`, `OPENAI_BASE_URL`,
  `OPENAI_MODEL`, `OLLAMA_API_KEY`, and `OLLAMA_MODEL` still select the
  `openai`/`ollama` providers exactly as before.
- **Credential brokering**: model tool calls must supply credentials as
  ephemeral `secret-ref://` references. Only credential-aware skills such as
  `browser.login` may resolve them; generic automation (`browser.fill`,
  `browser.eval_js`, ...) rejects them.