# Generador de Folletos Corporativos con IA

> Pipeline end-to-end que, dado el nombre de una empresa y su web principal, **raspa** páginas relevantes, **selecciona** enlaces útiles, **compila** contenidos y **redacta** un folleto en **Markdown** (con **HTML** opcional). Funciona con **Ollama** (LLM local, gratis) o en **modo mock** (sin LLM).

---

## 0) Scope del ejercicio (según enunciado)

**Objetivos de aprendizaje**
- Integrar **scraping responsable** con `requests + BeautifulSoup`.
- Diseñar **prompts** efectivos y **salidas estructuradas (JSON)**.
- Encadenar pasos: **scraping → filtrado de enlaces → compilación → brochure**.
- Entregar un proyecto **reproducible**: **CLI**, logs, **tests** y **documentación**.

**Requisitos funcionales (MVP)**
1. **Entrada**: `--company` y `--url`.
2. **Scraping**: descargar la **landing** y extraer enlaces internos (mismo dominio).
3. **Clasificación**: elegir enlaces **relevantes** (About/Company, Community, Careers, Blog/News, Success Stories/Clientes, Press/Partners).
4. **Normalización**: **URLs relativas → absolutas**; deduplicación; descarte de dominios externos.
5. **Compilación**: limpiar texto y extraer **metadatos** (title, h1/h2, meta description).
6. **Redacción**: generar **brochure Markdown** a partir de los contenidos; **HTML opcional**.
7. **Configuración**: parámetros por **CLI** y **variables de entorno**.
8. **Calidad**: **logs**, manejo de errores y **tests** básicos.

---

## 1) Arquitectura del pipeline
┌─────────────┐     ┌──────────────────┐             ┌───────────────────────┐     ┌─-─────────────────┐
│  Scraping   │────▶│ Selección enlaces│───--------▶ │Compilación de páginas │────▶│ Brochure (MD/HTML)|
│ (landing)   │     │ (LLM / Mock)     │             │ (texto + metadatos)   │     │ (LLM / Mock)      │
└─────────────┘     └──────────────────┘             └───────────────────────┘     └─-─────────────────┘
requests+BS4        JSON {links:[{type,url}]}       clean_text(), title/h1/h2/desc      prompts con FACTS

**Hardening clave**
- Solo **mismo dominio** (host base o subdominios).
- **Normalización** + **dedupe** de URLs.
- `fetch_page()` **no aborta** el pipeline: si falla, **se ignora** la URL.
- Check de **Content-Type** (solo HTML).
- **Rate limiting** y `User-Agent` realista.
- Prompts con **FACTS** (title, headings, meta desc, URL) → sin invents.
- Cliente Ollama con **fallback** `/api/chat → /api/generate`.

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
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Variables de entorno (ejemplo)
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
Modo Mock (sin LLM)

python3 -m brochure-ai.src.cli \
  --company "Distribuciones Hernan" \
  --url "https://www.distribucionesdh.com" \
  --tone formal \
  --export-html \
  --mock
Flags
  •	--company : nombre visible en el folleto
  •	--url     : URL base a raspar
  •	--tone    : formal | humorístico
  •	--export-html : genera .html además de .md
  •	--output-dir  : carpeta de salida (default outputs/)
  •	--mock        : fuerza plantilla mock (sin LLM)

Salidas
	•	outputs/<slug_company>_brochure.md
	•	outputs/<slug_company>_brochure.html (si --export-html)

⸻

5) Buenas prácticas implementadas (scraping responsable)
	•	Rate limiting: espera corta entre peticiones.
	•	User-Agent realista y Accept correcto.
	•	Mismo dominio (host base o subdominios); se descartan externos.
	•	Normalización de rutas relativas a absolutas; dedupe.
	•	Validación de Content-Type (solo HTML).
	•	Manejo de errores no disruptivo (continúa aunque fallen URLs).

⸻

6) Diseño de prompts y salida JSON (selección de enlaces)
	•	Prompt del selector instruye a devolver sólo JSON:
{
  "links": [
   {"type":"about page", "url": "https://../about"},
   {"type":"careers page", "url":"https://.../jobs"}
}

	•	Reglas duras en prompt y en código:
	•	Solo mismo dominio.
	•	Prioriza About/Company, Community, Careers/Jobs, Blog/News/Press, Success Stories/Clientes, Partners.
	•	Excluye login/signup/privacy/terms/#/mailto.
	•	Máx. 10 enlaces.

⸻

7) Testing (mínimo exigible)
pytest -q

Cobertura sugerida
	•	test_scraping.py → extract_links (dominio+dedupe) y clean_text.
	•	link_selector.py (tests) → parseo robusto del JSON del LLM y filtro de dominio.
	•	llm_ollama.py (tests) → fallback /api/chat → /api/generate.
	•	scraping.py (tests) → fetch_page() tolerante a errores.

⸻

8) Logging y manejo de errores
	•	Nivel INFO por defecto; traza cada fase:
	•	“Step 1/4: Scraping …”
	•	“Found X links”
	•	“Selected Y relevant links”
	•	“Compiled Z pages”
	•	fetch_page() no levanta excepción: devuelve "" en fallo.
	•	Enlaces no válidos → se saltan sin tumbar el pipeline.

⸻

9) Limitaciones y mejoras
	•	Modelos locales pequeños pueden generar copy menos “marketiniano”; se compensa con FACTS (titles, h1/h2, meta desc, URL).
	•	No se genera PDF nativo (la práctica pide MD/HTML). Se puede imprimir el HTML a PDF si se necesita.
	•	Extensiones futuras: UI mínima web, cache de scraping, más tests, soporte multi-idioma.

⸻

10) Checklist de corrección (rúbrica)
	•	Scraping responsable (UA, rate limit, dominio)
	•	Filtrado y JSON estructurado de enlaces
	•	Encadenado completo scraping → selección → compilación → brochure
	•	CLI reproducible con logs
	•	Tests básicos y documentación
	•	Export Markdown + HTML opcional

⸻

11) Licencia / uso académico

Proyecto docente para la práctica “Generador de Folletos Corporativos con IA”
