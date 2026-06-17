import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from telegram import Bot

from config import BOT_TOKEN, CHAT_ID, API_KEY

BD_TZ = ZoneInfo("Asia/Dhaka")
API_URL = "https://api.football-data.org/v4/competitions/WC/matches"

# Track what notifications have been sent per match
sent = {}


def get_matches():
    r = requests.get(API_URL, headers={"X-Auth-Token": API_KEY}, timeout=30)
    r.raise_for_status()
    return r.json().get("matches", [])


def get_match_detail(match_id):
    """Fetch a single match for goal scorers (requires match-level endpoint)."""
    url = f"https://api.football-data.org/v4/matches/{match_id}"
    r = requests.get(url, headers={"X-Auth-Token": API_KEY}, timeout=30)
    if r.status_code == 200:
        return r.json()
    return None


def format_scorers(goals, home_team, away_team):
    """
    Build a scorer board string from the goals list.
    goals = [{"minute": 45, "scorer": {"name": "Mbappe"}, "team": {"name": "France"}, "type": "NORMAL"}, ...]
    """
    if not goals:
        return ""

    home_goals = []
    away_goals = []

    for g in goals:
        scorer_name = g.get("scorer", {}).get("name", "Unknown")
        team_name = g.get("team", {}).get("name", "")
        minute = g.get("minute", "?")
        added = g.get("injuryTime")
        goal_type = g.get("type", "NORMAL")

        # Build minute string
        min_str = f"{minute}'"
        if added:
            min_str = f"{minute}+{added}'"

        # Add penalty/OG marker
        suffix = ""
        if goal_type == "PENALTY":
            suffix = " (P)"
        elif goal_type == "OWN":
            suffix = " (OG)"

        entry = f"  ⚽ {scorer_name}{suffix} {min_str}"

        if team_name == home_team:
            home_goals.append(entry)
        else:
            away_goals.append(entry)

    lines = []
    if home_goals:
        lines.append(f"🏠 {home_team}")
        lines.extend(home_goals)
    if away_goals:
        if lines:
            lines.append("")
        lines.append(f"✈️ {away_team}")
        lines.extend(away_goals)

    return "\n".join(lines)


def next_match_info(matches, current_match_id, now):
    """Find the next upcoming match after the current one."""
    upcoming = []
    for m in matches:
        if str(m["id"]) == current_match_id:
            continue
        if m["status"] in ("SCHEDULED", "TIMED"):
            kickoff = datetime.fromisoformat(
                m["utcDate"].replace("Z", "+00:00")
            ).astimezone(BD_TZ)
            if kickoff > now:
                upcoming.append((kickoff, m))

    if not upcoming:
        return None

    upcoming.sort(key=lambda x: x[0])
    kickoff, nm = upcoming[0]
    home = nm["homeTeam"]["name"]
    away = nm["awayTeam"]["name"]
    return f"📅 Next Match\n{home} vs {away}\n🕒 {kickoff:%d %b %Y %I:%M %p} (BDT)"


async def send(msg):
    bot = Bot(BOT_TOKEN)
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg)


async def monitor():
    print("✅ FIFA World Cup 2026 Bot started! Monitoring matches...")

    # ── On startup: silently mark all already-finished matches as done ──────
    # This prevents old results from being re-sent every time the bot restarts.
    try:
        boot_matches = get_matches()
        boot_now = datetime.now(BD_TZ)
        skipped = 0
        for m in boot_matches:
            mid = str(m["id"])
            kickoff = datetime.fromisoformat(
                m["utcDate"].replace("Z", "+00:00")
            ).astimezone(BD_TZ)
            # If the match kicked off before today (BDT date), mark everything sent
            if kickoff.date() < boot_now.date():
                sent[mid] = {"rem": True, "ht": True, "ft": True}
                skipped += 1
            else:
                sent[mid] = {"rem": False, "ht": False, "ft": False}
        print(f"   Skipped {skipped} past match(es). Watching from today onwards.")
    except Exception as e:
        print(f"[BOOT WARNING] Could not pre-load matches: {e}")

    while True:
        try:
            matches = get_matches()
            now = datetime.now(BD_TZ)

            for m in matches:
                match_id = str(m["id"])
                # Use existing sent state; don't reset it
                sent.setdefault(match_id, {"rem": False, "ht": False, "ft": False})

                home = m["homeTeam"]["name"]
                away = m["awayTeam"]["name"]
                status = m["status"]

                kickoff = datetime.fromisoformat(
                    m["utcDate"].replace("Z", "+00:00")
                ).astimezone(BD_TZ)

                mins_until = (kickoff - now).total_seconds() / 60

                # ── 30-Minute Reminder ──────────────────────────────────────
                if 0 <= mins_until <= 30 and not sent[match_id]["rem"]:
                    await send(
                        f"🔔 Match Reminder\n\n"
                        f"⚽ {home} vs {away}\n"
                        f"🕒 {kickoff:%d %b %Y %I:%M %p} (BDT)\n"
                        f"⏰ Kicks off in ~{int(mins_until)} minutes!"
                    )
                    sent[match_id]["rem"] = True
                    print(f"[{now:%H:%M}] Reminder sent: {home} vs {away}")

                # ── Half-Time Result ────────────────────────────────────────
                if status == "PAUSED" and not sent[match_id]["ht"]:
                    ht_score = m.get("score", {}).get("halfTime", {})
                    hs = ht_score.get("home", "?")
                    as_ = ht_score.get("away", "?")

                    # Try to get goal scorers from match detail
                    detail = get_match_detail(match_id)
                    scorer_block = ""
                    if detail:
                        goals = detail.get("goals", [])
                        # Only goals up to HT (minute <= 45+injury)
                        ht_goals = [g for g in goals if (g.get("minute") or 99) <= 45]
                        scorer_block = format_scorers(ht_goals, home, away)

                    msg = (
                        f"⏸ HALF TIME\n\n"
                        f"{home} {hs} — {as_} {away}\n"
                    )
                    if scorer_block:
                        msg += f"\n📋 Scorers (1st Half):\n{scorer_block}\n"

                    await send(msg)
                    sent[match_id]["ht"] = True
                    print(f"[{now:%H:%M}] HT sent: {home} {hs}-{as_} {away}")

                # ── Full-Time Result ────────────────────────────────────────
                if status == "FINISHED" and not sent[match_id]["ft"]:
                    ft_score = m.get("score", {}).get("fullTime", {})
                    hs = ft_score.get("home", "?")
                    as_ = ft_score.get("away", "?")

                    # Try to get all goal scorers
                    detail = get_match_detail(match_id)
                    scorer_block = ""
                    if detail:
                        goals = detail.get("goals", [])
                        scorer_block = format_scorers(goals, home, away)

                    # Get next match info
                    next_info = next_match_info(matches, match_id, now)

                    msg = (
                        f"🏁 FULL TIME\n\n"
                        f"{home} {hs} — {as_} {away}\n"
                    )
                    if scorer_block:
                        msg += f"\n📋 Scorers:\n{scorer_block}\n"
                    if next_info:
                        msg += f"\n{'─'*25}\n{next_info}"

                    await send(msg)
                    sent[match_id]["ft"] = True
                    print(f"[{now:%H:%M}] FT sent: {home} {hs}-{as_} {away}")

            await asyncio.sleep(60)

        except Exception as e:
            print(f"[ERROR] {e}")
            await asyncio.sleep(60)


asyncio.run(monitor())
