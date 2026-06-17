# FIFA World Cup 2026 – Telegram Bot

Sends Telegram notifications for every World Cup 2026 match:
- 🔔 **30-minute reminder** before kick-off
- ⏸ **Half-time score** + 1st half goal scorers
- 🏁 **Full-time score** + all goal scorers (name, minute, penalty/OG)
- 📅 **Next match info** shown after every full-time result

All times are in **Bangladesh Time (BDT / Asia/Dhaka)**.

---

## Setup (Run on your PC)

### 1. Install Python 3.9+
Download from https://python.org if you don't have it.

### 2. Install dependencies
Open a terminal/command prompt **inside this folder** and run:
```
pip install -r requirements.txt
```

### 3. Configure your credentials
Edit `config.py` and fill in:
- `BOT_TOKEN` — your Telegram bot token (from @BotFather)
- `CHAT_ID`   — your Telegram chat/user ID (from @userinfobot)
- `API_KEY`   — your football-data.org API key

### 4. Run the bot
```
python bot.py
```

Keep the terminal open. Your PC must stay ON and connected to the internet.

### To stop the bot
Press `Ctrl + C`.

---

## What you'll receive

**30 min before kick-off:**
```
🔔 Match Reminder

⚽ France vs Senegal
🕒 17 Jun 2026 07:00 AM (BDT)
⏰ Kicks off in ~28 minutes!
```

**Half-time:**
```
⏸ HALF TIME

France 1 — 0 Senegal

📋 Scorers (1st Half):
🏠 France
  ⚽ Mbappé 34'
```

**Full-time:**
```
🏁 FULL TIME

France 2 — 1 Senegal

📋 Scorers:
🏠 France
  ⚽ Mbappé 34'
  ⚽ Giroud 78'

✈️ Senegal
  ⚽ Diallo 65'

─────────────────────────
📅 Next Match
Norway vs Iraq
🕒 17 Jun 2026 10:00 AM (BDT)
```

---

## Notes
- Scorer details require a football-data.org **Tier 1 (free)** API key
- The bot checks for updates every 60 seconds
- Half-time is detected when match status = `PAUSED`
- Full-time is detected when match status = `FINISHED`
