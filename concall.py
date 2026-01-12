"""
Concall Results Bot - Production-Ready Implementation
Fetches quarterly results from Concall API and sends via Telegram
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import pytz
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.error import TelegramError, TimedOut
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
from logger_config import setup_logger, print_box, log_tree
from colorama import Fore

# Setup Logger
logger = setup_logger(__name__, config.LOG_DIR)


class ConcallResultsBot:
    """Main bot class for fetching and sending concall results"""
    
    def __init__(self):
        """Initialize the bot with configuration"""
        try:
            config.validate_config()
            # Increase timeout for large file uploads (PDFs)
            from telegram.request import HTTPXRequest
            request = HTTPXRequest(
                connection_pool_size=8,
                read_timeout=300.0,
                write_timeout=300.0,
                connect_timeout=60.0,
                pool_timeout=60.0
            )
            self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN, request=request)
            self.channel_id = config.TELEGRAM_CHANNEL_ID
            self.session = requests.Session()
            
            # Network Engineer Grade Headers for BSE
            self.browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.bseindia.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"'
            }
            self.session.headers.update(self.browser_headers)
            
            # Prime session with cookies
            try:
                self.session.get("https://www.bseindia.com/", timeout=30)
                logger.info("Session primed with BSE cookies")
            except Exception as e:
                logger.warning(f"Failed to prime session cookies: {e}")

            self.sent_companies = self.load_sent_companies()
            self.nifty_500_companies = self.load_nifty_500()
            self.image_generator = EnhancedNewsImageGenerator(
                show_brand=False,
                show_mesh_grid_background=True,
                brand_name="Concall Results"
            )
            print_box(logger, "Source: Concall Bot", {
                "Status": "Initialized",
                "Mode": "Sequential Flow",
                "Sent Cache": f"{len(self.sent_companies.get('companies', []))} companies",
                "Nifty 500": f"{len(self.nifty_500_companies)} loaded"
            }, color=Fore.CYAN)
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def load_nifty_500(self) -> Set[str]:
        """
        Load company names from Nifty 500 CSV file
        
        Returns:
            Set of company names in Nifty 500
        """
        try:
            df = pd.read_csv(config.NIFTY_500_CSV)
            # Extract company names and convert to a set for faster lookup
            companies = set(df['Company Name'].str.strip().tolist())
            logger.info(f"Loaded {len(companies)} companies from Nifty 500")
            return companies
        except Exception as e:
            logger.error(f"Error loading Nifty 500 CSV: {e}")
            return set()
    
    def load_sent_companies(self) -> Dict[str, List[str]]:
        """
        Load the list of companies already sent today
        
        Returns:
            Dictionary with date as key and list of company names as value
        """
        try:
            if config.SENT_COMPANIES_FILE.exists():
                with open(config.SENT_COMPANIES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if data is for today
                    tz = pytz.timezone(config.TIMEZONE)
                    today = datetime.now(tz).strftime('%Y-%m-%d')
                    if data.get('date') == today:
                        return data
                    else:
                        # Different day, start fresh
                        logger.info("Starting new day - clearing sent companies list")
                        return {'date': today, 'companies': []}
            else:
                tz = pytz.timezone(config.TIMEZONE)
                today = datetime.now(tz).strftime('%Y-%m-%d')
                return {'date': today, 'companies': []}
        except Exception as e:
            logger.error(f"Error loading sent companies: {e}")
            tz = pytz.timezone(config.TIMEZONE)
            today = datetime.now(tz).strftime('%Y-%m-%d')
            return {'date': today, 'companies': []}
    
    def save_sent_companies(self):
        """
        Save the list of sent companies to file
        """
        try:
            with open(config.SENT_COMPANIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sent_companies, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.sent_companies.get('companies', []))} sent companies to file")
        except Exception as e:
            logger.error(f"Error saving sent companies: {e}")
    
    def get_new_companies(self, all_companies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter companies to only return new ones not yet sent
        
        Args:
            all_companies: List of all companies found today
            
        Returns:
            List of companies not yet sent
        """
        sent_list = self.sent_companies.get('companies', [])
        new_companies = []
        
        for c in all_companies:
            # Create composite key: Name|Description
            # This allows same company to send different results (e.g. Standalone vs Consolidated)
            composite_key = f"{c['name']}|{c['description']}"
            
            # Check for exact match of composite key (new format)
            # OR Check for name match only if description is not in sent_list (backward compatibility check is tricky)
            # We strictly check if the composite key exists.
            # If the user has old "NameOnly" entries, they won't match "Name|Desc", so it might resend once.
            # This is acceptable per implementation plan.
            
            if composite_key not in sent_list:
                new_companies.append(c)
        
        if new_companies:
            logger.info(f"Found {len(new_companies)} new companies (out of {len(all_companies)} total)")
        else:
            logger.info(f"No new companies found ({len(all_companies)} already sent)")
        
        return new_companies
    
    def mark_companies_sent(self, companies: List[Dict[str, str]]):
        """
        Add companies to the sent list using composite key
        
        Args:
            companies: List of company data to mark as sent
        """
        current_list = self.sent_companies.get('companies', [])
        for company in companies:
            # Store composite key
            composite_key = f"{company['name']}|{company['description']}"
            if composite_key not in current_list:
                current_list.append(composite_key)
        
        self.sent_companies['companies'] = current_list
        self.save_sent_companies()
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(
            multiplier=config.INITIAL_BACKOFF,
            max=config.MAX_BACKOFF
        ),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_results(self) -> Optional[Dict]:
        """
        Fetch results from unauthenticated API endpoint with retry logic
        
        Returns:
            Dictionary containing API response data
        """
        try:
            logger.info("Fetching data from API...")
            response = self.session.post(
                config.API_URL,
                headers=config.API_HEADERS,
                json={},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Successfully fetched data")
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching data: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching data: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
    
    def is_today(self, date_str: str) -> bool:
        """
        Check if a date string matches today's date
        
        Args:
            date_str: Date string in ISO format (e.g., "2026-01-07T15:44:27")
            
        Returns:
            True if the date is today, False otherwise
        """
        try:
            tz = pytz.timezone(config.TIMEZONE)
            today = datetime.now(tz).date()
            
            # Parse the date string
            event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            
            return event_date == today
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {e}")
            return False
    
    def extract_companies(self, data: Dict) -> List[Dict[str, str]]:
        """
        Extract company data from API response data
        Filter by today's date
        
        Args:
            data: Dictionary with API response data
            
        Returns:
            List of dictionaries with company name and description, sorted by dateTime (oldest to newest)
        """
        companies = []
        
        if 'content' in data and data['content']:
            events_with_date = data['content'][0].get('eventsWithDate', [])
            
            for date_group in events_with_date:
                for event in date_group.get('eventList', []):
                    # Get event details
                    company_name = event.get('companyName', '')
                    assent_name = event.get('assentName', '')  # This is the key field to match
                    date_time = event.get('dateTime', '')
                    
                    # Filter 1: Check if announcement is today
                    if not self.is_today(date_time):
                        logger.debug(f"Skipping {company_name} - Date '{date_time}' is not today")
                        continue
                    
                    # Filter 2: Check if company is in Nifty 500 (COMMENTED OUT)
                    # Try matching both companyName and assentName
                    # is_in_nifty_500 = (
                    #     company_name in self.nifty_500_companies or 
                    #     assent_name in self.nifty_500_companies
                    # )
                    # 
                    # if not is_in_nifty_500:
                    #     logger.debug(f"Skipping {company_name} ({assent_name}) - Not in Nifty 500")
                    #     continue
                    
                    # Add company if it meets criteria and not already in list
                    # Logic changed: Check if (name, description) combination exists, not just name
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
        
        # Sort companies by dateTime (oldest to newest) so A->B->C->D
        companies.sort(key=lambda x: x['dateTime'])
        
        return companies
    
    def save_to_json(self, data: Dict, companies: List[str]) -> Path:
        """
        Save fetched data to JSON file for archival
        
        Args:
            data: Raw API response data
            companies: Extracted company names
            
        Returns:
            Path to the saved JSON file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = config.DATA_DIR / f'results_{timestamp}.json'
        
        output_data = {
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "companies_count": len(companies),
            "companies": companies,
            "raw_data": data
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save data to JSON: {e}")
            raise
    
    def format_telegram_message(self, companies: List[str]) -> str:
        """
        Format the Telegram message with company names
        
        Args:
            companies: List of company names
            
        Returns:
            Formatted message string
        """
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
    async def send_telegram_message(self, message: str) -> bool:
        """
        Send message to Telegram channel with retry logic
        
        Args:
            message: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Sending message to Telegram channel...")
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=None
            )
            logger.info("Message sent successfully to Telegram")
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
        """
        Send image to Telegram channel with retry logic
        
        Args:
            image_bytes: BytesIO object containing the image
            caption: Optional caption for the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Sending image to Telegram channel...")
            image_bytes.seek(0)  # Reset position
            await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=image_bytes,
                caption=caption,
                read_timeout=600,
                write_timeout=600,
                connect_timeout=60
            )
            logger.info("Image sent successfully to Telegram")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending image: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, max=15),
        retry=retry_if_exception(lambda x: isinstance(x, TelegramError) and not isinstance(x, TimedOut)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def send_telegram_document(self, file_path: Path, caption: str = None) -> bool:
        """
        Send document/PDF to Telegram channel with retry logic
        
        Args:
            file_path: Path to the document file
            caption: Optional caption for the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Sending document {file_path.name} to Telegram channel...")
            with open(file_path, 'rb') as doc:
                await self.bot.send_document(
                    chat_id=self.channel_id,
                    document=doc,
                    caption=caption,
                    read_timeout=600,
                    write_timeout=600,
                    connect_timeout=60
                )
            logger.info("Document sent successfully to Telegram")
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
        retry=retry_if_exception_type((requests.RequestException, ConnectionError, ConnectionResetError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def download_pdf(self, url: str, output_path: Path) -> bool:
        """
        Download PDF from URL using primed session with fallback support
        
        Args:
            url: URL to download PDF from
            output_path: Path to save the PDF
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading PDF from {url}")
        
        try:
            # Session already has headers and cookies from __init__
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"PDF saved to {output_path}")
            return True
            
        except requests.exceptions.HTTPError as e:
            # Check if 404 and if we can try a fallback
            if e.response.status_code == 404:
                logger.warning(f"Primary link 404s. Attempting fallback for {url}")
                
                # BSE Fallback Logic: Convert AnnPdfOpen.aspx link to direct AttachLive link
                # Original: https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=GUID.pdf
                # Fallback: https://www.bseindia.com/xml-data/corpfiling/AttachLive/GUID.pdf
                
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    
                    if 'Pname' in params:
                        pname = params['Pname'][0]
                        fallback_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{pname}"
                        
                        logger.info(f"Trying fallback URL: {fallback_url}")
                        fallback_response = self.session.get(fallback_url, timeout=60)
                        fallback_response.raise_for_status()
                        
                        with open(output_path, 'wb') as f:
                            f.write(fallback_response.content)
                            
                        logger.info(f"PDF saved from fallback to {output_path}")
                        return True
                except Exception as fallback_error:
                    logger.error(f"Fallback failed: {fallback_error}")
            
            # Re-raise original error if fallback didn't work/apply
            raise e
    
    def generate_pdf_filename(self, company_name: str, description: str) -> str:
        """
        Generate PDF filename based on company name and description
        Format: {company name} {standalone/consolidated} {period info}.pdf
        
        Args:
            company_name: Name of the company
            description: Result description containing period info
            
        Returns:
            Generated filename
        """
        import re
        
        # Extract type (consolidated or standalone)
        result_type = "consolidated" if "consolidated" in description.lower() else "standalone"
        
        # Try to extract period information using various patterns
        period_info = None
        
        # Pattern 1: "Quarter ended [Month] [Year]"
        pattern1 = r'Quarter ended ([A-Za-z]+) (\d{4})'
        match = re.search(pattern1, description, re.IGNORECASE)
        if match:
            month = match.group(1)
            year = match.group(2)
            period_info = f"Quarter {month} {year}"
        else:
            # Pattern 2: "Half-Yearly ended [Month] [Year]"
            pattern2 = r'Half-Yearly ended ([A-Za-z]+) (\d{4})'
            match = re.search(pattern2, description, re.IGNORECASE)
            if match:
                month = match.group(1)
                year = match.group(2)
                period_info = f"Half-Yearly {month} {year}"
            else:
                # Pattern 3: Try to extract any sentence ending with "results"
                pattern3 = r'([^:]*results)'
                match = re.search(pattern3, description, re.IGNORECASE)
                if match:
                    # Use the matched text but clean it up
                    period_text = match.group(1).strip()
                    # Remove common prefixes and clean up
                    period_text = re.sub(r'^(for|the)\s+', '', period_text, flags=re.IGNORECASE)
                    period_info = period_text
        
        # Construct filename with spaces as separators
        if period_info:
            filename = f"{company_name} {result_type} {period_info}.pdf"
        else:
            # Fallback if pattern not found
            filename = f"{company_name} {result_type}.pdf"
        
        # Clean filename (remove invalid characters but keep spaces)
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        return filename

    async def run_job(self):
        """Main job execution - fetch data and send to Telegram if new companies found"""
        try:
            logger.info("="*80)
            logger.info("Starting scheduled check")
            logger.info("="*80)
            
            # Get current date for logging
            tz = pytz.timezone(config.TIMEZONE)
            today = datetime.now(tz)
            logger.info(f"Checking results for date: {today.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Fetch results from API
            data = self.fetch_results()
            
            if not data:
                logger.warning("No data fetched from API")
                return
            
            # Extract company names (filtered by today's date and Nifty 500)
            all_companies = self.extract_companies(data)
            
            # Get only NEW companies not yet sent
            new_companies = self.get_new_companies(all_companies)
            
            # Box Summary for the check
            print_box(logger, "Scheduled Check", {
                "Time": today.strftime('%H:%M:%S'),
                "Total Found": len(all_companies),
                "New Results": len(new_companies)
            }, color=Fore.GREEN if new_companies else Fore.WHITE)
            
            if not new_companies:
                return
            
            # Save to JSON
            self.save_to_json(data, new_companies)
            
            # Generate and send image for each NEW company
            for company_data in new_companies:
                try:
                    company_name = company_data['name']
                    description = company_data['description']
                    result_link = company_data.get('resultLink', '')
                    
                    logger.info(f"Processing: {company_name}")
                    
                    # Generate and send image
                    logger.info(f"Generating image for {company_name}")
                    image_bytes = self.image_generator.generate_news_image(
                        title=company_name,
                        description=description,
                        timestamp="FY26 Q3"
                    )
                    await self.send_telegram_image(image_bytes)
                    
                    # Log with tree style
                    log_tree(logger, f"✅ Sent Image: {company_name}", level="SENT")
                    
                    # Flow Delay: Wait for image to settle
                    await asyncio.sleep(3)
                    
                    # Download and send PDF if result link is available
                    if result_link:
                        pdf_path = None
                        try:
                            # Generate PDF filename
                            pdf_filename = self.generate_pdf_filename(company_name, description)
                            pdf_path = config.DATA_DIR / pdf_filename
                            
                            # Download PDF
                            if self.download_pdf(result_link, pdf_path):
                                # Check file size (Telegram limit is 50MB, we'll set a safe limit)
                                file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                                
                                if file_size_mb > 45:
                                    logger.warning(f"PDF too large ({file_size_mb:.2f}MB), skipping send for {company_name}")
                                else:
                                    # Send PDF to Telegram
                                    try:
                                        await self.send_telegram_document(pdf_path)
                                        log_tree(logger, f"📄 Sent PDF: {company_name}", level="SENT")
                                        # Flow Delay: Wait after PDF send
                                        await asyncio.sleep(3)
                                    except Exception as send_error:
                                        logger.error(f"Failed to send PDF for {company_name}: {send_error}")
                            else:
                                logger.warning(f"Failed to download PDF for {company_name}")
                        except Exception as pdf_error:
                            logger.error(f"PDF processing error for {company_name}: {pdf_error}")
                        finally:
                            # Always try to delete PDF file, even if sending failed
                            if pdf_path and pdf_path.exists():
                                try:
                                    pdf_path.unlink()
                                    logger.info(f"Deleted PDF file: {pdf_path.name}")
                                except Exception as del_error:
                                    logger.error(f"Failed to delete PDF {pdf_path.name}: {del_error}")
                    else:
                        logger.info(f"No result link available for {company_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to process {company_data['name']}: {e}", exc_info=True)
                    continue
            
            # Mark these companies as sent
            self.mark_companies_sent(new_companies)
            
            # Final Box Summary
            print_box(logger, "Process Complete", {
                "Sent": f"{len(new_companies)} companies",
                "Status": "Waiting for next cycle"
            }, color=Fore.GREEN)
            
        except Exception as e:
            logger.error(f"Job execution failed: {e}", exc_info=True)
            # Send error notification
            error_message = f"⚠️ Error checking results:\n{str(e)}"
            try:
                await self.send_telegram_message(error_message)
            except:
                logger.error("Failed to send error notification")
    
    async def start_scheduler(self, use_interval: bool = True):
        """
        Start the scheduler for automated execution
        
        Args:
            use_interval: If True, run every N minutes. If False, run once daily at specific time.
        """
        scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
        
        if use_interval:
            # Run every N minutes
            interval_minutes = config.CHECK_INTERVAL_MINUTES
            scheduler.add_job(
                self.run_job,
                trigger='interval',
                minutes=interval_minutes,
                id='interval_concall_check',
                name=f'Check Concall Results Every {interval_minutes} Minutes',
                replace_existing=True
            )
            logger.info(f"Scheduler started - Job will run every {interval_minutes} minutes")
            
            # Run immediately on startup
            logger.info("Running initial check...")
            await self.run_job()
        else:
            # Run once daily at specific time
            hour, minute = map(int, config.SCHEDULE_TIME.split(':'))
            scheduler.add_job(
                self.run_job,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=config.TIMEZONE),
                id='daily_concall_fetch',
                name='Fetch Concall Results Daily',
                replace_existing=True
            )
            logger.info(f"Scheduler started - Job will run daily at {config.SCHEDULE_TIME} {config.TIMEZONE}")
        
        scheduler.start()
        
        try:
            # Keep the script running
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler...")
            scheduler.shutdown()


async def main():
    """Main entry point"""
    try:
        bot = ConcallResultsBot()
        
        # Check command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == '--run-once':
            # Run immediately without scheduling
            logger.info("Running in one-time mode")
            await bot.run_job()
        else:
            # Start scheduler
            logger.info("Starting in scheduled mode")
            await bot.start_scheduler()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run with asyncio
    asyncio.run(main())