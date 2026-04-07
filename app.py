import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Alpha Dashboard", layout="wide")

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# URLs
ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
SPOT_URL = "https://binance.vision"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"}

def send_telegram_alarm(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://telegram.org{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except:
        pass

def fetch_all_data():
    # Spot Preise via einfachem Request (umgeht oft die Cloud-Blockade)
    try:
        spot_resp = requests.get(SPOT_URL, timeout=10)
        spot_raw = spot_resp.json()
        spot_prices = {item['symbol']: float(item['price']) for item in spot_raw if item['symbol'] in SPOT_FAVS}
    except:
        spot_prices = {}
    
    # Alpha Preise
    try:
        alpha_resp = requests.get(ALPHA_URL, headers=HEADERS, timeout=10)
        alpha_raw = alpha_resp.json().get('data', [])
    except:
        alpha_raw = []
    
    return spot_prices, alpha_raw

# --- DASHBOARD UI ---
st.title("🚀 Binance Live Dashboard & Alarme")
st.write(f"Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (CH)")

if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

spot_prices, alpha_raw = fetch_all_data()

# Falls Spot immer noch blockiert wird
if not spot_prices:
    st.warning("Binance blockiert aktuell den Serverstandort. Versuche es in Kürze erneut.")

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
    st.subheader("⭐ Spot Favoriten")
    for s in SPOT_FAVS:
        p = spot_prices.get(s, 0.0)
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.4f}" if p > 0 else "N/A")

with col2:
    st.subheader("🧪 Alpha Favoriten")
    fav_alpha = [t for t in alpha_raw if t.get('symbol', '').upper() in ALPHA_FAVS]
    for t in fav_alpha:
        s = t.get('symbol')
        p = float(t.get('price') or 0)
        if p > 0: check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.6f}")

time.sleep(30)
st.rerun()
