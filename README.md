# Facility Locator Discord Bot

Basic discord for the game Foxhole, built in python, that keeps track of facilities on a per guild basis. Includes basic logging and allows you to search for specific services scoped to specific regions.

# Running

1. **Install python 3.10+**

2. **Setup venv**

Run `python -m venv .venv` in the location where the bot is
Activate the venv with:
PowerShell: `.venv/Scripts/Activate.ps1`
Command Prompt: `.venv/Scripts/Activate.bat`
Bash: `source .venv/bin/activate`

3. **Install dependencies**

Run `pip install -U -r requirements.txt`

4. **Configureation**

Create a `.env` file with the following contents:
```env
OWNER_ID=Enter your ID here *Not required but recomended*
BOT_TOKEN='Token goes here'
BOT_PREFIX='.'
```

5. **Make sure all intents are enabled in the dev portal**

6. **Run `startup.py` & Sync Commands**

Majority of the commands are app commands which needs to be synced with discord running the command `{BOT_PREFIX}sync` will sync these commands