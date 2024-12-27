import os
import logging
from flask import Flask, render_template, request, jsonify, Response
import yfinance as yf
from rich.console import Console
import time
from datetime import datetime, timedelta
from rich.table import Table
from urllib.parse import quote
import pdfkit
import requests
import datetime as dt
import json
from typing import Any, Dict, List, Union
from groq import Groq
from io import BytesIO
from typing import Any, Dict, List, Union, Optional,Tuple # Import Optional here
import logging
import json
import requests
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from groq import Groq
from bs4 import BeautifulSoup
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
import logging
import time
import requests
from urllib.parse import quote
from datetime import datetime
from typing import List, Dict

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)  # Change DEBUG to INFO
logging.getLogger('watchdog').setLevel(logging.WARNING)  # Suppress watchdog logs
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Suppress Flask development server logs

# API keys
API_KEY = 'CBW00IFBKPX65Q5D'
BASE_URL = 'https://www.alphavantage.co/query'
EOD_API_TOKEN = '670e930c66a298.91756873'
EOD_API_URL = 'https://eodhistoricaldata.com/api'
os.environ["GROQ_API_KEY"] = "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"
DCF_API_KEY = "c04b2887-3132-4684-ac58-9fc3b3e2dc81"
FMP_API_KEY = "tJJK650ilrzbpUNWeH25k9ShsOtL4XTz"
GROQ_NEWS_API_KEY = "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"
TRANSCRIPT_API_KEY = "09bef1b4-e838-4f58-8c90-a74d7101456f"
GROQ_TRANSCRIPT_API_KEY = "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"




class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

class ImprovedPaperFetcher:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Research Project)"  # Add user agent
        }
        self.console = Console()
        self.request_count = 0
        self.last_request_time = datetime.now()
        self.retry_delay = 2  # seconds between retries

    def fetch_papers(self, query, limit=10, offset=0, fields=None):
        if fields is None:
            fields = ["title", "url", "authors", "year", "domain"]
        
        # Properly encode the fields parameter
        fields_param = ",".join(fields)
        
        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": fields_param
        }

        url = f"{self.base_url}/paper/search"
        
        max_retries = 3
        current_retry = 0

        while current_retry < max_retries:
            try:
                # Rate limiting
                time_since_last_request = (datetime.now() - self.last_request_time).total_seconds()
                if time_since_last_request < self.retry_delay:
                    sleep_time = self.retry_delay - time_since_last_request
                    time.sleep(sleep_time)

                self.last_request_time = datetime.now()
                self.request_count += 1

                response = requests.get(
                    url, 
                    params=params, 
                    headers=self.headers,
                    timeout=10  # Add timeout
                )

                if response.status_code == 429:  # Rate limit exceeded
                    sleep_time = int(response.headers.get('Retry-After', self.retry_delay))
                    time.sleep(sleep_time)
                    current_retry += 1
                    continue

                response.raise_for_status()
                data = response.json()

                if not data.get("data"):
                    logging.warning(f"No results found for query: {query}")
                    return []

                papers = data.get("data", [])
                processed_papers = []
                
                for paper in papers:
                    processed_paper = {
                        "title": paper.get("title", "N/A"),
                        "url": paper.get("url", "N/A"),
                        "authors": [author.get("name", "N/A") for author in paper.get("authors", [])],
                        "year": paper.get("year", "N/A"),
                        "domain": paper.get("domain", "N/A")
                    }
                    processed_papers.append(processed_paper)

                return processed_papers

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching papers (attempt {current_retry + 1}/{max_retries}): {str(e)}")
                if current_retry == max_retries - 1:
                    return []
                current_retry += 1
                time.sleep(self.retry_delay)

        return []  # Return empty list if all retries failed


