import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Get your Google API key from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logging.error("Google API Key is missing! Make sure it's set in the .env file or environment.")
    raise RuntimeError("Missing GOOGLE_API_KEY")

try:
    # Configure Google Generative AI
    genai.configure(api_key=GOOGLE_API_KEY)
    logging.info("Google Gemini API successfully configured.")
except Exception as e:
    logging.error(f"Failed to configure Google Gemini API: {e}")
    raise RuntimeError("Error configuring Google Gemini API.")

# Removed VIDEO_ID_PATTERN

# Limits and constants used in the code
CONVERSATION_HISTORY_LIMIT = 5
SUMMARY_WORD_LIMIT = 500
MAX_TRANSCRIPT_LENGTH = 10000
