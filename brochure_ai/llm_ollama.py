import os
import logging
import requests

logger = logging.getLogger(__name__)

# Config básica
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# Ajusta al modelo que tengas: mira el resultado de /api/tags
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))


def chat_ollama(system_prompt: str, user_prompt: str) -> str:
    """
    Wrapper mínimo para Ollama usando /api/generate.
    - No usamos /api/chat.
    - No pasamos opciones raras.
    """

    # Prompt estilo instruct sencillo
    prompt = (
        f"<system>\n{system_prompt}\n</system>\n\n"
        f"<user>\n{user_prompt}\n</user>"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    logger.info("Ollama: calling /api/generate with model=%s", OLLAMA_MODEL)
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        if resp.status_code >= 400:
            logger.error("Ollama error %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
    except Exception as e:
        logger.error("Ollama request failed: %s", e)
        raise

    data = resp.json()
    # En Ollama, el texto va en 'response'
    return (data.get("response") or "").strip()