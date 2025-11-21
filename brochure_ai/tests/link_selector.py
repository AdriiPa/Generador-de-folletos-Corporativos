import json
import os
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse, urljoin

import re

from .llm_ollama import chat_ollama

logger = logging.getLogger(__name__)
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

def _base_host(url: str) -> str:
    """
    Devuelve el host "normalizado" sin www.
    Ej: https://www.huggingface.co -> huggingface.co
    """
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _normalize_url(url: str, base_url: str) -> str:
    """
    Normaliza enlaces relativos a absolutos usando la URL base.
    """
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return url
    return urljoin(base_url, url)


def _same_domain(url: str, base_url: str) -> bool:
    """
    Filtra para quedarnos solo con enlaces del mismo dominio (o subdominios).
    """
    base = _base_host(base_url)
    host = _base_host(url)
    return host == base or host.endswith("." + base)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _score_link(url: str) -> int:
    """
    Heurística simple para el modo MOCK.
    Asigna un "score" en función de palabras clave típicas.
    """
    path = urlparse(url).path.lower()

    patterns = [
        (r"(about|company|nosotros|quienes\-somos)", 95, "about page"),
        (r"(careers|jobs|empleo|trabaja\-con\-nosotros)", 90, "careers"),
        (r"(customers|clients|casos|success\-stories|references)", 88, "customers"),
        (r"(community|comunidad|ecosystem)", 85, "community"),
        (r"(partners|alliances)", 80, "partners"),
        (r"(press|news|noticias)", 75, "press"),
        (r"(blog|insights|articles)", 70, "blog"),
    ]

    for pattern, base_score, page_type in patterns:
        if re.search(pattern, path):
            return base_score

    # si no matchea nada, score bajo
    return 40


def select_relevant_links_mock(base_url: str, links: List[str]) -> Dict[str, Any]:
    """
    Versión sin LLM para pruebas y modo offline.
    Filtra enlaces por dominio y los ordena por score heurístico.
    """
    logger.info("Link selector MOCK: %d links de entrada", len(links))

    normalized = [
        _normalize_url(l, base_url)
        for l in links
    ]
    normalized = _dedupe_keep_order(
        [l for l in normalized if _same_domain(l, base_url)]
    )

    scored: List[Dict[str, Any]] = []
    for url in normalized:
        score = _score_link(url)
        if score >= 60:  # umbral minimo razonable
            scored.append(
                {
                    "type": "auto",
                    "url": url,
                    "score": score,
                    "rationale": "Seleccionado por heurística MOCK",
                }
            )

    scored = sorted(scored, key=lambda x: x["score"], reverse=True)[:10]

    logger.info("Link selector MOCK: %d links seleccionados", len(scored))

    return {"links": scored}


def _build_system_prompt(base_url: str) -> str:
    dominio = _base_host(base_url)
    return f"""
Eres un asistente que selecciona enlaces útiles para construir un folleto corporativo
a partir de la web de una empresa.

REGLAS ESTRICTAS:
- Devuelve SOLO JSON válido, sin texto adicional ni comentarios.
- Estructura obligatoria:
  {{
    "links": [
      {{"type": "...", "url": "...", "score": 0-100, "rationale": "..."}},
      ...
    ]
  }}
- INCLUYE SOLO enlaces del MISMO DOMINIO que: {dominio} (mismo host o subdominios).
- Prioriza (por orden aproximado):
  - About / Company / Sobre nosotros / Quiénes somos
  - Community / Comunidad / Ecosystem
  - Careers / Jobs / Empleo
  - Customers / Clients / Success Stories / Casos de éxito
  - Partners / Alianzas
  - Press / News / Noticias
  - Blog / Insights / Articles
- EXCLUYE SIEMPRE:
  - login, signup, sign-in, register
  - privacidad, privacy, terms, condiciones, cookies
  - anchors internos (#algo), mails (mailto:), teléfonos (tel:)
  - carritos, checkout, ecommerce, pricing, demo si no aportan visión corporativa
- Convierte enlaces relativos a absolutos usando la URL base.
- Máximo 10 enlaces relevantes.
"""


