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

# Supabase & Telegram Setup aus Secrets
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
T_TOKEN = st.secrets["TELEGRAM_TOKEN"]
T_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

supabase = create_client(URL, KEY)

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# --- FUNKTIONEN ---

def send_telegram_msg(text):
    url = f"https://telegram.org{T_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": T_CHAT_ID, "text": text}, timeout=5)
    except:
        pass

def get_closest_price(symbol, minutes=None, midnight=False):
    try:
        tz_swiss = timezone(timedelta(hours=2))
        if midnight:
            target = datetime.now(tz_swiss).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            target = datetime.now(tz_swiss) - timedelta(minutes=minutes)
        
        res = supabase.table("price_history") \
            .select("price") \
            .eq("symbol", symbol) \
            .lte("created_at", target.isoformat()) \
            .order("created_at", desc=True) \
            .limit(1).execute()
            
        if res.data:
            return float(res.data[0]['price']) # Korrektur: Index [0] für den Zugriff
    except: pass
    return None

def calc_change_and_alarm(symbol, current, old, threshold=0.4):
    if old is None or old == 0: return "---"
    diff = ((current - old) / old) * 100
    
    # ALARM LOGIK: Wenn Abweichung >= 0.4%
    if abs(diff) >= threshold:
        # Wir speichern in der Session, dass wir für diesen Preisstand bereits gewarnt haben
        alert_key = f"alert_{symbol}_{old}"
        if alert_key not in st.session_state:
            direction = "🚀" if diff > 0 else "🩸"
            msg = f"{direction} ALARM: {symbol}\nBewegung: {diff:+.2f}% (1m)\nPreis: {current}"
            send_telegram_msg(msg)
            st.session_state[alert_key] = True

    color = "#00ff00" if diff >= 0 else "#ff4b4b"
    return f'<span style="color:{color}">{diff:+.2f}%</span>'

# Platzhalter für die Live-Inhalte
main_container = st.empty()

while True:
    now_full = datetime.now(timezone(timedelta(hours=2)))
    display_time = now_full.replace(second=(now_full.second // 10) * 10, microsecond=0).strftime("%H:%M:%S")

    try:
        res = supabase.table("Binance_Prices").select("*").execute()
        current_data = {item['symbol']: float(item['price']) for item in res.data}
    except: current_data = {}

    def build_table(fav_list, is_alpha=False):
        rows = []
        for s in fav_list:
            curr = current_data.get(s, 0.0)
            p_1m = get_closest_price(s, minutes=1)
            p_5m = get_closest_price(s, minutes=5)
            p_1h = get_closest_price(s, minutes=60)
            p_day = get_closest_price(s, midnight=True)
            
            if f"last_{s}" not in st.session_state: st.session_state[f"last_{s}"] = curr
            p_10s = st.session_state[f"last_{s}"]
            st.session_state[f"last_{s}"] = curr

            p_format = f"{curr:,.6f}" if is_alpha else f"{curr:,.2f}"
            
            # Wir nutzen das 1m Intervall für den Alarm
            chg_1m_html = calc_change_and_alarm(s, curr, p_1m, threshold=0.4)

            rows.append({
                "Symbol": s, "Preis": p_format,
                "10s": calc_change_and_alarm(s, curr, p_10s, threshold=999), # Kein Alarm für 10s
                "1m": chg_1m_html,
                "5m": calc_change_and_alarm(s, curr, p_5m, threshold=999),
                "1h": calc_change_and_alarm(s, curr, p_1h, threshold=999),
                "00:00": calc_change_and_alarm(s, curr, p_day, threshold=999)
            })
        return pd.DataFrame(rows)

    with main_container.container():
        st.markdown(f'<p class="small-font"><b>BINANCE LIVE-TICKER | {display_time}</b></p>', unsafe_allow_html=True)
        st.write(build_table(SPOT_FAVS).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.write(build_table(ALPHA_FAVS, is_alpha=True).to_html(escape=False, index=False), unsafe_allow_html=True)

    wait_time = 10 - (datetime.now().second % 10)
    time.sleep(wait_time + 0.2)
