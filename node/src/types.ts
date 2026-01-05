export type Provider = "claude" | "openai" | "gemini";

export interface CallOptions {
  systemPrompt: string;
  userMessage: string;
  model?: string;
  maxTokens?: number;
}

export interface AIResponse {
  provider: Provider;
  content: string;
  raw: unknown;
}
