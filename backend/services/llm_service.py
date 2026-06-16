import os
import json
import re
from groq import Groq


def get_groq_client():
    """
    Create Groq client only when needed
    (prevents env loading issues at import time)
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Make sure .env is loaded correctly."
        )

    return Groq(api_key=api_key)


async def generate_summary_and_quiz(transcript: dict) -> dict:
    """
    Uses Groq Llama 3.1 70B to generate:
    - summary
    - key points
    - quiz
    """

    groq_client = get_groq_client()

    prompt = f"""
You are a lecture assistant.

Analyze the following lecture transcript and return:

1. A concise summary
2. Key important points (bullet format)
3. 5 quiz questions with answers

LECTURE TRANSCRIPT:
{transcript["text"]}

Return ONLY valid JSON in this format:

{{
  "summary": "string",
  "key_points": [
    "point 1",
    "point 2",
    "point 3"
  ],
  "quiz": [
    {{
      "question": "string",
      "answer": "string"
    }}
  ]
}}
"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    result = response.choices[0].message.content

    # ---- SAFE JSON PARSING ----
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # fallback: extract JSON block if model adds extra text
        match = re.search(r"\{.*\}", result, re.DOTALL)
        if match:
            return json.loads(match.group())

        raise ValueError(f"Groq returned invalid JSON:\n{result}")