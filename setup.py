"""
Setup script for Advanced Web Scraper.
"""
from setuptools import setup, find_packages

def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="respectscraper",
    version="0.1.0",
    author="Your Name",
    author_email="info@zakhelegamede.com",
    description="Ethical web scraper with robots.txt compliance, AI-powered interpretation, and comprehensive content extraction",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Zakhele-TechWannabe/respectscraper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
    },
    entry_points={
        "console_scripts": [
            "respectscraper=webscraper.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="webscraper, scraping, robots.txt, pdf, excel, word, ai, llm, ethical, respectful",
    project_urls={
        "Bug Reports": "https://github.com/Zakhele-TechWannabe/respectscraper/issues",
        "Source": "https://github.com/Zakhele-TechWannabe/respectscraper",
        "Documentation": "https://github.com/Zakhele-TechWannabe/respectscraper/wiki",
    },
)