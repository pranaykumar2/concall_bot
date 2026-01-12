# Concall Results Bot 📊

A production-ready bot that fetches quarterly results from Concall API and sends notifications via Telegram. Built with advanced engineering practices including exponential backoff, comprehensive logging, and cross-platform support (Windows, Linux, macOS, Android/Termux).

## Features ✨

### Core Functionality
- 🔄 **Continuous Monitoring**: Checks for new results every 5 minutes (configurable).
- 🆕 **Smart Notifications**: Sends alerts for NEW results via Telegram.
- 🖼️ **Image Generation**: Creates professional, branded summary images for each result.
- 📄 **PDF Delivery**: Automatically downloads and sends the official result PDF.

### Advanced Engineering
- 🛡️ **Network Resilience**:
    - **Session Priming**: establishing valid cookies to prevent 404 errors.
    - **Browser Mimicry**: Uses authentic Chrome headers to avoid bot detection.
    - **Strict Flow Control**: Enforces sequential processing with visual delays (3s) to ensure Telegram messages arrive in order (Image -> PDF).
    - **High Timeouts**: Uses 10-minute timeouts for uploads to handle large files on slow networks without breaking flow.
- 🧩 **Enhanced Duplicate Detection**: Tracks `Company Name` + `Result Description` (e.g., "Standalone" vs "Consolidated") to ensure you get all relevant updates, not just the first one.
+ 🎨 **Professional Logging**:
    - Visual box summaries for startup and periodic checks.
    - Color-coded logs (Blue=Info, Green=Sent, Red=Error).
    - Tree-structure output for actions (e.g., `╰──> ✅ Sent Image`).

## Platforms 🌍

- **Windows**: Full support with Task Scheduler integration.
- **Linux/VPS**: Systemd service support.
- **macOS**: Launchd support.
- **Android (Termux)**: Native support with background service handling.

## Installation 🚀

### 1. Clone or Download
```bash
git clone https://github.com/pranaykumar2/concall_bot.git
cd concall_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure
Copy the example environment file and fill in your details:
```bash
cp .env.example .env
```
Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHANNEL_ID=@your_channel
# Add your Concall API cookies/tokens if required by the scraper source
```

## Usage 📖

### Run Manually
```bash
python concall.py
```

### Run Once (Test Mode)
```bash
python concall.py --run-once
```

## Deployment 🌐

### 🤖 Android (Termux)
We have a dedicated setup script for Termux users that installs dependencies, sets up a background service, and schedules auto-restarts.

```bash
# Give execution permission
chmod +x setup_termux.sh

# Run the installer
./setup_termux.sh
```
*See [README_TERMUX.md](README_TERMUX.md) for full Android details.*

### 🪟 Windows (Task Scheduler)
Run this in PowerShell as Administrator to auto-start on login:
```powershell
$Action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\concall.py" -WorkingDirectory "C:\path\to\concall"
$Trigger = New-ScheduledTaskTrigger -AtLogon
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName "ConcallBot"
```

### 🐧 Linux (Systemd)
Create `/etc/systemd/system/concall.service`:
```ini
[Service]
ExecStart=/usr/bin/python3 /path/to/concall.py
WorkingDirectory=/path/to/concall
Restart=always
User=your_user

[Install]
WantedBy=multi-user.target
```

## Directory Structure 📂
```
concall/
├── concall.py          # Main Bot Logic (Async, Retry, Flow Control)
├── config.py           # Configuration & Config Validation
├── logger_config.py    # Professional Logging Formatter
├── image_generator.py  # Image Generation Logic
├── setup_termux.sh     # Android Deployment Script
├── README_TERMUX.md    # Android Specific Instructions
├── data/               # JSON Archives of fetched results
├── logs/               # Daily Application Logs
└── fonts_cache/        # Cached fonts for image generation
```

## Troubleshooting 🔧
- **Flow Issues**: The bot waits 10 minutes for PDF uploads. If messages appear stuck, checking your internet speed.
- **404 Errors**: The bot primes sessions automatically. If errors persist, check if BSE website structure has changed.
- **Duplicate Images**: The bot uses `sent_companies_today.json` to track history. Delete this file to reset daily history.

## License 📄
This project is for educational use.