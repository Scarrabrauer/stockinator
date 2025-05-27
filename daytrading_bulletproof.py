
import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import numpy as np

st.set_page_config(page_title="Daytrading Terminal", layout="wide")
st.title("Daytrading Terminal – Fehlerfrei & Stabil")

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

def safe_number(value, digits=2):
    try:
        if isinstance(value, (pd.Series, pd.DataFrame)):
            return "n/v"
        val = float(value)
        return f"{val:.{digits}f}" if np.isfinite(val) else "n/v"
    except:
        return "n/v"

def add_technical_indicators(data):
    result = {}
    try:
        close = data['Close']
        sma20 = close.rolling(window=20).mean()
        stddev = close.rolling(window=20).std()
        result['bollinger_upper'] = (sma20 + 2 * stddev).iloc[-1]
        result['bollinger_lower'] = (sma20 - 2 * stddev).iloc[-1]

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        result['macd'] = macd.iloc[-1]
        result['macd_signal'] = signal.iloc[-1]

        if isinstance(result['macd'], (float, int)) and isinstance(result['macd_signal'], (float, int)):
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
query = st.text_input("Beispiel: boeing, deutsche, rhein", "boeing")

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
            last_price = safe_number(close_eur.iloc[-1])
            ema9 = close_eur.ewm(span=9).mean().iloc[-1]
            ema20 = close_eur.ewm(span=20).mean().iloc[-1]
            delta = close_eur.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi_val = rs.iloc[-1] if rs.notna().any() else None
            rsi = 100 - (100 / (1 + rsi_val)) if rsi_val else None
            rsi_str = safe_number(rsi, 0)

            trend = "Seitwärts"
            if ema9 > ema20:
                trend = "Bullish"
            elif ema9 < ema20:
                trend = "Bearish"

            rsi_state = "neutral"
            if rsi and rsi < 30:
                rsi_state = "überverkauft"
            elif rsi and rsi > 70:
                rsi_state = "überkauft"

            # Basisdaten
            st.metric("Kurs (EUR)", last_price)
            st.metric("Trend", trend)
            st.metric("RSI", f"{rsi_str} ({rsi_state})")

            # Erweiterte Analyse
            st.markdown("### Erweiterte technische Analyse")
            ti = add_technical_indicators(data)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Bollinger oben", safe_number(ti.get('bollinger_upper')))
                st.metric("MACD", safe_number(ti.get('macd')))
            with col2:
                st.metric("Bollinger unten", safe_number(ti.get('bollinger_lower')))
                st.metric("MACD-Signal", safe_number(ti.get('macd_signal')))
            st.markdown(f"**MACD-Trend:** `{ti.get('macd_trend', 'n/v')}`")

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
