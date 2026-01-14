"""
Configuration management for Concall Results Bot
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / os.getenv('DATA_DIR', 'data')
LOG_DIR = BASE_DIR / os.getenv('LOG_DIR', 'logs')
PDF_DOWNLOAD_DIR = BASE_DIR / os.getenv('PDF_DOWNLOAD_DIR', 'pdfs') # Added PDF_DOWNLOAD_DIR

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
PDF_DOWNLOAD_DIR.mkdir(exist_ok=True) # Ensure PDF_DOWNLOAD_DIR is created

# Sent companies tracking file
SENT_COMPANIES_FILE = DATA_DIR / 'sent_companies_today.json'

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# API Endpoint
API_URL = "https://api.concall.in/leap/fetch/liveResults?page=0&size=40&sector=All&marketCap=All"

# API Headers
API_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Origin": "https://concall.in",
    "Referer": "https://concall.in/"
}

# Nifty 500 CSV file path
NIFTY_500_CSV = BASE_DIR / 'nifty_500.csv'

# Scheduling Configuration
SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '07:30')
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '5'))

# Retry Configuration
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '5'))
INITIAL_BACKOFF = int(os.getenv('INITIAL_BACKOFF', '1'))
MAX_BACKOFF = int(os.getenv('MAX_BACKOFF', '300'))

# Message Template
MESSAGE_TEMPLATE = """FY26 Q3 Corporate Earnings - Live

{companies}

📅 Date: {date}
⏰ Update: {time}"""

# Image Generator Configuration
# Font Sizes (in points)
FONT_TAG_SIZE = int(os.getenv('FONT_TAG_SIZE', '24'))
FONT_TITLE_SIZE = int(os.getenv('FONT_TITLE_SIZE', '40'))
FONT_DESCRIPTION_SIZE = int(os.getenv('FONT_DESCRIPTION_SIZE', '28'))
FONT_BRAND_SIZE = int(os.getenv('FONT_BRAND_SIZE', '16'))

# Font Styles (weights)
FONT_TAG_STYLE = os.getenv('FONT_TAG_STYLE', '700')
FONT_TITLE_STYLE = os.getenv('FONT_TITLE_STYLE', '600')
FONT_DESCRIPTION_STYLE = os.getenv('FONT_DESCRIPTION_STYLE', '400')
FONT_BRAND_STYLE = os.getenv('FONT_BRAND_STYLE', '600')

# Font Families
FONT_TAG_FAMILY = os.getenv('FONT_TAG_FAMILY', 'Montserrat')
FONT_TITLE_FAMILY = os.getenv('FONT_TITLE_FAMILY', 'Bricolage Grotesque')
FONT_DESCRIPTION_FAMILY = os.getenv('FONT_DESCRIPTION_FAMILY', 'Onest')
FONT_BRAND_FAMILY = os.getenv('FONT_BRAND_FAMILY', 'Gantari')

# Google Fonts CDN URL
GOOGLE_FONTS_CSS_URL = os.getenv('GOOGLE_FONTS_CSS_URL', '')

# Colors (RGB format: R,G,B)
BG_BLACK = os.getenv('BG_BLACK', '20,20,25')
BG_GREY = os.getenv('BG_GREY', '45,45,50')
CARD_BG = os.getenv('CARD_BG', '255,255,255')
TAG_BG_COLOR = os.getenv('TAG_BG_COLOR', '20,20,25')
TAG_TEXT_COLOR = os.getenv('TAG_TEXT_COLOR', '255,255,255')
TITLE_COLOR = os.getenv('TITLE_COLOR', '0,51,102')
DESCRIPTION_COLOR = os.getenv('DESCRIPTION_COLOR', '80,80,85')
BRAND_COLOR = os.getenv('BRAND_COLOR', '20,20,25')
SKY_BLUE = os.getenv('SKY_BLUE', '87,167,255')
LIGHT_GREEN = os.getenv('LIGHT_GREEN', '50,205,50')

def validate_config():
    """Validate required configuration variables"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'your_bot_token_here':
        errors.append("TELEGRAM_BOT_TOKEN is not configured")
    
    if not TELEGRAM_CHANNEL_ID or TELEGRAM_CHANNEL_ID == 'your_channel_id_here':
        errors.append("TELEGRAM_CHANNEL_ID is not configured")
    
    if not NIFTY_500_CSV.exists():
        errors.append("NIFTY_500_CSV file not found")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return True
