
import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import numpy as np

st.set_page_config(page_title="Einfaches Daytrading Tool", layout="wide")
st.title("Einfaches Daytrading Terminal – Stabil & Klar")

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

def get_last_valid(series):
    try:
        return series.dropna().iloc[-1]
    except:
        return None

def fetch_yahoo_news(symbol):
    try:
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        feed = feedparser.parse(feed_url)
        return [(entry.title, entry.link) for entry in feed.entries[:3]]
    except:
        return []

st.markdown("### Aktie eingeben")
query = st.text_input("Beispiel: boeing, deutsche, renk", "boeing")

selected_symbol = None
match_df = find_ticker_matches(query)

if match_df.empty:
    st.warning("Keine Treffer gefunden.")
elif len(match_df) == 1:
    selected_symbol = match_df.iloc[0]["YahooTicker"]
else:
    options = match_df["YahooTicker"] + " – " + match_df["Name"]
    choice = st.selectbox("Mehrere Treffer – auswählen:", options)
    selected_symbol = choice.split(" – ")[0]

if selected_symbol:
    st.markdown(f"### Analyse für `{selected_symbol}`")
    try:
        df = yf.download(selected_symbol, period="2mo", interval="1d", progress=False)
        if df.empty:
            st.error("Keine Kursdaten gefunden.")
        else:
            df['Close_EUR'] = df['Close'] * 0.92
            price = get_last_valid(df['Close_EUR'])
            trend = "unbekannt"
            rsi = None

            ema9 = df['Close_EUR'].ewm(span=9).mean()
            ema20 = df['Close_EUR'].ewm(span=20).mean()
            if get_last_valid(ema9) and get_last_valid(ema20):
                trend = "Bullish" if get_last_valid(ema9) > get_last_valid(ema20) else "Bearish"

            delta = df['Close_EUR'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = get_last_valid(rsi)
            rsi_status = "neutral"
            if rsi_val:
                if rsi_val > 70:
                    rsi_status = "überkauft"
                elif rsi_val < 30:
                    rsi_status = "überverkauft"

            st.metric("Kurs (EUR)", f"{price:.2f}" if price else "n/v")
            st.metric("Trend", trend)
            st.metric("RSI", f"{rsi_val:.0f} ({rsi_status})" if rsi_val else "n/v")

            # News
            st.markdown("### Aktuelle Yahoo-News")
            news = fetch_yahoo_news(selected_symbol)
            if news:
                for title, link in news:
                    st.markdown(f"- [{title}]({link})")
            else:
                st.info("Keine Schlagzeilen gefunden.")

    except Exception as e:
        st.error(f"Analysefehler: {e}")
