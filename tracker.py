#!/usr/bin/env python3
"""
Amazon Price Tracker
Reads tracked.json, scrapes current price for each product,
sends ntfy.sh notification if price <= target.
Updates tracked.json with last_checked_price and last_checked_at.
"""

import json
import re
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent / "tracked.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

PRICE_SELECTORS = [
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "#priceblock_saleprice",
    "span.a-price span.a-offscreen",
    "#corePrice_feature_div span.a-offscreen",
    "#corePriceDisplay_desktop_feature_div span.a-offscreen",
]


def load_tracked():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_tracked(items):
    with open(DATA_FILE, "w") as f:
        json.dump(items, f, indent=2)


def extract_price(text):
    """Pull a float out of a price string like '$1,234.56'."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


SCRAPERAPI_KEY = __import__("os").environ.get("SCRAPERAPI_KEY", "")


def fetch_price(url):
    if SCRAPERAPI_KEY:
        fetch_url = "https://api.scraperapi.com/"
        params = {"api_key": SCRAPERAPI_KEY, "url": url, "render": "false"}
        resp = requests.get(fetch_url, params=params, timeout=30)
    else:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} fetching {url}")

    soup = BeautifulSoup(resp.text, "html.parser")

    for selector in PRICE_SELECTORS:
        el = soup.select_one(selector)
        if el:
            price = extract_price(el.get_text())
            if price is not None:
                return price

    title = soup.select_one("#productTitle")
    if not title:
        snippet = resp.text[:300].replace("\n", " ")
        raise RuntimeError(f"Blocked/CAPTCHA likely. Response snippet: {snippet}")

    raise RuntimeError("Product page loaded but no price element matched")


def send_ntfy(topic, title, message, url=None):
    ntfy_url = f"https://ntfy.sh/{topic}"
    headers = {"Title": title}
    if url:
        headers["Click"] = url
    resp = requests.post(ntfy_url, data=message.encode("utf-8"), headers=headers, timeout=10)
    resp.raise_for_status()


def main():
    items = load_tracked()
    if not items:
        print("No tracked items. Nothing to do.")
        return

    changed = False

    for item in items:
        url = item.get("url")
        target = item.get("target_price")
        topic = item.get("ntfy_topic")
        name = item.get("name", url)

        if not url or target is None or not topic:
            print(f"Skipping malformed entry: {item}")
            continue

        print(f"Checking: {name}")
        try:
            price = fetch_price(url)
        except Exception as e:
            print(f"  ERROR: {e}")
            item["last_error"] = str(e)
            item["last_checked_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
            time.sleep(random.uniform(2, 5))
            continue

        print(f"  Current price: {price}  Target: {target}")
        item["last_checked_price"] = price
        item["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        item.pop("last_error", None)
        changed = True

        already_notified = item.get("notified_at_price")

        if price <= float(target):
            if already_notified == price:
                print("  Already notified at this price. Skipping notification.")
            else:
                print("  Price below target! Sending ntfy notification.")
                send_ntfy(
                    topic=topic,
                    title=f"Price drop: {name}",
                    message=f"Now ${price} (target ${target})\n{url}",
                    url=url,
                )
                item["notified_at_price"] = price
        else:
            item["notified_at_price"] = None

        time.sleep(random.uniform(2, 5))

    if changed:
        save_tracked(items)
        print("tracked.json updated.")


if __name__ == "__main__":
    main()