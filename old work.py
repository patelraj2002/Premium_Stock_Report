import os
import logging
from flask import Flask, render_template, request, jsonify, Response
import yfinance as yf
import pdfkit
import requests
import datetime as dt
import json
from groq import Groq
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from html.parser import HTMLParser
import traceback
import sys


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# API keys
API_KEY = 'CBW00IFBKPX65Q5D'
BASE_URL = 'https://www.alphavantage.co/query'
EOD_API_TOKEN = '670e930c66a298.91756873'
os.environ["GROQ_API_KEY"] = "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"
DCF_API_KEY = "c04b2887-3132-4684-ac58-9fc3b3e2dc81"

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['GET'])
def analyze_stock():
    try:
        symbol = request.args.get('symbol', '').upper()
        if not symbol:
            return jsonify({'error': 'No symbol provided'}), 400

        data = fetch_all_data(symbol)
        report_sections = generate_report_sections(symbol, data)
        
        return jsonify({'report': report_sections})
    except Exception as e:
        error_type, error_value, error_traceback = sys.exc_info()
        error_details = {
            'error_type': str(error_type),
            'error_message': str(error_value),
            'traceback': traceback.format_exc()
        }
        logging.error(f"Error in analyze_stock: {error_details}")
        return jsonify(error_details), 500


def generate_report_sections(symbol, data):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    report_sections = []

    sections = [
        ("Basic Information", generate_basic_info_prompt),
        ("Executive Summary", generate_executive_summary_prompt),
        ("About the Company", generate_about_company_prompt),
        ("Fundamental Analysis", generate_fundamental_analysis_prompt),
        ("Technical Analysis", generate_technical_analysis_prompt),
        ("Latest Earnings Report", generate_earnings_report_prompt),
        ("Press Release Summary", generate_press_release_prompt),
        ("Earnings Call Summary", generate_earnings_call_prompt),
        ("Historical Earnings Performance", generate_historical_earnings_prompt),
        ("5 Key Things to Know", generate_key_things_prompt),
        ("Analyst Coverage", generate_analyst_coverage_prompt),
        ("Company's Own Guidance", generate_company_guidance_prompt),
        ("Research Articles", generate_research_articles_prompt),
        ("Transcript Report", generate_transcript_report_prompt),
        ("References", generate_references_prompt)
    ]

    for section, prompt_generator in sections:
        try:
            prompt = prompt_generator(symbol, data)
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a highly knowledgeable financial analyst specializing in company overviews and stock analysis. Provide your analysis in a detailed, well-structured format with headings, subheadings, bullet points, and highlights. Use Markdown formatting for structure."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-8b-8192",
                temperature=0.5,
                max_tokens=2000,
                top_p=1,
            )
            content = response.choices[0].message.content
            report_sections.append({"content": content, "source": "AI"})
        except Exception as e:
            logging.error(f"Error generating {section} section: {str(e)}", exc_info=True)
            report_sections.append({"content": f"Error generating {section} section: {str(e)}", "source": "Error"})

    return report_sections


@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json
    html_content = data['html_content']

    # Configure pdfkit options for better rendering
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None
    }

    # Create the PDF from the HTML content
    pdf = pdfkit.from_string(html_content, False, options=options)

    return Response(pdf, mimetype='application/pdf', headers={"Content-Disposition": "attachment; filename=downloaded_page.pdf"})




def generate_basic_info_prompt(symbol, data):
    return f"""
    Generate a Basic Information section for {symbol} with the following format:

    ### Basic Information

    - **Ticker**: {symbol}
    - **Exchange**: {data['basic_info']['exchange']}
    - **Current Price**: ${data['basic_info']['current_price']}

    Provide a brief overview of what these metrics mean and how they compare to industry standards.

    Use the following data to fill in the placeholders:
    {json.dumps(data['basic_info'], indent=2)}
    """

def generate_executive_summary_prompt(symbol, data):
    return f"""
    Generate an Executive Summary for {symbol} with the following guidelines:
    
    ## Executive Summary

    1. Provide a concise summary of the entire report in 2-3 paragraphs
    2. Include key financial metrics, recent performance, and market position
    3. Highlight any significant recent developments or market trends affecting the company
    4. Use bullet points to list 3-5 key takeaways from the analysis

    ### Key Takeaways:
    - [Bullet point 1]
    - [Bullet point 2]
    - [Bullet point 3]
    - [Bullet point 4]
    - [Bullet point 5]

    Use the following data to inform your summary:
    {json.dumps(data, indent=2)}
    """

