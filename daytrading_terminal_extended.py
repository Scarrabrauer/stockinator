
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import datetime

st.set_page_config(page_title="Daytrading Terminal Robust+", layout="centered")
st.title("Daytrading Terminal – Erweiterter Symbol-Support")

# Manuelles Mapping für problematische Fälle
manual_map = {
    "renk group": "RENK.DE",
    "rheinmetall": "RHM.DE",
    "hims & hers": "HIMS",
    "boeing": "BA",
    "allianz": "ALV.DE",
    "münchner rück": "MUV2.DE",
    "münchener rück": "MUV2.DE",
    "thales": "HO.PA",
    "hensoldt": "HAG.DE",
    "porsche": "P911.DE",
    "mercedes": "MBG.DE",
    "hellofresh": "HFG.DE",
    "rolls royce": "RR.L",
    "heidelberg": "HDD.DE",
    "heidelberger druck": "HDD.DE",
    "byd": "1211.HK",
    "e.on": "EOAN.DE",
    "eon": "EOAN.DE",
    "deutsche bank": "DBK.DE",
    "deutsche börse": "DB1.DE",
    "novo nordisk": "NVO"
}

def resolve_symbol(query):
    q = query.strip().lower()
    if q in manual_map:
        return manual_map[q]
    try:
        info = yf.utils.get_ticker_by_name(q)
        if info:
            return info[0]["symbol"]
    except:
        pass
    return q.upper()

query = st.text_input("Aktie, ISIN, WKN oder Firmennamen eingeben", "rheinmetall")
symbol = resolve_symbol(query)
st.write(f"**Erkannter Ticker:** `{symbol}`")

@st.cache_data
def get_data(symbol):
    for interval in ["1h", "1d"]:
        try:
            hist = yf.download(symbol, period="1mo", interval=interval, progress=False)
            if not hist.empty:
                return hist, interval
        except:
            continue
    return pd.DataFrame(), None

hist, interval = get_data(symbol)

if hist.empty:
    st.error("Keine Kursdaten gefunden.")
else:
    usd_to_eur = 0.92
    hist['Close_EUR'] = hist['Close'] * usd_to_eur
    hist['EMA9'] = hist['Close_EUR'].ewm(span=9).mean()
    hist['EMA20'] = hist['Close_EUR'].ewm(span=20).mean()

    delta = hist['Close_EUR'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    hist['RSI'] = 100 - (100 / (1 + rs))

    hist['SMA20'] = hist['Close_EUR'].rolling(window=20).mean()
    hist['UpperBB'] = hist['SMA20'] + 2 * hist['Close_EUR'].rolling(window=20).std()
    hist['LowerBB'] = hist['SMA20'] - 2 * hist['Close_EUR'].rolling(window=20).std()

    latest = hist.dropna().iloc[-1]

    st.subheader(f"{symbol} – Analyse ({interval})")
    col1, col2, col3 = st.columns(3)
    col1.metric("Kurs", f"{latest['Close_EUR']:.2f}")
    col2.metric("EMA 9", f"{latest['EMA9']:.2f}")
    col3.metric("EMA 20", f"{latest['EMA20']:.2f}")

    if latest['EMA9'] > latest['EMA20']:
        st.success("Aufwärtstrend (Bullish Crossover)")
    elif latest['EMA9'] < latest['EMA20']:
        st.error("Abwärtstrend (Bearish Crossover)")
    else:
        st.info("Seitwärtstrend")

    rsi = latest['RSI']
    if rsi < 30:
        st.success(f"RSI: {rsi:.1f} (überverkauft)")
    elif rsi > 70:
        st.warning(f"RSI: {rsi:.1f} (überkauft)")
    else:
        st.info(f"RSI: {rsi:.1f} (neutral)")

    st.markdown("### Kursverlauf inkl. Bollinger Bänder")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close_EUR'], name='Kurs', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['UpperBB'], name='Upper BB', line=dict(color='lightgray')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['LowerBB'], name='Lower BB', line=dict(color='lightgray')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA9'], name='EMA 9', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA20'], name='EMA 20', line=dict(color='red', dash='dot')))
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Volumenprofil")
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volumen', marker_color='orange'))
    vol_fig.update_layout(height=200)
    st.plotly_chart(vol_fig, use_container_width=True)
