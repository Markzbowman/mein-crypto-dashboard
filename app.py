import streamlit as st
import requests
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
st.set_page_config(page_title="Binance Proxy Dashboard", layout="wide")

SPOT_FAVS = ["BTCUSDT", "BNBUSDT", "XRPUSDT", "ETHUSDT", "ZECUSDT"]
ALPHA_FAVS = ["ARIA", "RIVER", "SIREN"]

# URLs
ALPHA_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
SPOT_URL = "https://binance.com/api/v3/ticker/price"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_via_proxy(target_url):
    # Nutzt einen Proxy-Dienst, um die US-Blockade zu umgehen
    try:
        proxy_api_key = st.secrets["PROXY_API_KEY"]
        # Wir senden die Binance-URL als Parameter an den Proxy-Dienst
        proxy_url = f"https://webscraping.ai{proxy_api_key}&url={target_url}"
        resp = requests.get(proxy_url, timeout=15)
        return resp.json()
    except Exception as e:
        return None

def fetch_data():
    # 1. Spot Preise via Proxy (umgeht Blockade)
    spot_prices = {}
    raw_spot = fetch_via_proxy(SPOT_URL)
    if raw_spot:
        spot_prices = {item['symbol']: float(item['price']) for item in raw_spot if item['symbol'] in SPOT_FAVS}
    
    # 2. Alpha Preise (Direkt, da es bei dir funktioniert)
    alpha_raw = []
    try:
        resp = requests.get(ALPHA_URL, headers=HEADERS, timeout=10)
        alpha_raw = resp.json().get('data', [])
    except: pass
    
    return spot_prices, alpha_raw

# --- UI ---
st.title("🚀 Binance Dashboard (Proxy Mode)")
st.write(f"Update: {datetime.now(timezone(timedelta(hours=2))).strftime('%H:%M:%S')} (CH)")

# Secrets Check
if "PROXY_API_KEY" not in st.secrets:
    st.error("Bitte PROXY_API_KEY in den Streamlit Secrets hinterlegen!")

spot_prices, alpha_raw = fetch_data()

col1, col2 = st.columns(2)

with col1:
    st.subheader("⭐ Spot Favoriten (via Proxy)")
    if not spot_prices:
        st.warning("Proxy liefert aktuell keine Spot-Daten.")
    for s in SPOT_FAVS:
        p = spot_prices.get(s, 0.0)
        st.metric(label=s, value=f"{p:,.2f}" if p > 0 else "Lade...")

with col2:
    st.subheader("🧪 Alpha Favoriten (Direkt)")
    fav_alpha = [t for t in alpha_raw if t.get('symbol', '').upper() in ALPHA_FAVS]
    for t in fav_alpha:
        st.metric(label=t.get('symbol'), value=f"{float(t.get('price') or 0):,.6f}")

time.sleep(30)
st.rerun()
