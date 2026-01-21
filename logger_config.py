import logging
import sys
from datetime import datetime
from pathlib import Path
import shutil
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

class ElegantFormatter(logging.Formatter):
    """
    Formatter that produces a sleek, professional look:
    14:30:01 │ INFO  │ Source: Concall Bot 2.0
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

    ICONS = {
        logging.DEBUG: "⚙️",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🚨",
        SENT_LEVEL_NUM: "🚀"
    }

    def format(self, record):
        # Format Date and Time
        dt = datetime.fromtimestamp(record.created)
        # date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%H:%M:%S')
        
        # Level Styling
        level_color = self.COLORS.get(record.levelno, Fore.WHITE)
        level_name = record.levelname
        
        # Consistent width for level (5 chars to fit SENT, INFO, WARN)
        level_text = f"{level_name:<5}"
        
        # Use a vertical bar as separator
        separator = f"{Fore.BLACK}{Style.BRIGHT}│{Style.RESET_ALL}"
        
        # Construct the prefix: Time │ LEVEL │
        # Using grey for time to make it less distracting
        prefix = (
            f"{Fore.BLACK}{Style.BRIGHT}{time_str}{Style.RESET_ALL} "
            f"{separator} "
            f"{level_color}{Style.BRIGHT}{level_text}{Style.RESET_ALL} "
            f"{separator}"
        )
        
        message = record.getMessage()
        
        # Auto-color message based on level if not manually colored
        if record.levelno >= logging.ERROR:
            message = f"{level_color}{message}{Style.RESET_ALL}"
        elif record.levelno == self.SENT_LEVEL_NUM:
            message = f"{Fore.GREEN}{message}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            message = f"{Fore.YELLOW}{message}{Style.RESET_ALL}"
            
        return f"{prefix} {message}"

def setup_logger(name: str, log_dir: Path) -> logging.Logger:
    """Sets up the logger with the elegant formatter"""
    
    # Register custom level
    logging.addLevelName(ElegantFormatter.SENT_LEVEL_NUM, "SENT")
    def sent(self, message, *args, **kws):
        if self.isEnabledFor(ElegantFormatter.SENT_LEVEL_NUM):
            self._log(ElegantFormatter.SENT_LEVEL_NUM, message, args, **kws)
    logging.Logger.sent = sent
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
def setup_logger(name: str, log_dir: Path) -> logging.Logger:
    """
    Sets up the ROOT logger with the elegant formatter so all modules (including apscheduler)
    use the same style. Returns the requested named logger.
    """
    
    # Register custom level
    logging.addLevelName(ElegantFormatter.SENT_LEVEL_NUM, "SENT")
    def sent(self, message, *args, **kws):
        if self.isEnabledFor(ElegantFormatter.SENT_LEVEL_NUM):
            self._log(ElegantFormatter.SENT_LEVEL_NUM, message, args, **kws)
    logging.Logger.sent = sent
    
    # Configure Root Logger once
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers to prevent duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ElegantFormatter())
    root_logger.addHandler(console_handler)
    
    # File Handler - Standard format for parsing
    log_dir.mkdir(exist_ok=True)
    today_str = datetime.now().strftime('%Y%m%d')
    log_file = log_dir / f'concall_{today_str}.log'
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Return the requested logger (which will propagate to root)
    return logging.getLogger(name)

def print_box(logger, title: str, content: dict, color=Fore.CYAN):
    """
    Prints a beautiful, elegant box summary
    """
    # Fixed width for consistency
    width = 55
    
    # Colors
    border_color = f"{color}{Style.BRIGHT}"
    text_color = f"{Fore.WHITE}"
    reset = Style.RESET_ALL
    
    # Top Border
    # ╭───────────────── TITLE ─────────────────╮
    title_display = f" {title} "
    dash_count = (width - 2 - len(title_display)) // 2
    left_dashes = "─" * dash_count
    right_dashes = "─" * (width - 2 - len(title_display) - dash_count)
    
    logger.info(f"{border_color}╭{left_dashes}{Style.NORMAL}{title_display}{Style.BRIGHT}{right_dashes}╮{reset}")
    
    # Content
    for key, value in content.items():
        val_str = str(value)
        # Format: │ Key          Value              │
        # Key takes up to 15 chars
        key_display = f"{key}"
        
        # Calculate padding
        content_len = len(key_display) + len(val_str) + 10 # approximate spacing
        # Just use f-string alignment
        # │ Key............... Value │
        
        # We want: │ Key:       Value       │
        line_inner = f"  {key_display:<18} {val_str}"
        padding = width - 4 - len(line_inner) # -2 for borders, -2 for margin
        if padding < 0: padding = 0
        
        logger.info(f"{border_color}│{reset}{line_inner}{' ' * padding}  {border_color}│{reset}")
        
    # Bottom Border
    logger.info(f"{border_color}╰{'─' * (width - 2)}╯{reset}")

def log_tree(logger, message, level="INFO", color=Fore.WHITE):
    """
    Logs a message with a tree branch style
       └─> Message
    """
    tree_char = "   └─>"
    msg = f"{color}{tree_char} {message}{Style.RESET_ALL}"
    if level == "SENT":
        logger.sent(msg)
    elif level == "INFO":
        logger.info(msg)
    elif level == "ERROR":
        logger.error(msg)
