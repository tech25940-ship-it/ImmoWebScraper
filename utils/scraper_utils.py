from dotenv import load_dotenv
load_dotenv()
def smart_ki_extraction(target):
    """
    Lädt den HTML-Quelltext einer Seite und nutzt Groq/DeepSeek, um relevante Daten (z.B. Projektnamen und Links) per Prompt zu extrahieren.
    Args:
        target (dict): Dict mit 'url' und 'Selector'.
    Returns:
        List[dict] oder str: Extrahierte Daten oder KI-Antwort
    """
    import requests
    from bs4 import BeautifulSoup
    html = requests.get(target['url']).text
    soup = BeautifulSoup(html, "html.parser")
    selector = target.get('Selector') or target.get('selector')
    if not selector:
        raise RuntimeError("Kein Selector angegeben!")
    project_blocks = soup.select(selector)
    if not project_blocks:
        raise RuntimeError(f"Keine Projekt-Container ({selector}) gefunden. Bitte prüfe die Seite oder passe den Selektor an.")
    relevant_html = '\n'.join(str(block) for block in project_blocks)
    from crawl4ai import LLMExtractionStrategy
    import os
    import litellm
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key.strip() == "" or "dein_geheimer_api_key" in api_key:
        raise RuntimeError("GROQ_API_KEY fehlt oder ist ungültig! Bitte prüfe die .env-Datei und setze einen gültigen Key.")
    prompt = (
        "Du bist ein Web-Scraping-Experte. Extrahiere alle Projektnamen und die zugehörigen Links aus folgendem HTML. Gib die Daten als JSON-Liste mit den Feldern 'Projektname' und 'Link' zurück. HTML:\n" + relevant_html
    )
    response = litellm.completion(
        model="groq/deepseek-r1-distill-llama-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        max_tokens=2048
    )
    import json
    try:
        return json.loads(response["choices"][0]["message"]["content"])
    except Exception:
        return response["choices"][0]["message"]["content"]
    
    def ki_extraction_with_rate_limit(project_texts, model="groq/deepseek-r1-distill-llama-70b", api_key=None, max_tokens=2048):
        """
        Führt KI-Extraktion für eine Liste von Projekten durch und behandelt RateLimitError automatisch.
        Args:
            project_texts (List[str]): Liste mit HTML/Text für einzelne Projekte.
            model (str): Modellname.
            api_key (str): Groq API Key.
            max_tokens (int): Maximale Tokenzahl pro Anfrage.
        Returns:
            List: KI-Antworten für alle Projekte.
        """
        import time
        import re
        import litellm
        results = []
        for text in project_texts:
            while True:
                try:
                    response = litellm.completion(
                        model=model,
                        messages=[{"role": "user", "content": text}],
                        api_key=api_key,
                        max_tokens=max_tokens
                    )
                    results.append(response["choices"][0]["message"]["content"])
                    break
                except litellm.RateLimitError as e:
                    wait_time = extract_wait_time_from_error(str(e))
                    print(f"RateLimit erreicht, warte {wait_time} Sekunden...")
                    time.sleep(wait_time)
        return results

    def extract_wait_time_from_error(error_msg):
        """
        Extrahiert die Wartezeit aus einer RateLimitError-Meldung.
        Args:
            error_msg (str): Fehlermeldung als String.
        Returns:
            int: Sekunden zum Warten.
        """
        # Suche nach "try again in ...s" im Error-String
        match = re.search(r"try again in ([\d\.]+)s", error_msg)
        if match:
            return int(float(match.group(1))) + 1
        return 60  # Fallback: 1 Minute warten
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMExtractionStrategy
import asyncio
def auto_extract_with_groq(url):
    """
    Nutzt Groq/DeepSeek, um automatisch relevante Daten aus einer Webseite zu extrahieren.
    Args:
        url (str): Ziel-URL
    Returns:
        List[dict]: Extrahierte Objekte (z.B. Projekte)
    """
    async def run():
        browser_config = BrowserConfig(browser_type="chromium", headless=True, verbose=False)
        extraction_strategy = LLMExtractionStrategy(
            provider="groq/deepseek-r1-distill-llama-70b",
            api_token=os.getenv("GROQ_API_KEY"),
            schema=None,  # Keine feste Struktur, KI soll selbst erkennen
            extraction_type="auto",  # Automatische Extraktion
            instruction="Extrahiere alle relevanten Objekte (z.B. Projekte, Immobilien, Namen, Links) aus dem folgenden Inhalt.",
            input_format="markdown",
            verbose=False,
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(
                    cache_mode=None,
                    extraction_strategy=extraction_strategy,
                    css_selector=None,
                    session_id="auto-extract"
                ),
            )
            if result.success and result.extracted_content:
                try:
                    return json.loads(result.extracted_content)
                except Exception:
                    return result.extracted_content
            return []
    return asyncio.run(run())
import requests
from bs4 import BeautifulSoup
# Handler-Struktur für verschiedene Seiten
def scrape_brunner_bau():
    url = "https://www.brunner-bau.at/de/eigenprojekte"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    projects = []
    for card in soup.select('.project-list-item'):
        name_tag = card.select_one('.project-title')
        link_tag = card.select_one('a')
        if name_tag and link_tag:
            name = name_tag.get_text(strip=True)
            link = link_tag['href']
            if not link.startswith('http'):
                link = 'https://www.brunner-bau.at' + link
            projects.append({
                'Projektname': name,
                'Link': link
            })
    return projects

