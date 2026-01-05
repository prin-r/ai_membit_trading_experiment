# CLAUDE.md - AI API Client

This file provides guidance for AI assistants working with this codebase.

## Project Overview

A simple functional TypeScript client for calling multiple AI APIs (Claude, OpenAI, Gemini). The library provides both individual provider functions and a unified client interface.

## Project Structure

```
ai-api-client/
├── src/
│   ├── index.ts          # Main exports (re-exports all modules)
│   ├── types.ts          # Type definitions (Provider, CallOptions, AIResponse)
│   ├── providers.ts      # Individual provider call functions
│   └── client.ts         # Unified client functions (callAI, callAllAI)
├── package.json          # ESM module with tsx/typescript devDeps
├── tsconfig.json         # TypeScript config (ES2022, ESNext modules)
├── .env                  # API keys (not committed)
└── CLAUDE.md             # This file
```

## Key Types

```typescript
type Provider = "claude" | "openai" | "gemini";

interface CallOptions {
  systemPrompt: string;   // Required system prompt
  userMessage: string;    // Required user message
  model?: string;         // Optional model override
  maxTokens?: number;     // Optional token limit (default: 1024)
}

interface AIResponse {
  provider: Provider;     // Which provider responded
  content: string;        // Extracted text content
  raw: unknown;           // Full API response
}
```

## Build & Run Commands

```bash
pnpm install          # Install dependencies
pnpm dev              # Run with tsx (development)
```

## Development Guidelines

### Code Style

- **Functional approach**: Use pure functions, avoid classes
- **Type safety**: Always use TypeScript types, avoid `any`
- **Error handling**: Throw descriptive errors for missing env vars and API failures
- **Async/await**: Use async/await for all API calls
- **ESM modules**: Project uses ES modules (`"type": "module"`)

### Provider Functions Pattern

Each provider function (`callClaude`, `callOpenAI`, `callGemini`) follows this pattern:
1. Get required env var using `getEnv()` helper
2. Make fetch request with provider-specific headers/body
3. Parse response and check for errors
4. Return normalized `AIResponse` object

### Default Models

- Claude: `claude-sonnet-4-20250514`
- OpenAI: `gpt-4o`
- Gemini: `gemini-1.5-pro`

### Adding a New Provider

1. Add provider name to `Provider` type in `types.ts`
2. Create `callNewProvider` function in `providers.ts` following existing pattern
3. Add to `providers` object in `client.ts`
4. Export from `index.ts`
5. Add env var to `.env` documentation

### Environment Variables

Required API keys (set in `.env`):
- `ANTHROPIC_API_KEY` - For Claude API
- `OPENAI_API_KEY` - For OpenAI API
- `GOOGLE_API_KEY` - For Gemini API

### Error Handling

- Missing env vars throw: `"Missing: {KEY_NAME}"`
- API errors throw the error message from the response
- `callAllAI` uses `Promise.allSettled` and filters to only successful responses

## Testing Patterns

When testing, use the individual provider functions for isolation:
```typescript
const response = await callClaude({
  systemPrompt: "You are helpful.",
  userMessage: "Hello!",
});
```

Use `callAllAI` to test all providers simultaneously with the same prompt.

## Common Tasks

### Making a simple API call
```typescript
import { callAI } from "./index";

const response = await callAI("claude", {
  systemPrompt: "Be concise.",
  userMessage: "What is TypeScript?",
});
```

### Calling all providers at once
```typescript
import { callAllAI } from "./index";

const responses = await callAllAI({
  systemPrompt: "Reply in one sentence.",
  userMessage: "What is recursion?",
});
// Returns array of successful responses only
```

### Custom model selection
```typescript
const response = await callAI("openai", {
  systemPrompt: "Be helpful.",
  userMessage: "Hello",
  model: "gpt-4o-mini",
  maxTokens: 500,
});
```

## File Dependencies

```
index.ts
  └── exports from: types.ts, providers.ts, client.ts

client.ts
  ├── types.ts (Provider, CallOptions, AIResponse)
  └── providers.ts (callClaude, callOpenAI, callGemini)

providers.ts
  └── types.ts (CallOptions, AIResponse)

types.ts
  └── (no dependencies)
```

## API Endpoints

- Claude: `https://api.anthropic.com/v1/messages`
- OpenAI: `https://api.openai.com/v1/chat/completions`
- Gemini: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
