import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response
import yfinance as yf
from rich.console import Console
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta
from semanticscholar import SemanticScholar
from rich.table import Table
from urllib.parse import quote
import pdfkit
import requests
import datetime as dt
import json
from typing import Any, Dict, List, Union
from groq import Groq
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Frame, PageTemplate
from reportlab.platypus import Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageTemplate, Frame, Spacer, Table, TableStyle
from bs4 import BeautifulSoup
import re
from html.parser import HTMLParser
import traceback
import sys
from scholarly import scholarly


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# API keys
API_KEY = os.getenv('API_KEY')
BASE_URL = os.getenv('BASE_URL')
EOD_API_TOKEN = os.getenv('EOD_API_TOKEN')
EOD_API_URL = os.getenv('EOD_API_URL')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
DCF_API_KEY = os.getenv('DCF_API_KEY')
FMP_API_KEY = os.getenv('FMP_API_KEY')

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

def get_company_domains(ticker: str) -> List[str]:
    """Retrieves relevant search terms for a company using Groq."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY")) # Use environment variable
    prompt = f"""For the company with ticker {ticker}, list exactly 10 most important technical research areas and technologies.
    Provide them as a simple comma-separated list without explanations or additional text.
    Example format: "artificial intelligence, machine learning, computer vision"
    Keep terms concise and focused on technical aspects."""

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192"
        )
        response = chat_completion.choices[0].message.content.strip()
        terms = [term.strip() for term in response.split(',') if term.strip() and len(term.strip()) < 50][:10]
        console.print("[blue]Search terms identified:[/blue]")
        for i, term in enumerate(terms, 1):
            console.print(f"[blue]{i}. {term}[/blue]")
        return terms
    except Exception as e:
        console.print(f"[red]Error getting company domains: {str(e)}[/red]")
        return [ticker]  # Default to ticker if Groq fails



def get_research_papers(ticker: str, limit: int = 10) -> List[Dict]:
    """Fetches research papers from arXiv based on search terms."""
    base_url = "http://export.arxiv.org/api/query"
    search_terms = get_company_domains(ticker)
    search_query = " OR ".join(f'(ti:"{term}" OR abs:"{term}")' for term in search_terms)

    params = {
        "search_query": search_query,
        "max_results": limit * 5,  # Fetch more to filter for relevance
        "sortBy": "relevance",        # Sort by relevance
        "sortOrder": "descending"
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        papers = []

        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text.strip()
            abstract = entry.find('atom:summary', namespace).text.strip()
            is_relevant = any(term.lower() in title.lower() or term.lower() in abstract.lower() for term in search_terms)

            if is_relevant:  # Only append relevant papers
                authors = [author.find('atom:name', namespace).text for author in entry.findall('atom:author', namespace)]
                paper = {
                    "title": title,
                    "authors": authors,
                    "published": entry.find('atom:published', namespace).text,
                    "url": entry.find('atom:id', namespace).text,
                    "summary": abstract[:200] + "..." if len(abstract) > 200 else abstract
                }
                papers.append(paper)
                if len(papers) == limit:
                   break # Stop after finding enough relevant ones
        return papers

    except Exception as e:  # Catch broader exceptions
        console.print(f"[red]Error fetching papers: {str(e)}[/red]")
        return []



def display_papers(papers: List[Dict]) -> None:
    """Displays research papers in a rich table format with clickable links."""
    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", width=150) # Wider table
    table.add_column("Title", style="cyan", no_wrap=True)
    table.add_column("Authors", style="green")
    table.add_column("Published", style="yellow", justify="center")
    table.add_column("Link", style="blue") # Add link column
    table.add_column("Summary", style="white")  # Added Summary column


    for paper in papers:
        title_link = f"[link={paper['url']}]{paper['title']}[/link]"
        table.add_row(
            title_link,
            ", ".join(paper["authors"]),
            paper["published"].split("T")[0],
            paper["url"], # Direct link, not just title
            paper["summary"] # Include the summary
        )
    console.print(table)
    
def extract_key_takeaways(abstract: str) -> List[str]:
    """Extracts key takeaways from an abstract (placeholder - needs NLP)."""
    if not abstract:
        return ["No abstract available."]
    keywords = [word for word in abstract.split() if word.istitle() and len(word) > 3]
    return keywords[:2] or ["No specific takeaways found."]
    
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['GET'])
def analyze_stock():
    try:
        symbol = request.args.get('symbol', '').upper()
        if not symbol:
            return jsonify({'error': 'No symbol provided'}), 400

        data = fetch_all_data(symbol, FMP_API_KEY)

        # Fetch research articles separately
        research_articles = fetch_research_articles(symbol)

        # Generate other report sections
        report_sections = generate_report_sections(symbol, data)

        # Append research articles as a separate section
        report_sections.append({"content": research_articles, "source": "Research Papers"})


        return jsonify({'report': report_sections})  # Return all sections

    except Exception as e:
        error_type, error_value, error_traceback = sys.exc_info()
        error_details = {
            'error_type': str(error_type),
            'error_message': str(error_value),
            'traceback': traceback.format_exc()
        }
        logging.error(f"Error in analyze_stock: {error_details}")
        return jsonify(error_details), 500

console = Console()
sch = SemanticScholar(timeout=10)

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
        ("Historical Earnings Performance", generate_historical_earnings_prompt),
        ("5 Key Things to Know", generate_key_things_prompt),
        ("Company's Own Guidance", generate_company_guidance_prompt),
        ("Research Articles", generate_research_articles_prompt),
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



class CustomPDFTemplate(BaseDocTemplate):
    def __init__(self, filename, company_name, **kwargs):
        super().__init__(filename, **kwargs)
        self.company_name = company_name
        self.pagesize = A4

    def handle_pageBegin(self):
        self._handle_pageBegin()

    def build_header_footer(self, canvas, doc):
        canvas.saveState()
        page_width = self.pagesize[0]
        page_height = self.pagesize[1]

        # Header configuration
        header_height = 30
        header_top = page_height - 50
        header_bottom = header_top - header_height
        main_color = colors.HexColor('#0056b3')

        # Draw header rectangle
        canvas.setFillColor(main_color)
        canvas.setStrokeColor(colors.white)
        canvas.setLineWidth(0.4)
        canvas.rect(doc.leftMargin, header_bottom,
                   page_width - (doc.leftMargin + doc.rightMargin),
                   header_height, fill=1)

        # Header text
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 14)
        header_center_y = header_bottom + (header_height / 2) - 2
        canvas.drawCentredString(page_width/2, header_center_y,
                               "REPORT FROM MYAIREPORT.COM")

        # Footer
        footer_y = doc.bottomMargin - 30

        # Footer line
        canvas.setStrokeColor(main_color)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, footer_y + 15,
                   page_width - doc.rightMargin, footer_y + 15)

        # Company name
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(main_color)
        canvas.drawString(doc.leftMargin, footer_y, self.company_name)

        # Page number
        page_text = f"Page {doc.page}"
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawRightString(page_width - doc.rightMargin, footer_y, page_text)

        # Date
        current_date = datetime.now().strftime("%B %d, %Y")
        canvas.setFont('Helvetica', 9)
        canvas.drawCentredString(page_width/2, footer_y, current_date)

        canvas.restoreState()

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.json
        html_content = data.get('html_content', '')
        company = data.get('company', 'Company')

        buffer = BytesIO()

        # Create document
        doc = CustomPDFTemplate(
            buffer,
            company_name=company,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=60,
            bottomMargin=60
        )

        # Content frame
        content_frame = Frame(
            doc.leftMargin,
            doc.bottomMargin + 40,
            doc.width,
            doc.height - 120,
            id='normal'
        )

        def page_template_func(canvas, doc):
            doc.build_header_footer(canvas, doc)

        template = PageTemplate(
            id='main',
            frames=[content_frame],
            onPage=page_template_func
        )

        doc.addPageTemplates([template])

        # Styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#0056b3'),
            alignment=TA_LEFT
        ))
        styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=10,
            textColor=colors.HexColor('#0056b3'),
            alignment=TA_LEFT
        ))
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_LEFT
        ))
        styles.add(ParagraphStyle(
            name='URL',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#0066cc'),
            alignment=TA_LEFT,
            underline=True  # Adding underline for URLs
        ))
        
        styles.add(ParagraphStyle(
            name='InlineURL',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#0066cc'),
            underline=True
        ))

        story = []
        story.append(Paragraph(f"Stock Analysis Report: {company}", styles['CustomTitle']))
        story.append(Spacer(1, 12))

        def process_text(text):
            url_pattern = r'(https?://\S+)'
            parts = re.split(url_pattern, text)
            result = []
            for part in parts:
                if re.match(url_pattern, part):
                    result.append(Paragraph(part, styles['URL']))
                else:
                    result.append(part)
            return ''.join(str(p) if isinstance(p, str) else p.text for p in result)

        soup = BeautifulSoup(html_content, 'html.parser')

        for section in soup.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'table']):
            if section.name == 'h1':
                story.append(Spacer(1, 20))
                story.append(Paragraph(section.text, styles['CustomTitle']))
            elif section.name == 'h2':
                story.append(Spacer(1, 20))
                story.append(Paragraph(section.text, styles['CustomHeading']))
            elif section.name == 'h3':
                story.append(Paragraph(section.text, styles['Heading3']))
            elif section.name == 'p':
                processed_text = process_text(section.text)
                story.append(Paragraph(processed_text, styles['CustomBody']))
            elif section.name in ['ul', 'ol']:
                for item in section.find_all('li'):
                    processed_text = process_text(item.text)
                    story.append(Paragraph(f"• {processed_text}", styles['CustomBody']))
            elif section.name == 'table':
                data = []
                for row in section.find_all('tr'):
                    data.append([cell.text.strip() for cell in row.find_all(['th', 'td'])])

                if data:
                    col_widths = [doc.width/len(data[0])] * len(data[0])
                    table = Table(data, colWidths=col_widths, splitByRow=True)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0056b3')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('WORDWRAP', (0, 0), (-1, -1), True),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))

        # Build document
        doc.build(story)

        pdf = buffer.getvalue()
        buffer.close()

        return Response(
            pdf,
            mimetype='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename={company}_Report.pdf",
                "Content-Type": "application/pdf"
            }
        )

    except Exception as e:
        app.logger.error(f"PDF generation error: {str(e)}")
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500



def generate_basic_info_prompt(symbol, data):
    return f"""
    Generate a Basic Information section for {symbol} with the following format:

    ### Basic Information

    - **Ticker**: {symbol}
    - **Exchange**: {data['basic_info']['exchange']}
    - **Current Price**: ${data['basic_info']['current_price']}

    Provide a brief overview of what these metrics mean and how they compare to industry standards.(but with actual data, don't discuss about market capitalization here)
    
    Use the following data to fill in the placeholders:
    {json.dumps(data['basic_info'], indent=2)}
    """

def generate_executive_summary_prompt(symbol, data):
    return f"""
    Generate an Executive Summary for {symbol} with the following guidelines:

    ## Executive Summary
    ### Key Metrics:
    - P/E Ratio: {data.get('pe_ratio', 'N/A')}
    - Yearly Revenue: {data.get('yearly_revenue', 'N/A')}
    - Yield %: {data.get('yield', 'N/A')}
    - Profit/Loss per Year: {data.get('profit_loss_year', 'N/A')}
    - Market Cap: {data.get('market_cap', 'N/A')}

    [don't need to print key matrics direcctly you can use to generate summary]
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
    - P/E Ratio: {data.get('pe_ratio', 'N/A')}
    - Yearly Revenue: {data.get('yearly_revenue', 'N/A')}
    - Ex-Dividend Date: {data.get('ex_dividend_date', 'N/A')}
    - Yield %: {data.get('yield', 'N/A')}
    - Profit/Loss per Year: {data.get('profit_loss_year', 'N/A')}
    - Market Cap: {data.get('market_cap', 'N/A')}
    - Team: {', '.join([f"{comp['name']} ({comp['title']})" for comp in data.get('team', [])])}


    Provide a detailed analysis of these metrics, explaining what they mean and how they compare to industry averages or competitors.

    ### Revenue and Profit Trends
    [Analyze the company's revenue and profit trends over the past few years]

    ### Balance Sheet Analysis
    [Provide an overview of the company's assets, liabilities, and equity]

    ### Cash Flow Analysis
    [Discuss the company's cash flow from operations, investing, and financing activities]

    ### Competitors:
    1. [Competitor 1]
    2. [Competitor 2]
    3. [Competitor 3]

    [Provide a brief explanation of how {symbol} compares to its competitors in terms of market share, financial performance, and growth prospects]

    Use the following data to fill in the placeholders and provide analysis:
    {json.dumps(data['fundamental_analysis'], indent=2)}
    """

def generate_technical_analysis_prompt(symbol, all_data):
    technical_data = all_data.get('technical_analysis', {})

    rsi = technical_data.get("rsi", "N/A")
    sma_50 = technical_data.get("sma_50", "N/A")
    sma_200 = technical_data.get("sma_200", "N/A")

    return f"""
    Generate a Technical Analysis section for {symbol} with the following guidelines:

    ## Technical Analysis

    RSI: {rsi}
    50-Day Moving Average: {sma_50}
    200-Day Moving Average: {sma_200}
    [MUST print actual RSI, 50-DAY Moving Average, 200-day Moving Average]
    1. Provide a detailed interpretation of these technical indicators and their implications for the stock's future performance. 
    2. Structure your analysis using the following subsections:

    ### Trend Analysis
    [Discuss the overall trend of the stock based on moving averages and price action, explicitly mentioning the RSI, 50-Day MA, and 200-Day MA values.]

    ### Support and Resistance Levels
    [Identify key support and resistance levels and their significance.]

    ### Volume Analysis
    [Discuss recent volume trends and their implications.]

    ### Technical Outlook
    [Provide a summary of the technical outlook for the stock, including potential bullish or bearish signals.]

    Use the following additional data if needed for context:
    {json.dumps(technical_data, indent=2)} 
    """


def generate_earnings_report_prompt(symbol, data):
    if 'earnings_report' not in data or isinstance(data['earnings_report'], dict) and 'error' in data['earnings_report']:
        return f"Unable to generate earnings report for {symbol}: No data available"
    
    earnings_data = data['earnings_report']
    
    return f"""
    ## Latest Earnings Report Analysis for {symbol}

    ### Financial Performance:
    - Revenue: {earnings_data.get('Revenue', 'N/A')}
    - Earnings Per Share (EPS): {earnings_data.get('EPS', 'N/A')}
    - Net Income: {earnings_data.get('Net_Income', 'N/A')}
    - Gross Margin: {earnings_data.get('Gross_Margin', 'N/A')}
    - Operating Expenses: {earnings_data.get('Operating_Expenses', 'N/A')}

    ### Year-over-Year Growth:
    - Revenue Growth: {earnings_data.get('Revenue_Growth', 'N/A')}
    - EPS Growth: {earnings_data.get('EPS_Growth', 'N/A')}
    - Net Income Growth: {earnings_data.get('Net_Income_Growth', 'N/A')}

    ### Operational Metrics:
    - Cost of Revenue: {earnings_data.get('Cost_of_Revenue', 'N/A')}
    - Gross Profit: {earnings_data.get('Gross_Profit', 'N/A')}
    - Operating Income: {earnings_data.get('Operating_Income', 'N/A')}
    
    print all this data and add this also:

    Please provide a comprehensive analysis of these financial results, including:
    1. Overall financial health and performance
    2. Key trends in revenue and profitability
    3. Notable changes in operational metrics
    4. Comparison with industry standards
    5. Potential areas of concern or opportunity

    Use the following data for the analysis:
    {json.dumps(earnings_data, indent=2)}
    """



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
    """Generates the prompt for the Research Articles section."""
    try:
        # Initialize scholarly
        from scholarly import scholarly
        
        # Get company domains for better search results
        search_query = get_company_domains(symbol)
        papers = []
        
        for domain in search_query:
            search_query = scholarly.search_pubs(f"{symbol} {domain}")
            try:
                for i in range(2):  # Get 2 papers per domain
                    paper = next(search_query)
                    
                    # Extract available information
                    title = paper.get('bib', {}).get('title', 'No title available')
                    year = paper.get('bib', {}).get('year', 'N/A')
                    url = f"https://scholar.google.com/scholar?cluster={paper.get('cluster_id', '')}"
                    authors = ', '.join(paper.get('bib', {}).get('author', ['No authors available']))
                    abstract = paper.get('bib', {}).get('abstract', '')
                    
                    # Get summary and key findings using Groq
                    summary, key_findings = get_summary_and_findings(title, abstract)
                    
                    papers.append({
                        'title': title,
                        'authors': authors,
                        'year': year,
                        'url': url,
                        'summary': summary,
                        'key_findings': key_findings
                    })
                    
            except StopIteration:
                continue
                
            time.sleep(2)  # Add delay to avoid rate limits

        # Format the prompt with markdown and paper details
        prompt = f"""
        ## Research Articles about {symbol}

        Here are some recent research articles related to {symbol}'s technology and business domains:
        """
        
        for i, paper in enumerate(papers, 1):
            prompt += f"""
            ### {i}. {paper['title']} ({paper['year']})
            
            **Authors:** {paper['authors']}
            
            **Summary:** {paper['summary']}
            
            **Key Findings:**
            {chr(10).join([f"- {finding}" for finding in paper['key_findings']])}
            
            **Source:** [View Paper]({paper['url']})
            
            ---
            """
            
        return prompt
        
    except Exception as e:
        return f"Error generating research articles section: {str(e)}"    


def get_summary_and_findings(title, abstract):
    """Gets summary and key findings using Groq."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    prompt = f"""
    Based on the following research paper title and abstract, provide:
    1. A concise summary (2-3 sentences)
    2. Three key findings or main points
    
    Title: {title}
    Abstract: {abstract}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        # Split content into summary and findings
        parts = content.split('\n\n')
        summary = parts[0].strip()
        findings = [f.strip('- ') for f in parts[1].split('\n') if f.strip()]
        
        return summary, findings[:3]
    except Exception as e:
        return ("Error generating summary", ["Error generating findings"])

def get_company_domains(symbol):
    """Gets relevant technical domains for the company."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    prompt = f"""For the company with ticker {symbol}, list exactly 5 most important technical research areas and technologies.
    Provide them as a simple comma-separated list without explanations or additional text.
    Example format: "artificial intelligence, machine learning, computer vision"
    Keep terms concise and focused on technical aspects."""
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.3
        )
        
        domains = response.choices[0].message.content.strip().split(',')
        return [d.strip() for d in domains if d.strip()]
    except Exception as e:
        return [symbol]
        
        
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

def fetch_all_data(symbol, fmp_api_key):
    return {
        'basic_info': fetch_basic_info(symbol),
        'fundamental_analysis': fetch_fundamental_analysis(symbol),
        'technical_analysis': fetch_technical_analysis(symbol),
        'earnings_report': fetch_earnings_report(symbol, fmp_api_key),
        'press_release': fetch_press_release(symbol),
        'historical_earnings': fetch_historical_earnings(symbol),
        'company_guidance': fetch_company_guidance(symbol),
        'research_articles': fetch_research_articles(symbol),
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
        "yield": f"{info.get('dividendYield', 'N/A') * 100:.2f}%" if info.get("dividendYield") else "N/A",
        "profit_loss_year": format_large_number(info.get("netIncomeToCommon", "N/A")),
        "market_cap": format_large_number(info.get("marketCap", "N/A")),
        "team": [{"name": comp.get("name", "N/A"), "title": comp.get("title", "N/A")}
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
    def format_number(number):
        if number is None:
            return "N/A"
        if abs(number) >= 1_000_000_000:
            return f"${number/1_000_000_000:.2f}B"
        elif abs(number) >= 1_000_000:
            return f"${number/1_000_000:.2f}M"
        return f"${number:,.2f}"
        
    

def format_number(number):
    if number is None:
        return "N/A"
    if abs(number) >= 1_000_000_000:
        return f"${number/1_000_000_000:.2f}B"
    elif abs(number) >= 1_000_000:
        return f"${number/1_000_000:.2f}M"
    return f"${number:,.2f}"

def format_ratio(ratio):
    if ratio is None:
        return "N/A"
    return f"{ratio*100:.2f}%"

def calculate_growth(current, previous):
    if current is None or previous is None or previous == 0:
        return "N/A"
    growth = (current - previous) / abs(previous)
    return f"{growth*100:.2f}%"
    
def fetch_earnings_report(symbol, fmp_api_key):
    """Fetch financial data from FMP API"""
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}"
    params = {
        "period": "annual",
        "apikey": fmp_api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {"error": "No data found for this symbol"}
        
        current_data = data[0]
        previous_data = data[1] if len(data) > 1 else None
        
        # Format the data
        report_data = {
            "Revenue": format_number(current_data.get('revenue')),
            "EPS": f"${current_data.get('eps', 0):.2f}",
            "Net_Income": format_number(current_data.get('netIncome')),
            "Gross_Margin": format_ratio(current_data.get('grossProfitRatio')),
            "Operating_Expenses": format_number(current_data.get('operatingExpenses')),
            "Cost_of_Revenue": format_number(current_data.get('costOfRevenue')),
            "Gross_Profit": format_number(current_data.get('grossProfit')),
            "Operating_Income": format_number(current_data.get('operatingIncome')),
            
            # Year-over-Year Growth
            "Revenue_Growth": calculate_growth(
                current_data.get('revenue'),
                previous_data.get('revenue') if previous_data else None
            ),
            "EPS_Growth": calculate_growth(
                current_data.get('eps'),
                previous_data.get('eps') if previous_data else None
            ),
            "Net_Income_Growth": calculate_growth(
                current_data.get('netIncome'),
                previous_data.get('netIncome') if previous_data else None
            )
        }
        
        return report_data
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch earnings report: {str(e)}"}
    
    
def fetch_press_release(symbol):
    # This would typically require a news API or web scraping
    return {"error": "Press release fetching not implemented"}


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


def fetch_company_guidance(symbol):
    # This would typically require a specialized API or web scraping
    return {"error": "Company guidance fetching not implemented"}

def fetch_research_articles(symbol, limit=10):
    """Fetches research articles using Groq and Scholarly, prioritizing relevance."""
    try:
        papers = []
        search_terms = get_company_domains(symbol)

        # 1. Initial Search with Scholarly (broader scope)
        initial_papers = []
        for term in search_terms:
            search_query = scholarly.search_pubs(f"{symbol} {term}")
            for _ in range(limit * 2 // len(search_terms)):  # Fetch more initially
                try:
                    pub = next(search_query)
                    initial_papers.append(pub)
                except StopIteration:
                    break
                time.sleep(2)

        # 2. Filter and Summarize with Groq (ensure relevance)
        for pub in initial_papers:
            title = pub.bib.get('title', '')
            abstract = pub.bib.get('abstract', '')

            # Use Groq to check relevance and generate summary/findings
            is_relevant, summary, key_findings = check_relevance_and_summarize(symbol, title, abstract)

            if is_relevant and len(papers) < limit:  # Add only relevant papers up to the limit
                papers.append({
                    "title": title,
                    "source": f"https://scholar.google.com/scholar?cluster={pub.get('cluster_id', '')}",
                    "date": pub.bib.get('year', 'N/A'),
                    "author": ", ".join(pub.bib.get('author', [])),
                    "summary": summary,
                    "key_takeaways": key_findings
                })


        return papers

    except Exception as e:
        console.print(f"[red]Error fetching research articles: {e}[/red]")
        return []

def check_relevance_and_summarize(symbol, title, abstract):
    """Uses Groq to check relevance and generate summary/findings."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    prompt = f"""
    Given the following research paper title and abstract for company ticker {symbol}, determine if the paper is relevant to the company's business, technology, or industry.
    If relevant, provide:
    1. A concise summary (2-3 sentences)
    2. Three key findings or main points

    Title: {title}
    Abstract: {abstract}

    If not relevant, simply return "Not Relevant".
    """

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",  # Or a suitable model
            temperature=0.3,
            max_tokens=500
        )

        content = response.choices[0].message.content
        if "Not Relevant" in content:
            return False, "", []  # Not relevant

        parts = content.split('\n\n')
        summary = parts[0].strip()
        findings = [f.strip('- ') for f in parts[1].split('\n') if f.strip()]
        return True, summary, findings[:3]

    except Exception as e:
        console.print(f"[yellow]Error in Groq relevance check: {e}[/yellow]")
        return False, "Error generating summary", ["Error generating findings"]

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