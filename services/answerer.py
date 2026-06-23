# services/answerer.py
import requests

import config

GROQ_BASE = "https://api.groq.com/openai/v1"


def answer_short_groq(prompt: str, model: str = None, system: str = None) -> str:
    """
    One-sentence answer using Groq (OpenAI-compatible chat).
    Keeps it concise with low temperature.
    """
    if model is None:
        model = config.GROQ_LLM_MODEL
    if system is None:
        system = "Answer concisely in one sentence."

    url = f"{GROQ_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 120,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"LLM answer failed ({r.status_code}): {r.text}")

    j = r.json()
    text = j["choices"][0]["message"]["content"].strip()
    # keep tidy
    if len(text) > 400:
        text = text[:400].rsplit(" ", 1)[0] + "..."
    if not text.endswith((".", "!", "?")):
        text += "."
    return text
