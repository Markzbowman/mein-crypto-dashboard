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
    # KORREKTE URL-Zusammensetzung
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    
    # WICHTIG: Das Wort 'bot' muss direkt vor den Token
    url = f"https://telegram.org{token}/sendMessage"
    
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
        if r.status_code != 200:
            st.error(f"Telegram Fehler (Code {r.status_code}): {r.text}")
    except Exception as e:
        st.error(f"Verbindungsfehler zu Telegram: {e}")


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
            return float(res.data[0]['price']) # Korrektur: Index-Zugriff gefixt
    except: pass
    return None

def calc_change_and_alarm(symbol, current, old, threshold=0.4):
    if old is None or old == 0: return "---"
    diff = ((current - old) / old) * 100
    
    # ALARM LOGIK
    if abs(diff) >= threshold:
        # Prüfen, ob wir diesen speziellen Alarm heute schon gesendet haben (Reset alle 60 Sek)
        alert_key = f"alert_{symbol}"
        now = time.time()
        last_alert = st.session_state.get(f"{alert_key}_time", 0)
        
        if now - last_alert > 60: # Nur alle 60 Sekunden einen Alarm pro Coin
            direction = "🚀" if diff > 0 else "🩸"
            msg = f"{direction} ALARM: {symbol}\nBewegung: {diff:+.2f}% (1m)\nPreis: {current}"
            send_telegram_msg(msg)
            st.session_state[f"{alert_key}_time"] = now

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
            
            # Alarm nur für 1m Spalte prüfen
            chg_1m_html = calc_change_and_alarm(s, curr, p_1m, threshold=0.4)

            rows.append({
                "Symbol": s, "Preis": p_format,
                "10s": calc_change_and_alarm(s, curr, p_10s, threshold=99.0),
                "1m": chg_1m_html,
                "5m": calc_change_and_alarm(s, curr, p_5m, threshold=99.0),
                "1h": calc_change_and_alarm(s, curr, p_1h, threshold=99.0),
                "00:00": calc_change_and_alarm(s, curr, p_day, threshold=99.0)
            })
        return pd.DataFrame(rows)

    with main_container.container():
        st.markdown(f'<p class="small-font"><b>BINANCE LIVE-TICKER | {display_time}</b></p>', unsafe_allow_html=True)
        st.write(build_table(SPOT_FAVS).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.write(build_table(ALPHA_FAVS, is_alpha=True).to_html(escape=False, index=False), unsafe_allow_html=True)

    wait_time = 10 - (datetime.now().second % 10)
    time.sleep(wait_time + 0.2)
