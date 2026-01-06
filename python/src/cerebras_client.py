"""
Cerebras client using the official Cerebras Cloud SDK.
https://github.com/Cerebras/cerebras-cloud-sdk-python
"""

import os
from cerebras.cloud.sdk import Cerebras
from .types import CallOptions, AIResponse


def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing: {key}")
    return value


def call_cerebras(options: CallOptions) -> AIResponse:
    """
    Call Cerebras API using the official Cerebras Cloud SDK.

    Cerebras offers models like:
    - llama3.1-8b (fast, efficient)
    - llama3.1-70b (more capable)
    - llama-3.3-70b (latest, recommended)
    """
    api_key = get_env("CEREBRAS_API_KEY")

    client = Cerebras(api_key=api_key)

    model = options.model or "llama-3.3-70b"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": options.system_prompt},
            {"role": "user", "content": options.user_message},
        ],
        max_tokens=options.max_tokens,
    )

    content = response.choices[0].message.content or ""

    return AIResponse(
        provider="cerebras",
        content=content,
        raw=response.model_dump(),
    )
