import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, request, jsonify, Response
import asyncio
import json
import traceback
from io import BytesIO
from weasyprint import HTML, CSS
from datetime import datetime
import logging

# Import our domain checker modules
from src.domain_checker import DomainChecker, normalize_brand_name, DomainSuggestionGenerator
from src.registrar_apis import create_godaddy_provider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'domain_checker_secret_key'

# List of TLDs to check
DEFAULT_TLDS = ['.com', '.net', '.org', '.io', '.ai', '.com.br']

# Initialize the domain checker
domain_checker = DomainChecker()

# Try to add GoDaddy provider if credentials are available
godaddy_provider = create_godaddy_provider()
if godaddy_provider:
    domain_checker.add_provider(godaddy_provider)
    logger.info("GoDaddy API provider added to domain checker")
else:
    logger.warning("GoDaddy API provider not available - using WHOIS only")

@app.route('/')
def index():
    """Render the main page with the domain input form."""
    # Get the list of active providers
    providers = [p.source_name for p in domain_checker.providers]
    return render_template('index.html', tlds=DEFAULT_TLDS, providers=providers)

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
                    
                    # Use the multi-source domain checker
                    result = asyncio.run(domain_checker.check_domain(domain))
                    
                    # Add to results
                    domain_result = {
                        'domain': domain,
                        'available': result['available'],
                        'confidence': result['confidence'],
                        'status': result['status'],
                        'sources': result['sources'],
                        'conflicting_results': result['conflicting_results']
                    }
                    
                    brand_result['domains'].append(domain_result)
                    
                    current_check += 1
                    
                except Exception as e:
                    error_msg = f"Error checking domain {normalized_brand}{tld}: {str(e)}"
                    errors.append(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    
                    # Add domain with error status
                    brand_result['domains'].append({
                        'domain': f"{normalized_brand}{tld}",
                        'available': False,
                        'confidence': 0.0,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Generate suggestions for unavailable domains
            unavailable_domains = [d for d in brand_result['domains'] if not d.get('available')]
            if unavailable_domains:
                yield f"data: {json.dumps({'status': f'Generating suggestions for {brand}'})}\n\n"
                brand_result['suggestions'] = DomainSuggestionGenerator.generate_suggestions(
                    normalized_brand, selected_tlds)
            
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
                .uncertain {{ color: orange; }}
                .error {{ color: #ff6b6b; }}
                .confidence {{ font-size: 12px; color: #666; }}
                .high-confidence {{ font-weight: bold; }}
                .medium-confidence {{ font-style: italic; }}
                .low-confidence {{ font-style: italic; color: #999; }}
                .sources {{ font-size: 11px; color: #666; margin-top: 3px; }}
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
                        <th>Confidence</th>
                        <th>Sources</th>
                    </tr>
            """
            
            for domain in domains:
                # Determine status class
                status_class = "unavailable"
                status_text = "Unavailable"
                
                if domain.get('status') == 'error':
                    status_class = "error"
                    status_text = "Error"
                elif domain.get('available'):
                    status_class = "available"
                    status_text = "Available"
                elif domain.get('status') and 'uncertain' in domain.get('status'):
                    status_class = "uncertain"
                    status_text = "Uncertain"
                
                # Determine confidence class
                confidence = domain.get('confidence', 0.0)
                confidence_class = "low-confidence"
                if confidence >= 0.8:
                    confidence_class = "high-confidence"
                elif confidence >= 0.5:
                    confidence_class = "medium-confidence"
                
                # Format confidence as percentage
                confidence_text = f"{int(confidence * 100)}%"
                
                # Format sources
                sources = domain.get('sources', [])
                sources_text = ", ".join([s.get('source', 'Unknown') for s in sources if s.get('error') is None])
                if not sources_text:
                    sources_text = "No valid sources"
                
                html_content += f"""
                    <tr>
                        <td>{domain['domain']}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td class="confidence {confidence_class}">{confidence_text}</td>
                        <td class="sources">{sources_text}</td>
                    </tr>
                """
                
                # Add error message if present
                if domain.get('error'):
                    html_content += f"""
                    <tr>
                        <td colspan="4" class="error">Error: {domain['error']}</td>
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
