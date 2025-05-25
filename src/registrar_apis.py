"""
GoDaddy API integration for domain availability checking.
This module provides a GoDaddy API source provider for the multi-source domain checker.
"""

import os
import json
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from .domain_checker import DomainSourceProvider

# Import dotenv for secure credential loading
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoDaddyProvider(DomainSourceProvider):
    """Domain availability provider using GoDaddy API."""
    
    # GoDaddy API endpoints
    OTE_BASE_URL = "https://api.ote-godaddy.com"  # Test environment
    PROD_BASE_URL = "https://api.godaddy.com"     # Production environment
    
    def __init__(self, api_key: str, api_secret: str, use_production: bool = True):
        """
        Initialize the GoDaddy API provider.
        
        Args:
            api_key: GoDaddy API key
            api_secret: GoDaddy API secret
            use_production: Whether to use production API (True) or OTE/test API (False)
        """
        self._source_name = "GoDaddy"
        self._weight = 0.9  # Higher weight than WHOIS
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = self.PROD_BASE_URL if use_production else self.OTE_BASE_URL
        
        # Validate credentials
        if not api_key or not api_secret:
            logger.warning("GoDaddy API credentials not provided or incomplete")
        else:
            logger.info(f"GoDaddy provider initialized with API key: {api_key[:5]}... and base URL: {self._base_url}")
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def weight(self) -> float:
        return self._weight
    
    async def check_availability(self, domain: str) -> Dict[str, Any]:
        """Check domain availability using GoDaddy API."""
        result = {
            'available': False,
            'confidence': 0.0,
            'source': self.source_name,
            'details': {},
            'error': None
        }
        
        # Check if credentials are available
        if not self._api_key or not self._api_secret:
            error_msg = "GoDaddy API credentials not configured"
            logger.error(error_msg)
            result['error'] = error_msg
            result['confidence'] = 0.0
            return result
        
        logger.info(f"Checking domain availability via GoDaddy API: {domain}")
        
        try:
            # Prepare API request
            headers = {
                'Authorization': f'sso-key {self._api_key}:{self._api_secret}',
                'Accept': 'application/json'
            }
            
            # GoDaddy API endpoint for domain availability
            url = f"{self._base_url}/v1/domains/available"
            params = {'domain': domain}
            
            logger.debug(f"Making GoDaddy API request to {url} with params {params}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_status = response.status
                    response_text = await response.text()
                    logger.info(f"GoDaddy API response for {domain}: Status {response_status}")
                    logger.debug(f"GoDaddy API response body: {response_text}")
                    
                    # Handle rate limiting
                    if response_status == 429:
                        error_msg = "Rate limit exceeded for GoDaddy API"
                        logger.error(error_msg)
                        result['error'] = error_msg
                        result['confidence'] = 0.0
                        return result
                    
                    # Handle authentication errors
                    if response_status == 401:
                        error_msg = "Authentication failed for GoDaddy API"
                        logger.error(error_msg)
                        result['error'] = error_msg
                        result['confidence'] = 0.0
                        return result
                    
                    # Handle other errors
                    if response_status != 200:
                        error_msg = f"GoDaddy API error: {response_status} - {response_text}"
                        logger.error(error_msg)
                        result['error'] = error_msg
                        result['confidence'] = 0.0
                        return result
                    
                    # Parse response
                    try:
                        data = json.loads(response_text)
                        logger.info(f"GoDaddy API result for {domain}: available={data.get('available', False)}")
                        
                        # Update result
                        result['available'] = data.get('available', False)
                        result['confidence'] = 0.9  # High confidence for direct API response
                        result['details'] = {
                            'price': data.get('price', 0),
                            'currency': data.get('currency', 'USD'),
                            'definitive': data.get('definitive', True)
                        }
                        
                        # If the API specifically says the result is not definitive, lower confidence
                        if not data.get('definitive', True):
                            result['confidence'] = 0.7
                            
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse GoDaddy API response: {str(e)}"
                        logger.error(error_msg)
                        result['error'] = error_msg
                        result['confidence'] = 0.0
                        return result
                    
        except aiohttp.ClientError as e:
            error_msg = f"GoDaddy API connection error for {domain}: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            result['confidence'] = 0.0
        except Exception as e:
            error_msg = f"Error checking domain {domain} via GoDaddy API: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            result['confidence'] = 0.0
            
        logger.info(f"Final GoDaddy result for {domain}: {result}")
        return result


class NamecheapProvider(DomainSourceProvider):
    """
    Domain availability provider using Namecheap API.
    Note: This is a placeholder for future implementation.
    """
    
    def __init__(self, api_key: str = None, username: str = None, client_ip: str = None):
        """
        Initialize the Namecheap API provider.
        
        Args:
            api_key: Namecheap API key
            username: Namecheap username
            client_ip: Client IP address (required by Namecheap API)
        """
        self._source_name = "Namecheap"
        self._weight = 0.85  # Slightly lower than GoDaddy but higher than WHOIS
        self._api_key = api_key
        self._username = username
        self._client_ip = client_ip
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def weight(self) -> float:
        return self._weight
    
    async def check_availability(self, domain: str) -> Dict[str, Any]:
        """Check domain availability using Namecheap API."""
        # This is a placeholder for future implementation
        result = {
            'available': False,
            'confidence': 0.0,
            'source': self.source_name,
            'details': {},
            'error': "Namecheap API integration not implemented yet"
        }
        
        return result


def create_godaddy_provider() -> Optional[GoDaddyProvider]:
    """
    Create a GoDaddy provider using environment variables for credentials.
    Environment variables can be set directly or loaded from a .env file.
    
    Returns:
        GoDaddyProvider instance or None if credentials are not available
    """
    # If dotenv is available, it was already loaded at module import
    if DOTENV_AVAILABLE:
        logger.info("Dotenv support is enabled for credential loading")
    
    api_key = os.environ.get('GODADDY_API_KEY')
    api_secret = os.environ.get('GODADDY_API_SECRET')
    
    if not api_key or not api_secret:
        logger.warning("GoDaddy API credentials not found in environment variables or .env file")
        return None
    
    use_production = os.environ.get('GODADDY_USE_PRODUCTION', 'true').lower() == 'true'
    logger.info(f"Creating GoDaddy provider with {'production' if use_production else 'OTE'} environment")
    logger.info(f"API Key: {api_key[:5]}... API Secret: {api_secret[:5]}...")
    return GoDaddyProvider(api_key, api_secret, use_production)
