import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Alpha Dashboard", layout="wide")

SPOT_FAVS_MAP = {
    "bitcoin": "BTCUSDT",
    "binancecoin": "BNBUSDT",
    "ripple": "XRPUSDT",
    "ethereum": "ETHUSDT",
    "zcash": "ZECUSDT"
}
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
COINCAP_URL = "https://coincap.io"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"}

def send_telegram_alarm(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://telegram.org{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except: pass

def fetch_all_data():
    # 1. Spot Preise via CoinCap (USA-freundlich)
    spot_prices = {}
    try:
        resp = requests.get(COINCAP_URL, timeout=10)
        data = resp.json().get('data', [])
        for asset in data:
            id_name = asset['id']
            if id_name in SPOT_FAVS_MAP:
                ticker = SPOT_FAVS_MAP[id_name]
                spot_prices[ticker] = float(asset['priceUsd'])
    except: pass
    
    # 2. Alpha Preise
    alpha_raw = []
    try:
        alpha_resp = requests.get(ALPHA_URL, headers=HEADERS, timeout=10)
        alpha_raw = alpha_resp.json().get('data', [])
    except: pass
    
    return spot_prices, alpha_raw

# --- DASHBOARD UI ---
st.title("🚀 Binance Live Dashboard & Alarme")
st.write(f"Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (CH)")

if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

spot_prices, alpha_raw = fetch_all_data()

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
    st.subheader("⭐ Spot Favoriten (via CoinCap)")
    for ticker in SPOT_FAVS_MAP.values():
        p = spot_prices.get(ticker, 0.0)
        if p > 0: check_alarm(ticker, p)
        st.metric(label=ticker, value=f"{p:,.4f}" if p > 0 else "Lade...")

with col2:
    st.subheader("🧪 Alpha Favoriten (via Binance)")
    fav_alpha = [t for t in alpha_raw if t.get('symbol', '').upper() in ALPHA_FAVS]
    for t in fav_alpha:
        s = t.get('symbol')
        p = float(t.get('price') or 0)
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.6f}")

time.sleep(30)
st.rerun()
