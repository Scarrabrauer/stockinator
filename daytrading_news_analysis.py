
import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser

st.set_page_config(page_title="Daytrading – Analyse + News", layout="wide")
st.title("Daytrading Terminal – Technische Analyse + Yahoo News")

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

def add_technical_indicators(data):
    result = {}
    try:
        sma20 = data['Close'].rolling(window=20).mean()
        stddev = data['Close'].rolling(window=20).std()
        boll_upper = sma20 + (2 * stddev)
        boll_lower = sma20 - (2 * stddev)
        result['bollinger_upper'] = boll_upper.iloc[-1]
        result['bollinger_lower'] = boll_lower.iloc[-1]

        ema12 = data['Close'].ewm(span=12, adjust=False).mean()
        ema26 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        result['macd'] = macd.iloc[-1]
        result['macd_signal'] = signal.iloc[-1]
        result['macd_trend'] = (
            'bullish crossover' if macd.iloc[-1] > signal.iloc[-1]
            else 'bearish crossover' if macd.iloc[-1] < signal.iloc[-1]
            else 'neutral'
        )
    except Exception as e:
        result['error'] = str(e)
    return result

def fetch_yahoo_news(symbol):
    try:
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        feed = feedparser.parse(feed_url)
        entries = feed.entries[:3]
        return [(e.title, e.link) for e in entries]
    except:
        return []

st.markdown("### Aktie eingeben (Name, WKN, Synonym oder Ticker)")
query = st.text_input("Beispiel: deutsche, rhein, boeing", "deutsche")

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
        data = yf.download(selected_symbol, period="2mo", interval="1d", progress=False)
        if data.empty:
            st.error("Keine Kursdaten verfügbar.")
        else:
            usd_to_eur = 0.92
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

            st.metric("Kurs (EUR)", f"{round(data['Close_EUR'].iloc[-1], 2)}")
            st.metric("Trend", trend)
            st.metric("RSI", f"{int(rsi)} ({rsi_state})")

            st.markdown("### Erweiterte technische Analyse")
            ti = add_technical_indicators(data)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Bollinger oben", f"{ti['bollinger_upper']:.2f}")
                st.metric("MACD", f"{ti['macd']:.2f}")
            with col2:
                st.metric("Bollinger unten", f"{ti['bollinger_lower']:.2f}")
                st.metric("MACD-Signal", f"{ti['macd_signal']:.2f}")
            st.markdown(f"**MACD-Trend:** {ti['macd_trend'].capitalize()}")

            st.markdown("### Aktuelle News von Yahoo Finance")
            news_items = fetch_yahoo_news(selected_symbol)
            if news_items:
                for title, link in news_items:
                    st.markdown(f"- [{title}]({link})")
            else:
                st.info("Keine aktuellen Schlagzeilen gefunden.")

    except Exception as e:
        st.error(f"Fehler bei der Analyse: {e}")
