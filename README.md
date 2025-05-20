# Domain Availability Checker Web Application - README

## Overview
This web application allows users to check the availability of domain names based on a list of brand names. It provides a simple user interface for input and displays results on a webpage, including suggestions for alternative domains when the primary choices are unavailable.

## Features
- Check domain availability for multiple TLDs (.com, .net, .org, .io, .ai, .com.br)
- Input multiple brand names at once (one per line)
- Get alternative domain suggestions for unavailable domains
- User-friendly interface with responsive design

## Requirements
- Python 3.6+
- Flask
- python-whois
- Internet connection for WHOIS queries

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
   ```
   python -m src.main
   ```
2. Open a web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```
3. Enter your brand names in the text area (one per line)
4. Select the TLDs you want to check
5. Click "Check Domain Availability"
6. View the results, including availability status and alternative suggestions

## How It Works

1. The application takes the list of brand names and normalizes them (removes spaces, special characters, etc.)
2. For each brand name, it checks the availability of domains with the selected TLDs
3. For unavailable domains, it generates alternative suggestions using prefixes, suffixes, and other variations
4. Results are displayed in an organized, user-friendly format

## Limitations

- WHOIS queries may be rate-limited by servers
- Some WHOIS servers may return inconsistent results
- The application cannot reserve or purchase domains
- Large lists of domains may take time to process

## Future Enhancements

- User accounts for saving domain check history
- Email notifications for completed checks
- Integration with domain registrars for direct purchase
- Advanced domain suggestion algorithms using NLP
- Bulk import/export functionality