def generate_about_company_prompt(symbol, data):
    return f"""
    Generate an About the Company section for {symbol} with the following guidelines:

    ## About {symbol}

    1. Provide a brief company description (3-4 paragraphs)
    2. Include information about the company's history, founding, and major milestones
    3. Describe the company's main products or services
    4. Explain the company's business model and revenue streams
    5. Highlight the company's market position and competitive advantages
    6. Discuss any recent strategic initiatives or pivots

    ### Key Products/Services:
    - [Product/Service 1]
    - [Product/Service 2]
    - [Product/Service 3]

    ### Competitive Advantages:
    1. [Advantage 1]
    2. [Advantage 2]
    3. [Advantage 3]

    Use the following data to inform your description:
    {json.dumps(data, indent=2)}
    """

def generate_fundamental_analysis_prompt(symbol, data):
    return f"""
    Generate a Fundamental Analysis section for {symbol} with the following format:

    ## Fundamental Analysis

    ### Key Metrics:
    - P/E Ratio: [VALUE]
    - Quarterly Revenue: [VALUE]
    - Yearly Revenue: [VALUE]
    - Ex-Dividend Date: [DATE]
    - Yield %: [VALUE]
    - Profit/Loss per Quarter: [VALUE]
    - Profit/Loss per Year: [VALUE]
    - Market Cap: [VALUE]

    Provide a detailed analysis of these metrics, explaining what they mean and how they compare to industry averages or competitors.

    ### Revenue and Profit Trends
    [Analyze the company's revenue and profit trends over the past few years]

    ### Balance Sheet Analysis
    [Provide an overview of the company's assets, liabilities, and equity]

    ### Cash Flow Analysis
    [Discuss the company's cash flow from operations, investing, and financing activities]

    ### Competitors:
    1. [Competitor 1] (Market Cap: $X)
    2. [Competitor 2] (Market Cap: $X)
    3. [Competitor 3] (Market Cap: $X)

    [Provide a brief explanation of how {symbol} compares to its competitors in terms of market share, financial performance, and growth prospects]

    Use the following data to fill in the placeholders and provide analysis:
    {json.dumps(data['fundamental_analysis'], indent=2)}
    """

def generate_technical_analysis_prompt(symbol, data):
    return f"""
    Generate a Technical Analysis section for {symbol} with the following format:

    ## Technical Analysis

    ### Key Indicators:
    - RSI: [VALUE]
    - 50-Day Moving Average: [VALUE]
    - 200-Day Moving Average: [VALUE]
    

    Provide a detailed interpretation of these technical indicators and their implications for the stock's future performance. Include the following subsections:

    ### Trend Analysis
    [Discuss the overall trend of the stock based on moving averages and price action]

    
    ### Support and Resistance Levels
    [Identify key support and resistance levels and their significance]

    ### Volume Analysis
    [Discuss recent volume trends and their implications]

    ### Technical Outlook
    [Provide a summary of the technical outlook for the stock, including potential bullish or bearish signals]

    Use the following data to fill in the placeholders and provide analysis:
    {json.dumps(data['technical_analysis'], indent=2)}
    """

def generate_earnings_report_prompt(symbol, data):
    return f"""
    Generate a Latest Earnings Report section for {symbol} with the following format:

    ## Latest Earnings Report

    [Provide a comprehensive summary of the most recent earnings report, covering 3-5 paragraphs]

    ### Financial Highlights:
    - Revenue: [VALUE]
    - Earnings Per Share (EPS): [VALUE]
    - Net Income: [VALUE]
    - Gross Margin: [VALUE]
    - Operating Margin: [VALUE]

    ### Year-over-Year Comparison:
    - Revenue Growth: [PERCENTAGE]
    - EPS Growth: [PERCENTAGE]
    - Net Income Growth: [PERCENTAGE]

    ### Segment Performance:
    [Discuss the performance of different business segments or product lines]

    ### Key Points:
    - [Point 1]
    - [Point 2]
    - [Point 3]
    - [Point 4]
    - [Point 5]

    ### Management Commentary:
    [Summarize key statements from the management team regarding the company's performance and outlook]

    ### Q&A Summary:
    [Provide a summary of key questions and answers from the earnings call]

    ### Analyst Reactions:
    [Summarize how analysts have reacted to the earnings report]

    Use the following data to generate the content:
    {json.dumps(data['earnings_report'], indent=2)}
    """

