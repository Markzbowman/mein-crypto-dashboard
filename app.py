import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Dashboard", layout="wide")

SPOT_FAVS = ["BTC", "BNB", "XRP", "ETH", "ZEC"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# URLs
ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
# CryptoCompare als stabile Quelle für Spot-Daten (keine US-Blockade)
SPOT_URL = "https://cryptocompare.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def send_telegram_alarm(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://telegram.org{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except: pass

def fetch_data():
    # 1. Spot Preise (via CryptoCompare - Stabil in der Cloud)
    spot_prices = {}
    try:
        res = requests.get(SPOT_URL, timeout=10).json()
        for sym in SPOT_FAVS:
            if sym in res:
                spot_prices[f"{sym}USDT"] = float(res[sym]["USD"])
    except: pass
    
    # 2. Alpha Preise (Direkt via Binance Alpha BAPI)
    alpha_results = []
    try:
        res = requests.get(ALPHA_URL, headers=HEADERS, timeout=10).json()
        for t in res.get('data', []):
            sym = t.get('symbol', '').upper()
            if sym in ALPHA_FAVS:
                alpha_results.append({'symbol': sym, 'price': float(t.get('price') or 0)})
    except: pass
    
    return spot_prices, alpha_results

# --- UI ---
st.title("🚀 Binance Live Dashboard")
st.write(f"Letztes Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (CH)")

if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

spot_prices, alpha_favs = fetch_data()

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
    st.subheader("⭐ Spot Favoriten (Stabil)")
    for s in [f"{x}USDT" for x in SPOT_FAVS]:
        p = spot_prices.get(s, 0.0)
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.2f}" if p > 0 else "Lade...")

with col2:
    st.subheader("🧪 Alpha Favoriten")
    for t in alpha_favs:
        s = t['symbol']
        p = t['price']
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.6f}")

time.sleep(30)
st.rerun()
