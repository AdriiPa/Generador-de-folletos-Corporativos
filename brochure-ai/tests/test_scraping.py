"""
test_scraping.py - Tests para el módulo de scraping
"""
import pytest
from .scraping import clean_text, extract_links
from .link_selector import normalize_url


def test_clean_text_removes_scripts():
    """Test que clean_text elimina scripts."""
    html = """
    <html>
        <head><script>alert('test')</script></head>
        <body>
            <p>Hello World</p>
            <script>console.log('remove me')</script>
        </body>
    </html>
    """
    result = clean_text(html)
    assert 'script' not in result.lower()
    assert 'Hello World' in result


def test_clean_text_removes_styles():
    """Test que clean_text elimina estilos."""
    html = """
    <html>
        <style>body { color: red; }</style>
        <body><p>Content</p></body>
    </html>
    """
    result = clean_text(html)
    assert 'color: red' not in result
    assert 'Content' in result


def test_extract_links_basic():
    """Test extracción básica de enlaces."""
    html = """
    <html>
        <body>
            <a href="/about">About</a>
            <a href="/careers">Careers</a>
            <a href="#anchor">Skip</a>
        </body>
    </html>
    """
    base_url = "https://example.com"
    links = extract_links(html, base_url)

    assert len(links) >= 2
    assert any('about' in link for link in links)
    assert any('careers' in link for link in links)


def test_normalize_url_relative():
    """Test normalización de URLs relativas."""
    base = "https://example.com"
    relative = "/about"
    result = normalize_url(relative, base)
    assert result == "https://example.com/about"


def test_normalize_url_absolute():
    """Test que URLs absolutas no cambian."""
    base = "https://example.com"
    absolute = "https://example.com/careers"
    result = normalize_url(absolute, base)
    assert result == absolute


def test_extract_links_external_filtered():
    """Test que enlaces externos se filtran."""
    html = """
    <html>
        <body>
            <a href="/internal">Internal</a>
            <a href="https://external.com">External</a>
        </body>
    </html>
    """
    base_url = "https://example.com"
    links = extract_links(html, base_url)

    # Solo enlaces internos
    for link in links:
        assert 'example.com' in link


if __name__ == "__main__":
    pytest.main([__file__, "-v"])