def generate_press_release_prompt(symbol, data):
    return f"""
    Generate a Press Release Summary section for {symbol} with the following format:

    ## Press Release Summary

    [Provide a one-page summary of the latest press release, including the following elements:]

    ### Release Date: [DATE]

    ### Headline: [PRESS RELEASE HEADLINE]

    ### Key Announcements:
    1. [Announcement 1]
    2. [Announcement 2]
    3. [Announcement 3]

    ### Summary:
    [2-3 paragraphs summarizing the main points of the press release]

    ### Quotes:
    [Include any significant quotes from company executives]

    ### Impact Analysis:
    [Discuss the potential impact of this press release on the company's business, stock price, or industry position]

    ### Market Reaction:
    [If available, mention how the market has reacted to this news]

    **Source**: [Link to press release]

    Use the following data to generate the content:
    {json.dumps(data['press_release'], indent=2)}
    """

def generate_earnings_call_prompt(symbol, data):
    """Generate earnings call summary prompt"""
    if not data.get('earnings_call') or not data['earnings_call'].get('success', False):
        return f"No recent earnings call transcript available for {symbol}"
        
    transcript_data = data['earnings_call']
    analysis = transcript_data.get('analysis', {})
    
    return f"""
    ## Earnings Call Summary

    ### Call Date: {analysis.get('date', 'N/A')}

    ### Participants:
    - Company Representatives:
        {format_list(analysis.get('participants', {}).get('company_representatives', []))}
    - Investor Representatives:
        {format_list(analysis.get('participants', {}).get('analysts', []))}

    ### Key Discussion Points:
    {format_list(analysis.get('key_points', []))}

    ### Financial Highlights:
    {format_list(analysis.get('financial_highlights', []))}

    ### Strategic Initiatives:
    {format_list(analysis.get('strategic_initiatives', []))}

    ### Market and Competition:
    {format_list(analysis.get('market_competition', []))}

    ### Future Outlook:
    {format_list(analysis.get('future_outlook', []))}

    ### Q&A Highlights:
    {format_qa(analysis.get('qa_highlights', []))}

    ### Analyst Reactions:
    {format_list(analysis.get('analyst_reactions', []))}
    """
    
def format_participants(participants):
    if not participants:
        return "- No participants listed"
    
    formatted = []
    for p in participants:
        if isinstance(p, dict):
            if 'title' in p:
                formatted.append(f"- {p.get('name', 'N/A')}, {p.get('title', 'N/A')}")
            else:
                formatted.append(f"- {p.get('name', 'N/A')}, {p.get('company', 'N/A')}")
    
    return "\n".join(formatted) if formatted else "- No participants listed"

def format_list(items):
    if not items:
        return "No information available"
    
    return "\n".join(f"- {item}" for item in items)

def format_qa(qa_items):
    if not qa_items:
        return "No Q&A highlights available"
    
    formatted = []
    for qa in qa_items:
        formatted.append(f"Q: {qa.get('question', 'N/A')}\nA: {qa.get('answer', 'N/A')}\n")
    
    return "\n".join(formatted)


def generate_historical_earnings_prompt(symbol, data):
    return f"""
    Generate a Historical Earnings Performance section for {symbol} with the following format:

    ## Historical Earnings Performance

    [Provide an introduction explaining the importance of historical earnings data]

    ### Earnings Table:
    | Quarter/Year | Earnings Date | Expectations | Actual EPS | Revenue | Price 3 Days Before | Price on Earnings Date | Price After Earnings Report |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | [Q1 2024] |  |  |  |  |  |  |  |
    | [Q4 2023] |  |  |  |  |  |  |  |
    | [Q3 2023] |  |  |  |  |  |  |  |
    | [Continue for last 3 years] |  |  |  |  |  |  |  |

    ### Earnings Trend Analysis:
    [Provide a detailed analysis of the company's earnings trends over the past 3 years]

    ### Revenue Trend Analysis:
    [Analyze the company's revenue trends over the same period]

    ### Earnings Surprises:
    [Discuss any significant earnings surprises (positive or negative) and their impact on the stock price]

    ### Seasonal Patterns:
    [Identify any seasonal patterns in the company's earnings performance]

    ### Stock Price Reaction:
    [Analyze how the stock price typically reacts to earnings announcements]

    ### Comparison to Sector/Industry:
    [Compare the company's earnings performance to its sector or industry averages]

    Use the following data to fill in the table and provide analysis:
    {json.dumps(data['historical_earnings'], indent=2)}
    """

