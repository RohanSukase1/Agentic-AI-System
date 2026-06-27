import asyncio

from utils.llm import stream_chat


async def main():

    async for token in stream_chat(
        "You are a helpful assistant.",
        "Explain AI in 50 words."
    ):
        print(token, end="", flush=True)


asyncio.run(main())