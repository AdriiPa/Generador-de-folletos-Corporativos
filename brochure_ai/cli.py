"""
CLI - Generador de folletos corporativos con IA
"""
import argparse
import os
import sys
import logging
from pathlib import Path
from bs4 import BeautifulSoup

from .scraping import scrape_and_extract
from .link_selector import select_relevant_links
from .compiler import compile_pages, summarize_content
from .brochure import generate_brochure, translate_brochure

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """
    Convierte un nombre arbitrario a un slug de fichero sencillo
    """
    return "".join(c if c.isalnum() else "_" for c in text).lower()


def save_markdown(content: str, filepath: str):
    """
    Persiste contenido MD en disco creando carpetas si hace falta
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content,encoding="utf-8")
    logger.info(f"Contenido MD guardadi en disco {path}")


def export_html(markdown_content: str, filepath: str):
    """
    Exporta MD a HTML sencillo y legible
    """
    try:
        import markdown
    except ImportError:
        logger.warning("markdown library not installed. Skipping HTML export.")
        return

    try:
        html = markdown.markdown(markdown_content)
        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Corporate Brochure</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
h2 {{ color: #34495e; margin-top: 30px; }}
h3 {{ color: #555; }}
ul {{ padding-left: 20px; }}
li {{ margin: 8px 0; }}
hr {{ margin: 30px 0; border: none; border-top: 1px solid #ddd; }}
</style>
</head>
<body>
{html}
</body>
</html>"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(full_html, encoding="utf-8")
        logger.info("HTML exported to: %s", path)
    except Exception as e:
        logger.error("Error exporting HTML: %s", e)

def _autodetect_company_name(html_main:str, fallback:str)->str:
    """
    Intenta extraer un nombre de empresa razonable del HTML si el nombre pasado
    es un placeholder como 'EJEMPLO SA'
    """
    lower_name= fallback.strip().lower()
    if lower_name not in ("ejemplo sa","ejemplo","example","demo",""):
        return fallback

    try:
        soup=BeautifulSoup(html_main,"html.parser")
        auto = None
        og_site= soup.find("meta", attrs={"property":"og:site_name"})
        if og_site and og_site.get("content"):
            auto = og_site.get("content").strip()
        elif soup.title and soup.title.string:
            auto = soup.title.string.strip().split("_")[0].split("|")[0]

        if auto:
            logger.info(f"Autodetected company name: {auto}")
            return auto
    except Exception as e:
        logger.error("Error autodetecting company name: %s", e)
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Generador de Folletos Corporativos con IA")
    parser.add_argument("--company", required=True, help="Nombre de la empresa")
    parser.add_argument("--url", required=True, help="URL principal del sitio web")
    parser.add_argument(
        "--tone",
        choices=["formal", "humorístico"],
        default="formal",
        help="Tono del folleto",
    )
    parser.add_argument("--output-dir", default="outputs", help="Directorio de salida")
    parser.add_argument(
        "--export-html",
        action="store_true",
        help="Exportar también a HTML",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Usar modo mock (sin LLM)",
    )
    parser.add_argument(
        "--translate-to",
        help="Si se indica, traduce el folleto al idioma destino (por ejemplo: en, fr, de)",
    )

    args = parser.parse_args()

    mock_mode = args.mock or os.getenv("MOCK_MODE", "false").lower() == "true"
    if mock_mode:
        os.environ["MOCK_MODE"] = "true"
        logger.info("Running in MOCK mode (no LLM calls)")
    else:
        logger.info("Running in LLM mode (Ollama)")

    try:
        # Paso 1: Scraping
        logger.info("Step 1/4: Scraping %s", args.url)
        html_main, links = scrape_and_extract(args.url)
        logger.info("Found %d links", len(links))

        # Autodetectar nombre real si pasas 'Ejemplo SA' u otro placeholder
        company_name = _autodetect_company_name(html_main, args.company)

        # Paso 2: Selección de enlaces con LLM o mock
        logger.info("Step 2/4: Selecting relevant links")
        selected = select_relevant_links(args.url, links, mock=mock_mode)
        logger.info("Selected %d relevant links", len(selected.get("links", [])))

        # Paso 3: Compilar y resumir contenido
        logger.info("Step 3/4: Compiling pages")
        pages = compile_pages(selected, html_main, base_url=args.url)
        pages = summarize_content(pages)
        logger.info("Compiled %d pages", len(pages))

        # Paso 4: Generación folleto
        logger.info("Step 4/4: Generating brochure")
        brochure_md = generate_brochure(company_name, pages, args.tone, mock=mock_mode)

        slug = slugify(company_name)
        out_dir = args.output_dir

        # Guardar folleto original
        md_path = os.path.join(out_dir, f"{slug}_brochure.md")
        save_markdown(brochure_md, md_path)
        if args.export_html:
            html_path = os.path.join(out_dir, f"{slug}_brochure.html")
            export_html(brochure_md, html_path)

        # Traducción opcional
        translated_paths = []
        if args.translate_to:
            target = args.translate_to
            logger.info("Translating brochure to %s", target)
            brochure_tr = translate_brochure(brochure_md, target_lang=target)
            md_tr_path = os.path.join(out_dir, f"{slug}_brochure_{target}.md")
            save_markdown(brochure_tr, md_tr_path)
            translated_paths.append(md_tr_path)

            if args.export_html:
                html_tr_path = os.path.join(out_dir, f"{slug}_brochure_{target}.html")
                export_html(brochure_tr, html_tr_path)
                translated_paths.append(html_tr_path)

        logger.info("Brochure generation completed successfully!")
        print("\n" + "=" * 60)
        print(f"Brochure saved to: {md_path}")
        if translated_paths:
            for p in translated_paths:
                print(f"Translated version saved to: {p}")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error("Error during execution: %s", e)
        sys.exit(1)
if __name__ == "__main__":
    main()