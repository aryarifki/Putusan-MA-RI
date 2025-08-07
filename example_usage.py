#!/usr/bin/env python3
"""
Example script untuk menggunakan scraper Mahkamah Agung
"""

import sys
import os
import argparse
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scraper import MahkamahAgungScraper

def main():
    parser = argparse.ArgumentParser(description='Scraper Mahkamah Agung RI')
    parser.add_argument('--pages', type=int, default=5, help='Number of pages to scrape')
    parser.add_argument('--start-page', type=int, default=1, help='Starting page number')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--format', choices=['json', 'csv', 'excel'], default='json', help='Output format')
    parser.add_argument('--output', type=str, help='Output filename (without extension)')
    parser.add_argument('--test-only', action='store_true', help='Test connectivity only')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    
    args = parser.parse_args()
    
    print("🏛️  Scraper Mahkamah Agung RI")
    print("=" * 50)
    print(f"Debug mode: {'ON' if args.debug else 'OFF'}")
    print(f"Output format: {args.format}")
    
    # Initialize scraper
    scraper = MahkamahAgungScraper(debug=args.debug)
    
    try:
        if args.test_only:
            print("\n🔍 Testing connectivity...")
            test_url = "https://putusan3.mahkamahagung.go.id"
            content = scraper.get_page_content(test_url)
            
            if content:
                print(f"✅ Successfully connected to {test_url}")
                print(f"📄 Content length: {len(content):,} characters")
                
                # Test parsing
                sample_data = scraper.parse_putusan_list(content)
                print(f"📊 Sample data extracted: {len(sample_data)} items")
                
                if sample_data and args.debug:
                    print("\n📋 Sample data preview:")
                    for i, item in enumerate(sample_data[:3]):
                        print(f"  {i+1}. {item}")
            else:
                print(f"❌ Failed to connect to {test_url}")
                return
        
        else:
            print(f"\n🚀 Starting scraping...")
            print(f"📖 Pages: {args.start_page} to {args.start_page + args.pages - 1}")
            
            # Start scraping
            data = scraper.scrape_pages(
                start_page=args.start_page,
                max_pages=args.start_page + args.pages - 1,
                resume_from_checkpoint=args.resume
            )
            
            print(f"\n✅ Scraping completed!")
            print(f"📊 Total records: {len(data)}")
            
            # Show statistics
            stats = scraper.get_stats()
            print(f"📈 Success rate: {stats['success_rate']:.1f}%")
            print(f"🔢 Total requests: {stats['total_requests']}")
            print(f"✅ Successful: {stats['successful_requests']}")
            print(f"❌ Failed: {stats['failed_requests']}")
            
            if stats['method_used']:
                print(f"🛠️  Methods used: {stats['method_used']}")
            
            # Save data
            if data:
                output_name = args.output or f"putusan_ma_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                scraper.save_data(output_name, format=args.format)
                print(f"💾 Data saved as {output_name}.{args.format}")
            else:
                print("⚠️  No data to save")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Scraping interrupted by user")
        stats = scraper.get_stats()
        if stats['total_requests'] > 0:
            print(f"📊 Partial results: {len(scraper.scraped_data)} records")
            scraper.save_data("interrupted_run", format=args.format)
            print("💾 Partial data saved")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    
    finally:
        scraper.cleanup()
        print("\n🧹 Cleanup completed")

if __name__ == "__main__":
    main()