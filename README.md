```python?code_reference&code_event_index=2
content = """# 📈 Options Alpha Assistant

An AI-powered quantitative options trading assistant built with Streamlit, Groq (Llama 3), and `yfinance`. Designed specifically for executing the **Wheel Strategy** (Cash-Secured Puts and Covered Calls), this tool scans historical support/resistance levels, fetches live options premiums, and calculates automated profit-taking exits.

## ✨ Features
- **Market Scanners**: One-click bulk scanning of US Mega-Caps, Financials, and Nifty 100 constituents.
- **Live Options Data**: Automatically pulls the nearest sensible expiration date and strike price based on 3-month historical floors and ceilings.
- **Automated Profit Taking**: Calculates precise Limit Order prices for 30% and 50% profit exits on entry premiums.
- **AI Chat Interface**: Ask natural language questions about specific setups.
- **Manual Price Overrides**: Bypass delayed API quotes by typing exact real-time prices (e.g., "Setup for NVDA at 128.50").

## 🛠️ Prerequisites
- Python 3.8+
- A [Groq API Key](https://console.groq.com/keys) (Free tier)

## 📦 Installation

1. **Navigate to your project directory:**
   ```bash
   # Make sure you are in your project folder
   cd /path/to/your/project
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # venv\\Scripts\\activate  # On Windows
   ```

3. **Install the required dependencies:**
   Run the following command to install all necessary packages:
   ```bash
   pip install streamlit yfinance groq python-dotenv pandas lxml html5lib beautifulsoup4 tabulate
   ```
   *(Note: `lxml`, `html5lib`, and `beautifulsoup4` are required by Pandas for robust data parsing under the hood).*

4. **Environment Variables Setup:**
   Create a `.env` file in the root of your project directory and add your Groq API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

## 🚀 Usage

1. **Start the Streamlit application:**
   Ensure your virtual environment is activated, then run:
   ```bash
   streamlit run app.py
   ```
2. **Open your browser:** The app will typically host locally at `http://localhost:8501`.
3. **Run Scans or Chat:** Use the sidebar to trigger bulk market scans or type directly into the terminal (e.g., "What is the setup for TSLA @ 200?").

## ⚠️ Disclaimer
This tool is for informational and educational purposes only. Options trading involves significant risk. Always verify premiums and strike prices in your live brokerage account before executing trades.
"""

with open("README.md", "w") as f:
    f.write(content)


```