def generate_key_things_prompt(symbol, data):
    return f"""
    Generate a 5 Key Things to Know section for {symbol} with the following format:

    ## 5 Key Things to Know

    [Provide a brief introduction to this section]

    1. [Key point 1]
        - [Supporting detail]
        - [Supporting detail]
        - [Potential impact or significance]

    2. [Key point 2]
        - [Supporting detail]
        - [Supporting detail]
        - [Potential impact or significance]

    3. [Key point 3]
        - [Supporting detail]
        - [Supporting detail]
        - [Potential impact or significance]

    4. [Key point 4]
        - [Supporting detail]
        - [Supporting detail]
        - [Potential impact or significance]

    5. [Key point 5]
        - [Supporting detail]
        - [Supporting detail]
        - [Potential impact or significance]

    [Provide a concluding paragraph summarizing these key points and their overall significance for investors]

    Use the following data to generate the key points:
    {json.dumps(data, indent=2)}
    """

def generate_analyst_coverage_prompt(symbol, data):
    return f"""
    Generate an Analyst Coverage section for {symbol} with the following format:

    ## Analyst Coverage

    [Provide an introduction to this section, explaining the importance of analyst coverage]

    ### Analyst Ratings Summary:
    - Buy: [Number of Buy ratings]
    - Hold: [Number of Hold ratings]
    - Sell: [Number of Sell ratings]

    ### Consensus Price Target: $[Average Price Target]

    ### Detailed Analyst Ratings:
    1. Price Target: $X | Analyst: [Name/Company] | Rating: [Buy/Sell/Neutral/Overweight]
       - Key Points: [Brief summary of the analyst's view]
    2. Price Target: $X | Analyst: [Name/Company] | Rating: [Buy/Sell/Neutral/Overweight]
       - Key Points: [Brief summary of the analyst's view]
    3. Price Target: $X | Analyst: [Name/Company] | Rating: [Buy/Sell/Neutral/Overweight]
       - Key Points: [Brief summary of the analyst's view]
    4. Price Target: $X | Analyst: [Name/Company] | Rating: [Buy/Sell/Neutral/Overweight]
       - Key Points: [Brief summary of the analyst's view]
    5. Price Target: $X | Analyst: [Name/Company] | Rating: [Buy/Sell/Neutral/Overweight]
       - Key Points: [Brief summary of the analyst's view]
    [Continue up to 10 analysts]

    ### Recent Changes in Analyst Coverage:
    [Discuss any recent upgrades, downgrades, or significant changes in price targets]

    ### Comparing Analyst Views:
    [Provide an analysis of how analyst views differ and what might be driving these differences]

    ### Historical Accuracy:
    [If available, discuss the historical accuracy of analyst predictions for this stock]

    Use the following data to generate the analyst coverage:
    {json.dumps(data['analyst_coverage'], indent=2)}
    """

def generate_company_guidance_prompt(symbol, data):
    return f"""
    Generate a Company's Own Guidance section for {symbol} with the following format:

    ## Company's Own Guidance

    [Provide an introduction explaining the importance of company guidance]

    ### Latest Guidance:
    [One paragraph summarizing the most recent guidance provided by the company]

    ### Key Metrics:
    - Revenue Guidance: [VALUE]
    - EPS Guidance: [VALUE]
    - Other Key Metrics: [List any other metrics the company provides guidance on]

    ### Guidance Trends:
    [Discuss how the company's guidance has changed over recent quarters]

    ### Management Commentary:
    [Include relevant quotes from management about the company's future prospects]

    ### Factors Influencing Guidance:
    [Discuss key factors that the company cites as influencing their guidance]

    ### Comparison to Analyst Expectations:
    [Compare the company's guidance to current analyst expectations]

    ### Historical Accuracy:
    [If available, discuss how accurate the company's past guidance has been]

    ### Impact on Stock Price:
    [Discuss how the market typically reacts to this company's guidance]

    Use the following data to generate the guidance:
    {json.dumps(data['company_guidance'], indent=2)}
    """
#NEED TO IMPROVE RESEARCH REPORT
def generate_research_articles_prompt(symbol, data):
    return f"""
    Generate a Research Articles section for {symbol} with the following format:

    ## Research Articles

    [Provide an introduction to this section, explaining its purpose and importance]

    1. **[Article Title 1]**
        - **Source**: [URL]
        - **Date**: [Publication Date]
        - **Author**: [Author Name]
        - **Summary**: [2-3 paragraph summary of the article's main points]
        - **Key Takeaways**:
            - [Bullet point 1]
            - [Bullet point 2]
            - [Bullet point 3]

    2. **[Article Title 2]**
        - **Source**: [URL]
        - **Date**: [Publication Date]
        - **Author**: [Author Name]
        - **Summary**: [2-3 paragraph summary of the article's main points]
        - **Key Takeaways**:
            - [Bullet point 1]
            - [Bullet point 2]
            - [Bullet point 3]

    [Continue for at least 10 articles]

    ### Trends in Recent Research:
    [Provide an analysis of common themes or trends observed across recent research articles]

    ### Conflicting Views:
    [Highlight any significant disagreements or conflicting opinions found in the research]

    ### Impact on Investor Sentiment:
    [Discuss how these research articles might be influencing investor sentiment towards the stock]

    Use the following data to generate the research articles:
    {json.dumps(data['research_articles'], indent=2)}
    """

