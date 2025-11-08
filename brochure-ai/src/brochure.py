import os
import logging
from typing import List, Any, Dict
import json
import re

from .llm_ollama import chat_ollama

logger = logging.getLogger(__name__)
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"


def _extract_text_from_pages(pages: List[Any]) -> List[str]:
    texts: List[str] = []
    for p in pages:
        if isinstance(p, dict):
            txt = p.get("summary") or p.get("content") or ""
        else:
            txt = str(p)
        if txt:
            texts.append(txt)
    return texts


def _facts_from_pages(pages: List[Dict]) -> List[Dict]:
    facts = []
    for p in pages[:10]:
        if isinstance(p, dict):
            facts.append({
                "type": p.get("type", "page"),
                "url": p.get("url", ""),
                "title": p.get("title", ""),
                "headings": (p.get("headings") or [])[:6],
                "description": (p.get("description") or "")[:320],
            })
    return facts


def _sanitize_brochure(md: str) -> str:
    md = re.sub(r"\[[^\]]+\]", "", md)                  # quita [placeholders]
    md = re.sub(r"(?m)^\s*[-*]\s*$\n?", "", md)         # bullets vacíos
    md = re.sub(r"(?m)^\s*#{1,3}\s*$\n?", "", md)       # headings vacíos
    md = re.sub(r"\n{3,}", "\n\n", md)                  # colapsa saltos
    return md.strip()


def generate_brochure_mock(company_name: str, pages: List[Any], tone: str = "formal") -> str:
    # SOLO cuando se usa --mock o MOCK_MODE=true
    company = company_name or "Nuestra compañía"
    brochure = f"# {company} – Folleto Corporativo\n\n"
    brochure += "> Socio tecnológico para acelerar tu roadmap digital.\n\n"
    brochure += "## Resumen Ejecutivo\n\n"
    brochure += (f"{company} ayuda a organizaciones que quieren profesionalizar su capa digital, "
                 "automatizar procesos clave y tomar decisiones basadas en datos.\n\n")
    brochure += "## Líneas de Servicio\n\n"
    brochure += "### Consultoría y Estrategia\n- Roadmap tecnológico.\n- Quick wins.\n- Gobierno y priorización.\n\n"
    brochure += "### Implementación Tecnológica\n- Integración de canales.\n- Automatización de procesos.\n\n"
    brochure += "## Próximos Pasos\n\nAgenda una sesión de descubrimiento para priorizar iniciativas.\n"
    return brochure


def generate_brochure_llm(company_name: str, pages: List[Any], tone: str = "formal") -> str:
    texts = _extract_text_from_pages(pages)
    joined_content = "\n\n".join(texts[:8])
    facts_json = json.dumps(_facts_from_pages(pages), ensure_ascii=False, indent=2)

    system_prompt = (
        "Eres un copywriter B2B. Entrega SOLO Markdown. PROHIBIDO placeholders o datos inventados. "
        "Usa explícitamente nombres propios, títulos, headings, descripciones y URLs de los FACTS. "
        "Si algo no aparece en FACTS/Contenido, omítelo. Tono: " + tone
    )

    user_prompt = (
        f"Empresa: {company_name}\n\n"
        f"FACTS (JSON fiable):\n{facts_json}\n\n"
        "Contenido libre (texto plano adicional):\n" + joined_content + "\n\n"
        "Redacta un folleto anclado en FACTS. Estructura EXACTA (omite secciones sin evidencia):\n"
        f"# {company_name} – Folleto Corporativo\n\n"
        "## Resumen Ejecutivo\n"
        "• 1–2 párrafos con misión/propósito y foco real detectado en FACTS.\n\n"
        "## Líneas de Servicio / Programas / Recursos\n"
        "• Bullets con capacidades, programas, publicaciones o iniciativas que aparezcan en títulos/headings.\n\n"
        "## Comunidad / Ecosistema / Sectores\n"
        "• Bullets con comunidades, eventos, públicos o sectores citados en FACTS.\n\n"
        "## Evidencias / Casos / Recursos\n"
        "• 4–8 bullets con nombres de páginas/secciones/recursos concretos (usa los títulos/headings).\n\n"
        "## Próximos Pasos\n"
        "• CTA coherente con lo observado (contribuir, unirse, descargar, participar, contactar).\n"
    )

    draft = chat_ollama(system_prompt, user_prompt)
    cleaned = _sanitize_brochure(draft)
    return cleaned or "# Folleto\n\n(El modelo devolvió salida vacía.)"


def generate_brochure(company_name: str, pages: List[Any], tone: str = "formal", mock: bool = False) -> str:
    if mock or MOCK_MODE:
        logger.info("Generating brochure in MOCK mode (explicit)")
        return generate_brochure_mock(company_name, pages, tone)

    logger.info("Generating brochure with OLLAMA")
    return generate_brochure_llm(company_name, pages, tone)