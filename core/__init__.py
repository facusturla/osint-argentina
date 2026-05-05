"""
Paquete core de OSINT Argentina.

Las importaciones se hacen de forma defensiva para que módulos individuales
puedan usarse aunque falten dependencias opcionales (ej: holehe/trio para
email_search, que no instala en todos los entornos).
"""

from core.cuit_validator import analyze_cuit
from core.username_search import load_sites, search_username
from core.email_harvester import harvest_emails
from core.domain_info import get_domain_info
from core.ddjj_lookup import lookup_ddjj
from core.bcra_lookup import lookup_bcra_deudores
from core.georef import normalize_address, search_locality
from core.report_generator import generate_report

try:
    from core.email_search import search_email
except ImportError:
    def search_email(*_args, **_kwargs):
        raise ImportError(
            "El módulo email_search requiere las dependencias 'holehe' y 'trio'. "
            "Instalalas con: pip install holehe trio"
        )
