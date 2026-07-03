# Crypto top-20 trend alert bot

Watches the top 20 coins on CoinMarketCap for 1h/24h/7d percent-change threshold
crossings and pings you on Telegram. Alert-only — it never touches Bybit or any
exchange account, and never places a trade.

## 1. Get a CoinMarketCap API key

1. Sign up at https://coinmarketcap.com/api/ (free Basic tier: 15,000 calls/month,
   50 requests/minute — far more than this needs).
2. Copy your API key from the developer portal.

## 2. Create a Telegram bot

1. In Telegram, message **@BotFather**.
2. Send `/newbot` and follow the prompts. You'll get a token that looks like
   `123456789:AAExampleTokenTextGoesHere`.
3. Send any message to your new bot (search for it by the username you gave it).
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
   (with your real token in place of `<YOUR_TOKEN>`) and find `"chat":{"id":...}`
   in the response — that number is your chat ID.

## 3. Tune the thresholds (optional)

Open `crypto_alert_bot.py` and adjust `THRESHOLDS` and `COOLDOWN_HOURS` near the
top of the file if you want tighter or looser triggers than the defaults
(1h ±3%, 24h ±8%, 7d ±15%, 4-hour cooldown per coin/metric).

## 4. Deploy it — pick one

### Option A: GitHub Actions (recommended — free, no server to manage)

1. Create a new GitHub repo and push these files to it, keeping
   `.github/workflows/crypto-alerts.yml` in that exact path.
2. In the repo, go to **Settings -> Secrets and variables -> Actions** and add
   three repository secrets: `CMC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Done. It runs every 15 minutes automatically. Trigger it once by hand from
   the **Actions** tab (`Run workflow`) to confirm it works before waiting on
   the schedule.

Notes:
- Public repos get unlimited free Actions minutes. Private repos get 2,000
  free minutes/month, and a 15-minute schedule uses close to that on its own —
  if you keep the repo private, widen the schedule to every 30 minutes
  (`*/30 * * * *` in the workflow file) to stay comfortably inside the free
  tier. Nothing sensitive lives in the code either way; your keys stay in
  GitHub Secrets, never in the repo itself.
- GitHub can occasionally delay or skip a scheduled run during high load.
  If an alert seems late or missing, check the **Actions** tab for the run
  history.

### Option B: cron on a machine (or Raspberry Pi) you leave on

1. `pip install -r requirements.txt`
2. Export the three environment variables in your shell profile (or however
   you prefer to manage them).
3. Add a crontab entry:
   ```
   */15 * * * * cd /path/to/crypto_alert_bot && /usr/bin/python3 crypto_alert_bot.py >> run.log 2>&1
   ```

## How it works

Each run pulls the current top 20 by market cap and checks whether any coin's
1h/24h/7d change just crossed one of your thresholds. It remembers what already
alerted (in `state.json`) so it won't spam you every 15 minutes while a coin
sits above the line — you'll hear again only if it drops back below and
re-crosses, or after the cooldown window passes.
