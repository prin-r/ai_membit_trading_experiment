# AI API Client - Monorepo

A multi-language AI API client supporting various AI providers.

## Structure

- **[node/](./node/)** - Node.js/TypeScript implementation (Claude, OpenAI, Gemini)
- **[python/](./python/)** - Python implementation (Cerebras with Membit integration)

## Quick Start

### Node.js

```bash
cd node
pnpm install
pnpm dev
```

### Python

```bash
cd python
uv sync
uv run python -m src.examples.basic_chat
```

See individual README files in each directory for detailed documentation.
