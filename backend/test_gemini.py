import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "YOUR_GEMINI_API_KEY":
    print("API Key not found or still set to default.")
else:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Hello, this is a test. Reply precisely with: 'API IS WORKING'"
        )
        print("SUCCESS:", response.text.strip())
    except Exception as e:
        print(f"ERROR: {e}")
