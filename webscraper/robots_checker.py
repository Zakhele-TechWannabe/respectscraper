import logging
import requests
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from .llm_client import LLMClient


class RobotsChecker:
    """Handles robots.txt checking and compliance verification."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.llm_client = LLMClient(config) if config['llm']['api_key'] else None
        self.user_agent = config['general']['user_agent']
        
    def can_scrape(self, url: str) -> Dict:
        """
        Check if scraping is allowed for the given URL.
        
        Returns:
            Dict with 'allowed' (bool), 'reason' (str), and 'robots_txt_content' (str)
        """
        try:
            robots_url = self._get_robots_url(url)
            robots_content = self._fetch_robots_txt(robots_url)
            
            if not robots_content:
                # No robots.txt found - allowed by default
                return {
                    'allowed': True,
                    'reason': 'No robots.txt found',
                    'robots_txt_content': None
                }
            
            # Parse robots.txt
            parser_result = self._parse_robots_txt(robots_url, url)
            
            if parser_result['is_clear']:
                return {
                    'allowed': parser_result['allowed'],
                    'reason': parser_result['reason'],
                    'robots_txt_content': robots_content
                }
            
            # If unclear, use LLM for interpretation
            if self.llm_client:
                llm_result = self._ask_llm_about_robots(robots_content, url)
                return {
                    'allowed': llm_result['allowed'],
                    'reason': f"LLM interpretation: {llm_result['reason']}",
                    'robots_txt_content': robots_content
                }
            else:
                # No LLM available, err on the side of caution
                return {
                    'allowed': False,
                    'reason': 'Robots.txt is unclear and no LLM configured for interpretation',
                    'robots_txt_content': robots_content
                }
                
        except Exception as e:
            self.logger.error(f"Error checking robots.txt for {url}: {e}")
            return {
                'allowed': False,
                'reason': f'Error checking robots.txt: {str(e)}',
                'robots_txt_content': None
            }
    
    def _get_robots_url(self, url: str) -> str:
        """Get the robots.txt URL for the given URL."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(base_url, '/robots.txt')
    
    def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        """Fetch the robots.txt content."""
        try:
            # Configure SSL verification based on config
            verify_ssl = self.config['general'].get('verify_ssl', True)
            
            response = requests.get(
                robots_url,
                timeout=self.config['general']['timeout'],
                headers={'User-Agent': self.user_agent},
                verify=verify_ssl
            )
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                return None  # No robots.txt found
            else:
                self.logger.warning(f"Unexpected status code {response.status_code} for {robots_url}")
                return None
                
        except requests.exceptions.SSLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                self.logger.warning(f"SSL certificate verification failed for robots.txt: {robots_url}")
                if self.config['general'].get('allow_ssl_bypass', False):
                    self.logger.warning("Retrying robots.txt fetch with SSL verification disabled...")
                    try:
                        response = requests.get(
                            robots_url,
                            timeout=self.config['general']['timeout'],
                            headers={'User-Agent': self.user_agent},
                            verify=False
                        )
                        if response.status_code == 200:
                            return response.text
                        elif response.status_code == 404:
                            return None
                    except requests.RequestException as retry_e:
                        self.logger.error(f"Robots.txt fetch still failed after SSL bypass: {retry_e}")
                else:
                    self.logger.info("To bypass SSL issues for robots.txt, set 'allow_ssl_bypass': true in config")
            return None
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return None
    
    def _parse_robots_txt(self, robots_url: str, target_url: str) -> Dict:
        """
        Parse robots.txt using Python's built-in parser.
        
        Returns:
            Dict with 'allowed' (bool), 'is_clear' (bool), and 'reason' (str)
        """
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            # Handle SSL issues for robots.txt parsing
            if not self.config['general'].get('verify_ssl', True):
                import ssl
                import urllib.request
                # Create SSL context that doesn't verify certificates
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Install custom opener
                opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
                urllib.request.install_opener(opener)
            
            rp.read()
            
            # Check if our user agent can fetch the URL
            can_fetch = rp.can_fetch(self.user_agent, target_url)
            
            # Try to determine if the result is clear or ambiguous
            # This is a simple heuristic - in practice, robots.txt can be complex
            is_clear = True
            reason = ""
            
            if can_fetch:
                reason = f"Robots.txt allows access for user agent '{self.user_agent}'"
            else:
                reason = f"Robots.txt disallows access for user agent '{self.user_agent}'"
            
            # Check for complex patterns that might need LLM interpretation
            try:
                robots_content_response = requests.get(
                    robots_url, 
                    verify=self.config['general'].get('verify_ssl', True)
                )
                robots_content = robots_content_response.text.lower()
                complexity_indicators = [
                    'crawl-delay' in robots_content,
                    'request-rate' in robots_content,
                    '*' in robots_content and 'disallow' in robots_content,
                    len([line for line in robots_content.split('\n') if line.strip().startswith('disallow:')]) > 5
                ]
                
                if any(complexity_indicators):
                    is_clear = False
                    reason += " (but robots.txt contains complex rules that may need interpretation)"
            except:
                # If we can't fetch for complexity check, assume it's clear
                pass
            
            return {
                'allowed': can_fetch,
                'is_clear': is_clear,
                'reason': reason
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing robots.txt: {e}")
            return {
                'allowed': False,
                'is_clear': False,
                'reason': f"Error parsing robots.txt: {str(e)}"
            }
    
    def _ask_llm_about_robots(self, robots_content: str, target_url: str) -> Dict:
        """Ask LLM to interpret ambiguous robots.txt content."""
        prompt = f"""
Please analyze the following robots.txt file and determine if web scraping is allowed for the URL: {target_url}

The user agent being used is: {self.user_agent}

robots.txt content:
{robots_content}

Please respond with a JSON object containing:
- "allowed": boolean (true if scraping is allowed, false if not)
- "reason": string explaining your decision
- "confidence": number between 0-1 indicating your confidence in this interpretation

Consider:
1. Specific user agent rules that apply to '{self.user_agent}'
2. Wildcard (*) user agent rules
3. Disallow and Allow directives
4. Any crawl-delay or request-rate limitations
5. The specific path being accessed: {urlparse(target_url).path}

Be conservative - if there's ambiguity, err on the side of not allowing scraping.
"""
        
        try:
            response = self.llm_client.query(prompt) # type: ignore
            
            if response and 'allowed' in response:
                return {
                    'allowed': response['allowed'],
                    'reason': response.get('reason', 'LLM interpretation'),
                    'confidence': response.get('confidence', 0.5)
                }
            else:
                return {
                    'allowed': False,
                    'reason': 'LLM failed to provide clear interpretation',
                    'confidence': 0.0
                }
                
        except Exception as e:
            self.logger.error(f"LLM interpretation failed: {e}")
            return {
                'allowed': False,
                'reason': f'LLM interpretation failed: {str(e)}',
                'confidence': 0.0
            }
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get the crawl delay specified in robots.txt for our user agent."""
        try:
            robots_url = self._get_robots_url(url)
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            # Get crawl delay
            delay = rp.crawl_delay(self.user_agent)
            return float(delay) if delay else None
            
        except Exception as e:
            self.logger.error(f"Error getting crawl delay: {e}")
            return None
    
    def get_request_rate(self, url: str) -> Optional[tuple]:
        """Get the request rate specified in robots.txt for our user agent."""
        try:
            robots_url = self._get_robots_url(url)
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            # Get request rate (requests, seconds)
            rate = rp.request_rate(self.user_agent)
            return rate if rate else None
            
        except Exception as e:
            self.logger.error(f"Error getting request rate: {e}")
            return None