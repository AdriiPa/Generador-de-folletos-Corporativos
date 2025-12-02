# Generador de Folletos Corporativos con IA

> Pipeline end-to-end que, dado el nombre de una empresa y su web principal, **raspa** páginas relevantes, **selecciona** enlaces útiles, **compila** contenidos y **redacta** un folleto en **Markdown** (con **HTML** opcional). Funciona con **Ollama** (LLM local, gratis) o en **modo mock** (sin LLM).  
> **Extra**: soporta **_details(url)_** y **traducción del folleto a otro idioma** manteniendo el formato.

---

## 0) Scope del ejercicio (según enunciado)

**Objetivos de aprendizaje**

- Integrar **scraping responsable** con `requests + BeautifulSoup`.
- Diseñar **prompts** efectivos y **salidas estructuradas (JSON)**.
- Encadenar pasos: **scraping → filtrado de enlaces → compilación → brochure → traducción**.
- Entregar un proyecto **reproducible**: **CLI**, logs, (tests opcionales) y documentación.

**Requisitos funcionales (MVP)**

1. **Entrada**: `--company` y `--url`.
2. **Scraping**: descargar la **landing** y extraer enlaces internos (mismo dominio).
3. **Clasificación**: elegir enlaces **relevantes** (About/Company, Community, Careers, Blog/News, Success Stories/Clientes, Press/Partners).
4. **Normalización**: **URLs relativas → absolutas**; deduplicación; descarte de dominios externos.
5. **Compilación**: limpiar texto y extraer **metadatos** (title, h1/h2, meta description).
6. **Redacción**: generar **brochure Markdown** a partir de los contenidos; **HTML opcional**.
7. **Traducción (extra)**: traducir el folleto a un idioma destino (`--translate-to`) manteniendo el formato Markdown.
8. **Configuración**: parámetros por **CLI** y **variables de entorno**.
9. **Calidad**: **logs** y manejo de errores razonable; tests mínimos sugeridos.

---

## 1) Arquitectura del pipeline
┌─────────────┐     ┌──────────────────┐             ┌───────────────────────┐     ┌─-─────────────────┐
│  Scraping   │────▶│ Selección enlaces│───--------▶ │Compilación de páginas │────▶│ Brochure (MD/HTML)|
│ (landing)   │     │ (LLM / Mock)     │             │ (texto + metadatos)   │     │ (LLM / Mock)      │
└─────────────┘     └──────────────────┘             └───────────────────────┘     └─-─────────────────┘
requests+BS4        JSON {links:[{type,url}]}       clean_text(), title/h1/h2/desc      prompts con FACTS

Hardening clave
	•	Solo mismo dominio (host base o subdominios).
	•	Normalización + dedupe de URLs.
	•	fetch_page() registra errores, pero el pipeline continúa (URLs problemáticas se ignoran).
	•	Check básico de que lo que procesamos es HTML.
	•	User-Agent realista y posibilidad de rate limiting.
	•	Prompts con FACTS (title, headings, meta desc, URL) → se reduce el riesgo de invents.
	•	Cliente Ollama simplificado usando /api/generate con campo "model" obligatorio.
	•	Función details(url, ...) que implementa el _details(url) del enunciado:
	•	Orquesta scraping + selección + compilación + resumen en un solo bloque de texto.
	•	Función translate_brochure(text, target_lang) que traduce manteniendo la estructura Markdown.

---

## 2) Estructura del repositorio
Generador_Folletos/
├─ .venv/
├─ brochure-ai/
│  ├─ src/
│  │  ├─ init.py
│  │  ├─ cli.py               # CLI: orquesta los 4 pasos
│  │  ├─ scraping.py          # fetch_page, extract_links, clean_text
│  │  ├─ link_selector.py     # selección (LLM/Mock) + filtro dominio + JSON
│  │  ├─ compiler.py          # compila páginas y metadatos
│  │  ├─ brochure.py          # redacción del folleto (LLM/Mock)
│  │  └─ llm_ollama.py        # cliente Ollama con fallback
│  └─ tests/
│     ├─ init.py
│     ├─ test_scraping.py     # ejemplo: extract_links / clean_text
│     ├─ link_selector.py
│     ├─ scraping.py
│     └─ llm_ollama.py
├─ outputs/                   # resultados .md / .html
├─ .env.example
├─ requirements.txt
└─ README.md
---

## 3) Instalación y configuración

