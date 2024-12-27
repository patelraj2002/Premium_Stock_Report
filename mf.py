from flask import Flask, render_template, request
import yfinance as yf
import requests

app = Flask(__name__)

# Use your Groq API key here
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/v1/generate"

def fetch_data(symbol):
    """
    Fetches data for mutual funds or ETFs based on the symbol.
    Handles unavailable data gracefully to prevent application crashes.
    """
    data = {}
    ticker = yf.Ticker(symbol)

    try:
        info = ticker.info
        data["info"] = info

        if info.get("quoteType") == "ETF" or info.get("quoteType") == "MUTUALFUND":
            # Basic price history and fundamentals
            data["price"] = ticker.history(period="1y")
            data["fundamentals"] = {
                "expense_ratio": info.get("annualReportExpenseRatio", "N/A"),
                "category": info.get("category", "N/A"),
                "nav": info.get("navPrice", "N/A")
            }
            # Optional holdings and sector weights if available
            data["sector_weights"] = info.get("sectorWeightings", "N/A")

            try:
                data["holdings"] = ticker.get_institutional_holders()
            except Exception:
                data["holdings"] = "Holdings data not available."

        else:
            raise ValueError("Unsupported instrument type for symbol:", symbol)

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None
    
    return data

def generate_report(symbol, data):
    """
    Sends data to the Groq API to generate a formatted report.
    """
    payload = {
        "prompt": f"Generate a detailed analysis report for the symbol '{symbol}', including the category, expense ratio, NAV, sector allocation, and top holdings for this {'ETF' if data['info']['quoteType'] == 'ETF' else 'mutual fund'}.",
        "max_tokens": 500,
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROQ_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("content", "Report generation failed.")
    else:
        return "Error: Could not generate report."

@app.route("/", methods=["GET", "POST"])
def index():
    report = ""
    if request.method == "POST":
        symbol = request.form.get("symbol").strip().upper()
        data = fetch_data(symbol)
        
        if data:
            report = generate_report(symbol, data)
        else:
            report = f"Error: Could not retrieve data for symbol '{symbol}'. Please check and try again."
    
    return render_template("index2.html", report=report)

if __name__ == "__main__":
    app.run(debug=True)
