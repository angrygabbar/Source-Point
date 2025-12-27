from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
else:
    client = genai.Client(api_key=api_key)
    try:
        print(f"Authenticated with API Key: ...{api_key[-5:]}")
        print("Fetching available models...")
        
        # In the new SDK, we just iterate and print the name
        # The models returned here are generally available for use
        for m in client.models.list():
            print(f" - {m.name}")
            
    except Exception as e:
        print(f"Error: {e}")