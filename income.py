import requests
import pandas as pd
from datetime import datetime

def fetch_financial_data(ticker, api_key):
    """Fetch financial data from FMP API"""
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}"
    params = {
        "period": "annual",
        "apikey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def format_number(number):
    """Format large numbers in billions/millions"""
    if number is None or number == 0:
        return "N/A"
    
    billion = 1_000_000_000
    million = 1_000_000
    
    if abs(number) >= billion:
        return f"${number/billion:.2f}B"
    elif abs(number) >= million:
        return f"${number/million:.2f}M"
    else:
        return f"${number:,.2f}"

def format_ratio(ratio):
    """Format ratio as percentage"""
    if ratio is None:
        return "N/A"
    return f"{(ratio * 100):.2f}%"

def calculate_growth(current, previous):
    """Calculate year-over-year growth percentage"""
    if not previous or not current:
        return "N/A"
    return f"{((current - previous) / previous * 100):.2f}%"

def display_key_metrics_comparison(current_data, previous_data=None):
    """Display key metrics with year-over-year comparison"""
    print("\n=== KEY METRICS AND YEAR-OVER-YEAR COMPARISON ===")
    print("\nCurrent Year Metrics:")
    print(f"• Revenue: {format_number(current_data['revenue'])}")
    print(f"• Earnings Per Share (EPS): ${current_data['eps']:.2f}")
    print(f"• Net Income: {format_number(current_data['netIncome'])}")
    print(f"• Gross Margin: {format_ratio(current_data['grossProfitRatio'])}")
    
    if previous_data:
        print("\nYear-over-Year Growth:")
        print(f"• Revenue Growth: {calculate_growth(current_data['revenue'], previous_data['revenue'])}")
        print(f"• EPS Growth: {calculate_growth(current_data['eps'], previous_data['eps'])}")
        print(f"• Net Income Growth: {calculate_growth(current_data['netIncome'], previous_data['netIncome'])}")
        
        print("\nMargin Comparison:")
        print(f"• Gross Margin Change: {calculate_growth(current_data['grossProfitRatio'], previous_data['grossProfitRatio'])}")

def display_financial_data(data):
    """Display all available financial metrics"""
    
    print(f"Revenue: {format_number(data['revenue'])}")
    print(f"Cost of Revenue: {format_number(data['costOfRevenue'])}")
    print(f"Gross Profit: {format_number(data['grossProfit'])}")
    print(f"Gross Profit Ratio: {format_ratio(data['grossProfitRatio'])}")
    
    print("\n=== Operating Expenses ===")
    print(f"Operating Expenses: {format_number(data['operatingExpenses'])}")
    
    print("\n=== Income Metrics ===")
    print(f"Income Before Tax: {format_number(data['incomeBeforeTax'])}")
    print(f"Income Tax Expense: {format_number(data['incomeTaxExpense'])}")
    print(f"Net Income: {format_number(data['netIncome'])}")
    print(f"Net Income Ratio: {format_ratio(data['netIncomeRatio'])}")
    
    print("\n=== Interest and EBITDA ===")
    print(f"EBITDA: {format_number(data['ebitda'])}")
    print(f"EBITDA Ratio: {format_ratio(data['ebitdaratio'])}")
    
    print("\n=== Share Information ===")
    print(f"EPS: ${data['eps']:.2f}")
    print(f"EPS Diluted: ${data['epsdiluted']:.2f}")
    
    

def main():
    API_KEY = "tJJK650ilrzbpUNWeH25k9ShsOtL4XTz"
    
    while True:
        ticker = input("\nEnter company ticker (or 'quit' to exit): ").upper()
        if ticker == 'QUIT':
            break
            
        data = fetch_financial_data(ticker, API_KEY)
        
        if not data:
            print("No data found for this ticker.")
            continue
        
        print(f"\n=== {ticker} Financial Report ===")
        
        # Display key metrics comparison first
        if len(data) > 1:
            display_key_metrics_comparison(data[0], data[1])
        else:
            display_key_metrics_comparison(data[0])
        
        # Display detailed current year data
        print("\n=== DETAILED FINANCIAL DATA ===")
        display_financial_data(data[0])
        
        # Option to view historical data
        if len(data) > 1:
            view_historical = input("\nWould you like to view historical detailed data? (y/n): ").lower()
            if view_historical == 'y':
                for historical_data in data[1:]:
                    print(f"\n{'='*50}")
                    print(f"Historical Data for {historical_data['date']}")
                    print(f"{'='*50}")
                    display_financial_data(historical_data)

if __name__ == "__main__":
    main()