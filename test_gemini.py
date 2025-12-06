"""
Lightweight sanity check for a configured OPENAI_API_KEY.
Run with: python test_gemini.py
"""

import os

from openai import OpenAI


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY before running this test.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello in Levantine Arabic."}],
        temperature=0.3,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
