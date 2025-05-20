import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, request, jsonify, Response
import whois
import time
import re
import json
import traceback
from io import BytesIO
from weasyprint import HTML, CSS
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'domain_checker_secret_key'

# List of TLDs to check
DEFAULT_TLDS = ['.com', '.net', '.org', '.io', '.ai', '.com.br']

@app.route('/')
def index():
    """Render the main page with the domain input form."""
    return render_template('index.html', tlds=DEFAULT_TLDS)

@app.route('/check', methods=['POST'])
def check_domains():
    """Check domain availability for the provided brand names."""
    # Get form data
    brand_names = request.form.get('brand_names', '').strip().split('\n')
    selected_tlds = request.form.getlist('tlds')
    
    if not brand_names or not selected_tlds:
        return jsonify({'error': 'Please provide brand names and select at least one TLD'}), 400
    
    # Clean brand names (remove empty lines and whitespace)
    brand_names = [name.strip() for name in brand_names if name.strip()]
    
    # Initialize progress tracking
    total_checks = len(brand_names) * len(selected_tlds)
    current_check = 0
    
    # Check domains and get results
    results = []
    errors = []
    
    for brand_idx, brand in enumerate(brand_names):
        try:
            # Send progress update
            progress_percent = int((brand_idx / len(brand_names)) * 100)
            yield f"data: {json.dumps({'progress': progress_percent, 'status': f'Processing brand: {brand}'})}\n\n"
            
            brand_result = {
                'brand': brand,
                'domains': [],
                'suggestions': []
            }
            
            # Normalize brand name for domain use
            normalized_brand = normalize_brand_name(brand)
            
            # Check each selected TLD
            for tld_idx, tld in enumerate(selected_tlds):
                try:
                    domain = f"{normalized_brand}{tld}"
                    
                    # Send progress update for domain check
                    yield f"data: {json.dumps({'progress': progress_percent, 'status': f'Checking domain: {domain}'})}\n\n"
                    
                    available = check_domain_availability(domain)
                    
                    brand_result['domains'].append({
                        'domain': domain,
                        'available': available
                    })
                    
                    current_check += 1
                    
                except Exception as e:
                    error_msg = f"Error checking domain {normalized_brand}{tld}: {str(e)}"
                    errors.append(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    
                    # Add domain with error status
                    brand_result['domains'].append({
                        'domain': f"{normalized_brand}{tld}",
                        'available': False,
                        'error': str(e)
                    })
            
            # Generate suggestions for unavailable domains
            unavailable_domains = [d for d in brand_result['domains'] if not d['available']]
            if unavailable_domains:
                yield f"data: {json.dumps({'status': f'Generating suggestions for {brand}'})}\n\n"
                brand_result['suggestions'] = generate_domain_suggestions(normalized_brand, selected_tlds)
            
            results.append(brand_result)
            
        except Exception as e:
            error_msg = f"Error processing brand {brand}: {str(e)}"
            errors.append(error_msg)
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            traceback.print_exc()
    
    # Send completion status
    yield f"data: {json.dumps({'progress': 100, 'status': 'Completed', 'results': results, 'errors': errors})}\n\n"

@app.route('/stream-check', methods=['POST'])
def stream_check_domains():
    """Stream domain availability check results with progress updates."""
    return Response(check_domains(), mimetype='text/event-stream')

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate a PDF report of domain availability results."""
    try:
        # Get results data from request
        data = request.json
        if not data or 'results' not in data:
            return jsonify({'error': 'No results data provided'}), 400
        
        results = data['results']
        
        # Create HTML content for PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Domain Availability Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2541b2; text-align: center; }}
                .timestamp {{ text-align: center; color: #666; margin-bottom: 30px; }}
                .brand-section {{ margin-bottom: 30px; }}
                .brand-name {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                .domain-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                .domain-table th, .domain-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .domain-table th {{ background-color: #f2f2f2; }}
                .available {{ color: green; }}
                .unavailable {{ color: red; }}
                .suggestions-title {{ font-weight: bold; margin-top: 15px; }}
                .suggestions {{ margin-top: 5px; }}
                .suggestion-item {{ display: inline-block; background-color: #f8f9fa; padding: 5px 10px; 
                                   margin-right: 5px; margin-bottom: 5px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>Domain Availability Report</h1>
            <div class="timestamp">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        """
        
        for result in results:
            brand = result['brand']
            domains = result['domains']
            suggestions = result.get('suggestions', [])
            
            html_content += f"""
            <div class="brand-section">
                <div class="brand-name">{brand}</div>
                <table class="domain-table">
                    <tr>
                        <th>Domain</th>
                        <th>Status</th>
                    </tr>
            """
            
            for domain in domains:
                status_class = "available" if domain['available'] else "unavailable"
                status_text = "Available" if domain['available'] else "Unavailable"
                
                html_content += f"""
                    <tr>
                        <td>{domain['domain']}</td>
                        <td class="{status_class}">{status_text}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            """
            
            if suggestions:
                html_content += """
                <div class="suggestions-title">Alternative Suggestions:</div>
                <div class="suggestions">
                """
                
                for suggestion in suggestions:
                    html_content += f'<span class="suggestion-item">{suggestion}</span>'
                
                html_content += """
                </div>
                """
            
            html_content += """
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # Generate PDF
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Return PDF as response
        return Response(
            pdf_buffer,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': 'attachment; filename=domain_availability_report.pdf',
                'Content-Type': 'application/pdf'
            }
        )
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Error generating PDF: {str(e)}'}), 500

def normalize_brand_name(brand_name):
    """Normalize brand name for domain use (remove spaces, special chars, etc.)"""
    # Convert to lowercase
    normalized = brand_name.lower()
    
    # Remove special characters and spaces
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    
    return normalized

def check_domain_availability(domain):
    """Check if a domain is available using WHOIS."""
    try:
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
        
        # Query WHOIS
        domain_info = whois.whois(domain)
        
        # If the domain doesn't exist, it's available
        if domain_info.status is None or domain_info.domain_name is None:
            return True
        
        return False
    except Exception as e:
        # Log the error but don't fail the entire process
        error_msg = f"Error checking domain {domain}: {str(e)}"
        print(error_msg)
        # Re-raise to be caught by the caller
        raise

def generate_domain_suggestions(brand, selected_tlds):
    """Generate alternative domain suggestions."""
    suggestions = []
    
    # Prefixes to try
    prefixes = ['get', 'try', 'use', 'my', 'the']
    
    # Suffixes to try
    suffixes = ['app', 'site', 'online', 'digital', 'web']
    
    # Generate suggestions with prefixes
    for prefix in prefixes:
        for tld in selected_tlds:
            suggestions.append(f"{prefix}{brand}{tld}")
    
    # Generate suggestions with suffixes
    for suffix in suffixes:
        for tld in selected_tlds:
            suggestions.append(f"{brand}{suffix}{tld}")
    
    # Add hyphenated version if brand is long enough
    if len(brand) > 5:
        middle = len(brand) // 2
        hyphenated = f"{brand[:middle]}-{brand[middle:]}"
        for tld in selected_tlds:
            suggestions.append(f"{hyphenated}{tld}")
    
    # Limit to 10 suggestions to avoid overwhelming the user
    return suggestions[:10]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
