import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import datetime

st.set_page_config(page_title="Multi-Ticker Analyse & Trefferquote", layout="wide")
st.title("Multi-Ticker Daytrading Analyse + Journal-Auswertung")

# -------------------------------------
# Fester Ticker-Mapping (erweiterbar)
# -------------------------------------
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

# -------------------------------------
# Mehrere Ticker eingeben
# -------------------------------------
st.markdown("### Tickerliste eingeben (Name, ISIN, WKN oder Symbol – zeilenweise)")
user_input = st.text_area("Ein Ticker pro Zeile", "rheinmetall, boeing, allianz")

tickers = [resolve_symbol(x) for x in user_input.strip().splitlines() if x.strip()]

# -------------------------------------
# Daten laden & analysieren
# -------------------------------------
usd_to_eur = 0.92
results = []

for symbol in tickers:
    try:
        data = yf.download(symbol, period="1mo", interval="1d", progress=False)
        if data.empty:
            results.append((symbol, None, "Keine Daten"))
            continue

        data['Close_EUR'] = data['Close'] * usd_to_eur
        ema9 = data['Close_EUR'].ewm(span=9).mean().iloc[-1]
        ema20 = data['Close_EUR'].ewm(span=20).mean().iloc[-1]
        delta = data['Close_EUR'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        trend = "Seitwärts"
        if ema9 > ema20:
            trend = "Bullish"
        elif ema9 < ema20:
            trend = "Bearish"

        rsi_state = "neutral"
        if rsi < 30:
            rsi_state = "überverkauft"
        elif rsi > 70:
            rsi_state = "überkauft"

        results.append((symbol, round(data['Close_EUR'].iloc[-1], 2), f"{trend}, RSI {int(rsi)} ({rsi_state})"))

    except Exception as e:
        results.append((symbol, None, f"Fehler: {e}"))

df_result = pd.DataFrame(results, columns=["Ticker", "Kurs (EUR)", "Analyse"])

st.markdown("### Ergebnisse")
st.dataframe(df_result)

# -------------------------------------
# Trefferquote aus Tradejournal
# -------------------------------------
st.markdown("---")
st.markdown("### Tradejournal-Auswertung")

try:
    journal = pd.read_csv("tradejournal.csv")
    pos_trades = journal[journal["Gewinn/Verlust (EUR)"] > 0]
    neg_trades = journal[journal["Gewinn/Verlust (EUR)"] < 0]
    trefferquote = round(len(pos_trades) / len(journal) * 100, 2) if len(journal) > 0 else 0
    avg_win = round(pos_trades["Gewinn/Verlust (EUR)"].mean(), 2) if not pos_trades.empty else 0
    avg_loss = round(neg_trades["Gewinn/Verlust (EUR)"].mean(), 2) if not neg_trades.empty else 0
    total_pnl = round(journal["Gewinn/Verlust (EUR)"].sum(), 2)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Trefferquote", f"{trefferquote} %")
    col2.metric("Ø Gewinn", f"{avg_win} €")
    col3.metric("Ø Verlust", f"{avg_loss} €")
    col4.metric("Gesamt-PnL", f"{total_pnl} €")

    st.markdown("#### Tradeverlauf")
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=journal["Datum"], y=journal["Gewinn/Verlust (EUR)"].cumsum(), name="Kumuliert"))
    chart.update_layout(height=300, xaxis_title="Datum", yaxis_title="Gesamtgewinn (€)")
    st.plotly_chart(chart, use_container_width=True)

except FileNotFoundError:
    st.warning("Kein Tradejournal gefunden. Bitte zuerst Trades eintragen.")
