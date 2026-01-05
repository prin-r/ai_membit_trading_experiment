import "dotenv/config";
import { callClaude, callOpenAI, callGemini } from "./providers";
import type { AIResponse } from "./types";

const main = async () => {
  console.log("Calling all AI providers...\n");

  const options = {
    systemPrompt: "You are a helpful assistant. Reply concisely in one sentence.",
    userMessage: "What is the main benefit of TypeScript over JavaScript?",
  };

  const calls = [
    { name: "claude", fn: () => callClaude(options) },
    { name: "openai", fn: () => callOpenAI(options) },
    { name: "gemini", fn: () => callGemini(options) },
  ];

  const responses: AIResponse[] = [];

  for (const call of calls) {
    try {
      const response = await call.fn();
      responses.push(response);
    } catch (error) {
      console.error(`[${call.name.toUpperCase()}] Error: ${error instanceof Error ? error.message : error}`);
    }
  }

  console.log(`\nReceived ${responses.length} successful response(s):\n`);

  for (const response of responses) {
    console.log(`[${response.provider.toUpperCase()}]`);
    console.log(response.content);
    console.log();
  }
};

main().catch(console.error);
