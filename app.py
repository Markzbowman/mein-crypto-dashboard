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

# Supabase & Telegram Setup
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
T_TOKEN = st.secrets["TELEGRAM_TOKEN"].strip()
T_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

supabase = create_client(URL, KEY)

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# --- TELEGRAM FUNKTION (Die sicherste Version) ---
def send_telegram_msg(text):
    # Bau der URL ohne Plus-Zeichen Gefahr
    url = f"https://telegram.org/bot8774900378:AAHhnUzqBDBoJD-1CtLNrk7VvyFoj4K6eNY/sendMessage"
    payload = {"chat_id": T_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code != 200:
            st.error(f"Telegram meldet Fehler: {r.text}")
        return True
    except Exception as e:
        st.error(f"Telegram Verbindungsfehler: {e}")
        return False

def get_closest_price(symbol, minutes=None, midnight=False):
    try:
        tz_swiss = timezone(timedelta(hours=2))
        target = datetime.now(tz_swiss).replace(hour=0, minute=0, second=0, microsecond=0) if midnight else datetime.now(tz_swiss) - timedelta(minutes=minutes)
        res = supabase.table("price_history").select("price").eq("symbol", symbol).lte("created_at", target.isoformat()).order("created_at", desc=True).limit(1).execute()
        return float(res.data[0]['price']) if res.data else None
    except: return None

def calc_change(current, old):
    if old is None or old == 0: return "---"
    diff = ((current - old) / old) * 100
    color = "#00ff00" if diff >= 0 else "#ff4b4b"
    return f'<span style="color:{color}">{diff:+.2f}%</span>', diff

# Platzhalter
main_container = st.empty()

while True:
    now_full = datetime.now(timezone(timedelta(hours=2)))
    display_time = now_full.replace(second=(now_full.second // 10) * 10, microsecond=0).strftime("%H:%M:%S")

    try:
        res = supabase.table("Binance_Prices").select("*").execute()
        current_data = {item['symbol']: float(item['price']) for item in res.data}
    except: current_data = {}

    # ALARME PRÜFEN (Separat von der Tabellen-Erstellung)
    for s in SPOT_FAVS + ALPHA_FAVS:
        curr = current_data.get(s, 0.0)
        p_1m = get_closest_price(s, minutes=1)
        if curr > 0 and p_1m:
            diff = ((curr - p_1m) / p_1m) * 100
            # TEST-ALARM: 0.4%
            if abs(diff) >= 0.4:
                # Spam Schutz: Nur alle 2 Minuten pro Coin
                if f"alert_{s}" not in st.session_state or time.time() - st.session_state[f"alert_{s}"] > 120:
                    icon = "🚀" if diff > 0 else "🩸"
                    if send_telegram_msg(f"{icon} ALARM: {s}\nBewegung: {diff:+.2f}% (1m)\nPreis: {curr}"):
                        st.session_state[f"alert_{s}"] = time.time()

    # TABELLE BAUEN
    def build_table(fav_list, is_alpha=False):
        rows = []
        for s in fav_list:
            curr = current_data.get(s, 0.0)
            p_1m = get_closest_price(s, minutes=1)
            p_5m = get_closest_price(s, minutes=5)
            p_1h = get_closest_price(s, minutes=60)
            p_day = get_closest_price(s, midnight=True)
            
            # 10s Logik
            last_key = f"last_val_{s}"
            p_10s = st.session_state.get(last_key, curr)
            st.session_state[last_key] = curr

            price_str = f"{curr:,.6f}" if is_alpha else f"{curr:,.2f}"
            
            rows.append({
                "Symbol": s, "Preis": price_str,
                "10s": calc_change(curr, p_10s)[0],
                "1m": calc_change(curr, p_1m)[0],
                "5m": calc_change(curr, p_5m)[0],
                "1h": calc_change(curr, p_1h)[0],
                "00:00": calc_change(curr, p_day)[0]
            })
        return pd.DataFrame(rows)

    with main_container.container():
        st.markdown(f'<p class="small-font"><b>BINANCE LIVE-TICKER | {display_time}</b></p>', unsafe_allow_html=True)
        st.write(build_table(SPOT_FAVS).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.write(build_table(ALPHA_FAVS, is_alpha=True).to_html(escape=False, index=False), unsafe_allow_html=True)

    # Präzises Warten
    wait = 10 - (datetime.now().second % 10)
    time.sleep(wait + 0.2)
