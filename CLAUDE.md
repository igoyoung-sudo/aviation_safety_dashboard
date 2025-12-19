# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aviation safety data scraper and dashboard system for turboprop aircraft accidents. Scrapes data from Aviation Safety Network and visualizes it using Streamlit. The project consists of:
- Two web scrapers (basic and enhanced) using Playwright
- Interactive Streamlit dashboard for data visualization
- Data output in both CSV and JSON formats

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Data Collection
```bash
# Run basic scraper (faster, list data only)
python aviation_safety_scraper.py

# Run enhanced scraper (slower, includes detailed narratives and flight phase data)
python aviation_safety_scraper_enhanced.py
```

### Dashboard
```bash
# Run Streamlit dashboard
streamlit run dashboard_streamlit.py

# Dashboard automatically loads the most recent CSV file
# Looks for enhanced files first, falls back to basic files
```

## Architecture

### Data Collection Pipeline

**Two scraper implementations:**
1. `aviation_safety_scraper.py` - Basic scraper
   - Scrapes only the aircraft type list pages
   - Fields: date, type, registration, operator, fatalities, location, damage
   - Faster execution

2. `aviation_safety_scraper_enhanced.py` - Enhanced scraper
   - Scrapes list pages + individual accident detail pages (wikibase)
   - Additional fields: time, MSN, engine_model, flight phase, nature, departure/destination airports, narrative text
   - Significantly slower due to visiting each accident's detail page
   - Uses `fetch_details` parameter to control detail fetching

**Scraping workflow:**
- Both scrapers use async Playwright with headless Chromium
- Iterate through `TURBOPROP_AIRCRAFT` dictionary (aircraft type codes)
- For each type code, fetch `https://aviation-safety.net/asndb/type/{type_code}`
- Extract table data using JavaScript evaluation in browser context
- Enhanced scraper: for each accident, visit detail URL and extract additional fields
- Add 0.3-0.5s delays between requests to avoid overwhelming the server
- Output timestamped CSV and JSON files

**Aircraft types covered:**
- ATR series (42, 72)
- De Havilland Canada (Dash 8, Twin Otter, Dash 7)
- Saab (340, 2000)
- Fokker (50, 60)
- Embraer (EMB-120 Brasilia)
- Antonov turboprops (An-24, 26, 32, 140)
- Other turboprops (Let L-410, Il-114, Beech 1900, Jetstream)

### Dashboard Architecture

**File: `dashboard_streamlit.py`**

**Data loading:**
- Uses `@st.cache_data` decorator for data caching
- Auto-detects most recent CSV file (enhanced or basic)
- Preprocesses: parses dates, converts fatalities to numeric, creates derived fields (year, is_fatal, damage_full)

**UI structure:**
1. Sidebar filters (year range, aircraft type, fatal accidents only, flight phase for enhanced data)
2. KPI metrics (total accidents, fatalities, fatal accident rate)
3. Time series charts (yearly accident count, yearly fatalities)
4. Aircraft analysis (accidents by type, fatalities by type)
5. Enhanced visualizations (if enhanced data available):
   - Accidents by flight phase
   - Accidents by flight nature
6. Distribution charts (damage level pie chart, top operators)
7. Fatal accidents table with sortable columns
8. Narrative search (enhanced data only) - searchable accident descriptions with expandable details
9. Raw data viewer with CSV download functionality
10. Statistics summary footer

**Layout:** Wide layout with responsive columns, extensive use of Plotly for interactive charts

## Data Schema

### Basic fields (both scrapers)
- `date`: Accident date (format: "DD Mon YYYY")
- `type`: Specific aircraft variant
- `registration`: Aircraft registration number
- `operator`: Operating airline/company
- `fatalities`: Number of fatalities (as string)
- `location`: Accident location
- `damage`: Damage level code (w/o=written off, sub=substantial, min=minor, non=none)
- `aircraft_category`: Human-readable aircraft name
- `type_code`: Aircraft type code used in URL

### Enhanced fields (enhanced scraper only)
- `detail_url`: URL to accident detail page
- `time`: Time of accident
- `msn`: Manufacturer serial number
- `engine_model`: Engine type
- `fatalities_detail`: Detailed fatalities breakdown
- `other_fatalities`: Ground casualties
- `category`: Accident category classification
- `phase`: Flight phase (e.g., "Landing", "Takeoff", "Cruise")
- `nature`: Flight nature (e.g., "Passenger", "Cargo", "Training")
- `departure_airport`: Origin airport
- `destination_airport`: Destination airport
- `narrative`: Detailed accident description text

## File Naming Conventions

- Output files use timestamp suffix: `aviation_safety_data_YYYYMMDD_HHMMSS.csv`
- Enhanced files: `aviation_safety_enhanced_YYYYMMDD_HHMMSS.csv`
- Dashboard auto-detects and prefers enhanced files

## Modifying Scrapers

To scrape specific aircraft only, modify the `main()` function:

```python
# Example: scrape only ATR 72
selected_aircraft = {'_AT72': 'ATR 72 (all series)'}
await scraper.scrape_all(selected_aircraft)
```

To toggle detail fetching in enhanced scraper:
```python
scraper = EnhancedAviationScraper(fetch_details=False)  # Behaves like basic scraper
```

## Important Notes

- Web scraping respects rate limits (0.3-0.5s delays between requests)
- Data is from Aviation Safety Network - respect their copyright and terms of service
- Enhanced scraper can take significantly longer (visits each accident detail page)
- Dashboard requires at least one CSV file to exist in the directory
- Korean language comments in basic scraper, English in enhanced scraper and dashboard
