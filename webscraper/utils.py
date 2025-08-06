import os
import sys
import logging
import requests
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, urljoin


def setup_logging(logging_config: Dict) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        logging_config: Dictionary with logging configuration
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('webscraper')
    logger.setLevel(getattr(logging, logging_config.get('level', 'INFO')))
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    formatter = logging.Formatter(
        logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if logging_config.get('file'):
        try:
            file_handler = logging.FileHandler(logging_config['file'])
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create file handler for {logging_config['file']}: {e}")
    
    return logger


def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs belong to the same domain.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if same domain, False otherwise
    """
    try:
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        
        domain1 = domain1.replace('www.', '')
        domain2 = domain2.replace('www.', '')
        
        return domain1 == domain2
    
    except Exception:
        return False


def get_file_extension(url: str) -> str:
    """
    Extract file extension from URL.
    
    Args:
        url: The URL to extract extension from
        
    Returns:
        File extension including the dot (e.g., '.pdf')
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        if '?' in path:
            path = path.split('?')[0]
        if '#' in path:
            path = path.split('#')[0]
        
        extension = Path(path).suffix.lower()
        return extension if extension else ''
    
    except Exception:
        return ''


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid and accessible.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
    except Exception:
        return False


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    Normalize a URL by resolving relative URLs and cleaning up.
    
    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs
        
    Returns:
        Normalized absolute URL
    """
    try:
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        
        parsed = urlparse(url)
        
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    except Exception:
        return url


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length
        
    Returns:
        Sanitized filename
    """
    import re
    
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
    
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        available_length = max_length - len(ext)
        sanitized = name[:available_length] + ext
    
    return sanitized


def get_content_type(url: str, timeout: int = 10) -> str:
    """
    Get the content type of a URL without downloading the full content.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        Content type string
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.headers.get('content-type', '').lower()
    except Exception:
        return ''


def estimate_download_time(url: str, connection_speed_mbps: float = 10.0, timeout: int = 10) -> float:
    """
    Estimate download time for a file based on its size and connection speed.
    
    Args:
        url: URL to check
        connection_speed_mbps: Connection speed in Mbps
        timeout: Request timeout in seconds
        
    Returns:
        Estimated download time in seconds, or -1 if unable to determine
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        content_length = response.headers.get('content-length')
        
        if content_length:
            size_bytes = int(content_length)
            size_megabits = (size_bytes * 8) / (1024 * 1024)
            estimated_seconds = size_megabits / connection_speed_mbps
            return estimated_seconds
        
        return -1
    
    except Exception:
        return -1


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length while preserving word boundaries.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + suffix


def extract_domain(url: str) -> str:
    """
    Extract domain name from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    
    except Exception:
        return ''


def is_binary_content(content_type: str) -> bool:
    """
    Check if content type represents binary content.
    
    Args:
        content_type: MIME type string
        
    Returns:
        True if binary, False if text-based
    """
    text_types = [
        'text/',
        'application/json',
        'application/xml',
        'application/xhtml+xml',
        'application/rss+xml',
        'application/atom+xml'
    ]
    
    content_type_lower = content_type.lower()
    
    for text_type in text_types:
        if content_type_lower.startswith(text_type):
            return False
    
    return True


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing line breaks.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    import re
    
    if not text:
        return ""
    
    text = re.sub(r'\r\n|\r|\n', '\n', text)
    
    text = re.sub(r'[ \t]+', ' ', text)
    
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    text = text.strip()
    
    return text


def format_file_size(size_bytes: float) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def validate_config(config: Dict) -> list[str]:
    """
    Validate configuration and return list of errors.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    required_sections = ['general', 'crawling', 'file_extraction', 'llm', 'api', 'logging']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required configuration section: {section}")
    
    if 'general' in config:
        general = config['general']
        if not isinstance(general.get('timeout'), (int, float)) or general.get('timeout') <= 0:
            errors.append("Invalid timeout value in general settings")
        
        if not isinstance(general.get('max_retries'), int) or general.get('max_retries') < 0:
            errors.append("Invalid max_retries value in general settings")
    
    if 'crawling' in config:
        crawling = config['crawling']
        if not isinstance(crawling.get('max_depth'), int) or crawling.get('max_depth') < 0:
            errors.append("Invalid max_depth value in crawling settings")
        
        if not isinstance(crawling.get('delay_between_requests'), (int, float)) or crawling.get('delay_between_requests') < 0:
            errors.append("Invalid delay_between_requests value in crawling settings")
    
    if 'file_extraction' in config:
        file_config = config['file_extraction']
        if not isinstance(file_config.get('max_file_size_mb'), (int, float)) or file_config.get('max_file_size_mb') <= 0:
            errors.append("Invalid max_file_size_mb value in file_extraction settings")
    
    if 'api' in config and config['api'].get('enabled'):
        api = config['api']
        if not api.get('endpoint'):
            errors.append("API endpoint is required when API is enabled")
        
        if api.get('method') and api['method'].upper() not in ['GET', 'POST', 'PUT', 'PATCH']:
            errors.append("Invalid API method. Must be GET, POST, PUT, or PATCH")
    
    return errors