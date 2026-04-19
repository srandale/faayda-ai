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
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZATION ---
load_dotenv()
client = Groq()

@st.cache_data(ttl=86400) # Cache for 24 hours
def get_sp500_tickers():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    table = pd.read_html(
        'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        storage_options=headers
    )
    df = table[0]
    tickers = df['Symbol'].tolist()
    clean_tickers = [ticker.replace('.', '-') for ticker in tickers]
    return clean_tickers

# --- WATCHLIST UNIVERSES ---
US_TICKERS = get_sp500_tickers()

NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS", 
    "BHARTIARTL.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS", "BAJFINANCE.NS", 
    "AXISBANK.NS", "KOTAKBANK.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "TITAN.NS", "WIPRO.NS", "ULTRACEMCO.NS"
]

# --- HELPER FUNCTIONS ---
def get_option_targets(ticker_str, target_price, current_price, opt_type="put"):
    try:
        tkr = yf.Ticker(ticker_str)
        dates = tkr.options
        if not dates: return None
            
        exp_date = dates[3] if len(dates) > 3 else dates[-1] 
        chain = tkr.option_chain(exp_date)
        opts = chain.puts if opt_type == "put" else chain.calls
        
        if opts.empty: return None
        
        if opt_type == "put":
             min_buffer_price = current_price * 0.96
             adjusted_target = min(target_price, min_buffer_price)
        else: # call
             min_buffer_price = current_price * 1.04
             adjusted_target = max(target_price, min_buffer_price)
            
        closest_idx = (abs(opts['strike'] - adjusted_target)).idxmin()
        best_opt = opts.loc[closest_idx]
        
        entry_premium = round(best_opt['lastPrice'], 2)
        capital_required = best_opt['strike'] * 100
        premium_collected = entry_premium * 100
        roc_percent = round((premium_collected / capital_required) * 100, 2)
        
        return {
            "Exp Date": exp_date,
            "Target Strike": best_opt['strike'],
            "Entry Premium": entry_premium,
            "ROC (%)": f"{roc_percent}%",  # UPGRADE: Capital efficiency metric added
            "Exit (50% Profit)": round(entry_premium * 0.50, 2)
        }
    except Exception:
        return None

@st.cache_data(ttl=3600)
def scan_market_levels(market_type="US"):
    tickers = US_TICKERS if market_type == "US" else NIFTY_TICKERS
    data = yf.download(tickers, period="1mo", group_by='ticker', progress=False)
    
    put_candidates, call_candidates = [], []
    
    for t in tickers:
        try:
            df = data[t] if len(tickers) > 1 else data
            if df.empty or df['Close'].isna().all(): continue
                
            current_price = float(df['Close'].dropna().iloc[-1])
            low_1m, high_1m = float(df['Low'].min()), float(df['High'].max())
            
            put_candidates.append({"Ticker": t, "Stock Price": round(current_price, 2), "Support": round(low_1m, 2), "Dist": (current_price - low_1m) / low_1m})
            call_candidates.append({"Ticker": t, "Stock Price": round(current_price, 2), "Resistance": round(high_1m, 2), "Dist": (high_1m - current_price) / high_1m})
        except Exception: continue
            
    top_puts = sorted(put_candidates, key=lambda x: x["Dist"])[:10]
    top_calls = sorted(call_candidates, key=lambda x: x["Dist"])[:10]
    
    final_puts, final_calls = [], []
    
    for p in top_puts:
        opt = get_option_targets(p["Ticker"], p["Support"], p["Stock Price"], "put")
        if opt:
            del p["Dist"]; p.update(opt); final_puts.append(p)
            
    for c in top_calls:
        opt = get_option_targets(c["Ticker"], c["Resistance"], c["Stock Price"], "call")
        if opt:
            del c["Dist"]; c.update(opt); final_calls.append(c)

    return pd.DataFrame(final_puts), pd.DataFrame(final_calls)

