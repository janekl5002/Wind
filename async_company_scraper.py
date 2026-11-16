"""
async_company_scraper.py

Usage:
    - Put unique companies CSV as: unique_companies.csv
      with columns: company_imo_number,company_name
    - python async_company_scraper.py
"""

import asyncio
import aiohttp
import aiohttp.client_exceptions
import async_timeout
import csv
import os
import re
import random
import time
import logging
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# ---------------------------
# CONFIG
# ---------------------------
INPUT_CSV = "unique_companies.csv"
OUT_FOLDER = Path("scraped_companies")
RESULTS_CSV = OUT_FOLDER / "scrape_results.csv"
LOG_FILE = OUT_FOLDER / "scraper.log"
CONCURRENCY = 8
PER_HOST_DELAY = 1.0
REQUEST_TIMEOUT = 25
MAX_RETRIES = 3
HEADERS = {
    "User-Agent": "EconowindCompanyScraper/1.0 (+your-email@example.com)"
}
DUCKDUCKGO_HTML = "https://duckduckgo.com/html/?q="

# Pages to try in addition to homepage
EXTRA_PATHS = ["/about", "/about-us", "/contact", "/contact-us", "/company", "/who-we-are"]

# Create output folder
OUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------------------
# LOGGING SETUP
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------
# HELPERS
# ---------------------------
def slugify_netloc(netloc: str) -> str:
    """Create filesystem-friendly folder name from network location"""
    return netloc.replace(":", "_").replace("/", "_").replace(".", "_")