class TranscriptAnalyzer:
    def __init__(self, api_key: str, groq_api_key: str):
        self.api_key = api_key
        self.base_url = "https://discountingcashflows.com/api/transcript/"
        self.groq_client = Groq(api_key=groq_api_key)
        self.chunk_size = 3000
        self.overlap = 200
        self.logger = logging.getLogger(__name__)

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            if start > 0:
                chunk = text[start - self.overlap:end]
            chunks.append(chunk)
            start += self.chunk_size - self.overlap
        return chunks

    def analyze_chunk(self, chunk: str, chunk_index: int, total_chunks: int) -> dict:
        """Analyze a single chunk of the transcript with robust error handling"""
        prompt = f"""
        Extract ONLY actual question and answer exchanges from this earnings call transcript chunk.
        
        Rules:
        1. Look for text patterns like:
           - "Question:" or "Q:" followed by analyst questions
           - "Answer:" or "A:" followed by executive answers
           - Lines starting with analyst names followed by a question
           - Lines starting with executive names followed by answers
        
        2. Keep EXACT original text - do not summarize or modify
        3. Each exchange must be a verbatim quote from the transcript
        4. Include the complete question and complete answer
        5. Format each Q&A pair exactly like this:
           Q: [exact question text from transcript]
           A: [exact answer text from transcript]
        
        Do not generate summaries or bullet points. Only extract actual Q&A exchanges that exist in the transcript.
    
        Transcript chunk:
        {chunk}
        """
    
        try:
            self.logger.info(f'Analyzing chunk {chunk_index + 1} of {total_chunks}')
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a transcript extractor that finds and returns ONLY exact question-answer pairs from earnings call transcripts. Never generate, summarize or modify the text."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model="llama3-8b-8192",
                temperature=0.1,
            )
    
            # Extract Q&A pairs from response
            qa_pairs = []
            response_text = response.choices[0].message.content.strip()
            
            # Split response into lines and look for Q&A pairs
            lines = response_text.split('\n')
            current_q = ""
            current_a = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith('Q:'):
                    # If we have a complete Q&A pair, save it
                    if current_q and current_a:
                        qa_pairs.append(f"{current_q}\n{current_a}")
                    # Start new question
                    current_q = line
                    current_a = ""
                elif line.startswith('A:'):
                    current_a = line
                    # Save complete Q&A pair
                    if current_q and current_a:
                        qa_pairs.append(f"{current_q}\n{current_a}")
            
            # Add final pair if exists
            if current_q and current_a:
                qa_pairs.append(f"{current_q}\n{current_a}")
    
            return {"important_qa": qa_pairs}
    
        except Exception as e:
            self.logger.error(f"Error analyzing chunk {chunk_index + 1}: {str(e)}")
            return {}


            
    def merge_analyses(self, analyses: List[dict]) -> dict:
        """Merge analyses from multiple chunks"""
        merged = {
            "important_qa": []
        }
    
        seen_questions = set()
        for analysis in analyses:
            if not analysis:
                continue
                
            for qa in analysis.get('important_qa', []):
                # Get the question part (text between Q: and A:)
                try:
                    q_part = qa.split('A:')[0].strip().lower()
                    if q_part not in seen_questions and qa.count('Q:') == 1 and qa.count('A:') == 1:
                        seen_questions.add(q_part)
                        merged["important_qa"].append(qa)
                except:
                    continue
    
        # Limit to top 7 Q&A exchanges
        merged["important_qa"] = merged["important_qa"][:7]
        
        return merged

    def analyze_transcript(self, content: str) -> dict:
        """Analyze full transcript by processing it in chunks"""
        chunks = self.chunk_text(content)
        analyses = []

        for i, chunk in enumerate(chunks):
            chunk_analysis = self.analyze_chunk(chunk, i, len(chunks))
            analyses.append(chunk_analysis)

        return self.merge_analyses(analyses)

    def get_recent_quarters(self) -> List[Tuple[str, str]]:
        """Generate recent quarters to try"""
        current_date = datetime.now()
        current_quarter = (current_date.month - 1) // 3 + 1
        current_year = current_date.year

        quarters = []
        for year in range(current_year, current_year - 1, -1):
            for q in range(4, 0, -1):
                quarters.append((f"Q{q}", str(year)))
        return quarters

    def get_latest_transcript(self, ticker: str) -> Optional[dict]:
        """Fetch most recent transcript"""
        quarters_to_try = self.get_recent_quarters()

        for quarter, year in quarters_to_try:
            params = {
                'ticker': ticker.upper(),
                'quarter': quarter,
                'year': year,
                'key': self.api_key
            }

            try:
                self.logger.info(f'Checking transcript for {ticker} {quarter} {year}')
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                if data and len(data) > 0:
                    return data[0]

            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                self.logger.error(f"Error fetching transcript for {quarter} {year}: {str(e)}")
                continue

        return None

    def format_transcript(self, transcript_data: dict) -> dict:
        """Format transcript with key information highlighted"""
        if not transcript_data:
            return {
                'date': '',
                'symbol': '',
                'quarter': '',
                'year': '',
                'full_content': 'No transcript data available.',
                'qa_section': 'No Q&A section available.',
                'analysis': {}
            }
    
        try:
            formatted_date = datetime.strptime(
                transcript_data['date'],
                '%Y-%m-%d %H:%M:%S'
            ).strftime('%B %d, %Y')
    
            content = transcript_data['content']
            qa_start = content.lower().find("question-and-answer")
            qa_section = content[qa_start:] if qa_start != -1 else content
    
            self.logger.info('Analyzing transcript with AI...')
            analysis = self.analyze_transcript(content)
    
            # Format Q&A in a more readable way
            formatted_qa = []
            for qa in analysis.get('important_qa', []):
                formatted_qa.append({
                    'topic': qa['topic'],
                    'content': qa['content']
                })
    
            # Update the analysis with formatted Q&A
            analysis['important_qa'] = formatted_qa
    
            return {
                'date': formatted_date,
                'symbol': transcript_data['symbol'],
                'quarter': f"Q{transcript_data['quarter']}",
                'year': transcript_data['year'],
                'full_content': content,
                'analysis': analysis,
                'qa_section': qa_section
            }
        except Exception as e:
            self.logger.error(f"Error formatting transcript: {str(e)}")
            return {
                'date': 'Error',
                'symbol': transcript_data.get('symbol', 'Unknown'),
                'quarter': 'Error',
                'year': 'Error',
                'full_content': f'Error processing transcript: {str(e)}',
                'qa_section': 'Error',
                'analysis': {}
            }


