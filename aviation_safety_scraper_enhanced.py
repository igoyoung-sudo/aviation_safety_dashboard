#!/usr/bin/env python3
"""
Aviation Safety Network Enhanced Scraper with Detailed Information
Collects detailed accident data from wikibase pages
"""

import asyncio
import csv
import json
from datetime import datetime
from playwright.async_api import async_playwright
import pandas as pd

# Major turboprop aircraft types
TURBOPROP_AIRCRAFT = {
    # ATR series
    '_AT72': 'ATR 72 (all series)',
    'AT72': 'ATR 72-200',
    'AT73': 'ATR 72-210',
    'AT75': 'ATR 72-500',
    'AT76': 'ATR 72-600',
    '_AT42': 'ATR 42 (all series)',
    'AT43': 'ATR 42-300',
    'AT44': 'ATR 42-400',
    'AT45': 'ATR 42-500',
    'AT46': 'ATR 42-600',

    # De Havilland Canada (Dash 8 / DHC)
    'DH8A': 'Dash 8-100',
    'DH8B': 'Dash 8-200',
    'DH8C': 'Dash 8-300',
    'DH8D': 'Dash 8-400 (Q400)',
    'DHC6': 'DHC-6 Twin Otter',
    'DHC7': 'DHC-7 Dash 7',

    # Saab
    'S340': 'Saab 340',
    'S2000': 'Saab 2000',

    # Fokker
    'F50': 'Fokker 50',
    'F60': 'Fokker 60',

    # Embraer
    'E120': 'EMB-120 Brasilia',

    # Antonov (turboprop only)
    'AN24': 'Antonov An-24',
    'AN26': 'Antonov An-26',
    'AN32': 'Antonov An-32',
    'A140': 'Antonov An-140',

    # Others
    'L410': 'Let L-410',
    'IL114': 'Ilyushin Il-114',
    'B190': 'Beech 1900',
    'J31': 'Jetstream 31',
    'J41': 'Jetstream 41',
}