SCRAPE_HANDLERS = {
    'brunner-bau.at': scrape_brunner_bau,
    # Weitere Handler hier ergänzen
}

def scrape_projects_for_target(target):
    """
    Wählt den passenden Scraper-Handler für die Zielseite.
    Args:
        target (dict): Dict mit 'name' und 'url'.
    Returns:
        List[dict]: Projekte mit Name und Link
    """
    for domain, handler in SCRAPE_HANDLERS.items():
        if domain in target['url']:
            return handler()
    return []  # Kein passender Handler
import csv
# ...existing code...
def load_scrape_targets(filepath="scrape_targets.csv"):
    """
    Lädt die zu scrapenden Webseiten aus einer CSV-Datei.
    Args:
        filepath (str): Pfad zur CSV-Datei mit Name,URL.
    Returns:
        List[dict]: Liste mit Dicts {"name":..., "url":...}
    """
    targets = []
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Überspringe Kommentarzeilen oder leere Zeilen
            if not row.get("URL") or row["URL"].startswith("#"):
                continue
            targets.append({
                "name": row.get("Name"),
                "url": row.get("URL"),
                "Selector": row.get("Selector")
            })
    return targets
import json
import os
from typing import List, Set, Tuple

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

from models.venue import Venue
from utils.data_utils import is_complete_venue, is_duplicate_venue


def get_browser_config() -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.

    Returns:
        BrowserConfig: The configuration settings for the browser.
    """
    # https://docs.crawl4ai.com/core/browser-crawler-config/
    return BrowserConfig(
        browser_type="chromium",  # Type of browser to simulate
        headless=True,  # Headless-Modus für Server/Container
        verbose=True,  # Enable verbose logging
    )


def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Returns the configuration for the language model extraction strategy.

    Returns:
        LLMExtractionStrategy: The settings for how to extract data using LLM.
    """
    # https://docs.crawl4ai.com/api/strategies/#llmextractionstrategy
    return LLMExtractionStrategy(
        provider="groq/deepseek-r1-distill-llama-70b",  # Name of the LLM provider
        api_token=os.getenv("GROQ_API_KEY"),  # API token for authentication
        schema=Venue.model_json_schema(),  # JSON schema of the data model
        extraction_type="schema",  # Type of extraction to perform
        instruction=(
            "Extract all venue objects with 'name', 'location', 'price', 'capacity', "
            "'rating', 'reviews', and a 1 sentence description of the venue from the "
            "following content."
        ),  # Instructions for the LLM
        input_format="markdown",  # Format of the input content
        verbose=True,  # Enable verbose logging
    )


async def check_no_results(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
) -> bool:
    """
    Checks if the "No Results Found" message is present on the page.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        url (str): The URL to check.
        session_id (str): The session identifier.

    Returns:
        bool: True if "No Results Found" message is found, False otherwise.
    """
    # Fetch the page without any CSS selector or extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
        ),
    )

    if result.success:
        if "No Results Found" in result.cleaned_html:
            return True
    else:
        print(
            f"Error fetching page for 'No Results Found' check: {result.error_message}"
        )

    return False


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    """
    Fetches and processes a single page of venue data.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        page_number (int): The page number to fetch.
        base_url (str): The base URL of the website.
        css_selector (str): The CSS selector to target the content.
        llm_strategy (LLMExtractionStrategy): The LLM extraction strategy.
        session_id (str): The session identifier.
        required_keys (List[str]): List of required keys in the venue data.
        seen_names (Set[str]): Set of venue names that have already been seen.

    Returns:
        Tuple[List[dict], bool]:
            - List[dict]: A list of processed venues from the page.
            - bool: A flag indicating if the "No Results Found" message was encountered.
    """
    url = f"{base_url}?page={page_number}"
    print(f"Loading page {page_number}...")

    # Check if "No Results Found" message is present
    no_results = await check_no_results(crawler, url, session_id)
    if no_results:
        return [], True  # No more results, signal to stop crawling

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=llm_strategy,  # Strategy for data extraction
            css_selector=css_selector,  # Target specific content on the page
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print(f"No venues found on page {page_number}.")
        return [], False

    # After parsing extracted content
    print("Extracted data:", extracted_data)

    # Process venues
    complete_venues = []
    for venue in extracted_data:
        # Debugging: Print each venue to understand its structure
        print("Processing venue:", venue)

        # Ignore the 'error' key if it's False
        if venue.get("error") is False:
            venue.pop("error", None)  # Remove the 'error' key if it's False

        if not is_complete_venue(venue, required_keys):
            continue  # Skip incomplete venues

        if is_duplicate_venue(venue["name"], seen_names):
            print(f"Duplicate venue '{venue['name']}' found. Skipping.")
            continue  # Skip duplicate venues

        # Add venue to the list
        seen_names.add(venue["name"])
        complete_venues.append(venue)

    if not complete_venues:
        print(f"No complete venues found on page {page_number}.")
        return [], False

    print(f"Extracted {len(complete_venues)} venues from page {page_number}.")
    return complete_venues, False  # Continue crawling
