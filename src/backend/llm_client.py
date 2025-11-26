import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self, provider="gemini"):
        self.provider = provider
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            # Fallback or warning
            print("Warning: GOOGLE_API_KEY not found in environment.")
        
        if self.provider == "gemini":
            genai.configure(api_key=self.api_key)
            # Use the latest flash alias which was confirmed in the list
            self.model = genai.GenerativeModel('gemini-flash-latest')

    def generate_response(self, prompt: str) -> str:
        if self.provider == "gemini":
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error generating response: {e}"
        return "Unsupported provider"

if __name__ == "__main__":
    client = LLMClient()
    # print(client.generate_response("Hello, are you working?"))