class DCFAnalyzer:
    def __init__(self, dcf_api_key, groq_api_key):
        self.dcf_api_key = dcf_api_key
        self.base_url = "https://discountingcashflows.com/api"
        self.groq_client = Groq(api_key=groq_api_key)
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
            logging.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def fetch_article_content(self, url):
        try:
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
            logging.error(f"Error fetching article content: {str(e)}")
            return None

    def get_stock_news(self, tickers, page=1, length=15):
        try:
            url = f"{self.base_url}/news/?tickers={tickers}&page={page}&length={length}&key={self.dcf_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching stock news: {str(e)}")
            return []


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['GET'])
def analyze_stock():
    try:
        symbol = request.args.get('symbol', '').upper()
        if not symbol:
            return jsonify({'error': 'No symbol provided'}), 400

        # Validate symbol
        if not re.match(r'^[A-Z]{1,5}$', symbol):
            return jsonify({'error': 'Invalid symbol format'}), 400

        data = fetch_all_data(symbol, FMP_API_KEY)
        if not data:
            return jsonify({'error': 'Failed to fetch stock data'}), 500

        report_sections = generate_report_sections(symbol, data)
        if not report_sections:
            return jsonify({'error': 'Failed to generate report'}), 500

        return jsonify({'report': report_sections})

    except Exception as e:
        error_type, error_value, error_traceback = sys.exc_info()
        error_details = {
            'error': 'Internal server error',
            'error_message': str(e),
            'error_type': str(error_type.__name__),
            'traceback': traceback.format_exc()
        }
        logging.error(f"Error in analyze_stock: {error_details}")
        return jsonify(error_details), 500


@app.route('/news_analysis', methods=['GET'])
def analyze_news():
    try:
        symbol = request.args.get('symbol', '').upper()
        page = int(request.args.get('page', 1))
        length = int(request.args.get('length', 3))

        if not symbol:
            return jsonify({'error': 'No symbol provided'}), 400

        analyzer = DCFAnalyzer()
        news_data = analyzer.get_stock_news(tickers=symbol, page=page, length=length)
        
        analyzed_news = []
        for news_item in news_data:
            # Get full content or use initial text
            url = news_item.get('url', '')
            initial_text = news_item.get('text', '')
            full_text = analyzer.fetch_article_content(url) if url else initial_text
            text_to_analyze = full_text if full_text else initial_text
            
            # Generate AI summary
            summary = analyzer.generate_summary(text_to_analyze) if text_to_analyze else "No content available for analysis"
            
            analyzed_news.append({
                'symbol': news_item.get('symbol', 'N/A'),
                'title': news_item.get('title', 'No Title Available'),
                'url': url,
                'publishedDate': news_item.get('publishedDate', 'Not Available'),
                'source': news_item.get('site', 'Not Available'),
                'summary': summary,
                'originalText': text_to_analyze
            })

        return jsonify({'news': analyzed_news})

    except Exception as e:
        error_details = {
            'error': 'News analysis failed',
            'message': str(e),
            'traceback': traceback.format_exc()
        }
        logging.error(f"Error in news analysis: {error_details}")
        return jsonify(error_details), 500


