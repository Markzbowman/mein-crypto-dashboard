import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from supabase import create_client

# --- KONFIGURATION ---
st.set_page_config(page_title="My Crypto Live", layout="wide")

# Supabase Verbindung (via Secrets)
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# Favoriten zur Anzeige
SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# --- TELEGRAM ALARM ---
def send_telegram_alarm(message):
    try:
        t_token = st.secrets["TELEGRAM_TOKEN"]
        t_id = st.secrets["TELEGRAM_CHAT_ID"]
        import requests
        requests.post(f"https://telegram.org{t_token}/sendMessage", 
                      json={"chat_id": t_id, "text": message}, timeout=5)
    except: pass

# --- UI DASHBOARD ---
st.title("🚀 Binance Live (Via Home-PC Bridge)")
st.write(f"Update (CH): {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')}")

if 'price_history' not in st.session_state:
    st.session_state.price_history = {}

# Daten aus Supabase abrufen
try:
    response = supabase.table("Binance_Prices").select("*").execute()
    db_data = {item['symbol']: float(item['price']) for item in response.data}
except Exception as e:
    st.error(f"Datenbankfehler: {e}")
    db_data = {}

col1, col2 = st.columns(2)

def process_display(symbol, price, is_alpha=False):
    if price <= 0: return
    # Alarmprüfung (2%)
    if symbol in st.session_state.price_history:
        old = st.session_state.price_history[symbol]
        diff = ((price - old) / old) * 100
        if abs(diff) >= 2.0:
            send_telegram_alarm(f"🔔 {symbol}: {diff:+.2f}% ({price})")
            st.session_state.price_history[symbol] = price
    else:
        st.session_state.price_history[symbol] = price
    
    st.metric(label=symbol, value=f"{price:,.6f}" if is_alpha else f"{price:,.2f}")

with col1:
    st.subheader("⭐ Spot Favoriten")
    for s in SPOT_FAVS:
        process_display(s, db_data.get(s, 0.0))

with col2:
    st.subheader("🧪 Alpha Favoriten")
    for a in ALPHA_FAVS:
        process_display(a, db_data.get(a, 0.0), is_alpha=True)

# Automatischer Refresh
time.sleep(10)
st.rerun()
