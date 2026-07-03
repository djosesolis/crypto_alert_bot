#!/usr/bin/env python3
"""
Crypto Top 20 Trend Alert Bot

Checks CoinMarketCap's top 20 coins by market cap for 1h/24h/7d percent-change
threshold crossings and sends a Telegram alert when a coin crosses a threshold
for the first time (edge-triggered, with a cooldown so it won't spam you while
a coin stays above the threshold).

This script only reads data and sends messages. It never touches an exchange
account and never places trades.

Setup: see README.md
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration - tune these to taste
# ---------------------------------------------------------------------------
# How many coins to watch, ranked by market cap
TOP_N = 500
# % change that triggers an alert for each timeframe (absolute value)
THRESHOLDS = {
    "percent_change_1h": 3.0,
    "percent_change_24h": 8.0,
    "percent_change_7d": 15.0,
}

# Once a coin/metric has alerted, don't alert again for this many hours
# even if it's still above threshold (unless it dropped below and re-crossed)
COOLDOWN_HOURS = 4

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
STATE_FILE = Path(__file__).parent / "state.json"

# ---------------------------------------------------------------------------
# Secrets - set these as environment variables (see README.md)
# ---------------------------------------------------------------------------

CMC_API_KEY = os.environ.get("CMC_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def fetch_top_n() -> list:
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY, "Accept": "application/json"}
    params = {"start": "1", "limit": str(TOP_N), "convert": "USD"}
    resp = requests.get(CMC_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()


def hours_between(start_iso: str, end_iso: str) -> float:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return (end - start).total_seconds() / 3600


def check_coin(coin: dict, state: dict, now_iso: str) -> list:
    """Return alert lines for this coin and update state in place."""
    symbol = coin["symbol"]
    quote = coin["quote"]["USD"]
    alerts = []

    for metric, threshold in THRESHOLDS.items():
        value = quote.get(metric)
        if value is None:
            continue

        key = f"{symbol}:{metric}"
        entry = state.get(key, {})
        was_triggered = entry.get("triggered", False)
        last_alert = entry.get("last_alert")
        is_triggered = abs(value) >= threshold

        newly_crossed = is_triggered and not was_triggered
        cooldown_expired = (
            is_triggered and was_triggered and last_alert
            and hours_between(last_alert, now_iso) >= COOLDOWN_HOURS
        )

        if newly_crossed or cooldown_expired:
            direction = "up" if value > 0 else "down"
            label = metric.replace("percent_change_", "").upper()
            alerts.append(f"<b>{symbol}</b>  {label} {direction} {value:+.2f}%")
            state[key] = {"triggered": True, "last_alert": now_iso}
        else:
            state[key] = {"triggered": is_triggered, "last_alert": last_alert}

    return alerts


def main() -> None:
    missing = [n for n, v in {
        "CMC_API_KEY": CMC_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }.items() if not v]
    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}")

    state = load_state()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        coins = fetch_top_n()
    except requests.RequestException as e:
        sys.exit(f"CoinMarketCap request failed: {e}")

    all_alerts = []
    for coin in coins:
        all_alerts.extend(check_coin(coin, state, now_iso))

    save_state(state)

    if all_alerts:
        message = "<b>Crypto alert</b>\n\n" + "\n".join(all_alerts)
        try:
            send_telegram(message)
        except requests.RequestException as e:
            sys.exit(f"Telegram send failed: {e}")
        print(f"Sent {len(all_alerts)} alert(s):\n" + "\n".join(all_alerts))
    else:
        print("No thresholds crossed this run.")


if __name__ == "__main__":
    main()
