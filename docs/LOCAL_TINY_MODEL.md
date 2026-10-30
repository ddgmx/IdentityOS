# Local tiny-model profile

IdentityOS can reduce the amount of context and capability material passed to a
small local model. The interactive chat CLI now accepts `--context-tokens`,
`--max-tools`, and `--tool-result-chars`; defaults retain previous behavior.
For an Ollama model on a memory-constrained CPU laptop, start with 1200 context
tokens, two relevant tools, and 1200 characters per tool result. Keep Ollama's
own context limit at least as large as the IdentityOS context budget plus the
user turn and tool descriptions. This is an operational profile, not an accuracy
claim.

On Windows, `scripts/local_tiny_profile.ps1 -Model gemma3:270m` starts chat
with that profile. `-RunBenchmark` runs the existing frozen five-task demo
through both the bare and IDOS paths, without freezing or changing the suite.
Inspect each run's artifacts under `benchmarks/results/`; compare success and
latency before claiming a win. Tool calls can add a model round trip, and a
270M model may still fail to emit valid tool syntax.
