#!/usr/bin/env python3
"""
Quick debugging test runner for the scraper
"""

import sys
import os
sys.path.append('src')

from scraper import debug_site_structure, MahkamahAgungScraper
from debug_tools import inspect_website, test_selectors

def main():
    print("🔍 Mahkamah Agung Scraper Debug Tool")
    print("=" * 50)
    
    # Test URL (replace with actual Mahkamah Agung URL)
    test_url = "https://putusan3.mahkamahagung.go.id"
    
    print("Choose debugging mode:")
    print("1. Quick site inspection")
    print("2. Full structure analysis") 
    print("3. Interactive debugging")
    print("4. Selector testing")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        inspect_website(test_url)
    
    elif choice == "2":
        debug_site_structure(test_url)
    
    elif choice == "3":
        scraper = MahkamahAgungScraper(debug=True, interactive_debug=True)
        content = scraper.get_page_content(test_url)
        scraper.cleanup()
    
    elif choice == "4":
        test_selectors(url=test_url)
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
