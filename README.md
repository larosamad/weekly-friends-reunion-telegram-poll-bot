# 🇮🇹 Weekly Poll Bot 

A Telegram bot that automatically runs a weekly poll to decide which day the group wants to meet up. Powered by GitHub Actions — no server required.

## How it works

Every **Sunday** the bot sends a multiple-choice poll to the group:

> *"Che giorno preferite?"*
> Non posso / Lunedì sera / Martedì sera / … / Domenica sera

**Monday morning** the bot closes the poll and:
- If there is a **single winner** → sends the message *"Ciccini del X palesatevi…"*
- If there is a **tie** → sends a second single-choice poll with only the tied options

**Monday afternoon** (only if there was a tie) the bot closes the tiebreak poll and announces the winner.

```
Sunday 11:00 (IT winter) / 12:00 (IT summer)
│
└── Poll 1 opens  (multiple choice, ~22h)
        │
        ▼
Monday 09:00 (IT winter) / 10:00 (IT summer)
│
└── Poll 1 closes
        ├── single winner  →  winner message ✅
        └── tie            →  Poll 2 opens (single choice, ~8h)
                                    │
                                    ▼
                            Monday 17:00 (IT winter) / 18:00 (IT summer)
                            │
                            └── Poll 2 closes  →  winner message ✅
```

## Setup

### 1. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Copy the **bot token**

### 2. Get the chat ID

1. Add the bot to your group
2. Send a message in the group
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your browser
4. Find the `"id"` field inside `"chat"` — that is your chat ID (it will be a negative number for groups)

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Description |
|--------|-------------|
| `BOT_TOKEN` | The token you got from BotFather |
| `CHAT_ID` | The Telegram group chat ID (negative number) |

### 4. Enable write permissions for Actions

Go to **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**.

This is needed so the workflow can commit `poll_info.json` to the repo.

### 5. Deploy

Push the code to your repo. The workflow will trigger automatically every Sunday.

You can also run it manually from **Actions → Telegram weekly poll → Run workflow**.

## Manual trigger

The workflow can be triggered manually with a specific mode:

| Mode | Description |
|------|-------------|
| `start` | Opens poll 1 |
| `close_first` | Closes poll 1, announces winner or opens tiebreak |
| `close_tiebreak` | Closes poll 2 and announces winner |

## Files

| File | Description |
|------|-------------|
| `bot.py` | Main bot logic |
| `.github/workflows/poll.yml` | GitHub Actions workflow |
| `poll_info.json` | Auto-generated — stores the active poll ID between runs |
| `requirements.txt` | Python dependencies |

## Requirements

`requirements.txt`:
```
python-telegram-bot
```
