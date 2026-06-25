from groq import AsyncGroq
from config import GROQ_API_KEY, MODEL_NAME

# Create Groq client
client = AsyncGroq(api_key=GROQ_API_KEY)


async def chat(prompt: str) -> str:
    """
    Sends a prompt to Groq and returns the response text.
    """

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5,
    )

    return response.choices[0].message.content