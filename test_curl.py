import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"API Key: {api_key[:30]}...")

url = "https://api.anthropic.com/v1/messages"
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

data = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Say hello!"}]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    print("\n✅ SUCCESS!")
    print(f"Claude says: {result['content'][0]['text']}")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)