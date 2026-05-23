import os
import anthropic
from typing import Optional

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"


def build_messages(history: list[dict], user_message: str) -> list[dict]:
    messages = []
    for msg in history[-10:]:  # Keep last 10 messages for context
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


def chat_with_claude(system_prompt: str, messages: list[dict], max_tokens: int = 2048) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text
