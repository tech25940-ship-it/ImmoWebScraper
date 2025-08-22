from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Tuple

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMExtractionStrategy, CacheMode
from models.venue import Venue
from utils.data_utils import is_complete_venue, is_duplicate_venue

# ------------------------------
# Browser / LLM Konfiguration
# ------------------------------

def get_browser_config() -> BrowserConfig:
    return BrowserConfig(browser_type="chromium", headless=True, verbose=True)

def get_llm_strategy() -> LLMExtractionStrategy:
    return LLMExtractionStrategy(
        provider="groq/deepseek-r1-distill-llama-70b",
        api_token=os.getenv("GROQ_API_KEY"),
        schema=Venue.model_json_schema(),
        extraction_type="schema",
        instruction=(
            "Extract all venue objects with 'name', 'location', 'price', 'capacity', "
            "'rating', 'reviews', and a 1 sentence description of the venue from the "
            "following content."
        ),
        input_format="markdown",
        verbose=True
    )

# ------------------------------
# Utility: Smart KI Extraction
# ------------------------------

def smart_ki_extraction(target: Dict, list_sel: str = None, item_sel: str = None) -> List[Dict]:
    """
    Extrahiert Daten per KI aus einer Seite. Kann Listen-Container + Item-Selektor nutzen.
    """
    html = requests.get(target['url']).text
    soup = BeautifulSoup(html, "html.parser")

    if list_sel and item_sel:
        container = soup.select_one(list_sel)
        if not container:
            raise RuntimeError(f"Kein Container gefunden: {list_sel}")
        items = container.select(item_sel)
        results = []
        for item in items:
            data = {}
            for field_name, field_selector in target.get("fields", {}).items():
                el = item.select_one(field_selector)
                data[field_name] = el.get_text(strip=True) if el else None
            results.append(data)
        return results
    else:
        selector = target.get('Selector') or target.get('selector')
        if not selector:
            raise RuntimeError("Kein Selector angegeben!")
        blocks = soup.select(selector)
        relevant_html = '\n'.join(str(b) for b in blocks)
        from crawl4ai import LLMExtractionStrategy
        import litellm
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY fehlt!")

        prompt = (
            "Du bist ein Web-Scraping-Experte. Extrahiere alle Projektnamen und Links aus folgendem HTML. "
            "Gib die Daten als JSON-Liste mit 'Projektname' und 'Link' zurück.\n" + relevant_html
        )

        response = litellm.completion(
            model="groq/deepseek-r1-distill-llama-70b",
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            max_tokens=2048
        )
        try:
            return json.loads(response["choices"][0]["message"]["content"])
        except Exception:
            return response["choices"][0]["message"]["content"]

# ------------------------------
# CSV-Loader für Ziele
# ------------------------------

import csv
def load_scrape_targets(filepath="scrape_targets.csv") -> List[Dict]:
    targets = []
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not row.get("URL") or row["URL"].startswith("#"):
                continue
            targets.append({
                "name": row.get("Name"),
                "url": row.get("URL"),
                "Selector": row.get("Selector"),
                "list_selector": row.get("list_selector"),
                "item_selector": row.get("item_selector"),
                "fields": json.loads(row.get("fields") or "{}")
            })
    return targets

# ------------------------------
# Async Crawl Utility
# ------------------------------

async def check_no_results(crawler: AsyncWebCrawler, url: str, session_id: str) -> bool:
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS, session_id=session_id)
    )
    if result.success and "No Results Found" in result.cleaned_html:
        return True
    return False

async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str]
) -> Tuple[List[dict], bool]:
    url = f"{base_url}?page={page_number}"
    no_results = await check_no_results(crawler, url, session_id)
    if no_results:
        return [], True

    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=llm_strategy,
            css_selector=css_selector,
            session_id=session_id
        )
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    extracted_data = json.loads(result.extracted_content)
    complete_venues = []
    for venue in extracted_data:
        if venue.get("error") is False:
            venue.pop("error", None)
        if not is_complete_venue(venue, required_keys):
            continue
        if is_duplicate_venue(venue["name"], seen_names):
            continue
        seen_names.add(venue["name"])
        complete_venues.append(venue)

    return complete_venues, False