def extract_visible_text(html: str) -> str:
    """Extract visible text from HTML, removing scripts, styles, etc."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "iframe"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        return ""

def parse_duckduckgo_result_link(href: str) -> Optional[str]:
    """
    DuckDuckGo HTML results may return safe links or wrapped redirect forms.
    Try to extract real URL; fall back to href.
    """
    if not href:
        return None
    try:
        # Try to detect url param u=...
        m = re.search(r'u=(https?%3A%2F%2F[^&]+)', href)
        if m:
            return unquote(m.group(1))
        # If href is direct http
        if href.startswith("http"):
            return href
    except Exception as e:
        logger.warning(f"Error parsing DuckDuckGo link '{href}': {e}")
    return None

def company_name_in_text(company_name: str, text: str) -> bool:
    """Check if company name appears in text (case-insensitive)"""
    if not text or not company_name:
        return False
    try:
        nm = re.sub(r"\s+", " ", company_name).strip().lower()
        return nm in text.lower()
    except Exception as e:
        logger.warning(f"Error checking company name in text: {e}")
        return False

def safe_write_file(filepath: Path, content: str, encoding: str = "utf-8") -> bool:
    """Safely write content to file with error handling"""
    try:
        filepath.write_text(content, encoding=encoding)
        return True
    except Exception as e:
        logger.error(f"Failed to write file {filepath}: {e}")
        return False

# ---------------------------
# ASYNC HTTP
# ---------------------------
class HostDelayManager:
    """Simple per-host delay manager with thread-safe operations."""
    def __init__(self, min_delay: float = 0.5):
        self.last_called = {}
        self.min_delay = min_delay
        self.lock = asyncio.Lock()

    async def wait(self, host: str):
        """Wait appropriate delay before making request to host"""
        async with self.lock:
            now = time.monotonic()
            last = self.last_called.get(host, 0)
            elapsed = now - last
            to_wait = max(0, self.min_delay + random.random() * 0.5 - elapsed)
            if to_wait > 0:
                await asyncio.sleep(to_wait)
            self.last_called[host] = time.monotonic()

async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int = REQUEST_TIMEOUT
) -> Tuple[Optional[int], str]:
    """
    Fetch content with retries and timeout.
    Returns (status_code, text) or (None, error_message)
    """
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with async_timeout.timeout(timeout):
                async with session.get(url, headers=HEADERS, allow_redirects=True) as resp:
                    # Check if response is actually HTML/text
                    content_type = resp.headers.get('Content-Type', '').lower()
                    if not any(t in content_type for t in ['text', 'html', 'xml']):
                        return resp.status, f"ERROR: Non-text content type: {content_type}"
                    
                    text = await resp.text(errors="ignore")
                    return resp.status, text
        except asyncio.TimeoutError:
            last_exc = "Timeout"
            logger.warning(f"Timeout on attempt {attempt}/{MAX_RETRIES} for {url}")
        except aiohttp.ClientError as e:
            last_exc = str(e)
            logger.warning(f"Client error on attempt {attempt}/{MAX_RETRIES} for {url}: {e}")
        except Exception as e:
            last_exc = str(e)
            logger.error(f"Unexpected error on attempt {attempt}/{MAX_RETRIES} for {url}: {e}")
        
        if attempt < MAX_RETRIES:
            await asyncio.sleep(0.8 * attempt + random.random() * 0.5)
    
    return None, f"ERROR: {last_exc}"

# ---------------------------
# SCRAPING LOGIC
# ---------------------------
async def search_company(
    session: aiohttp.ClientSession,
    company_name: str
) -> Tuple[Optional[int], Optional[str]]:
    """Use DuckDuckGo HTML results to find likely first result URL."""
    try:
        q = company_name + " official website"
        url = DUCKDUCKGO_HTML + aiohttp.helpers.quote(q, safe='')
        status, html = await fetch_text(session, url)
        
        if not html or isinstance(html, str) and html.startswith("ERROR:"):
            logger.warning(f"Failed to search for {company_name}: {html}")
            return status, None
        
        soup = BeautifulSoup(html, "html.parser")

        # DuckDuckGo result selector heuristics
        candidate = None
        # Try results with class result__a
        a = soup.select_one("a.result__a")
        if a and a.get("href"):
            candidate = parse_duckduckgo_result_link(a.get("href"))
        
        # Fallback: first <a href> in results area
        if not candidate:
            a2 = soup.find("a", href=True)
            if a2:
                candidate = parse_duckduckgo_result_link(a2.get("href"))
        
        return status, candidate
    except Exception as e:
        logger.error(f"Error searching for company {company_name}: {e}")
        return None, None

async def check_robots(
    session: aiohttp.ClientSession,
    domain: str
) -> Tuple[Optional[int], str]:
    """Check robots.txt for the domain"""
    try:
        url = urljoin(domain, "/robots.txt")
        status, text = await fetch_text(session, url)
        return status, text if text and not text.startswith("ERROR:") else ""
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {domain}: {e}")
        return None, ""

async def fetch_allowed_pages(
    session: aiohttp.ClientSession,
    domain: str,
    verify_name: str,
    host_manager: HostDelayManager,
    save_folder: Path
) -> Dict[str, Any]:
    """
    Fetch homepage and extra pages (only if robots doesn't disallow).
    Save HTML and text files into save_folder. Return dict of results.
    """
    try:
        parsed = urlparse(domain)
        host = parsed.netloc
        results = {"domain": domain, "homepage": {}, "extra": []}

        # Check robots.txt first
        await host_manager.wait(host)
        robots_status, robots_text = await check_robots(session, domain)
        results["robots_status"] = robots_status
        results["robots_txt_snippet"] = (robots_text or "")[:2000]

        # Simple robots check
        disallow_all = False
        if robots_text:
            if re.search(r"User-agent:\s*\*\s*Disallow:\s*/\s*$", robots_text, re.IGNORECASE | re.MULTILINE):
                disallow_all = True
                logger.info(f"Domain {domain} disallows all crawling")

        if disallow_all:
            results["note"] = "robots.txt disallows all"
            return results

        # Fetch homepage
        await host_manager.wait(host)
        homepage_status, homepage_html = await fetch_text(session, domain)
        results["homepage"]["status"] = homepage_status
        
        if homepage_status and isinstance(homepage_html, str) and not homepage_html.startswith("ERROR:"):
            # Save raw HTML
            safe_write_file(save_folder / "homepage.html", homepage_html)
            
            # Extract and save text
            text = extract_visible_text(homepage_html)
            safe_write_file(save_folder / "homepage.txt", text)
            
            results["homepage"]["has_company_name"] = company_name_in_text(verify_name, text)
            results["homepage"]["text_snippet"] = text[:2000]
            results["homepage"]["text_length"] = len(text)
        else:
            results["homepage"]["error"] = homepage_html if isinstance(homepage_html, str) else "Unknown error"
            logger.warning(f"Failed to fetch homepage for {domain}: {results['homepage']['error']}")

        # Fetch extra pages if homepage succeeded and robots allows
        if homepage_status and homepage_status < 400 and not disallow_all:
            for p in EXTRA_PATHS:
                try:
                    # Simple allow check: if robots contains Disallow for that path, skip
                    if robots_text and re.search(rf"Disallow:.*{re.escape(p)}", robots_text, re.IGNORECASE):
                        logger.debug(f"Skipping {p} for {domain} due to robots.txt")
                        continue
                    
                    page_url = urljoin(domain, p)
                    await host_manager.wait(host)
                    st, html = await fetch_text(session, page_url)
                    
                    if st and st < 400 and isinstance(html, str) and not html.startswith("ERROR:") and len(html) > 200:
                        fn_base = p.strip("/").replace("/", "_") or "root"
                        safe_write_file(save_folder / f"{fn_base}.html", html)
                        
                        txt = extract_visible_text(html)
                        safe_write_file(save_folder / f"{fn_base}.txt", txt)
                        
                        results["extra"].append({
                            "path": p,
                            "status": st,
                            "has_company_name": company_name_in_text(verify_name, txt),
                            "text_length": len(txt)
                        })
                        logger.debug(f"Successfully fetched {page_url}")
                except Exception as e:
                    logger.warning(f"Error fetching extra page {p} for {domain}: {e}")
                    continue
        
        return results
    except Exception as e:
        logger.error(f"Error in fetch_allowed_pages for {domain}: {e}")
        return {"domain": domain, "error": str(e)}

# ---------------------------
# WORKER
# ---------------------------
async def worker(
    name: str,
    queue: asyncio.Queue,
    session: aiohttp.ClientSession,
    host_manager: HostDelayManager,
    writer_lock: asyncio.Lock,
    processed_imos: set
):
    """Worker that processes companies from the queue"""
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        
        company_imo, company_name = item
        try:
            logger.info(f"[{name}] Processing {company_imo} — {company_name}")

            # Create output folder for company
            company_folder = OUT_FOLDER / f"{company_imo}"
            company_folder.mkdir(parents=True, exist_ok=True)

            # Skip if already processed (in-memory check)
            if company_imo in processed_imos:
                logger.info(f"[{name}] Skipping {company_imo} (already processed)")
                queue.task_done()
                continue

            # 1) Search company
            await host_manager.wait("duckduckgo.com")
            status, candidate = await search_company(session, company_name)
            
            if not candidate:
                async with writer_lock:
                    append_result_row(
                        company_imo, company_name, "", "NO_SITE_FOUND",
                        {"search_status": status, "timestamp": datetime.now().isoformat()}
                    )
                    processed_imos.add(company_imo)
                logger.warning(f"[{name}] No candidate found for {company_imo}")
                queue.task_done()
                continue

            # Normalize domain
            parsed = urlparse(candidate)
            if not parsed.scheme:
                candidate = "https://" + candidate
                parsed = urlparse(candidate)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            # 2) Fetch homepage and extras (with robots check)
            results = await fetch_allowed_pages(session, domain, company_name, host_manager, company_folder)

            # 3) Determine confidence
            conf = 0.0
            if results.get("homepage", {}).get("has_company_name"):
                conf = 0.9
            elif results.get("homepage", {}).get("status") and results["homepage"]["status"] < 400:
                conf = 0.4
            else:
                conf = 0.1

            # Check extra pages for company name if homepage didn't have it
            if conf < 0.9:
                for extra in results.get("extra", []):
                    if extra.get("has_company_name"):
                        conf = max(conf, 0.7)
                        break

            # 4) Save result row
            row_info = {
                "domain": domain,
                "confidence": conf,
                "homepage_status": results.get("homepage", {}).get("status"),
                "robots_status": results.get("robots_status"),
                "note": results.get("note", ""),
                "extra_pages_count": len(results.get("extra", [])),
                "timestamp": datetime.now().isoformat()
            }
            
            async with writer_lock:
                append_result_row(company_imo, company_name, domain, "OK", row_info)
                processed_imos.add(company_imo)

            logger.info(f"[{name}] ✅ Saved {company_imo} → {domain} (confidence: {conf:.2f})")

        except Exception as e:
            logger.error(f"[{name}] Error processing {company_imo}: {e}", exc_info=True)
            async with writer_lock:
                append_result_row(
                    company_imo, company_name, "", "ERROR",
                    {"error": str(e), "timestamp": datetime.now().isoformat()}
                )
                processed_imos.add(company_imo)
        finally:
            queue.task_done()

# ---------------------------
# CSV Helpers
# ---------------------------
def append_result_row(
    company_imo: str,
    company_name: str,
    domain: str,
    status_label: str,
    info_dict: Dict[str, Any]
):
    """Append a result row to the CSV file"""
    try:
        header = ["company_imo_number", "company_name", "domain", "status", "info"]
        write_header = not RESULTS_CSV.exists()
        
        with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(header)
            writer.writerow([company_imo, company_name, domain, status_label, str(info_dict)])
    except Exception as e:
        logger.error(f"Failed to write CSV row for {company_imo}: {e}")

def load_processed_imos() -> set:
    """Load already processed IMO numbers from results CSV"""
    processed = set()
    if RESULTS_CSV.exists():
        try:
            with open(RESULTS_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    processed.add(row["company_imo_number"].strip())
            logger.info(f"Loaded {len(processed)} already processed companies")
        except Exception as e:
            logger.error(f"Error loading processed IMOs: {e}")
    return processed

# ---------------------------
# MAIN RUN
# ---------------------------
async def main():
    """Main execution function"""
    try:
        logger.info("=" * 60)
        logger.info("Starting Maritime Company Scraper")
        logger.info("=" * 60)
        
        # Validate input file exists
        if not Path(INPUT_CSV).exists():
            logger.error(f"Input file {INPUT_CSV} not found!")
            return
        
        # Load already processed companies
        processed_imos = load_processed_imos()
        
        # Build queue
        queue = asyncio.Queue()
        companies = []
        
        try:
            with open(INPUT_CSV, newline='', encoding='utf-8') as f:
                rdr = csv.DictReader(f)
                for r in rdr:
                    imo = r["company_imo_number"].strip()
                    name = r["company_name"].strip()
                    if imo and name:
                        companies.append((imo, name))
                    else:
                        logger.warning(f"Skipping row with missing data: {r}")
        except Exception as e:
            logger.error(f"Error reading input CSV: {e}")
            return
        
        logger.info(f"Loaded {len(companies)} companies from {INPUT_CSV}")
        
        # Filter out already processed
        companies_to_process = [c for c in companies if c[0] not in processed_imos]
        logger.info(f"Will process {len(companies_to_process)} companies (skipping {len(companies) - len(companies_to_process)} already done)")
        
        if not companies_to_process:
            logger.info("No companies to process. Exiting.")
            return
        
        for comp in companies_to_process:
            queue.put_nowait(comp)

        # Start aiohttp session
        timeout = aiohttp.ClientTimeout(
            total=None,
            sock_connect=REQUEST_TIMEOUT,
            sock_read=REQUEST_TIMEOUT
        )
        conn = aiohttp.TCPConnector(
            limit_per_host=CONCURRENCY,
            limit=CONCURRENCY * 2,
            ssl=False
        )

        host_manager = HostDelayManager(min_delay=PER_HOST_DELAY)
        writer_lock = asyncio.Lock()

        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
            workers = []
            for i in range(CONCURRENCY):
                w = asyncio.create_task(
                    worker(f"W{i+1}", queue, session, host_manager, writer_lock, processed_imos)
                )
                workers.append(w)
            
            # Wait for all tasks to complete
            await queue.join()
            
            # Signal termination
            for _ in workers:
                await queue.put(None)
            
            await asyncio.gather(*workers)
        
        logger.info("=" * 60)
        logger.info("Scraping completed successfully!")
        logger.info(f"Results saved to: {RESULTS_CSV}")
        logger.info(f"Company data saved to: {OUT_FOLDER}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)