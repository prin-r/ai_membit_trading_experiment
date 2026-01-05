import type { CallOptions, AIResponse } from "./types";

const getEnv = (key: string): string => {
  const value = process.env[key];
  if (!value) throw new Error(`Missing: ${key}`);
  return value;
};

export const callClaude = async (options: CallOptions): Promise<AIResponse> => {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": getEnv("ANTHROPIC_API_KEY"),
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: options.model ?? "claude-sonnet-4-20250514",
      max_tokens: options.maxTokens ?? 1024,
      system: options.systemPrompt,
      messages: [{ role: "user", content: options.userMessage }],
    }),
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message ?? "Claude API error");

  return {
    provider: "claude",
    content: data.content[0].text,
    raw: data,
  };
};

export const callOpenAI = async (options: CallOptions): Promise<AIResponse> => {
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getEnv("OPENAI_API_KEY")}`,
    },
    body: JSON.stringify({
      model: options.model ?? "gpt-5-nano",
      max_completion_tokens: options.maxTokens ?? 1024,
      messages: [
        { role: "system", content: options.systemPrompt },
        { role: "user", content: options.userMessage },
      ],
    }),
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message ?? "OpenAI API error");

  return {
    provider: "openai",
    content: data.choices[0].message.content,
    raw: data,
  };
};

export const callGemini = async (options: CallOptions): Promise<AIResponse> => {
  const model = options.model ?? "gemini-2.5-flash";
  console.log("GEMINI API: ", getEnv("GOOGLE_API_KEY"));
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${getEnv(
    "GOOGLE_API_KEY"
  )}`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: options.systemPrompt }] },
      contents: [{ role: "user", parts: [{ text: options.userMessage }] }],
      generationConfig: { maxOutputTokens: options.maxTokens ?? 1024 },
    }),
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message ?? "Gemini API error");

  return {
    provider: "gemini",
    content: data.candidates[0].content.parts[0].text,
    raw: data,
  };
};
