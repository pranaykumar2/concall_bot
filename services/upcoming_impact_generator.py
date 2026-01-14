
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import List, Dict, Optional
import sys
import os

# Ensure we can import config from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from image_generator import EnhancedNewsImageGenerator

logger = logging.getLogger(__name__)

class UpcomingImpactGenerator(EnhancedNewsImageGenerator):
    """
    Minimalist & Unique generator for Upcoming Results.
    Focuses on clarity, data density, and a premium editorial look.
    """

    def __init__(self):
        super().__init__()
        self.width = 1080  # Standard square/portrait friendly
        self.height = 1350 # 4:5 Aspect ratio (Instagram friendly)
        
        # Minimalist Palette
        self.c_bg_main = (255, 255, 255)       # Pure White
        self.c_text_main = (0, 0, 0)           # Black
        self.c_text_sub = (100, 100, 100)      # Grey
        self.c_accent = (0, 0, 0)              # Black Accent (Minimal)
        self.c_line = (230, 230, 230)          # Light Grey separator
        
        # Column Widths
        self.col_idx_w = 120
        self.col_fincode_w = 200
        self.col_comp_w = self.width - self.col_idx_w - self.col_fincode_w - 100 # Remaining

    def get_font(self, family, style, size):
        """Helper to safely load a specific configured font."""
        try:
            font_path = self.download_google_font(family, style)
            if font_path:
                return ImageFont.truetype(font_path, size)
        except Exception as e:
            logger.warning(f"Failed to load specific font {family} {style}: {e}")
        return self.load_system_font(size)

    def generate_upcoming_image(self, date_str: str, companies: List[Dict[str, str]], page_num: int = 1, total_pages: int = 1) -> BytesIO:
        """
        Generates the upcoming results image (1000x Editorial Edition).
        Design Philosophy: "Architectural Precision".
        """
        # Canvas Setup
        width = 1080
        height = 1350 # 4:5 optimized
        
        # Professional Palette
        c_bg = (252, 252, 252)        # Ultra-light grey, almost white
        c_text_main = (10, 10, 10)    # Soft Black
        c_text_meta = (140, 140, 140) # Silver Grey
        c_grid = (230, 230, 230)      # Very subtle grid lines
        c_accent = (0, 0, 0)          # Authority Black
        
        img = Image.new('RGB', (width, height), c_bg)
        draw = ImageDraw.Draw(img)
        
        # Grid System for Perfect Alignment
        margin_x = 80
        margin_y = 100
        
        # Column X Coordinates (Absolute precision)
        # Layout: [Index 15%] [FinCode 25%] [Company Name 60%]
        content_width = width - (margin_x * 2)
        col_1_x = margin_x
        col_2_x = margin_x + 140
        col_3_x = margin_x + 360
        
        # --- HEADER SECTION ---
        # "UPCOMING RESULTS" - Spaced out, Elegant, Centered
        header_text = "UPCOMING RESULTS"
        # header_font = self.load_system_font(48) # Medium size, high tracking if possible (simulated by font choice)
        header_font = self.get_font(config.UPCOMING_FONT_TITLE_FAMILY, config.UPCOMING_FONT_TITLE_STYLE, 48)
        
        # Center the header
        bbox = header_font.getbbox(header_text)
        header_w = bbox[2] - bbox[0]
        header_x = (width - header_w) // 2
        
        draw.text((header_x, margin_y), header_text, font=header_font, fill=c_text_main)
        
        # Underline accent
        line_y = margin_y + 80
        draw.line([(width//2 - 40, line_y), (width//2 + 40, line_y)], fill=c_accent, width=4)
        
        # --- SUB-HEADER / CONTEXT ---
        # Put date very subtle at top right or bottom? 
        # Requirement was "Remove date in image", but we need context? 
        # "we shall just Upcoming Results in the image". Okay, explicit instruction to remove date.
        # But maybe "TOMORROW" tag? Let's keep it strictly "UPCOMING RESULTS" as requested.
        
        # --- TABLE HEADER ---
        table_start_y = 300
        
        # Headers
        # meta_font = self.load_system_font(24)
        meta_font = self.get_font(config.UPCOMING_FONT_TABLE_HEADER_FAMILY, config.UPCOMING_FONT_TABLE_HEADER_STYLE, 24)
        draw.text((col_1_x, table_start_y), "NO.", font=meta_font, fill=c_text_meta)
        draw.text((col_2_x, table_start_y), "FIN CODE", font=meta_font, fill=c_text_meta)
        draw.text((col_3_x, table_start_y), "COMPANY", font=meta_font, fill=c_text_meta)
        
        # Horizontal Header Line
        draw.line([(margin_x, table_start_y + 40), (width - margin_x, table_start_y + 40)], fill=c_text_main, width=2)
        
        # --- CONTENT DATA ---
        row_start_y = table_start_y + 80
        row_height = 140 # Generous spacing
        
        # font_index = self.load_system_font(50) # Big Index
        # font_code = self.load_system_font(36)  # Monospace-ish
        # font_comp = self.load_system_font(42)  # Clean Sans
        
        # font_index = self.get_font(config.UPCOMING_FONT_TITLE_FAMILY, config.UPCOMING_FONT_TITLE_STYLE, 50)
        # font_code = self.get_font(config.UPCOMING_FONT_TAG_FAMILY, config.UPCOMING_FONT_TAG_STYLE, 36)
        # font_comp = self.get_font(config.UPCOMING_FONT_BODY_FAMILY, config.UPCOMING_FONT_BODY_STYLE, 42)

        font_index = self.get_font(config.UPCOMING_FONT_INDEX_FAMILY, config.UPCOMING_FONT_INDEX_STYLE, 50)
        font_code = self.get_font(config.UPCOMING_FONT_FINCODE_FAMILY, config.UPCOMING_FONT_FINCODE_STYLE, 36)
        font_comp = self.get_font(config.UPCOMING_FONT_COMPANY_FAMILY, config.UPCOMING_FONT_COMPANY_STYLE, 42)
        
        start_idx = (page_num - 1) * 6 + 1
        
        for i, comp in enumerate(companies):
            row_y = row_start_y + (i * row_height)
            center_y = row_y + (row_height // 2) - 20 # Optical adjustments
            
            # 1. Index (01, 02...)
            idx_str = f"{start_idx + i:02d}"
            draw.text((col_1_x, center_y), idx_str, font=font_index, fill=c_text_main)
            
            # 2. Fin Code (Subtle background pill?)
            code = str(comp.get('fin_code', '-'))
            draw.text((col_2_x, center_y + 8), code, font=font_code, fill=c_text_meta)
            
            # 3. Company Name
            comp_name = comp.get('company', '').upper()
            # Handle wrapping manually if needed, but lets assume 1-2 lines
            # For 1000x look, avoid cluttered wrapping. Truncate cleanly or 2 lines max.
            wrapped = self.wrap_text(comp_name, font_comp, width - col_3_x - margin_x)
            
            name_y = center_y
            if len(wrapped) > 1:
                name_y -= 25 # Shift up for multi-line
                
            for line in wrapped[:2]:
                draw.text((col_3_x, name_y), line, font=font_comp, fill=c_text_main)
                name_y += 50
                
            # Formatting: Vertical Divider Lines?
            # Lets add very subtle vertical lines to create "Swimlanes"
            # draw.line([(col_2_x - 40, row_y - 20), (col_2_x - 40, row_y + row_height - 20)], fill=c_grid, width=1)
            # draw.line([(col_3_x - 40, row_y - 20), (col_3_x - 40, row_y + row_height - 20)], fill=c_grid, width=1)
            
            # Horizontal Separator (Except last)
            if i < len(companies) - 1:
               draw.line([(col_2_x, row_y + row_height - 10), (width - margin_x, row_y + row_height - 10)], fill=c_grid, width=1)

        # --- FOOTER ---
        footer_y = height - 100
        
        # Branding
        draw.text((margin_x, footer_y), "", font=meta_font, fill=c_text_main)
        
        # Page Indicator (Circle or simply text)
        page_str = f"{page_num} / {total_pages}"
        draw.text((width - margin_x, footer_y), page_str, font=meta_font, fill=c_text_main, anchor="ra")
        
        # Save
        output = BytesIO()
        img.save(output, format='PNG', quality=100)
        output.seek(0)
        return output

if __name__ == "__main__":
    # Self-test
    generator = UpcomingImpactGenerator()
    test_companies = [
        {"fin_code": "234123", "company": "Reliance Industries Limited"},
        {"fin_code": "112233", "company": "HDFC Bank Limited"},
        {"fin_code": "998877", "company": "Infosys Limited"},
        {"fin_code": "554433", "company": "Tata Consultancy Services"},
        {"fin_code": "776655", "company": "Bajaj Finance"},
        {"fin_code": "123456", "company": "Avenue Supermarts (DMart)"},
    ]
    img_io = generator.generate_upcoming_image("15 Jan 2026", test_companies, 1, 3)
    with open("minimal_upcoming_sample.png", "wb") as f:
        f.write(img_io.read())
    print("Sample generated: minimal_upcoming_sample.png")