def generate_transcript_report_prompt(symbol, data):
    return f"""
    Generate a Transcript Report section for {symbol} with the following format:

    ## Transcript Report

    [Provide an introduction explaining what this transcript report covers and its significance]

    ### Event Details:
    - Type: Earnings Call
    - Date: April 25, 2023
    - Time: 5:00 PM ET
    - Duration: 2 hours and 15 minutes

    ### Participants:
    - Tim Cook, CEO
    - Luca Maestri, CFO
    - John Ternus, SVP, Hardware Technologies
    - Katy Huberty, Analyst, Morgan Stanley
    - Toni Sacconaghi, Analyst, Bernstein
    [Continue for all significant participants]

    ### Key Discussion Points:
    1. Revenue Growth
        - Summary of discussion: Apple reported a 5% year-over-year increase in revenue to $84.7 billion, driven by strong demand for its iPhone, Mac, and Services segments.
        - Relevant quotes:
          "We're thrilled with our Q2 results, which demonstrate the continued strength of our ecosystem and the success of our strategic initiatives." - Tim Cook
    2. Gross Margin
        - Summary of discussion: Apple's gross margin expanded by 100 basis points to 38.5%, driven by improved supply chain management and favorable product mix.
        - Relevant quotes:
          "Our gross margin expansion was driven by a combination of better supply chain management and a more favorable product mix." - Luca Maestri
    3. Services Segment
        - Summary of discussion: Apple's Services segment revenue grew 12% year-over-year to $14.5 billion, driven by strong demand for Apple Music, Apple TV+, and Apple Arcade.
        - Relevant quotes:
          "Our Services segment continues to be a key driver of our growth, with revenue up 12% year-over-year." - Tim Cook

    ### Financial Highlights:
    - Revenue: $84.7 billion, up 5% year-over-year
    - Gross Margin: 38.5%, up 100 basis points year-over-year
    - Operating Income: $23.6 billion, up 6% year-over-year
    - Net Income: $19.4 billion, up 7% year-over-year
    - Earnings Per Share: $1.97, up 8% year-over-year

    ### Strategic Initiatives:
    - Apple announced its plans to expand its manufacturing capabilities in the United States, with a new facility in Austin, Texas.
    - The company also reiterated its commitment to investing in emerging technologies, including artificial intelligence, machine learning, and augmented reality.

    ### Q&A Session Highlights:
    1. Question from Katy Huberty, Morgan Stanley: What's driving the strong demand for iPhones in China?
       - Response: "We're seeing strong demand for our latest iPhone models, particularly in China, where we're experiencing a resurgence in growth." - Tim Cook
    2. Question from Toni Sacconaghi, Bernstein: Can you provide more details on your plans for the Services segment?
       - Response: "We're committed to growing our Services segment through a combination of new product launches, strategic partnerships, and continued investment in our ecosystem." - Luca Maestri

    ### Key Quotes:
    - "We're thrilled with our Q2 results, which demonstrate the continued strength of our ecosystem and the success of our strategic initiatives." - Tim Cook
    - "Our gross margin expansion was driven by a combination of better supply chain management and a more favorable product mix." - Luca Maestri
    - "We're committed to growing our Services segment through a combination of new product launches, strategic partnerships, and continued investment in our ecosystem." - Luca Maestri

    ### Analyst Reactions:
    - "AAPL's Q2 results were impressive, with strong revenue growth and expanding gross margins. We maintain our Buy rating and $200 price target." - Katy Huberty, Morgan Stanley
    - "AAPL's Services segment is a key driver of growth, and we expect continued momentum in the coming quarters. We maintain our Outperform rating and $210 price target." - Toni Sacconaghi, Bernstein

    ### Conclusion:
    [Provide a brief conclusion summarizing the overall tone and key takeaways from the transcript]

    Use the following data to generate the transcript report:
    {json.dumps(data['transcript_report'], indent=2)}
    """

