
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

st.set_page_config(page_title="Daytrading – Tickerwahl bei Mehrfachtreffern", layout="wide")
st.title("Daytrading Terminal – Multi-Ticker mit Auswahl bei Mehrfachtreffern")

# Tickerdatenbank laden
@st.cache_data
def load_ticker_db():
    return pd.read_csv("ticker_database.csv")

ticker_db = load_ticker_db()

# Matching-Funktion mit Mehrfachauswahl
def find_ticker_matches(q):
    q = q.strip().lower()
    matches = ticker_db[
        ticker_db["Name"].str.lower().str.contains(q) |
        ticker_db["Synonyme"].str.lower().str.contains(q) |
        ticker_db["YahooTicker"].str.lower().str.contains(q)
    ]
    return matches[["Name", "Synonyme", "YahooTicker"]]

# Eingabe: mehrere Begriffe
st.markdown("### Eingabe von Titeln (einzeln oder mehrere, zeilenweise)")
user_input = st.text_area("Beispiel: rhein
deutsche", "rhein
deutsche")

input_lines = [x.strip() for x in user_input.strip().splitlines() if x.strip()]
final_symbols = []

for line in input_lines:
    matches = find_ticker_matches(line)
    if matches.empty:
        st.warning(f"Kein Ticker gefunden für: {line}")
    elif len(matches) == 1:
        final_symbols.append(matches.iloc[0]["YahooTicker"])
    else:
        st.markdown(f"**Mehrdeutige Eingabe:** `{line}`")
        options = matches["YahooTicker"] + " – " + matches["Name"]
        choice = st.selectbox(f"Bitte Ticker für '{line}' auswählen", options, key=line)
        selected_ticker = choice.split(" – ")[0]
        final_symbols.append(selected_ticker)

# Kursdaten abrufen & analysieren
usd_to_eur = 0.92
results = []

for symbol in final_symbols:
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

# Ergebnisse anzeigen
df_result = pd.DataFrame(results, columns=["Ticker", "Kurs (EUR)", "Analyse"])
st.markdown("### Analyse-Ergebnisse")
st.dataframe(df_result)
