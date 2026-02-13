# Discord Bot (Python)

## 1) Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set your bot token in `.env`.

## 2) Run

```powershell
python bot/main.py
```

## 3) Quick test

In your Discord server, send `!ping` and bot replies `pong`.

## 4) Git workflow (recommended)

```powershell
git add .
git commit -m "chore: bootstrap python discord bot"
```

`git init` is already done. `.gitignore` excludes venv/cache/.env.
