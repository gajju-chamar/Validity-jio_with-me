"""
Shared caller for xAI's Grok API.

Used by:
- /ai
- /ask
- passive chatbot triggers from chat.py

Uses xAI's OpenAI-compatible Chat Completions API.
"""

import aiohttp

from Reze.config import Config


XAI_URL = "https://api.x.ai/v1/chat/completions"


# Reze's personality
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
    """Raised when the xAI API cannot be reached or returns an error."""


async def call_grok(
    prompt: str,
    system: str = GROK_SYSTEM_PROMPT,
    max_tokens: int = 700,
) -> str:

    # ---------------------------------------------------------
    # 1. Check API key
    # ---------------------------------------------------------

    api_key = Config.XAI_API_KEY

    if not api_key:
        raise GrokError("XAI_API_KEY is not configured.")

    # ---------------------------------------------------------
    # 2. Safe debugging
    # ---------------------------------------------------------
    # NEVER print the complete API key.
    #
    # These values let us confirm Railway is actually loading
    # the key without exposing it in logs.

    print("[GROK] API key loaded:", bool(api_key))
    print("[GROK] API key length:", len(api_key))
    print("[GROK] API key prefix:", api_key[:8])
    print("[GROK] API key suffix:", api_key[-6:])
    print("[GROK] Model:", Config.XAI_MODEL)

    # ---------------------------------------------------------
    # 3. Prepare request
    # ---------------------------------------------------------

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": Config.XAI_MODEL,
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

    # ---------------------------------------------------------
    # 4. Call xAI
    # ---------------------------------------------------------

    timeout = aiohttp.ClientTimeout(total=30)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:

            async with session.post(
                XAI_URL,
                headers=headers,
                json=payload,
            ) as response:

                # Try to parse JSON
                try:
                    data = await response.json()

                except Exception:
                    raw_text = await response.text()

                    raise GrokError(
                        f"xAI returned HTTP {response.status} "
                        f"with non-JSON response: {raw_text[:500]}"
                    )

                # -------------------------------------------------
                # 5. Handle HTTP errors
                # -------------------------------------------------

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

                # -------------------------------------------------
                # 6. Validate successful response
                # -------------------------------------------------

                if not isinstance(data, dict):
                    raise GrokError(
                        f"Unexpected response type: {type(data).__name__}"
                    )

                choices = data.get("choices")

                if not choices:
                    raise GrokError(
                        f"xAI returned no choices: {data}"
                    )

                first_choice = choices[0]

                message = first_choice.get("message")

                if not message:
                    raise GrokError(
                        f"xAI response missing message: {data}"
                    )

                content = message.get("content")

                if content is None:
                    raise GrokError(
                        f"xAI response missing content: {data}"
                    )

                return str(content).strip() or "..."

    # ---------------------------------------------------------
    # 7. Network errors
    # ---------------------------------------------------------

    except aiohttp.ClientConnectorError as e:
        raise GrokError(
            f"Could not connect to xAI: {e}"
        )

    except aiohttp.ClientResponseError as e:
        raise GrokError(
            f"xAI HTTP error: {e.status} {e.message}"
        )

    except aiohttp.ClientError as e:
        raise GrokError(
            f"xAI network error: {e}"
        )

    except TimeoutError:
        raise GrokError(
            "xAI request timed out after 30 seconds."
        )

    except GrokError:
        # Don't wrap our own useful errors
        raise

    except Exception as e:
        print(
            f"[GROK] Unexpected error: "
            f"{type(e).__name__}: {e}"
        )

        raise GrokError(
            f"Unexpected error: {type(e).__name__}: {e}"
        )
