"""Talk to a large language model (LLM) that writes the answers.

DocGuard speaks the "OpenAI-compatible" chat format, which many providers share:
  - Ollama (free, runs on your own computer)  <- the default
  - Groq, OpenAI, and others: change LLM_BASE_URL, LLM_MODEL and LLM_API_KEY

Settings (environment variables, all optional):
  LLM_PROVIDER   "openai_compatible" (default) or "fake" (used by the tests)
  LLM_BASE_URL   default http://localhost:11434/v1  (Ollama on this computer)
  LLM_MODEL      default qwen3.5:4b
  LLM_API_KEY    default "ollama" (Ollama ignores it; hosted providers need a real key)
"""

import os
from functools import lru_cache


class LLMUnavailable(Exception):
    """The LLM could not be reached or returned an error."""


class OpenAICompatibleLLM:
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        from openai import OpenAI  # imported here so tests never need a server

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=120)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,  # as consistent as possible: same question, same answer
            )
        except Exception as error:  # connection refused, unknown model, timeout...
            raise LLMUnavailable(str(error)) from error
        return (response.choices[0].message.content or "").strip()


class FakeLLM:
    """For tests: 'answers' by repeating everything it was given.

    That makes leak tests strict: if a forbidden chunk ever reached the prompt,
    it would show up word for word in the answer.
    """

    def complete(self, system: str, user: str) -> str:
        return f"FAKE ANSWER. I was given:\n{user}"


@lru_cache  # create the client only once per process
def get_llm():
    if os.getenv("LLM_PROVIDER", "openai_compatible") == "fake":
        return FakeLLM()
    return OpenAICompatibleLLM(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        model=os.getenv("LLM_MODEL", "qwen3.5:4b"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
    )