# --- UI HEADER ---
st.title("📈 Options Alpha Assistant")
st.markdown("##### **Wheel Strategy scanner & interactive options terminal.**")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR & SCANNER ---
with st.sidebar:
    st.header("Radar & Scanners")
    
    # UPGRADE: Passing DataFrames to Chat History instead of raw text
    if st.button("🇺🇸 Scan US Market"):
        with st.spinner("Calculating 30-day support/resistance and options exits..."):
            puts, calls = scan_market_levels("US")
            st.session_state.messages.append({
                "role": "user", 
                "content": "I just ran a US Market scan. Please evaluate the top setups.",
                "puts": puts,
                "calls": calls
            })
            st.rerun()

    if st.button("🇮🇳 Scan Nifty 100"):
        with st.spinner("Fetching Nifty data..."):
            puts, calls = scan_market_levels("IN")
            st.session_state.messages.append({
                "role": "user", 
                "content": "I just ran an Indian Market scan. Please evaluate the top setups.",
                "puts": puts,
                "calls": calls
            })
            st.rerun()

    st.markdown("---")
    if st.button("Clear Terminal"):
        st.session_state.messages = []
        st.rerun()

# --- DISPLAY CHAT HISTORY ---
for m in st.session_state.messages:
    avatar = "🤖" if m["role"] == "assistant" else "👤"
    with st.chat_message(m["role"], avatar=avatar):
        
        # Render Interactive Dataframes if they exist in the message
        if "puts" in m and not m["puts"].empty:
            st.markdown("### 📉 Top Put Sells (Near 30-Day Support)")
            st.dataframe(m["puts"], use_container_width=True, hide_index=True)
        if "calls" in m and not m["calls"].empty:
            st.markdown("### 📈 Top Call Sells (Near 30-Day Resistance)")
            st.dataframe(m["calls"], use_container_width=True, hide_index=True)
            
        # Render KPI Cards if they exist in the message
        if "kpis" in m and m["kpis"]:
            for kpi in m["kpis"]:
                st.markdown(f"**Quick View: {kpi['ticker']}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Price", f"${kpi['curr_price']}")
                
                # Calculate percentage delta for the UI metrics
                sup_delta = round(((kpi['sup'] - kpi['curr_price']) / kpi['curr_price']) * 100, 2)
                res_delta = round(((kpi['res'] - kpi['curr_price']) / kpi['curr_price']) * 100, 2)
                
                col2.metric("1-Mo Support", f"${kpi['sup']}", f"{sup_delta}%", delta_color="inverse")
                col3.metric("1-Mo Resistance", f"${kpi['res']}", f"{res_delta}%", delta_color="normal")
            st.divider()

        st.markdown(m["content"])

