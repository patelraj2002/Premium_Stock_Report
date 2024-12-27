import streamlit as st
import requests
from datetime import datetime
import json
from typing import Optional, Tuple, List
from groq import Groq

class TranscriptAnalyzer:
    def __init__(self, api_key: str, groq_api_key: str):
        self.api_key = api_key
        self.base_url = "https://discountingcashflows.com/api/transcript/"
        self.groq_client = Groq(api_key=groq_api_key)
        self.chunk_size = 3000  # Characters per chunk
        self.overlap = 200  # Overlap between chunks to maintain context

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
        You are analyzing part {chunk_index + 1} of {total_chunks} from an earnings call transcript.
        Extract the following information in a clear, organized way, and omit any sections that do not contain relevant data:
        1. Important questions and answers between analysts and management (skip if none)
        2. Key financial metrics and numbers mentioned
        3. Future outlook and guidance statements
        4. Major announcements or strategic changes
        Format as JSON, omitting "Not mentioned" sections and ensure completeness:
        {{
            "important_qa": [
                {{"question": "...", "answer": "..."}}
            ],
            "financial_metrics": ["..."],
            "future_outlook": ["..."],
            "announcements": ["..."]
        }}
        Transcript chunk:
        {chunk}
        """

        try:
            with st.spinner(f'Analyzing chunk {chunk_index + 1} of {total_chunks}...'):
                response = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-8b-8192",
                    temperature=0.1,
                    max_tokens=2000,
                )

                response_text = response.choices[0].message.content.strip()
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    try:
                        analysis = json.loads(json_str)

                        # Filter out placeholders
                        analysis['important_qa'] = [
                            qa for qa in analysis.get('important_qa', [])
                            if "not mentioned" not in (qa['question'].lower() + qa['answer'].lower())
                        ]

                        return analysis
                    except json.JSONDecodeError:
                        st.warning(f"Invalid JSON response for chunk {chunk_index + 1}. Please check the AI response.")
                        return {}

                st.warning(f"No valid JSON found in the AI response for chunk {chunk_index + 1}.")
                return {}

        except Exception as e:
            st.error(f"Error analyzing chunk {chunk_index + 1}: {str(e)}")
            return {}

    def merge_analyses(self, analyses: List[dict]) -> dict:
        """Merge analyses from multiple chunks, ensuring no duplicates and handling cut-off entries"""
        merged = {
            "important_qa": [],
            "financial_metrics": [],
            "future_outlook": [],
            "announcements": []
        }

        for analysis in analyses:
            if not analysis:
                continue
            merged["important_qa"].extend(analysis.get("important_qa", []))
            merged["financial_metrics"].extend(analysis.get("financial_metrics", []))
            merged["future_outlook"].extend(analysis.get("future_outlook", []))
            merged["announcements"].extend(analysis.get("announcements", []))

        # Remove duplicates and limit list sizes
        for key in ["financial_metrics", "future_outlook", "announcements"]:
            merged[key] = list(dict.fromkeys(merged[key]))[:5]

        # Unique Q&A
        seen_questions = set()
        unique_qas = []
        for qa in merged["important_qa"]:
            q_lower = qa["question"].lower()
            if q_lower not in seen_questions:
                seen_questions.add(q_lower)
                unique_qas.append(qa)
        merged["important_qa"] = unique_qas[:7]

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
                with st.spinner(f'Checking {quarter} {year}...'):
                    response = requests.get(self.base_url, params=params)
                    response.raise_for_status()

                    data = response.json()
                    if data and len(data) > 0:
                        return data[0]

            except (requests.exceptions.RequestException, json.JSONDecodeError):
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

        formatted_date = datetime.strptime(
            transcript_data['date'],
            '%Y-%m-%d %H:%M:%S'
        ).strftime('%B %d, %Y')

        content = transcript_data['content']
        qa_start = content.lower().find("question-and-answer")
        qa_section = content[qa_start:] if qa_start != -1 else content

        with st.spinner('Analyzing transcript with AI...'):
            analysis = self.analyze_transcript(content)

        return {
            'date': formatted_date,
            'symbol': transcript_data['symbol'],
            'quarter': f"Q{transcript_data['quarter']}",
            'year': transcript_data['year'],
            'full_content': content,
            'analysis': analysis,
            'qa_section': qa_section
        }

def main():
    st.set_page_config(page_title="AI-Powered Earnings Call Analyzer", layout="wide")
    st.title("🤖 AI-Powered Earnings Call Analyzer")
    st.markdown("""
    Get instant access to earnings call transcripts with AI-powered analysis.
    """)

    TRANSCRIPT_API_KEY = "09bef1b4-e838-4f58-8c90-a74d7101456f"
    GROQ_API_KEY = "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"
    analyzer = TranscriptAnalyzer(TRANSCRIPT_API_KEY, GROQ_API_KEY)

    col1, col2 = st.columns([2, 3])
    with col1:
        ticker = st.text_input("Enter Stock Ticker:", placeholder="e.g., AAPL").strip().upper()

    if ticker:
        transcript_data = analyzer.get_latest_transcript(ticker)

        if transcript_data:
            formatted = analyzer.format_transcript(transcript_data)
            st.subheader(f"{formatted['symbol']} Earnings Call - {formatted['quarter']} {formatted['year']}")
            st.info(f"📅 Call Date: {formatted['date']}")

            tab1, tab2 = st.tabs(["AI Analysis", "Full Transcript"])

            with tab1:
                if formatted['analysis']:
                    st.markdown("### 🔍 Key Insights")

                    st.markdown("#### 📊 Key Financial Metrics")
                    for metric in formatted['analysis'].get('financial_metrics', []):
                        st.markdown(f"- {metric}")

                    st.markdown("#### 🔮 Future Outlook")
                    for outlook in formatted['analysis'].get('future_outlook', []):
                        st.markdown(f"- {outlook}")

                    st.markdown("#### 📢 Major Announcements")
                    for announcement in formatted['analysis'].get('announcements', []):
                        st.markdown(f"- {announcement}")

                    st.markdown("#### 🤝 Important Q&A")
                    for qa in formatted['analysis'].get('important_qa', []):
                        st.markdown(f"**Q:** {qa['question']}\n**A:** {qa['answer']}")

                else:
                    st.warning("No analysis available for this transcript.")

            with tab2:
                st.markdown("### 📜 Full Transcript")
                st.text_area("Transcript", formatted['full_content'], height=300)

        else:
            st.error("Could not find the transcript for the given ticker.")

if __name__ == "__main__":
    main()
