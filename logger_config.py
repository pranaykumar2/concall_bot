import logging
import sys
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

class ProfessionalFormatter(logging.Formatter):
    """
    Formatter that produces the professional look:
    Date [HH:MM:SS] ▕ LEVEL ▏ Message
    """
    
    # Custom Levels
    SENT_LEVEL_NUM = 25 
    logging.addLevelName(SENT_LEVEL_NUM, "SENT")
    
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.BLUE,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Back.WHITE,
        SENT_LEVEL_NUM: Fore.GREEN
    }

    def format(self, record):
        # Format Date and Time
        dt = datetime.fromtimestamp(record.created)
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%H:%M:%S')
        
        # Level Styling
        level_color = self.COLORS.get(record.levelno, Fore.WHITE)
        level_name = record.levelname
        # Center align level name in 6 chars
        level_text = f"{level_name:^6}"
        
        # Construct the prefix: Date [Time] ▕ LEVEL ▏
        # Using ▕ and ▏ for the box effect
        prefix = (
            f"{Fore.LIGHTBLACK_EX}{date_str} "
            f"[{time_str}]{Style.RESET_ALL} "
            f"{level_color}▕ {level_text} ▏{Style.RESET_ALL}"
        )
        
        message = record.getMessage()
        
        # Auto-color message based on level if not manually colored
        if record.levelno >= logging.ERROR:
            message = f"{level_color}{message}{Style.RESET_ALL}"
        elif record.levelno == self.SENT_LEVEL_NUM:
            # Add checkmark for SENT
            if "Sent:" in message:
                message = message.replace("Sent:", f"✅ Sent:")
            # Tree structure handling is done in the log call usually, but we can enhance it here if needed
            message = f"{Fore.GREEN}{message}{Style.RESET_ALL}"
            
        return f"{prefix} {message}"

def setup_logger(name: str, log_dir: Path) -> logging.Logger:
    """Sets up the logger with the professional formatter"""
    
    # Register custom level
    logging.addLevelName(ProfessionalFormatter.SENT_LEVEL_NUM, "SENT")
    def sent(self, message, *args, **kws):
        if self.isEnabledFor(ProfessionalFormatter.SENT_LEVEL_NUM):
            self._log(ProfessionalFormatter.SENT_LEVEL_NUM, message, args, **kws)
    logging.Logger.sent = sent
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        logger.handlers.clear()
        
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ProfessionalFormatter())
    logger.addHandler(console_handler)
    
    # File Handler - Standard format for parsing
    log_dir.mkdir(exist_ok=True)
    today_str = datetime.now().strftime('%Y%m%d')
    log_file = log_dir / f'concall_{today_str}.log'
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def print_box(logger, title: str, content: dict, color=Fore.CYAN):
    """
    Prints a beautiful box summary
    ╭─── Title ───────╮
    │  Key:    Value  │
    ╰─────────────────╯
    """
    # Calculate width based on longest line
    # Fixed minimum width 40
    import shutil
    # term_width = shutil.get_terminal_size((80, 20)).columns
    # width = min(60, term_width) 
    width = 50
    
    # Title line
    title_len = len(title)
    dash_len = width - title_len - 7 # ╭───  ───╮ (7 chars)
    left_dash = "─" * 3
    right_dash = "─" * (width - 5 - len(title) - 3) # border(1) + left_dash(3) + space(1) + title + space(1) + right_dash + border(1)
    
    top_border = f"{color}╭{left_dash} {Style.BRIGHT}{title}{Style.NORMAL}{color} {right_dash}╮{Style.RESET_ALL}"
    logger.info(top_border)
    
    for key, value in content.items():
        # Ensure value is string
        val_str = str(value)
        # Format: │  Key:    Value   │
        # Calculate padding
        key_str = f"{key}:"
        line_content = f"  {key_str:<15} {val_str}"
        padding = width - 2 - len(line_content) # Total width - borders(2) - content
        if padding < 0: padding = 0
        
        line = f"{color}│{Style.RESET_ALL}{line_content}{' ' * padding}{color}│{Style.RESET_ALL}"
        logger.info(line)
        
    bottom_border = f"{color}╰{'─' * (width - 2)}╯{Style.RESET_ALL}"
    logger.info(bottom_border)

def log_tree(logger, message, level="INFO", color=Fore.WHITE):
    """
    Logs a message with a tree branch style
       ╰──> Message
    """
    tree_char = "   ╰──>"
    msg = f"{color}{tree_char} {message}{Style.RESET_ALL}"
    if level == "SENT":
        logger.sent(msg)
    elif level == "INFO":
        logger.info(msg)
    elif level == "ERROR":
        logger.error(msg)
