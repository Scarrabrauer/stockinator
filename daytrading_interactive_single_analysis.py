
import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Daytrading – Interaktive Einzelanalyse", layout="wide")
st.title("Daytrading Terminal – Interaktive Analyse bei Mehrdeutigkeit")

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
        data = yf.download(selected_symbol, period="1mo", interval="1d", progress=False)
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
    except Exception as e:
        st.error(f"Fehler bei der Analyse: {e}")
