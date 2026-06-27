from groq import AsyncGroq
from config import GROQ_API_KEY, MODEL_NAME

client = AsyncGroq(api_key=GROQ_API_KEY)


# ---------------------------------------------------
# Standard Chat (Existing)
# ---------------------------------------------------
async def chat(system_prompt: str, user_prompt: str) -> str:

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content


# ---------------------------------------------------
# Streaming Chat
# ---------------------------------------------------
async def stream_chat(system_prompt: str, user_prompt: str):

    stream = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
        stream=True,
    )

    async for chunk in stream:

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        if delta is None:
            continue

        if delta.content:
            yield delta.content