def generate_transcript_report_prompt(symbol, data):
    transcript_data = data.get('transcript_analysis', {})
    
    prompt = f"""
    ## Earnings Call Analysis for {symbol}

    ### Call Details
    - Date: {transcript_data.get('date', 'N/A')}
    - Quarter: {transcript_data.get('quarter', 'N/A')} {transcript_data.get('year', 'N/A')}

    ### Important Q&A
    """
    
    qa_items = transcript_data.get('analysis', {}).get('important_qa', [])
    for qa in qa_items:
        prompt += f"\n{qa.get('exchange', '')}\n"

    prompt += "\n### Key Financial Metrics\n"
    metrics = transcript_data.get('analysis', {}).get('financial_metrics', [])
    for metric in metrics:
        prompt += f"- {metric}\n"

    prompt += "\n### Future Outlook\n"
    outlook = transcript_data.get('analysis', {}).get('future_outlook', [])
    for item in outlook:
        prompt += f"- {item}\n"

    prompt += "\n### Major Announcements\n"
    announcements = transcript_data.get('analysis', {}).get('announcements', [])
    for announcement in announcements:
        prompt += f"- {announcement}\n"

    return prompt

def generate_news_analysis_prompt(symbol, data):
    news_data = data.get('news_analysis', {})
    
    prompt = f"""
    ## Latest News Analysis for {symbol}

    ### Recent News Summary
    """

    if news_data:
        for item in news_data:
            prompt += f"""
            #### {item.get('title', 'No Title')}
            - Date: {item.get('publishedDate', 'N/A')}
            - Source: {item.get('source', 'N/A')}
            
            Key Points:
            {item.get('summary', 'No summary available')}
            
            ---
            """
    else:
        prompt += "\nNo recent news available for analysis.\n"

    prompt += """
    ### Market Impact Analysis
    [Analysis of how these news items might impact the stock's performance]

    ### Trading Implications
    [Discussion of potential trading strategies based on the news]
    """

    return prompt


def generate_report_sections(symbol, data):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    report_sections = []

    sections = [
        ("Basic Information", generate_basic_info_prompt),
        ("Research", generate_research_articles_prompt),
        ("News Analysis", generate_news_analysis_prompt),
        ("Earnings Call Analysis", generate_transcript_analysis_prompt),
    ]

    for section, prompt_generator in sections:
        try:
            prompt = prompt_generator(symbol, data)
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a highly knowledgeable financial analyst specializing in company overviews and stock analysis. Provide your analysis in a detailed, well-structured format with headings, subheadings, bullet points, and highlights. Use Markdown formatting for structure."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
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

#NEED TO IMPROVE RESEARCH REPORT
def generate_research_articles_prompt(symbol, data):
    fetcher = ImprovedPaperFetcher()
    papers = fetcher.fetch_papers(symbol, limit=10)
    
    PROMPT = f"""
    ## Research Articles

    ### Introduction
    This section provides an overview of recent research articles related to {symbol}. As a leading technology company, {symbol} is a subject of intense research and analysis among financial experts, analysts, and investors. This section aims to summarize the key findings, trends, and opinions from recent research articles, providing valuable insights for investors and analysts.

    ### Recent Research Papers
    """

    # Add each paper with detailed information
    for i, paper in enumerate(papers, 1):
        PROMPT += f"""
    {i}. **{paper.get('title', 'N/A')}**
       - **Year**: {paper.get('year', 'N/A')}
       - **URL**: {paper.get('url', 'N/A')}
       - **Authors**: {', '.join(paper.get('authors', ['N/A']))}
       - **Summary**: A comprehensive analysis of {paper.get('title', 'N/A')}, focusing on the impact on {symbol}'s business model and market position.
       - **Key Findings**:
         * Analysis of market trends and competitive positioning
         * Evaluation of financial performance and growth prospects
         * Assessment of technological innovations and future outlook

    """

    PROMPT += """
    ### Trends in Recent Research:
    
    ### Trends in Recent Research:
    [Provide an analysis of common themes or trends observed across recent research articles]

    ### Conflicting Views:
    [Highlight any significant disagreements or conflicting opinions found in the research]

    ### Impact on Investor Sentiment:
    [Discuss how these research articles might be influencing investor sentiment towards the stock]
    """

    return PROMPT
    


