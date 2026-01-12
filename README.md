# Concall Results Bot 📊

A production-ready bot that fetches quarterly results from Concall API and sends notifications via Telegram. Built with advanced engineering practices including exponential backoff, comprehensive logging, and cross-platform support.

## Features ✨

- 🔄 **Continuous Monitoring**: Checks for new results every 5 minutes (configurable)
- 🆕 **Smart Notifications**: Only sends alerts for NEW companies (tracks already sent)
- 📅 **Date Filtering**: Only fetches results announced on today's date
- 🔁 **Exponential Backoff**: Intelligent retry mechanism for API failures
- 📝 **Comprehensive Logging**: Detailed logs for debugging and monitoring
- 💾 **Data Archival**: Saves all fetched data to JSON files
- 🔒 **Secure Configuration**: Environment-based configuration management
- 🌍 **Cross-Platform**: Works on Windows, Linux, and macOS
- 📱 **Telegram Integration**: Sends formatted notifications to Telegram channels
- ⚡ **Async Operations**: Non-blocking async/await architecture

## How It Works 🔄

1. **Checks** every 5 minutes for new results from three authenticated API endpoints:
   - Large Cap companies
   - Mid Cap companies  
   - Small Cap companies
2. **Filters** results to only include companies with results announced **today**
3. **Compares** with previously sent companies (tracked in `sent_companies_today.json`)
4. **Sends** Telegram notification ONLY if new companies are found
5. **Saves** the data to a timestamped JSON file for archival
6. **Tracks** sent companies to avoid duplicate notifications

The bot automatically resets its tracking at midnight each day, so you'll get notifications for all companies with results the next day.

## Prerequisites 📋

