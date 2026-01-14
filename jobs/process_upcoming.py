
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    
    generator = UpcomingImpactGenerator()
    
    # Process chunks
    generated_images = []
    
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
            with open(f"upcoming_{target_date_iso_prefix}_p{page_num}.png", "wb") as f:
                f.write(image_io.read())
            image_io.seek(0)

    except Exception as e:
         logger.error(f"❌ Image generation failed: {e}", exc_info=True)
         return

    # 5. Send to Telegram (Album or Individual)
    logger.info("📤 Sending to Telegram...")
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHANNEL_ID:
        try:
            bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            
            # Create Media Group (Album) if multiple pages
            if len(generated_images) > 1:
                from telegram import InputMediaPhoto
                media_group = []
                for idx, img_io in enumerate(generated_images):
                    caption = None
                    if idx == 0:
                        caption = (
                            f"<b>Upcoming Results for {display_date}</b>\n"
                            f"Full List of companies reporting tomorrow.\n\n"
                            f"<b>Stay Tuned, </b>Thank You!"
                        )
                    media_group.append(InputMediaPhoto(media=img_io, caption=caption, parse_mode='HTML'))
                
                await bot.send_media_group(chat_id=config.TELEGRAM_CHANNEL_ID, media=media_group)
                logger.info("✅ Telegram album sent successfully!")
                
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

        except Exception as e:
            logger.error(f"❌ Telegram send failed: {e}")
    else:
        logger.warning("⚠️ Telegram credentials not set. Skipping send.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(fetch_and_process_upcoming())
