#!/usr/bin/env python3
"""
Command-line interface for the Advanced Web Scraper.
"""

import argparse
import json
import sys
from typing import Optional
from pathlib import Path

from . import WebScraper, create_default_config, validate_installation, get_info
from .utils import is_valid_url, validate_config


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == 'scrape':
        run_scrape_command(args)
    elif args.command == 'config':
        run_config_command(args)
    elif args.command == 'validate':
        run_validate_command(args)
    elif args.command == 'info':
        run_info_command(args)
    else:
        parser.print_help()


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="RespectScraper - Ethical web scraping with robots.txt compliance and AI interpretation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  respectscraper scrape https://example.com
  respectscraper scrape https://example.com --nested --download
  respectscraper scrape https://example.com --config my_config.json --brute-force
  respectscraper scrape https://example.com --ssl-bypass  # For SSL certificate issues
  respectscraper config --create
  respectscraper validate
  respectscraper info
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape a website')
    scrape_parser.add_argument('url', help='URL to scrape')
    scrape_parser.add_argument('--config', '-c', default='config.json',
                              help='Path to configuration file (default: config.json)')
    scrape_parser.add_argument('--nested', '-n', action='store_true',
                              help='Enable nested link crawling')
    scrape_parser.add_argument('--download', '-d', action='store_true',
                              help='Enable file downloading and extraction')
    scrape_parser.add_argument('--brute-force', '-f', action='store_true',
                              help='Ignore robots.txt restrictions')
    scrape_parser.add_argument('--user-owns-site', action='store_true',
                              help='User claims to own the site (bypasses robots.txt)')
    scrape_parser.add_argument('--ssl-bypass', action='store_true',
                              help='Bypass SSL certificate verification (use with caution)')
    scrape_parser.add_argument('--output', '-o', 
                              help='Output file to save results (JSON format)')
    scrape_parser.add_argument('--pretty', action='store_true',
                              help='Pretty print JSON output')
    scrape_parser.add_argument('--quiet', '-q', action='store_true',
                              help='Suppress progress output')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('--create', action='store_true',
                              help='Create default configuration file')
    config_parser.add_argument('--path', default='config.json',
                              help='Configuration file path (default: config.json)')
    config_parser.add_argument('--validate', action='store_true',
                              help='Validate existing configuration file')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate installation')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show package information')
    
    return parser