- Python 3.8 or higher
- Telegram Bot Token ([How to create a bot](https://core.telegram.org/bots#6-botfather))
- Telegram Channel ID
- Concall API authentication cookies (from premium account)

## Installation 🚀

### 1. Clone or Download

```bash
cd /path/to/concall
```

### 2. Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_CHANNEL_ID=@your_channel_name or -100123456789

# Update your Concall cookies if needed
ACCESS_TOKEN=your_current_access_token
REFRESH_TOKEN=your_refresh_token
# ... other cookies
```

## Usage 📖

### Run Once (Test Mode)

To test the bot and run it immediately:

```bash
python concall.py --run-once
```

### Continuous Monitoring Mode (Production)

To run the bot in continuous mode (checks every 5 minutes for new results):

```bash
python concall.py
```

The bot will:
- Check for new results every 5 minutes
- Only send notifications for NEW companies not yet sent today
- Automatically reset at midnight each day

## Deployment 🌐

### 🪟 Windows (Task Scheduler - Recommended)

Running as a scheduled task ensures the bot starts automatically when you log in and runs in the background.

#### **Option A: One-Command Deployment (PowerShell)**

Run this command in PowerShell as Administrator to automatically create the task:

```powershell
$Action = New-ScheduledTaskAction -Execute "C:\path\to\venv\Scripts\python.exe" -Argument "C:\path\to\concall\concall.py" -WorkingDirectory "C:\path\to\concall"
$Trigger = New-ScheduledTaskTrigger -AtLogon
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
Register-ScheduledTask -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -TaskName "ConcallBot" -Description "Concall Results Bot"
```

*Note: Replace paths with your actual paths.*

#### **Option B: Manual Setup (GUI)**

1. Open **Task Scheduler**.
2. Click **Create Basic Task** on the right.
3. Name: `ConcallBot` -> Next.
4. Trigger: **When I log on** -> Next.
5. Action: **Start a program** -> Next.
6. Program/script: `C:\path\to\venv\Scripts\python.exe` (Use full path to your venv python).
7. Add arguments: `concall.py`.
8. Start in: `C:\path\to\concall` (Full path to project folder).
9. Finish.

#### **❌ Removal (Windows)**

To stop and remove the bot:

**Via PowerShell:**
```powershell
Unregister-ScheduledTask -TaskName "ConcallBot" -Confirm:$false
```

**Via GUI:**
1. Open Task Scheduler.
2. Click "Task Scheduler Library".
3. Right-click `ConcallBot` in the list.
4. Select **Delete**.

---

### 🐧 Linux (Systemd Service)

Best for keeping the bot running 24/7 on servers.

#### **Deployment**

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/concall-bot.service
   ```

2. Paste configuration (edit paths/user):
   ```ini
   [Unit]
   Description=Concall Results Bot
   After=network.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/concall
   ExecStart=/path/to/concall/venv/bin/python /path/to/concall/concall.py
   Restart=always
   RestartSec=60

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable concall-bot
   sudo systemctl start concall-bot
   ```

#### **❌ Removal (Linux)**

```bash
sudo systemctl stop concall-bot
sudo systemctl disable concall-bot
sudo rm /etc/systemd/system/concall-bot.service
sudo systemctl daemon-reload
```

---

### 🍎 macOS (Launchd)

#### **Deployment**

1. Create the plist file:
   ```bash
   nano ~/Library/LaunchAgents/com.concall.bot.plist
   ```

2. Paste configuration:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.concall.bot</string>
       <key>ProgramArguments</key>
       <array>
           <string>/path/to/concall/venv/bin/python</string>
           <string>/path/to/concall/concall.py</string>
       </array>
       <key>WorkingDirectory</key>
       <string>/path/to/concall</string>
       <key>RunAtLoad</key>
       <true/>
       <key>KeepAlive</key>
       <true/>
       <key>StandardOutPath</key>
       <string>/path/to/concall/logs/stdout.log</string>
       <key>StandardErrorPath</key>
       <string>/path/to/concall/logs/stderr.log</string>
   </dict>
   </plist>
   ```

3. Load the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.concall.bot.plist
   ```

#### **❌ Removal (macOS)**

```bash
launchctl unload ~/Library/LaunchAgents/com.concall.bot.plist
rm ~/Library/LaunchAgents/com.concall.bot.plist
```

---

### 🐳 Docker (Optional)

#### **Deployment**
```bash
docker build -t concall-bot .
docker run -d --name concall-bot --env-file .env --restart unless-stopped concall-bot
```

#### **❌ Removal (Docker)**
```bash
docker stop concall-bot
docker rm concall-bot
docker rmi concall-bot
```

## Configuration ⚙️

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Required |
| `TELEGRAM_CHANNEL_ID` | Telegram channel ID | Required |
| `SCHEDULE_TIME` | Daily execution time (HH:MM) - for daily mode | 07:30 |
| `TIMEZONE` | Timezone for scheduling | Asia/Kolkata |
| `CHECK_INTERVAL_MINUTES` | Minutes between checks in continuous mode | 5 |
| `MAX_RETRIES` | Maximum retry attempts | 5 |
| `INITIAL_BACKOFF` | Initial backoff delay (seconds) | 1 |
| `MAX_BACKOFF` | Maximum backoff delay (seconds) | 300 |
| `DATA_DIR` | Directory for JSON storage | data |
| `LOG_DIR` | Directory for log files | logs |

## Monitoring 📊

### View Logs

Logs are stored in the `logs/` directory with daily rotation:

```bash
# View today's log
tail -f logs/concall_20260108.log

# Search for errors
grep ERROR logs/concall_*.log
```

### Check Stored Data

JSON files are stored in `data/` directory:

```bash
# View latest data
ls -lt data/ | head
cat data/results_20260108_073000.json
```

## Troubleshooting 🔧

### Bot Not Sending Messages

1. **Check Bot Token**: Ensure `TELEGRAM_BOT_TOKEN` is correct
2. **Verify Channel ID**: Make sure bot is admin in the channel
3. **Check Logs**: Look for Telegram errors in logs

### API Authentication Errors

1. **Update Cookies**: Login to Concall and extract fresh cookies
2. **Check Token Expiry**: Access tokens may expire, update in `.env`
3. **Verify Premium Status**: Ensure your Concall account has premium access

### Schedule Not Working

1. **Check Timezone**: Verify `TIMEZONE` matches your location
2. **Verify Schedule Time**: Ensure `SCHEDULE_TIME` format is HH:MM
3. **Check Process**: Ensure bot process is running

## Security 🔒

- **Never commit `.env` file** to version control
- **Rotate API tokens regularly**
- **Use environment variables** for all sensitive data
- **Limit file permissions**: `chmod 600 .env` on Unix systems

## Architecture 🏗️

```
concall/
├── concall.py          # Main bot application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── .env.example       # Template for .env
├── .gitignore         # Git ignore rules
├── data/              # JSON data storage (created automatically)
├── logs/              # Log files (created automatically)
└── README.md          # This file
```

## Advanced Features 🚀

### Custom Message Format

Edit `config.py` to customize the message template:

```python
MESSAGE_TEMPLATE = """📊 Your Custom Header

{companies}

Custom footer
"""
```

### Multiple Schedules

Modify `concall.py` to add multiple scheduled times:

```python
# Add another job
scheduler.add_job(
    self.run_job,
    trigger=CronTrigger(hour=18, minute=0),  # 6 PM
    id='evening_fetch'
)
```

### Webhook Integration

Extend the bot to support webhooks for real-time notifications.

## Dependencies 📦

- `requests` - HTTP library
- `pandas` - Data manipulation
- `python-telegram-bot` - Telegram API wrapper
- `APScheduler` - Task scheduling
- `tenacity` - Retry logic with exponential backoff
- `python-dotenv` - Environment variable management
- `pytz` - Timezone support

## Contributing 🤝

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License 📄

This project is for educational and personal use. Ensure compliance with Concall's terms of service.

## Support 💬

For issues or questions:
- Check the logs in `logs/` directory
- Review configuration in `.env`
- Ensure all dependencies are installed
- Verify API credentials are valid

## Changelog 📝

### Version 1.0.0 (2026-01-08)
- Initial production-ready release
- Exponential backoff retry mechanism
- Comprehensive logging
- Cross-platform support
- Telegram integration
- JSON data archival
- Scheduled execution
- Environment-based configuration

---

Made with ❤️ for automated stock market tracking