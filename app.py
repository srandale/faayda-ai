import streamlit as st
import os
import re
import pandas as pd
import yfinance as yf
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Options Alpha", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stChatMessage { border-radius: 10px; border: 1px solid #1f2937; background-color: #161b22 !important; }
    h1 { color: #00d26a; font-family: 'Helvetica Neue', sans-serif; }
    div.stButton > button:first-child { background-color: #1f2937; color: white; border: 1px solid #00d26a; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZATION ---
load_dotenv()
client = Groq()



import pandas as pd
import streamlit as st

@st.cache_data(ttl=86400) # Cache for 24 hours
def get_sp500_tickers():
    # Pass a standard browser User-Agent to bypass the 403 Forbidden block
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Include storage_options to send the headers
    table = pd.read_html(
        'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        storage_options=headers
    )
    
    df = table[0]
    tickers = df['Symbol'].tolist()
    
    # Clean up tickers for Yahoo Finance (e.g., BRK.B needs to be BRK-B)
    clean_tickers = [ticker.replace('.', '-') for ticker in tickers]
    return clean_tickers

# Then, in your code, simply call:
# US_TICKERS = get_sp500_tickers()

# --- WATCHLIST UNIVERSES ---
US_TICKERS = get_sp500_tickers()
""" US_TICKERS = [
    "WMT", "AMZN", "AAPL", "UNH", "CVS", "BRK-B", "GOOGL", "MSFT", "MCK", "CVX", 
    "CAH", "COST", "JPM", "KR", "WBA", "VZ", "F", "GM", "ELEV", "CI", 
    "T", "BAC", "WFC", "BA", "HD", "CMCSA", "JNJ", "META", "TGT", "IBM", 
    "PEP", "C", "AIG", "LMT", "PG", "UPS", "INTC", "MET", "PFE", "CAT", 
    "NKE", "SYY", "DE", "TSLA", "NVDA", "ORCL", "NFLX", "CRM", "AMD", "UBER", 
    "PYPL", "SQ", "ABNB", "SHOP", "SPOT", "NOW", "WDAY", "ADBE", "INTU", "CSCO", 
    "TXN", "QCOM", "AVGO", "AMAT", "MU", "LRCX", "KLAC", "SNPS", "CDNS", "V", 
    "MA", "AXP", "DFS", "COF", "SYF", "ALL", "TRV", "PGR", "XOM", "COP", 
    "SLB", "EOG", "OXY", "MPC", "PSX", "VLO", "HAL", "BKR", "NEE", "DUK", 
    "SO", "D", "EXC", "AEP", "SRE", "XEL", "PEG", "WMT", "HD", "LOW", 
    "TGT", "BBY", "TJX", "ROST", "DG", "DLTR", "MCD", "SBUX", "CMG", "YUM",
    "SNOW", "PLTR", "CRWD", "PANW", "FTNT", "DDOG", "NET"
] """


NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS", 
    "BHARTIARTL.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS", "BAJFINANCE.NS", 
    "AXISBANK.NS", "KOTAKBANK.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "TITAN.NS", "WIPRO.NS", "ULTRACEMCO.NS"
]

# --- HELPER FUNCTIONS ---
def get_option_targets(ticker_str, target_price, opt_type="put"):
    try:
        tkr = yf.Ticker(ticker_str)
        dates = tkr.options
        if not dates: return None
            
        exp_date = dates[1] if len(dates) > 1 else dates[0] 
        chain = tkr.option_chain(exp_date)
        opts = chain.puts if opt_type == "put" else chain.calls
        
        if opts.empty: return None
            
        closest_idx = (abs(opts['strike'] - target_price)).idxmin()
        best_opt = opts.loc[closest_idx]
        
        entry_premium = round(best_opt['lastPrice'], 2)
        return {
            "Exp Date": exp_date,
            "Strike": best_opt['strike'],
            "Entry Premium": entry_premium,
            "Exit (30% Profit)": round(entry_premium * 0.70, 2),
            "Exit (50% Profit)": round(entry_premium * 0.50, 2)
        }
    except Exception:
        return None

@st.cache_data(ttl=3600)
def scan_market_levels(market_type="US"):
    """Runs ONLY when buttons are clicked."""
    tickers = US_TICKERS if market_type == "US" else NIFTY_TICKERS
    data = yf.download(tickers, period="3mo", group_by='ticker', progress=False)
    
    put_candidates, call_candidates = [], []
    
    for t in tickers:
        try:
            df = data[t] if len(tickers) > 1 else data
            if df.empty or df['Close'].isna().all(): continue
                
            current_price = float(df['Close'].dropna().iloc[-1])
            low_3m, high_3m = float(df['Low'].min()), float(df['High'].max())
            
            put_candidates.append({"Ticker": t, "Stock Price": round(current_price, 2), "Support": round(low_3m, 2), "Dist": (current_price - low_3m) / low_3m})
            call_candidates.append({"Ticker": t, "Stock Price": round(current_price, 2), "Resistance": round(high_3m, 2), "Dist": (high_3m - current_price) / high_3m})
        except Exception: continue
            
    top_puts = sorted(put_candidates, key=lambda x: x["Dist"])[:10]
    top_calls = sorted(call_candidates, key=lambda x: x["Dist"])[:10]
    
    final_puts, final_calls = [], []
    
    for p in top_puts:
        opt = get_option_targets(p["Ticker"], p["Support"], "put")
        if opt:
            del p["Dist"]; p.update(opt); final_puts.append(p)
            
    for c in top_calls:
        opt = get_option_targets(c["Ticker"], c["Resistance"], "call")
        if opt:
            del c["Dist"]; c.update(opt); final_calls.append(c)

    return pd.DataFrame(final_puts), pd.DataFrame(final_calls)

# --- UI HEADER ---
st.title("📈 Options Alpha Assistant")
st.markdown("##### **Wheel Strategy scanner with manual override capabilities.**")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR & SCANNER ---
with st.sidebar:
    st.header("Radar & Scanners")
    
    if st.button("🇺🇸 Scan US Market"):
        with st.spinner("Calculating support/resistance and options exits..."):
            puts, calls = scan_market_levels("US")
            scan_msg = f"**US Market Scan Complete**\n\n**📉 Top Put Sells (Near Support):**\n{puts.to_markdown(index=False)}\n\n**📈 Top Call Sells (Near Resistance):**\n{calls.to_markdown(index=False)}"
            st.session_state.messages.append({"role": "user", "content": scan_msg})
            st.rerun()

    if st.button("🇮🇳 Scan Nifty 100"):
        with st.spinner("Fetching Nifty data..."):
            puts, calls = scan_market_levels("IN")
            puts_table = puts.to_markdown(index=False) if not puts.empty else "No valid options chains found."
            calls_table = calls.to_markdown(index=False) if not calls.empty else "No valid options chains found."
            scan_msg = f"**Indian Market Scan Complete**\n\n**📉 Top Put Sells (Near Support):**\n{puts_table}\n\n**📈 Top Call Sells (Near Resistance):**\n{calls_table}"
            st.session_state.messages.append({"role": "user", "content": scan_msg})
            st.rerun()

    st.markdown("---")
    if st.button("Clear Terminal"):
        st.session_state.messages = []
        st.rerun()

# Display Chat
for m in st.session_state.messages:
    avatar = "🤖" if m["role"] == "assistant" else "👤"
    with st.chat_message(m["role"], avatar=avatar):
        st.markdown(m["content"])

# --- MAIN CHAT LOGIC ---
if prompt := st.chat_input("E.g., 'Setup for NVDA' OR 'Setup for NVDA at 128.50'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_user_msg = st.session_state.messages[-1]["content"]
    
    # REGEX: Finds Tickers (e.g., NVDA, TCS.NS) and an optional price following it (e.g., "at 130", "@ 130.50", "130")
    # Captures Group 1: Ticker, Group 2: Price (if provided)
    ticker_matches = re.findall(r'\b([A-Z]{2,5}(?:\.NS)?)\b(?:\s+(?:at|@|is|:|-)?\s*\$?\s*(\d+(?:\.\d+)?))?', last_user_msg.upper())
    
    live_context = ""
    
    if ticker_matches and "SCAN COMPLETE" not in last_user_msg.upper():
        live_context = "\n\nMARKET DATA INJECTED:\n"
        for match in ticker_matches:
            ticker = match[0]
            manual_price_str = match[1]
            
            # Fetch 3-month history for the single ticker to establish Support/Resistance
            try:
                hist = yf.Ticker(ticker).history(period="3mo")
                if hist.empty: continue
                
                sup = round(hist['Low'].min(), 2)
                res = round(hist['High'].max(), 2)
                
                # Use user's manual price if provided, otherwise fallback to yfinance current close
                if manual_price_str:
                    curr_price = float(manual_price_str)
                    price_source = "(User Manual Override)"
                else:
                    curr_price = round(hist['Close'].iloc[-1], 2)
                    price_source = "(yfinance Latest)"
                
                live_context += f"- **{ticker}**:\n  - Current Price: ${curr_price} {price_source}\n  - 3-Mo Support: ${sup}\n  - 3-Mo Resistance: ${res}\n"
                
            except Exception:
                continue

    with st.chat_message("assistant", avatar="🤖"):
        system_prompt = f"""
        IDENTITY: 
        You are an expert quantitative options trading assistant focusing on the "Wheel Strategy".

        STRICT RULES:
        1. Base your technical analysis strictly on the MARKET DATA INJECTED below.
        2. If the user provided a manual price override, acknowledge it and calculate strike setups relative to that specific price and the provided historical support/resistance.
        3. If evaluating a scan table, advise on "Buy-To-Close" Limit orders for 30% or 50% profit taking.
        4. Keep answers concise, focusing on capital efficiency, strike placement, and profit realization.
        5. No AI prefixes. Start analyzing immediately.
        {live_context}
        """

        context = [{"role": "system", "content": system_prompt}] + st.session_state.messages[-5:]

        try:
            response = client.chat.completions.create(
                messages=context,
                model="meta-llama/llama-4-scout-17b-16e-instruct", 
                temperature=0.3,
                max_tokens=500
            )
            
            ans = response.choices[0].message.content.strip()
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            
        except Exception as e:
            st.error(f"Execution Error: {e}")