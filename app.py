import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client

# --- KONFIGURATION ---
st.set_page_config(page_title="Krypto Live Charts", layout="wide")

# Supabase Verbindung
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# --- FUNKTIONEN ---
def send_telegram_alarm(message):
    try:
        t_token = st.secrets["TELEGRAM_TOKEN"]
        t_id = st.secrets["TELEGRAM_CHAT_ID"]
        requests.post(f"https://telegram.org{t_token}/sendMessage", 
                      json={"chat_id": t_id, "text": message}, timeout=5)
    except: pass

def get_history(symbol):
    try:
        # Holt die letzten 20 Datenpunkte
        res = supabase.table("price_history").select("price, created_at").eq("symbol", symbol).order("created_at", desc=True).limit(20).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df = df.sort_values("created_at")
            return df["price"]
    except:
        return None

# --- UI DASHBOARD ---
st.title("📈 Live Charts (Home-Bridge)")
st.write(f"Zuletzt aktualisiert: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')}")

if 'price_history_alert' not in st.session_state:
    st.session_state.price_history_alert = {}

# Aktuelle Preise laden
try:
    response = supabase.table("Binance_Prices").select("*").execute()
    db_data = {item['symbol']: float(item['price']) for item in response.data}
except:
    db_data = {}

col1, col2 = st.columns(2)

# Hilfsfunktion für Metrik + Chart
def display_with_chart(symbol, price, is_alpha=False):
    if price <= 0: return
    
    # 2% Alarm-Logik
    if symbol in st.session_state.price_history_alert:
        old = st.session_state.price_history_alert[symbol]
        diff = ((price - old) / old) * 100
        if abs(diff) >= 2.0:
            send_telegram_alarm(f"🔔 {symbol}: {diff:+.2f}% ({price})")
            st.session_state.price_history_alert[symbol] = price
    else:
        st.session_state.price_history_alert[symbol] = price

    # Anzeige Metrik
    st.metric(label=symbol, value=f"{price:,.6f}" if is_alpha else f"{price:,.2f}")
    
    # Anzeige Chart
    hist = get_history(symbol)
    if hist is not None:
        st.line_chart(hist, height=120, use_container_width=True)

with col1:
    st.subheader("⭐ Spot")
    for s in SPOT_FAVS:
        display_with_chart(s, db_data.get(s, 0.0))

with col2:
    st.subheader("🧪 Alpha")
    for a in ALPHA_FAVS:
        display_with_chart(a, db_data.get(a, 0.0), is_alpha=True)

# Automatischer Refresh
time.sleep(10)
st.rerun()
