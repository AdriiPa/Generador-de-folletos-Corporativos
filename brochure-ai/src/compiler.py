import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup

from .scraping import fetch_page, clean_text

logger = logging.getLogger(__name__)


def extract_metadata(html: str, url: str, page_type: str = "page") -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    headings = [h.get_text(strip=True) for h in soup.select("h1, h2")][:10]
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()
    og = soup.find("meta", attrs={"property": "og:description"})
    if not meta_desc and og and og.get("content"):
        meta_desc = og["content"].strip()
    site_name = ""
    ogs = soup.find("meta", attrs={"property": "og:site_name"})
    if ogs and ogs.get("content"):
        site_name = ogs["content"].strip()
    return {
        "url": url,
        "type": page_type,
        "title": title,
        "headings": headings,
        "description": meta_desc,
        "site_name": site_name
    }


def compile_pages(selected: Dict, html_main: str, base_url: str) -> List[Dict[str, Any]]:
    """
    selected = {"links": [{"type": "...", "url": "..."}, ...]}
    """
    pages: List[Dict[str, Any]] = []

    # Home SIEMPRE = base_url
    home_dict: Dict[str, Any] = {
        "type": "home",
        "url": base_url,
        "content": clean_text(html_main),
    }
    home_dict.update(extract_metadata(html_main, home_dict["url"], "home"))
    home_dict["summary"] = home_dict["description"][:500] or home_dict["content"][:600]
    logger.info("Compilador de la pagina home: %s chars", len(home_dict["content"]))
    pages.append(home_dict)

    # Resto de páginas seleccionadas
    for item in selected.get("links", []):
        url = item.get("url")
        ptype = item.get("type", "page")
        if not url:
            continue
        try:
            html = fetch_page(url)
        except Exception as e:
            logger.error("Excepción inesperada en fetch_page(%s): %s", url, e)
            continue
        if not html:
            continue

        content = clean_text(html)
        page_dict: Dict[str, Any] = {"type": ptype, "url": url, "content": content}
        page_dict.update(extract_metadata(html, url, ptype))
        page_dict["summary"] = (page_dict.get("description") or "")[:500] or content[:600]
        logger.info("Compilador de la pagina %s: %s chars", ptype, len(content))
        pages.append(page_dict)

    return pages


def summarize_content(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for p in pages:
        if not p.get("summary"):
            p["summary"] = (p.get("description") or "")[:500] or (p.get("content") or "")[:600]
    return pages