# --- MAIN CHAT LOGIC ---
if prompt := st.chat_input("E.g., 'Setup for NVDA' OR 'Setup for NVDA at 128.50'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # We redraw the user message immediately for responsiveness
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_user_msg = st.session_state.messages[-1]
    msg_text = last_user_msg["content"]
    
    ticker_matches = re.findall(r'\b([A-Z]{2,5}(?:\.NS)?)\b(?:\s+(?:at|@|is|:|-)?\s*\$?\s*(\d+(?:\.\d+)?))?', msg_text.upper())
    
    live_context = ""
    kpi_metrics = [] # Hold the KPI data for the UI
    
    # Check if this is a manual query or a button scan
    is_scan = "puts" in last_user_msg
    
    if is_scan:
        # Feed the table data behind the scenes to the LLM so it can analyze the scan
        live_context = "\n\nMARKET SCAN DATA INJECTED:\n"
        if not last_user_msg["puts"].empty:
            live_context += "PUTS:\n" + last_user_msg["puts"].to_markdown() + "\n"
        if not last_user_msg["calls"].empty:
            live_context += "CALLS:\n" + last_user_msg["calls"].to_markdown() + "\n"
            
    elif ticker_matches:
        live_context = "\n\nMARKET DATA INJECTED:\n"
        for match in ticker_matches:
            ticker = match[0]
            manual_price_str = match[1]
            
            try:
                hist = yf.Ticker(ticker).history(period="1mo")
                if hist.empty: continue
                
                sup = round(hist['Low'].min(), 2)
                res = round(hist['High'].max(), 2)
                
                if manual_price_str:
                    curr_price = float(manual_price_str)
                    price_source = "(User Manual Override)"
                else:
                    curr_price = round(hist['Close'].iloc[-1], 2)
                    price_source = "(yfinance Latest)"
                
                # Save KPI data to render in the UI
                kpi_metrics.append({
                    "ticker": ticker,
                    "curr_price": curr_price,
                    "sup": sup,
                    "res": res
                })
                
                put_setup = get_option_targets(ticker, sup, curr_price, "put")
                call_setup = get_option_targets(ticker, res, curr_price, "call")
                
                live_context += f"- **{ticker}**:\n  - Current Price: ${curr_price} {price_source}\n  - 1-Mo Support: ${sup}\n  - 1-Mo Resistance: ${res}\n"
                
                if put_setup:
                     live_context += f"  - **Suggested Put Setup**: Sell {put_setup['Target Strike']} Strike Expiring {put_setup['Exp Date']}. Target Entry Premium: ${put_setup['Entry Premium']}. Target 50% Profit Exit: ${put_setup['Exit (50% Profit)']}\n"
                if call_setup:
                     live_context += f"  - **Suggested Call Setup**: Sell {call_setup['Target Strike']} Strike Expiring {call_setup['Exp Date']}. Target Entry Premium: ${call_setup['Entry Premium']}. Target 50% Profit Exit: ${call_setup['Exit (50% Profit)']}\n"
                
            except Exception:
                continue

    with st.chat_message("assistant", avatar="🤖"):
        # If we have KPIs, render them immediately so the user doesn't wait for the LLM
        if kpi_metrics:
            for kpi in kpi_metrics:
                st.markdown(f"**Quick View: {kpi['ticker']}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Price", f"${kpi['curr_price']}")
                sup_delta = round(((kpi['sup'] - kpi['curr_price']) / kpi['curr_price']) * 100, 2)
                res_delta = round(((kpi['res'] - kpi['curr_price']) / kpi['curr_price']) * 100, 2)
                col2.metric("1-Mo Support", f"${kpi['sup']}", f"{sup_delta}%", delta_color="inverse")
                col3.metric("1-Mo Resistance", f"${kpi['res']}", f"{res_delta}%", delta_color="normal")
            st.divider()

        system_prompt = f"""
        IDENTITY: 
        You are an expert quantitative options trading assistant focusing on the "Wheel Strategy".

        STRICT RULES:
        1. Base your technical analysis strictly on the MARKET DATA INJECTED below.
        2. If the user provided a manual price override, acknowledge it.
        3. ALWAYS advise setting "Buy-To-Close" Limit orders for profit taking.
        4. When evaluating setups, consider the newly added 'ROC (%)' (Return on Capital) to determine if a trade is highly efficient or tying up too much cash for too little premium.
        5. Keep answers concise. Focus on capital efficiency, strike placement, and profit realization.
        6. No AI prefixes. Start analyzing immediately.
        {live_context}
        """

        # Context slice to maintain chat memory without overloading
        chat_memory = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-5:]]
        context = [{"role": "system", "content": system_prompt}] + chat_memory

        try:
            response = client.chat.completions.create(
                messages=context,
                model="llama-3.1-8b-instant", 
                temperature=0.3,
                max_tokens=500
            )
            
            ans = response.choices[0].message.content.strip()
            st.markdown(ans)
            
            # Save the full assistant message (including UI elements) to history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": ans,
                "kpis": kpi_metrics
            })
            
        except Exception as e:
            st.error(f"Execution Error: {e}")
