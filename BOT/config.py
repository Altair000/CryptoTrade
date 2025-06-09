from dotenv import load_dotenv
import os

load_dotenv()

class BotConfig:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    API_URL = os.getenv("API_URL")