**Requisitos**
- Python **3.10+**
- [Ollama](https://ollama.com) en local (solo si usas modo LLM)
- Modelo instalado (ej.: `llama3:latest` o `llama3.2:latest`)

**Setup**
cd Generador_Folletos
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

**Variables de entorno (ejemplo)**
# Ollama
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3:latest
export OLLAMA_TEMPERATURE=0.2
# Si tu Ollama no expone /api/chat, fuerza /api/generate:
export OLLAMA_FORCE_GENERATE=true

# Alternativa sin LLM
export MOCK_MODE=false

4) Uso (CLI)
Modo LLM (recomendado)
python3 -m brochure-ai.src.cli \
  --company "Python Software Foundation" \
  --url "https://www.python.org" \
  --tone formal \
  --export-html
  --translate-to en
Modo Mock (sin LLM)

python3 -m brochure-ai.src.cli \
  --company "Distribuciones Hernan" \
  --url "https://www.distribucionesdh.com" \
  --tone formal \
  --export-html \
  --mock

En modo --mock:
	•	El selector de enlaces usa heurísticas regex sobre el path.
	•	El folleto se genera con una plantilla estática.
	•	La traducción (--translate-to) sigue necesitando LLM; si quieres mock total, no uses --translate-to.
	
Flags
  •	--company : nombre visible en el folleto
  •	--url     : URL base a raspar
  •	--tone    : formal | humorístico
  •	--export-html : genera .html además de .md
  •	--output-dir  : carpeta de salida (default outputs/)
  •	--mock        : fuerza plantilla mock (sin LLM)
  •	--translate-to: idioma destino para la traducción del folleto (ej. en, fr, de).

Salidas
	Para una empresa Hugging Face con --translate-to en:
	•	outputs/hugging_face_brochure.md → folleto original (ES, por defecto).
	•	outputs/hugging_face_brochure.html → HTML del folleto original.
	•	outputs/hugging_face_brochure_en.md → folleto traducido al idioma destino.
	•	outputs/hugging_face_brochure_en.html → HTML de la versión traducida.

⸻

5) Buenas prácticas implementadas (scraping responsable)
	•	User-Agent realista y requests con timeout.
	•	Preparado para rate limiting (esperas entre peticiones si se desea).
	•	Solo mismo dominio base / subdominios; se descartan enlaces externos en la capa de selección.
	•	Normalización de rutas relativas a absolutas + deduplicación.
	•	Validación básica de errores:
	•	fetch_page() loguea y levanta excepción controlada.
	•	Las URLs que dan 401/403/404 se ignoran sin tumbar el pipeline.
	•	Limpieza de HTML:
	•	Se eliminan script, style, noscript, iframe, svg y ruido habitual.
	•	Se devuelve texto “humano” para consumo del LLM.

⸻

6) Diseño de prompts y salida JSON (selección de enlaces)
	•	Prompt del selector instruye a devolver sólo JSON:
{
  "links": [
    { "type": "about", "url": "https://.../about", "score": 95, "rationale": "..." },
    { "type": "careers", "url": "https://.../jobs",  "score": 90, "rationale": "..." }
  ]
}

	•	Reglas duras, tanto en prompt como en código:
	•	Solo mismo dominio (host base o subdominios).
	•	Prioriza:
	•	About/Company
	•	Community
	•	Careers/Jobs
	•	Customers/Success Stories/Clients
	•	Blog/News/Press
	•	Partners/Alliances
	•	Excluye:
	•	login, signup, sign-in, register
	•	privacy, terms, cookies
	•	anchors #..., mailto:, tel:
	•	páginas de checkout/carrito, etc.
	•	Máximo 10 enlaces.
	•	Se usan FEWSHOTS (dos ejemplos completos user/assistant) para enseñar al modelo:
	•	Qué es relevante,
	•	Cómo debe ser la salida JSON.

Parseo robusto
	•	_parse_llm_response:
	•	Intenta extraer el bloque {...} aunque venga texto alrededor.
	•	Valida que links sea lista.
	•	Normaliza URLs y filtra por dominio.
	•	Deduplica y ordena por score desc.
	•	Recorta a un máximo de 10 enlaces.

⸻
7) Redacción del folleto y _details(url)

Compilación de contenido
	•	compile_pages(selected_links, main_html, base_url):
	•	Añade la landing como página type="home".
	•	Descarga cada enlace relevante seleccionado.
	•	Limpia el HTML → texto (clean_text).
	•	Extrae metadatos:
	•	title
	•	headings (h1, h2)
	•	description (meta description)
	•	Calcula summary usando description o los primeros caracteres del contenido.
	•	summarize_content(pages):
	•	Se asegura de que todas las páginas tengan un summary razonable.

