# Changelog

All notable changes to Mutual Dissent are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-03-08

Cross-tool research scaffolding: Payload Source Protocol and Finding Output Adapter.
Completes architectural integration points 4 and 5, enabling programmatic payload
injection and cross-tool finding correlation.

### Added

#### Research Platform
- Payload Source Protocol: `PayloadSource` ABC with `get_query()` and `get_context()` interface
- `DefaultPayloadSource` implementation for standard user-provided queries
- `run_debate()` accepts optional `payload_source` parameter for programmatic input
- `ResearchFinding` dataclass with CounterAgent-compatible JSON export via `to_dict()`
- `FindingSeverity` enum matching CounterAgent severity levels

## [0.1.0] — 2026-03-04

First public release. Cross-vendor multi-model debate and consensus engine with CLI,
web GUI, and research dashboard.

### Added

#### Core Engine
- Debate orchestrator with configurable round counts and reflection loops
- Provider abstraction layer: direct vendor APIs (Anthropic first) + OpenRouter unified routing
- Alias-space routing with per-model direct/OpenRouter/auto routing policy
- Cross-vendor reflection: each panelist sees competing responses and argues back
- Synthesis step via user-selected model after all reflection rounds complete

#### CLI
- `dissent ask` — run a debate from the command line with Markdown output
- `dissent ask --file` — load question from file
- `dissent ask --ground-truth` — score final answer against known correct answer
- `dissent replay` — re-run a saved transcript
- `dissent list` / `dissent show` — browse and inspect saved transcripts
- `dissent config test` / `config show` / `config path` — provider connectivity and config management
- `mutual-dissent` and `dissent` aliases both registered

#### Web GUI
- NiceGUI-based interface with WebSocket streaming
- Live debate view with per-panelist response cards and inline diff highlighting
- Research dashboard: transcript browser, convergence/influence/cost charts
- JSON and CSV transcript export
- Config panel for provider and model selection
- Dark mode

#### Research Platform
- Full debate transcripts logged as structured JSON to `~/.mutual-dissent/transcripts/`
- Per-panelist context injection for controlled experiment design
- Round-level event hooks for custom instrumentation
- Experiment metadata schema for cross-session analysis
- Cost tracking per debate and per model
- Ground-truth scoring for accuracy measurement

#### Documentation
- Mintlify docs site at [docs.mutual-dissent.dev](https://docs.mutual-dissent.dev) — 20 pages
- llms.txt for LLM-friendly navigation

#### Infrastructure
- CI pipeline: lint/format/typecheck/test matrix on Ubuntu + Windows (Python 3.11–3.14)
- `security-scan` job: bandit SAST + pip-audit dependency audit
- CodeQL enabled
- Pre-commit hooks: ruff, mypy, gitleaks, trailing whitespace
- 325+ tests

[0.2.0]: https://github.com/q-uestionable-AI/mutual-dissent/releases/tag/v0.2.0
[0.1.0]: https://github.com/q-uestionable-AI/mutual-dissent/releases/tag/v0.1.0
