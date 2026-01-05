import type { Provider, CallOptions, AIResponse } from "./types";
import { callClaude, callOpenAI, callGemini } from "./providers";

const providers = {
  claude: callClaude,
  openai: callOpenAI,
  gemini: callGemini,
} as const;

export const callAI = (
  provider: Provider,
  options: CallOptions
): Promise<AIResponse> => {
  return providers[provider](options);
};
