import requests
import json
from datetime import datetime

# API Key
API_KEY = "tJJK650ilrzbpUNWeH25k9ShsOtL4XTz"

def get_stock_rating(ticker: str) -> dict:
    """
    Fetch stock rating data from Financial Modeling Prep API
    """
    url = f"https://financialmodelingprep.com/api/v3/rating/{ticker}"
    params = {"apikey": API_KEY}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print(f"No data found for ticker {ticker}")
            return None
            
        return data[0]
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except json.JSONDecodeError:
        print("Error parsing API response")
        return None

def display_rating_info(rating_data: dict):
    """
    Display rating information in a formatted way
    """
    print("\n" + "="*50)
    print(f"Stock Rating Analysis for {rating_data['symbol']}")
    print("="*50)
    
    print(f"\nDate: {rating_data['date']}")
    print(f"Overall Rating: {rating_data['rating']} (Score: {rating_data['ratingScore']})")
    print(f"Recommendation: {rating_data['ratingRecommendation']}")
    
    print("\nDetailed Ratings:")
    print("-"*30)
    
    metrics = {
        "DCF": ("DCF Analysis", 'ratingDetailsDCFScore', 'ratingDetailsDCFRecommendation'),
        "ROE": ("Return on Equity", 'ratingDetailsROEScore', 'ratingDetailsROERecommendation'),
        "ROA": ("Return on Assets", 'ratingDetailsROAScore', 'ratingDetailsROARecommendation'),
        "DE": ("Debt/Equity", 'ratingDetailsDEScore', 'ratingDetailsDERecommendation'),
        "PE": ("P/E Ratio", 'ratingDetailsPEScore', 'ratingDetailsPERecommendation'),
        "PB": ("P/B Ratio", 'ratingDetailsPBScore', 'ratingDetailsPBRecommendation')
    }
    
    for metric, (name, score_key, rec_key) in metrics.items():
        print(f"{name:15} | Score: {rating_data[score_key]:2} | {rating_data[rec_key]}")

def main():
    """
    Main function to run the stock rating analyzer
    """
    print("Stock Rating Analyzer")
    print("-"*20)
    
    while True:
        ticker = input("\nEnter stock ticker (or 'q' to quit): ").strip().upper()
        
        if ticker.lower() == 'q':
            break
            
        if not ticker:
            print("Please enter a valid ticker symbol")
            continue
            
        rating_data = get_stock_rating(ticker)
        if rating_data:
            display_rating_info(rating_data)
        
        print("\n" + "-"*50)

if __name__ == "__main__":
    main()