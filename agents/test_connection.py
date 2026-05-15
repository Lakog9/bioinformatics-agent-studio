import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=100,
    messages=[{"role": "user", "content": "Reply with exactly: 'Connection working.'"}]
)

print(response.content[0].text)
print(f"\nTokens used: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
