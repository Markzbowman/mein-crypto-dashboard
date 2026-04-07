import streamlit as st
import requests
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Alpha Dashboard", layout="wide")

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# BAPI URLs (Diese funktionieren oft, wenn ://binance.com blockiert wird)
ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
MARKET_URL = "https://binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/spot/token/price/list"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"}

def send_telegram_alarm(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://telegram.org{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except: pass

def fetch_data():
    spot_results = {}
    alpha_results = []
    
    # 1. Spot-Daten via Marketing-BAPI (Web-Interface Mirror)
    try:
        res = requests.get(MARKET_URL, timeout=10).json()
        for item in res.get('data', []):
            symbol = item.get('symbol')
            if symbol in SPOT_FAVS:
                spot_results[symbol] = float(item.get('price', 0))
    except: pass
    
    # 2. Alpha-Daten (wie bisher)
    try:
        res = requests.get(ALPHA_URL, headers=HEADERS, timeout=10).json()
        for t in res.get('data', []):
            sym = t.get('symbol', '').upper()
            if sym in ALPHA_FAVS:
                alpha_results.append({'symbol': sym, 'price': float(t.get('price') or 0)})
    except: pass
    
    return spot_results, alpha_results

# --- UI ---
st.title("🚀 Binance Live Dashboard & Alarme")
st.write(f"Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (CH)")

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
    st.subheader("⭐ Spot Favoriten (Web-API)")
    for s in SPOT_FAVS:
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
