import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, request, jsonify
import whois
import time
import re

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
    
    # Check domains and get results
    results = []
    for brand in brand_names:
        brand_result = {
            'brand': brand,
            'domains': [],
            'suggestions': []
        }
        
        # Normalize brand name for domain use
        normalized_brand = normalize_brand_name(brand)
        
        # Check each selected TLD
        for tld in selected_tlds:
            domain = f"{normalized_brand}{tld}"
            available = check_domain_availability(domain)
            
            brand_result['domains'].append({
                'domain': domain,
                'available': available
            })
            
            # If domain is not available, add to list for suggestions
            if not available:
                brand_result['suggestions'] = generate_domain_suggestions(normalized_brand, selected_tlds)
        
        results.append(brand_result)
    
    return jsonify({'results': results})

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
        # If there's an error, assume the domain is not available
        print(f"Error checking domain {domain}: {str(e)}")
        return False

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
