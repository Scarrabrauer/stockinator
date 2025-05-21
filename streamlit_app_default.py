import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Daytrading Analyse Tool", layout="centered")

st.title("Daytrading Live-Analyse")

# Eingabefeld für den Ticker
ticker = st.text_input("Gib ein Ticker-Symbol ein (z. B. AAPL, MSFT, TSLA)", value="AAPL")

if ticker:
    try:
        # Daten abrufen
        stock = yf.Ticker(ticker)
        data = stock.history(period="5d", interval="5m")
        latest = data.iloc[-1]

        # Berechnungen für EMA und RSI
        close_prices = data['Close']
        ema9 = close_prices.ewm(span=9).mean().iloc[-1]

        delta = close_prices.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        roll_up = up.rolling(14).mean()
        roll_down = down.rolling(14).mean()
        rs = roll_up / roll_down
        rsi = 100.0 - (100.0 / (1.0 + rs)).iloc[-1]

        # VWAP
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        vwap = (typical_price * data['Volume']).cumsum() / data['Volume'].cumsum()
        vwap_latest = vwap.iloc[-1]

        # Ausgabe
        st.subheader(f"Analyse für {ticker.upper()}")
        st.metric("Aktueller Kurs", f"{latest['Close']:.2f} USD")
        st.metric("VWAP", f"{vwap_latest:.2f} USD")
        st.metric("EMA 9", f"{ema9:.2f} USD")
        st.metric("RSI (14)", f"{rsi:.0f}")

        if rsi < 30:
            st.success("Signal: Überverkauft – mögliche Rebound-Chance.")
        elif rsi > 70:
            st.warning("Signal: Überkauft – Einstieg mit Vorsicht.")
        else:
            st.info("Signal: Neutral – Momentum prüfen.")

        st.markdown("**Hinweis:** Breakouts bei steigendem Volumen bieten häufig gute Chancen für kurzfristige Gewinne.")

        # Chart
        st.line_chart(close_prices[-50:])

    except Exception as e:
        st.error(f"Fehler bei der Datenabfrage oder Analyse: {e}")
