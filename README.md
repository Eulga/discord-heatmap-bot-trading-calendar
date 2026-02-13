# Discord Bot (Python)

## 1) Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
```

Set your bot token in `.env`.
Per-server forum posting uses `/setforumchannel` (optional fallback: `DEFAULT_FORUM_CHANNEL_ID` in `.env`).

## 2) Run

```powershell
python bot/main.py
```

## 3) Architecture

- `bot/app`: app bootstrap, settings, shared types
- `bot/common`: clock/fs/errors utilities
- `bot/forum`: state repository + forum upsert service
- `bot/markets`: cache + capture orchestration + market providers
- `bot/features`: slash command feature modules (`kheatmap`, `usheatmap`)

## 4) Quick test

In your Discord server, send `!ping` and bot replies `pong`.

Also run slash commands `/kheatmap` and `/usheatmap`.
- Set each server's forum channel first with `/setforumchannel`.
- The bot stores forum channel per server and posts to that server's configured channel.
- Per command, it keeps one daily post and edits the first message on repeated runs.
- Post titles:
  - `[YYYY-MM-DD 한국장 히트맵]` for `kheatmap`
  - `[YYYY-MM-DD 미국장 히트맵]` for `usheatmap`
- Heatmap images are saved locally and reused for up to 1 hour.

## 5) Discord permissions

In the target server/channel, ensure the bot can:
- Use Application Commands
- Send Messages
- Attach Files
- Create/Send messages in forum posts
- Manage Server permission for users who run `/setforumchannel`

## 6) Tests

Default (exclude live network tests):

```powershell
pytest
```

Live capture tests only:

```powershell
pytest -m live
```

Live tests call real websites, so they can be flaky due to network/site-side protections.

## 7) Git workflow (recommended)

```powershell
git add .
git commit -m "chore: bootstrap python discord bot"
```

`git init` is already done. `.gitignore` excludes venv/cache/.env.
