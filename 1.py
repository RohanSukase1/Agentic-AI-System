from openai import OpenAI

client = OpenAI(api_key="")

messages = [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": "What is AI?"}
]
response = client.chat.completions.create(
    model="gpt-4.1",
    messages=messages
)
print(response.choices[0].message.content)