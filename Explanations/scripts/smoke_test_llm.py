# /scripts/smoke_test_llm.py
import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    load_dotenv()

    base_url = os.getenv("LOCAL_OPENAI_BASE_URL")
    api_key = os.getenv("LOCAL_OPENAI_API_KEY", "ollama")
    model = os.getenv("LOCAL_OPENAI_MODEL", "qwen2.5:14b")

    if not base_url:
        raise RuntimeError("Falta LOCAL_OPENAI_BASE_URL en el .env")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Eres un asistente breve."},
            {"role": "user", "content": "Dime 'OK' y nada más."},
        ],
        temperature=0.0,
    )

    print("Response:", resp.choices[0].message.content)
    usage = getattr(resp, "usage", None)
    if usage:
        print("Usage:", usage)

if __name__ == "__main__":
    main()