#Web scraping responsable
from venv import logger

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Tuple, List, Dict
import logging
import time

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