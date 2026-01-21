
import asyncio
import logging
import datetime
import sys
import os
import httpx

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from services.upcoming_impact_generator import UpcomingImpactGenerator
from telegram import Bot
import json

# Setup logging
# Setup logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fetch_and_process_upcoming():
    """
    Fetches upcoming results for TOMORROW and sends image if data exists.
    """
    # 1. Calculate Tomorrow's Date
    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    
    # Format for API comparison (API uses ISO-like "2026-01-15T00:00:00")
    # We will match by YYYY-MM-DD
    target_date_iso_prefix = tomorrow.strftime("%Y-%m-%d")
    
    # Display format for Image
    display_date = tomorrow.strftime("%d %b %Y")  # 15 Jan 2026
    
    logger.info(f"🚀 Starting Upcoming Results Job for Target Date: {target_date_iso_prefix}")

    # 2. Fetch API Data
    url = config.UPCOMING_RESULTS_API_URL
    
    # We might need to fetch more pages if there are many, but 50-100 is usually enough for one day.
    params = {
        "page": 0,
        "size": 100, # Increased size to catch more
        "sector": "All",
        "marketCap": "All"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            
    except Exception as e:
        logger.error(f"❌ Failed to fetch API data: {e}")
        return

    # 3. Filter for Tomorrow
    filtered_companies = []
    
    content = data.get('content', [])
    for content_item in content:
        events_with_date = content_item.get('eventsWithDate', [])
        for group in events_with_date:
            for event in group.get('eventList', []):
                
                result_date_str = event.get('resultDate') # e.g. "2026-01-15T00:00:00"
                
                if result_date_str and result_date_str.startswith(target_date_iso_prefix):
                    company_name = event.get('companyName', 'Unknown')
                    
                    fin_code = str(event.get('finCode', ''))
                    # Fallback if finCode missing
                    if not fin_code or fin_code == 'None':
                         fin_code = event.get('scripId', 'N/A')

                    filtered_companies.append({
                        "fin_code": fin_code,
                        "company": company_name
                    })

    # Deduplicate by fin_code
    seen_codes = set()
    unique_companies = []
    for comp in filtered_companies:
        code = comp['fin_code']
        # If code is N/A, try dedup by company name
        if code == 'N/A':
             key = comp['company']
        else:
             key = code
             
        if key not in seen_codes:
            seen_codes.add(key)
            unique_companies.append(comp)
    
    filtered_companies = unique_companies

    logger.info(f"✅ Found {len(filtered_companies)} companies for {display_date}")

    if not filtered_companies:
        logger.info("ℹ️ No upcoming results found for tomorrow. Skipping image generation.")
        return

    # 4. Generate & Send Images (Pagination Logic)
    logger.info("🎨 Generating Minimalist Images with Pagination...")
    
    # Sort alphabetical
    filtered_companies.sort(key=lambda x: x['company'])

    CHUNK_SIZE = 6
    total_items = len(filtered_companies)
    total_pages = (total_items + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    # Run generator init in thread because it downloads fonts (blocking)
    loop = asyncio.get_running_loop()
    generator = await loop.run_in_executor(None, UpcomingImpactGenerator)
    
    # Process chunks
    generated_images = []
    saved_files = [] # Track local files for cleanup
    
    try:
        for i in range(total_pages):
            chunk = filtered_companies[i*CHUNK_SIZE : (i+1)*CHUNK_SIZE]
            page_num = i + 1
            
            logger.info(f"Generating Page {page_num}/{total_pages} with {len(chunk)} items...")
            
            image_io = generator.generate_upcoming_image(
                display_date, 
                chunk,
                page_num=page_num,
                total_pages=total_pages
            )
            generated_images.append(image_io)
            
            # Save local copy debug
            filename = f"upcoming_{target_date_iso_prefix}_p{page_num}.png"
            with open(filename, "wb") as f:
                f.write(image_io.read())
            saved_files.append(filename)
            image_io.seek(0)

    except Exception as e:
         logger.error(f"❌ Image generation failed: {e}", exc_info=True)
         return

    # 5. Send to Telegram (Album or Individual)
    logger.info("📤 Sending to Telegram...")
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHANNEL_ID:
        try:
            bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            sent_success = False
            
            # Create Media Group (Album) if multiple pages
            if len(generated_images) > 1:
                from telegram import InputMediaPhoto
                media_group = []
                for idx, img_io in enumerate(generated_images):
                    caption = None
                    if idx == 0:
                        caption = (
                            f"<b>Q3 FY26 - Corporate Earnings for tomorrow\n"
                        )
                    media_group.append(InputMediaPhoto(media=img_io, caption=caption, parse_mode='HTML'))
                
                try:
                    # Native Album Sending (Replaced manual HTTPX implementation)
                    # Note: We need to rewind IO buffers for re-use if retries happen, but here we construct once.
                    for img_io in generated_images:
                        img_io.seek(0)
                        
                    await bot.send_media_group(
                        chat_id=config.TELEGRAM_CHANNEL_ID,
                        media=media_group,
                        read_timeout=600,
                        write_timeout=600,
                        connect_timeout=60
                    )
                    logger.info("✅ Telegram album sent successfully!")
                    sent_success = True

                except Exception as e:
                    logger.error(f"⚠️ Album send failed ({type(e).__name__}: {e}). Switching to individual send fallback...")
                    sent_success = False
                
                if not sent_success:
                    for idx, img_io in enumerate(generated_images):
                        try:
                            img_io.seek(0)
                            caption = None
                            if idx == 0:
                                caption = (
                                    f"📅 <b>Upcoming Results for {display_date}</b>\n\n"
                                    f"Companies reporting earnings tomorrow.\n"
                                    f"#Earnings #StockMarket"
                                )
                            
                            await bot.send_photo(
                                chat_id=config.TELEGRAM_CHANNEL_ID,
                                photo=img_io,
                                caption=caption,
                                parse_mode='HTML',
                                read_timeout=60
                            )
                            logger.info(f"✅ Fallback: Sent image {idx+1}/{len(generated_images)}")
                        except Exception as inner_e:
                             logger.error(f"❌ Fallback failed for image {idx+1}: {inner_e}")
                    
                    sent_success = True # Marked as success to trigger cleanup logic
                
            else:
                # Single Image
                caption = (
                    f"📅 <b>Upcoming Results for {display_date}</b>\n\n"
                    f"Companies reporting earnings tomorrow.\n"
                    f"#Earnings #StockMarket"
                )
                await bot.send_photo(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    photo=generated_images[0],
                    caption=caption,
                    parse_mode='HTML'
                )
                logger.info("✅ Telegram photo sent successfully!")
                sent_success = True

            # Cleanup local files if sent successfully
            if sent_success:
                for filename in saved_files:
                    try:
                        if os.path.exists(filename):
                            os.remove(filename)
                            logger.info(f"🗑️ Removed temp file: {filename}")
                    except Exception as e:
                        logger.error(f"⚠️ Failed to remove {filename}: {e}")

        except Exception as e:
            logger.error(f"❌ Telegram send failed: {e}")
    else:
        logger.warning("⚠️ Telegram credentials not set. Skipping send.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Configure logging for standalone run
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(fetch_and_process_upcoming())
