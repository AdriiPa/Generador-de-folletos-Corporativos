#Web scraping responsable
from venv import logger

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Tuple, List, Dict
import logging
import time

from urllib3.util import url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENT="BrochureAI/1.0 (Educational Project; contact@example.com)"
REQUEST_DELAY=1.0 #Segundos entre requests

def fetch_page(url:str, timeout :int =10)->str:
    """Descarga una pagina web respetando good practices.
        Args:
            url: URL a descargar.
            timeout: timeout en segundos

        Returns:
            HTML de la pagina.
    """
    headers={
        "User-Agent":USER_AGENT,
        'Accept': ' text/html.application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
    }

    try:
        logger.info(f"Fetching page {url}")
        time.sleep(REQUEST_DELAY) #Rate limiting
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching page {url}: {e}")
        raise

def extract_links(html:str, base_url:str)->List[str]:
    """
    Extrae todos los enlaces de un html.

    Args:
        html: Contenido HTML de la pagina.
        base_url: URL base para resolver enlaces relativos.

    Returns:
         Lista de URLs absolutas
    """
    soup= BeautifulSoup(html, 'html.parser')
    links = []

    for a_tag in soup.find_all('a', href=True):
        href= a_tag['href']

        #Ignorar anclas y javascript
        if href.startswith('#') or href.startswith('javascript:'):
            continue

        #Convertir a Url absoluta
        absolute_url= urljoin(base_url, href)

        #Filtrar solo URLs del mismo dominio
        if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
            links.append(absolute_url)

    return list(set(links)) #Quitar suplicados

def clean_text(html:str)->str:
    """
    Extrae texto limpio de HTML, eliminado scripts,styles,etc

    Args:
         html:Contenido HTML de la pagina.
    Returns:
        Texto limpio de HTML.
    """

    soup= BeautifulSoup(html, 'html.parser')

    #Eliminar elementos que no quiero
    for elements in soup(["script", "style", "nav", "footer", "header", "aside"]):
        elements.decompose()

    #Obtener texto
    text=soup.get_text(separator='\n', strip=True)

    #Limpiar lineas vacias duplicadas
    lines=[line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def scrape_and_extract(url:str)->Tuple[str,List[str]]:
    """
    Funcion principal: descarga pagina y extra enlaces.

    Args:
        url: URL principal de la empresa

    Returns:
        Tupla (HTML, lista de enlaces)
    """

    try:
        html= fetch_page(url)
        links =extract_links(html, url)
        logger.info(f"Extracting links {len(links)} links form {url}")
        return  html , links
    except Exception as e:
        logger.error(f"Error scraping page {url}: {e}")
        raise