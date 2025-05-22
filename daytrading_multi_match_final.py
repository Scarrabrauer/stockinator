
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

st.set_page_config(page_title="Daytrading Multi-Ticker Ultimate", layout="wide")
st.title("Daytrading Terminal – Ultimatives Ticker-Matching")

# ---------------------------------------
# Ticker-Datenbank laden
# ---------------------------------------
@st.cache_data
def load_ticker_db():
    return pd.read_csv("ticker_database.csv")

ticker_db = load_ticker_db()

# ---------------------------------------
# Matching-Funktion (alle Treffer + Favoritenwahl)
# ---------------------------------------
def find_ticker_matches(q):
    q = q.strip().lower()
    return ticker_db[
        ticker_db["Name"].str.lower().str.contains(q) |
        ticker_db["Synonyme"].str.lower().str.contains(q) |
        ticker_db["YahooTicker"].str.lower().str.contains(q)
    ][["Name", "Synonyme", "YahooTicker"]]

# ---------------------------------------
# Eingabe & Moduswahl
# ---------------------------------------
st.markdown("### Mehrere Ticker eingeben (z. B. 'rhein', 'deutsche', 'druck')")
user_input = st.text_area("Ein Ticker pro Zeile", "rhein
deutsche
hellofresh")

show_all = st.checkbox("Alle passenden Treffer je Eingabe anzeigen (statt Auswahl)", value=False)

input_lines = [x.strip() for x in user_input.strip().splitlines() if x.strip()]
final_symbols = []

for line in input_lines:
    matches = find_ticker_matches(line)
    if matches.empty:
        st.warning(f"Kein Ticker gefunden für: {line}")
    elif len(matches) == 1 or not show_all:
        if len(matches) > 1:
            options = matches["YahooTicker"] + " – " + matches["Name"]
            choice = st.selectbox(f"Bitte wählen für '{line}'", options, key=line)
            final_symbols.append(choice.split(" – ")[0])
        else:
            final_symbols.append(matches.iloc[0]["YahooTicker"])
    elif show_all:
        st.markdown(f"**Alle Treffer für '{line}':**")
        for _, row in matches.iterrows():
            st.markdown(f"- `{row['YahooTicker']}` – {row['Name']}")
        # alle Treffer hinzufügen
        final_symbols.extend(matches["YahooTicker"].tolist())

# ---------------------------------------
# Analyse
# ---------------------------------------
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

df_result = pd.DataFrame(results, columns=["Ticker", "Kurs (EUR)", "Analyse"])
st.markdown("### Analyse-Ergebnisse")
st.dataframe(df_result)
