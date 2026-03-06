# Mutual Dissent — Roadmap

## Problem Statement

AI models have different training data, architectures, and reasoning biases. Relying on a single model means inheriting its blind spots. Power users already work around this by manually querying multiple models, comparing responses, and cross-pollinating insights between conversations. This works but is slow and tedious.

Every existing multi-model tool either operates within a single vendor's ecosystem (Grok 4.20's 4-agent system, Anthropic's agent teams) or does cross-vendor comparison without a reflection loop (LLM Council, PolyCouncil). Nobody builds the full cycle: fan-out → reflection → refinement → synthesis across different vendors.

Mutual Dissent automates the workflow that power users already do manually — and logs the full debate as structured data for analysis.

---

## Development History & Status

### Core Debate Loop ✅

Working CLI that executes the fan-out → reflection → synthesis loop and saves transcripts. OpenRouter integration with async parallel model calls, configurable reflection rounds, Rich terminal output, and JSON transcript logging to `~/.mutual-dissent/transcripts/`. Completed 2026-02-21 — first live 4-vendor debate: 41,476 tokens.

### Provider Abstraction ✅

Replaced the single-provider OpenRouter client with a provider abstraction layer supporting direct vendor API keys alongside OpenRouter. Config schema drives the router interface; schema upgrades shipped concurrently with provider work for richer transcripts from day one. See design decisions below. Completed as part of the CLI expansion work.

| Decision | Rationale |
|----------|-----------|
| `resolved_config` dict over `config_hash` | Hash of TOML sections is fragile (ordering, whitespace). Full dict is more bytes, zero ambiguity. |
| Dynamic pricing from OpenRouter API | Model prices change weekly. Hardcoded pricing = constant maintenance. |
| Config schema before router implementation | Config shape drives the router interface, not the other way around. |
| Schema upgrades concurrent with provider work | Avoids migration later. Richer schema from the first multi-provider transcript. |
| Topology/roles/RAG deferred | They're the research payload — deferred because plumbing isn't ready, not because they're optional. |

### CLI Research Tools ✅

Replay capability, markdown export, file input, ground-truth scoring, and cost tracking — the CLI became a complete research tool. Completed 2026-02-28 with 325+ tests.

### Web GUI ✅

NiceGUI-based web interface with two modes: a power-tool debate view for running debates with live streaming, and a research dashboard for analyzing transcripts with convergence charts, influence heatmaps, and cost tracking.

**Cross-tool integration scaffolding** was added as a prerequisite: per-panelist context injection, round-level event hooks, and experiment metadata schema. These establish interface contracts for the broader research platform (CounterSignal, CounterAgent). See `Lab/Cross-Tool Research Directions.md` for the full context.

### Documentation ✅

