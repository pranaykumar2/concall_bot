# Termux Deployment Guide

This guide explains how to deploy the Concall Bot on an Android device using Termux.

## Prerequisites
1.  **Termux App**: Installed from F-Droid (recommended) or Play Store.
2.  **Termux:Boot App**: (Optional) Required if you want the bot to start automatically when the phone turns on, without opening the app.

## Installation Steps

1.  **Transfer Files**: Copy the entire `concall` folder to your phone usage USB or a file syncing tool.
2.  **Open Termux**: Navigate to the folder.
    ```bash
    cd storage/shared/concall  # Example path
    ```
3.  **Run Setup Script**:
    ```bash
    chmod +x setup_termux.sh
    ./setup_termux.sh
    ```
    This script will:
    - Install Python and required libraries.
    - Set up the bot as a background service.
    - Schedule a daily restart at 06:30 AM.

## managing the Bot

The bot runs as a service named `concall-bot`.

| Action | Command |
|_ |---|
| **Check Status** | `sv status concall-bot` |
| **View Logs** | `tail -f bot_service.log` |
| **Restart Bot** | `sv restart concall-bot` |
| **Stop Bot** | `sv down concall-bot` |

## Auto-Start on Boot (Termux:Boot)
To make the bot start when you restart your phone:
1.  Install **Termux:Boot** app.
2.  Open it once to initialize.
3.  The `setup_termux.sh` has already configured the service, so `termux-services` should handle the startup automatically if Termux:Boot is present.
