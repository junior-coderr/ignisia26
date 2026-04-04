import os
from google import genai

def test_vertex():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY in the environment before running this test")

    print("Testing google_genai initialization with the configured .env API key...")
    try:
        try:
            client = genai.Client(vertexai=True, api_key=api_key)
        except Exception:
            client = genai.Client(api_key=api_key)
        print("Initialized client")
        resp = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents='Hello, respond with yes'
        )
        print("Response:", resp.text)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    test_vertex()
