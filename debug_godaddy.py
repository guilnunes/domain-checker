"""
Debug script to test GoDaddy API integration directly.
This script can be run independently to verify GoDaddy API functionality.
"""

import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('godaddy_debug.log')
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from src.registrar_apis import create_godaddy_provider
from src.domain_checker import DomainChecker

async def test_godaddy_api():
    """Test GoDaddy API directly."""
    # Load environment variables
    load_dotenv()
    
    # Log environment variables (masked for security)
    api_key = os.environ.get('GODADDY_API_KEY', '')
    api_secret = os.environ.get('GODADDY_API_SECRET', '')
    use_production = os.environ.get('GODADDY_USE_PRODUCTION', 'true').lower() == 'true'
    
    logger.info(f"API Key present: {'Yes' if api_key else 'No'}")
    logger.info(f"API Secret present: {'Yes' if api_secret else 'No'}")
    logger.info(f"Using production API: {use_production}")
    
    # Create GoDaddy provider
    godaddy_provider = create_godaddy_provider()
    if not godaddy_provider:
        logger.error("Failed to create GoDaddy provider - check credentials")
        return
    
    logger.info(f"GoDaddy provider created successfully: {godaddy_provider.source_name}")
    
    # Test domains
    test_domains = [
        "google.com",          # Definitely registered
        "thisisarandomdomainthatdoesnotexist12345.com",  # Likely available
        "example.org",         # Registered
        "microsoft.net"        # Registered
    ]
    
    # Test each domain directly with the provider
    for domain in test_domains:
        logger.info(f"Testing domain directly with GoDaddy provider: {domain}")
        try:
            result = await godaddy_provider.check_availability(domain)
            logger.info(f"Direct GoDaddy result for {domain}: {json.dumps(result, indent=2)}")
        except Exception as e:
            logger.error(f"Error testing domain {domain}: {str(e)}")
    
    # Now test with the full domain checker
    logger.info("Creating domain checker with GoDaddy provider")
    domain_checker = DomainChecker()
    domain_checker.add_provider(godaddy_provider)
    
    for domain in test_domains:
        logger.info(f"Testing domain with full domain checker: {domain}")
        try:
            result = await domain_checker.check_domain(domain)
            logger.info(f"Full checker result for {domain}: {json.dumps(result, indent=2)}")
            
            # Specifically check if GoDaddy results are in the sources
            sources = [s['source'] for s in result['sources']]
            logger.info(f"Sources in result: {sources}")
            
            if "GoDaddy" not in sources:
                logger.error(f"GoDaddy source missing from results for {domain}")
            else:
                godaddy_result = next((s for s in result['sources'] if s['source'] == "GoDaddy"), None)
                logger.info(f"GoDaddy specific result: {godaddy_result}")
        except Exception as e:
            logger.error(f"Error testing domain {domain} with full checker: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting GoDaddy API debug script")
    asyncio.run(test_godaddy_api())
    logger.info("GoDaddy API debug script completed")
