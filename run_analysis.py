#!/usr/bin/env python3
"""
Run HTML structure analysis on saved debug files
"""

import sys
import os
sys.path.append('src')

from html_structure_analyzer import analyze_saved_html_files, print_analysis_summary, save_analysis_report

def main():
    print("🔍 Mahkamah Agung HTML Structure Analyzer")
    print("=" * 50)
    
    # Check for HTML debug files
    html_dirs = [
        "logs/html_debug",
        "src/logs/html_debug", 
        "logs"
    ]
    
    html_dir = None
    for directory in html_dirs:
        if os.path.exists(directory):
            html_files = [f for f in os.listdir(directory) if f.endswith('.html')]
            if html_files:
                html_dir = directory
                print(f"📁 Found {len(html_files)} HTML files in: {directory}")
                break
    
    if not html_dir:
        print("❌ No HTML debug files found!")
        print("Please run the scraper with --debug flag first to generate HTML files")
        return
    
    # Run analysis
    results = analyze_saved_html_files(html_dir)
    
    if results:
        print_analysis_summary(results)
        report = save_analysis_report(results)
        
        if report:
            print(f"\n✅ Analysis completed successfully!")
            print(f"📊 Report saved to: html_analysis_report.json")
            
            # Show key findings
            summary = report['summary']
            print(f"\n🔑 Key Findings:")
            print(f"  Files analyzed: {summary['total_files_analyzed']}")
            print(f"  Files with putusan data: {summary['files_with_putusan_data']}")
            print(f"  Recommended selectors: {len(summary['common_selectors'])}")
            
            if summary['common_selectors']:
                print(f"\n🎯 Top selectors to use:")
                for i, selector in enumerate(summary['common_selectors'][:3]):
                    print(f"    {i+1}. {selector}")
    else:
        print("❌ Analysis failed - no results generated")

if __name__ == "__main__":
    main()
