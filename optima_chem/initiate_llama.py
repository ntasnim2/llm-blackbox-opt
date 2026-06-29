import os
from openai import OpenAI

API_KEY = os.environ.get("LLAMA_API_KEY")

client = OpenAI(base_url="https://llamame.apps.czapps.llnl.gov/v1", api_key=API_KEY)

# Check which LLModels LC is hosting
print(client.models.list())

chat_response = client.chat.completions.create(
model="meta-llama/Llama-3.3-70B-Instruct",
messages=[
    {"role": "user", "content": "Tell me a joke."},
]
)

print("Chat response:", chat_response)

# Enjoy!