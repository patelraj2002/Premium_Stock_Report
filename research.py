import streamlit as st
import scholarly
from scholarly import scholarly
import time
from groq import Groq
import os

# Initialize Groq client
groq_client = Groq(
    api_key="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"  # Replace with your Groq API key
)

def get_summary_and_findings(title, abstract):
    prompt = f"""
    Based on the following research paper title and abstract, provide:
    1. A concise summary (2-3 sentences)
    2. Three key findings or main points
    
    Title: {title}
    Abstract: {abstract}
    
    Format the response as JSON with the following structure:
    {{
        "summary": "the summary here",
        "key_findings": ["finding1", "finding2", "finding3"]
    }}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="mixtral-8x7b-32768",  # or another appropriate model
            temperature=0.3,
            max_tokens=500
        )
        
        response = completion.choices[0].message.content
        # Convert string response to dictionary (you might need to add error handling)
        import json
        result = json.loads(response)
        return result["summary"], result["key_findings"]
    except Exception as e:
        print(f"Error with Groq API: {e}")
        return ("No summary available.", 
                ["Finding not available", 
                 "Finding not available", 
                 "Finding not available"])

def format_article(title, url, authors, summary, year, key_findings):
    html = f"""
    <div style="margin-bottom: 30px; padding: 15px; border-left: 3px solid #4CAF50; background-color: #f9f9f9;">
        <h3 style="color: #2C3E50;">• {title} Year: {year}</h3>
        <p><strong>URL:</strong> <a href="{url}" target="_blank">{url}</a></p>
        <p><strong>Authors:</strong> {authors}</p>
        <p><strong>Summary:</strong> {summary}</p>
        <p><strong>Key Findings:</strong></p>
        <ul>
            {''.join([f'<li>{finding}</li>' for finding in key_findings])}
        </ul>
    </div>
    """
    return html

def search_articles(query, num_articles=10):
    search_query = scholarly.search_pubs(query)
    articles = []
    count = 0
    
    while count < num_articles:
        try:
            article = next(search_query)
            
            # Extract available information
            title = article.get('bib', {}).get('title', 'No title available')
            year = article.get('bib', {}).get('year', 'N/A')
            url = f"https://scholar.google.com/scholar?cluster={article.get('cluster_id', '')}"
            authors = ', '.join(article.get('bib', {}).get('author', ['No authors available']))
            
            # Get abstract if available
            abstract = article.get('bib', {}).get('abstract', title)
            
            # Use Groq to generate summary and key findings
            summary, key_findings = get_summary_and_findings(title, abstract)
            
            articles.append({
                'title': title,
                'url': url,
                'authors': authors,
                'summary': summary,
                'year': year,
                'key_findings': key_findings
            })
            count += 1
            
        except StopIteration:
            break
        except Exception as e:
            print(f"Error processing article: {e}")
            continue
        
        time.sleep(2)  # Add delay to avoid hitting rate limits
        
    return articles

def main():
    st.set_page_config(page_title="Research Article Search", layout="wide")
    
    st.title("Research Article Search")
    st.markdown("""
    <style>
    .stTitle {
        color: #2C3E50;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Search input
    search_query = st.text_input("Enter your search query:")
    
    if search_query:
        with st.spinner('Searching for articles...'):
            articles = search_articles(search_query)
            
            if articles:
                for article in articles:
                    html_content = format_article(
                        article['title'],
                        article['url'],
                        article['authors'],
                        article['summary'],
                        article['year'],
                        article['key_findings']
                    )
                    st.markdown(html_content, unsafe_allow_html=True)
            else:
                st.error("No articles found.")

if __name__ == "__main__":
    main()