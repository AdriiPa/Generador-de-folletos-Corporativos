import json
import os
import logging
from typing import List, Dict
from urllib.parse import urlparse, urljoin
import re

from .llm_ollama import (chat_ollama)

logger = logging.getLogger(__name__)
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"


def _base_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _same_site(u: str, base_url: str) -> bool:
    """Mismo dominio que la base (mismo host o subdominio)."""
    host = urlparse(u).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    base = _base_host(base_url)
    return host == base or host.endswith("." + base)


def normalize_url(url: str, base_url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return url
    return urljoin(base_url, url)


def _dedupe_keep_order(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        key = it.get("url")
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def select_relevant_links_mock(base_url: str, links: List[str]) -> Dict:
    """Mock filtrando SOLO mismo dominio + dedupe."""
    normalized = [normalize_url(l, base_url) for l in links]
    selected = []
    for url in normalized:
        if not _same_site(url, base_url):
            continue
        if any(x in url.lower() for x in [
            "sobre", "about", "company", "community", "careers", "empleo",
            "success", "story", "clientes", "blog", "noticias", "press"
        ]):
            selected.append({"type": "page", "url": url})
        if len(selected) >= 8:
            break
    if not selected:
        selected.append({"type": "home", "url": base_url})
    return {"links": _dedupe_keep_order(selected)}


def _parse_llm_response(raw: str, base_url: str) -> Dict:
    # 1) Intento JSON directo
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 2) Extraer el primer bloque {...}
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            logger.warning("No se encontró JSON en la respuesta del LLM")
            return {"links": []}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            logger.warning("No se pudo parsear la respuesta del LLM como JSON")
            return {"links": []}

    if not isinstance(data, dict):
        logger.warning("Respuesta del LLM no es un JSON dict")
        return {"links": []}

    raw_links = data.get("links") or data.get("selected_links") or []
    if not isinstance(raw_links, list):
        logger.warning("Campo 'links' no es lista")
        return {"links": []}

    final_links = []
    for item in raw_links:
        if isinstance(item, dict):
            url = item.get("url")
            page_type = item.get("type", "page")
        elif isinstance(item, str):
            url = item
            page_type = "page"
        else:
            continue
        if not url:
            continue
        # Normaliza primero
        full = normalize_url(url, base_url)
        # Solo mismo dominio
        if not _same_site(full, base_url):
            continue
        final_links.append({"type": page_type, "url": full})

    # Dedupe + límite
    final_links = _dedupe_keep_order(final_links)[:10]
    return {"links": final_links}


def select_relevant_links_llm(base_url: str, links: List[str]) -> Dict:
    system_prompt = f"""
Eres un asistente que selecciona enlaces útiles para un folleto corporativo.

REGLAS ESTRICTAS:
- Devuelve SOLO JSON válido, sin texto adicional:
  {{
    "links": [
      {{"type": "about page", "url": "https://..."}},
      ...
    ]
  }}
- INCLUYE SOLO enlaces del MISMO DOMINIO que: {_base_host(base_url)} (mismo host o subdominios).
- Prioriza: About/Company/Sobre nosotros, Community/Comunidad, Careers/Jobs/Empleo,
  Success Stories/Clientes, Partners, Press/News/Noticias, Blog.
- EXCLUYE: login, signup, privacidad, términos, anchors (#), emails, carritos.
- Convierte relativos a absolutos con la URL base. Máximo 10.
"""
    user_prompt = f"URL base: {base_url}\n\nEnlaces encontrados:\n" + "\n".join(links)
    raw = chat_ollama(system_prompt, user_prompt)
    return _parse_llm_response(raw, base_url)


def select_relevant_links(base_url: str, links: List[str], mock: bool = False) -> Dict:
    if mock or MOCK_MODE:
        logger.info("Using MOCK mode for link selection")
        return select_relevant_links_mock(base_url, links)
    logger.info("Using OLLAMA for link selection")
    return select_relevant_links_llm(base_url, links)