Función _details(url) del enunciado
	•	Implementada como details(url, mock=False, max_chars=12000) en brochure.py:
	•	Internamente llama a:
	•	scrape_and_extract
	•	select_relevant_links
	•	compile_pages
	•	summarize_content
	•	_pages_for_prompt (para recortar el texto total)
	•	Devuelve un único bloque de texto con el contenido relevante, limitado por max_chars.

Generación del folleto
	•	generate_brochure(company_name, pages, tone, mock):
	•	Modo LLM:
	•	Construye:
	•	FACTS (JSON con type, url, title, headings, description de las páginas).
	•	Contenido adicional (texto plano concatenado y recortado).
	•	System prompt:
	•	Copywriter B2B, solo Markdown, prohibido inventar datos, anclado en FACTS.
	•	Estructura estándar:
	•	Resumen Ejecutivo
	•	Líneas de Servicio / Programas / Recursos
	•	Comunidad / Ecosistema / Sectores
	•	Evidencias / Casos / Recursos
	•	Próximos Pasos
	•	Modo MOCK:
	•	Devuelve un folleto estático genérico, útil para validar el flujo sin LLM.

---
8) Traducción del folleto

Función translate_brochure(brochure_text, target_lang="en")
	•	System prompt en inglés, rol de traductor profesional:
	•	Siempre responde solo en el idioma destino.
	•	Mantiene la estructura Markdown (encabezados, listas, negritas, links).
	•	User prompt:
	•	Indica Target language: <target_lang>.
	•	Incluye instrucciones explícitas para:
	•	No dejar frases en el idioma original.
	•	No añadir comentarios ni explicaciones.
	•	Respetar la estructura original del documento.
	•	Incluye un mini-ejemplo de traducción correcta para guiar al modelo.
	•	Output:
	•	Mismo Markdown, pero con el contenido traducido.
---
9) Testing (mínimo exigible)
Tests recomendados (no obligatorios para la entrega, pero alineados con la rúbrica):
	•	test_scraping.py:
	•	extract_links (normalización + filtrado de dominios en capas posteriores).
	•	clean_text (eliminar scripts/styles y ruido).
	•	test_link_selector.py:
	•	Parseo robusto del JSON del LLM (_parse_llm_response).
	•	Filtro de dominio y dedupe.
	•	test_llm_ollama.py:
	•	Manejo de errores cuando el modelo no existe.
	•	Payload correcto contra /api/generate.

Ejecución (si se implementan):
pytest -q
⸻

10) Logging y manejo de errores
	•	Nivel INFO por defecto; se traza cada fase principal:
	•	Step 1/4: Scraping …
	•	Step 2/4: Selecting relevant links
	•	Step 3/4: Compiling pages
	•	Step 4/4: Generating brochure
	•	Logs específicos de páginas compiladas, enlaces seleccionados, etc.
	•	Errores de scraping:
	•	Se loguean con nivel WARNING/ERROR.
	•	No detienen el pipeline completo (se salta la URL problemática).
	•	Errores LLM:
	•	Se loguea el status_code y el texto de la respuesta de Ollama.
	•	Si hay error crítico (404 modelo no encontrado, etc.), se aborta con mensaje claro.

⸻

11) Limitaciones y mejoras
	•	Modelos locales pequeños pueden generar copy menos “marketiniano”; se compensa con prompts anclados en FACTS.
	•	No se genera PDF nativo. Si se necesita, se puede imprimir el HTML a PDF desde el navegador.
	•	La traducción depende del modelo: algunos están más sesgados a un idioma concreto.
	•	Mejoras futuras:
	•	UI web mínima.
	•	Caché de scraping para no recargar la web objetivo en cada run.
	•	Soporte multi-idioma full (entrada en ES/EN y salida en varios idiomas).
	•	Tests automáticos adicionales.
⸻

12) Checklist de corrección (rúbrica)
	•	Scraping responsable (UA, rate limit, dominio)
	•	Filtrado y JSON estructurado de enlaces
	•	Encadenado completo scraping → selección → compilación → brochure
	•	CLI reproducible con logs
	•	Tests básicos y documentación
	•	Export Markdown + HTML opcional

⸻

13) Licencia / uso académico

Proyecto docente para la práctica “Generador de Folletos Corporativos con IA”
