# AI API Client

A simple functional TypeScript client for calling multiple AI APIs (Claude, OpenAI, Gemini).

## Installation

```bash
pnpm install
```

## Setup

Create a `.env` file with your API keys:

```
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

## Usage

### Single Provider

```typescript
import "dotenv/config";
import { callAI } from "./index";

const response = await callAI("claude", {
  systemPrompt: "Be concise.",
  userMessage: "What is TypeScript?",
});

console.log(response.content);
```

### Individual Provider Functions

```typescript
import "dotenv/config";
import { callClaude, callOpenAI, callGemini } from "./index";

const response = await callClaude({
  systemPrompt: "Be helpful.",
  userMessage: "Hello!",
  model: "claude-sonnet-4-20250514", // optional
  maxTokens: 500, // optional
});
```

## API

### Types

```typescript
type Provider = "claude" | "openai" | "gemini";

interface CallOptions {
  systemPrompt: string;
  userMessage: string;
  model?: string;
  maxTokens?: number; // default: 1024
}

interface AIResponse {
  provider: Provider;
  content: string;
  raw: unknown;
}
```

### Default Models

- Claude: `claude-sonnet-4-20250514`
- OpenAI: `gpt-5-nano`
- Gemini: `gemini-2.5-flash`

## Run Example

```bash
pnpm example
```
