"""
Multi-source domain availability checker core implementation.
This module provides the foundation for checking domain availability from multiple sources.
"""

import abc
import asyncio
import time
import re
import whois
import logging
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DomainSourceProvider(abc.ABC):
    """Base abstract class for domain availability source providers."""
    
    @abc.abstractmethod
    async def check_availability(self, domain: str) -> Dict[str, Any]:
        """
        Check domain availability from this source
        
        Args:
            domain (str): The domain to check
            
        Returns:
            dict: {
                'available': bool,  # True if available, False if not
                'confidence': float,  # 0.0-1.0 confidence score
                'source': str,  # Name of the source
                'details': dict,  # Source-specific details
                'error': str  # Error message if any, None otherwise
            }
        """
        pass
    
    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Return the name of this source provider."""
        pass
    
    @property
    @abc.abstractmethod
    def weight(self) -> float:
        """Return the weight of this source in the reconciliation algorithm."""
        pass


class WhoisProvider(DomainSourceProvider):
    """Domain availability provider using WHOIS protocol."""
    
    def __init__(self):
        self._source_name = "WHOIS"
        self._weight = 0.6  # Lower weight than registrar APIs
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def weight(self) -> float:
        return self._weight
    
    async def check_availability(self, domain: str) -> Dict[str, Any]:
        """Check domain availability using WHOIS."""
        result = {
            'available': False,
            'confidence': 0.0,
            'source': self.source_name,
            'details': {},
            'error': None
        }
        
        try:
            # Add a small delay to avoid rate limiting
            await asyncio.sleep(0.5)
            
            # Query WHOIS
            domain_info = whois.whois(domain)
            
            # Process the result
            if domain_info.status is None or domain_info.domain_name is None:
                result['available'] = True
                result['confidence'] = 0.7  # Moderate confidence for available domains
                result['details'] = {'raw_response': str(domain_info)}
            else:
                result['available'] = False
                result['confidence'] = 0.8  # Higher confidence for unavailable domains
                result['details'] = {
                    'status': str(domain_info.status),
                    'registrar': str(domain_info.registrar),
                    'creation_date': str(domain_info.creation_date),
                    'expiration_date': str(domain_info.expiration_date),
                    'raw_response': str(domain_info)
                }
                
        except Exception as e:
            error_msg = f"Error checking domain {domain} via WHOIS: {str(e)}"
            logger.error(error_msg)
            result['confidence'] = 0.3  # Low confidence due to error
            result['error'] = error_msg
            
        return result


class DomainChecker:
    """
    Core domain checker that orchestrates checks across multiple sources
    and reconciles the results.
    """
    
    def __init__(self):
        self.providers = []
        # Add the WHOIS provider by default
        self.add_provider(WhoisProvider())
    
    def add_provider(self, provider: DomainSourceProvider) -> None:
        """Add a domain source provider to the checker."""
        self.providers.append(provider)
        logger.info(f"Added provider: {provider.source_name} with weight {provider.weight}")
    
    async def check_domain(self, domain: str) -> Dict[str, Any]:
        """
        Check domain availability across all providers and reconcile results.
        
        Args:
            domain (str): The domain to check
            
        Returns:
            dict: Reconciled result with all source details
        """
        # Normalize domain
        domain = self._normalize_domain(domain)
        
        # Check with all providers in parallel
        tasks = [provider.check_availability(domain) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Provider {self.providers[i].source_name} raised exception: {str(result)}")
                processed_results.append({
                    'available': None,
                    'confidence': 0.0,
                    'source': self.providers[i].source_name,
                    'details': {},
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        # Reconcile the results
        reconciled = self._reconcile_results(processed_results)
        
        # Add all source results for transparency
        reconciled['sources'] = processed_results
        
        return reconciled
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain name for checking."""
        # Convert to lowercase
        domain = domain.lower()
        
        # Remove any protocol prefixes
        domain = re.sub(r'^https?://', '', domain)
        
        # Remove www. prefix if present
        domain = re.sub(r'^www\.', '', domain)
        
        # Remove any trailing paths
        domain = domain.split('/')[0]
        
        return domain
    
    def _reconcile_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reconcile results from multiple sources using a weighted algorithm.
        
        Args:
            results: List of results from different providers
            
        Returns:
            dict: Reconciled result
        """
        # Initialize the reconciled result
        reconciled = {
            'available': None,
            'confidence': 0.0,
            'sources_checked': len(results),
            'sources_with_errors': 0,
            'conflicting_results': False
        }
        
        # Count errors
        errors = [r for r in results if r['error'] is not None]
        reconciled['sources_with_errors'] = len(errors)
        
        # If all sources had errors, we can't determine availability
        if len(errors) == len(results):
            reconciled['available'] = None
            reconciled['confidence'] = 0.0
            reconciled['status'] = 'unknown'
            return reconciled
        
        # Filter out error results
        valid_results = [r for r in results if r['error'] is None]
        
        # Check if all valid results agree
        availabilities = [r['available'] for r in valid_results]
        all_agree = all(a == availabilities[0] for a in availabilities)
        
        if all_agree:
            # All sources agree
            reconciled['available'] = availabilities[0]
            # Average confidence weighted by provider weight
            total_weight = sum(self._get_provider_weight(r['source']) for r in valid_results)
            weighted_confidence = sum(r['confidence'] * self._get_provider_weight(r['source']) 
                                     for r in valid_results)
            reconciled['confidence'] = weighted_confidence / total_weight if total_weight > 0 else 0.5
            reconciled['status'] = 'available' if reconciled['available'] else 'unavailable'
        else:
            # Sources disagree - prioritize registrar APIs over WHOIS
            reconciled['conflicting_results'] = True
            
            # Group by source type
            registrar_results = [r for r in valid_results if r['source'] != 'WHOIS']
            whois_results = [r for r in valid_results if r['source'] == 'WHOIS']
            
            if registrar_results:
                # Prioritize registrar API results
                registrar_weights = [self._get_provider_weight(r['source']) for r in registrar_results]
                registrar_availabilities = [r['available'] for r in registrar_results]
                
                # Weighted vote among registrar APIs
                weighted_votes = {}
                for i, avail in enumerate(registrar_availabilities):
                    weighted_votes[avail] = weighted_votes.get(avail, 0) + registrar_weights[i]
                
                # Get the availability with the highest weighted vote
                reconciled['available'] = max(weighted_votes.items(), key=lambda x: x[1])[0]
                reconciled['confidence'] = 0.7  # Medium-high confidence for registrar API with conflicts
                reconciled['status'] = 'available' if reconciled['available'] else 'unavailable'
                reconciled['status'] += '_conflicted'
            else:
                # Only WHOIS results with conflicts (unusual case)
                # Take the majority vote
                true_votes = sum(1 for r in whois_results if r['available'])
                false_votes = len(whois_results) - true_votes
                
                reconciled['available'] = true_votes > false_votes
                reconciled['confidence'] = 0.5  # Medium confidence for conflicting WHOIS
                reconciled['status'] = 'available' if reconciled['available'] else 'unavailable'
                reconciled['status'] += '_uncertain'
        
        return reconciled
    
    def _get_provider_weight(self, source_name: str) -> float:
        """Get the weight of a provider by its source name."""
        for provider in self.providers:
            if provider.source_name == source_name:
                return provider.weight
        return 0.5  # Default weight if provider not found


class DomainSuggestionGenerator:
    """Generate alternative domain suggestions."""
    
    @staticmethod
    def generate_suggestions(brand: str, tlds: List[str], max_suggestions: int = 10) -> List[str]:
        """
        Generate alternative domain suggestions.
        
        Args:
            brand: The brand name
            tlds: List of TLDs to use for suggestions
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of domain suggestions
        """
        suggestions = []
        
        # Prefixes to try
        prefixes = ['get', 'try', 'use', 'my', 'the']
        
        # Suffixes to try
        suffixes = ['app', 'site', 'online', 'digital', 'web']
        
        # Generate suggestions with prefixes
        for prefix in prefixes:
            for tld in tlds:
                suggestions.append(f"{prefix}{brand}{tld}")
                if len(suggestions) >= max_suggestions:
                    return suggestions
        
        # Generate suggestions with suffixes
        for suffix in suffixes:
            for tld in tlds:
                suggestions.append(f"{brand}{suffix}{tld}")
                if len(suggestions) >= max_suggestions:
                    return suggestions
        
        # Add hyphenated version if brand is long enough
        if len(brand) > 5:
            middle = len(brand) // 2
            hyphenated = f"{brand[:middle]}-{brand[middle:]}"
            for tld in tlds:
                suggestions.append(f"{hyphenated}{tld}")
                if len(suggestions) >= max_suggestions:
                    return suggestions
        
        return suggestions[:max_suggestions]


def normalize_brand_name(brand_name: str) -> str:
    """Normalize brand name for domain use (remove spaces, special chars, etc.)"""
    # Convert to lowercase
    normalized = brand_name.lower()
    
    # Remove special characters and spaces
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    
    return normalized
