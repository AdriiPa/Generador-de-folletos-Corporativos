#Seleccion de enlaces con LLM
import json
import os
import logging
from typing  import List, Dict, Optional
from urllib.parse import urlparse, urljoin
from openai import OpenAI

logger =logging.getLogger(__name__)

#Mock mode para testing sin API key
MOCK_MODE= os.getenv("MOCK_MODE", 'false').lower() == "true"

def normalize_url(url: str, base_url) -> str:
    """
    Convierte URLS relativas a absolutas
    Args:
        url: URL a normalizar
        base_url: URL base

    Returns:
        URL absoluta
    """

    return  urljoin(base_url, url)

def select_relevant_links_mock(base_url: str, links: List[str])->Dict:
    """
    Modo mock : seleccion simulada de enlaces.
    """

    logger.info("Using MOCK mode for link selection")

    #Filtrado simple por palabras clave en la URL
    keywords ={
        'about': 'about page',
        'company': 'company page',
        'careers': 'careers page',
        'jobs': 'careers page',
        'customers': 'customers page',
        'partners': 'partners page',
        'press': 'press page',
        'blog': 'blog page',
        'culture': 'culture page',
    }

    selected_links = []
    for link in links[:20]: #Limitacion a 20
        link_lower =link.lower()
        for keyword, page_types in keywords.items():
            if keyword in link_lower:
                selected_links.append({
                    "type": page_types,
                    "url": normalize_url(link, base_url),
                })
                break
    return  {"links": selected_links[:10]} #Nos quedamos con 10

def select_relevant_links_llm(base_url: str, links: List[str], api_key: str, model: str)-> Dict:
    """
    Usa LLM para seleccionar enlaces relevantes
    Args:
        base_url: URL base del sitio
        links: Lista de enlaces encontrados
        api_key: API key de OpenAI
        model: Modelo a usar

    Returns:
        Dict con enlaces seleccionados en formato JSON
    """
    try:
        client = OpenAI(api_key=api_key)
    except ImportError:
        logger.error("OpenAI Python SDK is not installed. Use MOCK_MODE=true")
        raise

    system_prompt ="""
                    Eres un asistente que recibe enlaces de un sitio y elige los más útiles para un folleto corporativo.
                    Responde SOLO en JSON con la forma:
                    {"links":[{"type":"about page","url":"https://..."},{"type":"careers page","url":"https://..."}]}
                    Incluye solo enlaces de valor (About, Company, Careers, Customers, Partners, Press, Culture, Blog relevante).
                    Excluye: TOS, Privacy, email, login, carrito, cuentas, términos legales.
                    Convierte cualquier enlace relativo a absoluto basado en el dominio de origen.
                    Máximo 10 enlaces.
                    """
    user_prompt =f"""
                    Dominio base:{base_url}
                    Enlaces encontrados:
                    {chr(10).join(links[:50])}
                    Selecciona los enlaces más relevantes para un folleto corporativo.     
                """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt},
            ],
            temperature=0.3,
            response_format={'type': "json_object"}
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM: {e}")
        #Fallback al modo mock
        return  select_relevant_links_mock(base_url, links)
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        raise

def select_relevant_links(base_url:str, links:List[str],
                          api_key:Optional[str]=None,
                          model:str ="gpt-4o-mini") -> Dict:
    """
    Punto de entrada principal par seleccion de enlaces

    Args:
        base_url: URL base
        links: Lista de enlaces
        api_key: API key de OpenAI
        model: Modelo a usar

    Returns:
        Dict con enlaces seleccionados en formato JSON
    """
    if MOCK_MODE or not api_key:
        return select_relevant_links_mock(base_url, links)
    else:
        return select_relevant_links_llm(base_url, links, api_key, model)
    
