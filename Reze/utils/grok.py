"""
Shared caller for Groq's API.

Used by:
- /ai
- /ask
- passive chatbot triggers from chat.py

The function is still called call_grok() so existing imports
do not need to change.
"""

import aiohttp

from Reze.config import Config


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


GROK_SYSTEM_PROMPT = (
    "You are Reze, a Telegram group chatbot. Your personality fuses two "
    "things: Reze's steady, protective, no-nonsense core, and Grok's voice - "
    "witty, a little irreverent, quick with a joke or a blunt take, not afraid "
    "of sarcasm, doesn't take itself too seriously, and isn't shy about having "
    "an opinion. You're warm toward people you're talking with, sharp toward "
    "anyone being a problem. Reply like a real chat message: short, punchy, "
    "conversational - never an essay, never a wall of bullet points unless "
    "specifically asked. Use 🔥 sparingly, not in every message."
)


class GrokError(Exception):
    """Raised when the Groq API cannot be reached or returns an error."""


async def call_grok(
    prompt: str,
    system: str = GROK_SYSTEM_PROMPT,
    max_tokens: int = 700,
) -> str:

    api_key = Config.GROQ_API_KEY

    if not api_key:
        raise GrokError(
            "GROQ_API_KEY is not configured."
        )

    # Safe debugging. NEVER print the full API key.
    print("[GROQ] API key loaded:", bool(api_key))
    print("[GROQ] API key length:", len(api_key))
    print("[GROQ] API key prefix:", api_key[:8])
    print("[GROQ] API key suffix:", api_key[-6:])
    print("[GROQ] Model:", Config.GROQ_MODEL)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": Config.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_tokens": max_tokens,
    }

    timeout = aiohttp.ClientTimeout(total=30)

    try:
        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                GROQ_URL,
                headers=headers,
                json=payload,
            ) as response:

                try:
                    data = await response.json()

                except Exception:
                    raw_text = await response.text()

                    raise GrokError(
                        f"Groq returned HTTP {response.status} "
                        f"with non-JSON response: "
                        f"{raw_text[:500]}"
                    )

                # Handle API errors
                if response.status != 200:

                    error = data.get("error", data)

                    if isinstance(error, dict):

                        error_message = error.get(
                            "message",
                            str(error),
                        )

                        error_type = error.get(
                            "type",
                            "unknown",
                        )

                        error_code = error.get(
                            "code",
                            "unknown",
                        )

                        raise GrokError(
                            f"HTTP {response.status} | "
                            f"type={error_type} | "
                            f"code={error_code} | "
                            f"{error_message}"
                        )

                    raise GrokError(
                        f"HTTP {response.status} | {error}"
                    )

                # Validate response
                choices = data.get("choices")

                if not choices:
                    raise GrokError(
                        f"Groq returned no choices: {data}"
                    )

                message = choices[0].get("message")

                if not message:
                    raise GrokError(
                        f"Groq response missing message: {data}"
                    )

                content = message.get("content")

                if content is None:
                    raise GrokError(
                        f"Groq response missing content: {data}"
                    )

                return str(content).strip() or "..."

    except aiohttp.ClientConnectorError as e:
        raise GrokError(
            f"Could not connect to Groq: {e}"
        )

    except aiohttp.ClientResponseError as e:
        raise GrokError(
            f"Groq HTTP error: {e.status} {e.message}"
        )

    except aiohttp.ClientError as e:
        raise GrokError(
            f"Groq network error: {e}"
        )

    except TimeoutError:
        raise GrokError(
            "Groq request timed out after 30 seconds."
        )

    except GrokError:
        raise

    except Exception as e:
        print(
            f"[GROQ] Unexpected error: "
            f"{type(e).__name__}: {e}"
        )

        raise GrokError(
            f"Unexpected error: {type(e).__name__}: {e}"
        )
