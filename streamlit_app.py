import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import datetime

# ------------------------------
# TICKER-ERKENNUNG
# ------------------------------
ticker_db = pd.DataFrame({
    "Name": ["Apple", "Microsoft", "SAP", "Tesla", "MSCI World ETF"],
    "WKN": ["865985", "870747", "716460", "A1CX3T", "A0ETQX"],
    "ISIN": ["US0378331005", "US5949181045", "DE0007164600", "US88160R1014", "IE00B0M62Q58"],
    "Ticker": ["AAPL", "MSFT", "SAP.DE", "TSLA", "IQQW.DE"]
})

def find_ticker(query):
    query = query.strip().lower()
    for _, row in ticker_db.iterrows():
        if query in row['Name'].lower() or query == row['WKN'].lower() or query == row['ISIN'].lower():
            return row['Ticker']
    return query.upper()

st.set_page_config(page_title="Daytrading Terminal", layout="centered")
st.title("Daytrading Terminal – Analyse & Journal")

# ------------------------------
# TICKER-EINGABE
# ------------------------------
input_query = st.text_input("Aktienname, WKN oder ISIN eingeben", value="Apple")
resolved_ticker = find_ticker(input_query)
st.write(f"**Erkannter Ticker:** `{resolved_ticker}`")

# ------------------------------
# TECHNISCHE ANALYSE
# ------------------------------
try:
    stock = yf.Ticker(resolved_ticker)
    hist = stock.history(period="1mo", interval="1h")

    if hist.empty:
        hist = stock.history(period="1mo", interval="1d")

    if hist.empty:
        raise ValueError("Keine Kursdaten verfügbar. Bitte anderen Ticker versuchen.")

    usd_to_eur = 0.92
    hist['Close_EUR'] = hist['Close'] * usd_to_eur
    hist['EMA9'] = hist['Close_EUR'].ewm(span=9).mean()
    hist['EMA20'] = hist['Close_EUR'].ewm(span=20).mean()

    delta = hist['Close_EUR'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    hist['RSI'] = 100 - (100 / (1 + rs))

    hist['SMA20'] = hist['Close_EUR'].rolling(window=20).mean()
    hist['UpperBB'] = hist['SMA20'] + 2 * hist['Close_EUR'].rolling(window=20).std()
    hist['LowerBB'] = hist['SMA20'] - 2 * hist['Close_EUR'].rolling(window=20).std()

    latest = hist.dropna().iloc[-1]

    st.subheader(f"{resolved_ticker} – Technische Analyse (EUR)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Kurs", f"{latest['Close_EUR']:.2f}")
    col2.metric("EMA 9", f"{latest['EMA9']:.2f}")
    col3.metric("EMA 20", f"{latest['EMA20']:.2f}")

    if latest['EMA9'] > latest['EMA20']:
        st.success("Aufwärtstrend (Bullish Crossover)")
    elif latest['EMA9'] < latest['EMA20']:
        st.error("Abwärtstrend (Bearish Crossover)")
    else:
        st.info("Seitwärtstrend")

    rsi = latest['RSI']
    if rsi < 30:
        st.success(f"RSI: {rsi:.1f} (überverkauft)")
    elif rsi > 70:
        st.warning(f"RSI: {rsi:.1f} (überkauft)")
    else:
        st.info(f"RSI: {rsi:.1f} (neutral)")

    st.markdown("### Kursverlauf inkl. Bollinger Bänder")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close_EUR'], name='Kurs', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['UpperBB'], name='Upper BB', line=dict(color='lightgray')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['LowerBB'], name='Lower BB', line=dict(color='lightgray')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA9'], name='EMA 9', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA20'], name='EMA 20', line=dict(color='red', dash='dot')))
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Volumenprofil")
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volumen', marker_color='orange'))
    vol_fig.update_layout(height=200)
    st.plotly_chart(vol_fig, use_container_width=True)

except Exception as e:
    st.warning(f"Fehler bei Datenanalyse: {e}")

# ------------------------------
# TRADEJOURNAL
# ------------------------------
st.markdown("### Tradejournal")
csv_file = "tradejournal.csv"
try:
    journal_df = pd.read_csv(csv_file)
except FileNotFoundError:
    journal_df = pd.DataFrame(columns=["Datum", "Ticker", "Entry (EUR)", "Exit (EUR)", "Stückzahl", "Gewinn/Verlust (EUR)", "Setup", "Notizen"])

with st.form("new_trade"):
    col1, col2 = st.columns(2)
    entry = col1.number_input("Entry-Kurs (EUR)", min_value=0.0, value=100.0)
    exit = col2.number_input("Exit-Kurs (EUR)", min_value=0.0, value=105.0)
    qty = st.number_input("Stückzahl", min_value=1, value=10)
    setup = st.text_input("Setup", value="Breakout")
    notes = st.text_area("Notizen")
    submit = st.form_submit_button("Speichern")

    if submit:
        date = datetime.date.today().strftime("%Y-%m-%d")
        pnl = round((exit - entry) * qty, 2)
        new_entry = {
            "Datum": date,
            "Ticker": resolved_ticker,
            "Entry (EUR)": entry,
            "Exit (EUR)": exit,
            "Stückzahl": qty,
            "Gewinn/Verlust (EUR)": pnl,
            "Setup": setup,
            "Notizen": notes
        }
        journal_df = pd.concat([journal_df, pd.DataFrame([new_entry])], ignore_index=True)
        journal_df.to_csv(csv_file, index=False)
        st.success("Trade gespeichert!")

if not journal_df.empty:
    st.dataframe(journal_df.sort_values(by="Datum", ascending=False))

