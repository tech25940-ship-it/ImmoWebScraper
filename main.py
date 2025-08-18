
from dotenv import load_dotenv
load_dotenv()
from utils.scraper_utils import smart_ki_extraction, load_scrape_targets
import pandas as pd

if __name__ == "__main__":
    targets = load_scrape_targets()
    import json
    import re
    import pandas as pd
    all_rows = []
    for target in targets:
        name = target.get('name') or target.get('Name') or 'website'
        url = target.get('url') or target.get('URL')
        selector = target.get('Selector') or target.get('selector')
        print(f"Starte KI-gestützte Extraktion für {name}...")
        try:
            result = smart_ki_extraction(target)
            print("Extrahierte Daten:")
            print(result)
            # Fallback: Falls result kein echtes JSON ist, extrahiere den JSON-Codeblock
            if not isinstance(result, list):
                match = re.search(r"```json\s*(\[.*?\])\s*```", str(result), re.DOTALL)
                if match:
                    result = json.loads(match.group(1))
                else:
                    match = re.search(r"(\[.*?\])", str(result), re.DOTALL)
                    if match:
                        result = json.loads(match.group(1))
                    else:
                        print(f"Warnung: Konnte keine JSON-Daten extrahieren für {name}!")
                        continue
            from urllib.parse import urlparse, urljoin
            base_url = url
            if base_url:
                parsed = urlparse(base_url)
                domain = f"{parsed.scheme}://{parsed.netloc}"
            else:
                domain = ""
            for proj in result:
                raw_link = proj.get("Link")
                # Falls Link schon absolut ist, bleibt er so
                if raw_link and not raw_link.startswith("http") and domain:
                    full_link = urljoin(domain, raw_link)
                else:
                    full_link = raw_link
                all_rows.append({
                    "Website": name,
                    "Projektname": proj.get("Projektname"),
                    "Link": full_link
                })
        except Exception as e:
            print(f"Fehler bei {name}: {e}")
    # Schreibe alles in eine Excel-Datei
    df = pd.DataFrame(all_rows)
    df.to_excel("alle_projekte.xlsx", index=False)
    print("Excel-Datei 'alle_projekte.xlsx' wurde erstellt.")

load_dotenv()


async def crawl_venues():
    """
    Main function to crawl venue data from the website.
    """
    # Initialize configurations
    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy()
    session_id = "venue_crawl_session"

    # Initialize state variables
    page_number = 1
    all_venues = []
    seen_names = set()

    # Start the web crawler context
    # https://docs.crawl4ai.com/api/async-webcrawler/#asyncwebcrawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            # Fetch and process data from the current page
            venues, no_results_found = await fetch_and_process_page(
                crawler,
                page_number,
                BASE_URL,
                CSS_SELECTOR,
                llm_strategy,
                session_id,
                REQUIRED_KEYS,
                seen_names,
            )

            if no_results_found:
                print("No more venues found. Ending crawl.")
                break  # Stop crawling when "No Results Found" message appears

            if not venues:
                print(f"No venues extracted from page {page_number}.")
                break  # Stop if no venues are extracted

            # Add the venues from this page to the total list
            all_venues.extend(venues)
            page_number += 1  # Move to the next page

            # Pause between requests to be polite and avoid rate limits
            await asyncio.sleep(2)  # Adjust sleep time as needed

    # Save the collected venues to a CSV file
    if all_venues:
        save_venues_to_csv(all_venues, "complete_venues.csv")
        print(f"Saved {len(all_venues)} venues to 'complete_venues.csv'.")
    else:
        print("No venues were found during the crawl.")

    # Display usage statistics for the LLM strategy
    llm_strategy.show_usage()


async def main():
    """
    Entry point of the script.
    """
    await crawl_venues()


## Entfernt: Async-Crawler-Block, damit nur die Haslehner-Extraktion läuft
