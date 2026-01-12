"""
Professional Editorial News Image Generator - Masterpiece Edition
The pinnacle of minimalist design excellence.
Where Swiss precision meets contemporary sophistication.
"""

import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Optional
import requests
from pathlib import Path
import re
import config

logger = logging.getLogger(__name__)


class EnhancedNewsImageGenerator:
    """The ultimate news image generator - a masterpiece of design."""

    def __init__(self,
                 show_brand=False,
                 show_mesh_grid_background=True,
                 brand_name="Balaji Equities"):
        """Initialize with world-class design principles."""
        self.width = 1200
        self.min_height = 675

        self.show_brand = show_brand
        self.show_mesh_grid_background = show_mesh_grid_background
        self.brand_name = brand_name

        # Masterclass Color System - Perfection
        self.surface_primary = (255, 255, 255)     # Pure white canvas
        self.surface_elevated = (249, 250, 251)    # Subtle elevation
        
        # Text System - Maximum Readability & Impact
        self.text_absolute = (0, 0, 0)             # Pure black for ultimate contrast
        self.text_hero = (15, 23, 42)              # Deep slate
        self.text_primary = (30, 41, 59)           # Rich dark
        self.text_secondary = (71, 85, 105)        # Professional grey
        self.text_tertiary = (100, 116, 139)       # Muted
        self.text_subtle = (148, 163, 184)         # Ultra-subtle
        
        # Accent System - Strategic & Powerful
        self.accent_primary = (37, 99, 235)        # Bold blue
        self.accent_vibrant = (59, 130, 246)       # Bright blue
        self.accent_success = (34, 197, 94)        # Vivid green
        self.accent_electric = (14, 165, 233)      # Electric cyan
        
        # Border System
        self.border_primary = (226, 232, 240)
        self.border_accent = (191, 219, 254)
        
        # World-Class Typography - Load from config
        self.font_title_family = config.FONT_TITLE_FAMILY.strip("'\"")  # Remove quotes if present
        self.font_body_family = config.FONT_DESCRIPTION_FAMILY.strip("'\"")
        self.font_meta_family = config.FONT_TAG_FAMILY.strip("'\"")
        self.font_brand_family = config.FONT_BRAND_FAMILY.strip("'\"")

        self.font_title_style = config.FONT_TITLE_STYLE.strip("'\"")
        self.font_body_style = config.FONT_DESCRIPTION_STYLE.strip("'\"")
        self.font_meta_style = config.FONT_TAG_STYLE.strip("'\"")
        self.font_brand_style = config.FONT_BRAND_STYLE.strip("'\"")

        # Perfect Scale - Load from config
        self.font_badge_size = config.FONT_TAG_SIZE
        self.font_title_size = config.FONT_TITLE_SIZE
        self.font_body_size = config.FONT_DESCRIPTION_SIZE
        self.font_brand_size = config.FONT_BRAND_SIZE
        self.font_meta_size = config.FONT_TAG_SIZE

        # Optical Line Heights
        self.title_line_height = 72
        self.body_line_height = 48
         
        self.try_load_fonts()

    def download_google_font(self, font_family, weight='400'):
        """Download Google Font with intelligent caching."""
        if not font_family:
            return None

        cache_dir = Path(__file__).parent / 'fonts_cache'
        cache_dir.mkdir(exist_ok=True)

        font_filename = f"{font_family.replace(' ', '')}-{weight}.ttf"
        font_path = cache_dir / font_filename

        if font_path.exists():
            return str(font_path)

        try:
            font_name_encoded = font_family.replace(' ', '+')
            api_url = f"https://fonts.googleapis.com/css2?family={font_name_encoded}:wght@{weight}&display=swap"

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()

            font_urls = re.findall(r'src:\s*url\(([^)]+)\)', response.text)

            if font_urls:
                font_url = font_urls[0].strip()
                font_response = requests.get(font_url, timeout=15)
                font_response.raise_for_status()

                with open(font_path, 'wb') as f:
                    f.write(font_response.content)

                logger.info(f"⬇️ Downloaded font: {font_family} ({weight})")
                return str(font_path)

        except Exception as e:
            logger.warning(f"Font download failed for {font_family}: {e}")

        return None

    def load_system_font(self, size):
        """Load system font with comprehensive fallback chain."""
        fonts_to_try = [
            'arial.ttf', 'Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/SFNSDisplay.ttf',
        ]

        for font_path in fonts_to_try:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

        return ImageFont.load_default()

    def try_load_fonts(self):
        """Load world-class typography system."""
        try:
            title_path = self.download_google_font(self.font_title_family, self.font_title_style)
            self.font_title = ImageFont.truetype(title_path, self.font_title_size) if title_path else self.load_system_font(self.font_title_size)

            body_path = self.download_google_font(self.font_body_family, self.font_body_style)
            self.font_body = ImageFont.truetype(body_path, self.font_body_size) if body_path else self.load_system_font(self.font_body_size)

            brand_path = self.download_google_font(self.font_brand_family, self.font_brand_style)
            self.font_brand = ImageFont.truetype(brand_path, self.font_brand_size) if brand_path else self.load_system_font(self.font_brand_size)

            meta_path = self.download_google_font(self.font_meta_family, self.font_meta_style)
            self.font_meta = ImageFont.truetype(meta_path, self.font_meta_size) if meta_path else self.load_system_font(self.font_meta_size)
            
            # Badge font - slightly smaller but bold
            badge_path = self.download_google_font(self.font_meta_family, '700')
            self.font_badge = ImageFont.truetype(badge_path, self.font_badge_size) if badge_path else self.load_system_font(self.font_badge_size)

        except Exception as e:
            logger.warning(f"Font loading error: {e}")
            self.font_title = self.load_system_font(self.font_title_size)
            self.font_body = self.load_system_font(self.font_body_size)
            self.font_meta = self.load_system_font(self.font_meta_size)
            self.font_brand = self.load_system_font(self.font_brand_size)
            self.font_badge = self.load_system_font(self.font_badge_size)

    def create_masterpiece_background(self, height: int) -> Image:
        """Create the ultimate minimalist background."""
        img = Image.new('RGB', (self.width, height), self.surface_primary)

        if self.show_mesh_grid_background:
            overlay = Image.new('RGBA', (self.width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Signature vertical accent - Bold & Refined
            accent_width = 4
            for i in range(accent_width):
                alpha = int(200 - (i * 35))
                draw.rectangle([(i, 0), (i + 1, height)], 
                             fill=self.accent_primary + (alpha,))
            
            # Subtle corner detail - top right
            corner_size = 200
            for i in range(corner_size):
                alpha = max(0, int(8 - (i * 0.04)))
                draw.arc([
                    (self.width - corner_size + i, -corner_size + i),
                    (self.width + corner_size - i, corner_size - i)
                ], start=0, end=90, fill=self.accent_primary + (alpha,), width=2)
            
            img.paste(overlay, (0, 0), overlay)

        return img

    def draw_perfect_badge(self, draw, text, x, y, font, bg_color, text_color):
        """Draw the perfect rounded badge with precise centering."""
        # Get text dimensions
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Perfect padding
        padding_h = 28
        padding_v = 12
        
        # Badge dimensions
        badge_width = text_width + (padding_h * 2)
        badge_height = 42
        corner_radius = 21
        
        # Draw perfect rounded rectangle
        draw.rounded_rectangle(
            [(x, y), (x + badge_width, y + badge_height)],
            radius=corner_radius,
            fill=bg_color
        )
        
        # Calculate perfect text centering
        text_x = x + (badge_width - text_width) // 2
        text_y = y + (badge_height - text_height) // 2 - 1
        
        # Draw perfectly centered text
        draw.text((text_x, text_y), text, fill=text_color, font=font)
        
        return badge_width, badge_height

    def draw_precision_divider(self, draw, y, margin_left, margin_right):
        """Draw ultra-precise divider line."""
        draw.rectangle([(margin_left, y), (self.width - margin_right, y + 1)],
                     fill=self.border_primary)

    def wrap_text(self, text, font, max_width):
        """Perfect text wrapping with optimal break points."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))
        return lines
    
    def parse_description_with_bold(self, description):
        """Parse description to identify bold first sentence.
        Returns: (bold_text, remaining_text)
        """
        import re
        
        # Pattern to match any sentence ending with "results" or "results:"
        # Matches patterns like:
        # - "Quarter ended [Month] [Year] consolidated/standalone results"
        # - "Half-Yearly ended [Month] [Year] standalone results"
        # - Any other format that ends with "results" or "results:"
        pattern = r'([^:]*results:?)'
        match = re.search(pattern, description, re.IGNORECASE)
        
        if match:
            bold_text = match.group(1).strip()
            # Remove trailing colon from bold text if present
            if bold_text.endswith(':'):
                bold_text = bold_text[:-1].strip()
            # Get text after the bold part
            remaining_text = description[match.end():].strip()
            # Remove leading colon or colon+space
            if remaining_text.startswith(':'):
                remaining_text = remaining_text[1:].strip()
            return bold_text, remaining_text
        
        return None, description

    def generate_news_image(self, title, description="", timestamp="", image_data: Optional[bytes] = None):
        """Generate the masterpiece - the ultimate news image."""
        # Perfect margins - Swiss precision
        margin_left = 100
        margin_right = 100
        margin_top = 85

        content_width = self.width - margin_left - margin_right

        # Calculate precise content height
        title_lines = self.wrap_text(title, self.font_title, content_width)
        title_height = len(title_lines) * self.title_line_height

        desc_height = 0
        if description:
            desc_lines = self.wrap_text(description, self.font_body, content_width)
            desc_height = len(desc_lines) * self.body_line_height + 45

        # Perfect spacing
        header_height = 90 if self.show_brand else 0
        badge_section = 80
        title_spacing = 55
        footer_height = 95

        total_content_height = (margin_top + header_height + badge_section +
                               title_height + title_spacing + desc_height + footer_height)

        actual_height = max(self.min_height, total_content_height)

        # Create masterpiece canvas
        base = self.create_masterpiece_background(actual_height)
        draw = ImageDraw.Draw(base)

        current_y = margin_top

        # ═══════════════════════════════════════════════════════════
        # HEADER SECTION - Elite Brand Presentation
        # ═══════════════════════════════════════════════════════════
        if self.show_brand:
            # Top precision line
            self.draw_precision_divider(draw, current_y, margin_left, margin_right)
            current_y += 26

            # Brand identity
            brand_text = self.brand_name.upper()
            draw.text((margin_left, current_y), brand_text, 
                     fill=self.text_primary, font=self.font_meta)

            # Refined separator
            brand_bbox = self.font_meta.getbbox(brand_text)
            brand_width = brand_bbox[2] - brand_bbox[0]
            sep_x = margin_left + brand_width + 14
            draw.text((sep_x, current_y - 2), "•", 
                     fill=self.text_subtle, font=self.font_meta)

            # Live indicator badge - Right aligned perfection
            live_badge_text = "LIVE"
            live_bbox = self.font_badge.getbbox(live_badge_text)
            live_width = live_bbox[2] - live_bbox[0]
            badge_total_width = live_width + 48
            badge_x = self.width - margin_right - badge_total_width
            
            self.draw_perfect_badge(
                draw, live_badge_text, badge_x, current_y - 3,
                self.font_badge, self.accent_success, self.surface_primary
            )

            current_y += 30
            self.draw_precision_divider(draw, current_y, margin_left, margin_right)
            current_y += 55

        # ═══════════════════════════════════════════════════════════
        # CATEGORY BADGE - The Star of the Show
        # ═══════════════════════════════════════════════════════════
        if not self.show_brand:
            current_y += 25

        badge_text = "FY26 Q3 CORPORATE EARNINGS"
        
        # Create badge on separate layer for perfect rendering
        badge_layer = Image.new('RGBA', (self.width, actual_height), (0, 0, 0, 0))
        badge_draw = ImageDraw.Draw(badge_layer)
        
        badge_width, badge_height = self.draw_perfect_badge(
            badge_draw, badge_text, margin_left, current_y,
            self.font_badge, self.accent_primary, self.surface_primary
        )
        
        base.paste(badge_layer, (0, 0), badge_layer)
        
        current_y += badge_height + 58

        # ═══════════════════════════════════════════════════════════
        # TITLE SECTION - Maximum Impact
        # ═══════════════════════════════════════════════════════════
        for i, line in enumerate(title_lines):
            # Pure black for absolute maximum contrast and readability
            draw.text((margin_left, current_y), line, 
                     fill=self.text_absolute, font=self.font_title)
            current_y += self.title_line_height

        current_y += 40

        # ═══════════════════════════════════════════════════════════
        # DESCRIPTION SECTION - Perfect Readability
        # ═══════════════════════════════════════════════════════════
        if description:
            # Parse description for bold first sentence
            bold_text, remaining_text = self.parse_description_with_bold(description)
            
            # Load bold font for first sentence
            bold_body_path = self.download_google_font(self.font_body_family, '700')
            font_body_bold = ImageFont.truetype(bold_body_path, self.font_body_size) if bold_body_path else self.load_system_font(self.font_body_size)
            
            # Draw bold first sentence if present
            if bold_text:
                bold_lines = self.wrap_text(bold_text, font_body_bold, content_width)
                for line in bold_lines:
                    draw.text((margin_left, current_y), line, 
                             fill=self.text_primary, font=font_body_bold)
                    current_y += self.body_line_height
                
                # Add small spacing after bold text
                if remaining_text:
                    current_y += 5
            
            # Draw remaining text in regular font
            text_to_render = remaining_text if bold_text else description
            if text_to_render:
                desc_lines = self.wrap_text(text_to_render, self.font_body, content_width)
                for line in desc_lines:
                    draw.text((margin_left, current_y), line, 
                             fill=self.text_secondary, font=self.font_body)
                    current_y += self.body_line_height

        # ═══════════════════════════════════════════════════════════
        # FOOTER SECTION - Refined Elegance
        # ═══════════════════════════════════════════════════════════
        footer_y = actual_height - 65

        # Precision divider
        self.draw_precision_divider(draw, footer_y, margin_left, margin_right)

        footer_y += 24

        # Copyright
        copyright_text = "© 2025 Balaji Equities Ltd."
        draw.text((margin_left, footer_y), copyright_text, 
                 fill=self.text_tertiary, font=self.font_brand)

        # Rights statement
        rights_text = "All Rights Reserved"
        rights_bbox = self.font_brand.getbbox(rights_text)
        rights_width = rights_bbox[2] - rights_bbox[0]
        rights_x = self.width - margin_right - rights_width
        draw.text((rights_x, footer_y), rights_text, 
                 fill=self.text_tertiary, font=self.font_brand)

        # Export masterpiece
        output = BytesIO()
        base.save(output, format='PNG', quality=100, optimize=True, dpi=(300, 300))
        output.seek(0)
        return output