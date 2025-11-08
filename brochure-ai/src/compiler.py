#Compilacion de contenidos
import logging
from typing import Dict
from scraping import fetch_page,clean_text

logger = logging.getLogger(__name__)

def compile_pages(selected_links:Dict,main_html:str)->Dict[str,str]:
    """
    Descarga y compila el contenido de las paginas seleccionadas
    Args:
        selected_links: DIct con los enlaces seleccionados por el LLM
        main_html: HTML de la pagina principal

    Returns:
        Dict con el contenido de las paginas seleccionadas
    """

    pages={
        "landing": clean_text(main_html)
    }

    for item in selected_links.get("links",[]):
        page_type = item.get("type","unknown")
        url =item.get("url")

        if not url:
            continue

        try:
            html= fetch_page(url)
            cleaned_html = clean_text(html)

            #Limpiar longitud del texto (max 5000 caracteres)
            if len(cleaned_html) >5000:
                cleaned_html = cleaned_html[:5000]

            pages[page_type] = cleaned_html
            logger.info(f"Compilador de la pagina {page_type}: {len(cleaned_html)} chars")

        except Exception as e:
            logger.warning(f"Failed to fecth {url}: {e}")
            continue

    return pages

def summarize_content(pages:Dict[str,str], max_chars:int=3000)->Dict[str,str]:
    """
    Reduce el contenido de cada pagina para no exceder limites de tokens
    Args:
        pages: Dict con contenidos
        max_chars: Maximo de caracteres de la pagina

    Returns:
        Dict con el contenido de cada pagina
    """

    summarized={}
    for page_type, content in pages.items():
        if len(content) > max_chars:
            #tomar inicio y fin
            half= max_chars//2
            summarized[page_type]=(
                content[:half] +
                "\n\n[...contenido omitido...]\n\n" +
                content[-half:]
            )
        else:
            summarized[page_type] = content

    return summarized