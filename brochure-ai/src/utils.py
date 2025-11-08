#Funciones auxiliares

import logging
from typing import Optional
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """
    Valida que una URL tenga formato correcto.

    Args:
        url: URL a validar

    Returns:
        True si es válida
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def check_robots_txt(base_url: str, user_agent: str = "BrochureAI") -> Optional[str]:
    """
    Verifica robots.txt del sitio (función informativa).

    Args:
        base_url: URL base del sitio
        user_agent: User agent a verificar

    Returns:
        Contenido de robots.txt o None
    """
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200:
            logger.info(f"robots.txt found at {robots_url}")
            return response.text
        else:
            logger.info("No robots.txt found")
            return None

    except Exception as e:
        logger.warning(f"Could not check robots.txt: {e}")
        return None


def estimate_tokens(text: str) -> int:
    """
    Estima el número de tokens en un texto (aproximado).

    Args:
        text: Texto a estimar

    Returns:
        Número estimado de tokens
    """
    # Aproximación: ~4 caracteres por token
    return len(text) // 4


def truncate_text(text: str, max_tokens: int = 1000) -> str:
    """
    Trunca texto para no exceder cierto número de tokens.

    Args:
        text: Texto a truncar
        max_tokens: Máximo de tokens

    Returns:
        Texto truncado
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


def format_page_types(selected_links: dict) -> str:
    """
    Formatea los tipos de páginas seleccionadas para logging.

    Args:
        selected_links: Dict con enlaces seleccionados

    Returns:
        String formateado
    """
    types = [link.get('type', 'unknown') for link in selected_links.get('links', [])]
    return ", ".join(types)