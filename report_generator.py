import json
from report_sections.basic_info import generate_basic_info_prompt
from report_sections.fundamental_analysis import generate_fundamental_analysis_prompt
from report_sections.technical_analysis import generate_technical_analysis_prompt
from report_sections.earnings_report import generate_earnings_report_prompt
from report_sections.press_release import generate_press_release_prompt
from report_sections.earnings_call import generate_earnings_call_prompt
from report_sections.historical_earnings import generate_historical_earnings_prompt
from report_sections.analyst_coverage import generate_analyst_coverage_prompt
from report_sections.company_guidance import generate_company_guidance_prompt
from report_sections.research_articles import generate_research_articles_prompt
from report_sections.transcript_report import generate_transcript_report_prompt
from report_sections.references import generate_references_prompt

def generate_report(symbol, data):
    """Generate a complete report for the given stock symbol using the fetched data."""
    
    report = {}
    
    # Generate each section of the report
    report['basic_info'] = generate_basic_info_prompt(symbol, data)
    report['fundamental_analysis'] = generate_fundamental_analysis_prompt(symbol, data)
    report['technical_analysis'] = generate_technical_analysis_prompt(symbol, data)
    report['earnings_report'] = generate_earnings_report_prompt(symbol, data)
    report['press_release'] = generate_press_release_prompt(symbol, data)
    report['earnings_call'] = generate_earnings_call_prompt(symbol, data)
    report['historical_earnings'] = generate_historical_earnings_prompt(symbol, data)
    report['analyst_coverage'] = generate_analyst_coverage_prompt(symbol, data)
    report['company_guidance'] = generate_company_guidance_prompt(symbol, data)
    report['research_articles'] = generate_research_articles_prompt(symbol, data)
    report['transcript_report'] = generate_transcript_report_prompt(symbol, data)
    report['references'] = generate_references_prompt(symbol, data)

    return report

def generate_report_html(report):
    """Generate HTML representation of the report."""
    html_report = """
    <html>
    <head><title>Stock Analysis Report</title></head>
    <body>
    <h1>Stock Analysis Report</h1>
    """

    for section, content in report.items():
        html_report += f"<h2>{section.replace('_', ' ').title()}</h2>"
        html_report += f"<pre>{content}</pre>"

    html_report += """
    </body>
    </html>
    """
    return html_report
