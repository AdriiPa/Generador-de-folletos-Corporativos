import os
import logging
from typing import List, Any, Dict
import json
import re

from .llm_ollama import chat_ollama
from .scraping import scrape_and_extract
from .link_selector import select_relevant_links
from .compiler import compile_pages,summarize_content

logger = logging.getLogger(__name__)
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"


def _extract_text_from_pages(pages: List[Any]) -> List[str]:
    """
    Extrae bloques de texto de la lista de paginas.
    Prioriza:
    - summary
    - content
    Si la pagina es un dict. Si no convierte a str
    """
    texts: List[str] = []
    for p in pages:
        if isinstance(p, dict):
            txt = p.get("summary") or p.get("content") or ""
        else:
            txt = str(p)
        if txt:
            texts.append(txt)
    return texts


def _facts_from_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construye una lista compacta de facts por pagina para alimentar al LLM
    - type
    - url
    - title
    - headings (h1, h2)
    - description (meta description)
    """
    facts: List[Dict[str, Any]] = []
    for p in pages[:10]:
        if isinstance(p, dict):
            continue

        facts.append({
            "type": p.get("type", "page"),
            "url": p.get("url", ""),
            "title": p.get("title", ""),
            "headings": (p.get("headings") or [])[:6],
            "description": (p.get("description") or "")[:320],
        })
    return facts

def _pages_for_prompt(pages: List[Any], max_chars:int=12000)->str:
    """
    Junta el contenido relevante de las paginas en un unico bloque de texto,
    respetando un limite de caracteres para no inflar el contetxo del LLM
    """
    chunks = _extract_text_from_pages(pages)
    if not chunks:
        return ""

    buf:List[str] = []
    total=0
    for chunk in chunks:
        if total + len(chunk) >max_chars:
            #cortamos el chunk final si es necesario
            remaining=max_chars-total
            if remaining>0:
                buf.append(chunk[:remaining])
                total+=re
            break
        buf.append(chunk)
        total+=len(chunk)
    return "\n\n".join(buf)


def _sanitize_brochure(md: str) -> str:
    """
    Limpia ruido tipico de la salida del modelo:
    -placeholders
    -bullets vacios
    - heading vacios
    - saltos de linea redundante
    """
    # quita [placeholders]
    md = re.sub(r"\[[^\]]+\]", "", md)
    # bullets vacíos
    md = re.sub(r"(?m)^\s*[-*]\s*$\n?", "", md)
    # headings vacíos
    md = re.sub(r"(?m)^\s*#{1,3}\s*$\n?", "", md)
    # colapsa saltos
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def generate_brochure_mock(company_name: str, pages: List[Any], tone: str = "formal") -> str:
    # SOLO cuando se usa --mock o MOCK_MODE=true
    """
    Genera un folleto estatico para pruebas locales cuando:
    -se usa --mock en la CLI, o
    - MOCK_MODE=true en el entorno
    """
    company = company_name or "Nuestra compañía"
    brochure = f"# {company} – Folleto Corporativo\n\n"
    brochure += "> Socio tecnológico para acelerar tu roadmap digital.\n\n"

    brochure += "## Resumen Ejecutivo\n\n"
    brochure += (
        f"{company} ayuda a organizaciones que quieren profesionalizar su capa digital, "
                 "automatizar procesos clave y tomar decisiones basadas en datos.\n\n"

    )
    brochure += "## Líneas de Servicio\n\n"
    brochure += ("### Consultoría y Estrategia\n"
                 "- Roadmap tecnológico.\n"
                 "- Quick wins.\n"
                 "- Gobierno y priorización.\n\n")
    brochure += (
        "### Implementación y Datos\n"
        "- Integraciones.\n"
        "- Orquestación de datos.\n"
        "- Visualización y reporting.\n\n"
    )

    brochure += "## Casos y Comunidad\n\n"
    brochure += (
        "- Acompañamiento a empresas en su adopción de soluciones cloud.\n"
        "- Trabajo cercano con equipos internos para asegurar adopción.\n\n"
    )

    brochure += "## Próximos Pasos\n\n"
    brochure += (
        "Si quieres explorar cómo aplicar estas capacidades en tu organización, "
        "agenda una conversación con nuestro equipo.\n"
    )
    return brochure


def generate_brochure_llm(company_name: str, pages: List[Any], tone: str = "formal") -> str:
    """
    Genera el folleto llamando al LLM con:
    -FACTS (json compacto)
    - CONTENIDO libre (texto recortado de las paginas)
    """

    texts_for_prompt= _pages_for_prompt(pages, max_chars=12000)
    facts_json= json.dumps(_facts_from_pages(pages), ensure_ascii=False, indent=2)

    system_prompt = (
        "Eres un copywriter B2B. Entrega SOLO Markdown. "
        "PROHIBIDO inventar datos o usar placeholders. "
        "Tu misión es redactar un folleto corporativo sólido usando únicamente los FACTS "
        "y el contenido proporcionado. Tono: " + tone
    )

    user_prompt = (
        f"Empresa: {company_name}\n\n"
        f"FACTS (JSON fiable):\n{facts_json}\n\n"
        "Contenido adicional (texto libre):\n"
        f"{texts_for_prompt}\n\n"
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
    """
    Punto de entrada actual utilizado por CLI.
    - Si mock=TRUE o MOCK_MODE=true -> usa generate_brochure_mock
    - En caso contrario -> usa generate_brochure_llm
    """
    if mock or MOCK_MODE:
        logger.info("Generating brochure in MOCK mode (explicit)")
        return generate_brochure_mock(company_name, pages, tone)

    logger.info("Generating brochure with OLLAMA")
    return generate_brochure_llm(company_name, pages, tone)

def details(url:str, mock:bool = False,max_chars:int=12000) -> str:
    """
    Hace scraping de la landing
    -Selecciona enlaces relevantes con LLM.
    -Compila y resume paginas.
    -Devuelve un unico bloque de texto recortado a max_chars
    """
    html_main, links =scrape_and_extract(url)
    selected=select_relevant_links(url,links,mock=mock)
    pages = compile_pages(selected,html_main,base_url=url)
    pages= summarize_content(pages)
    return _pages_for_prompt(pages,max_chars=max_chars)

def translate_brochure(brochure_text:str, target_lang:str="en")->str:
    """
    Traduce un folleto manteniendo EXACTAMENTE  el formato Markdown.
    Se apoya en el mismo backend LLM (Ollama)
    """
    system_prompt = {
        "Eres un traductor profesional"
        "Tu objetivo es traducir el texto manteniendo EXACTAMENTE el mismo formato Markdown."
        "(encabezados, listas, enfasis) y la misa estructura"
        "No añadas comentarios ni explicaciones."
    }

    user_prompt = f"""
Traduce el siguiente folleto al idioma : {target_lang}.
No cambies la estructura de secciones ni el formato Markdown.

Texto:
\"\"\"markdown
{brochure_text}
\"\"\"
""".strip()

    translated= chat_ollama(system_prompt, user_prompt)
    return translated.strip() if translated else brochure_text