import requests
import re

# API key and endpoint information
DCF_API_KEY = "c04b2887-3132-4684-ac58-9fc3b3e2dc81"
BASE_URL = "https://api.discountingcashflows.com"

def get_transcript(ticker, quarter, year):
    """Fetches transcript for a specified company ticker, quarter, and year."""
    url = f"{BASE_URL}/api/transcript/?ticker={ticker}&quarter={quarter}&year={year}&key={DCF_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Extract content from transcript
        if data and len(data) > 0:
            transcript_content = data[0].get('content', '')
            return transcript_content
        else:
            print("Transcript data not available for the specified ticker, quarter, or year.")
            return None
    except requests.exceptions.RequestException as e:
        print("Error fetching transcript:", e)
        return None

def extract_qa(transcript_content):
    """Extracts question and answer pairs from the transcript content."""
    # Regex pattern to identify questions and answers
    qa_pairs = re.findall(r"(Q:\s.*?)(A:\s.*?)\n\n", transcript_content, re.DOTALL)
    return qa_pairs[:5]  # Limit to 5 pairs

def main():
    ticker = "AAPL"
    quarter = "Q4"
    year = "2023"

    # Get the transcript data
    transcript_content = get_transcript(ticker, quarter, year)
    
    if transcript_content:
        # Extract questions and answers
        qa_pairs = extract_qa(transcript_content)
        
        # Print questions and answers
        if qa_pairs:
            print("Sample Q&A from the transcript:")
            for i, (question, answer) in enumerate(qa_pairs, 1):
                print(f"\nQuestion {i}: {question.strip()}")
                print(f"Answer {i}: {answer.strip()}")
        else:
            print("No Q&A pairs found in the transcript.")
    else:
        print("Transcript content not available.")

if __name__ == "__main__":
    main()
