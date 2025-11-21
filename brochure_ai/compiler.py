import logging
from typing import Dict, List, Any

from bs4 import BeautifulSoup

from .scraping import fetch_page, clean_text

logger = logging.getLogger(__name__)


def extract_metadata(html: str, url: str, page_type: str = "page") -> Dict[str, Any]:
    """
    Extrae metadatos básicos de una página HTML:
    - title
    - headings (h1, h2)
    - meta description
    """
    soup = BeautifulSoup(html or "", "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    headings = [h.get_text(strip=True) for h in soup.select("h1, h2")][:10]

    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    return {
        "title": title,
        "headings": headings,
        "description": meta_desc,
    }


def compile_pages(
    selected_links: Dict[str, Any],
    main_html: str,
    base_url: str,
) -> List[Dict[str, Any]]:
    """
    A partir de:
      - HTML principal (landing)
      - diccionario de enlaces seleccionados por el LLM
        {"links": [ { "type": "...", "url": "...", ... }, ... ]}
      - base_url

    Construye una lista de páginas normalizadas con:
      - type
      - url
      - content (texto limpio)
      - title
      - headings
      - description
      - summary
    """
    pages: List[Dict[str, Any]] = []

    # 1) Página principal (landing)
    if main_html:
        content = clean_text(main_html)
        main_page: Dict[str, Any] = {
            "type": "home",
            "url": base_url,
            "content": content,
        }
        main_page.update(extract_metadata(main_html, base_url, "home"))
        main_page["summary"] = (
            (main_page.get("description") or "")[:500]
            or content[:600]
        )
        logger.info(
            "Compilada landing (%s): %s chars",
            base_url,
            len(content),
        )
        pages.append(main_page)

    # 2) Páginas seleccionadas por el LLM (About, Careers, Customers, etc.)
    items = selected_links.get("links", []) if isinstance(selected_links, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue

        url = item.get("url")
        if not url or url == base_url:
            continue

        ptype = item.get("type") or "page"

        try:
            html = fetch_page(url)
        except Exception as e:
            logger.warning("Error al descargar %s: %s", url, e)
            continue

        content = clean_text(html)
        page_dict: Dict[str, Any] = {
            "type": ptype,
            "url": url,
            "content": content,
        }
        page_dict.update(extract_metadata(html, url, ptype))
        page_dict["summary"] = (
            (page_dict.get("description") or "")[:500]
            or content[:600]
        )

        logger.info(
            "Compilada página %s (%s): %s chars",
            url,
            ptype,
            len(content),
        )
        pages.append(page_dict)

    return pages


def summarize_content(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Garantiza que cada página tenga un campo 'summary':
    - prioriza la description
    - si no hay, usa los primeros caracteres del content
    """
    for p in pages:
        if not p.get("summary"):
            desc = p.get("description") or ""
            content = p.get("content") or ""
            p["summary"] = (desc[:500] or content[:600])
    return pages