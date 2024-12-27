import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from groq import Groq

def get_company_domains(ticker):
    client = Groq(api_key="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")
    
    prompt = f"""
    For the company with ticker {ticker}, list exactly 10 most important technical research areas and technologies.
    Provide them as a simple comma-separated list without explanations or additional text.
    Example format: "artificial intelligence, machine learning, computer vision, etc"
    Keep terms concise and focused on technical aspects.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192"
        )
        
        response = chat_completion.choices[0].message.content.strip()
        
        # Clean up the response and split into terms
        terms = [term.strip() for term in response.split(',')]
        
        # Filter out any empty or too long terms
        terms = [term for term in terms if term and len(term) < 50]
        
        # Take only the first 10 terms
        terms = terms[:10]
        
        console.print("[blue]Search terms identified:[/blue]")
        for i, term in enumerate(terms, 1):
            console.print(f"[blue]{i}. {term}[/blue]")
        
        return terms
        
    except Exception as e:
        console.print(f"[red]Error getting company domains: {str(e)}[/red]")
        return [ticker]

def get_research_papers(ticker, limit=10):
    base_url = "http://export.arxiv.org/api/query"
    search_terms = get_company_domains(ticker)
    
    # Create search query combining terms with OR
    search_query = " OR ".join([
        f'(ti:"{term}" OR abs:"{term}")'
        for term in search_terms
    ])
    
    params = {
        "search_query": search_query,
        "max_results": limit * 3,  # Request more to ensure we get enough relevant ones
        "sortBy": "lastUpdatedDate",
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
            
            # Check relevancy
            is_relevant = any(term.lower() in title.lower() or term.lower() in abstract.lower() 
                            for term in search_terms)
            
            if is_relevant:
                authors = [author.find('atom:name', namespace).text 
                          for author in entry.findall('atom:author', namespace)]
                
                paper = {
                    "title": title,
                    "authors": authors,
                    "published": entry.find('atom:published', namespace).text,
                    "url": entry.find('atom:id', namespace).text,
                    "abstract": abstract[:200] + "..." if len(abstract) > 200 else abstract,
                    "relevance_score": sum(term.lower() in (title.lower() + abstract.lower()) 
                                        for term in search_terms)
                }
                papers.append(paper)

        # Sort by relevance score and return top results
        papers.sort(key=lambda x: x['relevance_score'], reverse=True)
        return papers[:limit]

    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error fetching papers: {str(e)}[/red]")
        return []
    except ET.ParseError as e:
        console.print(f"[red]Error parsing XML response: {str(e)}[/red]")
        return []

def display_papers(papers):
    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title", width=50, style="cyan", overflow="fold")
    table.add_column("Authors", width=30, style="green", overflow="fold")
    table.add_column("Published", width=12, style="yellow", justify="center")
    table.add_column("Abstract", width=50, style="white", overflow="fold")
    table.add_column("Relevance", width=10, style="red", justify="center")

    for paper in papers:
        table.add_row(
            paper["title"],
            ", ".join(paper["authors"]),
            paper["published"].split("T")[0],
            paper["abstract"],
            str(paper["relevance_score"])
        )

    console.print(table)

if __name__ == "_main_":
    console = Console()
    console.print("""
    [bold blue]
    ╔═══════════════════════════════════════╗
    ║     Research Paper Finder v1.0  ║
    ╚═══════════════════════════════════════╝
    [/bold blue]
    """)

    while True:
        ticker = console.input("\n[green]Enter a company ticker (or 'quit' to exit): [/green]").upper()
        if ticker.lower() == 'quit':
            break

        papers = get_research_papers(ticker, limit=10)
        console.print(f"\n[bold yellow]Papers found for {ticker}:[/bold yellow]")
        display_papers(papers)