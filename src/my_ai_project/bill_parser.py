import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, AsyncIterator
import re
from dataclasses import dataclass
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

@dataclass
class BillSection:
    number: str
    title: str
    text: str
    level: int
    parent_section: str = None

class CongressBillParser:
    API_BASE_URL = "https://api.congress.gov/v3"
    
    def __init__(self):
        self.session = None
        self.api_key = os.getenv("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError("CONGRESS_API_KEY environment variable not set")
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _parse_congress_url(self, url: str) -> tuple:
        """Extract bill info from congress.gov URL"""
        pattern = r"/bill/(\d+)(?:st|nd|rd|th)-congress/([^/]+)/([^/]+)"
        match = re.search(pattern, url)
        if not match:
            raise ValueError("Invalid congress.gov bill URL")
        congress, chamber, number = match.groups()
        # Convert chamber format (e.g., "house-bill" to "hr")
        if chamber == "house-bill":
            chamber = "hr"
        elif chamber == "senate-bill":
            chamber = "s"
        return congress, chamber, number.split("-")[0]
    
    async def fetch_bill_details(self, congress: str, bill_type: str, number: str) -> Dict:
        """Fetch bill details from congress.gov API"""
        params = {"api_key": self.api_key}
        url = f"{self.API_BASE_URL}/bill/{congress}/{bill_type}/{number}"
        print(f"Fetching bill details from: {url}")
        
        async with self.session.get(f"{url}?{urlencode(params)}") as response:
            response.raise_for_status()
            data = await response.json()
            return data.get('bill', {})
    
    async def fetch_bill_text_urls(self, congress: str, bill_type: str, number: str) -> Dict:
        """Fetch bill text version URLs"""
        params = {"api_key": self.api_key}
        url = f"{self.API_BASE_URL}/bill/{congress}/{bill_type}/{number}/text"
        print(f"Fetching text versions from: {url}")
        
        async with self.session.get(f"{url}?{urlencode(params)}") as response:
            response.raise_for_status()
            data = await response.json()
            
            if not data.get('textVersions'):
                raise ValueError("No text versions found")
            
            # Get the latest version
            latest_version = data['textVersions'][0]
            
            # Find the formatted text URL
            for fmt in latest_version.get('formats', []):
                if fmt.get('type') == 'Formatted Text':
                    return fmt['url']
            
            raise ValueError("No formatted text URL found")
    
    async def fetch_bill_text(self, text_url: str) -> str:
        """Fetch actual bill text content"""
        print(f"Fetching bill text from: {text_url}")
        
        async with self.session.get(text_url) as response:
            response.raise_for_status()
            html = await response.text()
            
            # Parse HTML to get text content
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for elem in soup.select('script, style, meta, link'):
                elem.decompose()
            
            # Get the main content
            content = soup.find('pre') or soup.find('div', class_='generated-html-container')
            if not content:
                raise ValueError("Could not find bill text content")
            
            return content.get_text()
    
    def _clean_text(self, text: str) -> str:
        """Clean up extracted text"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def _extract_section_info(self, header: str) -> tuple:
        """Extract section number and title from header"""
        match = re.match(r'SEC[.]?\s*(\d+[a-zA-Z0-9-]*)[.\s]*(.+)', header, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2).strip()
        return None, header.strip()
    
    def _parse_text_into_sections(self, text: str) -> List[Dict]:
        """Parse text into sections"""
        sections = []
        current_section = None
        
        # Split text into lines and process
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a section header
            if re.match(r'SEC[.]?\s*\d+', line, re.IGNORECASE):
                # If we have a current section, save it
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                section_num, section_title = self._extract_section_info(line)
                current_section = {
                    "number": section_num,
                    "title": section_title,
                    "text": [],
                    "level": 1  # Default level
                }
            elif current_section:
                # Add line to current section
                current_section["text"].append(line)
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    async def parse_bill(self, url: str) -> AsyncIterator[Dict]:
        """Parse bill text and yield sections"""
        # Get bill identifiers
        congress, bill_type, number = self._parse_congress_url(url)
        
        # Get bill details first
        bill_data = await self.fetch_bill_details(congress, bill_type, number)
        print(f"Processing bill: {bill_data.get('title', 'Unknown Title')}")
        
        # Get text URL and fetch content
        text_url = await self.fetch_bill_text_urls(congress, bill_type, number)
        text = await self.fetch_bill_text(text_url)
        
        # Parse into sections
        sections = self._parse_text_into_sections(text)
        
        # Yield each section
        for section in sections:
            if section["number"]:  # Only yield valid sections
                yield {
                    "number": section["number"],
                    "title": section["title"],
                    "text": self._clean_text(' '.join(section["text"])),
                    "level": section["level"],
                    "parent_section": None
                }

async def parse_bill_url(url: str) -> AsyncIterator[Dict]:
    """Helper function to parse a bill URL"""
    async with CongressBillParser() as parser:
        async for section in parser.parse_bill(url):
            yield section