def fetch_all_data(symbol, fmp_api_key):
    try:
        # Initialize analyzers
        dcf_analyzer = DCFAnalyzer(DCF_API_KEY, GROQ_NEWS_API_KEY)
        transcript_analyzer = TranscriptAnalyzer(TRANSCRIPT_API_KEY, GROQ_TRANSCRIPT_API_KEY)
        
        # Fetch news and analyze
        news_data = dcf_analyzer.get_stock_news(symbol, page=1, length=3)
        analyzed_news = []
        
        transcript_data = transcript_analyzer.get_latest_transcript(symbol)
        if transcript_data:
            formatted_transcript = transcript_analyzer.format_transcript(transcript_data)
        else:
            formatted_transcript = {
                'date': 'N/A',
                'symbol': symbol,
                'quarter': 'N/A',
                'year': 'N/A',
                'analysis': {},
                'full_content': 'No transcript available'
            }

        
        for news_item in news_data:
            url = news_item.get('url', '')
            initial_text = news_item.get('text', '')
            full_text = dcf_analyzer.fetch_article_content(url) if url else initial_text
            text_to_analyze = full_text if full_text else initial_text
            
            if text_to_analyze:
                summary = dcf_analyzer.generate_summary(text_to_analyze)
            else:
                summary = "No content available for analysis"
                
            analyzed_news.append({
                'title': news_item.get('title', 'No Title'),
                'publishedDate': news_item.get('publishedDate', 'N/A'),
                'source': news_item.get('site', 'N/A'),
                'summary': summary
            })

        return {
            'basic_info': fetch_basic_info(symbol),
            'research_articles': fetch_research_articles(symbol),
            'transcript_analysis': formatted_transcript,
            'news_analysis': analyzed_news
        }
    except Exception as e:
        logging.error(f"Error in fetch_all_data: {str(e)}")
        return None

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


def fetch_research_articles(symbol, limit=5):  # Reduced limit to avoid rate limiting
    try:
        fetcher = ImprovedPaperFetcher()
        papers = fetcher.fetch_papers(
            query=f"{symbol} stock market analysis",  # More specific query
            limit=limit
        )

        if not papers:
            return {
                "research_articles": [{
                    "title": "No research articles found",
                    "source": "N/A",
                    "date": "N/A",
                    "author": "N/A",
                    "summary": "No research articles were found for this stock symbol.",
                    "key_takeaways": ["No data available"]
                }]
            }

        articles = []
        for paper in papers:
            article = {
                "title": paper.get("title", "N/A"),
                "source": paper.get("url", "N/A"),
                "date": str(paper.get("year", "N/A")),
                "author": ", ".join(paper.get("authors", [])) or "N/A",
                "summary": f"Analysis of {paper.get('title', 'N/A')}",
                "key_takeaways": ["Research paper available for detailed analysis"]
            }
            articles.append(article)

        return {"research_articles": articles}

    except Exception as e:
        logging.error(f"Error in fetch_research_articles: {str(e)}")
        return {
            "research_articles": [{
                "title": "Error fetching research articles",
                "source": "N/A",
                "date": "N/A",
                "author": "N/A",
                "summary": f"An error occurred while fetching research articles: {str(e)}",
                "key_takeaways": ["Error in data retrieval"]
            }]
        }



def display_papers(papers: List[Dict], console: Console): # Updated display function
    """Display papers in a formatted table with clickable links"""
    if not papers:
        console.print("[red]No papers found!")
        return

    table = Table(show_header=True, header_style="bold magenta", width=120)  # Increased width
    table.add_column("Title", width=40, style="cyan", no_wrap=True)
    table.add_column("Year", justify="center", width=10)
    table.add_column("Domain", width=20)
    table.add_column("Authors", width=30)
    table.add_column("Link", width=20)  # Added Link column



    for paper in papers:
        authors = ", ".join(paper['authors'][:2]) if paper['authors'] else "N/A"
        if len(paper['authors']) > 2:
            authors += " et al."

        # Make title a clickable link
        title_link = f"[link={paper['url']}]{paper['title']}[/link]" if paper.get("url") else paper['title']


        table.add_row(
            title_link,  # Added title as link
            str(paper.get('year', 'N/A')),
            paper['domain'],
            authors,
            paper.get('url', 'N/A')  # Added link to the table
        )

    console.print(table)


if __name__ == '__main__':
    app.run(debug=True, port=5000)