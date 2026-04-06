# Mutual Dissent

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![CI](https://github.com/richardspicer/mutual-dissent/actions/workflows/ci.yml/badge.svg)](https://github.com/richardspicer/mutual-dissent/actions/workflows/ci.yml)
[![CodeQL](https://github.com/richardspicer/mutual-dissent/actions/workflows/codeql.yml/badge.svg)](https://github.com/richardspicer/mutual-dissent/actions/workflows/codeql.yml)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[![Docs](https://img.shields.io/badge/docs-mutual--dissent.dev-8b5cf6)](https://docs.mutual-dissent.dev)

**Cross-vendor multi-model debate and consensus engine for AI response distillation.**

Web UI with chat-style debate view, dashboard, and full CLI. Multi-model and single-model multi-agent modes. Direct vendor APIs, replay, cost tracking, and markdown export. 400+ tests across Windows and Linux CI.

> Built by [Richard Spicer](https://richardspicer.io) · [GitHub](https://github.com/richardspicer)

---

## Install

```bash
pip install mutual-dissent
```

Or from source:

```bash
git clone https://github.com/richardspicer/mutual-dissent.git
cd mutual-dissent
uv sync --group dev
```

---

## How It Works

1. **Fan out** — Query goes to your panel: multiple vendors (Claude, GPT, Gemini, Grok) or multiple agents of the same model
2. **Reflect** — Each agent sees the others' responses and argues back
3. **Synthesize** — A user-selected model distills the debate into a final answer
4. **Log** — Full debate transcript saved as structured JSON with cost and token data

## Why Multi-Model Debate?

Single-vendor multi-agent systems (Grok's 4-agent debate, Anthropic's agent teams) share the same training data and blind spots. Cross-vendor debate surfaces disagreements that correlated architectures can't. Mutual Dissent supports both modes: cross-vendor panels for maximum diversity, or single-model multi-agent panels (e.g., `--panel claude,claude,claude`) where context isolation drives independent evaluation.

## Usage

```bash
# Run a debate
dissent ask "Your query here"

# With explicit panel and options
dissent ask "Your query here" --synthesizer claude --rounds 2 --panel claude,gpt,gemini
dissent ask "Summarize this" --file report.pdf
dissent replay <transcript-id> --synthesizer grok
dissent serve
dissent config test
```

`mutual-dissent` also works as the full command name. Full documentation at [docs.mutual-dissent.dev](https://docs.mutual-dissent.dev).

---

## Status

| Capability | Status |
|------------|--------|
| Core debate loop | ✅ Complete — fan-out, reflection, synthesis |
| Provider abstraction | ✅ Complete — direct Anthropic API, OpenRouter, mixed-panel routing |
| Single-model multi-agent | ✅ Complete — duplicate aliases with context-isolated agents |
| CLI tools | ✅ Complete — replay, scoring, cost tracking, markdown export |
| Web UI | ✅ Complete — Starlette + DaisyUI chat interface, dashboard, settings |
| Documentation | ✅ Complete — Mintlify docs site with AI assistant and MCP server |
| Desktop app & batch mode | Planned — Tauri wrapper, alternative topologies |

## Transcript Logging

Full debate transcripts are logged as structured JSON — every round, every response, with cost, token, latency, and routing data. Browse and export transcripts via the web dashboard or CLI.

## License

[MIT](LICENSE)

## AI Disclosure

This project uses a human-led, AI-augmented workflow. See [AI-STATEMENT.md](AI-STATEMENT.md).
