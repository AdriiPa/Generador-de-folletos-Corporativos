# Web scraping responsable
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Tuple, List
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36"
REQUEST_DELAY = 1.0  # segundos entre requests


def fetch_page(url: str, timeout: int = 15) -> str:
    """Descarga una página web respetando good practices."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    try:
        logger.info("Fetching page %s", url)
        time.sleep(REQUEST_DELAY)  # rate limiting
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype:
            logger.warning("Contenido no HTML en %s: %s", url, ctype)
            return ""
        return resp.text
    except requests.RequestException as e:
        logger.error("Error fetching page %s: %s", url, e)
        return ""  # NO propagamos excepción


def extract_links(html: str, base_url: str) -> List[str]:
    """Extrae todos los enlaces (solo mismo dominio), resolviendo relativos."""
    soup = BeautifulSoup(html or "", "html.parser")
    links: List[str] = []
    base_host = urlparse(base_url).netloc.lower()
    if base_host.startswith("www."):
        base_host = base_host[4:]

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        # Ignorar anclas y javascript
        if href.startswith('#') or href.lower().startswith('javascript:'):
            continue
        absolute_url = urljoin(base_url, href)
        host = urlparse(absolute_url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        # Filtrar solo URLs del mismo dominio
        if host == base_host or host.endswith("." + base_host):
            links.append(absolute_url)

    # Quitar duplicados manteniendo orden
    seen = set()
    deduped = []
    for u in links:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def clean_text(html: str) -> str:
    """Extrae texto limpio de HTML, eliminando scripts, styles, etc."""
    soup = BeautifulSoup(html or "", 'html.parser')
    for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
        el.decompose()
    text = soup.get_text(separator='\n', strip=True)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)


def scrape_and_extract(url: str) -> Tuple[str, List[str]]:
    """Función principal: descarga página y extrae enlaces."""
    html = fetch_page(url)
    if not html:
        logger.error("Página base vacía o no descargada: %s", url)
        return "", []
    links = extract_links(html, url)
    logger.info("Extracting links %d links form %s", len(links), url)
    return html, links