FEWSHOTS: List[Dict[str, str]] = [
    # Ejemplo 1
    {
        "role": "user",
        "content": (
            "URL base: https://example.com\n\n"
            "Enlaces encontrados:\n"
            "https://example.com/\n"
            "https://example.com/about\n"
            "https://example.com/careers\n"
            "https://example.com/privacy\n"
            "https://example.com/login\n"
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "links": [
                    {
                        "type": "home",
                        "url": "https://example.com/",
                        "score": 85,
                        "rationale": "Landing principal de la compañía.",
                    },
                    {
                        "type": "about",
                        "url": "https://example.com/about",
                        "score": 95,
                        "rationale": "Página About con información clave sobre la empresa.",
                    },
                    {
                        "type": "careers",
                        "url": "https://example.com/careers",
                        "score": 88,
                        "rationale": "Sección de empleo y cultura.",
                    },
                ]
            },
            ensure_ascii=False,
        ),
    },
    # Ejemplo 2
    {
        "role": "user",
        "content": (
            "URL base: https://contoso.io\n\n"
            "Enlaces encontrados:\n"
            "https://contoso.io/\n"
            "https://contoso.io/customers\n"
            "https://contoso.io/blog\n"
            "https://contoso.io/terms\n"
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "links": [
                    {
                        "type": "home",
                        "url": "https://contoso.io/",
                        "score": 85,
                        "rationale": "Portada principal de la empresa.",
                    },
                    {
                        "type": "customers",
                        "url": "https://contoso.io/customers",
                        "score": 92,
                        "rationale": "Casos de clientes y referencias.",
                    },
                    {
                        "type": "blog",
                        "url": "https://contoso.io/blog",
                        "score": 80,
                        "rationale": "Artículos y recursos que muestran expertise.",
                    },
                ]
            },
            ensure_ascii=False,
        ),
    },
]


def _parse_llm_response(raw: str, base_url: str) -> Dict[str, Any]:
    """
    Intenta parsear la respuesta del LLM.
    - Asegura que se devuelve siempre {"links": [...]}
    - Normaliza URLs relativas y filtra por dominio.
    """
    if not raw:
        logger.warning("LLM devolvió respuesta vacía en selección de enlaces")
        return {"links": []}

    # En caso de que el modelo meta texto alrededor del JSON, intenta extraer el bloque {...}
    try:
        # buscar el primer '{' y el último '}'
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_json = raw[start : end + 1]
        else:
            raw_json = raw

        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.error("No se pudo parsear la respuesta del LLM como JSON: %s", raw[:200])
        return {"links": []}

    links = data.get("links", [])
    if not isinstance(links, list):
        logger.warning("Campo 'links' no es una lista en respuesta LLM")
        return {"links": []}

    cleaned: List[Dict[str, Any]] = []
    seen = set()

    for item in links:
        if not isinstance(item, dict):
            continue

        url = item.get("url")
        if not url:
            continue

        url = _normalize_url(str(url), base_url)

        # filtrar dominio
        if not _same_domain(url, base_url):
            continue

        if url in seen:
            continue
        seen.add(url)

        page_type = str(item.get("type", "page"))
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0

        rationale = str(item.get("rationale", "")).strip()

        cleaned.append(
            {
                "type": page_type,
                "url": url,
                "score": score,
                "rationale": rationale,
            }
        )

    # ordenar por score desc y limita a 10
    cleaned = sorted(cleaned, key=lambda x: x["score"], reverse=True)[:10]

    logger.info("LLM link selector: %d links limpios tras parseo", len(cleaned))

    return {"links": cleaned}


def select_relevant_links_llm(base_url: str, links: List[str]) -> Dict[str, Any]:
    """
    Llama al LLM (Ollama) para clasificar enlaces y devolver los relevantes.
    """
    # limpiamos la lista de entrada
    normalized = _dedupe_keep_order(
        [_normalize_url(l, base_url) for l in links]
    )
    normalized = [l for l in normalized if _same_domain(l, base_url)]

    logger.info("LLM link selector: %d links normalizados", len(normalized))

    if not normalized:
        logger.warning("No hay enlaces del mismo dominio, devolviendo vacío")
        return {"links": []}

    system_prompt = _build_system_prompt(base_url)
    user_prompt = f"URL base: {base_url}\n\nEnlaces encontrados:\n" + "\n".join(normalized)

    # Montamos el chat multishot
    messages = [
        {"role": "system", "content": system_prompt},
        *FEWSHOTS,
        {"role": "user", "content": user_prompt},
    ]

    full_system = messages[0]["content"]
    # concatenamos los ejemplos fewshot y el user real como texto
    fewshot_block = ""
    for m in messages[1:]:
        role = m["role"]
        content = m["content"]
        fewshot_block += f"\n\n[{role.upper()}]\n{content}"

    raw = chat_ollama(full_system, fewshot_block.strip())
    return _parse_llm_response(raw, base_url)


def select_relevant_links(base_url: str, links: List[str], mock: bool = False) -> Dict[str, Any]:
    """
    Punto de entrada usado por la CLI:
    - Devuelve SIEMPRE un dict con clave "links" -> lista de {type, url, score, rationale}.
    - Respeta MOCK_MODE global y el flag mock explícito.
    """
    if mock or MOCK_MODE:
        logger.info("Using MOCK mode for link selection")
        return select_relevant_links_mock(base_url, links)

    logger.info("Using LLM (Ollama) for link selection")
    return select_relevant_links_llm(base_url, links)