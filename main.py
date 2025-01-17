import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from typing import List, Dict
from urllib.parse import urljoin, urlparse

class FocusedContactScraper:
    def __init__(self, delay: int = 1):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.delay = delay

    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text using regex."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = list(set(re.findall(email_pattern, text)))
        # Filter out common false positives
        filtered_emails = [
            email for email in emails 
            if not any(fake in email.lower() for fake in ['example.com', 'domain.com'])
        ]
        return filtered_emails

    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text using regex."""
        # Fixed phone pattern
        phone_patterns = [
            r'\+?\d{1,3}[-. ]?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}',  # International format
            r'\d{3}[-. ]?\d{3}[-. ]?\d{4}',  # US format
            r'\(\d{3}\)\s*\d{3}[-. ]?\d{4}'  # (123) 456-7890 format
        ]
        
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        
        # Clean up phone numbers
        cleaned_phones = []
        for phone in phones:
            # Remove all non-digit characters except '+'
            cleaned = re.sub(r'[^\d+]', '', phone)
            if cleaned not in cleaned_phones:
                cleaned_phones.append(cleaned)
                
        return cleaned_phones

    def find_contact_sections(self, soup: BeautifulSoup) -> List[str]:
        """Find sections likely to contain contact information."""
        contact_info = []
        
        # Common contact-related terms
        contact_terms = ['contact', 'address', 'phone', 'tel', 'email', 'reach', 'footer']
        
        # Look for elements with contact-related IDs or classes
        for term in contact_terms:
            # Find elements with matching id or class
            elements = soup.find_all(class_=lambda x: x and term in x.lower() if x else False)
            elements.extend(soup.find_all(id=lambda x: x and term in x.lower() if x else False))
            
            # Also check footer and contact sections
            elements.extend(soup.find_all('footer'))
            elements.extend(soup.find_all('section', class_=lambda x: x and term in x.lower() if x else False))

        # Extract text from found elements
        for element in elements:
            text = element.get_text(strip=True)
            if text:
                contact_info.append(text)

        return contact_info

    def scrape_page(self, url: str) -> Dict:
        """Scrape a single page for contact information."""
        try:
            print(f"Attempting to scrape: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            print("Successfully fetched the page")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First try contact sections
            contact_sections = self.find_contact_sections(soup)
            all_text = ' '.join(contact_sections) if contact_sections else soup.get_text()
            
            # Extract emails and phones
            emails = self.extract_emails(all_text)
            phones = self.extract_phone_numbers(all_text)
            
            print(f"Found {len(emails)} emails and {len(phones)} phone numbers")
            
            return {
                'url': url,
                'emails': ', '.join(emails) if emails else 'No email found',
                'phone_numbers': ', '.join(phones) if phones else 'No phone found',
                'source': 'Contact section' if contact_sections else 'Full page scan'
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {str(e)}")
            return {
                'url': url,
                'emails': 'Connection error',
                'phone_numbers': 'Connection error',
                'source': str(e)
            }
        except Exception as e:
            print(f"General error for {url}: {str(e)}")
            return {
                'url': url,
                'emails': 'Error',
                'phone_numbers': 'Error',
                'source': str(e)
            }

    def scrape_multiple_urls(self, urls: List[str], output_file: str = 'contact_details.csv'):
        """Scrape multiple URLs and save results to CSV."""
        results = []
        
        for url in urls:
            print(f"\nProcessing: {url}")
            results.append(self.scrape_page(url))
            time.sleep(self.delay)
            
        # Convert to DataFrame and save to CSV
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nResults saved to {output_file}")
        return df

def main():
    # Example usage with katmatic.com
    urls_to_scrape = [
        "https://reliance-logistics.com",

        
    ]
    
    scraper = FocusedContactScraper(delay=2)
    results_df = scraper.scrape_multiple_urls(urls_to_scrape, "contact_details.csv")
    
    print("\nScraping Summary:")
    print(f"Total URLs processed: {len(results_df)}")
    print(f"Found emails: {results_df['emails'].ne('No email found').sum()}")
    print(f"Found phones: {results_df['phone_numbers'].ne('No phone found').sum()}")

if __name__ == "__main__":
    main()