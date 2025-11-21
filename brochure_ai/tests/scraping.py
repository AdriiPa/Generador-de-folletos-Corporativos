import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Tuple

logger = logging.getLogger(__name__)

def fetch_page(url: str, timeout: int = 15) -> str:
    """
    Descarga la página HTML de una URL con headers realistas.
    Devuelve el HTML plano como string.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error("Error fetching %s: %s", url, e)
        raise


def _normalize_url(href: str, base_url: str) -> str:
    """
    Convierte href en URL absoluta usando el base_url.
    """
    if not href:
        return None

    parsed = urlparse(href)

    # Caso: ya es absoluta
    if parsed.scheme and parsed.netloc:
        return href

    # Caso: relativa
    return urljoin(base_url, href)


def extract_links(html: str, base_url: str) -> List[str]:
    """
    Extrae TODOS los <a href="..."> del HTML, normalizados a URLs absolutas.
    No filtra por dominio aquí; eso se hace en link_selector.
    """
    soup = BeautifulSoup(html, "html.parser")
    raw_links = [a.get("href") for a in soup.find_all("a") if a.get("href")]

    normalized = []
    for href in raw_links:
        try:
            url = _normalize_url(href, base_url)
            if url:
                normalized.append(url)
        except Exception:
            continue

    # eliminar duplicados manteniendo orden
    seen = set()
    output = []
    for url in normalized:
        if url not in seen:
            seen.add(url)
            output.append(url)

    return output

def clean_text(html: str) -> str:
    """
    Limpia scripts, styles, iframes, SVG, etc. y devuelve texto plano.
    """
    soup = BeautifulSoup(html, "html.parser")

    # eliminar ruido
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # normalizar espacios y líneas
    lines = [line.strip() for line in text.splitlines()]
    clean = "\n".join([line for line in lines if line])

    return clean


def scrape_and_extract(url: str) -> Tuple[str, List[str]]:
    """
    Función principal usada por la CLI.
    - Descarga la página principal
    - Extrae links
    Devuelve:
        (html_main: str, links: List[str])
    """
    logger.info("Fetching main page: %s", url)

    html_main = fetch_page(url)
    links = extract_links(html_main, url)

    logger.info("Main page scraped: %d raw links", len(links))

    return html_main, links