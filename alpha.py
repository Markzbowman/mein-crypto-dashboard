import time, hmac, hashlib
import requests
from urllib.parse import urlencode

API_KEY = "DEIN_API_KEY"
API_SECRET = "DEIN_API_SECRET"  # nie teile

BASE = "https://api.binance.com"
SYMBOL = "ARIAUSDT"

def sign(params: dict, secret: str) -> str:
    qs = urlencode(params, doseq=True)
    return hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()

params = {
    "symbol": SYMBOL,
    "limit": 500,
    "timestamp": int(time.time() * 1000),
    # optional:
    # "startTime": 1710000000000,
    # "endTime":   1710500000000,
}

params["signature"] = sign(params, API_SECRET)

headers = {"X-MBX-APIKEY": API_KEY}

r = requests.get(f"{BASE}/api/v3/myTrades", params=params, headers=headers, timeout=15)
r.raise_for_status()
trades = r.json()

print(f"Trades: {len(trades)}")
for t in trades[:5]:
    print(t["id"], t["time"], t["qty"], t["price"], "BUY" if t["isBuyer"] else "SELL")

    