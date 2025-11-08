#Generacion de folleto
import os
import logging
from typing import Dict,Optional
from datetime import datetime
from openai import OpenAI

logger=logging.getLogger(__name__)

MOCK_MODE= os.getenv('MOCK_MODE','false').lower() == 'true'

def generate_brochure_mock(company_name:str, pages:Dict[str,str], tone:str)->str:
    """
    Genera un folleto de ejemplo en modo MOCK
    Args:
        company_name: Nombre de la compañia
        pages: Paginas
        tone: TOno

    Returns:
        Genera el contenido de cada pagina
    """
    logger.info('Generating mock pages')
    date_str = datetime.today().strftime('%Y/%m/%d')

    return f"""#{company_name}
    ## Innovación y Excelencia en Tecnología

    ### Qué Hacemos
    
    {company_name} es una empresa líder en el sector tecnológico que se dedica a proporcionar soluciones innovadoras para empresas y profesionales. Nuestro enfoque se centra en la calidad, la innovación y el servicio al cliente.
    
    Trabajamos constantemente para mejorar nuestros productos y servicios, manteniéndonos a la vanguardia de las últimas tendencias tecnológicas.
    
    ### Nuestros Productos y Servicios
    
    - **Soluciones empresariales**: Herramientas diseñadas para optimizar procesos y aumentar la productividad
    - **Plataforma tecnológica**: Infraestructura robusta y escalable
    - **Soporte y consultoría**: Equipo experto disponible para ayudar en cada paso
    - **Innovación continua**: Actualizaciones regulares y nuevas funcionalidades
    
    ### Para Quién Trabajamos
    
    Servimos a empresas de diversos sectores:
    - Tecnología y software
    - Servicios financieros
    - Educación y formación
    - Retail y e-commerce
    
    ### Cultura y Valores
    
    En {company_name}, creemos en:
    - **Innovación**: Buscamos constantemente nuevas formas de resolver problemas
    - **Colaboración**: Trabajamos juntos para lograr objetivos comunes
    - **Transparencia**: Mantenemos comunicación abierta y honesta
    - **Excelencia**: Nos esforzamos por superar expectativas
    
    ### Únete a Nuestro Equipo
    
    Estamos siempre en búsqueda de talento excepcional. Ofrecemos:
    - Ambiente de trabajo flexible
    - Oportunidades de crecimiento profesional
    - Proyectos desafiantes e innovadores
    - Equipo colaborativo y diverso
    
    ### Contacto
    
    ¿Interesado en conocer más sobre {company_name}?
    
    Visita nuestro sitio web para más información sobre nuestros productos, servicios y oportunidades de carrera.
    
    ---
    
    *Contenido generado a partir de fuentes públicas del sitio web en la fecha {date_str}. Este folleto es un resumen no oficial generado automáticamente. Verificar información antes de uso externo.*

"""

def generate_brochure_llm(company_name:str, pages:Dict[str,str], tone:str,
                          model:str, api_key:str)->str:
    """
    Genera un folleto de ejemplo en modo LLM
    Args:
        company_name: Nombre de la empresa
        pages: Contenidos compilados
        tone: Tono del folleto
        model: Modelo a usar
        api_key: API KEY de openAI

    Returns:
        Folleto en markdown
    """

    try:
        client = OpenAI(api_key=api_key)
    except ImportError:
        logger.error("OpenAI API key invalid. Use MOCK_MODE=true.")
        raise

    tone_instruction={
        "formal": "Usa un tono profesional, claro y directo.",
        "humorístico": "Usa un tono amigable y creativo, con toques de humor cuando sea apropiado, pero manteniendo profesionalismo."
    }.get(tone, "Usa un tono profesional.")

    system_prompt=f"""
    Eres un asistente que analiza el contenido limpio de varias páginas de una empresa y redacta un folleto breve en Markdown para clientes, inversores y candidatos.

    {tone_instruction}
    
    Estructura del folleto:
    - Título + slogan breve
    - Qué hacemos (1–2 párrafos)
    - Productos/Servicios (viñetas)
    - Para quién (industrias/beneficios)
    - Casos o clientes destacados (si la información existe)
    - Cultura y valores (viñetas o párrafo breve)
    - Carreras y beneficios (solo si existe información sobre esto)
    - CTA (cómo contactar)
    - Nota ética al final
    
    Usa subtítulos (##, ###) y viñetas. El folleto debe ser breve (2-3 páginas impresas) pero informativo.
"""
    #Preparar contenido
    content_parts=[]
    for page_type, content in pages.items():
        content_parts.append(f"==={page_type.upper()}===\n{content}\n")

    full_content="\n\n".join(content_parts)

    user_prompt=f"""
    Empresa: {company_name}
    
    Contenido de las páginas:
    
    {full_content}
    
    Genera un folleto corporativo profesional en Markdown.
"""
    try:
        response =client.chat.completions.create(
            model=model,
            messages=[
                {"role":"system","content": system_prompt},
                {"role":"user","content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000
        )
        brochure=response.choices[0].message.content

        # Agregar nota etica si no está
        date_str = datetime.now().strftime("%Y-%m-%d")
        if "generado" not in brochure.lower():
            brochure += f"\n\n---\n\n*Contenido generado a partir de fuentes publicas del sitio web en la fecha {date_str}. Este folleto es un resumen no oficial generado automáticamente. Verificar información antes de uso externo.*"

        logger.info("Brochure generated successfully")
        return brochure

    except Exception as e:
        logger.error(f"Error generating brochure with LLM: {e}")
        raise


def generate_brochure(company_name: str, pages: Dict[str, str],
                      tone: str = "formal",
                      api_key: Optional[str] = None,
                      model: str = "gpt-4o-mini") -> str:
    """
    Punto de entrada principal para generacion de folleto.

    Args:
        company_name: Nombre de la empresa
        pages: Contenidos compilados
        tone: Tono del folleto
        api_key: API key (opcional para modo mock)
        model: Modelo a usar

    Returns:
        Folleto en Markdown
    """
    if MOCK_MODE or not api_key:
        return generate_brochure_mock(company_name, pages, tone)
    else:
        return generate_brochure_llm(company_name, pages, tone, api_key, model)