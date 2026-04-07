import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Alpha Dashboard", layout="wide")

# Favoriten
SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# URLs
ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def send_telegram_alarm(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://telegram.org{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except: pass

def fetch_spot_fallback():
    # Quelle 1: CryptoCompare (Sehr stabil für US-Server)
    try:
        url = "https://cryptocompare.com"
        res = requests.get(url, timeout=5).json()
        return {
            "BTCUSDT": float(res["BTC"]["USD"]),
            "BNBUSDT": float(res["BNB"]["USD"]),
            "XRPUSDT": float(res["XRP"]["USD"]),
            "ETHUSDT": float(res["ETH"]["USD"]),
            "ZECUSDT": float(res["ZEC"]["USD"])
        }
    except: pass

    # Quelle 2: KuCoin API (Oft nicht blockiert)
    try:
        prices = {}
        for s in ["BTC-USDT", "BNB-USDT", "XRP-USDT", "ETH-USDT", "ZEC-USDT"]:
            url = f"https://kucoin.com{s}"
            res = requests.get(url, timeout=5).json()
            prices[s.replace("-", "")] = float(res["data"]["price"])
        return prices
    except: pass
    
    return {}

def fetch_alpha():
    try:
        resp = requests.get(ALPHA_URL, headers=HEADERS, timeout=10)
        return resp.json().get('data', [])
    except: return []

# --- UI ---
st.title("🚀 Binance Live Dashboard & Alarme")
st.write(f"Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (CH)")

if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

spot_prices = fetch_spot_fallback()
alpha_raw = fetch_alpha()

col1, col2 = st.columns(2)

def check_alarm(symbol, current_price):
    if current_price <= 0: return
    if symbol in st.session_state.price_history:
        old_price = st.session_state.price_history[symbol]
        diff = ((current_price - old_price) / old_price) * 100
        if abs(diff) >= 2.0:
            direction = "📈" if diff > 0 else "📉"
            send_telegram_alarm(f"🔔 ALARM: {symbol} {direction} {diff:.2f}%\nPreis: {current_price}")
            st.session_state.price_history[symbol] = current_price
    else:
        st.session_state.price_history[symbol] = current_price

with col1:
    st.subheader("⭐ Spot Favoriten (Multi-Quelle)")
    for s in SPOT_FAVS:
        p = spot_prices.get(s, 0.0)
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.4f}" if p > 0 else "Offline")

with col2:
    st.subheader("🧪 Alpha Favoriten (Binance)")
    fav_alpha = [t for t in alpha_raw if t.get('symbol', '').upper() in ALPHA_FAVS]
    for t in fav_alpha:
        s = t.get('symbol')
        p = float(t.get('price') or 0)
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.6f}")

time.sleep(30)
st.rerun()
