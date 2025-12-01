import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure API
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in .env file")
    exit()

print(f"Using API Key: {api_key[:10]}...")
genai.configure(api_key=api_key)

# List all available models
print("\n=== Available Gemini Models ===\n")

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✓ {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Description: {model.description}")
            print()
except Exception as e:
    print(f"Error listing models: {e}")