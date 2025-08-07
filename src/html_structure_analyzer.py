"""
HTML Structure Analyzer for Mahkamah Agung website
Analyzes saved HTML files to understand the actual structure
"""

import os
import json
from bs4 import BeautifulSoup
from typing import Dict, List
import re


def analyze_saved_html_files(html_dir: str = "logs/html_debug") -> Dict:
    """Analyze all saved HTML files to understand structure"""
    
    if not os.path.exists(html_dir):
        print(f"❌ HTML debug directory not found: {html_dir}")
        return {}
    
    analysis_results = {}
    
    for filename in os.listdir(html_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(html_dir, filename)
            print(f"🔍 Analyzing: {filename}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                analysis = analyze_single_html(html_content, filename)
                analysis_results[filename] = analysis
                
            except Exception as e:
                print(f"❌ Error analyzing {filename}: {e}")
    
    return analysis_results


def analyze_single_html(html_content: str, filename: str) -> Dict:
    """Analyze a single HTML file"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    analysis = {
        'filename': filename,
        'total_elements': len(soup.find_all()),
        'structure': {},
        'putusan_elements': [],
        'download_links': [],
        'forms': [],
        'navigation': []
    }
    
    # Basic structure
    analysis['structure'] = {
        'title': soup.title.string if soup.title else 'No title',
        'tables': len(soup.find_all('table')),
        'divs': len(soup.find_all('div')),
        'forms': len(soup.find_all('form')),
        'links': len(soup.find_all('a')),
        'scripts': len(soup.find_all('script'))
    }
    
    # Look for putusan elements based on the HTML structure
    putusan_selectors = [
        'div.spost',
        '#popular-post-list-sidebar div.spost',
        '.spost clearfix',
        'div[class*="spost"]'
    ]
    
    for selector in putusan_selectors:
        elements = soup.select(selector)
        if elements:
            analysis['putusan_elements'].append({
                'selector': selector,
                'count': len(elements),
                'sample_data': analyze_putusan_element(elements[0]) if elements else None
            })
    
    # Look for download links
    download_selectors = [
        'a[href*=".pdf"]',
        'a[href*=".zip"]',
        'a[href*="download"]',
        'a[href*="direktori/putusan/"]'
    ]
    
    for selector in download_selectors:
        links = soup.select(selector)
        if links:
            analysis['download_links'].append({
                'selector': selector,
                'count': len(links),
                'sample_links': [link.get('href') for link in links[:3]]
            })
    
    # Analyze forms
    forms = soup.find_all('form')
    for i, form in enumerate(forms):
        analysis['forms'].append({
            'index': i,
            'action': form.get('action', ''),
            'method': form.get('method', ''),
            'inputs': len(form.find_all('input')),
            'id': form.get('id', ''),
            'class': form.get('class', [])
        })
    
    # Look for navigation elements
    nav_selectors = [
        '.pagination',
        'nav',
        'a[href*="page="]',
        'button[onclick*="page"]'
    ]
    
    for selector in nav_selectors:
        nav_elements = soup.select(selector)
        if nav_elements:
            analysis['navigation'].append({
                'selector': selector,
                'count': len(nav_elements),
                'sample_text': nav_elements[0].get_text(strip=True)[:100] if nav_elements else ''
            })
    
    return analysis


def analyze_putusan_element(element) -> Dict:
    """Analyze a single putusan element to understand its structure"""
    if not element:
        return {}
    
    structure = {
        'tag': element.name,
        'classes': element.get('class', []),
        'id': element.get('id', ''),
        'children': [],
        'text_content': element.get_text(strip=True)[:200],
        'links': [],
        'dates': [],
        'numbers': []
    }
    
    # Analyze child elements
    for child in element.children:
        if hasattr(child, 'name') and child.name:
            child_info = {
                'tag': child.name,
                'classes': child.get('class', []),
                'id': child.get('id', ''),
                'text': child.get_text(strip=True)[:100]
            }
            structure['children'].append(child_info)
    
    # Find links
    links = element.find_all('a', href=True)
    for link in links:
        structure['links'].append({
            'href': link['href'],
            'text': link.get_text(strip=True),
            'title': link.get('title', '')
        })
    
    # Extract dates
    text = element.get_text()
    date_patterns = [
        r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
        r'\d{1,2}\s+\w+\s+\d{4}'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        structure['dates'].extend(matches)
    
    # Extract numbers (like case numbers)
    number_patterns = [
        r'\d+\s*[/K]\s*[A-Z]+[./]\w*[/]\d{4}',
        r'Nomor\s+([^<\n]+)'
    ]
    
    for pattern in number_patterns:
        matches = re.findall(pattern, text, re.I)
        structure['numbers'].extend(matches)
    
    return structure


def generate_selectors_from_analysis(analysis_results: Dict) -> List[str]:
    """Generate optimized selectors based on analysis"""
    selectors = []
    
    # Collect all successful putusan selectors
    for filename, analysis in analysis_results.items():
        for putusan_info in analysis.get('putusan_elements', []):
            if putusan_info['count'] > 0:
                selectors.append(putusan_info['selector'])
    
    # Remove duplicates and sort by preference
    unique_selectors = list(set(selectors))
    
    # Preferred order
    preference_order = [
        'div.spost',
        '#popular-post-list-sidebar div.spost',
        '.spost',
        'div[class*="spost"]'
    ]
    
    ordered_selectors = []
    for preferred in preference_order:
        if preferred in unique_selectors:
            ordered_selectors.append(preferred)
            unique_selectors.remove(preferred)
    
    # Add remaining selectors
    ordered_selectors.extend(unique_selectors)
    
    return ordered_selectors


def save_analysis_report(analysis_results: Dict, output_file: str = "html_analysis_report.json"):
    """Save detailed analysis report"""
    try:
        # Generate summary
        summary = {
            'total_files_analyzed': len(analysis_results),
            'files_with_putusan_data': 0,
            'common_selectors': [],
            'download_link_patterns': [],
            'recommended_parsing_strategy': {}
        }
        
        # Count files with putusan data
        for analysis in analysis_results.values():
            if analysis.get('putusan_elements'):
                summary['files_with_putusan_data'] += 1
        
        # Generate recommended selectors
        summary['common_selectors'] = generate_selectors_from_analysis(analysis_results)
        
        # Compile download patterns
        download_patterns = set()
        for analysis in analysis_results.values():
            for download_info in analysis.get('download_links', []):
                download_patterns.add(download_info['selector'])
        summary['download_link_patterns'] = list(download_patterns)
        
        # Create full report
        report = {
            'summary': summary,
            'detailed_analysis': analysis_results,
            'generated_at': str(datetime.now())
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Analysis report saved to: {output_file}")
        return report
        
    except Exception as e:
        print(f"❌ Error saving analysis report: {e}")
        return None


def print_analysis_summary(analysis_results: Dict):
    """Print a summary of the analysis"""
    print("\n" + "="*60)
    print("📊 HTML STRUCTURE ANALYSIS SUMMARY")
    print("="*60)
    
    for filename, analysis in analysis_results.items():
        print(f"\n📄 {filename}")
        print(f"  Total elements: {analysis['total_elements']}")
        print(f"  Title: {analysis['structure']['title']}")
        
        if analysis['putusan_elements']:
            print(f"  ✅ Found putusan data:")
            for putusan_info in analysis['putusan_elements']:
                print(f"    - {putusan_info['selector']}: {putusan_info['count']} elements")
        else:
            print(f"  ❌ No putusan data found")
        
        if analysis['download_links']:
            print(f"  📁 Download links found:")
            for download_info in analysis['download_links']:
                print(f"    - {download_info['selector']}: {download_info['count']} links")
    
    # Generate recommendations
    print(f"\n🎯 RECOMMENDATIONS")
    print(f"  Recommended selectors:")
    selectors = generate_selectors_from_analysis(analysis_results)
    for i, selector in enumerate(selectors[:5]):
        print(f"    {i+1}. {selector}")


if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    # Allow custom HTML directory
    html_dir = sys.argv[1] if len(sys.argv) > 1 else "logs/html_debug"
    
    print("🔍 Starting HTML structure analysis...")
    results = analyze_saved_html_files(html_dir)
    
    if results:
        print_analysis_summary(results)
        save_analysis_report(results)
        print("\n✅ Analysis completed!")
    else:
        print("❌ No HTML files found to analyze")
