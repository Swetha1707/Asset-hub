import os
from google import genai
from google.genai import types

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def ask_openai(question, system_prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt
        )
    )

    return response.text