def run_scrape_command(args):
    """Run the scrape command."""
    # Validate URL
    if not is_valid_url(args.url):
        print(f"Error: Invalid URL: {args.url}", file=sys.stderr)
        sys.exit(1)
    
    # Check if config file exists
    if not Path(args.config).exists():
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        print(f"Create one using: respectscraper config --create --path {args.config}")
        sys.exit(1)
    
    try:
        # Initialize scraper
        scraper = WebScraper(args.config)
        
        # Apply SSL bypass if requested
        if args.ssl_bypass:
            scraper.config['general']['allow_ssl_bypass'] = True
            scraper.config['general']['verify_ssl'] = False
            # Reconfigure session for SSL bypass
            scraper.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            if not args.quiet:
                print("⚠️  SSL verification disabled - use with caution!")
        
        if not args.quiet:
            print(f"Starting scrape for: {args.url}")
            if args.nested:
                print("  - Nested link crawling: ENABLED")
            if args.download:
                print("  - File downloading: ENABLED")
            if args.brute_force:
                print("  - Brute force mode: ENABLED (ignoring robots.txt)")
            if args.user_owns_site:
                print("  - User owns site: ENABLED (bypassing robots.txt)")
            if args.ssl_bypass:
                print("  - SSL bypass: ENABLED (certificates not verified)")
            print()
        
        # Perform scraping
        result = scraper.scrape_url(
            url=args.url,
            nested=args.nested,
            download=args.download,
            brute_force=args.brute_force,
            user_owns_site=args.user_owns_site
        )
        
        # Clean up
        scraper.close()
        
        # Output results
        output_json = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)
        
        if args.output:
            # Save to file
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_json)
                if not args.quiet:
                    print(f"Results saved to: {args.output}")
            except IOError as e:
                print(f"Error saving to file {args.output}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Print to stdout
            print(output_json)
        
        # Print summary if not quiet
        if not args.quiet:
            print(f"\nScraping completed. Success: {result['success']}")
            if not result['success']:
                print(f"Reason: {result.get('reason', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error during scraping: {e}", file=sys.stderr)
        sys.exit(1)


def run_config_command(args):
    """Run the config command."""
    if args.create:
        # Create default configuration
        if Path(args.path).exists():
            response = input(f"Configuration file {args.path} already exists. Overwrite? [y/N]: ")
            if response.lower() != 'y':
                print("Configuration creation cancelled.")
                return
        
        if create_default_config(args.path):
            print(f"Default configuration created: {args.path}")
            print("\nIMPORTANT: Please edit the configuration file to:")
            print("  - Set your LLM API key (if using LLM features)")
            print("  - Configure API endpoint (if using API integration)")
            print("  - Adjust scraping parameters as needed")
        else:
            print(f"Error: Failed to create configuration file: {args.path}", file=sys.stderr)
            sys.exit(1)
    
    elif args.validate:
        # Validate configuration
        if not Path(args.path).exists():
            print(f"Error: Configuration file not found: {args.path}", file=sys.stderr)
            sys.exit(1)
        
        try:
            with open(args.path, 'r') as f:
                config = json.load(f)
            
            errors = validate_config(config)
            
            if errors:
                print(f"Configuration validation failed for {args.path}:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print(f"Configuration file {args.path} is valid!")
        
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error validating configuration: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        print("Please specify --create or --validate option.")
        sys.exit(1)


def run_validate_command(args):
    """Run the validate command."""
    print("Validating Advanced Web Scraper installation...")
    print()
    
    results = validate_installation()
    
    print("Package Information:")
    info = get_info()
    for key, value in info.items():
        print(f"  {key.title()}: {value}")
    print()
    
    print("Dependency Check:")
    if results['valid']:
        print("  ✓ All required packages are installed")
    else:
        print("  ✗ Some packages are missing")
    
    print("\nInstalled Packages:")
    for package, version in results['version_info'].items():
        status = "✓" if package not in results['missing_packages'] else "✗"
        print(f"  {status} {package}: {version}")
    
    if results['missing_packages']:
        print(f"\nMissing Packages: {', '.join(results['missing_packages'])}")
    
    print("\nRecommendations:")
    for recommendation in results['recommendations']:
        print(f"  - {recommendation}")
    
    if not results['valid']:
        sys.exit(1)


def run_info_command(args):
    """Run the info command."""
    info = get_info()
    
    print("RespectScraper - Ethical Web Scraping")
    print("=" * 50)
    print(f"Version: {info['version']}")
    print(f"Author: {info['author']}")
    print(f"Email: {info['email']}")
    print(f"Description: {info['description']}")
    print()
    
    print("Features:")
    print("  • Robots.txt compliance checking with AI interpretation")
    print("  • LLM integration for ambiguous robots.txt files")
    print("  • Nested link crawling with depth control")
    print("  • File extraction (PDF, Excel, Word, Text)")
    print("  • Rate limiting and respectful scraping")
    print("  • API integration for data storage")
    print("  • Ethical override options with disclaimers")
    print("  • Configurable via JSON configuration")
    print("  • Comprehensive command-line interface")
    print()
    
    print("Usage Examples:")
    print("  respectscraper scrape https://example.com")
    print("  respectscraper scrape https://example.com --nested --download")
    print("  respectscraper config --create")
    print("  respectscraper validate")
    print()
    
    print("Configuration:")
    print("  Create a default config: respectscraper config --create")
    print("  Edit config.json to customize behavior")
    print("  Set LLM API keys for robots.txt interpretation")
    print("  Configure API endpoints for data storage")


if __name__ == '__main__':
    main()