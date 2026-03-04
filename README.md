# Mutual Dissent

[![CI](https://github.com/q-uestionable-AI/mutual-dissent/actions/workflows/ci.yml/badge.svg)](https://github.com/q-uestionable-AI/mutual-dissent/actions/workflows/ci.yml)
[![CodeQL](https://github.com/q-uestionable-AI/mutual-dissent/actions/workflows/codeql.yml/badge.svg)](https://github.com/q-uestionable-AI/mutual-dissent/actions/workflows/codeql.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Docs](https://img.shields.io/badge/docs-mutual--dissent.dev-8b5cf6)](https://docs.mutual-dissent.dev)

**Cross-vendor multi-model debate and consensus engine for AI response distillation.**

NiceGUI web interface with live debate view, research dashboard, and full CLI research tool. Direct vendor APIs, replay, ground-truth scoring, cost tracking, and markdown export. 400+ tests across Windows and Linux CI.

> Research program by [Richard Spicer](https://richardspicer.io) · [GitHub](https://github.com/richardspicer)

---

## Install

```bash
pip install mutual-dissent
```

Or from source:

```bash
git clone https://github.com/q-uestionable-AI/mutual-dissent.git
cd mutual-dissent
uv sync
```

---

## How It Works

1. **Fan out** — Query goes to Claude, GPT, Gemini, and Grok (direct APIs or via OpenRouter)
2. **Reflect** — Each model sees the others' responses and argues back
3. **Synthesize** — A user-selected model distills the debate into a final answer
4. **Log** — Full debate transcript saved as structured JSON with cost and token data

## Why Cross-Vendor?

Single-vendor multi-agent systems (Grok's 4-agent debate, Anthropic's agent teams) share the same training data and blind spots. Cross-vendor debate surfaces disagreements that correlated architectures can't — different training data, different safety postures, different failure modes.

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
| Core debate loop | ✅ Complete — fan-out, reflection, synthesis via OpenRouter |
| Provider abstraction | ✅ Complete — direct Anthropic API, mixed-panel routing |
| CLI research tools | ✅ Complete — replay, scoring, cost tracking, markdown export |
| Web GUI | ✅ Complete — NiceGUI debate view, research dashboard, live streaming |
| Documentation | ✅ Complete — Mintlify docs site with AI assistant and MCP server |
| Desktop app & batch mode | Planned — Tauri wrapper, alternative topologies, public release |

## Research Platform

Full debate transcripts are logged as structured JSON for research — disagreement patterns, convergence dynamics, consensus poisoning, and hallucination detection. See [Research Methodology](https://docs.mutual-dissent.dev) for details.

## Legal

All tools are intended for authorized security testing only. Only test systems you own, control, or have explicit permission to test. Responsible disclosure for all vulnerabilities discovered.

## License

[MIT](LICENSE)

## AI Disclosure

This project uses a human-led, AI-augmented workflow. See [AI-STATEMENT.md](AI-STATEMENT.md).
