import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client

# --- CONFIG ---
st.set_page_config(page_title="Binance Terminal", layout="wide")

st.markdown("""
    <style>
    .small-font { font-size:12px !important; font-family: 'Courier New', Courier, monospace; }
    td { font-size: 11px !important; padding: 2px 5px !important; border-bottom: 1px solid #333 !important; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Daten aus Secrets
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
T_TOKEN = st.secrets["TELEGRAM_TOKEN"].strip()
T_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

supabase = create_client(URL, KEY)

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# --- TELEGRAM FUNKTION ---
def send_telegram_msg(text):
    # Bau der URL: bot + Token verschmelzen
    url = f"https://telegram.org/bot{T_TOKEN}/sendMessage"
    payload = {"chat_id": T_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code == 200:
            return True
        else:
            st.error(f"Telegram Fehler: {r.text}")
            return False
    except Exception as e:
        st.error(f"Telegram Verbindung fehlgeschlagen: {e}")
        return False

def get_closest_price(symbol, minutes=None, midnight=False):
    try:
        tz_swiss = timezone(timedelta(hours=2))
        if midnight:
            target = datetime.now(tz_swiss).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            target = datetime.now(tz_swiss) - timedelta(minutes=minutes)
        
        res = supabase.table("price_history").select("price").eq("symbol", symbol).lte("created_at", target.isoformat()).order("created_at", desc=True).limit(1).execute()
        return float(res.data[0]['price']) if res.data else None
    except: return None

# Platzhalter
main_container = st.empty()
debug_container = st.empty()

# ALARM LOGIK (Aussertahl des Loops um State zu halten)
if 'alerts_sent' not in st.session_state:
    st.session_state.alerts_sent = {}

while True:
    now_full = datetime.now(timezone(timedelta(hours=2)))
    display_time = now_full.replace(second=(now_full.second // 10) * 10, microsecond=0).strftime("%H:%M:%S")

    try:
        res = supabase.table("Binance_Prices").select("*").execute()
        current_data = {item['symbol']: float(item['price']) for item in res.data}
    except: current_data = {}

    # --- ALARM CHECK ---
    for s in SPOT_FAVS + ALPHA_FAVS:
        curr = current_data.get(s, 0.0)
        p_1m = get_closest_price(s, minutes=1)
        
        if curr > 0 and p_1m:
            diff = ((curr - p_1m) / p_1m) * 100
            
            # Wir prüfen die 0.4% Schwelle
            if abs(diff) >= 0.4:
                # Nur alle 5 Minuten einen Alarm pro Coin, um Spam zu vermeiden
                last_alert_time = st.session_state.alerts_sent.get(s)
                if last_alert_time is None or (time.time() - last_alert_time > 300):
                    direction = "🚀" if diff > 0 else "🩸"
                    msg = f"{direction} ALARM: {s}\nBewegung: {diff:+.2f}% (1m)\nPreis: {curr}"
                    if send_telegram_msg(msg):
                        st.session_state.alerts_sent[s] = time.time()
                        st.success(f"Alarm gesendet für {s}!")

    # --- TABELLE BAUEN ---
    def build_table(fav_list, is_alpha=False):
        rows = []
        for s in fav_list:
            curr = current_data.get(s, 0.0)
            p_1m = get_closest_price(s, minutes=1)
            p_5m = get_closest_price(s, minutes=5)
            p_1h = get_closest_price(s, minutes=60)
            p_day = get_closest_price(s, midnight=True)
            
            # 10s Differenz
            last_key = f"last_val_{s}"
            p_10s = st.session_state.get(last_key, curr)
            st.session_state[last_key] = curr

            def fmt_chg(c, o):
                if not o: return "---"
                d = ((c-o)/o)*100
                color = "#00ff00" if d >= 0 else "#ff4b4b"
                return f'<span style="color:{color}">{d:+.2f}%</span>'

            rows.append({
                "Symbol": s, "Preis": f"{curr:,.6f}" if is_alpha else f"{curr:,.2f}",
                "10s": fmt_chg(curr, p_10s), "1m": fmt_chg(curr, p_1m),
                "5m": fmt_chg(curr, p_5m), "1h": fmt_chg(curr, p_1h), "00:00": fmt_chg(curr, p_day)
            })
        return pd.DataFrame(rows)

    with main_container.container():
        st.markdown(f'<p class="small-font"><b>BINANCE LIVE-TICKER | {display_time}</b></p>', unsafe_allow_html=True)
        st.write(build_table(SPOT_FAVS).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.write(build_table(ALPHA_FAVS, is_alpha=True).to_html(escape=False, index=False), unsafe_allow_html=True)

    # Präzises Warten
    wait = 10 - (datetime.now().second % 10)
    time.sleep(wait + 0.2)
