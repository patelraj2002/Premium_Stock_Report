import requests
import streamlit as st
from datetime import datetime
from groq import Groq
from bs4 import BeautifulSoup
import time

class DCFAnalyzer:
    def __init__(self):
        self.dcf_api_key = "09bef1b4-e838-4f58-8c90-a74d7101456f"
        self.base_url = "https://discountingcashflows.com/api"
        self.groq_client = Groq(
            api_key="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"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def generate_summary(self, text):
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
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def fetch_article_content(self, url):
        try:
            time.sleep(1)
            response = requests.get(url, headers=self.headers, timeout=10)
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            st.error(f"Error fetching article content: {str(e)}")
            return None

    def get_stock_news(self, tickers, page=1, length=15):
        try:
            url = f"{self.base_url}/news/?tickers={tickers}&page={page}&length={length}&key={self.dcf_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching stock news: {str(e)}")
            return []

    def display_summaries(self, tickers, page=1, length=15):
        with st.spinner('Fetching and analyzing news...'):
            news_data = self.get_stock_news(tickers=tickers, page=page, length=length)
            
            if news_data:
                for idx, news_item in enumerate(news_data):
                    st.markdown("---")
                    
                    # Display news details
                    st.subheader(f"{news_item.get('symbol', 'N/A')} News")
                    
                    # Title with link
                    title = news_item.get('title', 'No Title Available')
                    url = news_item.get('url', '#')
                    st.markdown(f"#### [{title}]({url})")
                    
                    # Date and source in columns
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("📅 Date:", news_item.get('publishedDate', 'Not Available'))
                    with col2:
                        st.write("🔗 Source:", news_item.get('site', 'Not Available'))
                    
                    # Get and display AI summary
                    with st.spinner(f'Analyzing article {idx + 1} of {len(news_data)}...'):
                        # Use initial text or try to fetch full content
                        initial_text = news_item.get('text', '')
                        full_text = self.fetch_article_content(url)
                        text_to_analyze = full_text if full_text else initial_text
                        
                        if text_to_analyze:
                            summary = self.generate_summary(text_to_analyze)
                            st.markdown("### Key Points")
                            st.markdown(summary)
                        
                        # Original text in expander
                        with st.expander("Show Original Text"):
                            st.write(text_to_analyze if text_to_analyze else "No content available")
                    
                    # Link to full article
                    st.markdown(f"[📰 Read full article]({url})")

def main():
    st.title("🚀 AI-Powered Stock News Analyzer")
    
    col1, col2, col3 = st.columns([2,1,1])
    
    with col1:
        tickers = st.text_input("Enter stock tickers (comma-separated)", value="AAPL")
    with col2:
        page = st.number_input("Page", min_value=1, value=1)
    with col3:
        length = st.number_input("Results per page", min_value=1, max_value=50, value=3)

    if st.button("🔍 Fetch and Analyze News"):
        if tickers:
            tickers = tickers.strip().upper()
            if not all(c.isalpha() or c == ',' for c in tickers):
                st.error("Invalid ticker format. Please use only letters and commas.")
                return
            
            analyzer = DCFAnalyzer()
            analyzer.display_summaries(tickers=tickers, page=page, length=length)
        else:
            st.warning("Please enter stock tickers.")

if __name__ == "__main__":
    main()
