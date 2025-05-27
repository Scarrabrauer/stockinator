import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import numpy as np

st.set_page_config(page_title="Daytrading Terminal", layout="wide")
st.title("Daytrading Terminal – Analyse mit MACD, Bollinger & News")

@st.cache_data
def load_ticker_db():
    return pd.read_csv("ticker_database.csv")

ticker_db = load_ticker_db()

def find_ticker_matches(q):
    q = q.strip().lower()
    return ticker_db[
        ticker_db["Name"].str.lower().str.contains(q) |
        ticker_db["Synonyme"].str.lower().str.contains(q) |
        ticker_db["YahooTicker"].str.lower().str.contains(q)
    ][["Name", "Synonyme", "YahooTicker"]]

def safe_last_float(series):
    try:
        value = series.dropna().iloc[-1]
        return float(value) if np.isfinite(value) else None
    except:
        return None

def add_technical_indicators(data):
    result = {}
    try:
        close = data['Close']
        sma20 = close.rolling(window=20).mean()
        stddev = close.rolling(window=20).std()
        result['bollinger_upper'] = safe_last_float(sma20 + 2 * stddev)
        result['bollinger_lower'] = safe_last_float(sma20 - 2 * stddev)

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        result['macd'] = safe_last_float(macd)
        result['macd_signal'] = safe_last_float(signal)

        if result['macd'] is not None and result['macd_signal'] is not None:
            if result['macd'] > result['macd_signal']:
                result['macd_trend'] = 'bullish crossover'
            elif result['macd'] < result['macd_signal']:
                result['macd_trend'] = 'bearish crossover'
            else:
                result['macd_trend'] = 'neutral'
        else:
            result['macd_trend'] = 'n/v'
    except Exception as e:
        result['error'] = str(e)
    return result

def fetch_yahoo_news(symbol):
    try:
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        feed = feedparser.parse(feed_url)
        return [(entry.title, entry.link) for entry in feed.entries[:3]]
    except:
        return []

st.markdown("### Aktie eingeben (Name, WKN, Synonym oder Ticker)")
query = st.text_input("Beispiel: rhein, boeing, deutsche", "boeing")

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
    st.markdown(f"### Analyse für `{selected_symbol}`")
    try:
        data = yf.download(selected_symbol, period="2mo", interval="1d", progress=False)
        if data.empty:
            st.error("Keine Kursdaten gefunden.")
        else:
            usd_to_eur = 0.92
            data['Close_EUR'] = data['Close'] * usd_to_eur
            close_eur = data['Close_EUR']
            ema9 = close_eur.ewm(span=9).mean().iloc[-1]
            ema20 = close_eur.ewm(span=20).mean().iloc[-1]
            delta = close_eur.diff()
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

            # Basisdaten
            st.metric("Kurs (EUR)", f"{round(close_eur.iloc[-1], 2)}")
            st.metric("Trend", trend)
            st.metric("RSI", f"{int(rsi)} ({rsi_state})")

            # Erweiterte Analyse
            st.markdown("### Erweiterte technische Analyse")
            ti = add_technical_indicators(data)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Bollinger oben", f"{ti['bollinger_upper']:.2f}" if ti['bollinger_upper'] else "n/v")
                st.metric("MACD", f"{ti['macd']:.2f}" if ti['macd'] else "n/v")
            with col2:
                st.metric("Bollinger unten", f"{ti['bollinger_lower']:.2f}" if ti['bollinger_lower'] else "n/v")
                st.metric("MACD-Signal", f"{ti['macd_signal']:.2f}" if ti['macd_signal'] else "n/v")
            st.markdown(f"**MACD-Trend:** `{ti['macd_trend']}`")

            # News
            st.markdown("### Aktuelle Nachrichten (Yahoo Finance)")
            news = fetch_yahoo_news(selected_symbol)
            if news:
                for title, link in news:
                    st.markdown(f"- [{title}]({link})")
            else:
                st.info("Keine aktuellen Schlagzeilen gefunden.")

    except Exception as e:
        st.error(f"Fehler bei der Analyse: {e}")