def generate_references_prompt(symbol, data):
    return f"""
    Generate a References section for {symbol} with the following format:

    ## References

    [Provide a brief introduction explaining the importance of these references]

    1. [Reference Name 1]
       - URL: [URL 1]
       - Description: [Brief description of the reference and its relevance]

    2. [Reference Name 2]
       - URL: [URL 2]
       - Description: [Brief description of the reference and its relevance]

    3. [Reference Name 3]
       - URL: [URL 3]
       - Description: [Brief description of the reference and its relevance]

    [Continue for all references provided]

    Use the following data to generate the references:
    {json.dumps(data['references'], indent=2)}
    """

def fetch_all_data(symbol):
    return {
        'basic_info': fetch_basic_info(symbol),
        'fundamental_analysis': fetch_fundamental_analysis(symbol),
        'technical_analysis': fetch_technical_analysis(symbol),
        'earnings_report': fetch_earnings_report(symbol),
        'press_release': fetch_press_release(symbol),
        'earnings_call': fetch_earnings_call(symbol),
        'historical_earnings': fetch_historical_earnings(symbol),
        'analyst_coverage': fetch_analyst_coverage(symbol),
        'company_guidance': fetch_company_guidance(symbol),
        'research_articles': fetch_research_articles(symbol),
        'transcript_report': fetch_transcript_report(symbol),
        'references': fetch_references(symbol)
    }

def fetch_basic_info(symbol):
    # Use yfinance to download stock data
    stock = yf.Ticker(symbol)
    stock_info = stock.info
    
    # Extract relevant information and fall back to previous close if current price is unavailable
    return {
        "symbol": stock_info.get("symbol", "N/A"),
        "exchange": stock_info.get("exchange", "N/A"),
        "current_price": stock_info.get("regularMarketPrice") or stock_info.get("previousClose", "N/A")
    }
    

def fetch_fundamental_analysis(symbol):
    # Fetch data from yfinance
    stock = yf.Ticker(symbol)
    info = stock.info

    # Format large numbers for readability
    def format_large_number(value):
        if value == "N/A" or value is None:
            return "N/A"
        elif value >= 1_000_000_000_000:  # Trillions
            return f"{value / 1_000_000_000_000:.2f} T"
        elif value >= 1_000_000_000:  # Billions
            return f"{value / 1_000_000_000:.2f} B"
        elif value >= 1_000_000:  # Millions
            return f"{value / 1_000_000:.2f} M"
        return str(value)

    # Return consolidated data with formatted values
    return {
        "pe_ratio": info.get("trailingPE", "N/A"),
        "yearly_revenue": format_large_number(info.get("totalRevenue", "N/A")),
        "ex_dividend_date": info.get("exDividendDate", "N/A"),
        "yield": f"{info.get('dividendYield', 'N/A') * 100:.2f}%" if info.get("dividendYield") else "N/A",
        "profit_loss_year": format_large_number(info.get("netIncomeToCommon", "N/A")),
        "market_cap": format_large_number(info.get("marketCap", "N/A")),
        "competitors": [{"name": comp.get("name", "N/A"), "title": comp.get("title", "N/A")}
                        for comp in info.get("companyOfficers", []) if "name" in comp and "title" in comp]
    }


def fetch_technical_analysis(symbol):
    # Initialize default values
    sma_50 = "N/A"
    sma_200 = "N/A"
    macd = "N/A"
    rsi = "N/A"
    

    # Fetch 50-day SMA
    url_sma_50 = f"{BASE_URL}?function=SMA&symbol={symbol}&interval=daily&time_period=50&series_type=close&apikey={API_KEY}"
    response_sma_50 = requests.get(url_sma_50)
    if response_sma_50.status_code == 200:
        data = response_sma_50.json().get("Technical Analysis: SMA", {})
        latest_date = max(data.keys()) if data else None
        sma_50 = data.get(latest_date, {}).get("SMA", "N/A")

    # Fetch 200-day SMA
    url_sma_200 = f"{BASE_URL}?function=SMA&symbol={symbol}&interval=daily&time_period=200&series_type=close&apikey={API_KEY}"
    response_sma_200 = requests.get(url_sma_200)
    if response_sma_200.status_code == 200:
        data = response_sma_200.json().get("Technical Analysis: SMA", {})
        latest_date = max(data.keys()) if data else None
        sma_200 = data.get(latest_date, {}).get("SMA", "N/A")


    # Fetch RSI (14-day)
    url_rsi = f"{BASE_URL}?function=RSI&symbol={symbol}&interval=daily&time_period=14&series_type=close&apikey={API_KEY}"
    response_rsi = requests.get(url_rsi)
    if response_rsi.status_code == 200:
        data = response_rsi.json().get("Technical Analysis: RSI", {})
        latest_date = max(data.keys()) if data else None
        rsi = data.get(latest_date, {}).get("RSI", "N/A")


    # Final return as specified
    return {
        "rsi": rsi,
        "sma_50": sma_50,
        "sma_200": sma_200
    }