Mintlify docs site with AI assistant, MCP server integration, and LLM-optimized content at [docs.mutual-dissent.dev](https://docs.mutual-dissent.dev).

### Desktop App & Batch Mode — Planned

Tauri 2 desktop wrapper, transcript analysis tooling, alternative debate topologies (ring, star, adversarial), local model support via Ollama, batch mode, and public release polish.

---

## v1.0 Exit Criteria

SemVer 1.0 is a public commitment to interface stability. After 1.0, breaking changes to CLI commands, transcript schema, config format, or data models require a major version bump.

### Capability Readiness

| Area | Gate |
|------|------|
| Debate engine | ≥10 completed multi-model debates with full transcripts logged |
| Research platform | ≥1 publishable finding from consensus poisoning or convergence analysis (MD-NNN) |

### Interface Stability

**CLI commands** (as documented at [docs.mutual-dissent.dev](https://docs.mutual-dissent.dev)):

| Command | Frozen |
|---------|--------|
| `ask` | Command, all flags (`--panel`, `--synthesizer`, `--rounds`, `--verbose`, `--no-save`, `--output`, `--file`, `--ground-truth`, `--ground-truth-file`) |
| `replay` | Command, all flags (`--synthesizer`, `--rounds`, `--verbose`, `--no-save`, `--output`, `--file`, `--ground-truth`, `--ground-truth-file`) |
| `list` | Command, `--limit` flag |
| `show` | Command, all flags (`--verbose`, `--output`, `--file`) |
| `config path` | Command |
| `config show` | Command, `--check-models` flag |
| `config test` | Command |
| `serve` | Command, all flags (`--port`, `--host`, `--no-open`) |

**Published schemas** (Data & Schemas at [docs.mutual-dissent.dev](https://docs.mutual-dissent.dev)):

| Schema | Commitment |
|--------|------------|
| Transcript JSON | Top-level fields, `DebateRound`, `ModelResponse`, `routing` object, `metadata` object — frozen |
| Data Models | `ModelResponse`, `DebateRound`, `DebateTranscript`, `ExperimentMetadata` — frozen |
| Metadata keys | `stats`, `scores`, `experiment`, `panelist_context`, `source_transcript_id`, `replay_config` — frozen |

**Provider interface:**

| Surface | Commitment |
|---------|------------|
| `Provider` ABC | `complete()`, `complete_parallel()`, async context manager — frozen |
| `ProviderRouter` | Routing modes (`auto`, `direct`, `openrouter`) — frozen |
| `ModelResponse` dataclass | All fields including `routing` dict — frozen |

**Config format:**

| Surface | Commitment |
|---------|------------|
| `config.toml` sections | `[providers]`, `[routing]`, `[model_aliases]`, `[defaults]` — section names and key semantics frozen |
| Environment variable overrides | `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `XAI_API_KEY`, `GROQ_API_KEY` — frozen |

**Extension points:**

| Surface | Commitment |
|---------|------------|
| `panelist_context` | `dict[str, str]` interface frozen |
| `on_round_complete` | `Callable[[DebateRound], Awaitable[None]]` signature frozen |
| `ExperimentMetadata` fields | `experiment_id`, `source_tool`, `campaign_id`, `condition`, `variables`, `finding_ref` — frozen |

**Web GUI:**

| Surface | Commitment |
|---------|------------|
| Routes | `/` (debate view), `/dashboard` — stable |
| WebSocket streaming | Round-by-round progressive rendering — behavior stable |

### Research Validation

- ≥1 publishable finding from consensus manipulation, convergence patterns, or safety boundary research
- Ground-truth scoring validated against ≥1 curated query set with known answers

### Known Limitations at 1.0

- **Navigation kills running debates** — NiceGUI re-creates pages on route change, orphaning the asyncio task. Results are lost. Workaround: stay on the debate page until synthesis completes. Fix targeted for post-1.0.
- **Influence heatmap visualMap text clipped** — mid-range labels render behind the bar or are color-invisible. ECharts `visualMap` config needs adjustment.
- **JSON/CSV export is metadata only** — dashboard export serializes summary index, not full transcripts. Labels are misleading.

### Explicitly Post-1.0

- **Tauri desktop wrapper** — web UI and CLI cover all current workflows.
- **Batch mode** — programmatic batch execution of debate campaigns.
- **Navigation bug fix** — requires SPA tab-switching or state recovery architecture.
- **Cross-tool studies** — tracked independently of Mutual Dissent tool versioning.

---

## Goals

- A tool I actually use when the answer matters — replacing my manual
  cross-conversation workflow
- Structured dataset of multi-model debate transcripts for behavior analysis
- At least one publishable finding from consensus poisoning or convergence
  pattern research
- If public: a tool other AI power users adopt because nothing else does
  cross-vendor reflection
- A research dashboard that makes transcript analysis visual and fast

---

## Out of Scope (for now)

- Integration with AnythingLLM, LibreChat, or other frontends
- Autonomous continuous debate (human initiates, human decides when to stop)
- Fine-tuning or training based on debate outcomes
- Mobile app (Tauri 2 supports it, but not a priority)