class EnhancedAviationScraper:
    """Enhanced Aviation Safety Network scraper with detailed info"""

    def __init__(self, fetch_details=True):
        self.base_url = "https://aviation-safety.net/asndb/type/"
        self.all_data = []
        self.fetch_details = fetch_details

    async def scrape_detail_page(self, page, detail_url):
        """Scrape detailed information from wikibase page"""
        try:
            await page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(0.3)

            # Extract detailed information from the page
            detail_data = await page.evaluate("""
                () => {
                    const table = document.querySelector('table');
                    if (!table) return {};

                    const rows = table.querySelectorAll('tr');
                    const data = {};

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const key = cells[0].textContent.trim().replace(':', '');
                            const value = cells[1].textContent.trim();
                            data[key] = value;
                        }
                    });

                    // Extract narrative
                    const allText = document.body.innerText;
                    const narrativeMatch = allText.match(/Narrative:\\s*([\\s\\S]*?)(?:Sources:|Location:|$)/);
                    if (narrativeMatch) {
                        data['Narrative'] = narrativeMatch[1].trim();
                    }

                    return data;
                }
            """)

            return detail_data

        except Exception as e:
            print(f"    ! Error fetching details: {str(e)[:50]}")
            return {}

    async def scrape_aircraft_type(self, page, type_code, aircraft_name):
        """Scrape aircraft type accident list"""
        url = f"{self.base_url}{type_code}"
        print(f"Collecting: {aircraft_name} ({url})")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(1)

            # Extract list and detail URLs
            list_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    if (tables.length < 2) return [];

                    const dataTable = tables[1];
                    const rows = dataTable.querySelectorAll('tr');
                    const result = [];

                    for (let i = 1; i < rows.length; i++) {
                        const cells = Array.from(rows[i].querySelectorAll('td'));
                        if (cells.length > 0) {
                            // Get detail page link
                            const dateLink = cells[0]?.querySelector('a');
                            const detailUrl = dateLink ? dateLink.href : '';

                            const rowData = {
                                date: cells[0]?.textContent.trim() || '',
                                type: cells[1]?.textContent.trim() || '',
                                registration: cells[2]?.textContent.trim() || '',
                                operator: cells[3]?.textContent.trim() || '',
                                fatalities: cells[4]?.textContent.trim() || '',
                                location: cells[5]?.textContent.trim() || '',
                                damage: cells[7]?.textContent.trim() || '',
                                detail_url: detailUrl
                            };
                            result.push(rowData);
                        }
                    }

                    return result;
                }
            """)

            # Fetch detailed information for each accident
            for idx, record in enumerate(list_data, 1):
                record['aircraft_category'] = aircraft_name
                record['type_code'] = type_code

                if self.fetch_details and record.get('detail_url'):
                    print(f"  [{idx}/{len(list_data)}] Fetching details...", end='\r')
                    details = await self.scrape_detail_page(page, record['detail_url'])

                    # Add detailed fields
                    record['time'] = details.get('Time', '')
                    record['msn'] = details.get('MSN', '')
                    record['engine_model'] = details.get('Engine model', '')
                    record['fatalities_detail'] = details.get('Fatalities', '')
                    record['other_fatalities'] = details.get('Other fatalities', '')
                    record['category'] = details.get('Category', '')
                    record['phase'] = details.get('Phase', '')
                    record['nature'] = details.get('Nature', '')
                    record['departure_airport'] = details.get('Departure airport', '')
                    record['destination_airport'] = details.get('Destination airport', '')
                    record['narrative'] = details.get('Narrative', '')

                    await asyncio.sleep(0.3)  # Be nice to the server

                self.all_data.append(record)

            print(f"  → {len(list_data)} records collected")
            return list_data

        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            return []

    async def scrape_all(self, aircraft_types=None, limit_per_type=None):
        """Scrape all aircraft data"""
        if aircraft_types is None:
            aircraft_types = TURBOPROP_AIRCRAFT

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            total = len(aircraft_types)
            for idx, (type_code, aircraft_name) in enumerate(aircraft_types.items(), 1):
                print(f"\n[{idx}/{total}]", end=" ")
                await self.scrape_aircraft_type(page, type_code, aircraft_name)
                await asyncio.sleep(0.5)

            await browser.close()

        print(f"\n\nTotal {len(self.all_data)} records collected.")
        return self.all_data

    def save_to_csv(self, filename='aviation_safety_data_enhanced.csv'):
        """Save to CSV file"""
        if not self.all_data:
            print("No data to save.")
            return

        df = pd.DataFrame(self.all_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"CSV saved: {filename}")

    def save_to_json(self, filename='aviation_safety_data_enhanced.json'):
        """Save to JSON file"""
        if not self.all_data:
            print("No data to save.")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_data, f, ensure_ascii=False, indent=2)
        print(f"JSON saved: {filename}")

    def get_statistics(self):
        """Print statistics"""
        if not self.all_data:
            print("No data.")
            return

        df = pd.DataFrame(self.all_data)

        print("\n" + "="*60)
        print("Data Statistics")
        print("="*60)
        print(f"Total records: {len(df)}")
        print(f"\nAccidents by aircraft:")
        print(df['aircraft_category'].value_counts().head(10))

        # Fatalities statistics
        df['fatalities_num'] = pd.to_numeric(df['fatalities'], errors='coerce')
        print(f"\nTotal fatalities: {df['fatalities_num'].sum():.0f}")
        print(f"Average fatalities per accident: {df['fatalities_num'].mean():.2f}")

        # Damage distribution
        print(f"\nDamage distribution:")
        print(df['damage'].value_counts())

        # Phase distribution (if available)
        if 'phase' in df.columns:
            phase_counts = df['phase'].value_counts()
            if len(phase_counts) > 0:
                print(f"\nFlight phase distribution:")
                print(phase_counts.head(10))


async def main():
    """Main execution function"""
    print("Aviation Safety Network Enhanced Scraper")
    print("="*60)
    print("This will collect detailed information from wikibase pages.")
    print("This may take longer due to additional page visits.")
    print("="*60)

    # Create scraper with detailed fetching enabled
    scraper = EnhancedAviationScraper(fetch_details=True)

    # For testing, you can limit to specific aircraft:
    # test_aircraft = {'_AT72': 'ATR 72 (all series)'}
    # await scraper.scrape_all(test_aircraft)

    # Collect all data
    await scraper.scrape_all()

    # Print statistics
    scraper.get_statistics()

    # Save files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scraper.save_to_csv(f'aviation_safety_enhanced_{timestamp}.csv')
    scraper.save_to_json(f'aviation_safety_enhanced_{timestamp}.json')

    print("\nData collection complete!")


if __name__ == "__main__":
    asyncio.run(main())
