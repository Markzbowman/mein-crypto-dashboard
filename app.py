import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Terminal", layout="wide")

# CSS für kompakte Darstellung
st.markdown("""
    <style>
    .small-font { font-size:12px !important; font-family: 'Courier New', Courier, monospace; }
    div[data-testid="stTable"] { font-size: 11px !important; }
    table { width: 100% !important; }
    th { background-color: #1e1e1e !important; color: white !important; font-size: 11px !important; text-align: left !important; }
    td { font-size: 11px !important; padding: 2px 5px !important; border-bottom: 1px solid #333 !important; }
    </style>
    """, unsafe_allow_html=True)

# Supabase Verbindung
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

def get_interval_price(symbol, minutes=None, midnight=False):
    try:
        if midnight:
            tz_swiss = timezone(timedelta(hours=2))
            target_ts = datetime.now(tz_swiss).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            target_ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        
        res = supabase.table("price_history").select("price").eq("symbol", symbol).gte("created_at", target_ts).order("created_at", asc=True).limit(1).execute()
        if res.data:
            return float(res.data[0]['price'])
    except: pass
    return None

def calc_change(current, old):
    if not old or old == 0: return "0.00%"
    diff = ((current - old) / old) * 100
    color = "#00ff00" if diff >= 0 else "#ff4b4b"
    return f'<span style="color:{color}">{diff:+.2f}%</span>'

# --- UI ---
tz_ch = timezone(timedelta(hours=2))
now_full = datetime.now(tz_ch)

# KORREKTUR: Zeit auf das letzte 10s-Intervall abrunden für die Anzeige
display_seconds = (now_full.second // 10) * 100 // 10 # Ergibt 0, 10, 20...
now_ch = now_full.replace(second=display_seconds, microsecond=0).strftime("%H:%M:%S")

st.markdown(f'<p class="small-font"><b>BINANCE LIVE-TICKER | UTC+2 | {now_ch}</b></p>', unsafe_allow_html=True)

# Daten laden
try:
    response = supabase.table("Binance_Prices").select("*").execute()
    current_data = {item['symbol']: float(item['price']) for item in response.data}
except:
    current_data = {}

def build_table(fav_list, is_alpha=False):
    rows = []
    for s in fav_list:
        curr = current_data.get(s, 0.0)
        p_1m = get_interval_price(s, minutes=1)
        p_5m = get_interval_price(s, minutes=5)
        p_1h = get_interval_price(s, minutes=60)
        p_day = get_interval_price(s, midnight=True)
        
        if f"last_{s}" not in st.session_state: st.session_state[f"last_{s}"] = curr
        p_10s = st.session_state[f"last_{s}"]
        st.session_state[f"last_{s}"] = curr

        price_format = f"{curr:,.6f}" if is_alpha else f"{curr:,.2f}"
        
        rows.append({
            "Symbol": s,
            "Preis": price_format,
            "10s": calc_change(curr, p_10s),
            "1m": calc_change(curr, p_1m),
            "5m": calc_change(curr, p_5m),
            "1h": calc_change(curr, p_1h),
            "00:00": calc_change(curr, p_day)
        })
    return pd.DataFrame(rows)

st.markdown('<p class="small-font">SPOT FAVORITEN</p>', unsafe_allow_html=True)
st.write(build_table(SPOT_FAVS).to_html(escape=False, index=False), unsafe_allow_html=True)

st.markdown('<p class="small-font" style="margin-top:15px;">ALPHA FAVORITEN</p>', unsafe_allow_html=True)
st.write(build_table(ALPHA_FAVS, is_alpha=True).to_html(escape=False, index=False), unsafe_allow_html=True)

# --- PRÄZISES TIMING ---
current_seconds = now_full.second
wait_time = 10 - (current_seconds % 10)
# Wir reduzieren den Puffer auf 0.2s für schnellere Reaktion
time.sleep(wait_time + 0.2)
st.rerun()
