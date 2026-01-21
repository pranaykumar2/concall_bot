"""
Concall Results Bot - Production-Ready Implementation
Fetches quarterly results from Concall API and sends via Telegram
"""
import asyncio
import json
import logging
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pandas as pd
import pytz
import httpx
import aiofiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError, TimedOut
from telegram.request import HTTPXRequest
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception,
    before_sleep_log
)

import config
from image_generator import EnhancedNewsImageGenerator
from logger_config import setup_logger, print_box
from colorama import Fore

# Import Upcoming Results Job
from jobs.process_upcoming import fetch_and_process_upcoming

# Setup Logger
logger = setup_logger(__name__, config.LOG_DIR)



def normalize_company_name(name: str) -> str:
    """
    Normalize company name for fuzzy matching.
    Removes common suffixes, special characters, and standardizes format.
    
    Args:
        name: Company name to normalize
        
    Returns:
        Normalized company name for matching
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower().strip()
    
    # Expand common abbreviations before normalization
    abbreviations = {
        r'\bmngt\.?\b': 'management',
        r'\bgen\.?\b': 'general',
        r'\bintl\.?\b': 'international',
        r'\bintn\'?l\.?\b': 'international',
        r'\bpvt\.?\b': 'private',
        r'\bltd\.?\b': 'limited',
        r'\bcorp\.?\b': 'corporation',
        r'\bcorpn\.?\b': 'corporation',
        r'\binc\.?\b': 'incorporated',
        r'\bco\.?\b': 'company',
        r'\bmfg\.?\b': 'manufacturing',
        r'\bind\.?\b': 'industries',
        r'\bpharm\.?\b': 'pharmaceutical',  # Fixed: singular to match standard usage often (or handle fuzzy)
        r'\bpharma\.?\b': 'pharmaceutical',
        r'\btech\.?\b': 'technology',
        r'\btelec?o?m\.?\b': 'telecommunications',
        r'\beng\.?\b': 'engineering',
        r'\bdev\.?\b': 'development',
        r'\binfra\.?\b': 'infrastructure',
        # r'\bpetro\.?\b': 'petroleum', # Removed: Conflict with Petronet, use substring match
        r'\bauto\.?\b': 'automotive',
        r'\bsvc?s?\.?\b': 'services',
        r'\badmin\.?\b': 'administration',
        r'\bagri\.?\b': 'agriculture',
        r'\bassoc\.?\b': 'associates',
        r'\bchem\.?\b': 'chemicals',
        # r'\bcons\.?\b': 'construction', # Removed: Ambiguous with Consultancy, Consumer
        r'\bcomm\.?\b': 'communications',
        r'\bfert\.?\b': 'fertilizers',
        r'\bguj\.?\b': 'gujarat',
        r'\bdist\.?\b': 'distribution',
        r'\belec\.?\b': 'electrical',
        r'\bent\.?\b': 'enterprises',
        r'\bfin\.?\b': 'financial',
        r'\bhldg\.?\b': 'holdings',
        r'\binvest\.?\b': 'investment',
        r'\blab\.?\b': 'laboratories',
        r'\bmat\.?\b': 'materials',
        r'\bprod\.?\b': 'products',
        r'\bsoln\.?\b': 'solutions',
        r'\bsyst\.?\b': 'systems',
        r'\btrans\.?\b': 'transport',
        r'\bamc\b': 'asset management company',
        r'\bins\.?\b': 'insurance'
    }
    
    for abbr, full in abbreviations.items():
        normalized = re.sub(abbr, full, normalized, flags=re.IGNORECASE)
    
    # Remove common company suffixes
    suffixes = [
        r'\s+ltd\.?$', r'\s+limited$', r'\s+inc\.?$', r'\s+incorporated$',
        r'\s+corp\.?$', r'\s+corporation$', r'\s+company$', r'\s+co\.?$',
        r'\s+pvt\.?$', r'\s+private$', r'\s+public$', r'\s+plc$'
    ]
    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
    
    # Remove special characters but keep spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def fuzzy_match_company(api_name: str, nifty_companies: Set[str], 
                         company_map: Dict[str, str], threshold: float = 0.8) -> Optional[str]:
    """
    Match API company name with Nifty 500 companies using fuzzy matching.
    
    Args:
        api_name: Company name from API
        nifty_companies: Set of Nifty 500 company names
        company_map: Dict mapping normalized names to original names
        threshold: Minimum similarity threshold (not used in current implementation)
        
    Returns:
        Matched company name or None
    """
    if not api_name:
        return None
    
    # Strategy 1: Exact match (case-insensitive)
    for company in nifty_companies:
        if api_name.lower() == company.lower():
            logger.debug(f"Exact match: '{api_name}' -> '{company}'")
            return company
    
    # Normalize the API name
    api_normalized = normalize_company_name(api_name)
    
    # Strategy 2: Normalized exact match
    if api_normalized in company_map:
        matched = company_map[api_normalized]
        logger.debug(f"Normalized match: '{api_name}' -> '{matched}'")
        return matched
    
    # Strategy 3: Normalized Substring match (Improved)
    # Use normalized API name against normalized company names
    for normalized_name, original_name in company_map.items():
        # Check if API normalized name is in Company normalized name
        if api_normalized in normalized_name:
            if len(api_normalized) >= 5:
                logger.debug(f"Normalized substring match: '{api_name}' -> '{original_name}'")
                return original_name
        
        # Check if Company normalized name is in API normalized name
        elif normalized_name in api_normalized:
            if len(normalized_name) >= 5:
                # Be careful with short company names being substrings of long API descriptions
                logger.debug(f"Reverse normalized substring match: '{api_name}' -> '{original_name}'")
                return original_name
    
    # Strategy 4: Token-based match (all significant words match)
    api_tokens = set(api_normalized.split())
    # Filter out common words that don't help matching
    stop_words = {'and', 'the', 'of', 'in', 'for', 'with', 'on', 'at', 'to', 'a', 'an'}
    api_tokens = api_tokens - stop_words
    
    if not api_tokens:
        return None
    
    best_match = None
    best_score = 0
    
    for company in nifty_companies:
        company_normalized = normalize_company_name(company)
        company_tokens = set(company_normalized.split()) - stop_words
        
        if not company_tokens:
            continue
        
        # Calculate token overlap
        common_tokens = api_tokens & company_tokens
        if len(common_tokens) > 0:
            # Score based on proportion of API tokens matched
            score = len(common_tokens) / len(api_tokens)
            
            # Require at least 80% of API tokens to match
            if score >= threshold and score > best_score:
                best_score = score
                best_match = company
    
    if best_match:
        logger.debug(f"Token match ({best_score:.2%}): '{api_name}' -> '{best_match}'")
    
    return best_match


class DatabaseManager:
    """Manages SQLite database connections and operations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize the database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sent_companies (
                        composite_key TEXT PRIMARY KEY,
                        company_name TEXT,
                        description TEXT,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_str TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON sent_companies(date_str)")
                conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def get_sent_keys_for_date(self, date_str: str) -> Set[str]:
        """Get all composite keys sent on a specific date"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT composite_key FROM sent_companies WHERE date_str = ?", 
                    (date_str,)
                )
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Failed to fetch sent companies: {e}")
            return set()

    def mark_sent(self, companies: List[Dict[str, str]], date_str: str):
        """Mark companies as sent in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                data = [
                    (
                        f"{c['name']}|{c['description']}", 
                        c['name'], 
                        c['description'], 
                        date_str
                    ) 
                    for c in companies
                ]
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO sent_companies 
                    (composite_key, company_name, description, date_str) 
                    VALUES (?, ?, ?, ?)
                    """,
                    data
                )
                conn.commit()
                logger.debug(f"Marked {len(companies)} companies as sent in DB")
        except Exception as e:
            logger.error(f"Failed to mark companies as sent: {e}")


class ConcallResultsBot:
    """Main bot class for fetching and sending concall results"""
    
    def __init__(self):
        """Initialize the bot with configuration"""
        try:
            config.validate_config()
            
            # Telegram Bot Init
            request = HTTPXRequest(
                connection_pool_size=8,
                read_timeout=config.TELEGRAM_READ_TIMEOUT,
                write_timeout=config.TELEGRAM_WRITE_TIMEOUT,
                connect_timeout=config.TELEGRAM_CONNECT_TIMEOUT,
                pool_timeout=60.0
            )
            self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN, request=request)
            self.channel_id = config.TELEGRAM_CHANNEL_ID
            
            # HTTP Client Setup (httpx)
            # Network Engineer Grade Headers for BSE (Updated for 2026 Chrome 143)
            self.browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Referer": "https://www.bseindia.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Ch-Ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Priority": "u=0, i",
                "DNT": "1"
            }
            
            self.client = httpx.AsyncClient(
                headers=self.browser_headers, 
                timeout=config.PDF_DOWNLOAD_TIMEOUT, 
                follow_redirects=True,
                http2=False # Forced HTTP/1.1 for Stability (Solves Zombie Connection)
            )
            
            # Database Init
            self.db = DatabaseManager(config.DATA_DIR / "sent_companies.db")
            
            # Image Generator & Executor
            self.nifty_500_companies, self.nifty_500_normalized_map, self.nifty_500_symbol_map = self.load_nifty_500()
            self.image_generator = EnhancedNewsImageGenerator(
                show_brand=False,
                show_mesh_grid_background=True,
                brand_name="Concall Results"
            )
            # Executor for CPU-bound tasks (Image Gen)
            self.cpu_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="img_gen")
            
            print_box(logger, "Source: Concall Bot 2.0", {
                "Status": "Initialized",
                "Architecture": "Async I/O + SQLite",
                "Network": "HTTPX (Non-blocking)",
                "Persistence": "SQLite 3",
                "Compute": "ThreadPoolExecutor",
                "Nifty 500": f"{len(self.nifty_500_companies)} loaded"
            }, color=Fore.CYAN)
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        self.cpu_executor.shutdown(wait=False)

    def load_nifty_500(self) -> Tuple[Set[str], Dict[str, str], Dict[str, str]]:
        """
        Load company names from Nifty 500 CSV file with multiple lookup strategies.
        """
        try:
            df = pd.read_csv(config.NIFTY_500_CSV)
            
            # Extract company names
            companies = set(df['Company Name'].str.strip().tolist())
            
            # Create normalized name mapping
            normalized_map = {}
            for company in companies:
                normalized = normalize_company_name(company)
                normalized_map[normalized] = company
            
            # Create symbol to name mapping
            symbol_map = {}
            for _, row in df.iterrows():
                symbol = str(row['Symbol']).strip()
                company_name = str(row['Company Name']).strip()
                symbol_map[symbol] = company_name
            
            logger.info(f"Loaded {len(companies)} companies from Nifty 500 with {len(normalized_map)} normalized mappings")
            return companies, normalized_map, symbol_map
        except Exception as e:
            logger.error(f"Error loading Nifty 500 CSV: {e}")
            return set(), {}, {}
    
    def get_new_companies(self, all_companies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter companies to only return new ones not yet sent using SQLite
        """
        tz = pytz.timezone(config.TIMEZONE)
        today_str = datetime.now(tz).strftime('%Y-%m-%d')
        
        sent_keys = self.db.get_sent_keys_for_date(today_str)
        new_companies = []
        
        for c in all_companies:
            composite_key = f"{c['name']}|{c['description']}"
            if composite_key not in sent_keys:
                new_companies.append(c)
        
        if new_companies:
            logger.info(f"Found {len(new_companies)} new companies (out of {len(all_companies)} total)")
        else:
            logger.info(f"No new companies found ({len(all_companies)} already sent)")
        
        return new_companies
    
    def mark_companies_sent(self, companies: List[Dict[str, str]]):
        """Mark companies as sent in SQLite"""
        tz = pytz.timezone(config.TIMEZONE)
        today_str = datetime.now(tz).strftime('%Y-%m-%d')
        self.db.mark_sent(companies, today_str)
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=config.INITIAL_BACKOFF, max=config.MAX_BACKOFF),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def fetch_results(self) -> Optional[Dict]:
        """
        Fetch results from unauthenticated API endpoint using HTTPX
        """
        try:
            logger.info("Fetching data from API...")
            response = await self.client.post(
                config.API_URL,
                headers=config.API_HEADERS,
                json={},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Successfully fetched data")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching data: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error fetching data: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
    
    def is_today(self, date_str: str) -> bool:
        """Check if a date string matches today's date"""
        try:
            tz = pytz.timezone(config.TIMEZONE)
            today = datetime.now(tz).date()
            event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            return event_date == today
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {e}")
            return False
    
    def extract_companies(self, data: Dict) -> List[Dict[str, str]]:
        """
        Extract company data from API response data
        Filter by today's date
        """
        companies = []
        
        if 'content' in data and data['content']:
            events_with_date = data['content'][0].get('eventsWithDate', [])
            
            for date_group in events_with_date:
                for event in date_group.get('eventList', []):
                    # Get event details
                    company_name = event.get('companyName', '')
                    assent_name = event.get('assentName', '')
                    date_time = event.get('dateTime', '')
                    
                    if not self.is_today(date_time):
                        continue
                    
                    # Filter: Check if company is in Nifty 500
                    matched_company = None
                    
                    if config.NIFTY_FILTER:
                    # Strict Filter: Check first 4 chars against Nifty 500
                    # We expect self.nifty_500_companies to be a set of full names.
                    # Ideally, we should pre-compute the 4-char prefixes for O(1) lookup.
                    # For now, we iterate, which is acceptable for 500 items.
                    
                        company_prefix = company_name[:4].lower()
                        assent_prefix = assent_name[:4].lower() if assent_name else ""
                        
                        match_found = False
                        
                        # Check Company Name Prefix
                        for nifty_co in self.nifty_500_companies:
                            nifty_prefix = nifty_co[:4].lower()
                            
                            if len(company_prefix) >= 4 and company_prefix == nifty_prefix:
                                matched_company = nifty_co
                                match_found = True
                                break
                            
                            # Fallback to Assent Name Prefix
                            if len(assent_prefix) >= 4 and assent_prefix == nifty_prefix:
                                matched_company = nifty_co
                                match_found = True
                                break
                                
                        if match_found:
                            logger.debug(f"Prefix match (4-char): API '{company_name}' -> Nifty '{matched_company}'")
                        else:
                            logger.debug(f"Skipping {company_name} - No Nifty 500 match (First 4 chars mismatch)")
                            continue
                    else:
                        # If filtering is disabled, take the API name as is (or maybe prefer assent_name if available?)
                        # Keeping original logic flow but skipping the check
                        pass
                    
                    result_description = event.get('resultDescription', '')
                    
                    # Check for duplicates in current batch
                    is_duplicate = False
                    for existing in companies:
                        if existing['name'] == company_name and existing['description'] == result_description:
                            is_duplicate = True
                            break
                    
                    if company_name and not is_duplicate:
                        result_link = event.get('resultLink', '')
                        companies.append({
                            'name': company_name,
                            'description': result_description,
                            'resultLink': result_link,
                            'dateTime': date_time
                        })
                        logger.info(f"Added company: {company_name} - Date: {date_time}")
        
        companies.sort(key=lambda x: x['dateTime'])
        return companies
    

    
    def format_telegram_message(self, companies: List[str]) -> str:
        """Format the Telegram message with company names"""
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        if not companies:
            companies_text = "No results found for today."
        else:
            companies_text = "\n".join(f"• {company}" for company in companies)
        
        message = config.MESSAGE_TEMPLATE.format(
            companies=companies_text,
            date=now.strftime('%d %B %Y'),
            time=now.strftime('%I:%M %p %Z')
        )
        return message
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(TelegramError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def send_telegram_message(self, message: str, parse_mode: str = None) -> bool:
        """Send message to Telegram channel"""
        try:
            logger.info("Sending message to Telegram channel...")
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("Message sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(TelegramError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def send_telegram_image(self, image_bytes, caption: str = None) -> bool:
        """Send image to Telegram channel"""
        try:
            logger.info("Sending image to Telegram channel...")
            image_bytes.seek(0)
            await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=image_bytes,
                caption=caption,
                read_timeout=600,
                write_timeout=600,
                connect_timeout=60
            )
            logger.info("Image sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending image: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(TelegramError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def send_telegram_album(self, media_group: List[InputMediaPhoto]) -> bool:
        """Send a media group (album) to Telegram"""
        try:
            logger.info(f"Sending album of {len(media_group)} images to Telegram...")
            await self.bot.send_media_group(
                chat_id=self.channel_id,
                media=media_group,
                read_timeout=600,
                write_timeout=600,
                connect_timeout=60
            )
            logger.info("Album sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error sending album: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending album: {e}")
            return False

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, max=15),
        retry=retry_if_exception(lambda x: isinstance(x, TelegramError) and not isinstance(x, TimedOut)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def send_telegram_document(self, file_path: Path, caption: str = None) -> bool:
        """Send document/PDF to Telegram channel"""
        try:
            logger.info(f"Sending document {file_path.name} to Telegram channel...")
            # Optimized: Stream file directly to prevent RAM spikes (Fixed OOM)
            with open(file_path, 'rb') as f:
                content = f # Pass file handle directly
                
                await self.bot.send_document(
                    chat_id=self.channel_id,
                    document=content,
                    filename=file_path.name,
                    caption=caption,
                    read_timeout=600,
                    write_timeout=600,
                    connect_timeout=60
                )
            logger.info("Document sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending document: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def download_pdf(self, url: str, output_path: Path) -> bool:
        """
        Stream download PDF from URL using HTTPX with fallback support
        """
        logger.info(f"Downloading PDF from {url}")
        
        try:
            async with self.client.stream('GET', url) as response:
                response.raise_for_status()
                async with aiofiles.open(output_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        await f.write(chunk)
            
            logger.info(f"PDF saved to {output_path}")
            return True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Primary link 404s. Attempting fallback for {url}")
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    
                    if 'Pname' in params:
                        pname = params['Pname'][0]
                        fallback_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{pname}"
                        
                        logger.info(f"Trying fallback URL: {fallback_url}")
                        async with self.client.stream('GET', fallback_url) as fb_response:
                            fb_response.raise_for_status()
                            async with aiofiles.open(output_path, 'wb') as f:
                                async for chunk in fb_response.aiter_bytes(chunk_size=8192):
                                    await f.write(chunk)
                        
                        logger.info(f"PDF saved from fallback to {output_path}")
                        return True
                except Exception as fallback_error:
                    logger.error(f"Fallback failed: {fallback_error}")
            
            raise e
    
    def generate_pdf_filename(self, company_name: str, description: str) -> str:
        """Generate PDF filename based on company name and description"""
        result_type = "consolidated" if "consolidated" in description.lower() else "standalone"
        period_info = None
        
        pattern1 = r'Quarter ended ([A-Za-z]+) (\d{4})'
        match = re.search(pattern1, description, re.IGNORECASE)
        if match:
            month = match.group(1)
            year = match.group(2)
            period_info = f"Quarter {month} {year}"
        else:
            pattern2 = r'Half-Yearly ended ([A-Za-z]+) (\d{4})'
            match = re.search(pattern2, description, re.IGNORECASE)
            if match:
                month = match.group(1)
                year = match.group(2)
                period_info = f"Half-Yearly {month} {year}"
            else:
                pattern3 = r'([^:]*results)'
                match = re.search(pattern3, description, re.IGNORECASE)
                if match:
                    period_text = match.group(1).strip()
                    period_text = re.sub(r'^(for|the)\s+', '', period_text, flags=re.IGNORECASE)
                    period_info = period_text
        
        if not period_info:
            period_info = "Results"
            
        # Clean filename
        safe_company = re.sub(r'[^\w\s-]', '', company_name).strip()
        safe_period = re.sub(r'[^\w\s-]', '', period_info).strip()
        
        return f"{safe_company} {result_type} {safe_period}.pdf"

    async def run_job(self):
        """Execute the bot job safely with Album support"""
        try:
            # 1. Fetch data
            data = await self.fetch_results()
            if not data:
                return

            # 2. Extract and Filter New Companies
            companies = self.extract_companies(data)
            
            # Offload DB call to executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            new_companies = await loop.run_in_executor(None, self.get_new_companies, companies)
            
            if not new_companies:
                logger.info("No new updates found")
                return

            logger.info(f"Processing {len(new_companies)} new updates...")
            
            # 3. Generate All Images First (Concurrently)
            processed_items = [] # List of tuples: (company_dict, image_bytes)
            
            loop = asyncio.get_running_loop()
            
            # Generate images for all new companies
            for company in new_companies:
                try:
                    logger.info(f"Generating image for {company['name']}...")
                    image_bytes = await loop.run_in_executor(
                        self.cpu_executor,
                        self.image_generator.generate_news_image,
                        company['name'],
                        company['description'],
                        ""
                    )
                    processed_items.append((company, image_bytes))
                    
                except Exception as e:
                    logger.error(f"Failed to generate image for {company['name']}: {e}")
                    continue

            if not processed_items:
                logger.warning("No images generated successfully. Exiting job.")
                return

            # 4. Sequential Sending Logic (Strict Order: Image -> PDF -> Next)
            logger.info("Starting sequential sending...")
            
            for company, img_bytes in processed_items:
                try:
                    # A. Send Image (No Caption)
                    if await self.send_telegram_image(img_bytes, caption=None):
                        # B. Download and Send PDF
                        await self._process_pdf_delivery(company)
                        
                        # C. Mark Sent (Offload to thread)
                        await loop.run_in_executor(None, self.mark_companies_sent, [company])
                        
                        # Rate limiting between companies
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    logger.error(f"Error sending data for {company['name']}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Job execution failed: {e}")

    async def _process_pdf_delivery(self, company: Dict[str, str]):
        """Helper to download and send PDF for a company"""
        if not company.get('resultLink'):
            return

        try:
            pdf_filename = self.generate_pdf_filename(company['name'], company['description'])
            pdf_path = config.PDF_DOWNLOAD_DIR / pdf_filename
            
            # Download
            if await self.download_pdf(company['resultLink'], pdf_path):
                
                # Send with minimal caption or just filename? 
                # User preference seems to be No Caption for single/simple items.
                try:
                    sent = await self.send_telegram_document(pdf_path, caption=None)
                    if not sent:
                        raise Exception("Document send returned False (Unknown Error)")
                except Exception as e:
                    # If sending fails (e.g. timeout), re-raise to trigger fallback
                    logger.error(f"Failed to send document to Telegram: {e}")
                    raise e
                finally:
                    # Cleanup PDF
                    try:
                        if pdf_path.exists():
                            pdf_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete PDF {pdf_path}: {e}")

        except Exception as e:
            logger.error(f"Error processing PDF for {company['name']}: {e}")
            
            # Fallback: Send Text Link
            try:
                # Escape special characters for MarkdownV2 if needed, or use 'Markdown'
                # Simple Markdown is easier for links: [text](url)
                fallback_msg = (
                    f"⚠️ *PDF Upload Failed*\n"
                    f"Could not upload the results PDF for {company['name']}.\n\n"
                    f"🔗 [Click here to download PDF]({company['resultLink']})"
                )
                await self.send_telegram_message(fallback_msg, parse_mode='Markdown')
                logger.info(f"Sent fallback link for {company['name']}")
            except Exception as fb_error:
                logger.error(f"Failed to send fallback link: {fb_error}")
            
            # Do NOT re-raise, so we continue to mark as sent
            return

async def main():
    """Main entry point"""
    try:
        bot = ConcallResultsBot()
        
        # Setup scheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(bot.run_job, CronTrigger(minute=f'*/{config.CHECK_INTERVAL_MINUTES}'))  # Check every N minutes
        
        # Schedule Upcoming Results
        # fetch_and_process_upcoming handles its own "Tomorrow" logic
        upcoming_hour, upcoming_minute = map(int, config.UPCOMING_SCHEDULE_TIME.split(':'))
        scheduler.add_job(fetch_and_process_upcoming, CronTrigger(hour=upcoming_hour, minute=upcoming_minute, timezone=config.TIMEZONE))
        
        scheduler.start()
        
        logger.info("Concall Bot Scheduler Started (Async)")
        
        
        # Send startup message - REMOVED per user request
        # await bot.send_telegram_message(
        #     f"🤖 **Concall Results Bot Started**\n"
        #     f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        #     f"🚀 Mode: Async/Non-blocking\n"
        #     f"💾 DB: SQLite"
        # )
        
        
        # Keep alive
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping bot...")
            await bot.cleanup()
            
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure data directory exists
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.run(main())