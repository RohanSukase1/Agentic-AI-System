import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read values from .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in .env")