
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import datetime

st.set_page_config(page_title="Daytrading Multi-Ticker+", layout="wide")
st.title("Daytrading Terminal – Multi-Ticker mit CSV-Tickerdatenbank")

# --------------------------
# Tickerdatenbank laden
# --------------------------
@st.cache_data
def load_ticker_db():
    return pd.read_csv("ticker_database.csv")

ticker_db = load_ticker_db()

# Tickerauflösung aus CSV-Datenbank
def resolve_symbol(input_text):
    q = input_text.strip().lower()
    match = ticker_db[
        ticker_db["Name"].str.lower().str.contains(q) |
        ticker_db["Synonyme"].str.lower().str.contains(q) |
        ticker_db["YahooTicker"].str.lower().str.contains(q)
    ]
    if not match.empty:
        return match.iloc[0]["YahooTicker"]
    return q.upper()

# --------------------------
# Multi-Ticker-Eingabe
# --------------------------
st.markdown("### Tickerliste eingeben (ein Ticker pro Zeile – Name, Synonym oder Symbol)")
user_input = st.text_area("Beispiele: Rheinmetall, Eon, Rolls Royce", "rheinmetall
eon
rolls royce
novo nordisk")

symbols = [resolve_symbol(line) for line in user_input.strip().splitlines() if line.strip()]

usd_to_eur = 0.92
results = []

for symbol in symbols:
    try:
        data = yf.download(symbol, period="1mo", interval="1d", progress=False)
        if data.empty:
            results.append((symbol, None, "Keine Kursdaten"))
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
st.markdown("### Analyse-Ergebnisse")
st.dataframe(df_result)