def fetch_earnings_report(symbol):
    url = f"{BASE_URL}?function=EARNINGS&symbol={symbol}&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        quarterly_earnings = data.get("quarterlyEarnings", [])
        if quarterly_earnings:
            latest_quarter = quarterly_earnings[0]
            return {
                "summary": f"Latest quarterly earnings for {symbol}",
                "key_points": [
                    f"EPS: {latest_quarter.get('reportedEPS', 'N/A')}",
                    f"Estimated EPS: {latest_quarter.get('estimatedEPS', 'N/A')}",
                    f"Surprise: {latest_quarter.get('surprise', 'N/A')}",
                    f"Surprise Percentage: {latest_quarter.get('surprisePercentage', 'N/A')}%"
                ],
                "qa_summary": "Q&A summary not available from this data source"
            }
    return {"error": "Failed to fetch earnings report"}

def fetch_press_release(symbol):
    # This would typically require a news API or web scraping
    return {"error": "Press release fetching not implemented"}

def fetch_earnings_call(symbol):
    """Fetch earnings call transcript data"""
    BASE_URL = "https://discountingcashflows.com/api/transcript/"
    
    def get_recent_quarters():
        current_date = datetime.now()
        current_quarter = (current_date.month - 1) // 3 + 1
        current_year = current_date.year
        
        quarters = []
        for year in range(current_year, current_year - 1, -1):
            for q in range(4, 0, -1):
                quarters.append((f"Q{q}", str(year)))
        return quarters

    quarters_to_try = get_recent_quarters()
    
    for quarter, year in quarters_to_try:
        params = {
            'ticker': symbol.upper(),
            'quarter': quarter,
            'year': year,
            'key': DCF_API_KEY  # Using the global DCF_API_KEY
        }
        
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                transcript_data = data[0]
                
                # Process the transcript content
                content = transcript_data['content']
                formatted_date = datetime.strptime(
                    transcript_data['date'],
                    '%Y-%m-%d %H:%M:%S'
                ).strftime('%B %d, %Y')
                
                # Extract Q&A section
                qa_start = content.lower().find("question-and-answer")
                qa_section = content[qa_start:] if qa_start != -1 else ""
                
                # Analyze transcript with AI using the global GROQ_API_KEY
                analysis = analyze_transcript_content(content)
                
                return {
                    'date': formatted_date,
                    'symbol': transcript_data['symbol'],
                    'quarter': f"Q{transcript_data['quarter']}",
                    'year': transcript_data['year'],
                    'content': content,
                    'qa_section': qa_section,
                    'analysis': analysis,
                    'success': True
                }
                
        except Exception as e:
            logging.error(f"Error fetching transcript for {symbol}: {str(e)}")
            continue
            
    return {"error": "No recent transcript found", "success": False}
