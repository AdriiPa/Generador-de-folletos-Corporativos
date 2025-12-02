# brochure_ai/src/llm_ollama.py
import os
import logging
import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

# Permite forzar el modo (opcional)
# OLLAMA_FORCE_CHAT=true  -> usa /api/chat y no intentes fallback
# OLLAMA_FORCE_GENERATE=true -> usa /api/generate directamente
FORCE_CHAT = os.getenv("OLLAMA_FORCE_CHAT", "false").lower() == "true"
FORCE_GENERATE = os.getenv("OLLAMA_FORCE_GENERATE", "false").lower() == "true"


def _chat_endpoint(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": OLLAMA_TEMPERATURE},
    }
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")


def _generate_endpoint(system_prompt: str, user_prompt: str) -> str:
    # Prompt simple compatible con plantillas instruct
    prompt = (
        f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n\n"
        f"{user_prompt}\n"
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": OLLAMA_TEMPERATURE},
    }
    resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


def chat_ollama(system_prompt: str, user_prompt: str) -> str:
    # Ruta forzada por variables de entorno
    if FORCE_GENERATE and not FORCE_CHAT:
        logger.info("Ollama: using /api/generate (forced)")
        return _generate_endpoint(system_prompt, user_prompt)
    if FORCE_CHAT and not FORCE_GENERATE:
        logger.info("Ollama: using /api/chat (forced)")
        return _chat_endpoint(system_prompt, user_prompt)

    # Ruta automática: intenta /api/chat y cae a /api/generate si no existe
    try:
        logger.info("Ollama: trying /api/chat")
        return _chat_endpoint(system_prompt, user_prompt)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 405, 501):
            logger.warning("Ollama /api/chat not available (status %s). Falling back to /api/generate.", status)
            return _generate_endpoint(system_prompt, user_prompt)
        # Otros errores HTTP: relanza
        raise
    except requests.RequestException:
        # Errores de conexión / timeouts: reintenta por /api/generate
        logger.warning("Ollama /api/chat request failed. Falling back to /api/generate.")
        return _generate_endpoint(system_prompt, user_prompt)