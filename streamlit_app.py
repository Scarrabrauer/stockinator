import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import numpy as np

st.set_page_config(page_title="Daytrader Pro", layout="wide")
st.title("Daytrader Pro – Technische Analyse + News")

@st.cache_data
def load_ticker_db():
    df = pd.read_csv("ticker_database.csv")
    df.dropna(subset=["YahooTicker"], inplace=True)
    return df

ticker_db = load_ticker_db()

def find_ticker_matches(q):
    q = q.strip().lower()
    return ticker_db[
        ticker_db["Name"].astype(str).str.lower().str.contains(q) |
        ticker_db["Synonyme"].astype(str).str.lower().str.contains(q) |
        ticker_db["YahooTicker"].astype(str).str.lower().str.contains(q)
    ][["Name", "YahooTicker"]]

def last_valid(series):
    try:
        return float(series.dropna().iloc[-1])
    except:
        return None

def fetch_yahoo_news(symbol):
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-EN"
        feed = feedparser.parse(url)
        return [(e.title, e.link) for e in feed.entries[:3]]
    except:
        return []

def calculate_indicators(df):
    close = df["Close"]
    indicators = {}
    close_eur = close * 0.92
    indicators["price_eur"] = last_valid(close_eur)

    delta = close_eur.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = last_valid(rsi)
    indicators["rsi"] = rsi_val
    indicators["rsi_state"] = "neutral"
    if rsi_val:
        if rsi_val > 70:
            indicators["rsi_state"] = "überkauft"
        elif rsi_val < 30:
            indicators["rsi_state"] = "überverkauft"

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    indicators["macd"] = last_valid(macd)
    indicators["macd_signal"] = last_valid(signal)
    indicators["macd_trend"] = "neutral"
    if indicators["macd"] and indicators["macd_signal"]:
        if indicators["macd"] > indicators["macd_signal"]:
            indicators["macd_trend"] = "bullish crossover"
        elif indicators["macd"] < indicators["macd_signal"]:
            indicators["macd_trend"] = "bearish crossover"

    sma20 = close.rolling(window=20).mean()
    std = close.rolling(window=20).std()
    indicators["bollinger_upper"] = last_valid(sma20 + 2 * std)
    indicators["bollinger_lower"] = last_valid(sma20 - 2 * std)

    ema9 = close_eur.ewm(span=9).mean()
    ema20 = close_eur.ewm(span=20).mean()
    if last_valid(ema9) and last_valid(ema20):
        indicators["trend"] = "Bullish" if last_valid(ema9) > last_valid(ema20) else "Bearish"
    else:
        indicators["trend"] = "n/v"

    # Neu: Performance und Volatilität
    indicators["perf_1d"] = (close_eur.pct_change(periods=1) * 100).iloc[-1]
    indicators["perf_1w"] = (close_eur.pct_change(periods=5) * 100).iloc[-1]
    indicators["perf_1m"] = (close_eur.pct_change(periods=21) * 100).iloc[-1]
    indicators["volatility"] = close_eur.pct_change().rolling(window=20).std().iloc[-1] * 100

    return indicators

st.markdown("### Aktie eingeben (Name, WKN, ISIN, Ticker oder Synonym)")
query = st.text_input("Beispiel: Rhein, Airbus, DAI", "SAP")

selected_symbol = None
match_df = find_ticker_matches(query)

if match_df.empty:
    st.warning("Keine Treffer gefunden.")
elif len(match_df) == 1:
    selected_symbol = match_df.iloc[0]["YahooTicker"]
else:
    options = match_df["YahooTicker"] + " – " + match_df["Name"]
    choice = st.selectbox("Mehrere Treffer gefunden – bitte auswählen:", options)
    selected_symbol = choice.split(" – ")[0]

if selected_symbol:
    st.markdown(f"### Analyse für: `{selected_symbol}`")
    try:
        df = yf.download(selected_symbol, period="2mo", interval="1d", progress=False)
        if df.empty:
            st.error("Keine Kursdaten gefunden.")
        else:
            ind = calculate_indicators(df)

            def fmt(val, digits=2):
                if isinstance(val, (float, int, np.floating)):
                    return f"{val:.{digits}f}"
                return "n/v"

            col1, col2, col3 = st.columns(3)
            col1.metric("Kurs (EUR)", fmt(ind.get("price_eur")))
            col2.metric("Trend", ind.get("trend", "n/v"))
            col3.metric("RSI", f"{fmt(ind.get('rsi'), 0)} ({ind.get('rsi_state', '')})" if ind.get("rsi") else "n/v")

            col4, col5, col6 = st.columns(3)
            col4.metric("MACD", fmt(ind.get("macd")))
            col5.metric("MACD-Signal", fmt(ind.get("macd_signal")))
            col6.metric("MACD-Trend", ind.get("macd_trend", "n/v"))

            col7, col8 = st.columns(2)
            col7.metric("Bollinger oben", fmt(ind.get("bollinger_upper")))
            col8.metric("Bollinger unten", fmt(ind.get("bollinger_lower")))

            st.markdown("### Aktuelle Schlagzeilen (Yahoo Finance)")
            news = fetch_yahoo_news(selected_symbol)
            if news:
                for title, link in news:
                    st.markdown(f"- [{title}]({link})")
            else:
                st.info("Keine aktuellen Schlagzeilen gefunden.")
    except Exception as e:
        st.error(f"Fehler bei der Analyse: {e}")
