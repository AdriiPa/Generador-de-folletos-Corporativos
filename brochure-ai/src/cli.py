# brochure-ai/src/cli.py
"""
cli.py - Interfaz de línea de comandos
"""
import argparse
import os
import sys
import logging
from pathlib import Path

from .scraping import scrape_and_extract
from .link_selector import select_relevant_links
from .compiler import compile_pages, summarize_content
from .brochure import generate_brochure

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).lower()


def save_markdown(content: str, filepath: str):
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"Brochure saved to: {filepath}")


def export_html(markdown_content: str, filepath: str):
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
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_html)
        logger.info(f"HTML exported to: {filepath}")
    except Exception as e:
        logger.error(f"Error exporting HTML: {e}")


def main():
    parser = argparse.ArgumentParser(description='Generador de Folletos Corporativos con IA')
    parser.add_argument('--company', required=True, help='Nombre de la empresa')
    parser.add_argument('--url', required=True, help='URL principal del sitio web')
    parser.add_argument('--tone', choices=['formal', 'humorístico'], default='formal', help='Tono del folleto')
    parser.add_argument('--output-dir', default='outputs', help='Directorio de salida')
    parser.add_argument('--export-html', action='store_true', help='Exportar también a HTML')
    parser.add_argument('--mock', action='store_true', help='Usar modo mock (sin LLM)')
    args = parser.parse_args()

    mock_mode = args.mock or os.getenv("MOCK_MODE", "false").lower() == "true"
    if mock_mode:
        os.environ['MOCK_MODE'] = 'true'
        logger.info("Running in MOCK mode (no LLM calls)")
    else:
        logger.info("Running in LLM mode (Ollama)")

    try:
        # Paso 1: Scraping
        logger.info(f"Step 1/4: Scraping {args.url}")
        html_main, links = scrape_and_extract(args.url)
        logger.info(f"Found {len(links)} links")

        # Autodetectar nombre real si pasas 'Ejemplo SA' u otro placeholder
        company_name = args.company
        lower_name = company_name.strip().lower()
        if lower_name in ("ejemplo sa", "ejemplo", "example", "demo", ""):
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_main, "html.parser")
                auto = None
                og_site = soup.find("meta", attrs={"property": "og:site_name"})
                if og_site and og_site.get("content"):
                    auto = og_site["content"].strip()
                elif soup.title and soup.title.string:
                    auto = soup.title.string.strip().split("—")[0].split("|")[0]
                if auto:
                    company_name = auto
                    logger.info(f"Auto-detected company name: {company_name}")
            except Exception as _:
                pass

        # Paso 2: Selección de enlaces
        logger.info("Step 2/4: Selecting relevant links")
        selected = select_relevant_links(args.url, links, mock=mock_mode)
        logger.info(f"Selected {len(selected.get('links', []))} relevant links")

        # Paso 3: Compilación
        logger.info("Step 3/4: Compiling page contents")
        pages = compile_pages(selected, html_main, base_url=args.url)
        pages = summarize_content(pages)
        logger.info(f"Compiled {len(pages)} pages")

        # Paso 4: Generación folleto
        logger.info("Step 4/4: Generating brochure")
        brochure_md = generate_brochure(company_name, pages, args.tone, mock=mock_mode)

        # Salvar
        slug = slugify(company_name)
        md_path = os.path.join(args.output_dir, f"{slug}_brochure.md")
        save_markdown(brochure_md, md_path)
        if args.export_html:
            html_path = os.path.join(args.output_dir, f"{slug}_brochure.html")
            export_html(brochure_md, html_path)

        logger.info("Brochure generation completed successfully!")
        print(f"\n{'=' * 60}\nBrochure saved to: {md_path}\n{'=' * 60}\n")
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()