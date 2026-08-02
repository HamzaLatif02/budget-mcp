import json

import anthropic

MODEL = "claude-haiku-4-5"

ALLOWED_CATEGORIES = [
    "rent",
    "food",
    "transport",
    "savings",
    "business_expense",
    "entertainment",
    "other",
]

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ALLOWED_CATEGORIES},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["category", "confidence", "reasoning"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = (
    "You classify raw bank/card transaction descriptions into exactly one "
    f"category from this fixed list: {', '.join(ALLOWED_CATEGORIES)}. "
    "Use 'other' when nothing else clearly fits. Base confidence on how "
    "unambiguous the description is, not on how important the transaction is."
)


def categorize(description: str) -> dict:
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": description}],
            output_config={"format": {"type": "json_schema", "schema": _RESPONSE_SCHEMA}},
        )
    except (anthropic.AuthenticationError, TypeError) as e:
        raise ValueError(
            "Anthropic API authentication failed - set the ANTHROPIC_API_KEY environment variable"
        ) from e
    except anthropic.RateLimitError as e:
        raise ValueError("Anthropic API rate limit exceeded - try again shortly") from e
    except anthropic.APIStatusError as e:
        raise ValueError(f"Anthropic API error: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ValueError("Could not reach the Anthropic API - check your network connection") from e

    text = next(block.text for block in response.content if block.type == "text")
    result = json.loads(text)

    category = result.get("category")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Model returned an invalid category {category!r}; "
            f"expected one of {ALLOWED_CATEGORIES}"
        )

    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError(f"Model returned a non-numeric confidence: {confidence!r}")
    confidence = max(0.0, min(1.0, float(confidence)))

    reasoning = result.get("reasoning")
    if not isinstance(reasoning, str):
        raise ValueError(f"Model returned non-string reasoning: {reasoning!r}")

    return {"category": category, "confidence": confidence, "reasoning": reasoning}
