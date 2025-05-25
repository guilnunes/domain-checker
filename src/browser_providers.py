"""
GoDaddy Browser Automation Provider for domain availability checking.
This module provides a browser-based alternative to the GoDaddy API.
"""

import os
import re
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError

from .domain_checker import DomainSourceProvider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoDaddyBrowserProvider(DomainSourceProvider):
    """Domain availability provider using browser automation with GoDaddy's website."""
    
    # GoDaddy search URL
    SEARCH_URL = "https://www.godaddy.com/domainsearch/find"
    
    def __init__(self, headless: bool = True, timeout: int = 30, max_retries: int = 2):
        """
        Initialize the GoDaddy Browser provider.
        
        Args:
            headless: Whether to run browser in headless mode
            timeout: Timeout in seconds for page operations
            max_retries: Maximum number of retry attempts for failed operations
        """
        self._source_name = "GoDaddy"
        self._weight = 0.9  # Higher weight than WHOIS
        self._headless = headless
        self._timeout = timeout * 1000  # Convert to ms for Playwright
        self._max_retries = max_retries
        self._browser = None
        self._context = None
        
        logger.info(f"GoDaddy Browser provider initialized with headless={headless}, timeout={timeout}s")
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def weight(self) -> float:
        return self._weight
    
    async def _initialize_browser(self):
        """Initialize the browser if not already initialized."""
        if self._browser is None:
            logger.info("Initializing browser for GoDaddy checks")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            logger.info("Browser initialized successfully")
    
    async def _close_browser(self):
        """Close the browser and clean up resources."""
        if self._browser:
            logger.info("Closing browser")
            await self._context.close()
            await self._browser.close()
            await self._playwright.stop()
            self._browser = None
            self._context = None
            logger.info("Browser closed successfully")
    
    async def check_availability(self, domain: str) -> Dict[str, Any]:
        """Check domain availability using GoDaddy's website."""
        result = {
            'available': False,
            'confidence': 0.0,
            'source': self.source_name,
            'details': {},
            'error': None
        }
        
        logger.info(f"Checking domain availability via GoDaddy Browser: {domain}")
        
        try:
            # Initialize browser if needed
            await self._initialize_browser()
            
            # Create a new page
            page = await self._context.new_page()
            
            # Set default timeout
            page.set_default_timeout(self._timeout)
            
            # Navigate to GoDaddy search page
            logger.info(f"Navigating to GoDaddy search page: {self.SEARCH_URL}")
            await page.goto(self.SEARCH_URL)
            
            # Wait for the search input to be available
            logger.info("Waiting for search input field")
            await page.wait_for_selector('input[name="domainToCheck"]')
            
            # Clear any existing input and type the domain
            await page.fill('input[name="domainToCheck"]', domain)
            logger.info(f"Entered domain: {domain}")
            
            # Click the search button
            await page.click('button[type="submit"]')
            logger.info("Clicked search button")
            
            # Wait for results to load
            logger.info("Waiting for search results")
            await page.wait_for_selector('.domain-search-results', timeout=self._timeout)
            
            # Extract availability information
            availability_info = await self._extract_availability_info(page, domain)
            
            # Update result with extracted information
            result.update(availability_info)
            
            # Close the page
            await page.close()
            
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout while checking domain {domain} via GoDaddy Browser: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            result['confidence'] = 0.0
            
        except Exception as e:
            error_msg = f"Error checking domain {domain} via GoDaddy Browser: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            result['confidence'] = 0.0
            
        logger.info(f"Final GoDaddy Browser result for {domain}: {result}")
        return result
    
    async def _extract_availability_info(self, page: Page, domain: str) -> Dict[str, Any]:
        """Extract domain availability information from the GoDaddy search results page."""
        result = {
            'available': False,
            'confidence': 0.0,
            'details': {},
        }
        
        try:
            # Check if the domain is available
            available_selector = '.domain-search-results .domain-available'
            unavailable_selector = '.domain-search-results .domain-unavailable'
            
            is_available = await page.is_visible(available_selector, timeout=5000)
            is_unavailable = await page.is_visible(unavailable_selector, timeout=5000)
            
            if is_available:
                logger.info(f"Domain {domain} is available according to GoDaddy")
                result['available'] = True
                result['confidence'] = 0.9
                
                # Try to extract price information
                try:
                    price_element = await page.query_selector('.domain-available .price')
                    if price_element:
                        price_text = await price_element.text_content()
                        # Extract price using regex
                        price_match = re.search(r'(\$[\d,.]+)', price_text)
                        if price_match:
                            result['details']['price'] = price_match.group(1)
                except Exception as e:
                    logger.warning(f"Could not extract price for {domain}: {str(e)}")
                
            elif is_unavailable:
                logger.info(f"Domain {domain} is unavailable according to GoDaddy")
                result['available'] = False
                result['confidence'] = 0.9
                
                # Try to extract "for sale" information if available
                try:
                    for_sale_element = await page.query_selector('.domain-unavailable .for-sale')
                    if for_sale_element:
                        for_sale_text = await for_sale_element.text_content()
                        result['details']['for_sale'] = True
                        result['details']['for_sale_info'] = for_sale_text.strip()
                except Exception as e:
                    logger.warning(f"Could not extract 'for sale' info for {domain}: {str(e)}")
            else:
                logger.warning(f"Could not determine availability for {domain}")
                result['confidence'] = 0.5
                result['details']['indeterminate'] = True
            
            # Try to extract alternative suggestions
            try:
                suggestions = []
                suggestion_elements = await page.query_selector_all('.domain-suggestions .domain-name')
                for element in suggestion_elements[:5]:  # Limit to 5 suggestions
                    suggestion_text = await element.text_content()
                    suggestions.append(suggestion_text.strip())
                
                if suggestions:
                    result['details']['suggestions'] = suggestions
            except Exception as e:
                logger.warning(f"Could not extract suggestions for {domain}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error extracting availability info for {domain}: {str(e)}")
            result['confidence'] = 0.3
            
        return result
    
    async def __del__(self):
        """Destructor to ensure browser is closed."""
        await self._close_browser()


def create_godaddy_browser_provider(headless: bool = True, timeout: int = 30, max_retries: int = 2) -> GoDaddyBrowserProvider:
    """
    Create a GoDaddy Browser provider with the specified configuration.
    
    Args:
        headless: Whether to run browser in headless mode
        timeout: Timeout in seconds for page operations
        max_retries: Maximum number of retry attempts for failed operations
        
    Returns:
        GoDaddyBrowserProvider instance
    """
    logger.info(f"Creating GoDaddy Browser provider with headless={headless}, timeout={timeout}s")
    return GoDaddyBrowserProvider(headless=headless, timeout=timeout, max_retries=max_retries)