def analyze_transcript_content(content: str) -> dict:
    """Analyze transcript content using Groq"""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))  # No need to pass API key as it's already set in environment
    
    prompt = f"""
    Analyze this earnings call transcript and extract the following information:
    1. Important questions and answers between analysts and management
    2. Key financial metrics and numbers mentioned
    3. Future outlook and guidance statements
    4. Major announcements or strategic changes
    5. Key participants (both company representatives and analysts)
    
    Format as JSON:
    {{
        "participants": {{
            "company_representatives": [
                {{"name": "...", "title": "..."}}
            ],
            "analysts": [
                {{"name": "...", "company": "..."}}
            ]
        }},
        "key_discussion_points": [
            "..."
        ],
        "financial_highlights": [
            "..."
        ],
        "strategic_initiatives": [
            "..."
        ],
        "market_competition": [
            "..."
        ],
        "future_outlook": [
            "..."
        ],
        "qa_highlights": [
            {{"question": "...", "answer": "..."}}
        ],
        "analyst_reactions": [
            "..."
        ]
    }}
    
    Transcript:
    {content}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a financial analyst expert in analyzing earnings call transcripts."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.1,
            max_tokens=2000,
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logging.error(f"Error analyzing transcript: {str(e)}")
        return {}
        
def fetch_historical_earnings(symbol):
    try:
        # Fetch earnings data from Alpha Vantage
        earnings_url = f"{BASE_URL}?function=EARNINGS&symbol={symbol}&apikey={API_KEY}"
        earnings_response = requests.get(earnings_url)

        if earnings_response.status_code == 200:
            earnings_data = earnings_response.json()
            quarterly_earnings = earnings_data.get("quarterlyEarnings", [])
            
            results = []
            for earning in quarterly_earnings[:12]:  # Fetch the last 12 quarters
                fiscal_date = earning.get("fiscalDateEnding", "N/A")
                
                # Fetch earnings date (placeholder, using fiscal date)
                earnings_date = fiscal_date

                # Fetch revenue from Alpha Vantage API
                revenue_url = f"{BASE_URL}?function=INCOME_STATEMENT&symbol={symbol}&apikey={API_KEY}"
                revenue_response = requests.get(revenue_url)
                revenue = "N/A"
                if revenue_response.status_code == 200:
                    revenue_data = revenue_response.json()
                    for report in revenue_data.get("quarterlyReports", []):
                        if report.get("fiscalDateEnding") == fiscal_date:
                            revenue = report.get("totalRevenue", "N/A")
                            break

                # Fetch price before, on, and after earnings date from EOD Historical Data API
                price_before, price_on_date, price_after = "N/A", "N/A", "N/A"
                try:
                    price_url = f"{EOD_API_URL}/eod/{symbol}?from={fiscal_date}&to={fiscal_date}&api_token={EOD_API_TOKEN}"
                    price_response = requests.get(price_url)
                    if price_response.status_code == 200:
                        price_data = price_response.json()
                        sorted_dates = sorted(price_data.keys())

                        # Fetch price on the earnings date
                        if fiscal_date in price_data:
                            price_on_date = price_data[fiscal_date].get("close", "N/A")
                        
                        # Fetch price before the earnings date
                        for prev_date in sorted_dates:
                            if prev_date < fiscal_date:
                                price_before = price_data[prev_date].get("close", "N/A")
                                break
                        
                        # Fetch price after the earnings date
                        for next_date in sorted_dates:
                            if next_date > fiscal_date:
                                price_after = price_data[next_date].get("close", "N/A")
                                break
                except Exception as e:
                    logging.error(f"Error fetching price data for {symbol}: {str(e)}")

                # Append the data for each quarter
                results.append({
                    "quarter": fiscal_date,
                    "earnings_date": earnings_date,
                    "expectations": earning.get("estimatedEPS", "N/A"),
                    "actual_eps": earning.get("reportedEPS", "N/A"),
                    "revenue": revenue,
                    "price_before": price_before,
                    "price_on_date": price_on_date,
                    "price_after": price_after
                })

            return results

        else:
            logging.error(f"Failed to fetch earnings data for {symbol}: {earnings_response.status_code}")
            return {"error": f"Failed to fetch earnings data for {symbol}"}

    except Exception as e:
        logging.exception("An error occurred while fetching historical earnings data.")
        return {"error": str(e)}
def fetch_analyst_coverage(symbol):
    stock = yf.Ticker(symbol)
    recommendations = stock.recommendations
    if not recommendations.empty:
        latest_recommendations = recommendations.iloc[-10:]  # Get the last 10 recommendations
        return [
            {
                "price_target": "N/A",  # Not provided by yfinance
                "analyst": row.get('Firm', 'Unknown Firm') if 'Firm' in recommendations.columns else 'Unknown Firm',
                "rating": row.get('To Grade', 'N/A') if 'To Grade' in recommendations.columns else 'N/A'
            }
            for _, row in latest_recommendations.iterrows()
        ]
    return {"error": "Failed to fetch analyst coverage"}

def fetch_company_guidance(symbol):
    # This would typically require a specialized API or web scraping
    return {"error": "Company guidance fetching not implemented"}

def fetch_research_articles(symbol):
    # This would typically require a news API or web scraping
    return {"error": "Research articles fetching not implemented"}



def fetch_references(symbol):
    return [
        {"name": "Alpha Vantage", "url": "https://www.alphavantage.co/"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/"},
        {"name": "yfinance Library", "url": "https://pypi.org/project/yfinance/"},
        {"name": "Morning Star", "url": "https://www.morningstar.in/default.aspx"},
        {"name": "Barron's", "url": "https://www.barrons.com/"},
        {"name": "discounting cash flows", "url": "https://discountingcashflows.com/"},
        {"name": "seeking alpha", "url": "https://seekingalpha.com/"}
    ]

if __name__ == '__main__':
    app.run(debug=True)