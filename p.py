import requests
from groq import Groq
from bs4 import BeautifulSoup
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DCFAnalyzer:
    def __init__(self):
        logging.info("Initializing DCFAnalyzer...")
        self.dcf_api_key = "09bef1b4-e838-4f58-8c90-a74d7101456f"
        self.base_url = "https://discountingcashflows.com/api"
        try:
            self.groq_client = Groq(
                api_key="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"
            )
            logging.info("Groq client initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Groq client: {str(e)}")
            raise
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def generate_summary(self, text):
        logging.info("Generating summary...")
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial news analyst. Summarize the following text in 5 clear bullet points, focusing on the key financial implications and market impact:"
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                model="llama3-8b-8192",
                temperature=0.3,
                max_tokens=300
            )
            logging.info("Summary generated successfully")
            return chat_completion.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def fetch_article_content(self, url):
        logging.info(f"Fetching article content from: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            logging.info("Article content fetched successfully")
            return text
        except Exception as e:
            logging.error(f"Error fetching article content: {str(e)}")
            return ""

    def get_stock_news(self, tickers, page=1, length=5):
        logging.info(f"Fetching news for tickers: {tickers}")
        try:
            url = f"{self.base_url}/news/?tickers={tickers}&page={page}&length={length}&key={self.dcf_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            news_data = response.json()
            logging.info(f"Successfully fetched {len(news_data)} news items")
            return news_data
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching stock news: {str(e)}")
            return []

    def display_summaries(self, tickers, page=1, length=5):
        print("\nFetching and analyzing news...")
        news_data = self.get_stock_news(tickers=tickers, page=page, length=length)
        
        if news_data and len(news_data) > 0:
            for idx, news_item in enumerate(news_data, 1):
                print(f"\n--- Article {idx} of {len(news_data)} ---\n")
                
                symbol = news_item.get('symbol', 'N/A')
                print(f"{symbol} News")
                
                title = news_item.get('title', 'No Title Available')
                url = news_item.get('url', '#')
                print(f"Title: {title}")
                print(f"URL: {url}")
                
                print(f"Date: {news_item.get('publishedDate', 'Not Available')}")
                print(f"Source: {news_item.get('site', 'Not Available')}")
                
                print('\nAnalyzing article content...')
                initial_text = news_item.get('text', '')
                full_text = self.fetch_article_content(url)
                text_to_analyze = full_text if full_text else initial_text
                
                if text_to_analyze:
                    print("\nGenerating AI Summary...")
                    summary = self.generate_summary(text_to_analyze)
                    print("\nKey Points:")
                    print(summary)
                    
                    print("\nWould you like to see the original text? (yes/no)")
                    show_original = input().lower().strip()
                    if show_original == 'yes':
                        print("\nOriginal Text:")
                        print(text_to_analyze)
                
                print(f"\nFull article available at: {url}")
                
                if idx < len(news_data):
                    print("\nPress Enter to continue to next article or 'q' to quit...")
                    if input().lower().strip() == 'q':
                        break
        else:
            print("No news data found for the specified ticker(s)")

def main():
    while True:
        print("\n=== AI-Powered Stock News Analyzer ===")
        print("\nEnter stock ticker(s) (comma-separated for multiple, or 'quit' to exit):")
        tickers = input().strip()
        
        if tickers.lower() == 'quit':
            print("Exiting program...")
            break
        
        print("\nEnter number of news articles to analyze (1-10):")
        try:
            length = int(input().strip())
            length = max(1, min(10, length))  # Ensure length is between 1 and 10
        except ValueError:
            print("Invalid input. Using default value of 5")
            length = 5
        
        analyzer = DCFAnalyzer()
        analyzer.display_summaries(tickers=tickers, length=length)
        
        print("\nWould you like to analyze another stock? (yes/no)")
        if input().lower().strip() != 'yes':
            print("Thank you for using the Stock News Analyzer!")
            break

if __name__ == "__main__":
    main()