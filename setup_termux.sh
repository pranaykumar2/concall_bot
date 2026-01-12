#!/data/data/com.termux/files/usr/bin/bash

# Termux Service Setup Script for Concall Bot
# Usage: ./setup_termux.sh

SERVICE_NAME="concall-bot"
BOT_DIR=$(pwd)
SERVICE_DIR="$PREFIX/var/service/$SERVICE_NAME"

echo "========================================"
echo "    Concall Bot Termux Setup"
echo "========================================"
echo "Bot Directory: $BOT_DIR"

# 1. Install Dependencies
echo "[*] Installing dependencies..."
pkg update -y
pkg install python termux-services cronie -y
pip install -r requirements.txt

# 2. Setup Service (runit)
echo "[*] Setting up service '$SERVICE_NAME'..."
mkdir -p "$SERVICE_DIR"

# Create run script
# We use exec to replace the shell process with python
cat <<EOF > "$SERVICE_DIR/run"
#!/data/data/com.termux/files/usr/bin/sh
cd "$BOT_DIR"
# Run python unbuffered (-u) and redirect logs to file
exec python -u concall.py >> bot_service.log 2>&1
EOF

chmod +x "$SERVICE_DIR/run"

# 3. Enable Service
echo "[*] Enabling service..."
# Use sv-enable from termux-services
sv-enable "$SERVICE_NAME"

# 4. Setup Cron Job (06:30 AM Restart)
echo "[*] Setting up Cron job (Restart at 06:30 AM)..."

# Ensure crond is enabled
sv-enable crond

# Add cron job safely (idempotent)
CRON_CMD="30 06 * * * sv restart $SERVICE_NAME"
# List existing cron, filter out our command to avoid dupes, append new command, install
(crontab -l 2>/dev/null | grep -v "$SERVICE_NAME"; echo "$CRON_CMD") | crontab -

echo "========================================"
echo "    Setup Complete!"
echo "========================================"
echo "Commands:"
echo "  Start:   sv up $SERVICE_NAME"
echo "  Stop:    sv down $SERVICE_NAME"
echo "  Restart: sv restart $SERVICE_NAME"
echo "  Status:  sv status $SERVICE_NAME"
echo "  Logs:    tail -f bot_service.log"
echo ""
echo "NOTE: The bot will start automatically when Termux app is opened."
echo "IMPORTANT: For auto-start on device boot independent of opening the app,"
echo "install 'Termux:Boot' app from F-Droid/Play Store."
