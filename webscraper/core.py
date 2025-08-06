import json
import time
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pyrate_limiter import Duration, Limiter, Rate

from .robots_checker import RobotsChecker
from .file_extractor import FileExtractor
from .api_client import APIClient
from .utils import is_same_domain, get_file_extension, setup_logging


class WebScraper:
    """Advanced web scraper with robots.txt compliance and file extraction."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the web scraper with configuration."""
        self.config = self._load_config(config_path)
        self.logger = setup_logging(self.config['logging'])
        
        self.robots_checker = RobotsChecker(self.config)
        self.file_extractor = FileExtractor(self.config)
        self.api_client = APIClient(self.config) if self.config['api']['enabled'] else None
        
        delay = self.config['crawling']['delay_between_requests']
        self.rate_limiter = Limiter(Rate(1, Duration.SECOND * delay))
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['general']['user_agent']
        })
        
        if not self.config['general'].get('verify_ssl', True):
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.logger.warning("SSL verification disabled - this reduces security!")
        
        self.visited_urls: Set[str] = set()
        self.results: List[Dict] = []
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make a rate-limited HTTP request."""
        try:
            self.rate_limiter.try_acquire("request")

            time.sleep(self.config['crawling']['delay_between_requests'])
            
            response = self.session.get(
                url,
                timeout=self.config['general']['timeout']
            )
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                self.logger.error(f"SSL certificate verification failed for {url}")
                self.logger.error("This website has SSL certificate issues.")
                if self.config['general'].get('allow_ssl_bypass', False):
                    self.logger.warning("Retrying with SSL verification disabled...")
                    try:
                        response = self.session.get(
                            url,
                            timeout=self.config['general']['timeout'],
                            verify=False
                        )
                        response.raise_for_status()
                        return response
                    except requests.RequestException as retry_e:
                        self.logger.error(f"Request still failed after SSL bypass: {retry_e}")
                        return None
                else:
                    self.logger.info("To bypass SSL verification, set 'allow_ssl_bypass': true in config.json")
                    self.logger.info("Or use --ssl-bypass flag in CLI (use with caution)")
            else:
                self.logger.error(f"SSL error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection failed for {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Request timeout for {url}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
    
    def scrape_url(self, 
                   url: str, 
                   nested: Optional[bool] = None, 
                   download: Optional[bool] = None, 
                   brute_force: Optional[bool] = None,
                   user_owns_site: bool = False) -> Dict:
        """
        Scrape a URL with optional nested link crawling and file download.
        
        Args:
            url: The URL to scrape
            nested: Override config for nested link crawling
            download: Override config for file downloading
            brute_force: Override config for ignoring robots.txt
            user_owns_site: User claims to own the site (bypasses robots.txt with disclaimer)
        
        Returns:
            Dictionary with scraping results
        """
        self.logger.info(f"Starting scrape for: {url}")
        
        if nested is not None:
            self.config['crawling']['nested_links'] = nested
        if download is not None:
            self.config['file_extraction']['download_files'] = download
        if brute_force is not None:
            self.config['general']['brute_force'] = brute_force

        if not self.config['general']['brute_force'] and not user_owns_site:
            robots_result = self.robots_checker.can_scrape(url)
            if not robots_result['allowed']:
                self.logger.warning(f"Robots.txt prevents scraping: {robots_result['reason']}")
                return {
                    'url': url,
                    'success': False,
                    'error': 'robots_txt_blocked',
                    'reason': robots_result['reason'],
                    'data': None
                }
        elif user_owns_site:
            self.logger.warning("DISCLAIMER: User claims site ownership. We are not responsible for any actions taken.")
        
        self.visited_urls.clear()
        self.results.clear()
        
        try:
            result = self._scrape_single_url(url, depth=0)
            
            if self.api_client and result['success']:
                self.api_client.send_data(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Scraping failed for {url}: {e}")
            return {
                'url': url,
                'success': False,
                'error': 'scraping_failed',
                'reason': str(e),
                'data': None
            }
    
    def _scrape_single_url(self, url: str, depth: int = 0) -> Dict:
        """Scrape a single URL and optionally its nested links."""
        if url in self.visited_urls:
            return {'url': url, 'success': False, 'reason': 'already_visited', 'data': None}
        
        if depth > self.config['crawling']['max_depth']:
            return {'url': url, 'success': False, 'reason': 'max_depth_reached', 'data': None}
        
        self.visited_urls.add(url)
        self.logger.info(f"Scraping URL (depth {depth}): {url}")
        
        response = self._make_request(url)
        if not response:
            return {'url': url, 'success': False, 'reason': 'request_failed', 'data': None}

        content_type = response.headers.get('content-type', '').lower()
        
        if 'text/html' in content_type:
            return self._process_html_content(url, response, depth)
        elif self.config['file_extraction']['download_files']:
            return self._process_file_content(url, response)
        else:
            return {'url': url, 'success': True, 'data': {'raw_content': response.text}}
    
    def _process_html_content(self, url: str, response: requests.Response, depth: int) -> Dict:
        """Process HTML content and extract nested links if configured."""
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            text_content = soup.get_text(strip=True)
            
            title = soup.title.string if soup.title else ""
            meta_description = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                meta_description = meta_tag.get('content', '') # type: ignore
            
            result = {
                'url': url,
                'success': True,
                'data': {
                    'title': title,
                    'meta_description': meta_description,
                    'text_content': text_content,
                    'word_count': len(text_content.split()),
                    'depth': depth
                }
            }
            
            if self.config['crawling']['nested_links'] and depth < self.config['crawling']['max_depth']:
                nested_results = self._extract_and_process_links(url, soup, depth + 1)
                result['data']['nested_pages'] = nested_results
            
            if self.config['file_extraction']['download_files']:
                file_results = self._extract_and_process_files(url, soup)
                result['data']['extracted_files'] = file_results
            
            return result
            
        except Exception as e:
            self.logger.error(f"HTML processing failed for {url}: {e}")
            return {'url': url, 'success': False, 'reason': f'html_processing_failed: {e}', 'data': None}
    
    def _extract_and_process_links(self, base_url: str, soup: BeautifulSoup, depth: int) -> List[Dict]:
        """Extract and process nested links from HTML."""
        nested_results = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href'] # type: ignore
            absolute_url = urljoin(base_url, href) # type: ignore
            
            if self.config['crawling']['same_domain_only'] and not is_same_domain(base_url, absolute_url):
                continue
            
            if absolute_url in self.visited_urls:
                continue
            
            if not absolute_url.startswith(('http://', 'https://')):
                continue
            
            nested_result = self._scrape_single_url(absolute_url, depth)
            if nested_result['success']:
                nested_results.append(nested_result)
        
        return nested_results
    
    def _extract_and_process_files(self, base_url: str, soup: BeautifulSoup) -> List[Dict]:
        """Extract and process downloadable files from HTML."""
        file_results = []
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href'] #type: ignore
            absolute_url = urljoin(base_url, str(href))
            file_ext = get_file_extension(absolute_url)
            
            if file_ext in self.config['file_extraction']['supported_extensions']:
                file_result = self._process_file_content(absolute_url, None)
                if file_result['success']:
                    file_results.append(file_result)
        
        return file_results
    
    def _process_file_content(self, url: str, response: Optional[requests.Response] = None) -> Dict:
        """Process file content and extract text."""
        if not response:
            response = self._make_request(url)
            if not response:
                return {'url': url, 'success': False, 'reason': 'download_failed', 'data': None}
        
        content_length = response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > self.config['file_extraction']['max_file_size_mb']:
                return {'url': url, 'success': False, 'reason': 'file_too_large', 'data': None}
        
        try:
            file_ext = get_file_extension(url)
            extracted_content = self.file_extractor.extract_content(response.content, file_ext)
            
            return {
                'url': url,
                'success': True,
                'data': {
                    'file_type': file_ext,
                    'content': extracted_content,
                    'size_bytes': len(response.content)
                }
            }
        
        except Exception as e:
            self.logger.error(f"File processing failed for {url}: {e}")
            return {'url': url, 'success': False, 'reason': f'file_processing_failed: {e}', 'data': None}
    
    def get_results(self) -> List[Dict]:
        """Get all scraping results."""
        return self.results
    
    def close(self):
        """Clean up resources."""
        self.session.close()