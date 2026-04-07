import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone
from binance.spot import Spot

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Alpha Dashboard", layout="wide")

# Favoriten Definition
SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]
ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"}

# --- TELEGRAM ALARM FUNKTION ---
def send_telegram_alarm(message):
    # Wir nutzen Streamlit Secrets für die Sicherheit in der Cloud
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    url = f"https://telegram.org{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except:
        pass

# --- DATENABRUF ---
def fetch_all_data():
    client = Spot()
    # Spot Preise
    spot_raw = client.ticker_price()
    spot_prices = {item['symbol']: float(item['price']) for item in spot_raw}
    
    # Alpha Preise
    resp = requests.get(ALPHA_URL, headers=HEADERS, timeout=10)
    alpha_raw = resp.json().get('data', []) if resp.status_code == 200 else []
    
    return spot_prices, alpha_raw

# --- DASHBOARD UI ---
st.title("🚀 Binance Live Dashboard & Alarme")
st.write(f"Letztes Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (Schweiz)")

# Session State für Preisvergleich (um 2% Alarm zu berechnen)
if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

spot_prices, alpha_raw = fetch_all_data()

col1, col2 = st.columns(2)

# Hilfsfunktion für Alarmprüfung
def check_alarm(symbol, current_price):
    if symbol in st.session_state.price_history:
        old_price = st.session_state.price_history[symbol]
        diff = ((current_price - old_price) / old_price) * 100
        if abs(diff) >= 2.0:
            direction = "📈" if diff > 0 else "📉"
            msg = f"🔔 ALARM: {symbol} {direction} {diff:.2f}%!\nPreis: {current_price}"
            send_telegram_alarm(msg)
            st.session_state.price_history[symbol] = current_price # Reset nach Alarm
    else:
        st.session_state.price_history[symbol] = current_price

# Anzeige Spot
with col1:
    st.subheader("⭐ Spot Favoriten")
    for s in SPOT_FAVS:
        p = spot_prices.get(s, 0.0)
        check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.4f}")

# Anzeige Alpha
with col2:
    st.subheader("🧪 Alpha Favoriten")
    fav_alpha = [t for t in alpha_raw if t.get('symbol', '').upper() in ALPHA_FAVS]
    for t in fav_alpha:
        s = t.get('symbol')
        p = float(t.get('price') or 0)
        check_alarm(s, p)
        st.metric(label=s, value=f"{p:,.6f}")

st.info("Das Dashboard prüft alle 30s auf 2% Preisänderungen.")
time.sleep(30)
st.rerun() # Automatisch neu laden
